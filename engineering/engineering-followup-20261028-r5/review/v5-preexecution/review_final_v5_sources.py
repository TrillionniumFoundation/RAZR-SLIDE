"""Bounded static final-source review; never imports the model or checker.

Only source hashes/AST, registered constants, the workflow and locked input
identities are read. The mathematical source review is documented separately.
No geometry function, model control or original R4 proof decoder is executed.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import resource
import time


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'r5-envelope'
REVIEWED = {
    'exterior_trim_r5e_v5.py': '6d79a7e323747fd6e815993e4d1bbb7b967d91ca69cd33f99e23269570730a73',
    'trim_boundary_model_r5e_v5.py': '704e5dad9195fbd31edd2a5aff9121bf198baf540a2d9c17bc9f4376ab42b1f6',
    'run_portable_trim_r5e_v5.py': '7a8dc6607e4a0e52330ad6a9bec253981b19205d307894ce11c6ff1d24b21cbe',
    'verify_exterior_trim_r5e_v5.py': '8d2083717a025601eccfbab8679f18e8839c2def0da4995652280b00f79be2a8',
    'R5E_TRIM_REALIZATION_MODEL_V5_BASIS.md': 'd55d3cb863b27ad1c9cf7ec61fe28855f4c5cb323db9965031470fdcd81f149b',
    'R5E_V5_STATIC_SOURCE_CAPACITY.json': 'c206e86982658a98b98960ac0a753ae53412aca638c2fa21d913b7d1e7521ab1',
    'R5E_V5_PLANAR_TRIM_SOURCE.json.gz': 'bc778c13f9efbc280bcb93e59edbc821d2a7b751f0b8730231d1b0bd855e2804',
}
TEMPLATE_SHA = 'da107b2ff8e6428e8f8e14b2df030e92b512eb7c3e6d8f05b8dec62a882935e9'
REQUIRED_RUNTIME = {
    'exterior_trim_r5e_v5.py', 'verify_exterior_trim_r5e_v5.py',
    'run_portable_trim_r5e_v5.py', 'trim_boundary_model_r5e_v5.py',
    'R5E_TRIM_REALIZATION_MODEL_V5_BASIS.md', 'R5E_V5_PLANAR_TRIM_SOURCE.json.gz',
    'R5E_V4_REAL_RETAINED_CELL.json', 'exterior_channels_r5e_v3.py',
    'verify_exterior_channels_r5e_v3.py', 'R5E_PUBLIC_INPUT_BRIDGE.json',
}
EXPECTED_STAGES = [
    ('single-trim-model-cell', 'single_trim_model_cell'),
    ('verify-single', 'verify_single'),
    ('preflight-trim-model', 'preflight_trim_model'),
    ('all-trim-model-frames', 'all_trim_model_frames'),
    ('verify-all', 'verify_all'),
]
EXPECTED_GATES = {
    'wall_seconds': 600, 'RSS_limit_bytes': 805306368,
    'shared_ceiling_bytes': 7301444403, 'disk_floor_bytes': 104857600,
    'expected_output_bytes': 41943040, 'maximum_output_bytes': 41943040,
    'metadata_margin_bytes': 4194304, 'zero_RSS_missing_observations_allowed': False,
}
streamed = 0


def need(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    global streamed
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        while chunk := stream.read(1 << 20):
            streamed += len(chunk)
            need(streamed <= 33554432, 'registered 32 MiB total stream budget exceeded')
            digest.update(chunk)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
            'sha256': digest.hexdigest()}


def checked_members(root, rows):
    need(len(rows) == len({r['path'] for r in rows}), 'duplicate source-lock member')
    result = []
    for row in rows:
        path = (root / row['path']).resolve()
        need(path.is_relative_to(root), 'locked member escapes its root')
        actual = identity(path)
        need(all(actual[k] == row[k] for k in ('bytes', 'sha256')), 'locked source identity differs')
        result.append(actual)
    return result


def assignment(tree, name):
    found = [n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    need(len(found) == 1, 'ambiguous reviewed static assignment: ' + name)
    return found[0]


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--workflow', type=Path, required=True)
    parser.add_argument('--r4-root', type=Path, default=ROOT / 'r4-envelope/public-final-v2')
    args = parser.parse_args()
    started = time.monotonic()
    budget = json.loads((HERE / 'R5_V5_STATIC_REVIEW_BUDGET.json').read_text())
    resource.setrlimit(resource.RLIMIT_AS, (budget['maximum_address_space_bytes'],) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    r4 = args.r4_root.resolve()
    result = {
        'schema': 'razr-r5-v5-independent-final-static-source-review',
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'execution_kind': 'static_source_and_identity_audit_only',
        'static_review_completed': False,
        'V5_producer_executions': 0, 'V5_checker_executions': 0,
        'V5_model_control_executions': 0, 'native_operations': 0,
        'original_R4_proof_decodes': 0, 'original_gate_admission_claimed': False,
        'new_mathematical_qualification': False,
        'conditional_trim_model_only': True,
        'native_trim_class_membership_verified': False,
        'inner_wire_hole_semantics_verified_for_native': False,
        'original_raw_gate_reclassified': False, 'full_continuous_G2': False,
        'original_V3_raw_passes_unchanged': 4,
        'actual_V4_failure_preserved': True,
        'formal_V5_run_or_remote_publication_verified': False,
    }
    try:
        reviewed_identities = []
        trees = {}
        for name, expected in REVIEWED.items():
            actual = identity(SOURCE / name)
            need(actual['sha256'] == expected, 'source changed after manual review: ' + name)
            reviewed_identities.append(actual)
            if name.endswith('.py'):
                trees[name] = ast.parse((SOURCE / name).read_text(), filename=name)
        result['reviewed_source_identities'] = reviewed_identities
        result['python_sources_AST_parsed_without_import'] = sorted(trees)
        lock_path = SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V5.json'
        lock = json.loads(lock_path.read_text())
        result['source_lock'] = identity(lock_path)
        need(result['source_lock']['sha256'] == 'd05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211',
             'final reviewed lock changed')
        need(lock['source_commit'] == 'c5f6606924937d716b007cd3ffa8e54df8ecfa5d', 'original R4 source anchor differs')
        need(REQUIRED_RUNTIME <= {r['path'] for r in lock['r5_files']}, 'runtime source omitted from lock')
        result['locked_R5_members'] = checked_members(SOURCE, lock['r5_files'])
        original_lock = json.loads((SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V4.json').read_text())
        need(lock['r4_source_files'] == original_lock['r4_source_files'], 'original owned supervisor/entry/process source lock changed')
        result['locked_original_owned_process_members'] = checked_members(r4, lock['r4_source_files'])
        bridge = json.loads((SOURCE / 'R5E_PUBLIC_INPUT_BRIDGE.json').read_text())
        need(bridge['source_commit'] == lock['source_commit'] and len(bridge['files']) == 19,
             'complete original public input bridge required')
        need(len({r['path'] for r in bridge['files']}) == 19, 'public bridge duplicate')
        need(all(r['decoded_json_equal'] is True and not r['changed_strings'] for r in bridge['files']),
             'public bridge declares altered original values')
        result['original_public_input_identities_streamed_only'] = checked_members(
            r4, [dict(r['public_identity'], path=r['path']) for r in bridge['files']])
        driver = trees['run_portable_trim_r5e_v5.py']
        sequence = ast.literal_eval(assignment(driver, 'sequence'))
        need(sequence == EXPECTED_STAGES, 'original five-stage sequential order changed')
        result['registered_sequential_stages'] = sequence
        gates_node = assignment(driver, 'shared_base')
        need(isinstance(gates_node, ast.Dict), 'owned process gates are not an explicit dictionary')
        gates = {}
        for key, value in zip(gates_node.keys, gates_node.values):
            if isinstance(key, ast.Constant) and key.value in EXPECTED_GATES:
                gates[key.value] = ast.literal_eval(value)
        need(gates == EXPECTED_GATES, 'original resource gates changed')
        result['unchanged_original_owned_process_gates'] = gates
        template = ROOT / 'r5-integration/r5-trim-v5-workflow.template.yml'
        result['reviewed_workflow_template'] = identity(template)
        need(result['reviewed_workflow_template']['sha256'] == TEMPLATE_SHA, 'reviewed workflow template changed')
        expected_workflow = template.read_text().replace('__FINAL_V5_LOCK_SHA__', result['source_lock']['sha256'])
        workflow = args.workflow.resolve()
        actual_workflow = workflow.read_text()
        need(actual_workflow == expected_workflow and '__FINAL_V5_LOCK_SHA__' not in actual_workflow,
             'concrete workflow does not exactly pin final reviewed lock')
        result['concrete_workflow'] = identity(workflow)
        need(result['concrete_workflow']['sha256'] == 'd47de5cb65f6abaed20392ca1ad06032d243cea703dc081b835e43d73a8e1417',
             'final concrete workflow changed')
        result['workflow_controls'] = {
            'repository': 'TrillionniumFoundation/RAZR-SLIDE',
            'push_branch': 'evidence/full-sprint-20261028-r5',
            'job_exact_ref': 'refs/heads/evidence/full-sprint-20261028-r5',
            'push_trigger_path': 'engineering/engineering-followup-20261028-r5/compute/RUN_REQUEST.json',
            'manual_dispatch_subject_to_same_job_ref_guard': True,
            'permissions': {'contents': 'read'}, 'credentials_persisted': False,
            'checkout_exact_github_sha_checked_again_by_git': True,
            'fixed_actions': re.findall(r'uses:\s*([^\s]+)', actual_workflow),
            'timeout_minutes': 55, 'artifact_upload_after_failure': True,
            'source_lock_literal_sha256': result['source_lock']['sha256'],
            'five_worker_limits_seconds': 5 * 600,
            'job_minus_worker_limit_margin_seconds': 55 * 60 - 5 * 600,
            'capacity_estimate_is_not_runtime_guarantee': True,
        }
        need(result['workflow_controls']['fixed_actions'] == [
            'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
            'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9'], 'action pin changed')
        result['control_programs_reviewed_but_not_executed'] = {
            'mandatory_synthetic_positive_cases': ['complete_six_face_box_channel', 'exact_split_with_positive_tiny_retained_leaf'],
            'mandatory_synthetic_negative_counts': {'channel': 4, 'split': 5, 'leaf': 2},
            'actual_certificate_mutation_counts_when_applicable': {'phase': 3, 'root': 2, 'leaf': 2, 'channel': 4, 'split': 5, 'trim_boundary': 4},
            'actual_channel_and_split_without_eligible_objects': 'explicitly not applicable; no fabricated object',
            'actual_trim_missing_specific_targets': 'explicit per-control not-applicable result',
            'V4_actual_twelve_rejections_imported_as_V5_results': False,
        }
        result['remaining_unproved_premises'] = [
            'Native inner-wire-as-hole semantics.',
            'Native closure of actual ULP endpoint gaps stays within registered corner squares.',
            'Native compiled transformation/Boolean error bounds and complete-factory G2.',
            'Actual V5 admission, execution, controls, mathematical outcomes and post-run hashes.',
        ]
        result['source_lock_rehash_scope'] = {
            'literal_lock_checked_at_workflow_entry': True,
            'driver_postchecks_locked_payloads_and_all19_public_inputs': True,
            'lock_file_itself_is_not_in_driver_final_payload_posthash_list': True,
            'assurance_requires_this_bound_workflow_driver_and_owned_chain': True,
        }
        result['blocking_static_findings'] = []
        result['static_review_completed'] = True
    finally:
        result['elapsed_seconds'] = time.monotonic() - started
        result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        result['bytes_streamed_for_identity'] = streamed
        need(result['elapsed_seconds'] <= budget['maximum_wall_seconds'], 'static audit wall budget exceeded')
        need(result['peak_RSS_bytes'] <= budget['maximum_RSS_bytes'], 'static audit RSS budget exceeded')
        data = (json.dumps(result, indent=2) + '\n').encode()
        need(len(data) <= budget['maximum_new_output_bytes'], 'static audit output budget exceeded')
        dest = HERE / 'R5_V5_FINAL_INDEPENDENT_STATIC_REVIEW.json'
        need(not dest.exists(), 'refuse overwrite of completed static review')
        dest.write_bytes(data)
        print(json.dumps({'output': str(dest), 'static_review_completed': result['static_review_completed'],
                          'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                          'seconds': result['elapsed_seconds'], 'peak_RSS_bytes': result['peak_RSS_bytes']}))


if __name__ == '__main__':
    main()
