"""Actual filesystem controls for the single empty uv root-lock ownership rule."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import tempfile
import time

ROOT = Path(__file__).resolve().parent

def main():
    source = ROOT / 'qualify_fresh_runtime_r7_v1.py'
    spec = importlib.util.spec_from_file_location('r7_owned_qualifier_control', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    controls = []
    start = time.monotonic()
    with tempfile.TemporaryDirectory(dir=ROOT, prefix='lock-control-') as td:
        root = Path(td)
        cases = [
            ('absent_root_lock', 'absent', True),
            ('empty_regular_root_lock', 'empty', True),
            ('nonempty_text_root_lock', 'text', False),
            ('nul_byte_root_lock', 'nul', False),
            ('newline_root_lock', 'newline', False),
            ('directory_root_lock', 'directory', False),
            ('symlink_to_empty_root_lock', 'symlink-empty', False),
            ('dangling_symlink_root_lock', 'symlink-dangling', False),
            ('fifo_root_lock', 'fifo', False),
            ('nested_lock_is_not_owned', 'nested', False),
            ('similar_root_filename_is_not_owned', 'similar', False),
            ('empty_root_does_not_cover_extra_payload', 'extra', False),
        ]
        for i, (name, kind, expected) in enumerate(cases):
            venv = root / str(i); venv.mkdir()
            lock = venv / '.lock'
            if kind == 'empty': lock.write_bytes(b'')
            elif kind == 'text': lock.write_bytes(b'x')
            elif kind == 'nul': lock.write_bytes(b'\0')
            elif kind == 'newline': lock.write_bytes(b'\n')
            elif kind == 'directory': lock.mkdir()
            elif kind == 'symlink-empty':
                (root / ('empty-' + str(i))).write_bytes(b'')
                lock.symlink_to(root / ('empty-' + str(i)))
            elif kind == 'symlink-dangling': lock.symlink_to(root / 'absent-target')
            elif kind == 'fifo': os.mkfifo(lock)
            elif kind == 'nested':
                (venv / 'nested').mkdir(); (venv / 'nested/.lock').write_bytes(b'')
            elif kind == 'similar': (venv / '.lock-other').write_bytes(b'')
            elif kind == 'extra':
                lock.write_bytes(b''); (venv / 'payload.py').write_text('unexpected = True\n')
            failure = None
            try:
                result = module.verified_uv_root_lock(venv)
                actual = {str(p.relative_to(venv)) for p in venv.rglob('*') if p.is_file() or p.is_symlink()}
                extras = sorted(actual - set(result['allowed_relative_files']))
                accepted = not extras
            except (ValueError, OSError) as exc:
                result, extras, accepted = None, None, False
                failure = {'type': type(exc).__name__, 'message': str(exc)}
            assert accepted is expected, name
            controls.append({'name': name, 'expected_accept': expected, 'actual_accept': accepted,
                             'helper_result': result, 'unowned_files': extras, 'failure': failure})
    report = {'schema': 'RAZR_R7_UV_ROOT_LOCK_ACTUAL_CONTROLS_V1', 'completed': True,
              'source': {'path': str(source), 'bytes': source.stat().st_size, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
              'controls': controls, 'count': len(controls), 'seconds': time.monotonic() - start,
              'actual_runtime_qualification_claimed': False, 'actual_CAD_claimed': False}
    p = ROOT / 'R7_UV_ROOT_LOCK_ACTUAL_CONTROLS_V1.json'
    assert not p.exists(); p.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'completed': True, 'controls': len(controls), 'seconds': report['seconds']}))

if __name__ == '__main__':
    main()
