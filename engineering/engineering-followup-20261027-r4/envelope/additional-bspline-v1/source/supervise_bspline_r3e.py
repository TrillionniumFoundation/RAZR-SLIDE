"""R3E owned native extraction; original CAD resource guards retained."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'source-original'));import owned_process

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resource(path):
 d={k:int(v) for k,v in (r.split() for r in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())};s=os.statvfs(path)
 return {'disk_available_bytes':s.f_bavail*s.f_frsize,'shared_unreclaimable_bytes':d['anon']+d['shmem']+max(d['kernel']-d['slab_reclaimable'],0)+d.get('unevictable',0)}
def main():
 a=argparse.ArgumentParser();a.add_argument('--contract',required=True);a.add_argument('--python',required=True);a.add_argument('--output',required=True);a.add_argument('--reader-of');args=a.parse_args();out=Path(args.output)
 if out.exists():raise ValueError('fresh output required')
 out.mkdir(parents=True);c=json.loads(Path(args.contract).read_text());source=HERE/'extract_bspline_r3e.py';command=[args.python,'-B',str(source),'--contract',str(Path(args.contract).resolve()),'--output',str(out/'worker')]
 if args.reader_of:command+=['--reader-of',str(Path(args.reader_of).resolve())]
 first=resource(out);r={'schema':'R3E-original-CAD-guard-owned-supervision-v1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'contract_sha256':sha(args.contract),'supervisor_sha256':sha(__file__),'worker_sha256':sha(source),'command':command,'limits':c,'worker_started':False,'completed':False,'observations':[first]}
 def save(): (out/'controller.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 if first['disk_available_bytes']<c['startup_disk_floor_bytes'] or first['shared_unreclaimable_bytes']+c['startup_additional_memory_bytes']>c['shared_ceiling_bytes']:
  r['resource_start_refused']=True;save();print(json.dumps({'resource_start_refused':True,'actual':first}));return 3
 channel=None;child=None;start=time.monotonic();last=start;stop=None
 def observe(memory=None):
  nonlocal stop,last
  s=resource(out);elapsed=time.monotonic()-start
  if elapsed>c['wall_seconds']:stop='wall_time'
  elif s['disk_available_bytes']<c['runtime_disk_floor_bytes']:stop='disk'
  elif s['shared_unreclaimable_bytes']>c['shared_ceiling_bytes']:stop='shared'
  elif memory is not None and max(memory.values())>c['RSS_limit_bytes']:stop='worker_RSS'
  if stop or time.monotonic()-last>2:r['observations'].append({**s,'elapsed_seconds':elapsed,'owned_worker_memory':memory});last=time.monotonic();save()
  if stop:raise RuntimeError(stop)
 try:
  channel=owned_process.OwnedChildChannel(source);env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}
  with (out/'native.log').open('wb') as log:
   child=subprocess.Popen(command,env=channel.child_env(env),stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=channel.pass_fds)
   r['worker_started']=True;r['worker_pid']=child.pid;channel.after_spawn();save();r['owned_child_handshake']=channel.accept(child,timeout_seconds=10,poll_callback=observe);r['owned_child_identity_verified']=True;save()
   while child.poll() is None:
    try:mem=channel.sample(child)
    except owned_process.OwnedChildExited:
     if child.poll() is not None:break
     raise
    observe(mem);time.sleep(.2)
   r['worker_exit_code']=child.wait()
 except BaseException as exc:
  r['failure']={'type':type(exc).__name__,'message':str(exc)}
  if child is not None:
   try:os.killpg(child.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
   r['worker_exit_code']=child.returncode
 finally:
  if channel is not None:channel.close();r['owned_channel_descriptors_closed']=not channel.descriptors
 r['resource_stop']=stop;r['elapsed_seconds']=time.monotonic()-start;r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();r['observations'].append(resource(out));result=out/'worker/report.json'
 if result.exists():r['result_sha256']=sha(result);r['worker_report_completed']=json.loads(result.read_text()).get('execution_completed')
 r['completed']=r.get('worker_report_completed') is True and r.get('worker_exit_code')==0 and not r.get('failure') and stop is None and r.get('owned_child_identity_verified') and r.get('owned_channel_descriptors_closed')
 save();print(json.dumps({k:r.get(k) for k in ['completed','worker_exit_code','failure','elapsed_seconds','resource_stop']}));return 0 if r['completed'] else 2
if __name__=='__main__':raise SystemExit(main())
