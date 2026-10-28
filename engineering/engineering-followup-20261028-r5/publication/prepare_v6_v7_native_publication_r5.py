"""Bind exact originals for the V6 checkpoint and reviewed V7/native CI sources."""
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
base_manifest = json.loads((ROOT / 'r5-integration/R5_V6_LOGICAL_GIT_PUBLICATION_MANIFEST.json').read_text())
selected = {row['path']: ROOT / row['source_path'] for row in base_manifest['files']}


def add(source, destination):
    source = ROOT / source
    assert source.is_file() and not source.is_symlink(), str(source)
    assert '.private.' not in source.name and source.suffix != '.zip'
    assert destination not in selected or selected[destination] == source
    selected[destination] = source


def tree(source, destination):
    for p in sorted((ROOT / source).rglob('*')):
        if p.is_file() and p.suffix != '.zip' and '.private.' not in p.name and '__pycache__' not in p.parts:
            add(p.relative_to(ROOT), destination + '/' + p.relative_to(ROOT / source).as_posix())


lock = json.loads((ROOT / 'r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V7.json').read_text())
for row in lock['r5_files']:
    p = ROOT / 'r5-envelope' / row['path']
    b = p.read_bytes()
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    add(p.relative_to(ROOT), PREFIX + 'compute/' + row['path'])
for name in ('R5E_PORTABLE_SOURCE_LOCK_V7.json', 'R5E_V7_READINESS.json'):
    add('r5-envelope/' + name, PREFIX + 'compute/' + name)
for name in ('R5_V7_LOCAL_EXECUTION_READINESS.json', 'README_R5_V7_PREEXECUTION.md'):
    add('r5-local-v7/' + name, PREFIX + 'envelope/local-v7/' + name)
tree('r5-integration/independent-planar-v7-preexecution-review', PREFIX + 'review/v7-preexecution')
tree('r5-integration/v7-independent-checker', PREFIX + 'review/v7-independent-checker')
for name in ('r5-planar-v7-workflow.yml', 'r5-planar-v7-workflow.template.yml',
             'R5_V6_LOGICAL_GIT_PUBLICATION_MANIFEST.json', 'prepare_v6_v7_native_publication_r5.py'):
    add('r5-integration/' + name, PREFIX + 'publication/' + name)
add('r5-integration/r5-planar-v7-workflow.yml', '.github/workflows/r5-exterior-channel.yml')
tree('r5-native/cloud-native-v1/publication-v3', PREFIX + 'cloud-native-v1')
add('r5-native/cloud-native-v1/publication-v3/r5-native-fresh-hosted-v1.yml',
    '.github/workflows/r5-native-fresh-hosted-v1.yml')

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
    b = source.read_bytes()
    decoded = gzip.decompress(b) if source.suffix == '.gz' else b
    for pattern in (rb'libfile_[0-9a-f]{32}', rb'https?://[^\s"<>]*oaiusercontent\.com', rb'https?://[^\s"<>]*[?&]sig='):
        assert not re.search(pattern, decoded), str(source)
    binary = source.suffix == '.gz'
    if not binary:
        b.decode('utf8')
    oid = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    rows.append({'path': destination, 'source_path': source.relative_to(ROOT).as_posix(),
                 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'git_blob_sha': oid,
                 'binary': binary, 'already_available_blob': oid in known,
                 'changed_from_base': base_files.get(destination) != oid,
                 'original_bytes_preserved': True})
result = {'schema': 'r5-v6-executed-and-v7-native-reviewed-source-publication-v1',
          'base_commit': BASE, 'base_tree': base_manifest['base_tree'], 'files': rows,
          'contains_RUN_REQUEST_mutation': False,
          'V6_actual_pipeline_completed': True, 'V7_math_execution_completed': False,
          'native_fresh_execution_completed': False,
          'original_failure_records_preserved': True,
          'historical_maps_are_bound_to_their_recorded_commit': True,
          'exact_a11_publication_completed': False, 'all_blockers_closed': False}
target = ROOT / 'r5-integration/R5_V6_V7_NATIVE_SOURCE_PUBLICATION_MANIFEST.json'
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'files': len(rows), 'changed_files': sum(r['changed_from_base'] for r in rows),
                  'unique_new_binary_bytes': sum(r['bytes'] for r in {r['git_blob_sha']: r for r in rows if r['binary'] and not r['already_available_blob']}.values()),
                  'new_scientific_execution': False}))
