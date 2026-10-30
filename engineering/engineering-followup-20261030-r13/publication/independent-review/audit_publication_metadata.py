"""Read-only final publication-metadata audit. No science/tests/network writes."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('/workspace/scratch/1b842ca762be/RAZR-SLIDE')
REL = Path('engineering/engineering-followup-20261030-r13')
R13 = ROOT / REL
PUB = R13 / 'publication'
OUTDIR = Path(__file__).resolve().parent
OUT = OUTDIR / 'R13_PUBLICATION_METADATA_INDEPENDENT_REVIEW.json'
P = 'd77d4c87de8362534f0fb57376114f6bf54a0da5'
A = 'cd703749886f7d2c040f80284d0fb07b368b5f9b'
T = 'c82cffaf61ce18ac04b175fe1418ce094d2603b7'
B = 'ab9ef3270a9a0d0d28f605f7188038db133dbcd8'
ENTRYPOINTS = ['CURRENT_DESIGN.md', 'design/current_product.json', 'docs/RESEARCH_OVERVIEW.md', 'status.json']


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def identity(p):
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}


def bind(row, p=None):
    p = ROOT / row['path'] if p is None else p
    assert p.is_file() and p.stat().st_size == row['bytes'], str(p)
    assert sha(p) == row['sha256'], str(p)


def git(*args, data=None):
    return subprocess.run(['git', *args], cwd=ROOT, input=data, check=True, capture_output=True).stdout


def ls_tree(commit):
    result = {}
    for item in git('ls-tree', '-r', '-z', commit).split(b'\0'):
        if not item:
            continue
        meta, name = item.split(b'\t', 1)
        mode, typ, oid = meta.decode().split()
        result[name.decode()] = {'mode': mode, 'type': typ, 'sha': oid}
    return result


receipt = read(PUB / 'R13_SCIENCE_PUBLICATION_READBACK.json')
plan = read(PUB / 'R13-science/PUBLICATION_PLAN.json')
api = read(PUB / 'R13-science/TREE_COMMIT_REF_RECEIPT.json')
assert git('rev-parse', 'HEAD').decode().strip() == P
assert git('rev-parse', 'refs/remotes/origin/evidence/full-sprint-20261030-r13').decode().strip() == P
assert receipt['local_science_commit'] == plan['local_target_commit'] == api['local_commit'] == A
assert receipt['published_science_commit'] == api['remote_commit'] == P
assert receipt['source_tree'] == plan['expected_tree'] == api['tree'] == T
assert receipt['base_commit'] == plan['base_commit'] == api['base_commit'] == B
for commit in (A, P):
    assert git('show', '-s', '--format=%T %P', commit).decode().strip().split() == [T, B]
assert git('diff', '--raw', A, P) == b''
for k in ('source_trees_identical', 'all_content_diff_empty', 'parent_order_verified', 'actual_Git_fetch_completed', 'fetched_remote_branch_head_matches'):
    assert receipt[k] is True
assert receipt['commit_metadata_identical'] is False
assert receipt['scientific_or_physical_release_changed_by_publication'] is False
for k in ('original_local_commit_raw_bytes', 'exact_publication_plan', 'recording_source'):
    bind(receipt[k])
raw = (ROOT / receipt['original_local_commit_raw_bytes']['path']).read_bytes()
assert hashlib.sha1(b'commit ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == A
assert raw == git('cat-file', 'commit', A)
assert len(raw) == plan['original_local_commit_bytes']
assert hashlib.sha256(raw).hexdigest() == plan['original_local_commit_sha256']

# Check final reachable files independently of the upload-job batching.
base_tree, published_tree = ls_tree(B), ls_tree(P)
changes = {p: item for p, item in published_tree.items() if base_tree.get(p) != item}
deleted = sorted(set(base_tree) - set(published_tree))
planned = {row['path']: {k: row[k] for k in ('mode', 'type', 'sha')} for row in plan['files']}
assert len(planned) == len(plan['files']) == len(changes) == plan['changed_files'] == 348
assert planned == changes and deleted == plan['deleted_files'] == []
added = sum(p not in base_tree for p in changes)
modified = len(changes) - added
assert (added, modified) == (plan['added_files'], plan['modified_files']) == (344, 4)
all_blob_ids = {row['sha'] for row in changes.values()}
base_blob_ids = {row['sha'] for row in base_tree.values() if row['type'] == 'blob'}
new_blob_ids = all_blob_ids - base_blob_ids
assert len(all_blob_ids) == 295 and len(new_blob_ids) == plan['unique_new_blobs'] == 263
batch = git('cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)', data=('\n'.join(sorted(all_blob_ids)) + '\n').encode())
sizes = {}
for line in batch.decode().splitlines():
    oid, typ, size = line.split()
    assert typ == 'blob'
    sizes[oid] = int(size)
assert sum(sizes[r['sha']] for r in changes.values()) == plan['changed_content_bytes'] == receipt['changed_content_bytes'] == 14424290

upload_rows = []
assert len(receipt['object_receipts']) == receipt['new_object_upload_jobs_verified'] == plan['upload_jobs'] == 31
for index, row in enumerate(receipt['object_receipts']):
    bind(row)
    item = read(ROOT / row['path'])
    assert item['seq'] == index
    assert item['returned_sha'] == item['expected_sha'] and item['exact_identity_match'] is True
    assert item['repository'] == 'TrillionniumFoundation/RAZR-SLIDE'
    assert item['branch_ref_updated'] is False
    if item['kind'] == 'blob':
        assert item['expected_sha'] in new_blob_ids
        assert changes[item['source_path']]['sha'] == item['expected_sha']
        assert sizes[item['expected_sha']] == item['source_bytes']
    else:
        assert item['kind'] == 'text_tree' and item['text_blob_count'] > 0
    upload_rows.append(item)
kind_counts = Counter(row['kind'] for row in upload_rows)
assert kind_counts == Counter({'blob': 25, 'text_tree': 6})
assert len({row['expected_sha'] for row in upload_rows if row['kind'] == 'blob'}) == 25
assert 25 + sum(row['text_blob_count'] or 0 for row in upload_rows) == len(new_blob_ids)
assert sum(row['source_bytes'] for row in upload_rows) == sum(sizes[oid] for oid in new_blob_ids) == 4189717
intermediate_trees_present = []
for row in upload_rows:
    if row['kind'] == 'text_tree':
        result = subprocess.run(['git', 'cat-file', '-e', row['expected_sha']], cwd=ROOT, capture_output=True)
        if result.returncode == 0:
            intermediate_trees_present.append(row['expected_sha'])

# Only four tracked current entrypoints changed after P. All tracked science,
# reproduction supplements and previous independent reviews stay byte-identical.
tracked_changes = set(git('diff', '--name-only', P).decode().splitlines())
assert tracked_changes == set(ENTRYPOINTS)
ledger = read(R13 / 'R13_COMPLETED_WORK_LEDGER.json')
assert len(ledger['bound_records']) == 31
for row in ledger['bound_records']:
    bind(row)
    assert git('show', P + ':' + row['path']) == (ROOT / row['path']).read_bytes()
assert all(v is False for v in ledger['release'].values())
assert ledger['publication_at_science_seal']['R13_publication_not_yet_claimed_by_this_science_record'] is True
assert ledger['publication_at_science_seal']['R12_remote_commit'] == B
assert (R13 / 'R13_COMPLETED_WORK_LEDGER.json').read_bytes() == git('show', P + ':' + str(REL / 'R13_COMPLETED_WORK_LEDGER.json'))

sync = read(R13 / 'status/R13_PUBLICATION_ENTRYPOINT_SYNC_RESULT.json')
assert {r['path'] for r in sync['source_and_outputs']} == set(ENTRYPOINTS)
for row in sync['source_and_outputs']:
    bind(row)
bind(sync['science_ledger_identity'])
bind(sync['published_science_receipt'])
assert len(sync['runs']) == 2 and all(r['returncode'] == 0 and r['stderr'] == '' for r in sync['runs'])
assert json.loads(sync['runs'][1]['stdout']) == {'mode': 'check', 'changed': []}
assert sync['source_reports_and_native_or_physical_release_changed'] is False
assert sync['new_test_or_science_execution'] is False

old = json.loads(git('show', P + ':design/current_product.json'))
current = read(ROOT / 'design/current_product.json')
changed_keys = {k for k in set(old) | set(current) if old.get(k) != current.get(k)}
expected_changed_keys = {'stage_summary', 'work_packages', 'publication_record', 'publication_record_scope', 'active_followup', 'updated_utc', 'r13_science_seal_publication_state', 'current_publication_sync_r13'}
assert changed_keys == expected_changed_keys
assert current['r13_science_seal_publication_state'] == {k: old[k] for k in ('publication_record', 'publication_record_scope', 'stage_summary')}
assert current['stage_summary'] == old['stage_summary'].replace('R12 is publicly verified with exact source-tree equivalence.', 'R12 and R13 science are publicly verified with exact source-tree equivalence.')
old_active, active = old['active_followup'], current['active_followup']
active_changes = {k for k in set(old_active) | set(active) if old_active.get(k) != active.get(k)}
assert active_changes == {'new_branch_pushed', 'containing_commit_scope', 'published_science_commit', 'published_science_tree', 'science_publication_readback'}
assert old_active['new_branch_pushed'] is False and active['new_branch_pushed'] is True
assert active['published_science_commit'] == P and active['published_science_tree'] == T
assert active['science_publication_readback'] == current['publication_record'] == str(REL / 'publication/R13_SCIENCE_PUBLICATION_READBACK.json')
assert len(old['work_packages']) == len(current['work_packages'])
changed_wp = [a['id'] for a, b in zip(old['work_packages'], current['work_packages']) if a != b]
assert changed_wp == ['WP9']
for obj in (current, active, read(ROOT / 'status.json')):
    assert all(obj[k] is False for k in ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go'))
status = read(ROOT / 'status.json')
old_status = json.loads(git('show', P + ':status.json'))
assert {k for k in set(status) | set(old_status) if status.get(k) != old_status.get(k)} == {'current_product_stage', 'current_work_packages'}
assert status['current_product_stage'] == current['stage_summary']
assert status['current_work_packages'] == current['work_packages']
assert status['current_fresh_verification'] == old_status['current_fresh_verification'] == current['verification_summary']
for name in ('CURRENT_DESIGN.md', 'docs/RESEARCH_OVERVIEW.md'):
    text = (ROOT / name).read_text()
    assert current['stage_summary'] in text and current['verification_summary'] in text

# Retain attempt 1's source/receipt identity without resolving its historical
# source path to the replacement source from attempt 2.
attempt = PUB / 'finalization-attempt1'
failed = read(attempt / 'FAILURE_AND_RECOVERY.json')
first_receipt = read(attempt / 'R13_SCIENCE_PUBLICATION_READBACK.json')
bind(first_receipt['recording_source'], attempt / 'finalize_science_publication.py')
assert 'FileNotFoundError' in failed['terminal_failure'] and 'Sparse checkout' in failed['terminal_failure']
assert failed['actual_science_publication_and_Git_readback_succeeded'] is True
assert failed['metadata_update_and_generated_entrypoint_sync_executed_before_failure'] is True
assert failed['science_results_or_release_flags_changed'] is False
assert failed['materialized_ledger_sha256'] == sha(R13 / 'R13_COMPLETED_WORK_LEDGER.json')
assert {k for k in set(first_receipt) | set(receipt) if first_receipt.get(k) != receipt.get(k)} == {'verified_utc', 'recording_source'}
assert sha(attempt / 'finalize_science_publication.py') != sha(PUB / 'finalize_science_publication.py')
assert "if 'r13_science_seal_publication_state' not in x:" in (PUB / 'finalize_science_publication.py').read_text()

report = {
    'schema': 'razr-r13-independent-final-publication-metadata-review-v1',
    'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
    'review_source': identity(Path(__file__).resolve()),
    'completed': True,
    'concrete_consistency_defects_found': [],
    'scope': 'Read-only publication metadata, saved receipts, existing local Git object identity, and current-entrypoint/unchanged-science comparison. No CAD, numerical solve or product, scientific producer, unit tests, network request, Git mutation or repository write.',
    'science_publication_identity': {'original_local_commit': A, 'published_commit': P, 'source_tree': T, 'common_parent': B, 'trees_and_parent_match_existing_fetched_Git_objects': True, 'local_original_commit_reconstructed_from_retained_raw_bytes': True, 'commit_metadata_identical': False, 'fetched_remote_tracking_ref_at_review': P},
    'publication_plan': {'changed_file_paths': 348, 'added': 344, 'modified': 4, 'deleted': 0, 'changed_content_bytes': 14424290, 'unique_changed_blob_ids': 295, 'unique_new_blob_ids_relative_to_R12': 263, 'reused_R12_blob_ids': 32, 'unique_new_blob_bytes': 4189717, 'all_348_exact_path_mode_type_blob_id_records_match_published_tree': True},
    'upload_job_receipts': {'total': 31, 'direct_blob_jobs': 25, 'batch_text_tree_jobs': 6, 'text_blob_count_sum': 238, 'all_receipt_SHA256_lengths_and_returned_expected_SHA_pairs_match': True, 'all_25_direct_blobs_present_in_fetched_final_tree': True, 'intermediate_batch_tree_objects_present_in_local_fetched_object_store': len(intermediate_trees_present), 'scope_boundary': 'The six temporary upload trees are intermediate job objects, not final science files. Their saved API receipts are checked; their remote existence is not independently re-queried in this review. The final reachable tree contains all planned blobs and matches the exact target tree.'},
    'science_immutability': {'root_bound_records_checked': 31, 'all_match_hashes_and_published_P_bytes': True, 'science_ledger': identity(R13 / 'R13_COMPLETED_WORK_LEDGER.json'), 'all_other_tracked_files_except_four_current_entrypoints_unchanged_from_P': True, 'original_science_seal_R13_publication_not_yet_claimed_flag_retained': True, 'original_science_seal_current_publication_state_archived_exactly': True, 'release': ledger['release']},
    'current_entrypoints': {'files': [identity(ROOT / n) for n in ENTRYPOINTS], 'all_match_post_publication_sync_receipt': True, 'changed_current_product_keys': sorted(changed_keys), 'changed_active_followup_keys': sorted(active_changes), 'only_changed_work_package': 'WP9', 'verification_and_scientific_claims_unchanged': True, 'new_branch_pushed_now_supported_by_science_commit_and_retained_actual_publication_record': True, 'all_release_flags_remain_false': True},
    'retained_metadata_attempt1': {'files': [identity(attempt / n) for n in ('FAILURE_AND_RECOVERY.json', 'R13_SCIENCE_PUBLICATION_READBACK.json', 'finalize_science_publication.py')], 'original_recording_source_hash_matches_preserved_attempt_source': True, 'failure_fact': failed['terminal_failure'], 'recovery': failed['fix'], 'failure_not_relabelled_as_success': True, 'attempt2_receipt_differences_only_timestamp_and_new_recording_source': True, 'scope_boundary': 'The retained failure declaration and source/receipt are inspected; this audit does not re-execute or reproduce the sparse-checkout failure.'},
    'bound_publication_records': [identity(p) for p in (PUB / 'R13_SCIENCE_PUBLICATION_READBACK.json', PUB / 'R13-science/PUBLICATION_PLAN.json', PUB / 'R13-science/TREE_COMMIT_REF_RECEIPT.json', PUB / 'finalize_science_publication.py', R13 / 'status/R13_PUBLICATION_ENTRYPOINT_SYNC_RESULT.json')],
    'containing_followup_scope': 'This review covers the current publication-metadata working tree before its followup commit. The already published science identity is P; no future metadata commit ID or ref update is pre-claimed.',
}
assert not OUT.exists(), 'Preserve prior audit results; use a separate receipt.'
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'completed': True, 'review': identity(OUT)}, ensure_ascii=False))
