"""Prepare a newly named narrow runtime ownership repair from exact public v5 bytes."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'razr-current/engineering/engineering-followup-20261028-r5/cloud-native-v1/qualify_fresh_runtime_r5.py'
EXPECTED = '9787944e893339831661542775ade149695137def6215dacdf878a6af36786c7'

def main():
    old = OLD.read_bytes()
    assert hashlib.sha256(old).hexdigest() == EXPECTED
    new = old.decode().replace('import resource\n', 'import resource\nimport stat\n', 1)
    marker = '\ndef main():\n'
    helper = '''
def verified_uv_root_lock(venv):
    """Admit only the exact empty regular .lock created at the venv root."""
    path = Path(venv) / '.lock'
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return {'present': False, 'allowed_relative_files': []}
    require(stat.S_ISREG(observed.st_mode), 'uv root .lock is not a regular file')
    require(observed.st_size == 0, 'uv root .lock is not empty')
    bound = identity(path)
    require(bound == {'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()},
            'uv root .lock identity is not the empty regular file')
    return {'present': True, 'allowed_relative_files': ['.lock'], 'identity': bound,
            'ownership': 'exact-root installer scaffold; no wildcard or payload exemption'}

'''
    assert new.count(marker) == 1
    new = new.replace(marker, '\n' + helper + marker, 1)
    marker2 = "        pth = site / '_virtualenv.pth'\n"
    assert new.count(marker2) == 1
    new = new.replace(marker2, "        root_lock = verified_uv_root_lock(venv)\n        scaffolds.update(root_lock['allowed_relative_files'])\n        report['verified_uv_root_lock'] = root_lock\n" + marker2, 1)
    ast.parse(new)
    target = ROOT / 'qualify_fresh_runtime_r7_v1.py'
    assert not target.exists()
    target.write_text(new)
    receipt = {'schema': 'RAZR_R7_NEW_RUNTIME_REPAIR_PREPARATION_V1',
               'original_public_source_commit': '65f2a8fbb30d6310c1a69ef37204fa7fa8f32b3a',
               'original': {'path': str(OLD), 'bytes': len(old), 'sha256': EXPECTED},
               'new': {'path': str(target), 'bytes': len(new.encode()), 'sha256': hashlib.sha256(new.encode()).hexdigest()},
               'prior_unsaved_v6_recovery_claimed': False,
               'changes': ['import stat', 'add exact root empty regular lock ownership helper', 'add verified helper result to scaffold set and actual report'],
               'original_43_wheel_RECORD_payload_import_and_before_after_checks_unchanged': True,
               'actual_new_runtime_or_native_execution_claimed': False}
    (ROOT / 'R7_NEW_RUNTIME_REPAIR_PREPARATION_V1.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
