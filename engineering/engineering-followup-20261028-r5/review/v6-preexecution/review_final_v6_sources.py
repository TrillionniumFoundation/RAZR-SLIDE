"""Final bounded static V6 readback: never imports model/checker geometry.

The explicit expected digests are supplied from the independently read final
lock, concrete workflow and basis. Source mathematics was reviewed separately;
this program binds that review to the actual payload and execution entry.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import resource
import signal
import time
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = ROOT / 'r5-envelope'
KNOWN = {
    'primitive_support_model_r5e_v6.py': 'c9026014433502ca83434b7296d249c3c889d3a8bcbcf0a0e65807f4704683a5',
    'primitive_refinement_r5e_v6.py': '11d0f8f72ba7e1db2936a7d7f2fcb9906f7f3eb426b4ad362e430ec41793bb57',
    'run_portable_primitive_r5e_v6.py': 'df9972a712433c6cb0f2e45589c725daf1c3876fd1888fba4a24522a3594ee1e',
    'verify_primitive_support_r5e_v6.py': '05f7d1d76096e0518943bbdfbf6d5da7ae6a91248f83ef6e98432ae168df29bd',
    'prepare_primitive_source_projection_r5e_v6.py': '31e193db399b01ee4e9376dd150fd851c1522fddbdb3b1cc936d79dd4bc7eb21',
    'R5E_V6_PRIMITIVE_SOURCE.json.gz': '1dfc953f6ef255ac8fdfe93d147c293049753b38c871ed4f4198bb5d089ba695',
    'R5E_V6_REAL_RETAINED_LEAF.json': '1e52b5f2021674f0e798aa97418ced7ceb0bdedd4fb7a08d1fc20a65ea136d5b',
    'R5E_V6_BASE_V5_INPUT_BRIDGE.json': '639dcb2d0d079dfd2e8356b1f096486a8f49c61aaeb2ecfd428988a0ab408335',
    'R5E_PORTABLE_SOURCE_LOCK_V5.json': 'd05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211',
}
REQUIRED = set(KNOWN) | {
    'R5E_PRIMITIVE_SUPPORT_V6_BASIS.md', 'R5E_V6_PRIMITIVE_SOURCE_RECEIPT.json',
    'exterior_channels_r5e_v3.py', 'verify_exterior_channels_r5e_v3.py',
    'verify_exterior_trim_r5e_v5.py', 'R5E_V5_PLANAR_TRIM_SOURCE.json.gz',
    'R5E_PUBLIC_INPUT_BRIDGE.json',
}
STAGES = [
    ('single-primitive-support-leaf', 'single_primitive_support_leaf'),
    ('verify-single', 'verify_single'),
    ('preflight-primitive-support', 'preflight_primitive_support'),
    ('all-primitive-support-frames', 'all_primitive_support_frames'),
    ('verify-all', 'verify_all'),
]
GATES = {
    'wall_seconds': 600, 'RSS_limit_bytes': 805306368,
    'shared_ceiling_bytes': 7301444403, 'disk_floor_bytes': 104857600,
    'expected_output_bytes': 41943040, 'maximum_output_bytes': 41943040,
    'metadata_margin_bytes': 4194304, 'zero_RSS_missing_observations_allowed': False,
}
ACTUAL_REL = 'engineering/engineering-followup-20261028-r5/envelope/actions/run-40645988108'
streamed = 0


def need(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    global streamed
    path = Path(path).resolve()
    with path.open('rb') as source:
        value = hashlib.sha256()
        while part := source.read(1 << 20):
            streamed += len(part)
            need(streamed <= 67108864, 'registered 64 MiB identity stream budget exceeded')
            value.update(part)
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': value.hexdigest()}


def members(root, records):
    need(len(records) == len({record['path'] for record in records}), 'duplicate locked input path')
    answers = []
    for record in records:
        path = (root / record['path']).resolve()
        need(path.is_relative_to(root.resolve()), 'locked input escapes its registered root')
        answer = identity(path)
        need(all(answer[key] == record[key] for key in ('bytes', 'sha256')), 'locked input content differs: ' + str(path))
        answers.append(answer)
    return answers


def assignment(tree, name):
    found = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    need(len(found) == 1, 'ambiguous static assignment: ' + name)
    return found[0]


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--workflow', type=Path, required=True)
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--expected-lock-sha', required=True)
    parser.add_argument('--expected-workflow-sha', required=True)
    parser.add_argument('--expected-template-sha', required=True)
    parser.add_argument('--expected-basis-sha', required=True)
    parser.add_argument('--r4-root', type=Path, default=ROOT / 'r4-envelope/public-final-v2')
    parser.add_argument('--base-v5-root', type=Path, default=ROOT / 'r5-ci-results/run-40645988108')
    args = parser.parse_args()
    for name in ('expected_lock_sha', 'expected_workflow_sha', 'expected_template_sha', 'expected_basis_sha'):
        need(re.fullmatch('[0-9a-f]{64}', getattr(args, name)), 'explicit final SHA-256 required: ' + name)
    destination = HERE / 'R5_V6_FINAL_INDEPENDENT_STATIC_REVIEW.json'
    need(not destination.exists(), 'new immutable final static report required')
    budget_path = HERE / 'R5_V6_FINAL_STATIC_REVIEW_BUDGET.json'
    budget = json.loads(budget_path.read_text())
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('registered 90 s final static review budget')))
    signal.alarm(90)
    started = time.monotonic()
    result = {
        'schema': 'razr-r5e-v6-independent-final-static-source-review',
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'execution_kind': 'static_source_and_identity_audit_only',
        'static_review_completed': False, 'V6_producer_executions': 0,
        'V6_checker_executions': 0, 'V6_model_control_executions': 0,
        'native_operations': 0, 'original_R4_proof_decodes': 0,
        'original_gate_admission_claimed': False, 'new_mathematical_qualification': False,
        'conditional_primitive_support_model_only': True, 'conditional_trim_model_only': True,
        'native_primitive_semantics_verified': False, 'native_trim_class_membership_verified': False,
        'inner_wire_hole_semantics_verified_for_native': False, 'original_raw_gate_reclassified': False,
        'full_continuous_G2': False, 'all_blockers_closed': False,
        'original_V3_raw_passes_unchanged': 4, 'actual_V4_failure_preserved': True,
        'actual_V5_conditional_passes_preserved': 8,
        'formal_V6_run_or_remote_publication_verified': False,
        'registered_budget': identity(budget_path), 'audit_source': identity(__file__),
    }
    try:
        reviewed = dict(KNOWN, **{'R5E_PRIMITIVE_SUPPORT_V6_BASIS.md': args.expected_basis_sha})
        trees = {}
        result['reviewed_source_identities'] = []
        for name, expected in reviewed.items():
            record = identity(SOURCE / name)
            need(record['sha256'] == expected, 'source changed after manual review: ' + name)
            result['reviewed_source_identities'].append(record)
            if name.endswith('.py'):
                trees[name] = ast.parse((SOURCE / name).read_text(), filename=name)
        result['python_sources_AST_parsed_without_import'] = sorted(trees)
        lock_path = SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V6.json'
        lock = json.loads(lock_path.read_text())
        result['source_lock'] = identity(lock_path)
        need(result['source_lock']['sha256'] == args.expected_lock_sha and lock['source_commit'] == 'c5f6606924937d716b007cd3ffa8e54df8ecfa5d', 'final V6 lock or original source anchor differs')
        need(lock['schema'] == 'razr-r5e-portable-source-lock-v6-primitive-support-conditioned' and
             lock['actual_V3_run_id'] == 40641230212 and lock['actual_V3_commit'] == '41333a369cbc44aab6fb5a723b75833a693ac16c' and
             lock['actual_V4_run_id'] == 40643098035 and lock['actual_V4_commit'] == '06e4f37690e2d5b9dc2abaf69cab9ba16957f1e2' and
             lock['actual_V5_run_id'] == 40645988108 and lock['actual_V5_commit'] == '2ce252f25d340b056bfd350bdde8c743f915c9a4', 'fixed prior actual run/head source anchors differ')
        need(lock['conditional_primitive_support_model_only'] is True and lock['conditional_trim_model_only'] is True and
             lock['native_primitive_semantics_verified'] is False and lock['native_trim_class_membership_verified'] is False and
             lock['original_raw_gate_reclassified'] is False and lock['V5_producer_rerun'] is False, 'source lock conditional scope differs')
        need(len(lock['r5_files']) == 25 and len(lock['r4_source_files']) == 3, 'complete final source census differs')
        need(REQUIRED <= {row['path'] for row in lock['r5_files']}, 'required source omitted from final V6 lock')
        result['locked_R5_members'] = members(SOURCE, lock['r5_files'])
        old_lock = json.loads((SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V5.json').read_text())
        need(lock['r4_source_files'] == old_lock['r4_source_files'], 'original owned supervisor/entry/process source changed')
        result['locked_original_owned_process_members'] = members(args.r4_root.resolve(), lock['r4_source_files'])
        # The full prior lock is checked as a source anchor; its prior runtime members stay byte-identical.
        result['unchanged_prior_V5_locked_R5_members'] = members(SOURCE, old_lock['r5_files'])
        bridge = json.loads((SOURCE / 'R5E_PUBLIC_INPUT_BRIDGE.json').read_text())
        need(bridge['source_commit'] == lock['source_commit'] and len(bridge['files']) == 19 and
             all(row['decoded_json_equal'] is True and not row['changed_strings'] for row in bridge['files']), 'original public bridge scope changed')
        result['original_public_input_identities_streamed_only'] = members(args.r4_root.resolve(), [dict(row['public_identity'], path=row['path']) for row in bridge['files']])
        actual_bridge = json.loads((SOURCE / 'R5E_V6_BASE_V5_INPUT_BRIDGE.json').read_text())
        need(actual_bridge['actual_run_id'] == 40645988108 and actual_bridge['actual_request_commit'] == '2ce252f25d340b056bfd350bdde8c743f915c9a4' and
             actual_bridge['public_repository_relative_root'] == ACTUAL_REL and actual_bridge['original_reports_or_certificates_edited'] is False and
             actual_bridge['path_mapping_only'] is True and len(actual_bridge['files']) == 25, 'actual V5 immutable bridge changed')
        result['actual_V5_archive_inputs_streamed_only'] = members(args.base_v5_root.resolve(), actual_bridge['files'])
        source_audit = HERE / 'R5_V6_INDEPENDENT_SOURCE_PROJECTION_AUDIT.json'
        result['independent_lossless_source_audit'] = identity(source_audit)
        need(result['independent_lossless_source_audit']['sha256'] == 'c59a9737848ebb64aafa03c1f943d7f2127fd210fe857bc4dca36756381daeca', 'independent original source audit changed')
        audit = json.loads(source_audit.read_text())
        need(audit['audit_completed'] is True and audit['new_mathematical_qualification'] is False, 'source-only audit scope differs')
        driver = trees['run_portable_primitive_r5e_v6.py']
        sequence = ast.literal_eval(assignment(driver, 'sequence'))
        need(sequence == STAGES, 'registered five-stage sequential order changed')
        result['registered_sequential_stages'] = sequence
        gate_node = assignment(driver, 'shared_base')
        need(isinstance(gate_node, ast.Dict), 'explicit original owned gate object required')
        gates = {key.value: ast.literal_eval(value) for key, value in zip(gate_node.keys, gate_node.values)
                 if isinstance(key, ast.Constant) and key.value in GATES}
        need(gates == GATES, 'original owned process gate changed')
        result['unchanged_original_owned_process_gates'] = gates
        workflow = args.workflow.resolve()
        template = args.template.resolve()
        result['concrete_workflow'] = identity(workflow)
        result['reviewed_workflow_template'] = identity(template)
        need(result['concrete_workflow']['sha256'] == args.expected_workflow_sha and result['reviewed_workflow_template']['sha256'] == args.expected_template_sha, 'final workflow/template bytes changed')
        actual_text = workflow.read_text()
        template_text = template.read_text()
        need(template_text.count('__FINAL_V6_LOCK_SHA__') == 1 and actual_text == template_text.replace('__FINAL_V6_LOCK_SHA__', args.expected_lock_sha), 'concrete workflow is not the one literal reviewed lock substitution')
        need('__FINAL_' not in actual_text, 'unbound workflow placeholder')
        fixed_actions = re.findall(r'uses:\s*([^\s]+)', actual_text)
        need(fixed_actions == ['actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1', 'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9'], 'fixed action commit changed')
        for fragment in [
            "branches: ['evidence/full-sprint-20261028-r5']",
            "- 'engineering/engineering-followup-20261028-r5/compute/RUN_REQUEST.json'",
            "if: github.repository == 'TrillionniumFoundation/RAZR-SLIDE' && github.ref == 'refs/heads/evidence/full-sprint-20261028-r5'",
            'permissions:\n  contents: read', 'persist-credentials: false', 'timeout-minutes: 55',
            'ref: ${{ github.sha }}', 'EXPECTED_HEAD: ${{ github.sha }}',
            'test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"',
            'R5E_PORTABLE_SOURCE_LOCK_V6.json', 'run_portable_primitive_r5e_v6.py',
            '--base-v5-root "$GITHUB_WORKSPACE/' + ACTUAL_REL + '"',
            '--r4-root "$GITHUB_WORKSPACE/engineering/engineering-followup-20261027-r4/envelope"',
            'if: always()', 'if-no-files-found: error', 'cancel-in-progress: false',
        ]:
            need(fragment in actual_text, 'required concrete workflow control missing: ' + fragment)
        sparse = actual_text.split('sparse-checkout: |', 1)[1].split('      - name:', 1)[0]
        need(set(line.strip() for line in sparse.splitlines() if line.strip()) == {
            'engineering/engineering-followup-20261027-r4/envelope',
            'engineering/engineering-followup-20261028-r5/compute', ACTUAL_REL}, 'complete sparse source/archive paths differ')
        need(actual_text.count('contents: read') == 1 and 'contents: write' not in actual_text and actual_text.count('permissions:') == 1, 'read-only workflow permission boundary changed')
        result['workflow_controls'] = {
            'repository': 'TrillionniumFoundation/RAZR-SLIDE', 'push_branch': 'evidence/full-sprint-20261028-r5',
            'job_exact_ref': 'refs/heads/evidence/full-sprint-20261028-r5',
            'push_trigger_path': 'engineering/engineering-followup-20261028-r5/compute/RUN_REQUEST.json',
            'manual_dispatch_subject_to_same_job_ref_guard': True, 'permissions': {'contents': 'read'},
            'credentials_persisted': False, 'checkout_exact_github_sha_checked_again_by_git': True,
            'fixed_actions': fixed_actions, 'timeout_minutes': 55, 'artifact_upload_after_failure': True,
            'immutable_actual_V5_archive_sparse_path_and_driver_argument': ACTUAL_REL,
            'source_lock_literal_sha256': args.expected_lock_sha,
            'maximum_five_worker_seconds': 3000, 'job_minus_worker_limit_margin_seconds': 300,
            'margin_is_not_a_guarantee_against_setup_or_artifact_timeout': True,
        }
        result['manual_math_and_execution_review'] = {
            'complete_original_UV_and_64_closed_patches': True, 'full_original_D_and_zero_width_carriers_retained': True,
            'Taylor_degree47_with_degree48_Lagrange_bound': True, 'exact_nonorthonormal_basis_dual_solved_independently': True,
            'closed_slabs_checked_against_open_channels': True, 'all12_unresolved_observations_reverified_before_cut': True,
            'deterministic_endpoint_or_explicit_radial_priority_midpoint': True,
            'new_exclusions_deducted_from_actual_V5_retained_sum_before_old_coarse_min': True,
            'all_pending_tiny_and_budget_stopped_leaves_retained': True,
            'prior_V5_certificates_reverified_with_prior_V5_limits': True,
            'single_positive_removal_original_TOL_and_independent_pass_precede_larger_stages': True,
            'failure_stops_later_stages': True,
            'resource_and_search_caps_are_finite_not_an_assertion_of_16_frame_success': True,
        }
        result['controls_reviewed_but_not_executed'] = {
            'mandatory_synthetic_positive_cases': ['complete_six_face_closed_box_exterior', 'exact_split_with_positive_tiny_leaf', 'complete_box_all_retained_no_excluded'],
            'mandatory_synthetic_negative_counts': {'channel': 4, 'split': 5, 'leaf': 2},
            'actual_case_negative_counts_when_applicable': {'phase': 3, 'root': 2, 'leaf': 2, 'channel': 4, 'split': 5, 'primitive_boundary': 6},
            'actual_positive_Taylor_remainder_deleted_and_original_value_saved': True,
            'absent_actual_channel_split_or_primitive_target_is_explicitly_not_applicable': True,
            'synthetic_controls_not_counted_as_actual_case_coverage': True,
            'prior_V4_or_V5_controls_not_relabelled_as_new_actual_V6_controls': True,
        }
        result['source_lock_rehash_scope'] = {
            'literal_lock_checked_at_workflow_entry': True,
            'driver_postchecks_all_locked_payloads_all19_public_inputs_and_all25_actual_V5_members': True,
            'lock_file_itself_is_not_in_driver_final_payload_posthash_list': True,
            'assurance_requires_this_exact_workflow_driver_and_owned_chain': True,
        }
        result['remaining_unproved_premises'] = [
            'Actual V6 execution, resource admission, control outcomes, resulting bounds and independent readback have not occurred.',
            'Native primitive membership and inherited trim/hole/corner-gap realization remain assumptions.',
            'Native compiled geometry/transform error, complete factory G2 and true independent mechanism domains remain open.',
            'Real specimen, original electrical/structural data and physical G3-G5 acceptance are not addressed by this mathematical source review.',
        ]
        result['blocking_static_findings'] = []
        result['static_review_completed'] = True
    except BaseException as exc:
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        result['elapsed_seconds'] = time.monotonic() - started
        result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        result['bytes_streamed_for_identity'] = streamed
        result['registered_budget_respected'] = result['elapsed_seconds'] <= budget['maximum_wall_seconds'] and result['peak_RSS_bytes'] <= budget['maximum_RSS_bytes'] and streamed <= budget['maximum_identity_stream_bytes']
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        encoded = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
        need(len(encoded) <= budget['maximum_new_output_bytes'], 'final static audit output budget exceeded')
        destination.write_bytes(encoded)
        print(json.dumps({key: result.get(key) for key in ('static_review_completed', 'elapsed_seconds', 'peak_RSS_bytes', 'bytes_streamed_for_identity', 'registered_budget_respected', 'failure')}))
    return 0 if result['static_review_completed'] and result['registered_budget_respected'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
