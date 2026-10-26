#!/usr/bin/env python3
"""Run the unchanged workflow native matrix locally with retained provenance."""
from __future__ import annotations
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
import yaml

ROOT=Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
EXPECTED='e76ff339cbd38610b42f550d1d990131233c8f7d'
OUT=Path('/tmp/razr-native-matrix-e76ff339-remaining')
PRIOR=Path('/workspace/scratch/95cd2986fdf2/ci_audit/native-matrix-e76ff339-final/report.json')
COMPLETION=PRIOR.with_name('capacity-stop-completion.json')
PYTHON=ROOT/'.venv/bin/python'
sys.path.insert(0,str(ROOT))
from tools.verify import snapshot, committed_bytes, sha
from tools.check_environment import inspect_environment

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def head(): return subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
def free():
    v=os.statvfs(OUT)
    return (v.f_bfree if os.geteuid()==0 else v.f_bavail)*v.f_frsize
def inventory(path):
    return [{'path':str(p.relative_to(path)),'bytes':p.stat().st_size,'sha256':sha(p)}
            for p in sorted(path.rglob('*')) if p.is_file() and not p.is_symlink()]
def bytes_used(): return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
def compress_verified(directory, files):
    archive=OUT/(directory.name+'.tar.gz')
    with tarfile.open(archive,'x:gz') as bundle:
        bundle.add(directory,arcname=directory.name,recursive=True)
    with tarfile.open(archive,'r:gz') as bundle:
        for item in files:
            member=bundle.extractfile(directory.name+'/'+item['path'])
            if member is None or hashlib.sha256(member.read()).hexdigest()!=item['sha256']:
                raise ValueError('compression verification differs: '+item['path'])
    receipt={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),
             'all_regular_members_reread_and_sha256_matched':True,'original_files':files}
    (OUT/(directory.name+'-archive-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    shutil.rmtree(directory)
    return receipt

OUT.mkdir(parents=True,exist_ok=False)
report={'schema':'razr-local-native-matrix-continuation-v1','started_utc':now(),'expected_head':EXPECTED,
        'scope':'remaining five unchanged native workflow jobs; first five are retained in the source-identical interrupted parent attempt; strict ten-job aggregation is separate',
        'hosted_execution':False,'full_motion_acceptance':False,'hardware_qualification':False,
        'candidate_go':False,'manufacturing_go':False,'jobs':[], 'passed':False,
        'disk_available_basis':'f_bfree for current uid 0, f_bavail otherwise; 300 MiB reserve and 430 MiB output compression threshold',
        'command_translation':'Only leading uv run --locked python is replaced by the already locked .venv/bin/python; RUNNER_TEMP points at a new per-job directory.',
        'controller_sha256':sha(Path(__file__))}
def save(): (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
try:
    if head()!=EXPECTED: raise ValueError('wrong initial commit')
    initial=snapshot(ROOT);identity=committed_bytes(ROOT,initial)
    if not identity['present_tracked_bytes_match_head']: raise ValueError('initial tracked source differs from HEAD')
    prior=json.loads(PRIOR.read_text());completion=json.loads(COMPLETION.read_text())
    if sha(PRIOR)!=completion['original_controller_report_sha256'] or not completion['completed_subset_source_and_environment_valid']:
        raise ValueError('parent completion receipt does not bind a valid source-identical subset')
    completed={job['id'] for job in prior['jobs'] if job['passed']}
    if completed!={'thin','mounted','coupling','pawl','serviceable'} or initial!=prior['source_sha256_before']:
        raise ValueError('completed parent subset or source identity differs')
    report['parent_report_sha256']=sha(PRIOR);report['parent_completion_sha256']=sha(COMPLETION)
    report['parent_completed_job_ids']=sorted(completed)
    report['source_head_before']=head();report['source_identity_before']=identity
    report['source_sha256_before']=initial;report['environment_before']=inspect_environment(ROOT)
    if not report['environment_before']['passed']: raise ValueError('locked environment not reproduced')
    workflow=ROOT/'.github/workflows/research-ci.yml';report['workflow_sha256']=sha(workflow)
    definition=yaml.safe_load(workflow.read_text())['jobs']['native']
    jobs=definition['strategy']['matrix']['include']
    jobs=sorted(jobs,key=lambda item:(item['id']=='lateral-guide',item['id']=='phone-layout'))
    report['declared_full_matrix_job_ids']=[item['id'] for item in jobs]
    if len(jobs)!=10:raise ValueError('full native matrix scope changed')
    jobs=[item for item in jobs if item['id'] not in completed]
    report['declared_job_ids']=[item['id'] for item in jobs]
    report['declared_job_timeout_seconds']=definition['timeout-minutes']*60
    if len(jobs)!=5 or {item['id'] for item in jobs}!={'endpoint-joint','catalogue-joint','root-clearance','phone-layout','lateral-guide'}:raise ValueError('remaining native scope changed')
    save()
    for item in jobs:
        job_name=item['id'];job_dir=OUT/job_name;job_dir.mkdir()
        row={'id':job_name,'started_utc':now(),'disk_free_before':free(),'commands':[],
             'source_head_before':head(),'passed':False}
        report['jobs'].append(row);save();started=time.monotonic()
        if row['source_head_before']!=EXPECTED or snapshot(ROOT)!=initial:
            raise ValueError('source changed before '+job_name)
        env={**os.environ,'RUNNER_TEMP':str(job_dir),'PYTHONDONTWRITEBYTECODE':'1',
             'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}
        for number,line in enumerate(item['commands'].splitlines(),1):
            if not line.strip(): continue
            original=shlex.split(line)
            if original[:4]!=['uv','run','--locked','python']:
                raise ValueError('unexpected workflow command prefix')
            command=[str(PYTHON),*[token.replace('$RUNNER_TEMP',str(job_dir)) for token in original[4:]]]
            if any('$' in token for token in command): raise ValueError('unresolved workflow expansion')
            if free()<300*1024*1024: raise RuntimeError('disk reserve reached before '+job_name)
            remaining=definition['timeout-minutes']*60-(time.monotonic()-started)
            if remaining<=0: raise TimeoutError('workflow native job timeout reached')
            step={'workflow_command':line,'command':command,'started_utc':now(),'log':f'command-{number:02d}.log'}
            row['commands'].append(step);save();begin=time.monotonic()
            with (job_dir/step['log']).open('w') as stream:
                try:
                    proc=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=remaining)
                    step['exit_code']=proc.returncode
                except subprocess.TimeoutExpired:
                    step['exit_code']='TIMEOUT'
            step.update(seconds=round(time.monotonic()-begin,3),completed_utc=now(),log_sha256=sha(job_dir/step['log']))
            save()
            if step['exit_code']!=0: break
        after=snapshot(ROOT);after_identity=committed_bytes(ROOT,after)
        row.update(source_head_after=head(),source_bytes_unchanged=after==initial,
                   present_tracked_bytes_match_head=after_identity['present_tracked_bytes_match_head'],
                   seconds=round(time.monotonic()-started,3),completed_utc=now(),disk_free_after=free())
        row['passed']=(bool(row['commands']) and len(row['commands'])==len(item['commands'].splitlines())
                       and all(step['exit_code']==0 for step in row['commands'])
                       and row['source_bytes_unchanged'] and row['source_head_after']==EXPECTED
                       and row['present_tracked_bytes_match_head'])
        files=inventory(job_dir);row['files']=files;row['output_bytes']=sum(f['bytes'] for f in files)
        if files:  # Always archive completed private-temp output, verify every byte, then release originals.
            row['compression']=compress_verified(job_dir,files)
        save();print(json.dumps({'job':job_name,'passed':row['passed'],'seconds':row['seconds'],
                                'output_bytes':row['output_bytes'],'disk_free':free()}),flush=True)
        if not row['source_bytes_unchanged'] or row['source_head_after']!=EXPECTED:
            raise ValueError('source changed during '+job_name)
    after=snapshot(ROOT)
    report.update(source_sha256_after=after,source_head_after=head(),source_bytes_unchanged=after==initial,
                  source_identity_after=committed_bytes(ROOT,after),environment_after=inspect_environment(ROOT))
    report['passed']=(len(report['jobs'])==5 and all(job['passed'] for job in report['jobs'])
                      and after==initial and head()==EXPECTED and report['environment_after']['passed'])
except Exception as exc:
    report['execution_error']={'type':type(exc).__name__,'message':str(exc)}
finally:
    report['completed_utc']=now();report['output_total_bytes']=bytes_used();report['disk_free_final']=free();save()
print(json.dumps({'report':str(OUT/'report.json'),'passed':report['passed'],'error':report.get('execution_error')}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
