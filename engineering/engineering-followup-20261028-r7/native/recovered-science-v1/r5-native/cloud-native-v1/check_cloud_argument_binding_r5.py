"""Actual stdlib-only denial controls for the reviewed cloud entry sources.

The real entry/qualifier main functions execute through runpy in fresh -I -B
processes. An independent import hook refuses any CAD/numeric import attempt.
Canonical arguments must reach, and be refused by, an explicitly unqualified
runtime fixture. Changed pose/output/receipt and noncanonical option spellings
must be refused earlier, without creating any candidate output.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent


def identity(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


HOOK = '''from pathlib import Path
import builtins, importlib.abc, json, runpy, sys, traceback
config=json.loads(Path(sys.argv[1]).read_text())
blocked=[]
forbidden={'cadquery','OCP','vtk','vtkmodules','numpy','scipy','shapely','casadi','nlopt'}
class NoNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in forbidden:
            blocked.append(fullname)
            raise RuntimeError('Pure stdlib rejection control prohibits native/numeric import: '+fullname)
sys.meta_path.insert(0,NoNative())
sys.argv=[config['script'],*config['arguments']]
result={'actual_source':config['script'],'actual_arguments':list(config['arguments']),
        'blocked_native_import_attempts':blocked,'exception':None}
code=2
try:
    runpy.run_path(config['script'],run_name='__main__')
    code=0
except SystemExit as exc:
    code=0 if exc.code is None else exc.code if isinstance(exc.code,int) else 2
    result['SystemExit_code']=code
except BaseException as exc:
    result['exception']={'type':type(exc).__name__,'message':str(exc)}
    traceback.print_exc()
finally:
    result['exit_code']=code
    result['native_numeric_modules_loaded']=sorted(n for n in sys.modules if n.split('.')[0] in forbidden)
    Path(config['audit']).write_text(json.dumps(result,indent=2)+'\\n')
raise SystemExit(code)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise ValueError('Fresh control-output directory required')
    out.mkdir(parents=True)
    hook = out / 'stdlib_denial_hook.py'
    hook.write_text(HOOK)
    entry = HERE / 'run_fresh_runtime_script_r5.py'
    qualifier = HERE / 'qualify_fresh_runtime_r5.py'
    started = time.monotonic()
    report = {'schema': 'razr-r5-cloud-argv-binding-actual-stdlib-controls-v1',
              'entry': identity(entry), 'qualifier': identity(qualifier), 'control_source': identity(__file__),
              'independent_no_native_hook': identity(hook), 'completed': False, 'controls': [],
              'native_execution_claimed': False, 'new_runtime_qualification_claimed': False,
              'fixture_is_explicitly_unqualified_not_a_fabricated_venv': True}
    for kind in ('entry', 'qualifier'):
        names = ['canonical_unqualified_denial', 'wrong_output', 'abbreviated_option', 'duplicate_option', 'equals_option', 'wrong_contract_locator']
        if kind == 'entry':
            names += ['wrong_pose', 'wrong_receipt', 'duplicate_payload_option', 'abbreviated_payload_option', 'extra_payload_argument']
        for name in names:
            folder = out / (kind + '-' + name)
            folder.mkdir()
            cp = folder / 'contract.json'
            target = folder / ('receipt.json' if kind == 'entry' else 'worker')
            script = entry if kind == 'entry' else qualifier
            if kind == 'entry':
                false = folder / 'EXPLICITLY_UNQUALIFIED_NEGATIVE_FIXTURE.json'
                false.write_text(json.dumps({'completed': False, 'fixture_only': True, 'runtime_qualification_claimed': False}) + '\n')
                payload = ['--pose', 'near', '--output', str(folder / 'never-started-study-output')]
                contract = {'entry_identity': identity(entry), 'expected_entry_contract': str(cp),
                            'expected_receipt': str(target), 'expected_script_arguments': payload,
                            'bound_sources': [], 'qualification': {'path': str(false), 'identity': identity(false)},
                            'maximum_receipt_bytes': 4194304}
                argv = ['--contract', str(cp), '--receipt', str(target), '--', *payload]
                if name == 'wrong_output':
                    argv[-1] = str(folder / 'UNAUTHORIZED_OUTPUT')
                elif name == 'wrong_pose':
                    argv[-3] = 'far'
                elif name == 'wrong_receipt':
                    argv[3] = str(folder / 'UNAUTHORIZED_RECEIPT.json')
                elif name == 'abbreviated_option':
                    argv[2] = '--rec'
                elif name == 'duplicate_option':
                    argv[4:4] = ['--receipt', str(target)]
                elif name == 'equals_option':
                    argv[2:4] = ['--receipt=' + str(target)]
                elif name == 'duplicate_payload_option':
                    argv += ['--pose', 'near']
                elif name == 'abbreviated_payload_option':
                    argv[5] = '--po'
                elif name == 'extra_payload_argument':
                    argv.append('extra')
            else:
                contract = {'qualifier_identity': identity(qualifier), 'expected_qualification_contract': str(cp),
                            'expected_qualification_output': str(target),
                            'functional_root': str(folder / 'EXPLICITLY_NOT_A_GENUINE_VENV_OR_GIT_CHECKOUT'),
                            'maximum_report_bytes': 6291456, 'maximum_output_bytes': 8388608}
                argv = ['--contract', str(cp), '--out', str(target)]
                if name == 'wrong_output':
                    argv[3] = str(folder / 'UNAUTHORIZED_OUTPUT')
                elif name == 'abbreviated_option':
                    argv[2] = '--ou'
                elif name == 'duplicate_option':
                    argv += ['--out', str(target)]
                elif name == 'equals_option':
                    argv[2:4] = ['--out=' + str(target)]
            cp.write_text(json.dumps(contract, indent=2) + '\n')
            if name == 'wrong_contract_locator':
                alias = folder / 'copied-contract-at-unregistered-path.json'
                alias.write_bytes(cp.read_bytes())
                argv[1] = str(alias)
            config = folder / 'control-command.json'
            audit = folder / 'hook-observation.json'
            config.write_text(json.dumps({'script': str(script), 'arguments': argv, 'audit': str(audit)}, indent=2) + '\n')
            with (folder / 'stdout').open('xb') as stdout, (folder / 'stderr').open('xb') as stderr:
                result = subprocess.run([sys.executable, '-I', '-B', str(hook), str(config)], stdout=stdout, stderr=stderr)
            observed = json.loads(audit.read_text())
            if result.returncode != 2 or observed['blocked_native_import_attempts'] or observed['native_numeric_modules_loaded']:
                raise AssertionError('Control did not fail without native/numeric imports: ' + kind + '/' + name)
            expected_rejection = False
            if name == 'canonical_unqualified_denial':
                rp = target if kind == 'entry' else target / 'R5_FRESH_RUNTIME_QUALIFICATION.json'
                r = json.loads(rp.read_text())
                flag = 'complete_entry_argv_and_receipt_bound' if kind == 'entry' else 'complete_qualification_argv_and_output_bound'
                expected_rejection = r[flag] and not r['completed']
                if kind == 'entry':
                    expected_rejection = expected_rejection and not r['payload_started'] and any('Actual new runtime did not qualify' in i.get('message', '') for i in r['issues'])
                else:
                    expected_rejection = expected_rejection and any('Original cloud Python patch differs' in i.get('message', '') or 'not the genuine new S4 venv' in i.get('message', '') for i in r['issues'])
            elif name == 'abbreviated_option':
                expected_rejection = observed.get('SystemExit_code') == 2 and not target.exists()
            else:
                expected_rejection = observed['exception'] is not None and 'differs from complete registered argv' in observed['exception']['message'] and not target.exists()
            if not expected_rejection or any(p.name.startswith('UNAUTHORIZED_') for p in folder.iterdir()):
                raise AssertionError('Control failed for an unexpected reason or wrote unauthorized output: ' + kind + '/' + name)
            report['controls'].append({'entry_kind': kind, 'control': name, 'exit_code': result.returncode,
                                       'expected_rejection_observed': True, 'native_import_attempts': 0,
                                       'native_modules_loaded': 0, 'actual_hook_observation': {'relative': str(audit.relative_to(out)), **identity(audit)}})
    report['completed'] = len(report['controls']) == 17 and all(r['expected_rejection_observed'] for r in report['controls'])
    report['seconds'] = time.monotonic() - started
    report['sources_unchanged'] = identity(entry) == report['entry'] and identity(qualifier) == report['qualifier']
    (out / 'R5_CLOUD_ARGUMENT_CONTROLS_ACTUAL.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'completed': report['completed'], 'controls': len(report['controls']), 'seconds': report['seconds'], 'native_execution': False}), flush=True)
    return 0 if report['completed'] and report['sources_unchanged'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
