"""Finite real-process controls for the new bounded completed-entry confirmation.

Sampling failures are explicitly injected stimuli. This does not claim to have
reproduced the Linux kernel timing of the original V9 observation or any science.
"""
import argparse,copy,hashlib,importlib.util,json,os,resource,signal,subprocess,sys,time,traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'r7-supervisor/source-v2'
SUPERVISOR=SOURCE/'supervise_owned_pure_math_r7_v2.py'
ENTRY=SOURCE/'run_owned_pure_math_r7_v1.py'
OWNED=ROOT/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/r4/additional-bspline-v1/source/source-original/owned_process.py'
CASES=[
    ('completed-exit-VmRSS','VmRSS',True),
    ('completed-exit-VmHWM','VmHWM',True),
    ('completed-but-stays-live','VmRSS',False),
    ('incomplete-entry','VmRSS',False),
    ('different-key','Pid',False),
    ('identity-error','ValueError',False),
    ('wrong-nonce','VmRSS',False),
    ('wrong-starttime','VmRSS',False),
    ('wrong-Popen-binding','VmRSS',False),
    ('zero-peak','VmRSS',False),
    ('over-limit-peak','VmRSS',False),
    ('wrong-argv','VmRSS',False),
    ('changed-math-contract-before','VmRSS',False),
    ('changed-math-contract-during','VmRSS',False),
    ('exit-nonzero-after-receipt','VmRSS',False),
    ('original-resource-gate-failure','VmRSS',False),
    ('validation-exceeds-one-interval','VmRSS',False),
    ('second-attempt','VmRSS',False),
]
WORKER_SOURCE='''"""Explicit non-scientific real-process exit-control fixture."""
import argparse,atexit,json,os,time
from pathlib import Path
p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--contract',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
c=json.loads(a.contract.read_text());a.output.mkdir(exist_ok=False)
def finish():
    time.sleep(c['exit_delay_seconds'])
    if c.get('mutate_math_after_receipt'):a.contract.write_text(json.dumps({**c,'actual_mutation_after_receipt':True})+'\\n')
    if c.get('nonzero_after_receipt'):os._exit(7)
atexit.register(finish)
time.sleep(c['worker_delay_seconds'])
(a.output/'fixture.json').write_text(json.dumps({'fixture_only':True,'scientific_geometry_executed':False})+'\\n')
'''

def need(value,message):
    if not value:raise ValueError(message)

def ident(p):
    p=Path(p).resolve();return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def load_module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')

