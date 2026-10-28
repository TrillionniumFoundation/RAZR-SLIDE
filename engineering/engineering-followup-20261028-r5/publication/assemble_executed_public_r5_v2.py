"""Project frozen R5 execution/audit records without changing any original.

Run only after the selected experiment and reviews have finished. Original CI
files keep their exact bytes; local review records may replace workspace path
prefixes, and every such projection receives an original/public identity pair.
"""
from pathlib import Path
import gzip
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'razr-current/engineering/engineering-followup-20261028-r5'
ROWS = []


def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def copy_one(path, destination, project_workspace):
    assert path.is_file() and not path.is_symlink()
    assert path.suffix != '.zip' and '.private.' not in path.name
    original = path.read_bytes()
    decoded = gzip.decompress(original) if path.suffix == '.gz' else original
    text = decoded.decode('utf8')
    public_text = re.sub(r'/workspace/scratch/[A-Za-z0-9_-]+', '<workspace>', text) if project_workspace else text
    assert not re.search(r'libfile_[0-9a-f]{32}', public_text), str(path)
    assert not re.search(r'https?://[^\s"<>]*oaiusercontent\.com', public_text), str(path)
    assert not re.search(r'https?://[^\s"<>]*[?&]sig=', public_text), str(path)
    if public_text == text:
        public = original
    elif path.suffix == '.gz':
        public = gzip.compress(public_text.encode(), compresslevel=9, mtime=0)
    else:
        public = public_text.encode()
    target = DEST / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == public, 'Different existing public record: ' + str(target)
    else:
        target.write_bytes(public)
    ROWS.append({'source': str(path.relative_to(ROOT)), 'destination': str(destination),
                 'source_identity': ident(original), 'public_identity': ident(public),
                 'workspace_prefix_projection': public != original,
                 'scientific_original_changed': False})


def copy_tree(source, destination, project_workspace):
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.suffix == '.zip' or '.private.' in path.name or '__pycache__' in path.parts:
            continue
        copy_one(path, destination / path.relative_to(source), project_workspace)


for directory in sorted((ROOT / 'r5-ci-results').glob('run-*')):
    assert directory.is_dir()
    copy_tree(directory, Path('envelope/actions') / directory.name, False)
for path in sorted((ROOT / 'r5-ci-results').glob('*.json')):
    copy_one(path, Path('envelope/reception') / path.name, True)
review_destinations = (
    ('independent-envelope-v3-execution-review', 'v3-execution'),
    ('independent-refinement-method-review', 'v4-method'),
    ('independent-envelope-v4-execution-review', 'v4-execution'),
    ('independent-trim-v5-preexecution-review', 'v5-preexecution'),
    ('independent-envelope-v5-execution-review', 'v5-execution'),
)
for name, destination in review_destinations:
    source = ROOT / 'r5-integration' / name
    if source.is_dir():
        copy_tree(source, Path('review') / destination, True)
handled = {name for name, _ in review_destinations} | {
    'independent-native-archive-review', 'independent-ci-preparation-review',
}
for source in sorted((ROOT / 'r5-integration').glob('independent-*')):
    if source.is_dir() and source.name not in handled:
        copy_tree(source, Path('review') / source.name, True)
for source in sorted((ROOT / 'r5-integration').glob('v*-independent-checker')):
    if source.is_dir():
        copy_tree(source, Path('review') / source.name, True)
copy_tree(ROOT / 'r5-integration/external-blocker-handoff', Path('handoff'), True)
copy_tree(ROOT / 'r5-envelope', Path('envelope/source-history'), True)
numeric = ROOT / 'r5-numeric-readback'
for path in sorted(numeric.glob('*')):
    if path.is_file() and path.suffix in ('.py', '.md', '.json') and '.private.' not in path.name:
        copy_one(path, Path('numerics') / path.name, True)
scope = json.loads((numeric / 'R5_ORIGINAL_NUMERIC_QUALIFICATION_SCOPE.json').read_text())
for entry in scope['source_records'].values():
    relative = Path(entry['archive_relative_path'])
    path = numeric / 'original-records' / relative
    assert ident(path.read_bytes()) == {'bytes': entry['bytes'], 'sha256': entry['sha256']}
    copy_one(path, Path('numerics/original-records') / relative, True)
for pattern in ('R5_V3_*.json', 'R5_V4_*.json', 'R5_V5_*.json', 'R5_STABLE_PUBLICATION_*.json'):
    for path in sorted((ROOT / 'r5-integration').glob(pattern)):
        if '.private.' not in path.name:
            copy_one(path, Path('publication') / path.name, True)
for name in ('verify_stable_publication_readback_r5.py', 'assemble_executed_public_r5_v2.py', 'build_r5_scientific_archives_v1.py'):
    copy_one(ROOT / 'r5-integration' / name, Path('publication') / name, True)
report = {'schema': 'r5-actual-execution-public-projection-map-v2', 'files': ROWS,
          'raw_CI_files_keep_original_bytes': True, 'raw_science_replaced_by_projection': False,
          'all_blockers_closed': False}
(DEST / 'R5_EXECUTED_PUBLIC_EVIDENCE_MAP.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'files': len(ROWS), 'public_bytes': sum(r['public_identity']['bytes'] for r in ROWS),
                  'projected_files': sum(r['workspace_prefix_projection'] for r in ROWS)}))
