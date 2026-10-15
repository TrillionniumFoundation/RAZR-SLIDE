#!/usr/bin/env python3
"""Run the new bounded G2 experiment and preserve every native exit status."""
from pathlib import Path
import argparse, hashlib, json, os, platform, subprocess, sys, time

ROOT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'native_input_manifest.json').read_text())
    before = {name: sha(ROOT / name) for name in manifest['files']}
    if before != manifest['files']:
        raise ValueError('native input differs from frozen source manifest')
    started = time.time()
    runs = []
    commands = [
        ('new_geometry_tests', [sys.executable, '-B', str(ROOT / 'test_geometry_candidates.py')]),
        ('actual_obstacles_and_conditional_J', [sys.executable, '-B', str(ROOT / 'actual_obstacle_and_jacobian.py'), '--out-dir', str(output / 'actual')]),
    ]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for label, command in commands:
        with (output / (label + '.stdout.log')).open('wb') as stdout, (output / (label + '.stderr.log')).open('wb') as stderr:
            native = subprocess.run(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr)
        runs.append({'name': label, 'command': command, 'actual_exit_code': native.returncode})
        if native.returncode:
            break
    after = {name: sha(ROOT / name) for name in manifest['files']}
    receipt = {
        'host': platform.node(), 'python': sys.version, 'python_executable': sys.executable,
        'native_input_manifest_sha256': sha(ROOT / 'native_input_manifest.json'),
        'input_file_count': len(before), 'input_sha256_before': before, 'input_sha256_after': after,
        'input_bytes_unchanged': before == after, 'runs': runs,
        'all_actual_native_exit_codes_zero': len(runs) == len(commands) and all(r['actual_exit_code'] == 0 for r in runs),
        'elapsed_seconds': time.time() - started,
        'actual_phone_and_dynamic_FPC_qualification_received': False, 'manufacturing_go': False,
    }
    (output / 'native_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('host', 'input_file_count', 'input_bytes_unchanged', 'all_actual_native_exit_codes_zero', 'manufacturing_go')}), flush=True)
    return 0 if receipt['all_actual_native_exit_codes_zero'] and before == after else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.out_dir))
