"""Preserve V1; close independently found final timing and math-contract gaps."""
import ast,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];src=root/'r7-supervisor/source-v1';dst=root/'r7-supervisor/source-v2'
dst.mkdir(exist_ok=False)
def identity(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
entry=dst/'run_owned_pure_math_r7_v1.py';entry.write_bytes((src/entry.name).read_bytes())
old=src/'supervise_owned_pure_math_r7_v1.py';text=old.read_text()
needle="    evidence['original_Popen_confirmed_exit_code'] = code\n    evidence['actual_elapsed_seconds'] = time.monotonic() - detected\n    observe()\n    require(evidence['actual_elapsed_seconds'] <= SAMPLING_INTERVAL_SECONDS,\n            'actual exit confirmation exceeded one original sampling interval')\n"
replacement="    evidence['original_Popen_confirmed_exit_code'] = code\n    evidence['waited_exit_elapsed_seconds'] = time.monotonic() - detected\n    observe()\n"
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle="    require(sha(receipt_path) == receipt_sha and sha(contract_path) == report['contract_sha256'] and\n"
replacement="    require(sha(receipt_path) == receipt_sha and sha(contract_path) == report['contract_sha256'] and\n            sha(__file__) == contract['supervisor_sha256'] and\n            sha(math_contract) == contract['registered_math_contract_sha256'] and\n"
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle="    require(code == 0, 'owned completed entry subsequently exited nonzero')\n    evidence['completed'] = True\n"
replacement="    require(code == 0, 'owned completed entry subsequently exited nonzero')\n    observe()\n    evidence['actual_elapsed_seconds'] = time.monotonic() - detected\n    require(evidence['actual_elapsed_seconds'] <= SAMPLING_INTERVAL_SECONDS,\n            'actual exit confirmation including all validation exceeded one original sampling interval')\n    require(time.monotonic() - started <= contract['wall_seconds'],\n            'actual final exit confirmation exceeded the original wall limit')\n    evidence['completed'] = True\n"
assert text.count(needle)==1;text=text.replace(needle,replacement)
new=dst/'supervise_owned_pure_math_r7_v2.py';new.write_text(text);compile(text,str(new),'exec',dont_inherit=True,optimize=0)
def functions(p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
a,b=functions(old),functions(new);assert set(a)==set(b)
assert all(a[k]==b[k] for k in a if k!='confirm_completed_entry_exit')
report={'schema':'razr-r7-owned-math-exit-confirmation-v2-narrow-preparation','superseded_V1_preserved':identity(old),'new_source':identity(new),'entry_unchanged_from_V1':identity(entry),'changed_function_only':'confirm_completed_entry_exit','final_timing_now_includes_all_receipt_source_math_contract_and_resource_checks':True,'original_resource_gate_values_changed':False,'actual_controls_executed':False,'scientific_run_authorized':False}
(root/'r7-supervisor/R7_OWNED_MATH_SOURCE_PREPARATION_V2.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
