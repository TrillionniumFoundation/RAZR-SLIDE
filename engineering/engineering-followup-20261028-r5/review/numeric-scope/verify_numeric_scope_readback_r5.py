"""Read-only numeric-history scope audit; no numerical operator is imported."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import struct
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'r5-numeric-readback'
OUT = Path(__file__).resolve().parent


def identity(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def same_float64(a, b):
    return struct.pack('<d', a) == struct.pack('<d', b)


def main():
    target = OUT / 'R5_INDEPENDENT_NUMERIC_SCOPE_REVIEW.json'
    require(not target.exists(), 'Preserve prior review; use a new report for a new audit.')
    started = time.monotonic()
    report = {'schema': 'razr-r5-independent-original-numeric-scope-review-v1',
              'recorded_utc': datetime.now(timezone.utc).isoformat(), 'review_completed': False,
              'cross_author_review': True, 'new_numeric_execution': False,
              'K_or_Kff_product_executed': False, 'H_action_executed': False,
              'new_factorization_or_solver_executed': False,
              'new_current_geometry_FE_qualification': False,
              'all_384_member_CRC_repeated_by_reviewer': False,
              'issues': []}
    try:
        scope_path = SOURCE / 'R5_ORIGINAL_NUMERIC_QUALIFICATION_SCOPE.json'
        prose_path = SOURCE / 'README_R5_ORIGINAL_NUMERIC_SCOPE.md'
        receipt_path = SOURCE / 'R5_N15_READONLY_RECEPTION_ACTUAL.json'
        original_ids = [identity(p) for p in (scope_path, prose_path, receipt_path)]
        scope = json.loads(scope_path.read_text())
        prose = prose_path.read_text()
        receipt = json.loads(receipt_path.read_text())
        archive_path = SOURCE / scope['source_zip']['file_name']
        archive_id = identity(archive_path)
        require(all(archive_id[k] == scope['source_zip'][k] for k in ('bytes', 'sha256')),
                'Actual complete ZIP identity differs from scope.')
        require(archive_id['bytes'] == receipt['zip_bytes'] == 40413347 and
                archive_id['sha256'] == receipt['zip_sha256'] ==
                'c3cc04b9c577b8cc1d4c884e9e4334a9533148757473d32334db65a886e3f4be',
                'Original complete ZIP or receipt identity differs.')
        require(receipt['all_member_CRC_verified'] is True and len(receipt['members']) == 384,
                'Original full-member CRC receipt is incomplete.')
        original_ids.append(archive_id)
        member_receipts = {r['path']: r for r in receipt['members']}
        require(len(member_receipts) == 384, 'Duplicate original member identity.')
        records = {}
        readbacks = []
        with zipfile.ZipFile(archive_path) as archive:
            files = [i for i in archive.infolist() if not i.is_dir()]
            require(len(files) == len({i.filename for i in files}) == 384,
                    'ZIP member cardinality or uniqueness differs.')
            require({i.filename: i.file_size for i in files} ==
                    {r['path']: r['bytes'] for r in receipt['members']},
                    'Actual central directory and full reception inventory differ.')
            for name, binding in scope['source_records'].items():
                relative = binding['archive_relative_path']
                raw = archive.read(relative)  # Reads/CRC-checks only the eight selected originals.
                local = SOURCE / 'original-records' / relative
                require(raw == local.read_bytes(), 'Selected extracted original differs from actual ZIP member.')
                actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                require(all(actual[k] == binding[k] == member_receipts[relative][k]
                            for k in ('bytes', 'sha256')), 'Selected source identity differs.')
                records[name] = json.loads(raw)
                readbacks.append({'record': name, 'archive_relative_path': relative, **actual,
                                  'actual_member_CRC_checked': True, 'extracted_copy_exactly_equal': True})
                original_ids.append(identity(local))
        require(len(records) == 8, 'Exactly eight claimed original reports required.')
        report['actual_archive_identity'] = archive_id
        report['actual_archive_non_directory_member_count'] = 384
        report['existing_complete_CRC_receipt_identity'] = identity(receipt_path)
        report['existing_complete_CRC_receipt_matches_actual_whole_ZIP_identity'] = True
        report['source_records_read_back'] = readbacks
        threshold = scope['original_float64_residual_threshold']
        require(same_float64(threshold, 1e-7), 'Original binary64 threshold changed.')
        for key in ('frame_producer', 'panel_H_pilot', 'frame_H_pilot', 'four_loads'):
            require(same_float64(records[key]['original_threshold'], threshold), 'Original source threshold differs.')
        require(same_float64(records['linear_seed']['original_native_residual_threshold'], threshold),
                'Original seed threshold differs.')
        h = records['H_restore']
        probe_rows = []
        for body in ('panel', 'frame'):
            source = records[body + '_five']
            require(source['original_five_qualification_verified'] is True, 'Historical independent five pass absent.')
            original = source['original_five_ratios']
            stated = scope[body + '_original_five_residuals']
            actions = h['bodies'][body]['five_original_field_actions']
            require(len(original) == len(stated) == len(actions) == 5, 'Five original probes required.')
            for index, (a, b, action) in enumerate(zip(original, stated, actions)):
                require(action['index'] == index and same_float64(a, b) and
                        same_float64(a, action['saved_native_residual_ratio']) and a <= threshold,
                        'Reported original probe values, order or original gate differ.')
                require(len(action['full_field_file_sha256']) == len(action['full_RHS_array_sha256']) == 64,
                        'Original action field/RHS identity binding absent.')
                probe_rows.append({'body': body, 'probe_index': index, 'reported_residual': a,
                                   'reported_residual_float64_hex': a.hex(),
                                   'source_reader_and_H_action_values_bit_equal': True,
                                   'reported_value_within_original_threshold': True,
                                   'K_residual_recomputed_here': False})
            item = h['bodies'][body]
            stated_h = scope['historical_H_column_producer_scope'][body]
            require(stated_h['unique_columns'] == item['unique_original_columns'] == 3885 and
                    same_float64(stated_h['maximum_reported_column_residual'],
                                 item['maximum_reported_original_column_residual_ratio']) and
                    stated_h['raw_H_array_sha256'] == item['raw_H_array_sha256'] and
                    stated_h['raw_global_checks'] == item['raw_global_checks'], 'Historical H scope differs.')
            require(records[body + '_H_pilot']['successful_full_fields_preserved'] is False and
                    records[body + '_H_pilot']['successful_field_and_native_residual_array_hashes_preserved'] is True,
                    'H pilot field-content versus hash-preservation boundary changed.')
        report['original_ten_reported_residual_checks'] = probe_rows
        require(scope['historical_combined_H_checks'] == h['combined_unsymmetrized_raw_H_checks'] and
                scope['historical_restore'] == h['original_ExactResponseCache_restore'] and
                scope['historical_restore_callback_scope'] == h['callback_scope'], 'H/restore source scope differs.')
        require(h['original_ExactResponseCache_restore']['probes'] ==
                h['original_ExactResponseCache_restore']['response_calls'] ==
                h['exact_original_restore_callback_calls'] == 5 and
                h['original_combined_ExactResponseCache_restore_passed'] is True,
                'Original five-action restore scope differs.')
        require(h['independent_all_7770_column_K_products_executed'] is False and
                h['all_successful_H_column_full_fields_retained'] is False and
                h['arbitrary_RHS_inverse_qualified'] is False and
                h['historical_finite_QP_resume_executed'] is False and
                h['original_ten_probe_full_fields_and_residuals_preserved'] is True,
                'Historical qualification limitation or original-field preservation changed.')
        seed = records['linear_seed']
        require(seed['scientific_execution_completed'] is True and
                seed['original_linear_response_seed_qualified'] is True and
                seed['original_trace_seed_format_and_energy_intake_preconditions_checked'] is True,
                'Original seed format/energy-input qualification absent.')
        require(all(seed['scope'][k] is False for k in (
                    'full_7770_K_residuals_independently_recomputed_here', 'finite_QP_checkpoint',
                    'same_energy_finite_QP_driver_resume_executed', 'original_trace_driver_executed',
                    'current_K3_FE_qualified', 'physical_or_OEM_inputs_newly_acquired')),
                'Seed scope overstates finite-QP/current-geometry/physical qualification.')
        loads = records['four_loads']
        require(scope['historical_four_load_residuals'] == loads['final_original_ratios'] ==
                seed['original_native_four_scalar_residual_ratios'] and
                scope['historical_four_load_block_residual'] == seed['original_native_two_dimensional_block_residual_ratio'],
                'Original four-load scalar/block values differ.')
        report['H_restore_seed_scope_matches_original_reports'] = True
        report['scope_limits_retained'] = [
            'No independent all7770-column K products were performed.',
            'Hashes of successful H-column fields do not mean every full field was retained.',
            'Restore accepts exactly five ordered SHA-bound genuine saved actions; unknown RHS is rejected.',
            'Linear seed format/energy intake is distinct from arbitrary-RHS inverse qualification or finite-QP checkpoint/resume.',
            'Historical evidence does not acquire current K1/K3 FE, OEM, manufacturing, physical or current-runtime qualification.']
        full = {'panel': loads['files']['final/load-0-field.npy']['shape'][0],
                'frame': records['frame_producer']['files']['final/probe-0-field.npy']['shape'][0]}
        free = {body: records[body + '_H_pilot']['original_Kff']['shape'][0] for body in ('panel', 'frame')}
        require(full == {'panel': 344103, 'frame': 474726} and free == {'panel': 344097, 'frame': 473949},
                'Original full/free dimension source differs.')
        capacity = scope['full_field_extension_capacity_lower_bound']
        require(capacity['original_full_dofs'] == full and capacity['original_free_dofs'] == free and
                capacity['columns_per_body'] == 3885 and capacity['float64_bytes_per_value'] == 8,
                'Capacity arithmetic inputs differ from original source.')
        field_bytes = 3885 * 8 * sum(full.values())
        residual_bytes = 3885 * 8 * sum(free.values())
        total = field_bytes + residual_bytes
        require(field_bytes == capacity['all_7770_full_field_raw_bytes'] == 25449205320 and
                residual_bytes == capacity['all_7770_free_residual_raw_bytes'] == 25424869680 and
                total == capacity['field_plus_residual_raw_bytes'] == 50874075000,
                'Storage lower-bound integer arithmetic differs.')
        report['capacity_arithmetic'] = {
            'full_field_dimension_sources': {
                'panel': 'four_loads#/files/final~1load-0-field.npy/shape/0',
                'frame': 'frame_producer#/files/final~1probe-0-field.npy/shape/0'},
            'free_dimension_sources': {body: body + '_H_pilot#/original_Kff/shape/0' for body in ('panel', 'frame')},
            'full_dofs': full, 'free_dofs': free, 'columns_per_body': 3885, 'bytes_per_float64_value': 8,
            'equation': '3885 * 8 * ((344103 + 474726) + (344097 + 473949))',
            'full_fields_raw_bytes': field_bytes, 'free_residuals_raw_bytes': residual_bytes, 'sum_raw_bytes': total,
            'storage_payload_lower_bound_only': True, 'not_RAM_peak_or_compressed_size_or_time_guarantee': True,
            'RHS_corrections_K_factors_headers_and_copies_excluded': True, 'new_campaign_started': False}
        require(all(scope[k] is False for k in (
            'independent_all_7770_column_K_products_executed', 'all_H_column_full_fields_historically_retained',
            'arbitrary_RHS_inverse_qualified', 'finite_QP_checkpoint_or_resume_qualified',
            'current_K1_K3_geometry_FE_qualified', 'original_numeric_inputs_or_threshold_changed',
            'historical_runtime_requalified_by_current_R4_runtime', 'new_numeric_execution_in_R5', 'all_blockers_closed')),
            'Public qualification limit changed.')
        require('50,874,075,000' in prose and '7,770' in prose and '未知 RHS 被拒绝' in prose and
                '没有独立重算' in prose and '没有保留全部成功 H 列的全场' in prose and '没有运行数值求解器' in prose,
                'Human-readable scope omits the reviewed limits.')
        require(all(identity(ROOT / r['path']) == r for r in original_ids), 'An original input changed during readback.')
        require(identity(ROOT / 'r5-envelope/verify_exterior_trim_r5e_v5.py')['sha256'] ==
                '8d2083717a025601eccfbab8679f18e8839c2def0da4995652280b00f79be2a8', 'Frozen V5 checker differs.')
        report['reviewed_artifact_identities'] = original_ids[:3]
        report['original_inputs_unchanged_after_review'] = True
        report['frozen_V5_checker_unchanged'] = True
        report['review_completed'] = True
        report['conclusion'] = 'No mismatch found in the historical numeric scope or storage arithmetic. This is report/identity readback, not a new numerical qualification.'
    except BaseException as exc:
        report['issues'].append({'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
        raise
    finally:
        report['reader_source_identity'] = identity(Path(__file__))
        report['seconds'] = time.monotonic() - started
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'review_completed': report['review_completed'], 'issues': report['issues'],
                          'seconds': report['seconds'], 'peak_RSS_bytes': report['peak_RSS_bytes']}))


if __name__ == '__main__':
    main()
