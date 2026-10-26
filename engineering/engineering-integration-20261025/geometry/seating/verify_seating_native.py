"""Prepared native SEATING diagnostic; CAD requires the explicit --native flag.

This scratch adapter cannot grant canonical G2 or physical release. It retains
the full 154-part travel inventory, represents the common descent exactly, and
encloses the original finite FPC/OLED material rather than making them rigid.
Resource checks occur between native operators; an external wall/memory
supervisor is still required to interrupt a single long-running OCCT operation.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import seating_domain as domain
import seating_enclosures as enclosure
import seating_checkpoint as checkpoint
import owned_process

HERE = Path(__file__).resolve().parent
ROOT = enclosure.ROOT
if str(ROOT / 'tools') not in sys.path:
    sys.path.insert(0, str(ROOT / 'tools'))
import validate_product_nominal_report as postguard

TOL = 1e-7
DEFAULT_HEAD = '042b768903cccbd7a0995317c8598401e0318e2a'
SOURCE_NAMES = ('seating_domain.py', 'seating_enclosures.py', 'verify_seating_native.py',
                'test_seating_arithmetic.py', 'seating-inventory.json', 'run_seating_preparation.py',
                'seating_checkpoint.py', 'check_seating_checkpoint.py', 'test_seating_checkpoint.py',
                'supervise_seating_native.py', 'owned_process.py', 'test_owned_process.py',
                'test_seating_supervisor_lifecycle.py')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def adapter_identity():
    if HERE != ROOT / 'engineering/engineering-integration-20261025/geometry/seating':
        raise ValueError('the portable adapter must run from its declared repository source path')
    if Path(owned_process.__file__).resolve() != HERE/'owned_process.py':
        raise ValueError('the executed owned-child helper differs from its source-bound path')
    return {name: digest(HERE / name) for name in SOURCE_NAMES}


def expected_inventory():
    record = json.loads((HERE / 'seating-inventory.json').read_text())
    names = record['names']
    if len(names) != len(set(names)) or len(names) != 154 or not domain.FLEXIBLE <= set(names):
        raise ValueError('complete unique 154-part expected travel inventory required')
    return sorted(names)


def collect_evaluation_errors(value, path='root'):
    """Keep every failed attempt, including a failed opposite-frame try."""
    result = []
    if isinstance(value, dict):
        if value.get('disposition') == 'unresolved_evaluation':
            result.append({'path': path, 'error': value.get('error', 'missing error detail')})
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                result.extend(collect_evaluation_errors(item, path + '.' + key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.extend(collect_evaluation_errors(item, path + '[' + str(index) + ']'))
    return result


def aggregate_material_regions(rows):
    """One tolerance for the whole original participant, not per cage region."""
    if not rows:
        raise ValueError('an empty material enclosure is forbidden')
    for row in rows:
        postguard.validate_frame(row)
    if any(row.get('disposition') != 'clear' for row in rows):
        return {'disposition': 'unresolved_enclosure_overlap', 'regions': rows,
                'collision_proved': False, 'whole_material_region_count': len(rows)}
    values = []
    for row in rows:
        if row.get('method') == 'continuous_relative_axis_gap':
            value = 0.
        elif 'common_upper_bound_mm3' in row:
            value = row['common_upper_bound_mm3']
        else:
            raise ValueError('a clear native region lacks a complete Common upper bound')
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0.:
            raise ValueError('invalid material region Common bound')
        values.append(value)
    upper = math.fsum(values)
    if not math.isfinite(upper):
        raise ValueError('nonfinite complete material Common upper bound')
    return {'disposition': 'clear' if upper <= TOL else 'unresolved_enclosure_overlap',
            'method': 'sum_of_complete_material_region_Common_upper_bounds',
            'regions': rows, 'common_upper_bound_mm3': upper,
            'whole_material_region_count': len(rows),
            'common_upper_bound_is_sum_not_union_volume': True, 'collision_proved': False}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_interval(values):
    require(isinstance(values, list) and len(values) == 2, 'two exact interval endpoints required')
    low, high = map(domain.fraction, values)
    require(low <= high, 'reversed exact interval')
    return low, high


def validate_flexible_interval(row, flexible, law, low, high, depth=0):
    """Independently derive complete interval/cage coverage from raw evidence."""
    require(isinstance(row, dict) and depth <= 9, 'invalid/deep flexible interval evidence')
    require(exact_interval(row.get('descent_interval_exact')) == (low, high),
            'flexible interval does not represent its entire expected domain')
    disposition = row.get('disposition')
    require(disposition in ('clear', 'unresolved_enclosure_overlap', 'unresolved_evaluation', 'unresolved_budget'),
            'unknown flexible interval disposition')
    attempts = row.get('attempts')
    require(isinstance(attempts, list) and 0 < len(attempts) <= 2, 'relative frame attempts absent or duplicated')
    frames = [a.get('reference_frame') for a in attempts]
    require(len(frames) == len(set(frames)) and set(frames) <= {'A', 'B'}, 'invalid relative frames')
    established = False
    for attempt in attempts:
        kind = attempt.get('disposition')
        if kind in ('unresolved_evaluation', 'unresolved_budget'):
            continue
        require(kind in ('clear', 'unresolved_enclosure_overlap'), 'unknown cage aggregate disposition')
        frame = attempt['reference_frame']
        expected_shift = law.in_frame(frame).projection(low, high)
        require(exact_interval(attempt.get('rigid_relative_Z_interval_exact')) == expected_shift,
                'rigid/cage relative domain differs from the complete shared-descent projection')
        cages = (enclosure.fpc_grouped(float(low), float(high), frame) if flexible == 'EP5_finite_material'
                 else enclosure.oled_cages(float(low), float(high), frame))
        expected_labels = {cage['label'] for cage in cages}
        records = attempt.get('regions')
        require(isinstance(records, list) and len(records) == len(expected_labels),
                'complete FPC/OLED cage region count missing')
        labels = [record.get('cage') for record in records]
        require(len(labels) == len(set(labels)) and set(labels) == expected_labels,
                'duplicate, missing or substituted complete material cage')
        derived = aggregate_material_regions(records)
        require(attempt.get('whole_material_region_count') == len(expected_labels)
                and kind == derived['disposition'], 'raw cage regions disagree with aggregate disposition')
        if kind == 'clear':
            require(attempt.get('method') == derived['method']
                    and postguard.finite(attempt.get('common_upper_bound_mm3'))
                    and attempt['common_upper_bound_mm3'] == derived['common_upper_bound_mm3']
                    and attempt.get('common_upper_bound_is_sum_not_union_volume') is True,
                    'whole material Common sum is missing, nonfinite, or inconsistent')
            established = True
    children = row.get('children')
    children_clear = False
    if children is not None:
        require(isinstance(children, list) and len(children) == 2 and low < high,
                'continuous interval partition must contain both nonempty children')
        middle = (low + high) / 2
        first = validate_flexible_interval(children[0], flexible, law, low, middle, depth + 1)
        second = validate_flexible_interval(children[1], flexible, law, middle, high, depth + 1)
        children_clear = first and second
    if disposition == 'clear':
        method = row.get('method')
        require((method == 'whole_material_relative_cage' and established and children is None)
                or (method == 'closed_interval_partition_with_complete_material_cages' and children_clear),
                'clear flexible family lacks a complete frame or gap-free closed-interval partition')
        return True
    return False


def validate_pair_evidence(row, laws):
    """Validate numeric native evidence and the declared complete material domain."""
    a, b = row['a'], row['b']
    require(row.get('disposition') in ('clear', 'unresolved_enclosure_overlap',
            'unresolved_evaluation', 'unresolved_budget', 'not_evaluated'), 'unknown pair disposition')
    if row['disposition'] in ('not_evaluated', 'unresolved_budget', 'unresolved_evaluation'):
        return False
    flexible = {a, b} & domain.FLEXIBLE
    if not flexible:
        require(row.get('pair_class') == 'rigid_rigid_shared_descent_polytope', 'rigid pair evidence class differs')
        require(exact_interval(row.get('exact_relative_Z_interval_mm')) == laws[a].relative_to(laws[b]).projection(),
                'rigid pair projected independent descents or an incomplete allocation domain')
        postguard.validate_frame(row)
    elif len(flexible) == 2:
        require(row.get('pair_class') == 'complete_FPC_OLED_material', 'flex/flex material certificate missing')
        derived = enclosure.flex_flex_certificate()
        observed = row.get('gap_lower_mm')
        require(isinstance(observed, dict) and set(observed) == set(derived['gap_lower_mm'])
                and all(postguard.finite(value) and value > 0. for value in observed.values())
                and observed == derived['gap_lower_mm'], 'whole FPC/OLED regional gaps are invalid or differ')
        require(row.get('whole_seating_parameter_domain') is True
                and row.get('actual_native_Common_executed') is False,
                'analytic whole-family coverage was substituted for a native Common result')
    else:
        require(row.get('pair_class') == 'deforming_flexible_complete_rigid_material', 'flex/rigid evidence class differs')
        flex = next(iter(flexible)); rigid = b if a == flex else a
        return validate_flexible_interval(row, flex, laws[rigid], F(0), domain.SEATING)
    return row['disposition'] == 'clear'


class BudgetExceeded(RuntimeError):
    def __init__(self, message, partial=None):
        super().__init__(message)
        self.partial = partial


class Budget:
    def __init__(self, args):
        self.started = time.monotonic()
        self.args = args
        self.pair_calls = 0

    def check(self, operator=False):
        if time.monotonic() - self.started > self.args.seconds:
            raise BudgetExceeded('between-operator wall-time budget exhausted')
        disk = os.statvfs('/tmp')
        if disk.f_bavail * disk.f_frsize < self.args.minimum_available_disk_mib * 2**20:
            raise BudgetExceeded('f_bavail disk reserve is below the requested minimum')
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        if rss > self.args.maximum_rss_mib * 2**20:
            raise BudgetExceeded('observed peak RSS exceeds the requested between-operator budget')
        if operator:
            if self.pair_calls >= self.args.maximum_pair_calls:
                raise BudgetExceeded('continuous-pair call budget exhausted')
            self.pair_calls += 1

    def record(self):
        return {'wall_seconds': time.monotonic() - self.started,
                'peak_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'continuous_pair_calls': self.pair_calls,
                'limits_checked_between_operators_not_hard_preemption': True,
                'f_bavail_is_budget_not_root_reserved_blocks': True}


def arithmetic_repository_identity(expected_head):
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    if head != expected_head or len(expected_head) != 40:
        raise ValueError('repository HEAD differs from the explicitly expected full commit')
    # The in-repository .venv is a locked dependency installation, not a
    # project source tracked by Git. Bind only actual project source areas.
    source_areas = tuple(ROOT / name for name in ('integration', 'design', 'engineering', 'tools'))
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
             if getattr(module, '__file__', None) and str(module.__file__).endswith('.py')
             and any(Path(module.__file__).resolve().is_relative_to(area) for area in source_areas)}
    paths.update(ROOT / relative for relative in (
        'integration/product_assembly.py', 'integration/product_split_assembly.py',
        'integration/product_motion.py', 'integration/product_nominal_motion.py',
        'integration/oled_storage.py', 'integration/product_fpc.py',
        'integration/verify_cam_coupling.py', 'integration/verify_endpoint_joint_pawl.py',
        'design/product_geometry.json', 'design/product_routing_ep5.json',
        'design/product_routing_ep4.json', 'pyproject.toml', 'uv.lock'))
    sources = {}
    for path in sorted(paths):
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        frozen = subprocess.check_output(['git', '-C', str(ROOT), 'show', head + ':' + relative])
        if raw != frozen:
            raise ValueError('arithmetic source/configuration differs from the selected HEAD: ' + relative)
        sources[relative] = hashlib.sha256(raw).hexdigest()
    return {'repository_head': head, 'head_bound_arithmetic_sources_and_configs': sources,
            'native_input_closure_and_locked_environment_not_evaluated': True}


def preparation_report(expected_head=DEFAULT_HEAD):
    before = arithmetic_repository_identity(expected_head)
    adapter = adapter_identity()
    names = expected_inventory()
    report = {'schema': 'razr-complete-seating-preparation-v2',
              'domain': domain.domain_record(), 'expected_participant_names': names,
              'pair_inventory': {'rigid_rigid': math.comb(152, 2), 'flex_rigid': 2 * 152,
                                 'flex_flex': 1, 'all_unordered_pairs': math.comb(154, 2)},
              'finite_FPC_cell_contract': enclosure.chord_cell_contract(),
              'full_finite_FPC_vs_OLED_regional_certificate': enclosure.flex_flex_certificate(),
              'FPC_cell_count': len(enclosure.fpc_cells()),
              'FPC_native_group_count': len(enclosure.fpc_grouped()),
              'OLED_native_region_count': len(enclosure.oled_cages()),
              'native_checks_executed': False, 'whole_declared_seating_domain_clear': False,
              'canonical_execution_checks_passed': False, 'complete_G2_qualification': False,
              'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False,
              'adapter_source_sha256': adapter, 'arithmetic_identity_before': before}
    after = arithmetic_repository_identity(expected_head)
    if before != after or adapter != adapter_identity():
        raise ValueError('arithmetic preparation source bytes changed during execution')
    report['arithmetic_identity_after'] = after
    report['arithmetic_preparation_source_identity_unchanged'] = True
    report['CAD_imported'] = any(name == 'cadquery' or name == 'OCP' or name.startswith('OCP.')
                                 for name in sys.modules)
    if report['CAD_imported']:
        raise ValueError('pure arithmetic preparation unexpectedly imported CAD')
    return report


def verify_factory_rigid_laws(base, laws, nominal, p, before, budget):
    """Actual body equality probes complement, but do not infer, code-owned laws."""
    results = []
    for d in (F('2.6'), F('4.1'), F('8.2')):
        budget.check()
        vertices = domain.joints_at(d)
        left, right = vertices[0], vertices[-1]
        values = (d, left[0], left[1], right[0], right[1], F('-.4'), F('.65'))
        allocations = {'L': list(map(float, left)), 'R': list(map(float, right))}
        actual, metadata = nominal.full_scene(79.75, float(d), 3., 3., flanks=(-.4, .65),
                            telescope_offsets=allocations, key_offsets=(0., 0.),
                            crosshead_offsets=(0., 0.), open_hold=False, open_support=False)
        enclosure.ep5.validate_factory_input_coverage(metadata['scene'], before['executed_source_sha256'])
        if set(actual) != set(base):
            raise ValueError('factory probe changed the complete participant inventory')
        maximum = 0.
        for name in sorted(laws):
            budget.check()
            p.whole_material(actual[name])
            shift = float(laws[name].evaluate(values))
            expected = base[name].translate((0., 0., shift)) if shift else base[name]
            difference = (0. if actual[name].isSame(expected) else
                          max(p.volume(actual[name].cut(expected)), p.volume(expected.cut(actual[name]))))
            maximum = max(maximum, difference)
            if difference > TOL:
                raise ValueError('source-owned Z law does not represent native material: ' + name)
        results.append({'descent_mm': float(d), 'joints_by_side_mm': allocations,
                        'flanks': [-.4, .65], 'rigid_materials_checked': len(laws),
                        'maximum_bidirectional_material_difference_mm3': maximum,
                        'complete_factory_reconstructed_including_both_flexible_bodies': True,
                        'samples_do_not_establish_continuous_law': True})
        del actual
    return results


class CageCache:
    def __init__(self, maximum=16):
        self.maximum = maximum
        self.values = OrderedDict()

    def get(self, flexible, low, high, frame, budget):
        key = (flexible, str(low), str(high), frame)
        if key not in self.values:
            budget.check()
            rows = (enclosure.fpc_grouped(float(low), float(high), frame)
                    if flexible == 'EP5_finite_material' else enclosure.oled_cages(float(low), float(high), frame))
            value = [(row, enclosure.native_cage(row)) for row in rows]
            self.values[key] = value
            while len(self.values) > self.maximum:
                self.values.popitem(last=False)
        self.values.move_to_end(key)
        return self.values[key]


def flexible_rigid_interval(flexible, body, law, low, high, depth, nominal, p, cache, budget):
    """Complete correlated family -> conservative whole-material relative cages."""
    frames = ('B', 'A') if law == domain.B_FOLLOWING else ('A', 'B')
    attempts = []
    for frame in frames:
        rows = []
        try:
            zlow, zhigh = law.in_frame(frame).projection(low, high)
            for cage, native in cache.get(flexible, low, high, frame, budget):
                budget.check(operator=True)
                result = nominal.continuous_pair(body, native, [[0., 0., 1.]],
                         b_bounds=enclosure.record_bounds(cage), domain=((float(zlow), float(zhigh)),))
                rows.append({'cage': cage['label'], **result})
            attempt = {**aggregate_material_regions(rows), 'reference_frame': frame,
                       'rigid_relative_Z_interval_exact': [str(zlow), str(zhigh)]}
        except BudgetExceeded as exc:
            exc.partial = {'disposition': 'unresolved_budget',
                           'descent_interval_exact': [str(low), str(high)],
                           'attempts': attempts, 'interrupted_frame': frame,
                           'completed_regions_in_interrupted_frame': rows,
                           'resource_stop': str(exc), 'collision_proved': False}
            raise
        except Exception as exc:
            attempt = {'reference_frame': frame, 'disposition': 'unresolved_evaluation',
                       'error': type(exc).__name__ + ': ' + str(exc),
                       'completed_regions_before_failure': rows, 'collision_proved': False}
        attempts.append(attempt)
        if attempt['disposition'] == 'clear':
            return {'disposition': 'clear', 'method': 'whole_material_relative_cage',
                    'descent_interval_exact': [str(low), str(high)], 'attempts': attempts}
    result = {'disposition': 'unresolved_enclosure_overlap',
              'descent_interval_exact': [str(low), str(high)], 'attempts': attempts,
              'collision_proved': False}
    if depth > 0 and low < high:
        # The two closed intervals cover the entire parent. No pose sampling.
        middle = (low + high) / 2
        children = []
        for a, b in ((low, middle), (middle, high)):
            try:
                children.append(flexible_rigid_interval(flexible, body, law, a, b, depth - 1,
                                                        nominal, p, cache, budget))
            except BudgetExceeded as exc:
                if exc.partial is not None:
                    children.append(exc.partial)
                exc.partial = {**result, 'disposition': 'unresolved_budget',
                               'children': children, 'resource_stop': str(exc)}
                raise
        result['children'] = children
        if all(row['disposition'] == 'clear' for row in children):
            result['disposition'] = 'clear'
            result['method'] = 'closed_interval_partition_with_complete_material_cages'
    return result


def check_complete_result(names, pairs, before, after, own_before, own_after,
                          construction_completed, execution_failed=False, laws=None):
    expected = set(itertools.combinations(sorted(names), 2))
    actual = [(row['a'], row['b']) for row in pairs]
    inventory = (len(names) == len(set(names)) == 154 and set(names) == set(expected_inventory())
                 and len(actual) == len(set(actual)) == len(expected) and set(actual) == expected)
    failures = collect_evaluation_errors(pairs, 'pairs')
    pending = any(row.get('disposition') in ('not_evaluated', 'unresolved_budget') for row in pairs)
    source_unchanged = (before is not None and after is not None and before == after
                        and own_before == own_after)
    locked = (before is not None and after is not None
              and before.get('environment', {}).get('passed') is True
              and after.get('environment', {}).get('passed') is True)
    proof_errors = []
    proof_error_count = 0
    if not isinstance(laws, dict) or set(laws) != set(names) - domain.FLEXIBLE:
        proof_errors.append({'error': 'complete source-owned rigid law inventory absent'})
        proof_error_count = 1
    else:
        for row in pairs:
            try:
                validate_pair_evidence(row, laws)
            except Exception as exc:
                proof_error_count += 1
                if len(proof_errors) < 100:
                    proof_errors.append({'a': row.get('a'), 'b': row.get('b'),
                                         'error': type(exc).__name__ + ': ' + str(exc)})
    complete = (inventory and source_unchanged and locked and construction_completed
                and not pending and not failures and not execution_failed and not proof_error_count)
    clear = complete and all(row.get('disposition') == 'clear' for row in pairs)
    return {'all_unordered_pairs_present_once': inventory,
            'source_bytes_unchanged': source_unchanged,
            'evaluation_failures': failures, 'evaluation_failure_count': len(failures),
            'raw_evidence_validation_failures_first_100': proof_errors,
            'raw_evidence_validation_failure_count': proof_error_count,
            'complete_native_diagnostic_executed': complete,
            'whole_declared_seating_external_pair_domain_clear': clear,
            'whole_declared_seating_domain_clear': False,
            'external_pair_scope_only': True,
            'continuous_native_flexible_self_validity_not_inferred_from_pair_checks': True,
            'canonical_execution_checks_passed': False,
            'complete_G2_qualification': False,
            'source_owned_scratch_adapter_identity_explicit': True}


def run_native(args):
    # No import above this point constructs or imports CAD.
    import product_nominal_motion as nominal
    import product_assembly as p
    names = expected_inventory()
    rows = [{'a': a, 'b': b, 'disposition': 'not_evaluated'} for a, b in itertools.combinations(names, 2)]
    budget = Budget(args)
    own_before = adapter_identity()
    before = after = None
    laws = None
    construction_completed = False
    journal = None
    controls = {'seconds': args.seconds, 'minimum_available_disk_mib': args.minimum_available_disk_mib,
                'maximum_rss_mib': args.maximum_rss_mib, 'maximum_pair_calls': args.maximum_pair_calls,
                'maximum_subdivision_depth': args.maximum_subdivision_depth}
    report = {'schema': 'razr-complete-seating-native-diagnostic-v2',
              'domain': domain.domain_record(), 'native_checks_executed': False,
              'expected_head': args.expected_head, 'adapter_source_sha256_before': own_before,
              'complete_participant_names': names, 'participant_count': len(names),
              'expected_pair_count': math.comb(len(names), 2), 'pairs': rows,
              'execution_limits': controls, 'construction_completed': False,
              'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
    try:
        budget.check()
        before = nominal.execution_identity(args.expected_head)
        report['identity_before'] = before
        helper = ROOT / 'tools/validate_product_nominal_report.py'
        require(Path(postguard.__file__).resolve() == helper.resolve()
                and before['head_bound_source_sha256'].get('tools/validate_product_nominal_report.py') == digest(helper),
                'executed raw native postguard differs from its HEAD-bound source')
        report['raw_native_postguard_sha256'] = digest(helper)
        journal = checkpoint.PairJournal(args.output.parent / 'pairs.jsonl', checkpoint.context_record(
            args.expected_head, report['domain'], names, own_before, before, controls))
        budget.check()
        reference = {'L': [float(domain.REFERENCE_JOINT)] * 3,
                     'R': [float(domain.REFERENCE_JOINT)] * 3}
        base, metadata = nominal.full_scene(79.75, 0., 3., 3., flanks=(0., 0.),
                telescope_offsets=reference, key_offsets=(0., 0.), crosshead_offsets=(0., 0.),
                open_hold=False, open_support=False)
        enclosure.ep5.validate_factory_input_coverage(metadata['scene'], before['executed_source_sha256'])
        report['native_scene_metadata'] = metadata
        slots = p.native_inputs()[5]
        report['native_slot_halfwidth_mm'] = {side: slots[side]['halfwidth'] for side in 'LR'}
        laws = domain.rigid_laws(base, {side: slots[side]['halfwidth'] for side in 'LR'}, names)
        report['rigid_Z_laws'] = {name: law.record() for name, law in sorted(laws.items())}
        for body in base.values():
            p.whole_material(body)
        bounds = {name: p.bounds(body) for name, body in base.items()}
        report['construction_probes'] = verify_factory_rigid_laws(base, laws, nominal, p, before, budget)
        construction_completed = True
        report['construction_completed'] = True
        report['native_checks_executed'] = True
        journal.record_construction(report)
        cage_cache = CageCache()
        for index, row in enumerate(rows):
            budget.check()
            a, b = row['a'], row['b']
            flexible = {a, b} & domain.FLEXIBLE
            if not flexible:
                zlow, zhigh = laws[a].relative_to(laws[b]).projection()
                budget.check(operator=True)
                result = nominal.continuous_pair(base[a], base[b], [[0., 0., 1.]],
                            a_bounds=bounds[a], b_bounds=bounds[b], domain=((float(zlow), float(zhigh)),))
                result['exact_relative_Z_interval_mm'] = [str(zlow), str(zhigh)]
                result['pair_class'] = 'rigid_rigid_shared_descent_polytope'
            elif len(flexible) == 2:
                result = {'disposition': 'clear', 'pair_class': 'complete_FPC_OLED_material',
                          **enclosure.flex_flex_certificate()}
            else:
                flex = next(iter(flexible)); rigid = b if a == flex else a
                result = flexible_rigid_interval(flex, base[rigid], laws[rigid], F(0), domain.SEATING,
                         args.maximum_subdivision_depth, nominal, p, cage_cache, budget)
                result['pair_class'] = 'deforming_flexible_complete_rigid_material'
            rows[index] = {'a': a, 'b': b, **result}
            # Write only this completed pair. No accumulated report is
            # repeatedly serialized; the complete final JSON remains separate.
            journal.record_pair(index, rows[index])
            if (index + 1) % 128 == 0:
                print(json.dumps({'pairs_evaluated': index + 1, 'total_pairs': len(rows), **budget.record()}), flush=True)
    except BudgetExceeded as exc:
        report['resource_stop'] = str(exc)
        if exc.partial is not None:
            report['interrupted_pair_partial_evidence'] = exc.partial
            if 'index' in locals():
                rows[index] = {'a': rows[index]['a'], 'b': rows[index]['b'], **exc.partial}
        for row in rows:
            if row['disposition'] == 'not_evaluated':
                row['disposition'] = 'unresolved_budget'
        if journal is not None and not journal.broken:
            try:
                interrupted = rows[index] if exc.partial is not None and 'index' in locals() else None
                journal.record_interruption(str(exc), interrupted)
            except Exception as checkpoint_error:
                report['checkpoint_write_failure'] = type(checkpoint_error).__name__ + ': ' + str(checkpoint_error)
    except Exception as exc:
        report['execution_failure'] = type(exc).__name__ + ': ' + str(exc)
        if journal is not None and not journal.broken:
            try:
                journal.record_interruption(report['execution_failure'])
            except Exception as checkpoint_error:
                report['checkpoint_write_failure'] = type(checkpoint_error).__name__ + ': ' + str(checkpoint_error)
    finally:
        if before is not None:
            try:
                after = nominal.execution_identity(before['repository_head'])
                report['identity_after'] = after
            except Exception as exc:
                report['post_execution_identity_failure'] = type(exc).__name__ + ': ' + str(exc)
        try:
            own_after = adapter_identity()
        except Exception as exc:
            own_after = None
            report['post_execution_identity_failure'] = type(exc).__name__ + ': ' + str(exc)
        report['adapter_source_sha256_after'] = own_after
        report.update(check_complete_result(names, rows, before, after, own_before, own_after,
                      construction_completed, any(key in report for key in
                          ('execution_failure', 'resource_stop', 'checkpoint_write_failure',
                           'post_execution_identity_failure')), laws))
        report['pair_count'] = len(rows)
        report['counts'] = dict(Counter(row['disposition'] for row in rows))
        report['resources'] = budget.record()
        if journal is not None and not journal.broken:
            try:
                journal.record_postflight(report)
            except Exception as checkpoint_error:
                report['checkpoint_write_failure'] = type(checkpoint_error).__name__ + ': ' + str(checkpoint_error)
        if journal is None or journal.broken or 'checkpoint_write_failure' in report:
            report['checkpoint_unavailable_or_failed'] = True
            report['complete_native_diagnostic_executed'] = False
            report['whole_declared_seating_external_pair_domain_clear'] = False
    return report, journal


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='explicitly execute CAD after resource coordination')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head', default=DEFAULT_HEAD)
    parser.add_argument('--seconds', type=float, default=1800.)
    parser.add_argument('--minimum-available-disk-mib', type=int, default=300)
    parser.add_argument('--maximum-rss-mib', type=int, default=1536)
    parser.add_argument('--maximum-pair-calls', type=int, default=20000)
    parser.add_argument('--maximum-subdivision-depth', type=int, default=3)
    args = parser.parse_args(argv)
    if args.native:
        # The supervising parent must validate this owned PID and release it
        # through the dedicated nonce pipe before any native CAD is imported.
        owned_process.announce_worker_from_environment(Path(__file__))
    args.output = args.output.resolve()
    if args.output.exists() or args.output.is_relative_to(ROOT.resolve()):
        raise ValueError('a new evidence output outside the repository is required')
    if not args.output.parent.is_dir():
        raise ValueError('output parent must already exist')
    if (not math.isfinite(args.seconds) or args.seconds <= 0
            or min(args.minimum_available_disk_mib, args.maximum_rss_mib, args.maximum_pair_calls) <= 0
            or not 0 <= args.maximum_subdivision_depth <= 8):
        raise ValueError('positive bounded resource controls required')
    if args.native:
        result, journal = run_native(args)
        try:
            if journal is not None and not journal.broken and 'checkpoint_write_failure' not in result:
                journal.publish_report(args.output, result)
            else:
                # An ordinary failed JSON is still useful, but cannot satisfy
                # the independent complete-report checkpoint guard.
                checkpoint.atomic_bytes(args.output, json.dumps(result, indent=2, allow_nan=False).encode() + b'\n')
        finally:
            if journal is not None:
                journal.close()
    else:
        result = preparation_report(args.expected_head)
        checkpoint.atomic_bytes(args.output, json.dumps(result, indent=2, allow_nan=False).encode() + b'\n')
    print(json.dumps({key: result[key] for key in ('schema', 'native_checks_executed', 'counts',
                      'whole_declared_seating_domain_clear', 'execution_failure', 'resource_stop') if key in result}))
    return 0 if not args.native or result.get('complete_native_diagnostic_executed') else 2


if __name__ == '__main__':
    raise SystemExit(main())
