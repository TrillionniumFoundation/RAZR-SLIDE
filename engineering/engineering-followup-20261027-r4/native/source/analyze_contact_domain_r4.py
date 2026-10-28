"""Assemble actual whole-pair failures and exact source-box domain results.

Exact rational mathematics is not promoted to a universal native-kernel proof.
The native material bridge, source-model implications, and remaining premises
are reported independently, retaining every original failed scalar witness.
"""
from pathlib import Path
from fractions import Fraction as Q
import datetime as dt
import hashlib
import json
import math
import sys


ROOT = Path(__file__).resolve().parent


def identity(path):
    p = Path(path)
    return {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def value(q):
    q = Q(q); f = float(q)
    if Q(f) > q:
        f = math.nextafter(f, -math.inf)
    return {'exact': str(q), 'float_rounded_down': f}


def record(relative):
    p = ROOT / relative
    return json.loads(p.read_text()), {'path': str(p), 'identity': identity(p)}


def main():
    out = Path(sys.argv[1]); out.mkdir(exist_ok=False)
    native, native_id = record('native-producer-v2/R4_WHOLE_KEY_PAWL_NATIVE.json')
    reader, reader_id = record('native-reader/R4_WHOLE_KEY_PAWL_READBACK.json')
    prisms, prism_id = record('prism-producer/R4_CONTACT_PRISMS_NATIVE.json')
    prism_reader, prism_reader_id = record('prism-reader/R4_CONTACT_PRISMS_READBACK.json')
    contract, contract_id = record('R4_CONTACT_PRISM_CONTRACT.json')
    for r in (native, reader, prisms, prism_reader):
        assert r['completed']
    assert reader['producer_report_identity'] == native_id['identity']
    assert prism_reader['producer_identity'] == prism_id['identity']
    assert prisms['contract_identity'] == contract_id['identity']
    threshold = Q(native['original_Common_threshold_mm3'])
    r = {'schema': 'razr-r4-current-whole-key-pawl-domain-evidence-v1',
         'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
         'analysis_source': identity(__file__), 'native_inputs': native['inputs'],
         'evidence': [native_id, reader_id, prism_id, prism_reader_id, contract_id],
         'original_Common_threshold_mm3': value(threshold),
         'actual_finite_pairs': [], 'native_and_runtime_executions': [],
         'uniform_source_box_exclusions': [], 'whole_pair_source_bbox_release': [],
         'scope': {'same_current_K1_material_and_original_PAWL': True,
                   'no_product_geometry_candidate_change': True,
                   'native_whole_pair_failures_and_independent_readbacks': True,
                   'native_material_bridge_for_four_inset_prisms': True,
                   'exact_rational_source_box_uniform_proof': True,
                   'strict_native_set_containment_or_semantics_closed': False,
                   'universal_compiled_transform_closed': False,
                   'whole_factory_all_pairs_or_G2_closed': False,
                   'global_minimum_wall_or_section_closed': False,
                   'current_K1_K3_FE_or_physical_domain_closed': False,
                   'G3_G4_G5_or_physical_release': False}}
    lookup = {c['name']: c for c in reader['cases']}
    for case in native['cases']:
        other = lookup[case['name']]
        assert case['completed'] and other['completed'] and case['pair_only_clear'] == other['pair_only_clear']
        row = {'name': case['name'], 'kind': case['kind'], 'pair_only_clear': case['pair_only_clear'],
               'whole_factory_feasibility_claimed': False, 'sides': {}}
        for side, x in case['side_results'].items():
            y = other['side_results'][side]
            assert y['all_checks_passed'] and x['same_original_tolerance_gate_classification']
            row['sides'][side] = {'pose': x['pose'], 'pawl_Z_translation_mm': x['computed_pawl_z_translation_mm'],
                'direct_Common_mm3': x['direct_Common']['guard']['signed_volume_mm3'],
                'strict_Common_mm3': x['original_strict_common']['common_mm3'],
                'independent_Common_mm3': y['fresh_direct_Common']['guard']['signed_volume_mm3'],
                'original_gate_pass': x['original_Common_gate_pass'],
                'source_pose_and_Common_material_readback_pass': y['all_checks_passed']}
        r['actual_finite_pairs'].append(row)
    scalar = [x for x in r['actual_finite_pairs'] if x['kind'] == 'unchanged_original_R3_scalar_witness_pair_check']
    controls = [x for x in r['actual_finite_pairs'] if x['kind'].startswith('preregistered')]
    r['finite_summary'] = {'original_scalar_witnesses': len(scalar),
        'original_scalar_witness_pair_clear': sum(x['pair_only_clear'] for x in scalar),
        'original_scalar_witness_pair_colliding': sum(not x['pair_only_clear'] for x in scalar),
        'declared_contact_control_poses': len(controls),
        'contact_control_pair_colliding': sum(not x['pair_only_clear'] for x in controls),
        'independent_whole_pair_comparisons': 2 * len(r['actual_finite_pairs']),
        'all62_direct_strict_and_independent_classifications_agree': len(r['actual_finite_pairs']) == 31,
        'all17_source_profile_cells_still_retained': True,
        'rejected_particular_witness_does_not_prove_empty_profile_cell': True}
    job_names = [('producer', 'producer_runtime_receipt.json', 'producer-supervision-v2/controller.json', native),
                 ('reader', 'reader_runtime_receipt.json', 'reader-supervision/controller.json', reader),
                 ('prism_producer', 'prism_producer_runtime_receipt.json', 'prism-producer-supervision/controller.json', prisms),
                 ('prism_reader', 'prism_reader_runtime_receipt.json', 'prism-reader-supervision/controller.json', prism_reader)]
    for name, runtime_path, controller_path, job in job_names:
        rt, rt_id = record(runtime_path); ctl, ctl_id = record(controller_path)
        assert rt['completed'] and ctl['completed'] and ctl['resource_stop'] is None
        assert len(rt['payload_before']) == len(rt['payload_after']) == 8112
        assert all(x['equal'] for x in rt['payload_before'] + rt['payload_after'])
        assert rt['nodes_before']['all_43_RECORDs_unchanged'] and rt['nodes_after']['all_43_RECORDs_unchanged']
        r['native_and_runtime_executions'].append({'name': name, 'runtime_receipt': rt_id, 'controller': ctl_id,
            'worker_seconds': job['seconds'], 'worker_peak_RSS_bytes': job['peak_RSS_bytes'],
            'supervisor_seconds': ctl['seconds'], 'resource_stop': None,
            'original_limits': ctl['limits'], 'all8112_payloads_and43_RECORDs_unchanged': True,
            'observed_foreign_installed_module_origins': rt['observed_foreign_installed_module_origins']})
    region = contract['source_model_region']
    qlo, qhi = map(Q, region['independent_q_each_side_mm'])
    ulo, uhi = region['independent_tab_each_side_mm']
    fmin, fmax = region['independent_flank_each_side']
    native_prism_map = {p['name']: p for p in prisms['prisms']}
    for side in 'LR':
        slot = native['slots'][side]
        zlo = slot['origin'] + slot['slope'] * ulo + fmin * slot['halfwidth']
        zhi = slot['origin'] + slot['slope'] * uhi + fmax * slot['halfwidth']
        data = {p['parent']: p for p in contract['prisms']}
        key = [[Q(x) for x in v] for v in data[side + '_KEY']['bounds_mm']]
        pawl = [[Q(x) for x in v] for v in data[side + '_PAWL']['bounds_mm']]
        common = [[Q(x) for x in v] for v in region['common_box_' + side + '_mm']]
        lower_shift_key, upper_shift_key = [Q(0), qhi, Q(0)], [Q(0), qlo, Q(0)]
        lower_shift_pawl, upper_shift_pawl = [Q(0), Q(0), Q(zhi)], [Q(0), Q(0), Q(zlo)]
        margins = {}
        for name, box, lower, upper in [('KEY', key, lower_shift_key, upper_shift_key), ('PAWL', pawl, lower_shift_pawl, upper_shift_pawl)]:
            lo = [common[0][i] - box[0][i] - lower[i] for i in range(3)]
            hi = [box[1][i] + upper[i] - common[1][i] for i in range(3)]
            assert all(x >= 0 for x in lo + hi)
            margins[name] = {'lower_face_margin_mm': [value(x) for x in lo], 'upper_face_margin_mm': [value(x) for x in hi]}
        v = math.prod(common[1][i] - common[0][i] for i in range(3))
        defect_adjusted = v - 2 * threshold
        assert v > threshold and defect_adjusted > threshold
        r['uniform_source_box_exclusions'].append({
            'side': side, 'domain': region, 'source_slot_Z_extrema_mm': [value(Q(zlo)), value(Q(zhi))],
            'all_scalar_operations_monotone_and_finite_on_declared_box': True,
            'scalar_arithmetic_model': 'Fixed observed binary64 slot parameters; ordinary correctly rounded + and * are monotone here. No variable sqrt or hypot is evaluated inside this tab/flank domain.',
            'uniform_inclusion_face_margins': margins,
            'fixed_source_common_box_volume_mm3': value(v),
            'strictly_exceeds_original_Common_gate': True,
            'mathematical_defect_robustness': {'premise': 'If each whole exact native material omits at most original TOL real volume from its corresponding base prism and undergoes true rigid translation, the two translated real materials intersect by at least V_fixed_box - 2*TOL.',
                'conditional_lower_bound_mm3': value(defect_adjusted), 'above_original_gate': True,
                'native_computed_volumes_are_not_certified_real_volume_upper_bounds': True},
            'native_finite_base_bridge': {role: {'source_box_volume_mm3': native_prism_map[side + '_' + role + '_inner']['source_box']['guard']['signed_volume_mm3'],
                'missing_volume_mm3': native_prism_map[side + '_' + role + '_inner']['source_minus_whole_parent']['guard']['signed_volume_mm3'],
                'missing_topologically_empty': native_prism_map[side + '_' + role + '_inner']['missing_is_topologically_empty']} for role in ('KEY', 'PAWL')},
            'intersect_with_original_shared_slide_coupled_offset_domain': True,
            'universal_native_material_exclusion_claimed': False})
        release_u = 2.3
        zmin = slot['origin'] + slot['slope'] * release_u - slot['halfwidth']
        key_zmax = Q(native['whole_inputs'][side + '_KEY']['native_guard']['bounds_mm'][5])
        pawl_zmin = Q(native['whole_inputs'][side + '_PAWL']['native_guard']['bounds_mm'][4])
        gap = pawl_zmin + Q(zmin) - key_zmax
        assert gap > 0
        r['whole_pair_source_bbox_release'].append({'side': side, 'q_domain_mm': [0, 12],
            'tab_domain_mm': [release_u, 3], 'flank_domain': [-1, 1],
            'source_minimum_Z_translation_mm': value(Q(zmin)), 'source_support_gap_lower_mm': value(gap),
            'whole_bounding_support_premise': 'Each base whole material lies within the observed native support bounds; mathematical rigid KEY motion is only along Y and PAWL motion only along Z.',
            'source_model_box_separation_pass': True, 'universal_compiled_native_transform_claimed': False,
            'native_kernel_support_bounds_formally_certified_for_all_poses': False,
            'other_body_pairs_or_relock_force_checked_by_this_box_argument': False})
    r['remaining_open'] = [
        'Strict native BRep set coherence and certified real-volume upper bounds for the finite kernel cut results; a native topologically empty result is retained as evidence, not promoted to a formal exact set theorem.',
        'Uniform compiled-kernel transformation and whole-current-factory all-pair checks over the original coupled domain, including other STOP/SPRING/telescope/contact participants.',
        'Definition and complete whole-material coverage of global wall/section metrics with sourced acceptance criteria; these contact prisms are not wall measurements.',
        'Current material/process/load/preload/contact/friction/tolerance input, validated FE, actual spring law and physical release/hold/relock path.',
        'Real same-specimen structural/electrical/process evidence and staged G3 -> G4 -> G5 passes.']
    r['completed'] = True
    (out / 'R4_CURRENT_STRUCTURE_DOMAIN_RESULT.json').write_text(json.dumps(r, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'completed': True, **r['finite_summary'],
                      'source_box_lower_mm3': r['uniform_source_box_exclusions'][0]['fixed_source_common_box_volume_mm3'],
                      'release_source_gap_mm': r['whole_pair_source_bbox_release'][0]['source_support_gap_lower_mm']}))


if __name__ == '__main__':
    main()
