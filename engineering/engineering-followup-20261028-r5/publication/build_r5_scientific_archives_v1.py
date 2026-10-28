"""Freeze complete R5 scientific records without changing executed sources.

This is an evidence packaging operation, not a geometry or qualification run.
Signed transfer descriptors and complete Git repositories are never packaged.
Every selected original is hashed before writing and read back from the ZIP.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'razr-current'
OUTPUT = ROOT / 'r5-deliverables'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def add_tree(selected, directory, prefix, exclude_zip=False):
    for path in sorted(directory.rglob('*')):
        if not path.is_file():
            continue
        assert not path.is_symlink(), str(path)
        if '.private.' in path.name or path.name.endswith('.private.json'):
            continue
        if exclude_zip and path.suffix == '.zip':
            continue
        if '__pycache__' in path.parts:
            continue
        selected[str(Path(prefix) / path.relative_to(directory))] = path


def envelope_selection():
    selected = {}
    add_tree(selected, ROOT / 'r5-envelope', 'source/r5')
    add_tree(selected, ROOT / 'r5-ci-results', 'actual-ci')
    bridge = json.loads((ROOT / 'r5-envelope/R5E_PUBLIC_INPUT_BRIDGE.json').read_text())
    for entry in bridge['files']:
        path = REPO / bridge['repo_prefix'] / entry['path']
        assert identity(path.read_bytes()) == entry['public_identity']
        selected['inputs/r4/' + entry['path']] = path
    lock = json.loads((ROOT / 'r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V4.json').read_text())
    for entry in lock['r4_source_files']:
        path = REPO / bridge['repo_prefix'] / entry['path']
        assert identity(path.read_bytes()) == {'bytes': entry['bytes'], 'sha256': entry['sha256']}
        selected['inputs/r4/' + entry['path']] = path
    for dirname in (
        'independent-ci-preparation-review',
        'independent-envelope-v3-execution-review',
        'independent-refinement-method-review',
        'independent-envelope-v4-execution-review',
        'independent-trim-model-preparation-review',
        'independent-trim-v5-preexecution-review',
        'independent-envelope-v5-execution-review',
    ):
        directory = ROOT / 'r5-integration' / dirname
        if directory.is_dir():
            add_tree(selected, directory, 'reviews/' + dirname, exclude_zip=True)
    for directory in sorted((ROOT / 'r5-integration').glob('v*-independent-checker')):
        if directory.is_dir():
            add_tree(selected, directory, 'reviews/' + directory.name, exclude_zip=True)
    for path in sorted((ROOT / 'r5-integration').glob('*')):
        if not path.is_file() or '.private.' in path.name:
            continue
        if path.suffix == '.log' or path.suffix == '.yml' or path.name.startswith(('R5_V3_', 'R5_V4_', 'R5_V5_', 'R5_EXTERIOR_')):
            selected['integration/' + path.name] = path
    selected['README.md'] = OUTPUT / 'README_R5_ENVELOPE_ARCHIVE.md'
    return selected


def integration_selection():
    selected = {}
    add_tree(selected, ROOT / 'r5-integration', 'integration', exclude_zip=True)
    add_tree(selected, ROOT / 'r5-resource', 'resources', exclude_zip=True)
    numeric = ROOT / 'r5-numeric-readback'
    for path in sorted(numeric.glob('*')):
        if path.is_file() and path.suffix in ('.py', '.json', '.md') and '.private.' not in path.name:
            selected['numeric-scope-readback/' + path.name] = path
    scope = json.loads((numeric / 'R5_ORIGINAL_NUMERIC_QUALIFICATION_SCOPE.json').read_text())
    for entry in scope['source_records'].values():
        path = numeric / 'original-records' / entry['archive_relative_path']
        assert identity(path.read_bytes()) == {'bytes': entry['bytes'], 'sha256': entry['sha256']}
        selected['numeric-scope-readback/original-records/' + entry['archive_relative_path']] = path
    for name in ('R5_FINAL_EXECUTED_STATUS.json', 'README_R5_SCIENTIFIC_DELIVERY.md'):
        selected[name] = OUTPUT / name
    return selected


def build(kind):
    start = time.monotonic()
    OUTPUT.mkdir(exist_ok=True)
    selected = envelope_selection() if kind == 'envelope' else integration_selection()
    name = ('RAZR-R5-continuous-envelope-executed-evidence-20261028.zip'
            if kind == 'envelope' else
            'RAZR-R5-integration-and-independent-review-evidence-20261028.zip')
    target = OUTPUT / name
    assert not target.exists(), 'Refuse overwrite of a frozen archive'
    rows = []
    for archive_path, path in sorted(selected.items()):
        assert path.is_file(), str(path)
        assert not Path(archive_path).is_absolute() and '..' not in Path(archive_path).parts
        rows.append({'archive_path': archive_path,
                     'source_path': str(path.relative_to(ROOT)),
                     **identity(path.read_bytes())})
    manifest = {
        'schema': 'razr-r5-complete-scientific-archive-manifest-v1',
        'kind': kind,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'files': rows,
        'file_count': len(rows),
        'total_original_bytes': sum(row['bytes'] for row in rows),
        'scientific_originals_rewritten': False,
        'contains_complete_git_repository': False,
        'contains_signed_transfer_descriptors': False,
        'all_blockers_closed': False,
    }
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for row in rows:
            data = selected[row['archive_path']].read_bytes()
            assert identity(data) == {'bytes': row['bytes'], 'sha256': row['sha256']}, 'Source changed during packaging'
            archive.writestr(row['archive_path'], data,
                compress_type=zipfile.ZIP_STORED if Path(row['archive_path']).suffix in ('.gz', '.zip') else zipfile.ZIP_DEFLATED)
        archive.writestr('MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(target) as archive:
        assert len(archive.infolist()) == len(rows) + 1
        assert len(set(archive.namelist())) == len(archive.namelist())
        assert json.loads(archive.read('MANIFEST.json')) == manifest
        for row in rows:
            assert identity(archive.read(row['archive_path'])) == {'bytes': row['bytes'], 'sha256': row['sha256']}
    seal = {'schema': 'r5-scientific-archive-full-local-readback-v1',
            'kind': kind, 'file_name': name, **identity(target.read_bytes()),
            'file_count': len(rows) + 1, 'manifest_files': len(rows),
            'all_member_CRC_and_SHA_verified': True,
            'elapsed_seconds': time.monotonic() - start,
            'scientific_gate_execution': False,
            'all_blockers_closed': False}
    (OUTPUT / ('R5_' + kind.upper() + '_ARCHIVE_SEAL.json')).write_text(json.dumps(seal, indent=2) + '\n')
    print(json.dumps(seal))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('kind', choices=('envelope', 'integration'))
    build(parser.parse_args().kind)
