"""Bind exact current source bytes and original gates before local setup."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO = BASE / 'razr-current'
ASSETS = REPO / 'engineering/engineering-followup-20261028-r5/cloud-native-v1'
S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'

def identity(p):
    data = Path(p).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def bind(p):
    return {'path': str(Path(p).resolve()), 'identity': identity(p)}

def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--stage', choices=['assess_only', 'install_only'], required=True)
    args = ap.parse_args()
    manifest = BASE / 'r7-recovery/native-audit/R5_RECOVERED_FUNCTIONAL_SOURCE_MANIFEST.json'
    expected = dict(json.loads(manifest.read_text())['members'])
    assert len(expected) == 971
    tree_raw = subprocess.check_output(['git', '--no-lazy-fetch', 'ls-tree', '-rz', S4], cwd=REPO)
    tree = {}
    for item in tree_raw.split(b'\0'):
        if item:
            meta, name = item.split(b'\t', 1)
            mode, kind, sha = meta.decode().split()
            tree[name.decode()] = {'mode': mode, 'kind': kind, 'git_blob': sha}
    all_paths = sorted(set(expected) | {'.python-version', '.gitignore'})
    commands = ''.join(S4 + ':' + p + '\n' for p in all_paths).encode()
    proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    data, _ = proc.communicate(commands)
    assert proc.returncode == 0
    offset, observations = 0, []
    for path in all_paths:
        end = data.index(b'\n', offset)
        head = data[offset:end].decode().split()
        assert len(head) == 3 and head[1] == 'blob', 'Original Git blob missing: ' + path
        n = int(head[2]); raw = data[end + 1:end + 1 + n]
        assert len(raw) == n and data[end + 1 + n:end + 2 + n] == b'\n'
        offset = end + 2 + n
        digest = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        assert hashlib.sha1(b'blob ' + str(n).encode() + b'\0' + raw).hexdigest() == head[0] == tree[path]['git_blob']
        assert tree[path]['kind'] == 'blob' and tree[path]['mode'] in ('100644', '100755')
        if path in expected:
            assert digest == expected[path], 'Historical recovered source differs from actual S4 Git blob: ' + path
        else:
            expected[path] = digest
        observations.append({'path': path, 'Git_blob': head[0], **digest})
    assert offset == len(data) and len(expected) == 973
    source_readback = ROOT / 'R7_EXACT_973_S4_GIT_SOURCE_READBACK_V1.json'
    source_record = {'schema': 'RAZR_R7_EXACT_S4_SOURCE_READBACK_V1', 'commit': S4,
                     'tree': subprocess.check_output(['git', '--no-lazy-fetch', 'rev-parse', S4 + '^{tree}'], cwd=REPO, text=True).strip(),
                     'original_recovered_971_manifest': bind(manifest), 'all_971_exact_originals_equal_to_real_Git': True,
                     'tracked_files_selected': 973, 'expected_actual_worktree_file_count_with_git_pointer': 974,
                     'all_file_bytes': sum(x['bytes'] for x in expected.values()), 'members': observations}
    if source_readback.exists():
        assert json.loads(source_readback.read_text()) == source_record
    else:
        source_readback.write_text(json.dumps(source_record, indent=2) + '\n')
    template_path = ASSETS / 'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json'
    template = json.loads(template_path.read_text())
    plan = {'schema': 'RAZR_R7_LOCAL_SETUP_REGISTERED_CONTRACT_V1',
            'registered_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'stage': args.stage,
            'setup_source_identity': identity(ROOT / 'setup_fresh_s4_runtime_r7_v1.py'),
            'repository': str(REPO), 'functional_root': str(ROOT / 'genuine-s4-worktree-v1'),
            'output': str(ROOT / ('setup-' + args.stage + '-v1')), 'uv_root': str(ROOT / 'pinned-uv-0.10.10-v1'),
            'uv_selection': str(ROOT / 'R7_PINNED_UV_WHEEL_SELECTION_V1.json'),
            'python_executable': sys.executable, 'expected_sources': expected,
            'original_six_limits': template['original_resource_limits'],
            'conservative_preinstall_reserve_bytes': 7968830419,
            'capacity_basis': {'original_postinstall_available_floor': 4294967296,
                               'source_checkout_reserve': 67108864, 'pinned_uv_tool_reserve': 201326592,
                               'new_venv_reserve': 1610612736, 'metadata_reserve': 16777216,
                               'installer_transient_reserve': 1778037715,
                               'source_exact_bytes': source_record['all_file_bytes'],
                               'previous_43_payload_reference_bytes': 1226421880,
                               'time_estimate_seconds': [120, 480], 'setup_hard_wall_seconds': 1200,
                               'historical_reference_not_new_install_qualification': True},
            'qualification_or_CAD_allowed_by_this_contract': False,
            'bound_inputs': [bind(p) for p in (manifest, source_readback, template_path,
                              ROOT / 'R7_PINNED_UV_WHEEL_SELECTION_V1.json', ROOT / 'uv-0.10.10-pypi-original.json',
                              ROOT / 'qualify_fresh_runtime_r7_v1.py', Path(__file__))]}
    assert sum(plan['capacity_basis'][k] for k in ('original_postinstall_available_floor','source_checkout_reserve','pinned_uv_tool_reserve','new_venv_reserve','metadata_reserve','installer_transient_reserve')) == plan['conservative_preinstall_reserve_bytes']
    if args.stage == 'install_only':
        assessment = ROOT / 'setup-assess_only-v1/R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1.json'
        assert json.loads(assessment.read_text())['completed']
        plan['bound_inputs'].append(bind(assessment))
    target = ROOT / ('R7_SETUP_' + args.stage.upper() + '_CONTRACT_V1.json')
    assert not target.exists()
    target.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps({'contract': str(target), 'identity': identity(target), 'stage': args.stage,
                      'exact_sources': len(expected), 'source_bytes': source_record['all_file_bytes']}))

if __name__ == '__main__':
    main()
