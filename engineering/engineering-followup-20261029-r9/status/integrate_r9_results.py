"""Bind completed R9 scientific scopes and update only current entrypoint metadata.

This is a report integrator, not a new CAD, solver, electrical or physical run.
Run after the immutable independent ledgers and geometry scope are present.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


R9 = Path(__file__).resolve().parents[1]
ROOT = R9.parents[1]
REL = R9.relative_to(ROOT).as_posix()


def load(path):
    return json.loads(Path(path).read_text())


def identity(path):
    path = Path(path)
    with path.open('rb') as stream:
        return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main():
    scopes = {
        'ten_state_independent': R9 / 'independent-review/R9_GEOMETRY_TEN_STATE_INDEPENDENT_FINAL_LEDGER.json',
        'three_scope_independent': R9 / 'independent-review/R9_INDEPENDENT_SCOPE_CROSS_LEDGER.json',
        'geometry': R9 / 'geometry/R9_GEOMETRY_SCOPE.json',
        'geometry_archive_readback': R9 / 'geometry/ARCHIVE_READBACK.json',
        'geometry_source_motion': R9 / 'geometry/NATIVE_PROFILE_EIGHT_STATES.json',
        'material_domain_crossreview': R9 / 'independent-review/R9_K1_K3_MATERIAL_AND_DOMAIN_CROSSREVIEW.json',
        'envelope': R9 / 'envelope/R9_ENVELOPE_SCOPE.json',
        'envelope_independent': R9 / 'independent-review/R9_ENVELOPE_INDEPENDENT_FINAL_LEDGER.json',
        'numerics': R9 / 'numerics/R9_NUMERICAL_SCOPE.json',
        'OEM_public_source_applicability': R9 / 'real-sources/R9_OEM_SOURCE_APPLICABILITY.json',
        'external_originals': R9 / 'provenance/R9_EXTERNAL_ORIGINALS.json',
    }
    records = {key: load(path) for key, path in scopes.items()}
    g, n, e = records['ten_state_independent'], records['numerics'], records['envelope']
    assert g['completed'] and g['full_native_producer_states_completed'] == 10
    assert g['full_native_reader_states_completed'] == 10 and g['finite_state_pairs_per_role'] == 118909
    assert g['producer_plus_reader_pair_results'] == 237818 and g['saved_whole_native_body_files_rehashed'] == 3094
    assert records['three_scope_independent']['completed']
    for item in records['three_scope_independent']['bound_scope_records'].values():
        actual = identity(R9 / item['path'])
        assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
    geometry = records['geometry']
    assert geometry['all_ten_finite_state_executions_complete'] and geometry['all_ten_finite_states_clear']
    assert geometry['new_R9_state_count'] == 8 and geometry['retained_R7_state_count'] == 2
    assert geometry['actual_matrix_method_totals_by_role'] == g['method_counts_per_role']
    motion = records['geometry_source_motion']
    assert motion['all_source_native_bounds_mappings_pass'] and len(motion['states']) == 8
    assert sum(len(row['bodies']) for row in motion['states'].values()) == 64
    assert all(row['all_source_native_bounds_mappings_pass'] for row in motion['states'].values())
    archive = records['geometry_archive_readback']
    assert archive['complete_member_names_sizes_and_SHA256_match'] and archive['all_source_files_before_after_unchanged']
    for key in ('archive', 'manifest'):
        item = archive[key]
        actual = identity(R9 / 'geometry' / item['path'])
        assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
    assert n['original_all_ten_full_fields_native_readback_passed'] and n['original_K_b_C_and_threshold_unchanged']
    assert not n['new_solver_executed'] and n['new_native_K_products_executed']
    assert all(value <= 1e-7 for value in n['panel_original_five_residuals'] + n['frame_original_five_residuals'])
    assert records['envelope_independent']['qualification_layers']['all16_original_conditional_frame_gates_passed']
    assert not e['full_native_envelope_qualified'] and not e['full_continuous_G2']
    assert not g['scope']['full_continuous_G2'] and not g['scope']['current_structure_FE_qualified']
    now = datetime.now(timezone.utc).isoformat()
    ledger_path = R9 / 'R9_COMPLETED_WORK_LEDGER.json'
    if ledger_path.exists():
        raise FileExistsError('A sealed R9 work ledger already exists; do not silently rewrite it.')
    ledger = {
        'schema': 'razr-r9-completed-work-ledger-v1', 'sealed_utc': now,
        'source_evidence_base_commit': 'e51de63915a1abeed29e2f95be3044a5d5965045',
        'tested_functional_source_commit': 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
        'tested_functional_source_tree': 'cdd9e2c41216201b6cd04dd610d45fde80499045',
        'named_candidate_sources': ['key_forward_loop_v1', 'panel_key_travel_stops_v1'],
        'bound_records': {key: identity(path) for key, path in scopes.items()},
        'workstreams': {
            '1_original_midtravel_witnesses': {
                'status': 'qualified_in_the_original_finite_scope',
                'historical_native_states_reaudited': ['near', 'far'],
                'new_R9_native_states': [row['state'] for row in g['states'] if row['state'] not in ('near', 'far')],
                'total_original_registered_states': 10, 'pairs_per_producer_or_reader': 118909,
                'producer_and_reader_results': 237818, 'whole_STEP_BREP_files_rehashed': 3094,
                'method_counts_per_role': g['method_counts_per_role'],
                'new_state_different_method_branch_count': g['new_state_different_method_branch_count'],
                'method_identity_not_required_by_original_Common_and_classification_gate': True,
                'original_positive_F1a_collisions_retained': True,
                'same_CAD_kernel_separate_process_reader': True, 'continuous_domain_proof': False,
            },
            '2_structure_and_allowed_domain': {
                'status': 'named_material_repair_and_software_domain_documented_physical_scope_open',
                'positive_q_profiles_recomputed': 4, 'native_STOP_SPRING_body_mappings': 64,
                'global_minimum_wall_or_effective_section_qualified': False,
                'all_functional_faces_qualified': False, 'physically_supported_full_domain_qualified': False,
                'current_structure_FE_qualified': False,
            },
            '3_continuous_envelope': {
                'status': 'all16_original_conditional_volume_gates_passed_native_obligations_open',
                'original_frames': 16, 'conditional_passes': 16,
                'original_roots': 1537, 'global_splits': 718, 'maximum_depth': 18,
                'boundary_piece_tests': 4722120, 'channel_tests': 13224,
                'recorded_producer_seconds': e['producer_recorded_seconds'],
                'recorded_reader_seconds': e['independent_reader_seconds'],
                'largest_conservative_upper_mm3': 9.321533029448826e-8,
                'original_binary64_threshold': 1e-7, 'whole_box_unresolved_final_leaves_retained': 12,
                'zero_intersection_proof': False, 'original_native_failures_preserved': True,
                'full_native_envelope_qualified': False, 'full_continuous_G2': False,
            },
            'parallel_original_numerics': {
                'status': 'original_saved_fields_K_products_and_five_restore_actions_revalidated',
                'original_K_b_C_and_threshold_unchanged': True,
                'panel_original_five_residuals': n['panel_original_five_residuals'],
                'frame_original_five_residuals': n['frame_original_five_residuals'],
                'all_7770_basis_RHS_and_saved_projection_hashes_recomputed': True,
                'all_7770_fresh_K_products_executed': False,
                'restore': n['original_ExactResponseCache_restore'],
                'whole_seed_bitwise_reproduction': False, 'auxiliary_roundoff_failure_preserved': True,
                'new_solver_executed': False, 'current_modified_structure_FE_qualified': False,
            },
            'parallel_real_parts': {
                'status': 'public_OEM_reference_routes_found_actual_same_specimen_binding_open',
                'identity_items': 10, 'part_roles': 7, 'physical_interfaces': 12,
                'required_facts': 228, 'same_specimen_facts': 207, 'selected_revision_facts': 21,
                'new_physical_observations': 0, 'qualified_new_specimen_OEM_bindings': 0,
                'full_new_service_manual_PDFs_obtained': False,
            },
            'subsequent_current_FE_electrical_test_contract': {
                'status': 'not_qualified_for_freeze', 'unsourced_material_rows': 154,
                'unsourced_load_cases': 13, 'current_FE_and_tolerance_qualified': False,
                'OEM_terminals_finished_stack_and_electrical_qualified': False,
                'historical_reference_OLED_fixed_route_failure_retained': True,
                'historical_E3_research_DRC_pass_not_relabelled_as_OEM_qualification': True,
            },
            'final_physical_acceptance': {
                'status': 'not_executed', 'G3': 'not_executed', 'G4': 'not_executed', 'G5': 'not_executed',
                'same_candidate_specimen_assembly_revision_required': True,
                'missing_failed_repaired_replaced_events_kept_distinct': True,
            },
        },
        'publication': {'local_evidence_branch': 'evidence/full-sprint-20261029-r9',
                        'new_branch_pushed_at_seal': False, 'main_merged': False,
                        'historical_unavailable_a11b00f7_not_recreated_or_published': True},
        'release': {'candidate_go': False, 'fixture_fabrication_go': False,
                    'manufacturing_go': False, 'all_blockers_closed': False},
        'new_full_unit_suite_execution': False,
        'historical_S4_unit_scope': {'suites': 36, 'tests': 1654, 'is_new_R9_execution': False},
    }
    write(ledger_path, ledger)

    current_path = ROOT / 'design/current_product.json'
    current = load(current_path)
    prior_keys = ('stage_summary', 'verification_summary', 'hardware_summary', 'active_followup',
                  'current_execution_summary', 'publication_record', 'publication_record_scope', 'work_packages', 'last_update_date')
    current['prior_current_summary_before_20261030_r9'] = {key: copy.deepcopy(current.get(key)) for key in prior_keys}
    current['stage_summary'] = (
        'S4 dd7def6e6a4de9f47dc91ca2ab336fb1a8828560 remains the historically tested functional source. '
        'R9 joins two original R7 midtravel native executions with eight new original-roster states for the '
        'named key_forward_loop_v1 / panel_key_travel_stops_v1 candidate: all ten complete producers and '
        'independent same-kernel native readers pass their finite criteria, with 118909 pair records per role '
        'and 3094 whole STEP/BREP files rehashed. The original 16 conditional envelope gates now all pass '
        'under the unchanged original limits: 718 splits, depth18, 4722120 pieces, recorded 552.217835624s, '
        'maximum conservative upper 9.321533029448826e-8 mm3; all12 unresolved whole-box leaves remain counted. '
        'The full independent certificate reader confirms 16/16. Original K/b/C saved-field products reproduce '
        'all five panel and five frame residuals below 1e-7, with the original H and five saved-action restore '
        'scope retained. Physical domains, native continuous envelopes/G2, current K1/K3 FE,228 actual '
        'specimen/selected-revision bindings, OEM electrical/stackup and real G3-G5 remain open. '
        'All release flags remain false. The controlling ledger is ' + REL + '/R9_COMPLETED_WORK_LEDGER.json.'
    )
    current['verification_summary'] = (
        'Historical S4 D6 is the actual 36-suite/1654-test full-unit pass; R9 is not a new full software run. '
        'R9 freshly executes eight native finite factories/readers and reaudits two original R7 midtravel '
        'archives, preserving original inputs and named material identity. All ten finite states are clear '
        'under the original Common criteria; positive-axis gaps and native Common are counted separately. '
        'The original 16 conditional envelope gates and full independent proof reader pass within the '
        'original recorded budgets. Original numerical K products, correction history, H projections and '
        'five SHA-bound restore actions were actually read back; no new solver was run. The auxiliary '
        'whole-seed bitwise failure remains recorded. Original F1a collisions, native envelope failures, '
        'stopped campaigns and earlier rejection histories remain unchanged. These results do not qualify '
        'the full mechanical domain, native continuous G2, current structure, OEM electrical stack or physical G3-G5.'
    )
    current['hardware_summary'] += (
        ' R9 records no new physical measurement or qualified specimen/OEM binding. Official repair '
        'distribution routes and public L2/L3/BOM previews were located, but complete PDFs were not '
        'obtained; the visible USA BOM applies to XT2551-1/-2 and is not qualified for historical XT2551-3. '
        'The source/applicability record is ' + REL + '/real-sources/R9_OEM_SOURCE_APPLICABILITY.json.'
    )
    current['current_execution_summary'] = REL + '/R9_COMPLETED_WORK_LEDGER.json'
    current['publication_record'] = current['current_execution_summary']
    current['last_update_date'] = now[:10]
    current['updated_utc'] = now
    current['publication_record_scope'] = (
        'R9 is a local evidence successor to e51de63915a1abeed29e2f95be3044a5d5965045. '
        'No push or main merge is claimed by this record. S4 remains the tested functional source; '
        'the new conditional envelope, original numerical readbacks and finite native geometry retain '
        'their separate source/run identities. Prior publication records remain historical.'
    )
    active = current['active_followup']
    active.update({
        'scope': 'R9 ten finite native states, 16 conditional envelope gates and original numerical readbacks; full native continuous/current FE/physical gates open',
        'state': 'R9_completed_finite_and_conditional_scopes_remaining_native_structural_and_physical_obligations_open',
        'branch': 'evidence/full-sprint-20261029-r9', 'pull_request': None,
        'execution_summary': current['current_execution_summary'],
        'latest_evidence_commit': None,
        'latest_evidence_commit_scope': 'Containing local commit is recorded by the final external delivery/publication manifest; this JSON does not self-hash.',
        'latest_completed_diagnostic_run_scope': 'Historical S4 hosted run; R9 local finite/conditional/readback executions are bound by current_execution_summary.',
        'original_ten_native_finite_states_clear': True,
        'original_sixteen_conditional_envelope_frames_passed': True,
        'new_R9_native_finite_states_completed': 8,
        'new_R9_CAD_execution': True,
        'new_R9_native_K_products_executed': True,
        'new_R9_solver_executed': False,
        'new_R9_physical_acquisition': False,
        'new_branch_pushed': False,
        'complete_G2_qualification': False, 'full_motion_qualified': False,
        'current_K1_K3_FE_qualified': False, 'qualified_new_specimen_OEM_fact_bindings': 0,
        'physical_G3_G4_G5_executed_this_run': False, 'all_blockers_closed': False,
    })
    for key in ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go'):
        assert current[key] is False and active[key] is False
    changes = {
        'WP1': ('R9 found public OEM repair routes/manual previews, with no new qualified specimen bindings. The 228 original facts remain open.', REL + '/real-sources/README.md', None),
        'WP4': ('R9 completes the original ten finite states: two historical R7 native midposes reaudited plus eight new producers/readers, 118909 pairs per role. The full 16-frame conditional envelope now passes with 718 splits/depth18/recorded 552.217835624s and maximum 9.321533029448826e-8 mm3; all positive unresolved contributions remain.', REL + '/R9_COMPLETED_WORK_LEDGER.json', 'Qualify native error/filling/topology, the actual full mechanical domain, complete functional faces and continuous G2. Ten finite states and 16 conditional arithmetic gates do not establish these obligations.'),
        'WP5': ('R9 verifies named K1/K3 material accounts, four source cam profiles and 64 native STOP/SPRING mappings across eight new states. The 154 material rows and 13 load cases remain unsourced. Local sections do not prove global minimum wall or strength.', REL + '/geometry/R9_GEOMETRY_SCOPE.json', None),
        'WP7': ('R9 actually recomputes unchanged original K/b/C products for five panel and five frame saved full fields: maxima 9.983337773558199e-8 and 5.659897926075834e-9, both below 1e-7. All 7770 basis RHS/projection hashes and five original saved-action restores are read back; restore maximum 1.1659935073707673e-8. No new solver or all 7770 fresh K products are claimed; the auxiliary whole-seed bitwise failure is retained.', REL + '/numerics/R9_NUMERICAL_SCOPE.json', None),
        'WP9': ('R9 preserves full new native originals, all-pair journals, complete conditional proof forests, numerical readback sources, failed/partial attempts and independent ledgers. The original 14 companion archives retain exact identities. Generated current entrypoints now point to R9; publication of this local successor is not claimed.', REL + '/README.md', None),
    }
    for row in current['work_packages']:
        if row['id'] in changes:
            result, path, remaining = changes[row['id']]
            row.update(result=result, path=path)
            if remaining is not None:
                row['remaining'] = remaining
    current['current_entrypoint_sync_r9'] = {
        'controlling_ledger': current['current_execution_summary'],
        'independent_scientific_cross_ledger': REL + '/independent-review/R9_INDEPENDENT_SCOPE_CROSS_LEDGER.json',
        'functional_source_unchanged': True, 'historical_records_retained': True,
        'new_full_unit_execution': False, 'new_solver_execution': False,
        'new_native_finite_factory_states': 8, 'historical_native_states_reaudited': 2,
        'new_conditional_envelope_full_compute_and_reader': True,
        'new_original_numerical_K_products_and_restore_readback': True,
        'new_physical_observations': 0, 'new_release_qualification': False,
        'validation_record': REL + '/status/R9_CURRENT_ENTRYPOINT_SYNC_RESULT.json',
    }
    write(current_path, current)
    print(json.dumps({'completed': True, 'ledger': identity(ledger_path), 'metadata_updated': current_path.as_posix()}))


if __name__ == '__main__':
    main()
