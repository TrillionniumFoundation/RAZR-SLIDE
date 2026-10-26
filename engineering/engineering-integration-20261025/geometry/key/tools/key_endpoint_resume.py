"""Independently validate complete finite KEY trials; never run CAD.

The API receives a fresh identity from the repository's canonical postguard.
The CLI obtains that identity itself. Partial checkpoints, old stdout-only
attempts, and finite clear trials cannot establish a continuous motion domain.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys

TOL = 1e-7
PROFILE_INPUT = 'engineering/thin-mechanism-20261015/native-verification.json.gz'
STUDY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    'integration/probe_key_endpoint_extension.py', 'run_key_endpoint_trials.py',
    'tests/test_key_endpoint_extension.py', 'tools/key_endpoint_resume.py',
    'tests/test_key_endpoint_resume.py',
)
LABELS = tuple(pose+'_OUTSIDE_'+label for pose in ('STOW', 'OPEN')
               for label in ('0p001mm', 'HALF_BAND', 'FULL_BAND'))
ROLES = ('KEY', 'CROSSHEAD', 'CROSSHEAD_TUBE_BOTTOM_CAP', 'KEY_FOLLOWER_LOWER_FLANGE',
         'TELESCOPE_1', 'TELESCOPE_1_BOTTOM_CAP', 'TELESCOPE_2', 'TELESCOPE_2_BOTTOM_CAP',
         'TELESCOPE_3', 'TELESCOPE_3_CORE_BOTTOM_SHOULDER',
         'TELESCOPE_3_CAM_LOWER_FLANGE', 'TELESCOPE_3_CAM_UPPER_FLANGE')
MOVING = sorted(side+'_'+role for side in 'LR' for role in ROLES)
FALSE_FLAGS = ('execution_checks_passed', 'canonical_execution_claimed',
               'continuous_backlash_domain_proved', 'global_KEY_hard_stop_proved',
               'complete_product_motion_proved', 'physical_qualification', 'candidate_go',
               'fixture_fabrication_go', 'manufacturing_go', 'formal_directed_rounding_certificate',
               'whole_current_factory_acceptance_claimed', 'all_trial_states_accepted_by_existing_factory')
TRUE_FLAGS = ('execution_completed', 'diagnostic_execution_checks_passed', 'source_bytes_unchanged',
              'scratch_study_source', 'geometry_generator_imported', 'same_CAD_kernel',
              'positive_Common_means_penetrating_trial_not_usable_state',
              'all_positive_pair_numeric_records_retained_even_when_STEP_export_limit_reached')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(2**20):
            digest.update(block)
    return digest.hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: '+key)
        result[key] = value
    return result


def read_json(path):
    def reject_constant(value):
        raise ValueError('nonfinite JSON constant: '+value)
    return json.loads(Path(path).read_text(), object_pairs_hook=_object, parse_constant=reject_constant)


def study_sources(root):
    root = Path(root).resolve()
    result = {}
    for name in SOURCE_FILES:
        path = root/name
        require(path.is_file() and not path.is_symlink() and path.resolve() == path,
                'missing or linked study source: '+name)
        result[name] = sha(path)
    return result


def expected_inputs(label):
    require(label in LABELS, 'unknown finite trial label')
    pose = label.split('_')[0]
    cam = (.425-.4)*math.hypot(1., 12./79.75)
    half = cam+(.425-.4)*math.sqrt(2.)
    factor = {'0p001mm': .001/half, 'HALF_BAND': .5, 'FULL_BAND': 1.}[label.split('_OUTSIDE_')[1]]
    sign = -1. if pose == 'STOW' else 1.
    dq, dx = sign*half*factor, sign*cam*factor
    q = 0. if pose == 'STOW' else 12.
    return {'label': label, 'KEY_offset_mm': dq, 'crosshead_offset_mm': dx,
            'nominal_q_mm': q, 'pose': pose, 'q_mm': q+dq}


def expected_scope(pose):
    opened = pose == 'OPEN'
    joint = .1 if opened else .1+8.2/3
    return {'pose': pose, 'slide_mm': 79.75 if opened else 0., 'descent_mm': 8.2 if opened else 0.,
            'tabs_mm': [3., 3.], 'slot_flanks': [0., 0.], 'telescope_offsets_each_mm': [joint]*3,
            'independent_left_right_offsets_explored': False}


def _numeric_equal(actual, expected):
    return finite(actual) and math.isclose(actual, expected, rel_tol=0., abs_tol=1e-12)


def _vector(value, count, label):
    require(isinstance(value, (list, tuple)) and len(value) == count
            and all(finite(v) for v in value), 'finite '+label+' required')
    return value


def _interval(value, label):
    value = _vector(value, 2, label)
    require(value[0] < value[1], 'nonempty ordered '+label+' required')
    return value


def _same_vector(actual, expected, label):
    actual = _vector(actual, len(expected), label)
    require(all(_numeric_equal(a, b) for a, b in zip(actual, expected)),
            'derived '+label+' differs from raw geometry')


def _original_profiles(current):
    """Read only the original HEAD-bound JSON payload, without importing CAD."""
    import validate_product_nominal_report as postguard
    path = postguard.ROOT/PROFILE_INPUT
    digest = sha(path)
    require(current.get('head_bound_source_sha256', {}).get(PROFILE_INPUT) == digest,
            'original four-profile payload is not bound to the current HEAD identity')
    data = json.loads(gzip.decompress(path.read_bytes()), object_pairs_hook=_object)
    require(sha(path) == digest, 'original profile payload changed while reading')
    profiles = {}
    for side in 'LR':
        contacts = data['sides'][side]['contacts']
        require(isinstance(contacts, list) and len(contacts) == 2,
                'exact original four contact profiles required')
        for index, contact in enumerate(contacts):
            profile = contact['profile']
            fields = ('pin_radius', 'floor_height', 'floor_corner_q', 'ramp_slope',
                      'pin_q', 'lower_stop_height', 'q_max')
            require(isinstance(profile, dict) and all(finite(profile.get(key)) for key in fields),
                    'finite original profile parameters required')
            r, m = profile['pin_radius'], profile['ramp_slope']
            require(r > 0 and m > 0 and profile['q_max'] > 0,
                    'positive original radius, slope and travel required')
            first = profile['pin_q']-profile['floor_corner_q']
            intercept = profile['floor_height']-m*profile['floor_corner_q']+r*math.hypot(1., m)
            breaks = [first, first+r*m/math.hypot(1., m),
                      profile['pin_q']+(intercept-profile['lower_stop_height'])/m]
            require(0 < breaks[0] < breaks[1] < breaks[2] < profile['q_max'],
                    'original four contact branches or positive home plateau missing')
            _same_vector(profile['breakpoints_q_mm'], breaks, 'original profile breakpoints')
            profiles[(side, index)] = profile
    return profiles, {'path': str(path), 'sha256': digest}


def _floor_geometry(floor, side, profile):
    """Derive the complete finite rectangular face from recorded native data."""
    require(isinstance(floor, dict) and type(floor.get('face')) is int and floor['face'] >= 0,
            'native floor face identity missing')
    e = _interval(floor.get('e_extent_mm'), 'floor e extent')
    q = _interval(floor.get('q_extent_mm'), 'floor q extent')
    vertices = floor.get('vertices_eqr_mm')
    require(isinstance(vertices, list) and len(vertices) >= 3, 'native floor vertices missing')
    for vertex in vertices:
        _vector(vertex, 3, 'floor vertex')
        require(abs(vertex[2]-profile['floor_height']) <= TOL,
                'native floor vertex is off the original contact plane')
    _same_vector(e, [min(v[0] for v in vertices), max(v[0] for v in vertices)], 'floor e extent')
    _same_vector(q, [min(v[1] for v in vertices), max(v[1] for v in vertices)], 'floor q extent')
    normal = _vector(floor.get('normal_xyz'), 3, 'floor normal')
    sign = -1. if side == 'L' else 1.
    require(abs(sign*normal[0]-1.) <= 1e-9 and abs(math.hypot(*normal)-1.) <= 1e-9,
            'native floor normal differs from original placement')
    center = _vector(floor.get('center_eqr_mm'), 3, 'floor center')
    require(-.61 < center[0] < -.19 and abs(center[2]-profile['floor_height']) <= TOL,
            'native floor center differs from original selected contact face')
    require(type(floor.get('wire_count')) is int and floor['wire_count'] >= 1,
            'native floor wire count missing')
    edges = floor.get('edge_geometry_types')
    require(isinstance(edges, list) and edges and all(type(value) is str and value for value in edges),
            'native floor edge types missing')
    require(finite(floor.get('area_mm2')) and floor['area_mm2'] > 0,
            'positive finite native floor area required')
    corners = {(round(v[0], 9), round(v[1], 9)) for v in vertices}
    rectangular = (floor['wire_count'] == 1 and len(vertices) == 4 and len(edges) == 4
                   and all(edge == 'LINE' for edge in edges)
                   and corners == set(itertools.product([round(v, 9) for v in e], [round(v, 9) for v in q]))
                   and abs(floor['area_mm2']-(e[1]-e[0])*(q[1]-q[0])) <= TOL)
    require(floor.get('complete_trimmed_face_is_rectangle') is rectangular,
            'native floor rectangle flag differs from its complete finite face')
    if rectangular:
        require(abs(center[0]-(e[0]+e[1])/2) <= TOL
                and abs(center[1]-(q[0]+q[1])/2) <= TOL,
                'native rectangular face centroid differs from its complete vertices')
    return rectangular


def _pin_geometry(pin, side, profile):
    require(isinstance(pin, dict) and type(pin.get('face')) is int and pin['face'] >= 0,
            'native pin face identity missing')
    e = _interval(pin.get('e_extent_mm'), 'pin e extent')
    q, r, radius = pin.get('pin_q_mm'), pin.get('pin_r_mm'), pin.get('radius_mm')
    require(finite(q) and finite(r) and finite(radius) and radius > 0
            and abs(radius-profile['pin_radius']) <= TOL, 'native pin/profile radius differs')
    axis = _vector(pin.get('axis_direction_xyz'), 3, 'pin cylinder axis')
    require(abs(abs(axis[2])-1.) <= 1e-9 and abs(math.hypot(*axis)-1.) <= 1e-9,
            'native pin cylinder axis differs from original placement')
    location = _vector(pin.get('cylinder_location_xyz'), 3, 'pin cylinder location')
    sign = -1. if side == 'L' else 1.
    require(_numeric_equal(q, location[1]-14.8) and _numeric_equal(r, sign*location[0]-23.85),
            'native pin q/r differs from its actual cylinder location')
    vertices = pin.get('vertices_eqr_mm')
    require(isinstance(vertices, list) and len(vertices) >= 2, 'native pin vertices missing')
    for vertex in vertices:
        _vector(vertex, 3, 'pin vertex')
        require(abs(math.hypot(vertex[1]-q, vertex[2]-r)-radius) <= TOL,
                'native pin vertex is off the recorded cylinder')
    _same_vector(e, [min(v[0] for v in vertices), max(v[0] for v in vertices)], 'pin e extent')
    outside = pin.get('full_pin_outside_STOP_mm3')
    require(finite(outside) and outside >= 0, 'finite nonnegative full pin outside STOP required')


def _plateau_geometry(plateau, profiles, half):
    require(isinstance(plateau, dict) and plateau.get('schema') == 'razr-native-finite-plateau-extension-v1',
            'native finite plateau diagnostic schema missing')
    rows = plateau.get('rows')
    require(isinstance(rows, list) and len(rows) == 4
            and all(isinstance(r, dict) and type(r.get('STOP')) is int for r in rows)
            and {(r.get('side'), r.get('STOP')) for r in rows} == set(itertools.product('LR', (0, 1))),
            'complete four native plateau diagnostics missing')
    require(plateau.get('restoring_force_and_physical_contact_qualified') is False
            and plateau.get('formal_directed_rounding_certificate') is False,
            'native plateau diagnostic overclaims qualification')
    supported_rows = []
    for row in rows:
        require(type(row.get('native_plateau_extension_supported')) is bool,
                'native plateau disposition missing')
        _same_vector(row.get('negative_KEY_interval_mm'), [-half, 0.], 'negative KEY interval')
        floors, pins = row.get('floor_candidates'), row.get('pin_candidates')
        require(isinstance(floors, list) and isinstance(pins, list), 'native plateau raw candidates missing')
        profile = profiles[(row['side'], row['STOP'])]
        rectangles = [_floor_geometry(floor, row['side'], profile) for floor in floors]
        for pin in pins:
            _pin_geometry(pin, row['side'], profile)
        require(len({floor['face'] for floor in floors}) == len(floors)
                and len({pin['face'] for pin in pins}) == len(pins), 'duplicate native floor or pin face')
        supported = False
        if len(floors) == len(pins) == 1:
            floor, pin = floors[0], pins[0]
            interval = [pin['pin_q_mm'], pin['pin_q_mm']+half]
            margins = [interval[0]-floor['q_extent_mm'][0], floor['q_extent_mm'][1]-interval[1]]
            overlap = min(floor['e_extent_mm'][1], pin['e_extent_mm'][1])-max(floor['e_extent_mm'][0], pin['e_extent_mm'][0])
            _same_vector(row.get('contact_q_interval_mm'), interval, 'finite contact q interval')
            _same_vector(row.get('finite_floor_q_edge_margins_mm'), margins, 'finite floor q edge margins')
            require(_numeric_equal(row.get('contact_e_overlap_mm'), overlap),
                    'derived contact e overlap differs from actual finite extents')
            supported = (rectangles[0] and min(margins) >= 0. and overlap > 0.
                         and pin['full_pin_outside_STOP_mm3'] <= TOL
                         and abs(pin['pin_r_mm']-profile['floor_height']-profile['pin_radius']) <= TOL
                         and abs(pin['pin_q_mm']-profile['pin_q']) <= TOL)
        else:
            require(not {'contact_q_interval_mm', 'finite_floor_q_edge_margins_mm', 'contact_e_overlap_mm'} & set(row),
                    'ambiguous native floor/pin candidates cannot claim derived unique contact intervals')
        require(row['native_plateau_extension_supported'] is supported,
                'native plateau support flag differs from recomputed finite contact geometry')
        supported_rows.append(supported)
    require(plateau.get('all_four_current_native_floors_support_the_declared_negative_q_contact') is all(supported_rows),
            'native plateau summary differs from four recomputed raw rows')


def _raw_errors(value, path='report'):
    """Declared profile rejection text is the only intentional error record."""
    if isinstance(value, dict):
        for key, child in value.items():
            if path == 'report' and key == 'existing_profile_rejections':
                continue
            if key in ('error', 'execution_failure', 'STEP_export_failure', 'failure_stage'):
                raise ValueError('error record in completed evidence: '+path+'.'+key)
            if key in ('errors', 'evaluation_failed', 'evaluation_failures', 'budget_exceeded',
                       'resource_stop_reason', 'stop_event', 'interrupted', 'timed_out'):
                require(not child, 'failed or interrupted nested evidence: '+path+'.'+key)
            _raw_errors(child, path+'.'+key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _raw_errors(child, path+'['+str(index)+']')
    elif type(value) in (int, float):
        require(finite(value), 'nonfinite number in raw evidence: '+path)


def _baseline_postcheck(report, pose, head, current):
    import validate_product_nominal_report as postguard
    return postguard.validate_report(report, pose, head, current)


def _validate_pose(record, names, moving, scope, baseline, profiles):
    require(isinstance(record, dict), 'full pose evidence required')
    require(record.get('pose') == scope['pose'] and record.get('participants') == len(names)
            and record.get('complete_participant_names') == names
            and record.get('moving_participants') == moving, 'pose material inventory differs')
    cross = record.get('in_domain_factory_crosscheck', {})
    differences = cross.get('bidirectional_material_difference_mm3')
    require(cross.get('all_participants_compared') == len(names)
            and isinstance(differences, dict) and set(differences) == set(names)
            and all(finite(v) and 0 <= v <= TOL for v in differences.values()),
            'actual factory crosscheck does not cover all complete materials')
    inward, dx = cross.get('KEY_offset_mm'), cross.get('crosshead_offset_mm')
    cam = (.425-.4)*math.hypot(1., 12./79.75)
    yoke = (.425-.4)*math.sqrt(2.)
    require(finite(inward) and finite(dx) and abs(dx) <= cam+1e-12 and abs(dx-inward) <= yoke+1e-12
            and _numeric_equal(dx, inward*cam/(cam+yoke)), 'in-domain construction offsets differ')
    expected_inward = min(profile['pin_q']-profile['floor_corner_q'] for profile in profiles.values())/4
    require(_numeric_equal(inward, expected_inward if scope['pose'] == 'STOW' else -.001),
            'construction crosscheck is not on the original inward endpoint branch')
    meta = record.get('native_scene_metadata', {})
    scene = meta.get('scene', {})
    base_scene = baseline['native_scene_metadata']['scene']
    require(meta.get('combined_participants') == len(names) and meta.get('candidate_participants') == 41
            and meta.get('mechanical_participants') == len(names)-46,
            'full factory participant counts differ')
    require(scene.get('factory') == 'integration/product_split_assembly.py:split_scene'
            and scene.get('installed_mechanical_parts') == len(names)-46
            and _numeric_equal(scene.get('slide_mm'), scope['slide_mm'])
            and _numeric_equal(scene.get('descent_mm'), scope['descent_mm'])
            and _numeric_equal(scene.get('left_tab_mm'), 3.) and _numeric_equal(scene.get('right_tab_mm'), 3.)
            and scene.get('slot_flanks') == [0., 0.]
            and scene.get('KEY_offsets_mm') == scene.get('crosshead_offsets_mm') == [0., 0.],
            'native base scene does not have the declared endpoint controls')
    joints = scene.get('telescope_offsets_by_side_mm', {})
    require(set(joints) == {'L', 'R'} and all(isinstance(joints[s], list) and len(joints[s]) == 3
            and all(_numeric_equal(a, b) for a, b in zip(joints[s], scope['telescope_offsets_each_mm']))
            for s in 'LR'), 'native base telescope allocation differs')
    require(record.get('tabs_mm') == [3., 3.] and record.get('slot_flanks') == [0., 0.]
            and record.get('telescope_allocation') == joints, 'pose-record control metadata differs')
    for key in ('source_inputs', 'archive', 'archive_sha256'):
        require(scene.get(key) == base_scene.get(key), 'native payload identity differs: '+key)
    opened = scope['pose'] == 'OPEN'
    require(scene.get('OPEN_hold_screws_installed') is opened
            and scene.get('OPEN_display_support_insert_installed') is opened,
            'native OPEN accessory inventory differs')
    for key in ('physical_holding_and_force_qualified', 'OPEN_thread_retention_load_qualified',
                'loose_OPEN_accessories_have_onboard_storage', 'complete_functional_phone',
                'candidate_go', 'manufacturing_go'):
        require(scene.get(key) is False, 'native scene overclaims physical scope: '+key)
    if opened:
        require(record.get('selected_lower_stop_positions_retained') is True
                and record.get('new_lower_stop_force_or_retention_proof') is False,
                'OPEN lower-stop scope differs')
    else:
        _plateau_geometry(record.get('native_plateau_contact_extension'), profiles, cam+yoke)


def _validate_completed_trial(record, *, expected_head, expected_label, current_identity,
                              expected_study_sources, baseline_report, baseline_path, report_directory):
    """Return finite-trial accounting or raise; no incomplete state can resume."""
    require(type(expected_head) is str and re.fullmatch('[0-9a-f]{40}', expected_head), 'full expected HEAD required')
    expected = expected_inputs(expected_label)
    pose, scope = expected['pose'], expected_scope(expected['pose'])
    require(isinstance(record, dict) and record.get('schema') == 'razr-KEY-endpoint-single-trial-v2',
            'only full versioned single-trial raw reports are resumable')
    require(record.get('source_commit') == expected_head and record.get('trial_label') == expected_label
            and record.get('status') == 'complete', 'wrong identity, trial, or incomplete checkpoint')
    require(all(record.get(k) is True for k in TRUE_FLAGS) and all(record.get(k) is False for k in FALSE_FLAGS),
            'completion or scientific-scope flags differ')
    require(type(record.get('checkpoint_generation')) is int and record['checkpoint_generation'] >= 0
            and finite(record.get('seconds')) and record['seconds'] >= 0, 'checkpoint generation or duration invalid')
    _raw_errors(record)
    trial = record.get('trial_inputs')
    require(isinstance(trial, dict) and set(trial) == set(expected), 'trial inputs missing or extra')
    for key, value in expected.items():
        require(trial[key] == value if isinstance(value, str) else _numeric_equal(trial[key], value),
                'finite trial input differs: '+key)
    supplied_scope = record.get('scope')
    require(supplied_scope == scope and supplied_scope.get('independent_left_right_offsets_explored') is False
            and finite(supplied_scope.get('slide_mm')) and finite(supplied_scope.get('descent_mm'))
            and all(finite(v) for name in ('tabs_mm', 'slot_flanks', 'telescope_offsets_each_mm')
                    for v in supplied_scope[name]), 'finite trial domain differs')
    require(current_identity.get('repository_head') == expected_head
            and current_identity.get('executed_source_overlay') is False
            and current_identity.get('outside_repository_executed_files') == []
            and current_identity.get('environment', {}).get('passed') is True
            and current_identity['environment'].get('checked_package_count') == 43,
            'fresh canonical current identity and all 43 locked packages required')
    require(record.get('identity_before') == record.get('identity_after') == current_identity,
            'actual source/runtime pre/post identity differs from the current repository')
    require(isinstance(expected_study_sources, dict) and set(expected_study_sources) == set(SOURCE_FILES)
            and all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in expected_study_sources.values()),
            'complete five-file current study source map required')
    require(record.get('study_source_sha256_before') == record.get('study_source_sha256_after') == expected_study_sources,
            'actual study source closure differs')
    executed = record.get('executed_study_source', {})
    worker = STUDY_ROOT/'integration/probe_key_endpoint_extension.py'
    require(executed == {'path': str(worker), 'sha256': expected_study_sources['integration/probe_key_endpoint_extension.py']},
            'actual worker source path or bytes differ')
    baseline_path = Path(baseline_path).resolve()
    require(baseline_path.is_file() and not Path(record.get('baseline_report', {}).get('path', '')).is_symlink(),
            'original canonical baseline file required')
    baseline_sha = sha(baseline_path)
    require(record.get('baseline_report') == {'pose': pose, 'path': str(baseline_path), 'sha256': baseline_sha},
            'original baseline path or bytes differ')
    require(read_json(baseline_path) == baseline_report, 'supplied baseline object differs from the hashed bytes')
    checked = _baseline_postcheck(baseline_report, pose, expected_head, current_identity)
    require(record.get('baseline_receipt_postcheck') == checked, 'baseline canonical postcheck differs')
    names = baseline_report.get('complete_participant_names')
    require(isinstance(names, list) and len(names) == (154 if pose == 'STOW' else 161)
            and all(type(n) is str and n for n in names) and names == sorted(set(names))
            and set(MOVING) <= set(names), 'complete baseline material names required')
    require(record.get('complete_participant_names') == names and record.get('moving_participants') == MOVING,
            'trial material inventory differs from complete canonical baseline')
    all_pairs = list(itertools.combinations(names, 2))
    moving = set(MOVING)
    changed = [list(pair) for pair in all_pairs if moving.intersection(pair)]
    fixed = [list(pair) for pair in all_pairs if not moving.intersection(pair)]
    require(record.get('expected_changed_pairs') == changed and record.get('reused_unchanged_pairs') == fixed,
            'complete changed/fixed pair partition differs')
    rows = record.get('actual_native_changed_pairs')
    require(isinstance(rows, list) and len(rows) == len(changed)
            and [[row.get('a'), row.get('b')] for row in rows if isinstance(row, dict)] == changed
            and record.get('pending_changed_pairs') == []
            and type(record.get('processed_pair_count')) is int and record['processed_pair_count'] == len(rows),
            'raw pair prefix is incomplete, repeated, reordered or outside the expected field')
    methods, positive = Counter(), []
    for row in rows:
        value, gap, method = row.get('common_mm3'), row.get('axis_gap_lower_mm'), row.get('method')
        require(finite(value) and value >= 0 and finite(gap), 'nonfinite or negative actual Common/gap')
        require(method in ('positive_axis_gap', 'native_common'), 'unknown original strict Common method')
        require((gap > 0 and value == 0) if method == 'positive_axis_gap' else gap == 0,
                'actual strict Common method and raw numerical evidence disagree')
        require(row.get('rejected') is (value > TOL), 'actual Common rejection flag differs from original 1e-7')
        methods[method] += 1
        if value > TOL:
            positive.append(row)
    require(record.get('evaluation_failures') == [], 'failed native/export operation cannot resume')
    positives = record.get('positive_actual_Common')
    require(isinstance(positives, list) and len(positives) == len(positive)
            and record.get('positive_Common_STEP_export_limit_per_trial') == 8,
            'all actual positive records and original STEP cap required')
    directory = Path(report_directory).resolve()
    require(directory.is_dir(), 'actual report directory required')
    steps = []
    for index, (item, original) in enumerate(zip(positives, positive)):
        require(isinstance(item, dict) and all(item.get(k) == v for k, v in original.items()),
                'a positive numeric witness differs from its actual raw row')
        step = item.get('actual_Common_STEP')
        if index >= 8:
            require(step is None, 'STEP export count exceeds original limit')
            continue
        require(isinstance(step, dict) and set(step) == {'path', 'sha256'}
                and type(step['path']) is str and step['path'] == Path(step['path']).name
                and step['path'].endswith('.step') and type(step['sha256']) is str
                and re.fullmatch('[0-9a-f]{64}', step['sha256']), 'required positive STEP identity missing or unsafe')
        path = directory/step['path']
        require(path.is_file() and not path.is_symlink() and path.resolve().parent == directory
                and path.stat().st_size > 0 and sha(path) == step['sha256'], 'positive STEP bytes differ or escape the report')
        require(step['path'] not in steps, 'two positive witnesses reuse one STEP filename')
        steps.append(step['path'])
    require(record.get('finite_trial_material_clear') is (not positive),
            'finite clearance summary discards an actual positive Common')
    rejected = record.get('existing_profile_rejections')
    require(isinstance(rejected, list) and len(rejected) == 4
            and all(isinstance(r, dict) and type(r.get('STOP')) is int for r in rejected)
            and {(r.get('side'), r.get('STOP')) for r in rejected if isinstance(r, dict)} == set(itertools.product('LR', (0, 1)))
            and all(type(r.get('error')) is str and r['error'] for r in rejected),
            'all four original outside-profile rejections must remain explicit')
    profiles, profile_input = _original_profiles(current_identity)
    _validate_pose(record.get('pose_record'), names, MOVING, scope, baseline_report, profiles)
    require(sha(baseline_path) == baseline_sha, 'canonical baseline changed while reading')
    require(sha(profile_input['path']) == profile_input['sha256'], 'original profile input changed during validation')
    return {'schema': 'razr-KEY-completed-trial-independent-resume-check-v1',
            'source_commit': expected_head, 'trial_label': expected_label,
            'participants': len(names), 'changed_pairs': len(changed), 'unchanged_pairs': len(fixed),
            'complete_unordered_pairs': len(all_pairs), 'methods': dict(methods),
            'positive_actual_pairs': len(positive), 'verified_positive_STEP_files': len(steps),
            'finite_trial_material_clear': not positive, 'completed_trial_resumable': True,
            'baseline_sha256': baseline_sha, 'original_profile_input': profile_input,
            'continuous_backlash_domain_proved': False,
            'global_KEY_hard_stop_proved': False, 'complete_product_motion_proved': False,
            'physical_qualification': False, 'CAD_executed_by_validator': False}


def validate_completed_trial(record, *, expected_head, expected_label, current_identity,
                             expected_study_sources, baseline_report, baseline_path, report_directory):
    """API boundary: malformed or unavailable raw evidence always raises ValueError."""
    try:
        return _validate_completed_trial(record, expected_head=expected_head, expected_label=expected_label,
            current_identity=current_identity, expected_study_sources=expected_study_sources,
            baseline_report=baseline_report, baseline_path=baseline_path, report_directory=report_directory)
    except (KeyError, TypeError, AttributeError, OSError, OverflowError) as error:
        raise ValueError('invalid or unavailable completed-trial evidence: '+str(error)) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--study-root', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--expected-label', choices=LABELS, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    require(args.study_root.resolve() == STUDY_ROOT, 'validator must execute from the bound current study root')
    root = args.root.resolve()
    sys.path.insert(0, str(root/'tools'))
    import validate_product_nominal_report as postguard
    require(Path(postguard.__file__).resolve() == root/'tools/validate_product_nominal_report.py',
            'canonical repository postguard must be the actual imported module')
    identity = postguard.current_identity(root, args.expected_head)
    sources = study_sources(STUDY_ROOT)
    digest = sha(args.report)
    result = validate_completed_trial(read_json(args.report), expected_head=args.expected_head,
        expected_label=args.expected_label, current_identity=identity, expected_study_sources=sources,
        baseline_report=read_json(args.baseline), baseline_path=args.baseline,
        report_directory=args.report.resolve().parent)
    require(sha(args.report) == digest and study_sources(STUDY_ROOT) == sources
            and postguard.current_identity(root, args.expected_head) == identity,
            'report, study source or repository/runtime changed during independent resume validation')
    result.update(raw_report=str(args.report.resolve()), raw_report_sha256=digest,
                  study_source_sha256=sources, source_and_runtime_postflight_unchanged=True)
    encoded = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        require(args.output.resolve() not in (args.report.resolve(), args.baseline.resolve()),
                'independent receipt must not overwrite an input')
        args.output.write_text(encoded)
    print(encoded, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
