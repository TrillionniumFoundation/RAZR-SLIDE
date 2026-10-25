"""Source-bound research identities without pretending a dirty tree is a commit.

The geometry drivers bind every actual project Python import and every declared
native payload before/after execution. Unrelated unimported work may proceed in
the shared checkout. Exact-commit canonical validation remains a separate gate.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AREAS = ('integration', 'tools', 'engineering', 'design')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def environment():
    check = module(ROOT/'tools/check_environment.py', '_geometry_environment')
    record = check.inspect_environment(ROOT)
    if record.get('passed') is not True or record.get('checked_package_count') != 43:
        raise ValueError('all 43 original locked package versions are required')
    return record


def snapshot():
    roles = module(ROOT/'integration/ep5_input_closure.py', '_geometry_input_roles').native_input_roles('full')
    paths = {ROOT/name for name in roles}
    paths.update(ROOT/name for name in ('pyproject.toml', 'uv.lock'))
    for area in AREAS:
        paths.update(path for path in (ROOT/area).rglob('*.py') if path.is_file())
    paths.update(path for path in (ROOT/'design').rglob('*.json') if path.is_file())
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('missing or linked declared execution input: '+str(path))
    return {'repository_head_at_start': git('rev-parse', 'HEAD'),
            'worktree_status_at_start': git('status', '--porcelain'),
            'native_input_roles': roles,
            'available_source_sha256': {str(path): sha(path) for path in sorted(paths)},
            'environment': environment(), 'exact_commit_execution_claimed': False}


def record_executed_project_files():
    """Include importlib exec_module users that never register in sys.modules."""
    executed = set()
    areas = tuple(ROOT/area for area in AREAS)
    def audit(event, args):
        if event == 'exec' and args:
            filename = getattr(args[0], 'co_filename', '')
            if filename and not filename.startswith('<'):
                path = Path(filename).resolve()
                if any(path.is_relative_to(area) for area in areas):
                    executed.add(path)
    sys.addaudithook(audit)
    return executed


def finish(before, explicit_sources=()):
    required = {ROOT/name for name in before['native_input_roles']}
    required.update(ROOT/name for name in ('pyproject.toml', 'uv.lock'))
    required.update(Path(path).resolve() for path in explicit_sources)
    areas = tuple(ROOT/area for area in AREAS)
    for loaded in tuple(sys.modules.values()):
        path = getattr(loaded, '__file__', None)
        if path and any(Path(path).resolve().is_relative_to(area) for area in areas):
            required.add(Path(path).resolve())
    mismatches = []
    sources = {}
    for path in sorted(required):
        previous = before['available_source_sha256'].get(str(path))
        current = sha(path) if path.is_file() and not path.is_symlink() else None
        sources[str(path)] = current
        if previous is None or current != previous:
            mismatches.append({'path': str(path), 'before': previous, 'after': current})
    after_environment = environment()
    return {'executed_source_and_input_sha256': sources,
            'executed_source_count': len(sources), 'changed_or_late_sources': mismatches,
            'environment_after': after_environment,
            'source_bytes_and_locked_environment_unchanged': not mismatches and after_environment == before['environment'],
            'repository_head_at_finish': git('rev-parse', 'HEAD'),
            'exact_commit_execution_claimed': False}


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.partial')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        import os
        os.fsync(stream.fileno())
    temporary.replace(path)
