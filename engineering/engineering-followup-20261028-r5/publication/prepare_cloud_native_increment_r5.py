"""Prepare an exact reviewed cloud-native source increment without moving any ref.

This publication helper performs no scientific calculation and does not issue a
RUN_REQUEST. Every changed blob is written from its original source bytes before
the expected tree is calculated; only unchanged promisor base blobs may be absent.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess

parser = argparse.ArgumentParser(allow_abbrev=False)
parser.add_argument('--packet', required=True)
parser.add_argument('--base-commit', required=True)
parser.add_argument('--expected-lock', required=True)
parser.add_argument('--tag', required=True)
parser.add_argument('--review-file', action='append', default=[])
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'razr-current'
PREFIX = 'engineering/engineering-followup-20261028-r5/'
assert re.fullmatch('[a-z0-9-]+', args.tag)
assert re.fullmatch('[0-9a-f]{40}', args.base_commit)
assert re.fullmatch('[0-9a-f]{64}', args.expected_lock)
packet = (ROOT / args.packet).resolve()
assert packet.is_relative_to(ROOT / 'r5-native/cloud-native-v1')
lock_bytes = (packet / 'SOURCE_LOCK.json').read_bytes()
assert hashlib.sha256(lock_bytes).hexdigest() == args.expected_lock
lock = json.loads(lock_bytes)
assert lock['repository'] == 'TrillionniumFoundation/RAZR-SLIDE'
assert lock['branch'] == 'evidence/full-sprint-20261028-r5'
assert lock['repository_directory'] == PREFIX.rstrip('/') + '/cloud-native-v1'
assert lock['original_six_native_limits_unchanged'] == {
    'wall_seconds': 1200, 'worker_RSS_limit_bytes': 1610612736,
    'shared_limit_bytes': 7301444403, 'startup_disk_floor_bytes': 268435456,
    'startup_extra_shared_bytes': 2147483648, 'runtime_disk_floor_bytes': 104857600}
for name, identity in lock['asset_files'].items():
    source = packet / name
    assert source.is_file() and not source.is_symlink()
    b = source.read_bytes()
    assert {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()} == identity
selected = {}
for p in sorted(packet.iterdir()):
    assert p.is_file() and not p.is_symlink()
    assert p.name != 'RUN_REQUEST.json' and '.private.' not in p.name
    selected[PREFIX + 'cloud-native-v1/' + p.name] = p
workflow = packet / 'r5-native-fresh-hosted-v1.yml'
assert {'bytes': workflow.stat().st_size, 'sha256': hashlib.sha256(workflow.read_bytes()).hexdigest()} == lock['workflow_identity']
selected[lock['workflow_path']] = workflow
for path in args.review_file:
    p = (ROOT / path).resolve()
    assert p.is_relative_to(ROOT / 'r5-integration') and p.is_file() and not p.is_symlink()
    assert '.private.' not in p.name
    selected[PREFIX + 'review/' + args.tag + '/' + p.name] = p
base_tree = subprocess.check_output(['git', '--no-lazy-fetch', 'rev-parse', args.base_commit + '^{tree}'], cwd=REPO).decode().strip()
base = {}
for item in subprocess.check_output(['git', '--no-lazy-fetch', 'ls-tree', '-r', '-z', args.base_commit], cwd=REPO).split(b'\0'):
    if item:
        metadata, name = item.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        if kind == b'blob':
            base[name.decode()] = oid.decode()
known = set(base.values())


def row(destination, source):
    b = source.read_bytes()
    decoded = gzip.decompress(b) if source.suffix == '.gz' else b
    for pattern in (rb'libfile_[0-9a-f]{32}', rb'https?://[^\s"<>]*oaiusercontent\.com', rb'https?://[^\s"<>]*[?&]sig='):
        assert not re.search(pattern, decoded), str(source)
    oid = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    return {'path': destination, 'source_path': source.relative_to(ROOT).as_posix(),
            'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'git_blob_sha': oid,
            'binary': source.suffix == '.gz', 'already_available_blob': oid in known,
            'changed_from_base': base.get(destination) != oid}


rows = [row(destination, p) for destination, p in sorted(selected.items())]
result = {'schema': 'r5-reviewed-native-exact-source-increment-v1', 'tag': args.tag,
          'base_commit': args.base_commit, 'base_tree': base_tree,
          'source_lock_sha256': args.expected_lock, 'files': rows,
          'RUN_REQUEST_included': False, 'source_bytes_modified': False,
          'original_six_native_limits_unchanged': True,
          'new_native_execution_claimed': False, 'all_blockers_closed': False}
manifest_path = ROOT / 'r5-integration' / ('R5_' + args.tag.upper().replace('-', '_') + '_PUBLICATION_MANIFEST.json')
envelope_path = manifest_path.with_name(manifest_path.name.replace('_MANIFEST.json', '_ENVELOPE.json'))
assert not manifest_path.exists() and not envelope_path.exists()
manifest_path.write_text(json.dumps(result, indent=2) + '\n')
rows.append(row(PREFIX + 'publication/' + manifest_path.name, manifest_path))
rows.append(row(PREFIX + 'publication/' + Path(__file__).name, Path(__file__).resolve()))
index = '/tmp/razr-r5-' + args.tag + '-publication-index'
assert not Path(index).exists()
env = dict(os.environ, GIT_INDEX_FILE=index)
subprocess.run(['git', 'read-tree', args.base_commit], cwd=REPO, env=env, check=True)
for item in rows:
    if not item['changed_from_base']:
        continue
    b = (ROOT / item['source_path']).read_bytes()
    assert hashlib.sha256(b).hexdigest() == item['sha256']
    oid = subprocess.check_output(['git', 'hash-object', '-w', '--stdin'], cwd=REPO, input=b).decode().strip()
    assert oid == item['git_blob_sha']
    subprocess.run(['git', 'update-index', '--index-info'], cwd=REPO, env=env,
                   input=('100644 ' + oid + '\t' + item['path'] + '\n').encode(), check=True)
result['expected_tree'] = subprocess.check_output(['git', 'write-tree', '--missing-ok'], cwd=REPO, env=env).decode().strip()
envelope_path.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'manifest': str(manifest_path.relative_to(ROOT)), 'envelope': str(envelope_path.relative_to(ROOT)),
                  'files': len(rows), 'changed_files': sum(r['changed_from_base'] for r in rows),
                  'expected_tree': result['expected_tree']}))
