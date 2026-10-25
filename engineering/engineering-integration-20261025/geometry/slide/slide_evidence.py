"""Independent arithmetic contracts for the scratch continuous SLIDE diagnostic.

This module never imports CAD. Native records are checked against an independently
rebuilt complete material/cage inventory, source-owned motion laws and one Common
volume budget per original material pair. Positive conservative overlap remains
unresolved; no sampled clear result can discharge a continuous interval.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import gzip
import itertools
import json
import math
from pathlib import Path
import sys

import slide_domain as d

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
HELPER_DIR = HERE
INVENTORY = HERE.parent / 'seating/seating-inventory.json'
for directory in (ROOT / 'tools', ROOT / 'integration', HELPER_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
import slide_enclosures as cages
import validate_product_nominal_report as postguard

TOL = postguard.TOL
FPC_LABELS = frozenset(('S', 'U1', 'U2', 'A_straight_core', 'A_taper_wings',
                        'bridge', 'upper_reverse', 'B_final_core', 'B_taper_wings'))
OLED_LABELS = frozenset(('OLED_front', 'OLED_turn', 'OLED_planar_return'))
CLASS_COUNTS = {'rigid_rigid': 10878, 'spring_rigid': 592, 'spring_spring': 6,
                'flex_rigid': 296, 'flex_spring': 8, 'flex_flex': 1}
FALSE_FLAGS = ('canonical_execution_checks_passed', 'complete_G2_qualification',
               'whole_declared_slide_domain_clear', 'physical_qualification',
               'candidate_go', 'fixture_fabrication_go', 'manufacturing_go',
               'formal_directed_rounding_certificate')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def json_value(value):
    return json.loads(json.dumps(value, allow_nan=False))


def recorded_domain(profiles=None):
    # Source-derived interval tuples must compare identically after JSON replay.
    return json_value(d.domain_record(profiles))


def original_profiles():
    from cam_contact_profile import ContactProfile
    source = ROOT/'engineering/thin-mechanism-20261015/native-verification.json.gz'
    data = json.loads(gzip.decompress(source.read_bytes()))
    fields = tuple(ContactProfile.__dataclass_fields__)
    profiles = tuple(ContactProfile(**{key: row['profile'][key] for key in fields})
                     for side in 'LR' for row in data['sides'][side]['contacts'])
    require(len(profiles) == 4, 'all four frozen native source profiles required')
    return profiles


def expected_names():
    names = json.loads(INVENTORY.read_text())['names']
    require(isinstance(names, list) and names == sorted(set(names)) and len(names) == 154
            and d.FLEX | d.SPRINGS | set(d.STOP_ROLES) <= set(names),
            'complete immutable 154-material travel name inventory required')
    return names


def pair_class(a, b):
    flex = len({a, b} & d.FLEX)
    springs = len({a, b} & d.SPRINGS)
    if flex == 2:
        return 'flex_flex'
    if flex:
        return 'flex_spring' if springs else 'flex_rigid'
    return ('rigid_rigid', 'spring_rigid', 'spring_spring')[springs]


def exact_interval(value):
    require(isinstance(value, list) and len(value) == 2 and all(type(v) is str for v in value),
            'two exact rational interval strings required')
    low, high = map(F, value)
    require(0 <= low <= high <= d.QMAX, 'invalid declared q interval')
    return low, high


@dataclass(frozen=True)
class Spring:
    """Original complete X cylinder; its source profile grows one endpoint only."""
    name: str
    base_bounds: tuple
    radius: float = .43

    def __post_init__(self):
        require(self.name in d.SPRINGS and len(self.base_bounds) == 6
                and all(postguard.finite(v) for v in self.base_bounds), 'invalid complete spring source')
        require(all(self.base_bounds[2*i] < self.base_bounds[2*i+1] for i in range(3))
                and self.radius == .43, 'original nonempty .43-mm spring envelope required')
        require(all(abs(self.base_bounds[2*i+1]-self.base_bounds[2*i]-2*self.radius) < 1e-6
                    for i in (1, 2)), 'spring bounding box is not the original complete cylinder')

    @property
    def profile_index(self):
        return 2*('LR'.index(self.name[0])) + int(self.name.split('_')[2])

    def record(self, profiles, low=0, high=12):
        low, high = d.q_interval(low, high)
        profile = profiles[self.profile_index]
        hlow, hhigh = profile.height_bounds(float(low), float(high))
        home = profile.evaluate(0.)[0]
        require(all(postguard.finite(v) for v in (hlow, hhigh, home))
                and hlow <= hhigh <= home + 1e-12, 'source spring profile is not monotone growth')
        sign = -1. if self.name[0] == 'L' else 1.
        shift = sign*(hlow-home)
        lo, hi, ya, yb, za, zb = self.base_bounds
        return {'material': self.name, 'kind': 'complete_growing_spring_cylinder',
                'q_interval_exact': [str(low), str(high)], 'base_bounds_mm': list(self.base_bounds),
                'axis_start_mm': [lo+min(0., shift), (ya+yb)/2, (za+zb)/2],
                'axis_end_mm': [hi+max(0., shift), (ya+yb)/2, (za+zb)/2],
                'radius_mm': self.radius, 'profile_index': self.profile_index,
                'whole_interval_contained_by_monotone_high_q_material': True,
                'profile_height_bounds_mm': [hlow, hhigh], 'profile_home_height_mm': home}


def in_frame(law, frame):
    require(frame in ('A', 'B'), 'unknown relative frame')
    return law if frame == 'A' else law.relative_to(d.Law((0, d.SLIDE_PER_Q, 0)))


@lru_cache(maxsize=8192)
def parameters(law, profiles, low, high):
    vectors, intervals = law.enclosure_parameters(profiles, low, high)
    return tuple(map(tuple, vectors)), tuple(map(tuple, intervals))


class Contract:
    def __init__(self, names, laws, profiles, springs):
        require(names == expected_names(), 'source-owned full inventory changed')
        require(set(laws) == set(names)-d.FLEX-d.SPRINGS and len(laws) == 148,
                'all 148 whole rigid material laws required')
        require(set(springs) == d.SPRINGS and all(s.name == n for n, s in springs.items()),
                'all four independent complete growing spring envelopes required')
        require(len(profiles) == 4, 'four original source profiles required')
        self.names, self.laws, self.profiles, self.springs = names, laws, tuple(profiles), springs
        self.profile_intervals = tuple((F(str(a)), F(str(b))) for a, b in d.profile_intervals(profiles))
        self.pairs = tuple(itertools.combinations(names, 2))
        require(dict(Counter(pair_class(a, b) for a, b in self.pairs)) == CLASS_COUNTS,
                'complete material pair classification changed')

    @lru_cache(maxsize=256)
    def cage_rows(self, material, low, high, frame):
        require(material in d.FLEX, 'unknown finite flexible material')
        rows = list(cages.fpc_grouped(low, high, frame) if material == 'EP5_finite_material'
                    else cages.oled_cages(low, high, frame))
        expected = FPC_LABELS if material == 'EP5_finite_material' else OLED_LABELS
        require(len(rows) == len(expected) and {r['label'] for r in rows} == expected,
                'complete finite polygon/cage inventory changed')
        for row in rows:
            bounds = cages.record_bounds(row)
            require(len(bounds) == 6 and all(postguard.finite(v) for v in bounds)
                    and all(bounds[2*i] < bounds[2*i+1] for i in range(3)),
                    'nonfinite or empty whole-material cage')
        return tuple(rows)

    def body_reference(self, name, low, high, frame='A', cage=None):
        if cage is not None:
            return {'kind': 'finite_flexible_cage', 'material': name,
                    'cage_label': cage['label'], 'cage_sha256': digest_json(cage),
                    'bounds_mm': list(cages.record_bounds(cage)), 'reference_frame': frame}
        if name in d.SPRINGS:
            return self.springs[name].record(self.profiles, low, high)
        require(name in self.laws, 'unknown rigid material')
        return {'kind': 'complete_rigid_material', 'material': name}

    def specifications(self, a, b, low, high, frame='A'):
        """Rebuild every actual kernel-call input descriptor from source laws."""
        require(a < b and a in self.names and b in self.names, 'ordered expected pair required')
        low, high = d.q_interval(low, high)
        kind = pair_class(a, b)
        require(frame in ('A', 'B') and (kind.startswith('flex') or frame == 'A'),
                'non-flexible pair uses its original relative material frame')
        result = []

        def add(moving, fixed, law=d.ZERO):
            vectors, intervals = parameters(law, self.profiles, low, high)
            result.append({'moving': moving, 'fixed': fixed, 'relative_law': law.record(),
                           'coefficients': list(map(list, vectors)),
                           'parameter_intervals': list(map(list, intervals))})

        ref = lambda name: self.body_reference(name, low, high)
        if kind == 'rigid_rigid':
            add(ref(a), ref(b), self.laws[a].relative_to(self.laws[b]))
        elif kind == 'spring_rigid':
            spring = next(n for n in (a, b) if n in d.SPRINGS)
            rigid = b if a == spring else a
            add(ref(rigid), ref(spring), self.laws[rigid])
        elif kind == 'spring_spring':
            add(ref(a), ref(b))
        elif kind == 'flex_flex':
            for ca in self.cage_rows(a, low, high, frame):
                for cb in self.cage_rows(b, low, high, frame):
                    add(self.body_reference(a, low, high, frame, ca),
                        self.body_reference(b, low, high, frame, cb))
        else:
            flexible = next(n for n in (a, b) if n in d.FLEX)
            other = b if a == flexible else a
            law = self.laws[other] if other in self.laws else d.ZERO
            law = in_frame(law, frame)
            for cage in self.cage_rows(flexible, low, high, frame):
                add(ref(other), self.body_reference(flexible, low, high, frame, cage), law)
        return result

    def child_intervals(self, low, high, split):
        require(low < high, 'cannot split an empty q interval')
        if split == 'all_actual_profile_breakpoints':
            require((low, high) == (F(0), d.QMAX), 'profile partition must cover the original full domain')
            return self.profile_intervals
        require(split == 'closed_midpoint_bisection', 'unknown continuous interval partition')
        middle = (low+high)/2
        return ((low, middle), (middle, high))


def aggregate(records):
    """Exactly one volume budget for the whole original physical pair."""
    require(isinstance(records, list) and records, 'nonempty complete region evidence required')
    values = []
    unresolved = False
    for record in records:
        raw = record['raw']
        postguard.validate_frame(raw)
        if raw['disposition'] != 'clear':
            unresolved = True
        else:
            value = 0. if raw['method'] == 'continuous_relative_axis_gap' else raw['common_upper_bound_mm3']
            require(postguard.finite(value) and value >= 0., 'invalid whole material Common bound')
            values.append(value)
    if unresolved:
        return {'disposition': 'unresolved_enclosure_overlap', 'whole_material_region_count': len(records),
                'collision_proved': False, 'complete_common_upper_bound_available': False}
    upper = math.fsum(values)
    require(postguard.finite(upper), 'nonfinite whole material Common bound')
    return {'disposition': 'clear' if upper <= TOL else 'unresolved_enclosure_overlap',
            'whole_material_region_count': len(records), 'common_upper_bound_mm3': upper,
            'common_upper_bound_is_sum_not_union_volume': True,
            'complete_common_upper_bound_available': True, 'collision_proved': False}


def errors_in(value, path='root'):
    result = []
    if isinstance(value, dict):
        if value.get('disposition') == 'unresolved_evaluation' or 'error' in value:
            result.append({'path': path, 'error': value.get('error', 'native evaluation failure')})
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                result.extend(errors_in(item, path+'.'+key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.extend(errors_in(item, path+'['+str(index)+']'))
    return result


def pending_in(value):
    if isinstance(value, dict):
        return (int(value.get('disposition') in ('not_evaluated', 'unresolved_budget'))
                +sum(pending_in(item) for item in value.values() if isinstance(item, (dict, list))))
    return sum(pending_in(item) for item in value) if isinstance(value, list) else 0


def validate_interval(row, a, b, low, high, contract, depth=0):
    require(isinstance(row, dict) and depth <= 7
            and exact_interval(row.get('q_interval_exact')) == (low, high),
            'missing, deep, or incorrect continuous q interval')
    disposition = row.get('disposition')
    require(disposition in ('clear', 'unresolved_enclosure_overlap', 'unresolved_evaluation', 'unresolved_budget'),
            'unknown interval disposition')
    attempts = row.get('attempts')
    require(isinstance(attempts, list) and 1 <= len(attempts) <= 2, 'native frame attempt inventory missing')
    frames = [r.get('reference_frame') for r in attempts]
    allowed = {'A', 'B'} if pair_class(a, b).startswith('flex') else {'A'}
    require(len(set(frames)) == len(frames) and set(frames) <= allowed, 'duplicate or invalid relative frame')
    proven = False
    for attempt in attempts:
        if attempt.get('disposition') in ('unresolved_budget', 'unresolved_evaluation'):
            continue
        expected = contract.specifications(a, b, low, high, attempt['reference_frame'])
        records = attempt.get('records')
        require(isinstance(records, list) and len(records) == len(expected)
                and [r.get('specification') for r in records] == expected,
                'native material/region/law/domain descriptor is incomplete or substituted')
        actual = aggregate(records)
        require(all(attempt.get(key) == value for key, value in actual.items()),
                'native raw values disagree with whole material Common disposition')
        proven |= actual['disposition'] == 'clear'
    children_clear = False
    if 'children' in row:
        intervals = contract.child_intervals(low, high, row.get('split'))
        children = row['children']
        require(isinstance(children, list) and len(children) == len(intervals),
                'continuous closed interval partition has a missing/duplicate child')
        child_flags = [validate_interval(child, a, b, lo, hi, contract, depth+1)
                       for child, (lo, hi) in zip(children, intervals)]
        children_clear = all(child_flags)
    if disposition == 'clear':
        require((row.get('method') == 'whole_material_relative_enclosure' and proven and 'children' not in row)
                or (row.get('method') == 'complete_closed_interval_partition' and children_clear),
                'clear continuous material pair lacks a complete finite enclosure proof')
        return True
    return False


def validate_pair(row, contract):
    a, b = row['a'], row['b']
    require(row.get('pair_class') == pair_class(a, b), 'whole material pair classification changed')
    if row.get('disposition') in ('not_evaluated', 'unresolved_budget'):
        return False
    return validate_interval(row, a, b, F(0), d.QMAX, contract)


def validate_metadata(meta):
    scene = meta.get('scene', {})
    require(meta.get('combined_participants') == 154 and meta.get('mechanical_participants') == 108
            and meta.get('candidate_participants') == 41 and scene.get('installed_mechanical_parts') == 108
            and scene.get('factory') == 'integration/product_split_assembly.py:split_scene'
            and scene.get('slide_mm') == scene.get('descent_mm') == 0.
            and scene.get('left_tab_mm') == scene.get('right_tab_mm') == 3.
            and scene.get('slot_flanks') == [0., 0.]
            and scene.get('KEY_offsets_mm') == scene.get('crosshead_offsets_mm') == [0., 0.]
            and scene.get('telescope_offsets_by_side_mm') == {s: [float(d.JOINT_NOMINAL)]*3 for s in 'LR'}
            and scene.get('OPEN_hold_screws_installed') is False
            and scene.get('OPEN_display_support_insert_installed') is False,
            'native base is not the complete full_scene(0,0,3,3) equal-joint zero-offset factory')
    for key in ('physical_holding_and_force_qualified', 'OPEN_thread_retention_load_qualified',
                'loose_OPEN_accessories_have_onboard_storage', 'complete_functional_phone',
                'candidate_go', 'manufacturing_go'):
        require(scene.get(key) is False, 'native factory physical scope changed: '+key)


def probe_inputs(profiles):
    """Finite probes only complement the source-owned continuous laws."""
    qs = {F(0), d.QMAX}
    for profile in profiles:
        a, b, c = map(lambda value: F(str(value)), profile.breakpoints)
        qs.update(((a+b)/2, (b+c)/2))
    vertices = d.joint_vertices()
    return [{'q_exact': str(q), 'joints_left_exact': list(map(str, vertices[index%3])),
             'joints_right_exact': list(map(str, vertices[(index+1)%3])),
             'flanks': [-1., 1.] if index%2 else [.65, -.4]}
            for index, q in enumerate(sorted(qs))]


def validate_construction(record, contract):
    springs = record.get('original_complete_spring_identity', [])
    require(len(springs) == 4 and {r.get('material') for r in springs} == d.SPRINGS,
            'base complete spring identity checks missing')
    for row in springs:
        require(row.get('spring_descriptor') == contract.springs[row['material']].record(contract.profiles, 0, 0),
                'base spring cylinder descriptor changed')
    expected = probe_inputs(contract.profiles)
    probes = record.get('probes', [])
    require(len(probes) == len(expected) and [r.get('inputs') for r in probes] == expected
            and record.get('source_laws_not_inferred_from_samples') is True,
            'actual factory probe parameter inventory missing or substituted')
    all_checks = list(springs)
    for probe in probes:
        checked = probe.get('material_law_checks', [])
        require(probe.get('complete_participant_names') == contract.names
                and len(checked) == 152 and {r.get('material') for r in checked} == set(contract.names)-d.FLEX
                and probe.get('source_laws_not_inferred_from_samples') is True,
                'probe omitted an actual factory rigid or spring material')
        flexible = probe.get('flexible_materials_retained', [])
        require(len(flexible) == 2 and {r.get('material') for r in flexible} == d.FLEX,
                'complete actual flexible materials absent from probe')
        for row in flexible:
            require(type(row.get('positive_solid_count')) is int and row['positive_solid_count'] > 0
                    and postguard.finite(row.get('whole_volume_mm3')) and row['whole_volume_mm3'] > 0
                    and row.get('whole_material_validation_passed') is True,
                    'native flexible material validity/whole positive volume absent')
        inputs = probe['inputs']
        scene = probe.get('native_scene_metadata', {}).get('scene', {})
        require(scene.get('slide_mm') == float(d.SLIDE_PER_Q*F(inputs['q_exact']))
                and scene.get('descent_mm') == 0.
                and scene.get('left_tab_mm') == scene.get('right_tab_mm') == 3.
                and scene.get('slot_flanks') == inputs['flanks']
                and scene.get('KEY_offsets_mm') == scene.get('crosshead_offsets_mm') == [0., 0.]
                and scene.get('telescope_offsets_by_side_mm') == {
                    'L': list(map(lambda x: float(F(x)), inputs['joints_left_exact'])),
                    'R': list(map(lambda x: float(F(x)), inputs['joints_right_exact']))}
                and scene.get('OPEN_hold_screws_installed') is False
                and scene.get('OPEN_display_support_insert_installed') is False,
                'actual factory probe metadata differs from its finite source-law inputs')
        all_checks.extend(checked)
    for check in all_checks:
        values = check.get('bidirectional_difference_mm3')
        require(isinstance(values, list) and len(values) == 2
                and all(postguard.finite(v) and 0. <= v <= TOL for v in values),
                'rejected or invalid complete material identity probe')
    return True


def complete_result(report, contract, current_identity, current_sources):
    rows = report.get('pairs', [])
    actual = [(row.get('a'), row.get('b')) for row in rows]
    inventory = (report.get('complete_participant_names') == contract.names
                 and len(actual) == len(set(actual)) == len(contract.pairs)
                 and set(actual) == set(contract.pairs))
    numerical_failures = errors_in(rows, 'pairs')
    validation_failures = []
    proven = 0
    for row in rows:
        try:
            proven += validate_pair(row, contract)
        except Exception as exc:
            validation_failures.append({'a': row.get('a'), 'b': row.get('b'),
                                        'error': type(exc).__name__+': '+str(exc)})
    try:
        validate_metadata(report.get('native_scene_metadata', {}))
        require(report.get('domain') == recorded_domain(contract.profiles), 'declared motion domain differs')
        require(report.get('participant_count') == 154 and report.get('pair_count') == report.get('expected_pair_count') == 11781
                and report.get('pair_class_counts') == CLASS_COUNTS, 'declared full pair scope/count differs')
        require(report.get('native_checks_executed') is True and report.get('execution_completed') is True,
                'original native producer did not complete execution')
        require(all(report.get(flag) is False for flag in FALSE_FLAGS), 'scratch metadata overclaims scope')
        require(report.get('construction_probes_complete') is True, 'complete actual factory law probes missing')
        validate_construction(report.get('construction', {}), contract)
    except Exception as exc:
        validation_failures.append({'error': type(exc).__name__+': '+str(exc)})
    identities = (current_identity is not None and report.get('identity_before') == current_identity
                  and report.get('identity_after') == current_identity
                  and report.get('scratch_source_sha256_before') == current_sources
                  and report.get('scratch_source_sha256_after') == current_sources
                  and current_identity.get('environment', {}).get('passed') is True
                  and current_identity.get('executed_source_overlay') is False
                  and current_identity.get('repository_head') == report.get('expected_head'))
    pending = sum(row.get('disposition') in ('not_evaluated', 'unresolved_budget') for row in rows)
    nested_pending = pending_in(rows)
    complete = (inventory and identities and not pending and not numerical_failures
                and not nested_pending and not validation_failures
                and not report.get('terminal_failure') and not report.get('postflight_failure'))
    return {'all_unordered_pairs_present_once': inventory,
            'source_bytes_and_locked_environment_unchanged': identities,
            'raw_evidence_validation_failure_count': len(validation_failures),
            'raw_evidence_validation_failures_first_100': validation_failures[:100],
            'evaluation_failure_count': len(numerical_failures), 'evaluation_failures': numerical_failures,
            'pending_pair_count': pending, 'independently_validated_clear_pair_count': proven,
            'recursive_pending_or_budget_node_count': nested_pending,
            'complete_native_diagnostic_executed': complete,
            'whole_declared_slide_external_pair_domain_clear': complete and proven == len(contract.pairs),
            'external_pair_scope_only': True,
            'continuous_native_flexible_self_validity_not_inferred_from_pair_checks': True,
            **{key: False for key in FALSE_FLAGS}}


def contract_from_report(report):
    """Rebuild the saved-receipt checker without importing native geometry."""
    names = expected_names()
    profiles = original_profiles()
    require(report.get('profiles') == [asdict(p) for p in profiles],
            'saved profile data differs from the original frozen native source')
    halfwidth = report.get('native_slot_halfwidth_mm')
    require(isinstance(halfwidth, dict) and set(halfwidth) == {'L', 'R'}, 'actual native slot measurements missing')
    laws = d.rigid_laws(names, halfwidth, names)
    require(report.get('rigid_motion_laws') == {name: law.record() for name, law in sorted(laws.items())},
            'saved rigid classification/laws differ from current source')
    raw = report.get('base_spring_records')
    require(isinstance(raw, dict) and set(raw) == d.SPRINGS, 'all four actual base spring records required')
    springs = {name: Spring(name, tuple(row['base_bounds_mm'])) for name, row in raw.items()}
    require(raw == {name: spring.record(profiles, 0, 0) for name, spring in springs.items()},
            'original complete spring identity/dimensions differ')
    return Contract(names, laws, profiles, springs)
