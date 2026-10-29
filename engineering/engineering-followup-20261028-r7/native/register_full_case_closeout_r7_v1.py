"""Run unchanged original complete-pair validator and engineering exporter."""
from pathlib import Path
import argparse
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r7_core_closeout_helpers',ROOT/'register_and_run_native_local_r7_v4.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
DRIVERS=ROOT.parent/'r7-recovery/k3/source/k3full'

def sources():
    rec=json.loads((ROOT/'R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1.json').read_text())
    core.require(core.strict_inventory(DRIVERS)==rec['original_drivers'],'Original complete validator/exporter source set differs')
    return [core.bind(DRIVERS/k) for k in rec['original_drivers']]

def register(pose,phase):
    core.verify_sources();qualification=core.check_qualification();core.require_sealed_phase('core-reader')
    case=ROOT/('full-'+pose+'-attempt1');core.require(case.is_dir(),'Actual full pose case missing')
    out=ROOT/('full-'+pose+'-attempt1-engineering')
    prior=[]
    for mode in ('factory','readback'):
        actual=case/(mode+'-command-actual.json');runtime=case/(mode+'-runtime.json');controller=case/mode/'controller.json'
        report=case/mode/'worker/report.json';journal=case/mode/'worker/pairs.jsonl'
        core.require(all(json.loads(p.read_text())['completed'] for p in (actual,runtime,controller)),'Original full stage has not completed')
        prior += [core.bind(p) for p in (actual,runtime,controller,report,journal)]
    if phase=='verify-complete':
        script=DRIVERS/'verify_k3full_complete.py';payload=['--case',str(case),'--pose',pose]
        core.require(not (case/'K3FULL-complete-observation.json').exists(),'Original complete verifier output already exists')
    else:
        core.require(phase=='export-engineering','Unknown closeout phase')
        complete=case/'K3FULL-complete-observation.json';closed=case/'verify-complete-command-actual.json'
        core.require(json.loads(complete.read_text())['complete_full_pair_execution'] and json.loads(closed.read_text())['completed'],'Original complete verification failed')
        prior += [core.bind(complete),core.bind(closed)]
        script=DRIVERS/'export_k3full_engineering.py';payload=['--case',str(case),'--output',str(out)]
        core.require(not out.exists(),'Fresh engineering output required')
    bound_sources=sources()+[core.bind(p) for p in (Path(__file__),ROOT/'register_and_run_native_local_r7_v4.py',core.QUALIFIER,core.ENTRY)]
    limits=json.loads((core.ASSETS/'R5_CLOUD_NATIVE_SCIENCE_TEMPLATE.json').read_text())['original_resource_limits']
    rp=core.save(case/(phase+'-runtime-contract.json'),{
        'schema':'RAZR_R7_ORIGINAL_FULL_CASE_CLOSEOUT_RUNTIME_CONTRACT_V1','entry_identity':core.identity(core.ENTRY),
        'expected_entry_contract':str(case/(phase+'-runtime-contract.json')),'expected_receipt':str(case/(phase+'-runtime.json')),
        'expected_script_arguments':payload,'script':str(script),'script_identity':core.identity(script),
        'qualifier_source':str(core.QUALIFIER),'qualification':core.bind(qualification),'bound_sources':bound_sources,
        'maximum_receipt_bytes':4194304,'native_original_six_limits':limits,'full_factory_child_module_origins_claimed':False})
    worker=[str(core.FUNCTIONAL/'.venv/bin/python'),'-I','-B',str(core.ENTRY),'--contract',str(rp),'--receipt',str(case/(phase+'-runtime.json')),'--',*payload]
    ep=core.save(case/(phase+'-supervision-contract.json'),{
        'schema':'RAZR_R7_ORIGINAL_FULL_CLOSEOUT_SUPERVISION_CONTRACT_V1','supervisor_sha256':core.identity(core.SUPERVISOR)['sha256'],
        'resource_limits':limits,'runtime_contract':core.bind(rp),'exact_worker_command':worker})
    command=[sys.executable,'-B',str(core.SUPERVISOR),'--contract',str(ep),'--out',str(case/(phase+'-owned')),*worker]
    setup=json.loads((ROOT/'setup-install_only-v3/R7_FRESH_LOCAL_RUNTIME_SETUP_ACTUAL_V1.json').read_text())
    rec={'schema':'RAZR_R7_ORIGINAL_FULL_CASE_CLOSEOUT_COMMAND_V1','phase':phase,'pose':pose,'case':str(case),
         'registered_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'command':command,'worker_command':worker,'cwd':str(core.FUNCTIONAL),
         'supervision_contract':core.bind(ep),'bound_inputs':bound_sources+prior+[core.bind(p) for p in (rp,ep,qualification,core.SUPERVISOR)],
         'environment_overrides':{'GITHUB_WORKSPACE':str(core.FUNCTIONAL)},'hosted_identity_claimed':False,
         'pinned_uv_directory':str(Path(setup['uv']['executable']).parent),
         'capacity_basis':{'algorithm':'Read original full matrices/journals and exactcopy all declared existing engineering inputs; no new CAD arithmetic',
                           'expected_pair_rows':23562,'expected_journal_events':47124,'existing_prerequisite_bytes':408408534,
                           'estimated_seconds':[5,60],'original_native_limits_applied_conservatively':limits}}
    p=core.save(case/(phase+'-command.json'),rec);print(json.dumps({'registered':str(p),'identity':core.identity(p)}))

