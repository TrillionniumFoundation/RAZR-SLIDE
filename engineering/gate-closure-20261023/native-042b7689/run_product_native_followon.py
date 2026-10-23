"""Run one unchanged EP4/EP5 native workflow and preserve a verified archive."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import signal
import subprocess
import tarfile
import time

ROOT = Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
GIB = 1024**3

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def resource_snapshot(folder):
    raw = {}
    for row in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines():
        key, value = row.split(); raw[key] = int(value)
    unrec = raw.get('anon', 0) + raw.get('shmem', 0) + max(0, raw.get('kernel', 0)-raw.get('slab_reclaimable', 0)) + raw.get('unevictable', 0)
    v = os.statvfs(folder)
    return {'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'available_disk_bytes': v.f_bavail*v.f_frsize,
            'estimated_unreclaimable_bytes': unrec,
            'anon_bytes': raw.get('anon'), 'shared_memory_bytes': raw.get('shmem')}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('ep4','ep5'), required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError('new output outside the repository required')
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty = subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    if head != args.expected_head or dirty:
        raise ValueError('exact clean functional source required')
    output.mkdir(parents=True)
    free_floor = (300 if args.kind=='ep4' else 400)*1024**2
    first = resource_snapshot(output)
    receipt = {'schema': 'razr-unchanged-native-workflow-controller-v1',
               'kind': args.kind, 'expected_head': args.expected_head,
               'controller_source_sha256': sha(__file__),
               'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'resource_start_floor_disk_bytes': free_floor,
               'resource_start_ceiling_unreclaimable_bytes': int(6.1*GIB),
               'runtime_disk_reserve_bytes': 100*1024**2,
               'runtime_unreclaimable_stop_bytes': int(6.8*GIB),
               'resource_observations': [first], 'worker_started': False,
               'hosted_execution': False, 'native_timeouts_changed': False,
               'candidate_go': False, 'fixture_fabrication_go': False,
               'manufacturing_go': False}
    def save():
        (output/'controller.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    if first['available_disk_bytes'] < free_floor or first['estimated_unreclaimable_bytes'] > 6.1*GIB:
        receipt.update(resource_start_refused=True, completed=False); save()
        return 3
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'OPENBLAS_NUM_THREADS':'1',
           'OMP_NUM_THREADS':'1', 'MKL_NUM_THREADS':'1', 'NUMEXPR_NUM_THREADS':'1'}
    python = str(ROOT/'.venv/bin/python')
    lock = subprocess.run([python,'-B','tools/check_environment.py','--output',str(output/'locked-environment.json')],
                          cwd=ROOT,env=env,capture_output=True,text=True)
    (output/'locked-environment.log').write_text(lock.stdout+lock.stderr)
    receipt['environment_exit_code'] = lock.returncode
    if lock.returncode:
        receipt.update(completed=False, error='complete locked environment preflight failed');save();return 2
    script = 'tools/verify_product_native.py' if args.kind=='ep4' else 'tools/verify_product_ep5_native.py'
    command = [python,'-B',script,'--expected-head',args.expected_head,'--output',str(output/'results'),
               '--timeout-seconds','1200' if args.kind=='ep4' else '3000']
    receipt.update(command=command, working_directory=str(ROOT), worker_started=True)
    save(); started = time.monotonic(); stopped = False
    with (output/'controller.log').open('wb') as log:
        child = subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        receipt['pid'] = child.pid;save(); last_recorded = started
        while child.poll() is None:
            time.sleep(2)
            now = resource_snapshot(output)
            if time.monotonic()-last_recorded>=20:
                receipt['resource_observations'].append(now);save();last_recorded=time.monotonic()
            if now['available_disk_bytes']<100*1024**2 or now['estimated_unreclaimable_bytes']>6.8*GIB:
                receipt.update(capacity_stop=True, capacity_stop_snapshot=now)
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                stopped=True;break
        exit_code=child.wait()
    receipt.update(worker_exit_code=exit_code, elapsed_seconds=time.monotonic()-started,
                   completed=not stopped, finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   head_after=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   worktree_clean_after=not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    report_path=output/'results/report.json'
    if report_path.is_file():
        report=json.loads(report_path.read_text())
        receipt.update(execution_checks_passed=report.get('execution_checks_passed') is True,
                       source_bytes_unchanged=report.get('source_bytes_unchanged'),
                       native_report_sha256=sha(report_path))
    save()
    members=[]
    for p in sorted((output/'results').rglob('*')):
        if p.is_file():members.append({'path':str(p.relative_to(output/'results')),'bytes':p.stat().st_size,'sha256':sha(p)})
    archive=output/(args.kind+'-native.tar.xz')
    try:
        with tarfile.open(archive,'w:xz',preset=3) as target:
            for row in members:
                capacity=resource_snapshot(output)
                if capacity['available_disk_bytes']<100*1024**2:
                    raise OSError('archive disk reserve fell below 100 MiB')
                target.add(output/'results'/row['path'],arcname=row['path'],recursive=False)
    except Exception as exc:
        receipt.update(archive_complete=False,archive_error=type(exc).__name__+': '+str(exc),
                       archive_partial_path=str(archive),original_members_compacted=False)
        receipt['resource_observations'].append(resource_snapshot(output));save()
        return 1
    with tarfile.open(archive,'r:xz') as source:
        actual={m.name:m for m in source.getmembers() if m.isfile()}
        if set(actual)!={r['path'] for r in members}:raise ValueError('archive member inventory differs')
        for row in members:
            member=actual[row['path']]
            with source.extractfile(member) as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if member.size!=row['bytes'] or digest!=row['sha256']:raise ValueError('archive member mismatch: '+row['path'])
    manifest={'schema':'razr-native-evidence-archive-v1','functional_commit':args.expected_head,
              'archive':archive.name,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),
              'members':members,'all_members_reread_and_sha256_matched':True}
    (output/'member-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    receipt.update(archive=archive.name,archive_complete=True,archive_sha256=manifest['archive_sha256'],archive_bytes=manifest['archive_bytes'],
                   verified_archive_member_count=len(members),verified_original_bytes=sum(r['bytes'] for r in members))
    # Only verified, reproducible temporary copies are compacted. Keep the original driver report directly readable.
    compacted=[]
    for row in members:
        p=output/'results'/row['path']
        if row['bytes']>1024**2 and row['path']!='report.json':
            if p.stat().st_nlink!=1 or sha(p)!=row['sha256']:raise ValueError('unsafe temporary-copy compaction')
            with p.open('wb'):pass
            compacted.append(row)
    receipt['compacted_temporary_members']=compacted;receipt['resource_observations'].append(resource_snapshot(output));save()
    print(json.dumps({k:receipt.get(k) for k in ('kind','expected_head','worker_exit_code','execution_checks_passed',
                     'source_bytes_unchanged','elapsed_seconds','verified_archive_member_count','archive_sha256')}))
    return 0 if (exit_code==0 and receipt.get('execution_checks_passed') and not stopped
                 and receipt.get('head_after')==args.expected_head
                 and receipt.get('worktree_clean_after')
                 and receipt.get('source_bytes_unchanged') is True) else 1

if __name__=='__main__':
    raise SystemExit(main())
