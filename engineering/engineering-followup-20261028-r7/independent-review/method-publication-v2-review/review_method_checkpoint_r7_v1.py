"""Bounded read-only review of the frozen 151-file method checkpoint.

No repository ref, selected original, transport, ledger, ZIP or native record
is written.  Only this new audit directory receives outputs.
"""
from pathlib import Path, PurePosixPath
import argparse
import collections
import datetime
import gzip
import hashlib
import io
import json
import re
import resource
import signal
import stat
import time
import traceback

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PLAN = OUT / 'R7_METHOD_CHECKPOINT_INDEPENDENT_REVIEW_PLAN_V1.json'
REPORT = OUT / 'R7_METHOD_CHECKPOINT_INDEPENDENT_REVIEW_V1.json'
LIMITS = {'wall_seconds': 30, 'address_space_bytes': 128 * 2**20,
          'total_read_and_decode_bytes': 256 * 2**20,
          'maximum_single_gzip_decoded_bytes': 16 * 2**20, 'maximum_report_bytes': 2 * 2**20}
REFS = {
    'manifest': 'r7-publication/method-checkpoint-v2/MANIFEST.json',
    'preparation_seal': 'r7-publication/method-checkpoint-v2/PREPARATION_SEAL.json',
    'summary': 'r7-publication/R7_METHOD_DIAGNOSTICS_AND_CURRENT_BLOCKERS_V1.md',
    'preparer_v1': 'r7-publication/prepare_method_checkpoint_publication_v1.py',
    'preparer_v2': 'r7-publication/prepare_method_checkpoint_publication_v2.py',
    'prior_remote_R7_tree': 'r7-publication/R7_NATIVE_FINITE_REMOTE_SUBTREE_READBACK_V1.json',
    'prior_verified_publication': 'r7-publication/R7_NATIVE_FINITE_REMOTE_PUBLICATION_VERIFIED_V1.json',
    'original_preparation_failure': 'r7-publication/method-checkpoint-v1/ACTUAL_FAILURE_V1.json',
    'edge_actual': 'r7-envelope/edge189-source-diagnostic-v1/attempt-1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_V1.json',
    'edge_tolerance_source_scope': 'r7-native/edge189-independent-v1/R7I_EDGE189_ORIGINAL_LINE_AND_TOLERANCE_SCOPE_REVIEW_V1.json',
    'positive_q': 'r7-audit/blocker-ledger/positive-q-source-readback/R7_POSITIVE_Q_SOURCE_AND_FACTORY_MAPPING_READBACK_V1.json',
    'ledger_V2': 'r7-audit/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_V2.json',
    'numeric_original_scope': 'razr-current/engineering/engineering-followup-20261028-r5/numerics/R5_ORIGINAL_NUMERIC_QUALIFICATION_SCOPE.json',
    'method_saved': 'r7-deliverables/R7_METHOD_COMPLETE_PRESERVATION_V1.json',
    'catalog_saved': 'r7-publication/R7_SCIENTIFIC_CATALOG_SAVED_V2.json',
}
read_bytes = 0
PATTERNS = {
    'private_key_material': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'GitHub_credential_literal': rb'\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,})\b',
    'AWS_access_key_literal': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'OpenAI_credential_literal': rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b',
    'signed_or_credential_URL_parameter': rb'(?i)(?:[?&])(?:x-amz-signature|x-goog-signature|access_token|api_key|sig)=([^\s\"<>\\]{12,})',
    'long_Bearer_credential_literal': rb'(?i)\bBearer[ \t]+[A-Za-z0-9._~+/-]{30,}',
}


class BudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def charge(n):
    global read_bytes
    read_bytes += n
    need(read_bytes <= LIMITS['total_read_and_decode_bytes'], 'Registered small-review byte budget exceeded')


def raw(path):
    need(path.is_relative_to(BASE) and stat.S_ISREG(path.lstat().st_mode), 'Expected a regular workspace original/transport')
    value = path.read_bytes()
    charge(len(value))
    return value