def execute(path):
    c=json.loads(path.read_text());before=core.identity(path)
    for x in c['bound_inputs']:core.require(core.identity(x['path'])==x['identity'],'Bound closeout input changed')
    target=path.with_name(path.stem+'-actual.json');core.require(not target.exists(),'New actual closeout receipt required')
    env=dict(os.environ);env.update(c['environment_overrides']);env['PATH']=c['pinned_uv_directory']+os.pathsep+env['PATH'];env['PYTHONDONTWRITEBYTECODE']='1'
    start=time.monotonic()
    with path.with_suffix('.stdout').open('xb') as out,path.with_suffix('.stderr').open('xb') as err:
        result=subprocess.run(c['command'],cwd=c['cwd'],env=env,stdout=out,stderr=err)
    case=Path(c['case']);controller=case/(c['phase']+'-owned/controller.json');runtime=case/(c['phase']+'-runtime.json')
    cv=json.loads(controller.read_text()) if controller.exists() else None;rv=json.loads(runtime.read_text()) if runtime.exists() else None
    unchanged=all(core.identity(x['path'])==x['identity'] for x in c['bound_inputs']) and core.identity(path)==before
    command_bound=bool(cv and cv['command']==c['worker_command'] and cv['contract_sha256']==c['supervision_contract']['identity']['sha256'])
    rec={'schema':'RAZR_R7_ORIGINAL_FULL_CASE_CLOSEOUT_ACTUAL_V1','command_record':core.bind(path),
         'exit_code':result.returncode,'seconds':time.monotonic()-start,'all_bound_inputs_unchanged':unchanged,
         'actual_original_supervisor_argv_bound':command_bound,'runtime':core.bind(runtime) if runtime.exists() else None,
         'controller':core.bind(controller) if controller.exists() else None,
         'stdout':core.bind(path.with_suffix('.stdout')),'stderr':core.bind(path.with_suffix('.stderr')),
         'completed':result.returncode==0 and unchanged and command_bound and bool(cv and cv['completed']) and bool(rv and rv['completed'])}
    core.save(target,rec);print(json.dumps(rec));return 0 if rec['completed'] else result.returncode or 2

def seal(pose):
    case=ROOT/('full-'+pose+'-attempt1');engineering=ROOT/('full-'+pose+'-attempt1-engineering')
    for phase in ('factory','readback','verify-complete','export-engineering'):
        core.require(json.loads((case/(phase+'-command-actual.json')).read_text())['completed'],'Incomplete full case phase')
    summary=json.loads((case/'K3FULL-complete-observation.json').read_text());core.require(summary['complete_full_pair_execution'],'Original complete verifier failed')
    manifest=json.loads((engineering/'ENGINEERING_MANIFEST.json').read_text());actual=core.strict_inventory(engineering)
    core.require(set(actual)==set(manifest['members'])|{'ENGINEERING_MANIFEST.json'},'Actual complete engineering member set differs')
    for rel,ref in manifest['members'].items():core.require(actual[rel]=={'bytes':ref['bytes'],'sha256':ref['sha256']},'Engineering original/projection hash differs')
    raw=core.strict_inventory(case)
    rec={'schema':'RAZR_R7_COMPLETE_FINITE_POSE_FINAL_SEAL_V1','pose':pose,'completed':True,
         'raw_members':raw,'engineering_members':actual,'raw_bytes':sum(x['bytes'] for x in raw.values()),
         'engineering_bytes':sum(x['bytes'] for x in actual.values()),'complete_full_pair_execution':True,
         'finite_state_clear':summary['finite_state_clear'],'remaining_unproved_domains':summary['remaining_unproved_domains'],
         'full_continuous_G2':False,'physical_qualification':False,'strength_qualified':False,'manufacturing_go':False}
    p=core.save(ROOT/('R7_'+pose.upper()+'_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json'),rec)
    print(json.dumps({'seal':str(p),'identity':core.identity(p),'raw_bytes':rec['raw_bytes'],'engineering_bytes':rec['engineering_bytes'],'finite_state_clear':rec['finite_state_clear']}))

def main():
    ap=argparse.ArgumentParser(allow_abbrev=False);sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('register');p.add_argument('pose',choices=['near','far']);p.add_argument('phase',choices=['verify-complete','export-engineering'])
    p=sub.add_parser('execute');p.add_argument('record',type=Path)
    p=sub.add_parser('seal');p.add_argument('pose',choices=['near','far'])
    a=ap.parse_args()
    if a.action=='register':register(a.pose,a.phase);return 0
    if a.action=='seal':seal(a.pose);return 0
    return execute(a.record.resolve())

if __name__=='__main__':raise SystemExit(main())
