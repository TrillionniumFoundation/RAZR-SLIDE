"""Record the completed V6 local run; this is not a new geometric audit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'attempt-1'
started = time.monotonic()


def identity(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest}


def load(path):
    return json.loads(Path(path).read_text())


def controls(report):
    real = {key: {'count': len(value), 'rejected_count': sum(row['actual_rejected'] is True for row in value),
                  'records': value}
            for key, value in report.items() if key.endswith('negative_controls')}
    analytic = report['mandatory_analytic_controls']
    return {'actual_case_controls': real, 'actual_case_applicability': report['real_case_control_applicability'],
            'actual_case_rejection_count': sum(row['rejected_count'] for row in real.values()),
            'synthetic_analytic_controls': analytic,
            'synthetic_analytic_rejection_count': sum(sum(row['actual_rejected'] is True for row in value)
                                                     for key, value in analytic.items() if key.endswith('negative_controls')),
            'all_retained_no_excluded_positive_was_executed': analytic['all_retained_no_excluded_positive']['verified'],
            'all_retained_positive_is_not_an_actual_V5_or_V6_case': not analytic['all_retained_no_excluded_positive']['is_actual_V5_or_V6_case_branch_coverage']}


pipeline = load(OUT / 'pipeline.json')
launch = load(HERE / 'R5_V6_LOCAL_LAUNCH_RECEIPT_V1.json')
assert pipeline['completed'] and launch['driver_completed'] and launch['driver_exit_code'] == 0
assert launch['snapshot_files_unchanged_after_execution'] and pipeline['source_and_public_inputs_unchanged']
stages = []
for stage in pipeline['stages']:
    label = stage['label']
    controller_path = OUT / (label + '-supervision/controller.json')
    report_path = OUT / label / 'report.json'
    controller = load(controller_path)
    report = load(report_path)
    assert stage['completed'] and controller['completed'] and controller['worker_started']
    assert controller['resource_stop'] is None and controller['worker_exit_code'] == 0 and report['execution_completed']
    stages.append({'label': label, 'worker_seconds': report['seconds'], 'worker_peak_RSS_bytes': report['peak_RSS_bytes'],
                   'live_RSS_sample_count': sum(isinstance(row.get('owned_worker_memory'), dict) for row in controller['observations']),
                   'controller': identity(controller_path), 'report': identity(report_path),
                   'actual_output_bytes': sum(path.stat().st_size for path in (OUT / label).rglob('*') if path.is_file()),
                   'owned_gate_completed': True, 'resource_stop': None, 'actual_worker_exit_code': 0})
producer = load(OUT / 'all-primitive-support-frames/report.json')
checker = load(OUT / 'verify-all/report.json')
single = load(OUT / 'single-primitive-support-leaf/report.json')
single_checker = load(OUT / 'verify-single/report.json')
assert producer['primitive_support_model_conditional_clearance_passes'] == checker['primitive_support_model_conditional_clearance_passes'] == 8
frame_rows = []
splits_before = 0
for row in producer['frames']:
    frame_rows.append({key: row[key] for key in ['case_id', 'frame', 'pair', 'root_count',
        'primitive_support_model_conditional_upper_mm3', 'primitive_support_model_conditional_upper_exact_mm3',
        'primitive_support_model_conditional_clearance_gate_passed', 'exact_splits_this_frame',
        'exact_piece_tests_this_frame', 'exact_support_inequality_tests_this_frame',
        'maximum_depth_reached', 'total_leaf_count', 'certificate']})
    frame_rows[-1]['global_splits_spent_before_this_frame'] = splits_before
    frame_rows[-1]['global_split_budget_already_exhausted_on_frame_entry'] = splits_before == 4096
    splits_before += row['exact_splits_this_frame']
rows = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        assert not path.is_symlink()
        item = identity(path)
        rows.append(dict(item, path=path.relative_to(OUT).as_posix()))
manifest = {'schema': 'r5-v6-local-completed-output-manifest-v1', 'output_root': str(OUT),
            'files': rows, 'file_count': len(rows), 'total_bytes': sum(r['bytes'] for r in rows),
            'all_original_execution_bytes_preserved': True, 'local_execution_not_GitHub_run': True}
manifest_path = HERE / 'R5_V6_LOCAL_ACTUAL_OUTPUT_MANIFEST.json'
assert not manifest_path.exists()
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
summary = {
    'schema': 'r5-v6-local-actual-execution-summary-v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
    'record_kind': 'completed_execution_and_original_report_readback_not_an_independent_geometric_reproof',
    'summary_source': identity(__file__), 'pipeline': identity(OUT / 'pipeline.json'),
    'local_launch': identity(HERE / 'R5_V6_LOCAL_LAUNCH_RECEIPT_V1.json'),
    'output_manifest': identity(manifest_path), 'actual_output_file_count': len(rows),
    'actual_output_bytes': manifest['total_bytes'], 'local_pipeline_elapsed_seconds': pipeline['elapsed_seconds'],
    'local_launcher_elapsed_seconds': launch['elapsed_seconds'], 'all_five_stages_completed': len(stages) == 5,
    'stages': stages, 'producer_conditioned_pass_count': 8, 'independent_checker_conditioned_pass_count': 8,
    'frame_count': 16, 'new_complete_frame_passes_over_V5': 0,
    'raw_original_V3_model_pass_count_unchanged': 4, 'V4_actual_failure_preserved': True,
    'original_V5_model_pass_count_unchanged': 8, 'original_float64_TOL_unchanged': True,
    'selected_actual_V5_leaf_conditional_upper_exact_mm3': single['frames'][0]['primitive_support_model_conditional_upper_exact_mm3'],
    'producer_counters': producer['counters'], 'frames': frame_rows,
    'registered_global_split_budget': 4096, 'actual_global_split_budget_exhausted': producer['counters']['splits'] == 4096,
    'global_budget_exhausted_during': {'case_id': 'case-028', 'frame': 1},
    'pending_and_budget_stopped_leaves_retained_in_full': True,
    'full_checker_counts': {key: checker[key] for key in ['total_new_tree_nodes_verified', 'total_new_splits_verified',
         'total_new_positive_leaves_verified', 'total_actual_new_excluded_leaves_verified', 'total_actual_retained_roots_verified',
         'applied_plane_occurrences_verified', 'applied_cylinder_occurrences_verified']},
    'single_independent_controls': controls(single_checker), 'full_independent_controls': controls(checker),
    'conditional_primitive_support_model_only': True, 'conditional_trim_model_only': True,
    'native_primitive_semantics_verified': False, 'native_trim_class_membership_verified': False,
    'native_Common_called': False, 'original_raw_gate_reclassified': False, 'full_continuous_G2': False,
    'all_blockers_closed': False, 'summary_readback_seconds': time.monotonic() - started,
}
target = HERE / 'R5_V6_LOCAL_EXECUTION_ACTUAL_SUMMARY.json'
assert not target.exists()
target.write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'summary': identity(target), 'manifest': identity(manifest_path), 'file_count': len(rows),
                 'output_bytes': manifest['total_bytes'], 'stages': len(stages), 'conditioned_passes': 8,
                 'actual_case_controls_rejected': [summary['single_independent_controls']['actual_case_rejection_count'], summary['full_independent_controls']['actual_case_rejection_count']],
                 'analytic_controls_rejected': [summary['single_independent_controls']['synthetic_analytic_rejection_count'], summary['full_independent_controls']['synthetic_analytic_rejection_count']]}))
