"""Freeze exact completed diagnostic files for an append-only Git evidence publication."""
import gzip
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'engineering/engineering-followup-20261028-r7/'
OUT = ROOT / 'r7-publication/method-checkpoint-v2'
PARENT = '34764db3c8d61d6e53ea22da8caf4dc57b931463'
BASE_TREE = '1195ca799d551a53f7c27b8ff3a175cca19cb8fb'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob_sha': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def main():
    assert not OUT.exists()
    start = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('60-second publication preparation limit')))
    signal.alarm(60)
    prior = json.loads((ROOT / 'r7-publication/R7_NATIVE_FINITE_REMOTE_SUBTREE_READBACK_V1.json').read_text())
    assert prior['sha'] == '6e98caa0292d3145215f8675b8c1115bd8686da8' and not prior['truncated']
    prior_blobs = {PREFIX + row['path']: row for row in prior['tree'] if row['type'] == 'blob'}
    selected = {}

    def add(path, dest):
        path = Path(path).resolve()
        assert path.is_file() and not path.is_symlink() and path.is_relative_to(ROOT)
        assert '.private.' not in path.name and 'r7-private-helpers' not in path.parts
        assert '__pycache__' not in path.parts and path.suffix != '.pyc'
        dest = PREFIX + dest
        assert dest not in selected
        selected[dest] = path

    def tree(local, dest):
        directory = ROOT / local
        assert directory.is_dir()
        for path in sorted(directory.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                add(path, dest + '/' + path.relative_to(directory).as_posix())

    for name in ('v9-meaning-review-v1', 'spatial-pilot-v1', 'edge189-source-diagnostic-v1'):
        tree('r7-envelope/' + name, 'envelope/' + name)
    for name in ('edge189-independent-v1', 'edge189-actual-readback-v1'):
        tree('r7-native/' + name, 'native/' + name)
    for name in ('envelope-spatial-probe-review', 'envelope-edge189-review', 'storage-observation',
                 'storage-migration-followup-v1', 'blocker-ledger'):
        tree('r7-audit/' + name, 'independent-review/' + name)
    for name in ('append_blocker_closure_ledger_r7_v2.py', 'build_blocker_closure_ledger_r7_v1.py',
                 'read_positive_q_source_mapping_r7_v1.py', 'extract_exact_push_read_observations_r7_v1.py',
                 'R7_REAL_SPECIMEN_SCOPED_RETRIEVAL_OBSERVATION_V1.json',
                 'R7_UNPUBLISHED_OBJECT_READ_RECEIPTS_V1.json'):
        add(ROOT / 'r7-audit' / name, 'independent-review/source/' + name)
    for name in ('R7_METHOD_ARCHIVE_ATTEMPT1_ACTUAL_CAPACITY_FAILURE_V1.json',
                 'R7_METHOD_ARCHIVE_V2_SOURCE_REVISION_V1.json', 'R7_METHOD_COMPLETE_ARCHIVE_PLAN_V2.json',
                 'R7_METHOD_COMPLETE_ARCHIVE_SEAL_V2.json', 'R7_METHOD_COMPLETE_PRESERVATION_V1.json',
                 'RAZR-SLIDE_R7_scientific_files_20261028.json'):
        add(ROOT / 'r7-deliverables' / name, 'preservation/' + name)
    for name in ('package_method_diagnostics_complete_r7_v1.py', 'package_method_diagnostics_complete_r7_v2.py'):
        add(ROOT / 'r7-recovery-tools' / name, 'preservation/source/' + name)
    for name in ('R7_COMPLETE_FACTORY_ARCHIVE_EXPANSION_MIGRATION_V1.json',
                 'reclaim_complete_archived_factory_expansions_v1.py',
                 'R7_ORIGINAL_V6_ALL16_STATUS_READBACK_V1.json',
                 'R7_ENVELOPE_RUNTIME_REMOTE_PUBLICATION_VERIFIED_V1.json',
                 'R7_NATIVE_FINITE_REMOTE_PUBLICATION_VERIFIED_V1.json',
                 'R7_NATIVE_FINITE_REMOTE_WRITE_RECEIPTS_V1.json',
                 'R7_FAR_REDUNDANT_PARTIAL_CACHE_RECLAIM_V1.json', 'reclaim_far_redundant_partial_cache_v1.py',
                 'R7_CATALOG_PREPARATION_ATTEMPT1_ACTUAL_FAILURE_V1.json',
                 'R7_SCIENTIFIC_CATALOG_PREVIOUS_VERSION0_ORIGINAL.json', 'R7_SCIENTIFIC_CATALOG_SAVED_V2.json',
                 'R7_THREE_SAVED_ARCHIVE_CACHE_RECLAIM_V1.json', 'reclaim_three_saved_archive_caches_v1.py',
                 'R7_TWO_SAVED_FACTORY_ZIP_CACHE_RECLAIM_V1.json', 'reclaim_two_saved_factory_zip_caches_v1.py'):
        add(ROOT / 'r7-publication' / name, 'preservation/' + name)
    add(ROOT / 'r7-publication/R7_METHOD_DIAGNOSTICS_AND_CURRENT_BLOCKERS_V1.md', 'METHOD_DIAGNOSTICS_AND_CURRENT_BLOCKERS_V1.md')
    tree('r7-publication/method-checkpoint-v1', 'publication/method-checkpoint-preparation-attempt1')
    add(ROOT / 'r7-publication/prepare_method_checkpoint_publication_v1.py', 'publication/prepare_method_checkpoint_publication_v1.py')
    add(Path(__file__), 'publication/' + Path(__file__).name)
    OUT.mkdir()
    compressed_dir = OUT / 'lossless-gzip'
    compressed_dir.mkdir()
    rows = []
    skipped = []
    total = 0
    for original_dest, path in sorted(selected.items()):
        data = path.read_bytes()
        original = identity(data)
        total += len(data)
        assert total <= 64 * 1024 * 1024
        if original_dest in prior_blobs:
            old = prior_blobs[original_dest]
            assert old['sha'] == original['git_blob_sha'] and old['size'] == original['bytes']
            skipped.append({'repository_path': original_dest, 'identity': original})
            continue
        try:
            text = data.decode('utf-8')
            is_text = '\0' not in text
        except UnicodeDecodeError:
            is_text = False
        compressed = len(data) > 262144 and is_text
        dest = PREFIX + 'method-original-gzip/' + original_dest.removeprefix(PREFIX) + '.gz' if compressed else original_dest
        assert dest not in prior_blobs
        transport_path = path
        transport_data = data
        if compressed:
            transport_data = gzip.compress(data, compresslevel=6, mtime=0)
            assert gzip.decompress(transport_data) == data
            transport_path = compressed_dir / (hashlib.sha256(original_dest.encode()).hexdigest()[:20] + '-' + path.name + '.gz')
            transport_path.write_bytes(transport_data)
        transport = identity(transport_data)
        rows.append({'repository_path': dest, 'original_repository_path': original_dest,
                     'original_path': str(path), 'original_identity': original,
                     'transport_path': str(transport_path), 'transport_identity': transport,
                     'representation': 'lossless_gzip_original' if compressed else 'exact_original',
                     'content_kind': 'binary' if compressed or not is_text else 'text',
                     'full_original_roundtrip_verified': True})
    assert len({row['repository_path'] for row in rows}) == len(rows)
    for row in rows:
        assert identity(Path(row['original_path']).read_bytes()) == row['original_identity']
        assert identity(Path(row['transport_path']).read_bytes()) == row['transport_identity']
    manifest = {'schema': 'razr-r7-completed-method-checkpoint-publication-manifest-v2',
                'parent_commit': PARENT, 'base_tree': BASE_TREE, 'repository_prefix': PREFIX,
                'prior_R7_blob_count': len(prior_blobs), 'prior_paths_unchanged': True,
                'selected_original_count': len(selected), 'selected_original_bytes': total,
                'unchanged_existing_originals_not_republished': skipped,
                'new_file_count': len(rows), 'files': rows,
                'complete_consumed_scientific_originals_saved_archive': {
                    'library_file_id': 'libfile_2caa15dac6808191b426fda57b336694',
                    'bytes': 53293490, 'sha256': '709500f8d11e3c4a98114de5777ab3a7605d0a324169fb74054cd6b5e1a77b9d',
                    'members': 535},
                'new_Cylinder_preparation_included': False,
                'workflows_or_RUN_REQUEST_modified': False, 'exact_a11_requested_push_fulfilled': False,
                'original_V9_failure_reclassified': False, 'full_continuous_G2': False,
                'all_blockers_closed': False}
    (OUT / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    seal = {'schema': 'razr-r7-completed-method-checkpoint-preparation-seal-v2',
            'manifest': identity((OUT / 'MANIFEST.json').read_bytes()),
            'original_count': len(selected), 'new_files': len(rows),
            'new_binary_files': sum(row['content_kind'] == 'binary' for row in rows),
            'new_transport_bytes': sum(row['transport_identity']['bytes'] for row in rows),
            'all_selected_original_bytes_unchanged': True, 'full_gzip_roundtrip_verified': True,
            'seconds': time.monotonic() - start,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'new_geometry_execution': False, 'ref_mutated': False}
    (OUT / 'PREPARATION_SEAL.json').write_text(json.dumps(seal, indent=2) + '\n')
    signal.alarm(0)
    print(json.dumps(seal))


if __name__ == '__main__':
    main()
