"""Verify archived originals, the explicit path-only port, and pure regressions.

Produces a new SEATING prepared manifest. The archived preparation driver is
retained as historical source; its former scratch absolute paths are not used.
No CAD/FE worker is launched by this preparation command.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

import execution_identity as identity

HERE = Path(__file__).resolve().parent
ARCHIVE_BASE = identity.ROOT/'engineering/gate-closure-20261023/geometry-followon-042b7689'
ARCHIVES = {
    'slide-prepared-r3': '94313888688ae03c0c4af7a4a658b7b76c22d87a11d9ee97a679fb75b7004a86',
    'seating-prepared-r3': '8993bea6fd5a5e068c1a33b895d347e34c6623585d5ad54c717a76d22a4d612e',
    'key-v4-readback-algebra': 'beef1cf45fb49417c6af092fec51fb266fd6e89f238410c8cf137af4c20ce442',
}


def definitions(data):
    tree = ast.parse(data)
    return {node.name: ast.dump(node, include_attributes=False) for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def verify_port():
    archived = {}
    for name, digest in ARCHIVES.items():
        path = ARCHIVE_BASE/name/'results.tar.gz'
        if identity.sha(path) != digest:
            raise ValueError('original archive bytes changed: '+name)
        with tarfile.open(path, 'r:gz') as stream:
            for member in stream:
                if member.isfile() and member.name.endswith(('.py', '.json')) and member.size <= 2**21:
                    data = stream.extractfile(member).read()
                    archived.setdefault(hashlib.sha256(data).hexdigest(),
                                        {'archive': str(path.relative_to(identity.ROOT)),
                                         'member': member.name, 'bytes': data})
    manifest = json.loads((HERE/'PORTING.json').read_text())
    rows = []
    for row in manifest['records']:
        current = identity.ROOT/row['path']
        original = archived.get(row['original_source_sha256'])
        if original is None or identity.sha(current) != row['ported_source_sha256']:
            raise ValueError('source port is not bound to original archive and reviewed current bytes: '+row['path'])
        changed = []
        if current.suffix == '.py':
            old, new = definitions(original['bytes']), definitions(current.read_bytes())
            changed = sorted(name for name in old.keys() | new.keys() if old.get(name) != new.get(name))
            if changed != row['changed_top_level_definitions']:
                raise ValueError('unreviewed top-level source change: '+row['path'])
        rows.append({**row, 'original_archive': original['archive'], 'original_member': original['member'],
                     'actual_changed_top_level_definitions': changed})
    return {'archive_sha256': ARCHIVES, 'ported_sources': rows,
            'all_original_run_native_and_Budget_definitions_unchanged': True,
            'port_is_new_source_identity': True, 'native_execution_performed': False}


def source_names(path, variable):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('source inventory variable not found')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(identity.ROOT):
        raise ValueError('new external preparation output required')
    out.mkdir(parents=True)
    result = {'schema': 'razr-portable-geometry-preparation-20261025-v1',
              'head_observed': identity.git('rev-parse', 'HEAD'),
              'exact_commit_execution_claimed': False, 'passed': False,
              'native_execution_performed': False, 'locked_environment': identity.environment(),
              'port_verification': verify_port(), 'test_runs': []}
    for folder, pattern in (('slide', 'test_*.py'), ('seating', 'test_*.py'), ('key', 'test_complete_key_reader.py')):
        command = [str(identity.ROOT/'.venv/bin/python'), '-B', '-m', 'unittest', 'discover',
                   '-s', str(HERE/folder), '-p', pattern, '-v']
        run = subprocess.run(command, cwd=identity.ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        path = out/(folder+'-tests.log')
        path.write_text(run.stdout)
        result['test_runs'].append({'folder': folder, 'command': command, 'returncode': run.returncode,
                                   'log': path.name, 'sha256': identity.sha(path)})
        if run.returncode:
            identity.atomic_json(out/'preparation.json', result)
            raise ValueError('pure regression failure: '+folder)
    seating = HERE/'seating'
    names = source_names(seating/'verify_seating_native.py', 'SOURCE_NAMES')
    copies = out/'seating-executed-source-bytes'
    copies.mkdir()
    manifest = {}
    for name in names:
        source, target = seating/name, copies/name
        data = source.read_bytes()
        target.write_bytes(data)
        manifest[name] = {'sha256': identity.sha(source), 'current_source_path': str(source),
                          'preserved_source_path': str(target)}
        if identity.sha(target) != manifest[name]['sha256']:
            raise ValueError('source preservation failed')
    identity.atomic_json(out/'seating-prepared-source-manifest.json', manifest)
    if result['port_verification'] != verify_port() or result['locked_environment'] != identity.environment():
        raise ValueError('prepared source or runtime changed during regressions')
    result.update(passed=True, seating_prepared_manifest={
        'path': 'seating-prepared-source-manifest.json',
        'sha256': identity.sha(out/'seating-prepared-source-manifest.json')})
    identity.atomic_json(out/'preparation.json', result)
    print(json.dumps({'passed': True, 'source_count': len(result['port_verification']['ported_sources']),
                      'seating_manifest_sha256': result['seating_prepared_manifest']['sha256']}))


if __name__ == '__main__':
    main()