def identity(value):
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest(),
            'git_blob_sha': hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest()}


def file_identity(path):
    return identity(raw(path))


def source_id(path):
    return {'path': str(path), **file_identity(path)}


def save(path, value):
    data = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    need(len(data) <= LIMITS['maximum_report_bytes'], 'Registered audit output cap exceeded')
    need(not path.exists(), 'New immutable review artifact required')
    with path.open('xb') as stream:
        stream.write(data)
    return identity(data)


def load(name):
    return json.loads(raw(BASE / REFS[name]))


def safe_repo_path(path, prefix):
    p = PurePosixPath(path)
    return not p.is_absolute() and str(p) == path and '..' not in p.parts and path.startswith(prefix)


def tree_hash_from_blobs(blobs):
    dirs = {'': {}}
    for path, row in blobs.items():
        parts = path.split('/')
        parent = ''
        for name in parts[:-1]:
            child = parent + ('/' if parent else '') + name
            entry = dirs.setdefault(parent, {}).get(name)
            need(entry is None or entry['type'] == 'tree', 'A blob conflicts with a projected directory')
            dirs[parent][name] = {'type': 'tree', 'child': child}
            dirs.setdefault(child, {})
            parent = child
        need(parts[-1] not in dirs[parent], 'Duplicate or ancestor-conflicting projected blob')
        dirs[parent][parts[-1]] = {'type': 'blob', 'mode': row['mode'], 'sha': row['sha']}
    hashes = {}
    for path in sorted(dirs, key=lambda x: (x.count('/'), len(x)), reverse=True):
        payload = bytearray()
        entries = sorted(dirs[path].items(), key=lambda pair: pair[0].encode() + (b'/' if pair[1]['type'] == 'tree' else b''))
        for name, row in entries:
            mode = '40000' if row['type'] == 'tree' else row['mode'].lstrip('0')
            sha = hashes[row['child']] if row['type'] == 'tree' else row['sha']
            payload += mode.encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(sha)
        hashes[path] = hashlib.sha1(b'tree ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    return hashes


def plan():
    manifest = load('manifest')
    need(file_identity(BASE / REFS['manifest'])['sha256'] == '19c591f3f48af446215a79852149e75be14d9e0a73bfebc3f4db10f5a68f5872', 'Requested frozen manifest identity differs')
    need(len(manifest['files']) == manifest['new_file_count'] == 151, 'Frozen payload count differs')
    value = {'schema': 'razr-r7-method-checkpoint-independent-review-plan-v1',
             'registered_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'source': source_id(Path(__file__)), 'limits': LIMITS,
             'exact_original_reference_identities': {name: source_id(BASE / rel) for name, rel in REFS.items()},
             'selected_original_bytes': manifest['selected_original_bytes'],
             'selected_transport_bytes': sum(row['transport_identity']['bytes'] for row in manifest['files']),
             'selected_payload_rows': 151,
             'scope': 'Read only the frozen selected files/transports and listed evidence; hash bytes/Git blobs, completely decompress gzip, check unique and ancestor-safe destinations, reconstruct pinned prior/projected Git tree identities, and review stated scientific/privacy scope.',
             'ZIP_or_workspace_full_scan_authorized': False, 'remote_ref_mutation_authorized_by_this_reader': False,
             'selected_originals_or_frozen_manifest_modified': False}
    found = save(PLAN, value)
    print(json.dumps({'plan': str(PLAN), **found}))


def review():
    started = time.monotonic()
    registered = json.loads(raw(PLAN))
    need(registered['source'] == source_id(Path(__file__)) and registered['limits'] == LIMITS, 'Registered audit source/limits changed')
    refs = registered['exact_original_reference_identities']
    for value in refs.values():
        need(source_id(Path(value['path'])) == value, 'Frozen review input changed before execution')
    manifest, seal, prior = load('manifest'), load('preparation_seal'), load('prior_remote_R7_tree')
    prefix = manifest['repository_prefix']
    need(seal['manifest'] == file_identity(BASE / REFS['manifest']), 'Preparation seal binds different manifest')
    parent = load('prior_verified_publication')
    need(manifest['parent_commit'] == parent['commit'] == '34764db3c8d61d6e53ea22da8caf4dc57b931463'
         and manifest['base_tree'] == parent['root_tree'] == '1195ca799d551a53f7c27b8ff3a175cca19cb8fb', 'Parent publication binding differs')
    need(prior['sha'] == parent['R7_tree'] == '6e98caa0292d3145215f8675b8c1115bd8686da8' and not prior['truncated'], 'Pinned complete prior subtree differs')
    old_blobs = {row['path']: row for row in prior['tree'] if row['type'] == 'blob'}
    need(len(old_blobs) == manifest['prior_R7_blob_count'] == 767, 'Expected full prior767 blob inventory')
    old_hashes = tree_hash_from_blobs(old_blobs)
    need(old_hashes[''] == prior['sha'], 'Prior complete tree object cryptographic reconstruction differs')
    for row in prior['tree']:
        if row['type'] == 'tree':
            need(old_hashes[row['path']] == row['sha'], 'Pinned prior child tree identity differs')
    payload = manifest['files']
    dests = [row['repository_path'] for row in payload]
    need(len(set(dests)) == len(payload) == 151 and not manifest['unchanged_existing_originals_not_republished'], 'Frozen unique payload count differs')
    records = []
    policy_findings = []
    token_findings = []
    scanned_hashes = set()
    decoded_gzip_records = []
    original_bytes = 0
    transport_bytes = 0
    proposed = dict(old_blobs)
    def scan(label, data):
        signature = hashlib.sha256(data).hexdigest()
        if signature in scanned_hashes:
            return
        scanned_hashes.add(signature)
        for name, pattern in PATTERNS.items():
            for match in re.finditer(pattern, data):
                token_findings.append({'input_label': label, 'pattern': name, 'byte_offset': match.start(),
                                       'matched_value_sha256_not_literal': hashlib.sha256(match.group()).hexdigest()})
    for row in payload:
        dest = row['repository_path']
        original_path, transport_path = Path(row['original_path']), Path(row['transport_path'])
        need(safe_repo_path(dest, prefix) and safe_repo_path(row['original_repository_path'], prefix), 'Unsafe/out-of-prefix destination')
        rel = dest.removeprefix(prefix)
        need(rel not in old_blobs, 'A selected payload overwrites a prior blob')
        forbidden_parts = {'r7-private-helpers', '.aws', '.ssh', '.env', '.codex', '.agents'}
        if ('.private.' in original_path.name or forbidden_parts.intersection(original_path.parts)
            or original_path.suffix == '.pyc' or '__pycache__' in original_path.parts):
            policy_findings.append({'path': str(original_path), 'reason': 'Private/helper/credential/runtime-only path selected'})
        if 'cylinder' in original_path.name.lower() or 'cylinder-' in str(original_path).lower():
            policy_findings.append({'path': str(original_path), 'reason': 'Unexecuted next Cylinder directory/file selected'})
        original, transport = raw(original_path), raw(transport_path)
        original_id, transport_id = identity(original), identity(transport)
        need(original_id == row['original_identity'] and transport_id == row['transport_identity'], 'Selected original/transport identity differs')
        original_bytes += len(original)
        transport_bytes += len(transport)
        representation = row['representation']
        if representation == 'lossless_gzip_original':
            expected_dest = prefix + 'method-original-gzip/' + row['original_repository_path'].removeprefix(prefix) + '.gz'
            need(dest == expected_dest, 'New gzip is outside collision-isolated destination namespace')
            with gzip.GzipFile(fileobj=io.BytesIO(transport)) as stream:
                decoded = stream.read(LIMITS['maximum_single_gzip_decoded_bytes'] + 1)
            charge(len(decoded))
            need(len(decoded) <= LIMITS['maximum_single_gzip_decoded_bytes'] and decoded == original, 'Complete gzip roundtrip differs')
            decoded_gzip_records.append({'destination': dest, 'decoded_identity': identity(decoded),
                                         'complete_roundtrip_to_selected_original': True})
        elif representation == 'exact_original':
            need(dest == row['original_repository_path'] and original == transport, 'Exact-original transport differs')
            if original.startswith(b'\x1f\x8b'):
                with gzip.GzipFile(fileobj=io.BytesIO(original)) as stream:
                    decoded = stream.read(LIMITS['maximum_single_gzip_decoded_bytes'] + 1)
                charge(len(decoded))
                need(len(decoded) <= LIMITS['maximum_single_gzip_decoded_bytes'], 'Original gzip decoded size exceeded bounded review')
                decoded_gzip_records.append({'destination': dest, 'decoded_identity': identity(decoded),
                                             'exact_original_gzip_integrity_read': True})
                scan(dest + '::decompressed', decoded)
        else:
            raise ValueError('Unknown representation')
        scan(dest + '::original', original)
        if row['content_kind'] == 'text':
            need(b'\0' not in transport, 'Text payload contains NUL')
            transport.decode('utf-8')
        else:
            need(row['content_kind'] == 'binary', 'Unknown text/binary content classification')
        proposed[rel] = {'path': rel, 'type': 'blob', 'mode': '100644',
                         'sha': transport_id['git_blob_sha'], 'size': transport_id['bytes']}
        records.append({'repository_path': dest, 'original_path': str(original_path),
                        'original_identity': original_id, 'transport_path': str(transport_path),
                        'transport_identity': transport_id, 'representation': representation,
                        'content_kind': row['content_kind'], 'complete_bytes_verified': True})
    need(original_bytes == manifest['selected_original_bytes'] == 15563173, 'Selected original byte sum differs')
    need(transport_bytes == seal['new_transport_bytes'] == 5856208, 'Selected transport byte sum differs')
    need(sum(row['content_kind'] == 'binary' for row in payload) == seal['new_binary_files'] == 9, 'Binary row count differs')
    projected_hashes = tree_hash_from_blobs(proposed)
    need(all(proposed[key] == value for key, value in old_blobs.items()), 'A prior blob mode/identity/path changed in projection')
    binary_groups = collections.defaultdict(list)
    for row in records:
        if row['content_kind'] == 'binary':
            binary_groups[row['transport_identity']['git_blob_sha']].append(row['repository_path'])
    need(len(binary_groups) == 5 and sum(len(v) == 2 for v in binary_groups.values()) == 4, 'Expected four reused gzip object identities')
    first_failure = load('original_preparation_failure')
    need(first_failure['exit_code'] == 1 and not first_failure['manifest_written'] and not first_failure['remote_mutation'], 'Original collision failure was reclassified')
    need(first_failure['source_sha256'] == file_identity(BASE / REFS['preparer_v1'])['sha256'], 'Original failed source identity differs')
    need(len(first_failure['partial_transport_files']) == 4 and sum(row['bytes'] for row in first_failure['partial_transport_files']) == 1682204, 'Original partial files differ')
    for row in first_failure['partial_transport_files']:
        need({k: file_identity(Path(row['path']))[k] for k in ('bytes', 'sha256')} == {k: row[k] for k in ('bytes', 'sha256')}, 'Preserved original partial gzip changed')
        need(any(p['original_path'] == row['path'] for p in payload), 'Original preparation failure partial omitted from publication')
    need(any(p['original_path'] == str(BASE / REFS['original_preparation_failure']) for p in payload), 'Original failure receipt omitted')
    edge, q, ledger, numeric = load('edge_actual'), load('positive_q'), load('ledger_V2'), load('numeric_original_scope')
    source_scope = load('edge_tolerance_source_scope')
    need(edge['source_child_cumulative_depth'] == 25 and not edge['original_V6_depth_gate_passed']
         and edge['fixed_whole_channel_result']['conditional_source_model_open_interior_excluded']
         and not edge['native_BREP_error_bound_certified'] and not edge['full_continuous_G2'], 'Line local/conditional scope differs')
    need(not source_scope['compiled_OCCT_binary_equivalence_proved'], 'Original source-only OCP qualification scope differs')
    need(not ledger['all_blockers_closed'] and not ledger['full_continuous_G2'] and not ledger['current_K1_K3_FE_qualified']
         and not any(ledger['physical_gate_pass'].values()), 'Overall blocker scope differs')
    need(ledger['numerical_original_scope_detail']['panel_five_ratios'] == numeric['panel_original_five_residuals']
         and not ledger['numerical_original_scope_detail']['independent_all_7770_recomputation_added_as_a_new_required_gate'], 'Original numerical scope changed')
    need(len(q['four_profiles']) == 4 and not q['new_continuous_G2_strength_manufacturing_or_G3_G5_qualification'], 'Positive-q source scope differs')
    for pose in ('near', 'far'):
        need(q['two_actual_pose_report_mappings'][pose]['actual_factory_q_by_side_mm'] == ledger['finite_pose_scope'][pose]['actual_q_by_side_mm'], 'Positive-q and actual finite-pose mapping differs')
    summary = raw(BASE / REFS['summary']).decode()
    for literal in ('depth 25', 'The original V6 depth limit is 24', 'not contained in the original AABB',
                    'not a KEY travel upper bound', 'No actual pass is recorded', 'all_blockers_closed = false'):
        need(literal in summary, 'Expected visible scope qualification missing: ' + literal)
    saved, catalog = load('method_saved'), load('catalog_saved')
    need(saved['saved_file']['status'] == 'succeeded' and saved['full_zip_members'] == 535
         and saved['bytes'] == 53293490 and saved['sha256'] == '709500f8d11e3c4a98114de5777ab3a7605d0a324169fb74054cd6b5e1a77b9d', 'Saved complete method identity differs')
    need(catalog['saved_file']['status'] == 'succeeded' and catalog['file_count'] == 65
         and catalog['previous_59_entries_unchanged'] and catalog['saved_file']['current_version_number'] == 1, 'Saved scientific catalog scope differs')
    for value in refs.values():
        need(source_id(Path(value['path'])) == value, 'Bound review reference changed during read')
    for row in records:
        need(file_identity(Path(row['original_path'])) == row['original_identity']
             and file_identity(Path(row['transport_path'])) == row['transport_identity'], 'A selected original/transport changed during read')
    report = {'schema': 'razr-r7-method-checkpoint-independent-prepublication-review-v1',
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'plan': source_id(PLAN), 'source': registered['source'], 'limits': LIMITS,
        'original_references': refs, 'reviewed_payload_count': 151,
        'selected_original_bytes': original_bytes, 'transport_bytes': transport_bytes,
        'all_selected_original_and_transport_bytes_SHA256_and_Git_blob_SHA_verified': True,
        'all_selected_bytes_unchanged_before_after': True,
        'complete_per_payload_readback': records,
        'complete_gzip_readbacks': decoded_gzip_records,
        'representation_counts': dict(collections.Counter(row['representation'] for row in payload)),
        'binary_rows': 9, 'unique_binary_Git_blob_objects': 5, 'four_reused_gzip_object_destinations': dict(binary_groups),
        'all_destinations_unique_prefix_safe_and_ancestor_collision_free': True,
        'prior_remote_tree_snapshot_is_complete': True,
        'prior767_blob_and209_child_tree_hashes_reconstructed_from_complete_snapshot': True,
        'prior_R7_tree_reconstructed_SHA': old_hashes[''],
        'prior767_paths_modes_sizes_and_blob_SHA_preserved_in_projected_append_tree': True,
        'all_prior_blob_records_preserved': old_blobs,
        'payload_only_projected_R7_tree_SHA': projected_hashes[''],
        'payload_only_projected_blob_count': len(proposed),
        'projected_tree_excludes_future_publication_manifest_seal_and_audit_metadata_additions': True,
        'remote_ref_update_executed_or_final_remote_tree_verified_by_this_audit': False,
        'private_helper_or_out_of_scope_path_findings': policy_findings,
        'known_secret_material_pattern_findings_redacted': token_findings,
        'privacy_scan_scope': 'All selected original bytes and every original gzip decoded content; exact-original copies/filters may mention private paths, but no private recovery container or private helper path is selected. Engineering opaque Library IDs and public official-source URLs are intentional provenance, not credential findings.',
        'scientific_scope_review': {
            'native_results_remain_two_finite_current_candidate_poses_same_kernel': True,
            'original_numeric_qualification_keeps_original_K_b_C_and_saved_action_scope': True,
            'new_full7770_K_recomputation_not_added_as_required_gate': True,
            'Line_result_only_original_depth25_low_child_fixed_channel_conditional_source_open_interior': True,
            'original_depth24_V9_u_owned_and_full16_not_promoted': True,
            'hypothetical_tube_not_in_original_B_and_native_error_cert_false_retained': True,
            'positive_q_lower_stop_height_transition_not_KEY_travel_bound_or_real_contact': True,
            'true_physical_domain_current_FE_and_G3_G5_not_qualified': True,
            'new_Cylinder_preparation_excluded': True,
            'exact_a11_push_not_claimed': True,
        },
        'nonblocking_wording_and_source_precision_clarifications': [
            {'location': 'README Complete evidence and storage state', 'original_wording': 'after verified redundant copies were recovered',
             'clarification': 'Read as capacity reclaimed by verified redundant-cache migration/removal. No deleted unique scientific original was restored or recreated, and original failures remain failed.'},
            {'location': 'README tolerance accessor statement',
             'clarification': 'The Confusion-floor statement is established for the pinned official OCCT source reviewed in the included original scope report. compiled_OCCT_binary_equivalence_proved remains false; no installed OCP binary-equivalence or native point-error certificate is conferred.'},
        ],
        'original_preparation_failure_and_all_four_partial_gzips_preserved': True,
        'V2_collision_fix_uses_separate_method_original_gzip_namespace': True,
        'original_failure_reclassified': False,
        'no_private_or_secret_material_detected_in_bounded_selected_review': not policy_findings and not token_findings,
        'prepublication_payload_review_pass_with_stated_scope_clarifications': not policy_findings and not token_findings,
        'selected_originals_manifest_ledger_or_ref_modified': False,
        'ZIP_read_or_workspace_full_scan_performed': False,
        'new_scientific_algorithm_or_geometry_execution': False,
        'actual_read_and_decode_bytes': read_bytes, 'elapsed_seconds': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'full_continuous_G2': False, 'all_blockers_closed': False}
    found = save(REPORT, report)
    print(json.dumps({'report': str(REPORT), **found,
        'review_pass': report['prepublication_payload_review_pass_with_stated_scope_clarifications'],
        'private_path_findings': len(policy_findings), 'secret_pattern_findings': len(token_findings),
        'payload_only_projected_R7_tree_SHA': projected_hashes[''],
        'seconds': report['elapsed_seconds'], 'peak_RSS_bytes': report['peak_RSS_bytes'], 'read_and_decode_bytes': read_bytes}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    need(args.plan != args.execute, 'Choose registration or actual review')
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['address_space_bytes'], LIMITS['address_space_bytes']))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(BudgetExceeded('Registered 30-second review exceeded')))
    signal.alarm(LIMITS['wall_seconds'])
    try:
        plan() if args.plan else review()
        return 0
    except BaseException as exc:
        failure = {'schema': 'razr-r7-method-checkpoint-independent-review-actual-failure-v1',
                   'stage': 'plan' if args.plan else 'actual', 'type': type(exc).__name__,
                   'message': str(exc), 'traceback': traceback.format_exc(),
                   'source': source_id(Path(__file__)), 'originals_or_manifest_changed': False,
                   'new_scientific_execution': False, 'remote_mutation': False}
        save(OUT / ('PLAN_FAILURE_V1.json' if args.plan else 'ACTUAL_FAILURE_V1.json'), failure)
        print(json.dumps(failure))
        return 2
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    raise SystemExit(main())
