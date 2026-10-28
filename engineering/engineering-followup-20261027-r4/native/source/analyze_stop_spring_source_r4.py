"""Trace the unchanged source STOP and SPRING envelope laws on positive q.

Uses the archived actual profile records and original pure scalar profile code.
Does not import CAD, assert physical restoring force, or relabel an OD envelope
as a load-bearing spring. The prior R3 scalar domain remains unchanged.
"""
from pathlib import Path
import datetime as dt
from fractions import Fraction
import hashlib
import importlib.util
import json
import sys


ROOT = Path(__file__).resolve().parent


def identity(path):
    p = Path(path)
    return {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def scalar(value):
    v = float(value)
    return {'float': v, 'hex': v.hex(), 'exact': str(Fraction(v))}


def main():
    out = Path(sys.argv[1]); out.mkdir(exist_ok=False)
    original = ROOT / 'recovered/functional-source/integration'
    profile_source = original / 'cam_contact_profile.py'
    spec = importlib.util.spec_from_file_location('r4_original_scalar_contact_profile', profile_source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    recovered = ROOT / 'R4_STOP_SPRING_INPUT_RECOVERY.json'
    rr = json.loads(recovered.read_text())
    domain_path = ROOT / 'recovered/domain/execution/R3_SCALAR_DOMAIN_RESULT.json'
    domain = json.loads(domain_path.read_text())
    fields = ('pin_radius', 'floor_height', 'floor_corner_q', 'ramp_slope', 'pin_q', 'lower_stop_height', 'q_max')
    profiles = {s: [module.ContactProfile(**{k: p[k] for k in fields})
                    for p in rr['profiles_by_side'][s]] for s in 'LR'}
    result = {
        'schema': 'razr-r4-stop-spring-source-motion-audit-v1',
        'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'analysis_source': identity(__file__),
        'source_identities': {str(p.relative_to(ROOT)): identity(p) for p in
            (profile_source, original / 'product_assembly.py', original / 'verify_cam_coupling.py', recovered, domain_path)},
        'original_profile_record': rr['profile_record'],
        'original_stop_and_spring_inputs': rr['inputs'],
        'source_laws': {
            'independent_side_KEY_coordinate': 'q_side = (12 / 79.75) * slide_s + dq_side; 0 <= q_side <= 12',
            'STOP_translation_mm': '(sign_side * (profile_i.evaluate(q_side)[0] - profile_i.evaluate(0)[0]), 0, 0)',
            'side_sign': {'L': -1, 'R': 1},
            'SPRING_OD_envelope_radius_mm': 0.43,
            'SPRING_low_X': 'old_bbox.xmin + min(0, sign_side * delta_i)',
            'SPRING_high_X': 'old_bbox.xmax + max(0, sign_side * delta_i)',
            'SPRING_length_source_operation': 'high_X - low_X',
            'SPRING_center_YZ': '((old_ymin + old_ymax)/2, (old_zmin + old_zmax)/2)',
            'SPRING_axis': [1, 0, 0],
            'real_arithmetic_length_identity_only': 'old_X_width + abs(delta_i)',
            'binary64_length_is_not_claimed_identical_to_reassociated_formula': True,
            'nominal_source_bbox_method': 'verify_cam_coupling.scene: old[role].BoundingBox()',
            'explicit_offset_or_allocation_bbox_method': 'product_assembly.native_scene: bounds(old[role]) using AddOptimal(no mesh cache)',
            'SPRING_material_model': 'A newly constructed OD_TOL_ENVELOPE cylinder for each pose; no wire, coils, constitutive law, rate, preload or free length is supplied by this operation.'},
        'per_side_profile_cells': [], 'unchanged_R3_witness_checks': [],
        'physical_inputs_not_established_by_these_sources': [
            'Real spring PN/revision, wire/coil geometry, material/process and measured dimensional uncertainty',
            'Compression/extension force-displacement relation, free length, preload and assembly direction',
            'Actual restoring force maintaining the selected lower cam contact branch in both travel directions',
            'Friction, detent, manual hold/release/relock, dynamic impact and wear/fatigue limits',
            'Current K1/K3 load cases, restraints, wall/section definitions, acceptance thresholds and mesh convergence'],
        'scope': {'original_scalar_source_executed': True, 'native_CAD_imported': False,
                  'prior_R3_domain_changed': False, 'native_whole_motion_clearance': False,
                  'full_factory_guard_completeness': False, 'real_independent_reachability': False,
                  'spring_force_or_current_FE_pass': False, 'physical_release': False}}
    for cell in domain['per_side_cells']:
        lo, hi = cell['minimum']['float'], cell['maximum']['float']
        row = {'cell_index': cell['index'], 'q_minimum': cell['minimum'], 'q_maximum': cell['maximum'],
               'expected_two_profile_branches': cell['label'], 'profiles_by_side': {}}
        for side in 'LR':
            sign = -1 if side == 'L' else 1
            row['profiles_by_side'][side] = []
            for i, profile in enumerate(profiles[side]):
                records = []
                for q in (lo, hi):
                    h, slope, branch = profile.evaluate(q)
                    delta = h - profile.evaluate(0)[0]
                    assert branch == cell['label'][i]
                    records.append({'q': scalar(q), 'height': scalar(h), 'height_derivative': scalar(slope),
                                    'delta': scalar(delta), 'STOP_X_translation': scalar(sign * delta),
                                    'branch': branch})
                row['profiles_by_side'][side].append({'index': i, 'profile': profile.receipt(),
                                                     'cell_endpoint_source_evaluations': records})
        result['per_side_profile_cells'].append(row)
    for row in domain['SLIDE_complete_joint_profile_partition']['rows']:
        if 'witness' not in row:
            continue
        checks = []
        for side in row['witness']['sides']:
            actual = [list(p.evaluate(side['q']['float'])) for p in profiles[side['side']]]
            same = actual == side['profile_values']
            assert same
            checks.append({'side': side['side'], 'q': side['q'], 'same_original_profile_values': same})
        result['unchanged_R3_witness_checks'].append({'left_cell': row['left_cell'], 'right_cell': row['right_cell'], 'sides': checks})
    c0, c1 = (profiles['R'][i].breakpoints[2] for i in (0, 1))
    result['separate_lower_stop_engagements'] = {
        'c0': scalar(c0), 'c1': scalar(c1), 'exact_difference_mm': str(Fraction(c1) - Fraction(c0)),
        'mixed_cell_not_removed': True,
        'terminal_deltas_mm': [scalar(p.evaluate(12)[0] - p.evaluate(0)[0]) for p in profiles['R']],
        'two_terminal_binary64_deltas_not_forced_equal': True}
    result['all17_R3_scalar_witness_profile_results_retained'] = len(result['unchanged_R3_witness_checks']) == 17
    result['python'] = sys.version
    result['completed'] = result['all17_R3_scalar_witness_profile_results_retained']
    (out / 'R4_STOP_SPRING_SOURCE_MOTION.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'completed': result['completed'], 'source_cells': len(result['per_side_profile_cells']),
                      'scalar_witnesses': len(result['unchanged_R3_witness_checks']), 'native_CAD_imported': False}))


if __name__ == '__main__':
    main()
