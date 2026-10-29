"""Preserve V1 and prepare narrowly corrected V2 after independent static gaps."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parent

def identity(p):
    b = p.read_bytes(); return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def main():
    old = ROOT / 'setup_fresh_s4_runtime_r7_v1.py'
    text = old.read_text()
    start = text.index('    actual = {}\n', text.index('def verify_checkout('))
    end = text.index('    require(set(actual)', start)
    text = text[:start] + '    actual = strict_worktree_inventory(root)\n' + text[end:]
    helper = '''def strict_worktree_inventory(root):
    require(stat.S_ISDIR(root.lstat().st_mode), 'Worktree root is not a real directory')
    actual = {}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(base)
        for name in list(dirs):
            p = base / name
            require(stat.S_ISDIR(p.lstat().st_mode), 'Non-directory or symlink directory in worktree')
            if base == root and name == '.venv':
                dirs.remove(name)
        for name in files:
            p = base / name
            require(stat.S_ISREG(p.lstat().st_mode), 'Special or symlink file in worktree')
            actual[str(p.relative_to(root))] = identity(p)
    return actual


def transient_bytes(root):
    # Installer files can be removed while sampled. Every completed sample is
    # an observation, not a claim that every intervening byte was observable.
    total = 0
    if root.exists():
        for p in root.rglob('*'):
            try:
                s = p.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISREG(s.st_mode):
                total += s.st_size
    return total


'''
    marker = 'def verify_checkout(root, expected, commit):\n'
    assert text.count(marker) == 1
    text = text.replace(marker, helper + marker)
    old_sample = "sum(p.stat().st_size for p in temp.rglob('*') if p.is_file() and not p.is_symlink()) if temp.exists() else 0"
    assert text.count(old_sample) == 1
    text = text.replace(old_sample, 'transient_bytes(temp)')
    old_bound = "require(sum(x.file_size for x in members) <= 201326592, 'uv wheel expanded capacity exceeded')"
    assert text.count(old_bound) == 1
    text = text.replace(old_bound, "require(wheel['size'] + sum(x.file_size for x in members) <= 201326592, 'Retained uv wheel plus expanded tool capacity exceeded')")
    ast.parse(text)
    target = ROOT / 'setup_fresh_s4_runtime_r7_v2.py'
    assert not target.exists(); target.write_text(text)
    old_reg = ROOT / 'register_local_setup_r7_v1.py'
    new_reg = old_reg.read_text().replace('setup_fresh_s4_runtime_r7_v1.py', 'setup_fresh_s4_runtime_r7_v2.py')
    new_reg = new_reg.replace('genuine-s4-worktree-v1', 'genuine-s4-worktree-v2').replace('pinned-uv-0.10.10-v1','pinned-uv-0.10.10-v2')
    new_reg = new_reg.replace("('setup-' + args.stage + '-v1')", "('setup-' + args.stage + '-v2')")
    new_reg = new_reg.replace('setup-assess_only-v1/', 'setup-assess_only-v2/').replace("'_CONTRACT_V1.json'", "'_CONTRACT_V2.json'")
    new_reg = new_reg.replace('RAZR_R7_LOCAL_SETUP_REGISTERED_CONTRACT_V1', 'RAZR_R7_LOCAL_SETUP_REGISTERED_CONTRACT_V2')
    new_reg_path = ROOT / 'register_local_setup_r7_v2.py'; assert not new_reg_path.exists(); new_reg_path.write_text(new_reg)
    old_run = ROOT / 'register_and_run_native_local_r7_v1.py'
    new_run = old_run.read_text().replace('genuine-s4-worktree-v1', 'genuine-s4-worktree-v2')
    new_run = new_run.replace('setup-install_only-v1/', 'setup-install_only-v2/').replace('R7_SETUP_INSTALL_ONLY_CONTRACT_V1.json','R7_SETUP_INSTALL_ONLY_CONTRACT_V2.json')
    new_run = new_run.replace('setup_fresh_s4_runtime_r7_v1.py','setup_fresh_s4_runtime_r7_v2.py')
    new_run_path = ROOT / 'register_and_run_native_local_r7_v2.py'; assert not new_run_path.exists(); new_run_path.write_text(new_run)
    for p in (new_reg_path, new_run_path): ast.parse(p.read_text())
    receipt = {'schema': 'RAZR_R7_SETUP_V1_STATIC_GAPS_AND_V2_REVISION',
               'v1_actual_installer_or_native_execution': False,
               'v1_actual_pure_assessment_retained': True,
               'independent_review_gaps': ['Complete member census could silently skip FIFO/socket/special entries', 'Retained compressed uv wheel was outside expanded-tool reserve bound'],
               'v2_fixes': ['lstat every actual non-runtime entry; reject symlinks/specialfiles; prune only real root .venv directory', 'retained wheel plus all expanded files bounded by same 201326592-byte tool reserve', 'installer transient size sample tolerates genuine deletion races without ignoring persistent entries'],
               'source_versions': {p.name: identity(p) for p in (old, target, old_reg, new_reg_path, old_run, new_run_path)},
               'original_scientific_limits_reduced': False, 'actual_new_install_or_native_execution_claimed': False}
    out = ROOT / 'R7_SETUP_V1_STATIC_GAPS_AND_V2_REVISION.json'; out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

if __name__ == '__main__': main()
