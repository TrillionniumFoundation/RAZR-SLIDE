"""Prepare an exact-byte Git projection without duplicating large originals."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'razr-current'
PREFIX = 'engineering/engineering-followup-20261028-r5/'
BASE = '6c26a5749cf9d241f629519a62efd3ad625fdc2c'
selected = {}


def add(path, destination):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert '.private.' not in path.name and path.suffix != '.zip'
    target = PREFIX + destination
    assert target not in selected or selected[target] == path
    selected[target] = path


def tree(directory, destination):
    for path in sorted(directory.rglob('*')):
        if path.is_file() and path.suffix != '.zip' and '.private.' not in path.name and '__pycache__' not in path.parts:
            add(path, str(Path(destination) / path.relative_to(directory)))


lock = json.loads((ROOT / 'r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V6.json').read_text())
for row in lock['r5_files']:
    path = ROOT / 'r5-envelope' / row['path']
    data = path.read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    add(path, 'compute/' + row['path'])
for name in ('R5E_PORTABLE_SOURCE_LOCK_V6.json', 'R5E_V6_READINESS.json'):
    add(ROOT / 'r5-envelope' / name, 'compute/' + name)
tree(ROOT / 'r5-local-v6/attempt-1', 'envelope/local/attempt-v6-1')
for path in sorted((ROOT / 'r5-local-v6').iterdir()):
    if path.is_file():
        add(path, 'envelope/local-v6/' + path.name)
tree(ROOT / 'r5-local-v6/input-snapshot-v1', 'envelope/local-v6/input-snapshot-v1')
tree(ROOT / 'r5-local-v6/retained-diagnostic-v1', 'envelope/local-v6/retained-diagnostic-v1')
for source, destination in (
    ('independent-envelope-v5-execution-review', 'v5-execution'),
    ('independent-numeric-scope-review', 'numeric-scope'),
    ('independent-key-stop-source-review', 'key-stop-source'),
    ('independent-primitive-v6-preexecution-review', 'v6-preexecution'),
    ('independent-primitive-v6-execution-review', 'v6-execution'),
    ('v6-independent-checker', 'v6-independent-checker'),
):
    tree(ROOT / 'r5-integration' / source, 'review/' + destination)
for name in (
    'r5-primitive-v6-workflow.yml', 'r5-primitive-v6-workflow.template.yml',
    'R5_V5_EXECUTED_PUBLICATION_MANIFEST.json', 'R5_V5_EXECUTED_CHECKPOINT_PUBLICATION.json',
    'R5_V5_EXECUTED_CHECKPOINT_REMOTE_READBACK.json',
    'R5_EXACT_A11_REMOTE_RECHECK_20261028T165100Z.json',
    'R5_EXECUTED_CHECKPOINT_THROUGH_V5.md', 'prepare_v6_logical_git_projection_r5.py',
    'build_v6_scientific_checkpoint_archive_r5.py',
):
    add(ROOT / 'r5-integration' / name, 'publication/' + name)
add(ROOT / 'r5-integration/R5_EXECUTED_CHECKPOINT_THROUGH_V6.md', 'README.md')
base_files = {}
for item in subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE], cwd=REPO).split(b'\0'):
    if item:
        metadata, name = item.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        if kind == b'blob':
            base_files[name.decode()] = oid.decode()
known = set(base_files.values())
rows = []
for destination, source in sorted(selected.items()):
    data = source.read_bytes()
    decoded = gzip.decompress(data) if source.suffix == '.gz' else data
    decoded.decode('utf8')
    for pattern in (rb'libfile_[0-9a-f]{32}', rb'https?://[^\s"<>]*oaiusercontent\.com', rb'https?://[^\s"<>]*[?&]sig='):
        assert not re.search(pattern, decoded), str(source)
    oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    rows.append({'path': destination, 'source_path': source.relative_to(ROOT).as_posix(),
                 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob_sha': oid,
                 'binary': source.suffix == '.gz', 'already_available_blob': oid in known,
                 'changed_from_base': base_files.get(destination) != oid,
                 'original_bytes_preserved': True, 'workspace_paths_preserved_in_original_records': True})
manifest = {'schema': 'r5-v6-original-byte-logical-git-projection-v1', 'base_commit': BASE,
            'base_tree': '96b1eeffc0d1826d4009f9f565cc8069ad5d985f',
            'files': rows, 'changed_files': [r for r in rows if r['changed_from_base']],
            'V7_drafts_included': False, 'large_originals_duplicated_on_local_disk': False,
            'new_scientific_execution': False, 'all_blockers_closed': False}
target = ROOT / 'r5-integration/R5_V6_LOGICAL_GIT_PUBLICATION_MANIFEST.json'
assert not target.exists()
target.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'files': len(rows), 'changed_files': len(manifest['changed_files']),
                  'new_binary_files': sum(r['binary'] and not r['already_available_blob'] for r in rows),
                  'new_binary_bytes': sum(r['bytes'] for r in rows if r['binary'] and not r['already_available_blob']),
                  'new_text_bytes': sum(r['bytes'] for r in rows if not r['binary'] and not r['already_available_blob'])}))
