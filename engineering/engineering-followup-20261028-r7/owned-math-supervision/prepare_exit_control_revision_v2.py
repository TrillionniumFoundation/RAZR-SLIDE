"""Tighten preregistered control acceptance to exact expected rejection reasons."""
import ast,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];old=root/'r7-supervisor/exercise_owned_exit_confirmation_r7_v1.py';new=root/'r7-supervisor/exercise_owned_exit_confirmation_r7_v2.py'
assert not new.exists();text=old.read_text()
expected={
 'completed-but-stays-live':'did not actually exit within the one original sampling interval',
 'incomplete-entry':'a bounded regular entry receipt must already exist',
 'different-key':'sampling error is not an eligible missing memory field',
 'identity-error':'sampling error is not an eligible missing memory field',
 'wrong-nonce':'entry receipt is not bound to this Popen PID/starttime/namespace/nonce',
 'wrong-starttime':'entry receipt is not bound to this Popen PID/starttime/namespace/nonce',
 'wrong-Popen-binding':'the original verified owned Popen handshake is required',
 'zero-peak':'a positive in-limit original worker peak RSS is required',
 'over-limit-peak':'a positive in-limit original worker peak RSS is required',
 'wrong-argv':'actual same-run mathematical contract, arguments or output binding differs',
 'changed-math-contract-before':'actual same-run mathematical contract, arguments or output binding differs',
 'changed-math-contract-during':'completed entry receipt, source or contract changed during confirmation',
 'exit-nonzero-after-receipt':'owned completed entry subsequently exited nonzero',
 'original-resource-gate-failure':'explicit original resource-gate rejection control',
 'validation-exceeds-one-interval':'no original sample interval or wall budget remains',
 'second-attempt':'at most one completed-entry exit confirmation is allowed',
}
needle='WORKER_SOURCE=';assert text.count(needle)==1;text=text.replace(needle,'EXPECTED_REJECTIONS = '+repr(expected)+'\n'+needle)
needle="        write(directory/'control.json',row);results.append(row)";assert text.count(needle)==1
text=text.replace(needle,"        if not expected:\n            row['expected_rejection_message'] = EXPECTED_REJECTIONS[name]\n            row['passed'] = row['passed'] and row.get('rejection',{}).get('message') == EXPECTED_REJECTIONS[name]\n        write(directory/'control.json',row);results.append(row)")
needle="    need(c['cases']==[list(x) for x in CASES],'registered cases differ')";assert text.count(needle)==1
text=text.replace(needle,needle+"\n    need(c['expected_rejections'] == EXPECTED_REJECTIONS, 'registered rejection reasons differ')")
needle="        write(args.out/'report.json',report)";assert text.count(needle)==1
text=text.replace(needle,"        current_bytes=sum(p.stat().st_size for p in args.out.rglob('*') if p.is_file())\n        report['control_output_bytes_before_final_report']=current_bytes\n        encoded=json.dumps(report,indent=2)+'\\n'\n        need(current_bytes+len(encoded.encode())<=4194304,'registered 4MiB actual control output cap')\n        (args.out/'report.json').write_text(encoded)")
new.write_text(text);compile(text,str(new),'exec',dont_inherit=True,optimize=0)
def ident(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
contract_path=root/'r7-supervisor/R7_ACTUAL_PROCESS_CONTROLS_CONTRACT_V2.json';assert not contract_path.exists()
c=json.loads((root/'r7-supervisor/R7_ACTUAL_PROCESS_CONTROLS_CONTRACT_V1.json').read_text());c.update(schema='razr-r7-owned-exit-confirmation-actual-controls-contract-v2',harness=ident(new),expected_rejections=expected)
contract_path.write_text(json.dumps(c,indent=2)+'\n')
report={'schema':'razr-r7-control-revision-v2-preparation','V1_source_preserved':ident(old),'V1_actual_executed':False,'new_source':ident(new),'new_contract':ident(contract_path),'negative_controls_now_require_exact_registered_rejection_reason':True,'actual_complete_output_cap_enforced':True,'supervisor_or_entry_source_changed':False,'actual_controls_executed':False}
(root/'r7-supervisor/R7_ACTUAL_PROCESS_CONTROLS_PREPARATION_V2.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
