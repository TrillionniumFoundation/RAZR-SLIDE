from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
RECORDS = ROOT / 'original-records'
names = {
    'panel_five': 'original-probe-qualification/panel/N13-v3-independent-readback.json',
    'frame_five': 'original-probe-qualification/frame/FRAME_INDEPENDENT_READBACK.json',
    'H_restore': 'independent-audit/H_EXECUTED_READBACK_SUMMARY.json',
    'linear_seed': 'independent-audit/LINEAR_SEED_EXECUTED_SUMMARY.json',
    'four_loads': 'actual-results/panel-four-loads/FOUR_LOAD_REPORT.json',
    'frame_producer': 'original-probe-qualification/frame/N14_REPORT.json',
    'panel_H_pilot': 'H-column-records/panel-H-pilot/H_BLOCK_REPORT.json',
    'frame_H_pilot': 'H-column-records/frame-H-pilot/H_BLOCK_REPORT.json',
}
docs = {key: json.loads((RECORDS / name).read_text()) for key, name in names.items()}
identities = {key: {'archive_relative_path': name,
                    'bytes': (RECORDS / name).stat().st_size,
                    'sha256': hashlib.sha256((RECORDS / name).read_bytes()).hexdigest()}
              for key, name in names.items()}
panel = docs['panel_five']['original_five_ratios']
frame = docs['frame_five']['original_five_ratios']
H = docs['H_restore']
assert len(panel) == len(frame) == 5
assert all(0 <= ratio <= 1e-7 for ratio in panel + frame)
assert docs['panel_five']['original_five_qualification_verified'] is True
assert docs['frame_five']['original_five_qualification_verified'] is True
for body, ratios in [('panel', panel), ('frame', frame)]:
    assert [row['saved_native_residual_ratio'] for row in H['bodies'][body]['five_original_field_actions']] == ratios
    assert H['bodies'][body]['unique_original_columns'] == 3885
assert H['completed'] and H['both_body_complete_H_accepted']
assert H['original_combined_ExactResponseCache_restore_passed']
assert H['independent_all_7770_column_K_products_executed'] is False
assert H['all_successful_H_column_full_fields_retained'] is False
assert H['original_ten_probe_full_fields_and_residuals_preserved'] is True
assert H['arbitrary_RHS_inverse_qualified'] is False
assert docs['linear_seed']['original_linear_response_seed_qualified']
assert docs['linear_seed']['scope']['original_finite_QP_resume_state_contract_satisfied'] is False
full_dofs = {'panel': 344103, 'frame': 474726}
free_dofs = {body: docs[body + '_H_pilot']['original_Kff']['shape'][0] for body in ('panel', 'frame')}
for doc, body in [(docs['four_loads'], 'panel'), (docs['frame_producer'], 'frame')]:
    shapes = {tuple(row['shape']) for name, row in doc['files'].items() if 'field' in name and 'shape' in row}
    assert shapes == {(full_dofs[body],)}
capacity = {
    'purpose': 'Storage lower bound for any proposed new all-column full-field/residual preservation campaign; not a registered execution strategy or a new acceptance criterion.',
    'columns_per_body': 3885,
    'original_full_dofs': full_dofs,
    'original_free_dofs': free_dofs,
    'float64_bytes_per_value': 8,
    'all_7770_full_field_raw_bytes': 3885 * 8 * sum(full_dofs.values()),
    'all_7770_free_residual_raw_bytes': 3885 * 8 * sum(free_dofs.values()),
    'excludes_RHS_corrections_K_factors_headers_and_copies': True,
    'compressed_size_or_time_guarantee': False,
    'new_all_column_campaign_started': False,
    'historical_missing_full_fields_recreated': False,
}
capacity['field_plus_residual_raw_bytes'] = capacity['all_7770_full_field_raw_bytes'] + capacity['all_7770_free_residual_raw_bytes']
report = {
    'schema': 'razr-r5-original-numeric-qualification-scope-readback-v1',
    'source_zip': {'file_name': 'RAZR-SLIDE_N15_H_restore_four_load_science_20261027.zip',
                   'bytes': 40413347, 'sha256': 'c3cc04b9c577b8cc1d4c884e9e4334a9533148757473d32334db65a886e3f4be'},
    'source_records': identities,
    'readback_method': 'Full original ZIP SHA/CRC and all 384 members were re-read; these eight original JSON records were then cross-compared. No numerical solver, native K product or H action ran in R5.',
    'original_float64_residual_threshold': 1e-7,
    'panel_original_five_residuals': panel,
    'frame_original_five_residuals': frame,
    'historical_independent_original_five_passes': {'panel': 5, 'frame': 5},
    'historical_H_column_producer_scope': {body: {
        'unique_columns': H['bodies'][body]['unique_original_columns'],
        'maximum_reported_column_residual': H['bodies'][body]['maximum_reported_original_column_residual_ratio'],
        'raw_H_array_sha256': H['bodies'][body]['raw_H_array_sha256'],
        'raw_global_checks': H['bodies'][body]['raw_global_checks'],
    } for body in ('panel', 'frame')},
    'historical_combined_H_checks': H['combined_unsymmetrized_raw_H_checks'],
    'historical_restore': H['original_ExactResponseCache_restore'],
    'historical_restore_callback_scope': H['callback_scope'],
    'historical_four_load_residuals': docs['linear_seed']['original_native_four_scalar_residual_ratios'],
    'historical_four_load_block_residual': docs['linear_seed']['original_native_two_dimensional_block_residual_ratio'],
    'historical_linear_seed_complete': True,
    'original_ten_probe_full_fields_and_corrections_preserved': True,
    'independent_all_7770_column_K_products_executed': False,
    'all_H_column_full_fields_historically_retained': False,
    'arbitrary_RHS_inverse_qualified': False,
    'finite_QP_checkpoint_or_resume_qualified': False,
    'current_K1_K3_geometry_FE_qualified': False,
    'original_numeric_inputs_or_threshold_changed': False,
    'historical_runtime_requalified_by_current_R4_runtime': False,
    'new_numeric_execution_in_R5': False,
    'full_field_extension_capacity_lower_bound': capacity,
    'all_blockers_closed': False,
}
(ROOT / 'R5_ORIGINAL_NUMERIC_QUALIFICATION_SCOPE.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'panel_five': panel, 'frame_five': frame,
    'historical_restore_largest_error': H['original_ExactResponseCache_restore']['largest_relative_error'],
    'field_plus_residual_raw_bytes_if_extending_all_columns': capacity['field_plus_residual_raw_bytes'],
    'new_numeric_execution_in_R5': False}))
