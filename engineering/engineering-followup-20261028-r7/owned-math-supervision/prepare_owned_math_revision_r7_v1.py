"""Create new named exit-race handling; original scientific/source bytes retained."""
import ast, hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = root/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/r4'
destination = root/'r7-supervisor/source-v1'
destination.mkdir(exist_ok=False)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)

old_entry = base/'run_owned_pure_math_r4e_v3.py'
text = old_entry.read_text()
text = replace_once(text, 'import json\n', 'import json\nimport os\n')
text = replace_once(text, "    owned.announce_worker_from_environment(Path(__file__).resolve())\n", "    owned.announce_worker_from_environment(Path(__file__).resolve())\n    execution_identity = owned.own_identity()\n    execution_nonce = os.environ[owned.NONCE]\n    supervision_contract_sha = sha(args.supervision_contract)\n")
text = replace_once(text, "'schema': 'razr-r4e-owned-pure-math-entry-v3-canonical-arguments'", "'schema': 'razr-r7-owned-pure-math-entry-v1-identity-receipt'")
text = replace_once(text, "    actual_args = args.worker_arguments", "    report.update(owned_execution_identity=execution_identity, owned_execution_nonce=execution_nonce,\n                  supervision_contract_sha256=supervision_contract_sha)\n    actual_args = args.worker_arguments")
text = replace_once(text, "        report['peak_RSS_bytes'] =", "        report['owned_execution_identity_unchanged'] = owned.own_identity() == execution_identity\n        report['supervision_contract_unchanged'] = sha(args.supervision_contract) == supervision_contract_sha\n        report['peak_RSS_bytes'] =")
text = replace_once(text, "            report['entry_and_worker_and_owned_source_unchanged'] and\n", "            report['entry_and_worker_and_owned_source_unchanged'] and\n            report['owned_execution_identity_unchanged'] and report['supervision_contract_unchanged'] and\n")
entry = destination/'run_owned_pure_math_r7_v1.py'
entry.write_text(text)

old_supervisor = base/'supervise_owned_pure_math_r4e_v2.py'
text = old_supervisor.read_text()
extension = (root/'r7-supervisor/termination_extension_v1.py.txt').read_text()
text = replace_once(text, '\ndef main():\n', '\n'+extension+'\n\ndef main():\n')
text = replace_once(text, "    require(sha(__file__) == contract['supervisor_sha256'], 'supervisor identity differs')", "    require(sha(__file__) == contract['supervisor_sha256'], 'supervisor identity differs')\n    require(contract.get('completed_entry_exit_confirmation_policy') == EXIT_CONFIRMATION_POLICY,\n            'exact explicit completed-entry policy required')")
text = replace_once(text, "'schema': 'razr-r4e-owned-pure-math-supervision-v2-bound-entry'", "'schema': 'razr-r7-owned-pure-math-supervision-v1-completed-entry-exit'")
text = replace_once(text, "'missing_RSS_zero_substitutions': 0}", "'missing_RSS_zero_substitutions': 0, 'bounded_exit_confirmation_count': 0,\n              'completed_entry_exit_confirmation_policy': EXIT_CONFIRMATION_POLICY}")
text = replace_once(text, "                    if confirmed_code is None:\n                        raise RuntimeError('still-running owned child RSS unavailable: '+type(exc).__name__+': '+str(exc)) from exc", "                    if confirmed_code is None:\n                        confirmed_code = confirm_completed_entry_exit(\n                            exc, child, channel, contract, args.contract, args.out/'entry-receipt.json',\n                            args.worker_arguments, report, started, observe)")
supervisor = destination/'supervise_owned_pure_math_r7_v1.py'
supervisor.write_text(text)
for p in (entry, supervisor):
    compile(p.read_text(), str(p), 'exec', dont_inherit=True, optimize=0)
def functions(p):
    return {f.name:ast.dump(f,include_attributes=False) for f in ast.parse(p.read_text()).body if isinstance(f,ast.FunctionDef)}
original_entry_functions, new_entry_functions = functions(old_entry),functions(entry)
original_supervisor_functions,new_supervisor_functions=functions(old_supervisor),functions(supervisor)
assert all(new_entry_functions[k]==v for k,v in original_entry_functions.items() if k!='main')
assert all(new_supervisor_functions[k]==v for k,v in original_supervisor_functions.items() if k!='main')
report={'schema':'razr-r7-owned-math-termination-source-preparation-v1',
        'original_files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in (old_entry,old_supervisor)],
        'new_files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in (entry,supervisor)],
        'owned_identity_source_changed':False,'mathematical_algorithm_changed':False,
        'original_resource_gate_values_changed':False,'new_exit_confirmation_policy_explicit':True,
        'V9_actual_failure_reclassified':False,'actual_control_execution_completed':False,
        'scientific_execution_authorized_by_this_preparation':False,
        'compilation_only':True}
(root/'r7-supervisor/R7_OWNED_MATH_SOURCE_PREPARATION_V1.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
