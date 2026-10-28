"""Prepare only the frozen ASCII native source revision; never start a worker."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'r5-native/cloud-native-v1/publication-v4'
REPO = ROOT / 'razr-current'
PREFIX = 'engineering/engineering-followup-20261028-r5/cloud-native-v1/'
BASE = '1a513697ef2aea7144518742ab67080b8b6e1192'
LOCK_SHA = 'dbf70814f6933b98818338f0a342706161b0b47268ec6da7ddf36ef3d4be13b4'
assert hashlib.sha256((SOURCE / 'SOURCE_LOCK.json').read_bytes()).hexdigest() == LOCK_SHA
lock = json.loads((SOURCE / 'SOURCE_LOCK.json').read_bytes())
for name, identity in lock['asset_files'].items():
    b = (SOURCE / name).read_bytes()
    assert len(b) == identity['bytes'] and hashlib.sha256(b).hexdigest() == identity['sha256']
base = {}
for item in subprocess.check_output(['git', 'ls-tree', '-r', '-z', BASE], cwd=REPO).split(b'\0'):
    if item:
        metadata, name = item.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        if kind == b'blob':
            base[name.decode()] = oid.decode()
rows = []
known = set(base.values())
for source in sorted(SOURCE.iterdir()):
    assert source.is_file() and not source.is_symlink()
    b = source.read_bytes()
    decoded = gzip.decompress(b) if source.suffix == '.gz' else b
    for pattern in (rb'libfile_[0-9a-f]{32}', rb'https?://[^\s"<>]*oaiusercontent\.com', rb'https?://[^\s"<>]*[?&]sig='):
        assert not re.search(pattern, decoded), str(source)
    oid = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    destination = PREFIX + source.name
    rows.append({'path': destination, 'source_path': source.relative_to(ROOT).as_posix(),
                 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'git_blob_sha': oid,
                 'binary': source.suffix == '.gz', 'already_available_blob': oid in known,
                 'changed_from_base': base.get(destination) != oid})
result = {'schema': 'r5-native-ascii-v4-exact-source-publication-v1', 'base_commit': BASE,
          'base_tree': '18bca69ddccffe1f1cf97f1a45c517136e787041', 'files': rows,
          'source_lock_sha256': LOCK_SHA, 'RUN_REQUEST_included': False,
          'prior_v3_unexecuted_source_preserved_in_parent_history': True,
          'geometry_operations_and_original_resource_gates_unchanged': True,
          'native_execution_completed': False, 'all_blockers_closed': False}
target = ROOT / 'r5-integration/R5_NATIVE_V4_SOURCE_PUBLICATION_MANIFEST.json'
assert not target.exists()
target.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'files': len(rows), 'changed_files': sum(r['changed_from_base'] for r in rows),
                  'changed_bytes': sum(r['bytes'] for r in rows if r['changed_from_base'])}))
