"""Run a named worker through the verified projection with full pre/post hashes."""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import traceback


def identity(path):
    h=hashlib.sha256(); size=0
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576), b''):
            h.update(block); size+=len(block)
    return {'bytes':size,'sha256':h.hexdigest()}


def require(condition,message):
    if not condition: raise ValueError(message)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-contract',type=Path,required=True)
    p.add_argument('--qualification',type=Path,required=True)
    p.add_argument('--runtime-receipt',type=Path,required=True)
    p.add_argument('--script',type=Path,required=True)
    p.add_argument('script_args',nargs=argparse.REMAINDER)
    a=p.parse_args(); args=a.script_args[1:] if a.script_args[:1]==['--'] else a.script_args
    report={'schema':'razr-r4-qualified-script-runtime-observation-v1',
        'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'launcher_identity':identity(__file__),'contract_identity':identity(a.runtime_contract),
        'qualification_identity':identity(a.qualification),'worker_identity':identity(a.script),
        'worker_script':str(a.script.resolve()),'worker_arguments':args,
        'worker_started':False,'worker_exit_code':None,'issues':[],
        'historical_execution_requalified':False,'universal_absence_of_other_side_effects_claimed':False,
        'OS_enforced_immutability_claimed':False,'compiled_kernel_formal_correctness_claimed':False}
    plan=None; contract=None; root=None; expected_records={}
    def save():
        a.runtime_receipt.parent.mkdir(parents=True,exist_ok=True)
        a.runtime_receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def observe():
        rows=[]
        for item in plan['payload_files']:
            alias=root/item['relative']
            bound=alias.is_symlink() and os.readlink(alias)==item['source']
            actual=identity(alias) if bound else None
            rows.append({'relative':item['relative'],'alias_bound':bound,'actual':actual,
                         'equal':bound and actual==item['identity']})
        return rows
    def nodes():
        expected={r['relative'] for r in plan['payload_files']} | set(expected_records)
        actual={str(q.relative_to(root)) for q in root.rglob('*') if q.is_file() or q.is_symlink()}
        records=[{'relative':relative,'equal':(root/relative).is_file() and not (root/relative).is_symlink()
                  and identity(root/relative)==value} for relative,value in expected_records.items()]
        return {'file_set_exact':actual==expected,'file_count':len(actual),'RECORD_observations':records,
                'all_43_RECORDs_unchanged':len(records)==43 and all(r['equal'] for r in records)}
    try:
        contract=json.loads(a.runtime_contract.read_text())
        qual=json.loads(a.qualification.read_text())
        require(qual['completed'] and qual['current43_payload_and_namespace_qualified'] and not qual['issues'],
                'Current projection is not qualified')
        require(qual['contract_identity']==report['contract_identity'] and
                qual['source_identity']==contract['validator_identity'], 'Qualification binding differs')
        plan_path=Path(contract['plan']['path'])
        require(identity(plan_path)=={k:contract['plan'][k] for k in ('bytes','sha256')}, 'Projection plan differs')
        plan=json.loads(plan_path.read_text());root=Path(plan['candidate_root'])
        expected_records={r['relative']:r['generated_record_identity'] for r in qual['record_observations']}
        report['payload_before']=observe()
        require(all(r['equal'] for r in report['payload_before']), 'Pre-execution payload identity failure')
        report['nodes_before']=nodes()
        require(report['nodes_before']['file_set_exact'] and report['nodes_before']['all_43_RECORDs_unchanged'],
                'Pre-execution candidate inventory/RECORD failure')
        entry_path=Path(contract['entry_source'])
        require(identity(entry_path)==contract['entry_identity'], 'Entry source differs')
        spec=importlib.util.spec_from_file_location('r4_frozen_projection_entry',entry_path)
        entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
        report['entry_state']=entry.activate(a.runtime_contract)
        report['worker_started']=True;save()
        sys.argv[:]=[str(a.script.resolve()),*args]
        try:
            runpy.run_path(str(a.script.resolve()),run_name='__main__')
            report['worker_exit_code']=0
        except SystemExit as exc:
            report['worker_exit_code']=exc.code if isinstance(exc.code,int) else 0 if exc.code is None else 1
            if not isinstance(exc.code,(int,type(None))):report['worker_exit_message']=str(exc.code)
    except BaseException as exc:
        report['issues'].append({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
    finally:
        if plan is not None:
            try:
                report['payload_after']=observe()
                report['nodes_after']=nodes()
                report['all_8112_payloads_unchanged_after_worker']=len(report['payload_after'])==8112 and all(r['equal'] for r in report['payload_after'])
                site=root/'lib/python3.12/site-packages'
                foreign=[]
                for name,module in list(sys.modules.items()):
                    paths=[getattr(module,'__file__',None),*list(getattr(module,'__path__',[]) or [])]
                    for item in paths:
                        if item and ('site-packages' in Path(item).parts or 'dist-packages' in Path(item).parts) and not Path(item).is_relative_to(site):
                            foreign.append({'module':name,'path':item})
                report['observed_foreign_installed_module_origins']=foreign
                report['plan_and_entry_and_contract_unchanged']=(identity(a.runtime_contract)==report['contract_identity'] and
                    identity(Path(contract['plan']['path']))=={k:contract['plan'][k] for k in ('bytes','sha256')} and
                    identity(Path(contract['entry_source']))==contract['entry_identity'])
                report['worker_source_unchanged']=identity(a.script)==report['worker_identity']
                report['qualification_and_launcher_unchanged']=(identity(a.qualification)==report['qualification_identity']
                    and identity(__file__)==report['launcher_identity'])
            except BaseException as exc:
                report['issues'].append({'phase':'postflight','type':type(exc).__name__,'message':str(exc)})
        report['completed']=(report['worker_exit_code']==0 and not report['issues'] and
            report.get('all_8112_payloads_unchanged_after_worker',False) and
            report.get('plan_and_entry_and_contract_unchanged',False) and
            report.get('nodes_after',{}).get('file_set_exact',False) and
            report.get('nodes_after',{}).get('all_43_RECORDs_unchanged',False) and
            report.get('qualification_and_launcher_unchanged',False) and
            report.get('worker_source_unchanged',False) and not report.get('observed_foreign_installed_module_origins',[]))
        report['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat();save()
    print(json.dumps({'runtime_receipt':str(a.runtime_receipt),'completed':report['completed'],
        'worker_exit_code':report['worker_exit_code'],'issues':report['issues']}),flush=True)
    return 0 if report['completed'] else 2


if __name__=='__main__': raise SystemExit(main())
