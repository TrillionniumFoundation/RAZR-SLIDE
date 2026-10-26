"""Execute the unmodified S4 native KiCad verifier with pinned isolated packages."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
SOURCES = ('tools/verify_ep5_ecad_native.py', 'tools/read_ep5_ecad_native.py',
           'integration/product_ep5_ecad.py', 'integration/product_interfaces.py',
           'design/product_routing_ep5.json')

def sha(path):
    with Path(path).open('rb') as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        return digest.hexdigest()

def main():
    repo = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    base = Path(os.environ['RUNNER_TEMP']) / 'razr-ec1-s4'
    base.mkdir(exist_ok=False)
    output = base / 'result'
    packages = json.loads(Path(sys.argv[1]).read_text())['packages']
    receipt = {'schema': 'razr-S4-EC1-launch-v1', 'source_commit': S4,
               'started': time.time(), 'completed': False, 'passed': False,
               'new_native_execution': False, 'source_sha256': {}, 'packages': [],
               'candidate_go': False, 'fixture_fabrication_go': False,
               'manufacturing_go': False}
    try:
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == S4
        assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=repo, text=True)
        for name in SOURCES:
            actual = (repo / name).read_bytes()
            assert actual == subprocess.check_output(['git', 'show', S4 + ':' + name], cwd=repo)
            receipt['source_sha256'][name] = hashlib.sha256(actual).hexdigest()
        cache = base / 'downloads'
        cache.mkdir()
        def fetch(row):
            target = cache / row['name']
            assert Path(row['name']).name == row['name']
            assert row['url'].startswith(('https://archive.ubuntu.com/ubuntu/', 'https://ppa.launchpadcontent.net/kicad/'))
            with urllib.request.urlopen(row['url'], timeout=90) as source, target.open('xb') as dest:
                while block := source.read(1024 * 1024):
                    dest.write(block)
            if target.stat().st_size != row['bytes'] or sha(target) != row['sha256']:
                raise ValueError('pinned package bytes differ: ' + row['name'])
            return {**row, 'verified': True}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            receipt['packages'] = list(pool.map(fetch, packages))
        runtime = base / 'runtime'
        runtime.mkdir()
        for row in packages:
            subprocess.run(['dpkg-deb', '-x', str(cache / row['name']), str(runtime)], check=True, timeout=60)
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['LD_LIBRARY_PATH'] = ':'.join(str(runtime / p) for p in ('usr/lib/x86_64-linux-gnu', 'usr/lib'))
        env['PYTHONPATH'] = str(runtime / 'usr/lib/python3/dist-packages')
        env['KICAD_STOCK_DATA_HOME'] = str(runtime / 'usr/share/kicad')
        for name, folder in [('KICAD_CONFIG_HOME', 'config'), ('KICAD_DOCUMENTS_HOME', 'documents'),
                             ('XDG_CONFIG_HOME', 'xdg-config'), ('XDG_CACHE_HOME', 'xdg-cache'),
                             ('XDG_DATA_HOME', 'xdg-data')]:
            directory = base / folder
            directory.mkdir()
            env[name] = str(directory)
        command = ['/usr/bin/python3', '-B', str(repo / SOURCES[0]), '--output', str(output),
                   '--expected-head', S4, '--kicad-python', '/usr/bin/python3',
                   '--kicad-cli', str(runtime / 'usr/bin/kicad-cli')]
        with (base / 'verifier.log').open('x') as log:
            result = subprocess.run(command, cwd=repo, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=930)
        receipt['verifier_exit_code'] = result.returncode
        receipt['verifier_report_produced'] = (output / 'report.json').is_file()
        if receipt['verifier_report_produced']:
            report = json.loads((output / 'report.json').read_text())
            receipt['new_native_execution'] = any(c.get('label') in ('native-readback', 'native-drc')
                and isinstance(c.get('exit_code'), int) for c in report.get('commands', []))
            receipt['native_DRC_executed'] = report.get('native_DRC_executed', False)
            receipt['passed'] = result.returncode == 0 and report.get('passed') is True
        receipt['completed'] = True
    except Exception as exc:
        receipt['error_type'] = type(exc).__name__
        receipt['error_message'] = str(exc)
    finally:
        receipt['elapsed_seconds'] = time.time() - receipt['started']
        receipt['source_bytes_unchanged'] = all(sha(repo / n) == h for n, h in receipt['source_sha256'].items())
        receipt['passed'] = receipt['passed'] and receipt['source_bytes_unchanged']
        (base / 'execution.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return 0 if receipt['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