def actual_controls(out,registration):
    supervisor=load_module('r7_control_supervisor',SUPERVISOR)
    owned=load_module('r7_control_original_owned',OWNED)
    worker=out/'registered_fixture_worker.py';worker.write_text(WORKER_SOURCE)
    need(ident(worker)['sha256']==registration['fixture_source_sha256'],'registered fixture bytes differ')
    results=[]
    for name,exception_name,expected in CASES:
        directory=out/name;directory.mkdir();output=directory/'worker-output';receipt=directory/'entry-receipt.json'
        math_path=directory/'math-contract.json'
        math_contract={'schema':'razr-r7-nonscientific-exit-fixture-v1','case':name,
                       'worker_delay_seconds':0.6 if name=='incomplete-entry' else 0.0,
                       'exit_delay_seconds':0.65 if name=='completed-but-stays-live' else 0.08,
                       'mutate_math_after_receipt':name=='changed-math-contract-during',
                       'nonzero_after_receipt':name=='exit-nonzero-after-receipt'}
        write(math_path,math_contract)
        contract={'supervisor_sha256':ident(SUPERVISOR)['sha256'],
                  'worker_entry':str(ENTRY),'worker_entry_sha256':ident(ENTRY)['sha256'],
                  'owned_process':ident(OWNED),'worker':ident(worker),
                  'canonical_worker_options':['--contract','--output'],
                  'registered_math_contract_sha256':ident(math_path)['sha256'],
                  'worker_output_directory':str(output),
                  'wall_seconds':600,'RSS_limit_bytes':805306368,'shared_ceiling_bytes':7301444403,
                  'disk_floor_bytes':104857600,'maximum_output_bytes':41943040,'metadata_margin_bytes':4194304,
                  'completed_entry_exit_confirmation_policy':supervisor.EXIT_CONFIRMATION_POLICY}
        contract_path=directory/'supervision-contract.json';write(contract_path,contract)
        arguments=['--','--contract',str(math_path),'--output',str(output)]
        command=[sys.executable,'-I','-S','-B',str(ENTRY),'--supervision-contract',str(contract_path),'--receipt',str(receipt),*arguments]
        row={'case':name,'stimulus':'explicit injected sampling exception against a real owned child',
             'expected_acceptance':expected,'injected_exception':exception_name,'command':command,
             'scientific_worker':False,'kernel_failure_reproduction_claimed':False,'accepted':False}
        report={'contract_sha256':ident(contract_path)['sha256'],'owned_child_identity_verified':False,
                'bounded_exit_confirmation_count':0,'resource_stop':None}
        channel=owned.OwnedChildChannel(ENTRY);child=None;started=time.monotonic();observations=[]
        def observe(memory=None):
            sample=supervisor.resources(directory);sample['elapsed_seconds']=time.monotonic()-started
            sample['owned_worker_memory']=memory
            sample['actual_output_bytes']=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()) if output.exists() else 0
            observations.append(sample)
            need(sample['elapsed_seconds']<=contract['wall_seconds'],'original wall_seconds gate')
            need(sample['disk_available_bytes']>=contract['disk_floor_bytes'],'original disk floor gate')
            need(sample['shared_unreclaimable_bytes']<=contract['shared_ceiling_bytes'],'original shared ceiling gate')
            need(memory is None or max(memory.values())<=contract['RSS_limit_bytes'],'original worker RSS gate')
            need(sample['actual_output_bytes']<=contract['maximum_output_bytes'],'original output bytes gate')
        try:
            first=supervisor.resources(directory)
            need(first['disk_available_bytes']>=contract['disk_floor_bytes']+contract['maximum_output_bytes']+contract['metadata_margin_bytes'],'original startup disk gate')
            need(first['shared_unreclaimable_bytes']+contract['RSS_limit_bytes']<=contract['shared_ceiling_bytes'],'original startup shared gate')
            with (directory/'execution.log').open('wb') as log:
                child=subprocess.Popen(command,env=channel.child_env(dict(os.environ)),pass_fds=channel.pass_fds,
                                       start_new_session=True,stdout=log,stderr=subprocess.STDOUT)
                channel.after_spawn();handshake=channel.accept(child,timeout_seconds=2,poll_callback=observe)
                report['owned_child_handshake']=copy.deepcopy(handshake);report['owned_child_identity_verified']=True
                row['original_Popen_pid']=child.pid;row['actual_handshake']=handshake
                if name!='incomplete-entry':
                    deadline=time.monotonic()+1
                    while True:
                        need(child.poll() is None,'entry exited before registered live-process stimulus')
                        if receipt.exists():
                            try:entry_data=json.loads(receipt.read_text())
                            except json.JSONDecodeError:entry_data=None
                            if entry_data and entry_data.get('completed') is True:break
                        need(time.monotonic()<deadline,'completed entry not observed in finite control window')
                        time.sleep(0.001)
                    row['original_entry_receipt_before_stimulus']=ident(receipt)
                    if name=='wrong-nonce':entry_data['owned_execution_nonce']='0'*64
                    if name=='wrong-starttime':entry_data['owned_execution_identity']['stat']['starttime_ticks']+=1
                    if name=='zero-peak':entry_data['peak_RSS_bytes']=0
                    if name=='over-limit-peak':entry_data['peak_RSS_bytes']=contract['RSS_limit_bytes']+1
                    if name=='wrong-argv':entry_data['canonical_worker_arguments'][-1]+='-different'
                    if name in ('wrong-nonce','wrong-starttime','zero-peak','over-limit-peak','wrong-argv'):write(receipt,entry_data)
                if name=='wrong-Popen-binding':channel.child_pid+=1
                if name=='changed-math-contract-before':write(math_path,{**math_contract,'actual_mutation_before_confirmation':True})
                if name=='second-attempt':report['bounded_exit_confirmation_count']=1
                injected=ValueError('explicit owned identity error control') if exception_name=='ValueError' else KeyError(exception_name)
                real_observe=observe
                if name=='original-resource-gate-failure':
                    def observe(memory=None):
                        real_observe(memory)
                        raise RuntimeError('explicit original resource-gate rejection control')
                if name=='validation-exceeds-one-interval':
                    def observe(memory=None):
                        real_observe(memory);time.sleep(0.21)
                row['actual_live_before_injected_missing_sample']=child.poll() is None
                need(row['actual_live_before_injected_missing_sample'],'live Popen before injected error required')
                try:
                    exit_code=supervisor.confirm_completed_entry_exit(injected,child,channel,contract,contract_path,
                                                                      receipt,arguments,report,started,observe)
                    row.update(accepted=True,returned_exit_code=exit_code)
                except Exception as exc:
                    row['rejection']={'type':type(exc).__name__,'message':str(exc)}
        except Exception as exc:
            row['control_execution_failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        finally:
            if child is not None:
                if child.poll() is None:
                    try:os.killpg(child.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:child.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid,signal.SIGKILL);child.wait()
                row['actual_original_Popen_final_returncode']=child.returncode
            channel.close();row['owned_descriptors_closed']=not channel.descriptors
        row.update(confirmation_report=report,actual_resource_observations=observations,
                   elapsed_seconds=time.monotonic()-started,
                   passed=('control_execution_failure' not in row and row['accepted'] is expected and row['owned_descriptors_closed']))
        if expected:
            row['passed']=row['passed'] and report.get('bounded_exit_confirmation',{}).get('completed') is True and child.returncode==0
        write(directory/'control.json',row);results.append(row)
    return results

def main():
    p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    c=json.loads(args.contract.read_text());need(ident(__file__)==c['harness'],'registered harness differs')
    need(all(ident(Path(v['path']))==v for v in c['bound_sources']),'registered reviewed sources differ')
    need(c['cases']==[list(x) for x in CASES],'registered cases differ')
    need(not args.out.exists(),'new actual control output required');args.out.mkdir(parents=True)
    resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912));started=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('registered60sactualprocesscontrols')));signal.alarm(60)
    report={'schema':'razr-r7-owned-exit-confirmation-real-process-controls-v1','completed':False,'contract':ident(args.contract),'scientific_execution':False,'kernel_exit_gap_reproduction_claimed':False}
    try:
        results=actual_controls(args.out,c);report['cases']=results
        report['passed_count']=sum(x['passed'] for x in results);report['case_count']=len(results)
        report['sources_unchanged']=all(ident(Path(v['path']))==v for v in c['bound_sources'])
        report['completed']=len(results)==18 and all(x['passed'] for x in results) and report['sources_unchanged']
    except Exception as exc:report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);report.update(elapsed_seconds=time.monotonic()-started,peak_parent_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write(args.out/'report.json',report)
    print(json.dumps({k:report.get(k) for k in ('completed','case_count','passed_count','failure','elapsed_seconds','peak_parent_RSS_bytes')}))
    return 0 if report['completed'] else 2

if __name__=='__main__':raise SystemExit(main())
