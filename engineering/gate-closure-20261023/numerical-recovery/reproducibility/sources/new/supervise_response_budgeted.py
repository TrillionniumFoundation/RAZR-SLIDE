"""External bounded supervisor for one complete-body response rebuild.

Bounds wall time even while Python is inside SuperLU.  Cgroup file cache is
reclaimable, so the stop metric counts anonymous/shmem and unreclaimable kernel
memory explicitly.  A resource stop is not a numerical convergence failure.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
ROOT=Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
PRIVATE=Path('/tmp/razr-fe-20261023')
CGROUP=Path('/sys/fs/cgroup')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def memory():
    values={line.split()[0]:int(line.split()[1]) for line in (CGROUP/'memory.stat').read_text().splitlines()}
    kernel=max(values.get('kernel',0)-values.get('slab_reclaimable',0),0)
    nonreclaimable=values['anon']+values.get('shmem',0)+kernel+values.get('unevictable',0)
    return {'cgroup_current':int((CGROUP/'memory.current').read_text()),
            'cgroup_limit':int((CGROUP/'memory.max').read_text()),
            'anon':values['anon'],'shmem':values.get('shmem',0),
            'kernel_excluding_reclaimable_slab':kernel,
            'estimated_unreclaimable_bytes':nonreclaimable}


def write(path,value):
    temporary=path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    os.replace(temporary,path)


def main(args):
    started=time.monotonic()
    attempt=args.attempt_label or (args.body+('-resumed' if args.resume_manifest is not None else '-chunked'))
    assert all(c.isalnum() or c in '-_' for c in attempt)
    control=PRIVATE/'supervision'/attempt
    control.mkdir(parents=True,exist_ok=False)
    output=PRIVATE/'base-response-budgeted'/attempt
    worker=BASE/'rebuild_base_response_budgeted.py'
    limit=int(6.8*1024**3)
    snapshot=memory()
    # Panel's completed 2,560-column attempt measured 2.5601 GiB peak RSS.
    # The mapped variant removes 271 MiB anonymous Kff and releases LU before
    # full-H validation. AS remains 4.25 GiB and the
    # independently measured 6.8 GiB whole-cgroup watchdog remains unchanged.
    # Frame has no factor measurement yet, so reserve its entire AS ceiling.
    incremental_reserve_gib=2.4 if args.body=='panel' else 4.25
    state={'schema':'razr-full-response-bounded-supervisor-v1','body':args.body,
           'worker_source':str(worker),'worker_sha256':digest(worker),
           'supervisor_sha256':digest(Path(__file__)),'address_space_limit_GiB':4.25,
           'cgroup_unreclaimable_stop_bytes':limit,'wall_time_limit_seconds':600,
           'output':str(output),'initial_memory':snapshot,'finished':False,
           'initial_incremental_memory_reserve_GiB':incremental_reserve_gib,
           'numerical_failure_implied_by_resource_stop':False}
    disk=os.statvfs(PRIVATE)
    available_disk=disk.f_bavail*disk.f_frsize
    start_disk_floor=(1024 if args.body=='panel' else 1152)*1024**2
    state.update(initial_nonprivileged_available_disk_bytes=available_disk,
                 initial_disk_required_bytes=start_disk_floor,
                 disk_budget_uses_nonprivileged_available_blocks=True)
    if available_disk<start_disk_floor:
        state.update(finished=True,status='not_started_insufficient_disk_margin')
        write(control/'report.json',state);print(json.dumps(state));return 3
    if snapshot['estimated_unreclaimable_bytes']+int(incremental_reserve_gib*1024**3)>limit:
        state.update(finished=True,status='not_started_insufficient_memory_margin')
        write(control/'report.json',state);print(json.dumps(state));return 3
    command=[str(ROOT/'.venv/bin/python'),'-B',str(worker),'--body',args.body,
             '--volume',str(PRIVATE/'volume-rebuild'),'--output',str(output),
             '--seconds','600','--batch','8','--memory-gib','4.25']
    if args.resume_manifest is not None:
        assert args.resume_sha256 is not None
        command+=['--resume-manifest',str(args.resume_manifest),'--resume-sha256',args.resume_sha256]
    else:
        assert args.resume_sha256 is None
    state['command']=command
    environment=os.environ.copy()
    environment.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    reason=None
    with (control/'worker.log').open('wb') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,
                                 env=environment,cwd=str(BASE),start_new_session=True)
        state['pid']=process.pid
        last_update=-100.0
        maximum_unreclaimable=0
        while process.poll() is None:
            now=time.monotonic()-started
            current=memory()
            maximum_unreclaimable=max(maximum_unreclaimable,current['estimated_unreclaimable_bytes'])
            if current['estimated_unreclaimable_bytes']>limit:
                reason='cgroup_unreclaimable_memory_guard'
            elif now>600:
                reason='wall_time_guard'
            else:
                disk=os.statvfs(PRIVATE)
                if disk.f_bavail*disk.f_frsize<500*1024**2:
                    reason='disk_reserve_guard'
            if now-last_update>=15 or reason:
                state.update(seconds=now,memory=current,maximum_unreclaimable_bytes=maximum_unreclaimable,
                             resource_stop_reason=reason)
                write(control/'progress.json',state)
                print(json.dumps({'body':args.body,'seconds':now,'unreclaimable_bytes':current['estimated_unreclaimable_bytes'],
                                  'pid':process.pid,'stop':reason}),flush=True)
                last_update=now
            if reason:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait()
                break
            time.sleep(0.5)
        code=process.wait()
    state.update(finished=True,exit_code=code,seconds=time.monotonic()-started,
                 final_memory=memory(),resource_stop_reason=reason,
                 status='worker_completed' if code==0 else 'worker_failed_or_stopped')
    progress=output/'progress.json'
    if progress.is_file():
        state['worker_progress_sha256']=digest(progress)
        state['worker_final_progress']=json.loads(progress.read_text())
    write(control/'report.json',state)
    print(json.dumps({'body':args.body,'status':state['status'],'exit_code':code,'resource_stop_reason':reason,
                      'seconds':state['seconds'],'report':str(control/'report.json')}),flush=True)
    return 0 if code==0 else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body',choices=('panel','frame'),required=True)
    parser.add_argument('--resume-manifest',type=Path)
    parser.add_argument('--resume-sha256')
    parser.add_argument('--attempt-label')
    raise SystemExit(main(parser.parse_args()))
