"""Bounded direct-child supervisor retaining actual worker RSS and all failures."""
import argparse, hashlib, json, os, pathlib, signal, subprocess, sys, time

def ident(path):
    path=pathlib.Path(path)
    with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=digest)

def main():
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=pathlib.Path,required=True);p.add_argument('--seconds',type=float,default=180);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    cmd=a.command[1:] if a.command[0]=='--' else a.command
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    cgroup=pathlib.Path('/sys/fs/cgroup');before={n:(cgroup/n).read_text() for n in ['memory.current','memory.max','memory.stat','memory.events']}
    record=dict(schema='r12.actual_numeric_worker_receipt.v1',command=cmd,worker_source=ident(cmd[1]),supervisor_source=ident(__file__),before=before,
        launcher_rss_cap_bytes=1536*1024**2,external_RSS_sampling_scope='nested_launcher_only_not_numerical_worker',worker_RSS_cap_enforced=False,wall_cap_seconds=a.seconds,threads=1,started_unix=time.time())
    started=time.monotonic();rss_peak=0;reason=None;samples=[]
    out=a.receipt.with_suffix('.stdout');err=a.receipt.with_suffix('.stderr')
    with out.open('x') as fo,err.open('x') as fe:
        child=subprocess.Popen(cmd,env=env,stdout=fo,stderr=fe,start_new_session=True)
        while child.poll() is None:
            elapsed=time.monotonic()-started
            try:
                status=dict((s.split(':',1)[0],s.split(':',1)[1].strip()) for s in pathlib.Path('/proc',str(child.pid),'status').read_text().splitlines() if ':' in s)
                rss=int(status.get('VmRSS','0 kB').split()[0])*1024;rss_peak=max(rss_peak,rss)
                samples.append(dict(seconds=elapsed,rss_bytes=rss))
                if rss>record['launcher_rss_cap_bytes']:reason='launcher_RSS_cap'
            except FileNotFoundError:pass
            if elapsed>a.seconds:reason='wall_cap'
            if reason:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                break
            time.sleep(.25)
        code=child.wait()
    record.update(exit_code=code,external_seconds=time.monotonic()-started,sampled_launcher_peak_RSS_bytes=rss_peak,stop_reason=reason,samples=samples,
        stdout=ident(out),stderr=ident(err),worker_source_after=ident(cmd[1]),after={n:(cgroup/n).read_text() for n in ['memory.current','memory.events']})
    with a.receipt.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps({k:record[k] for k in ['exit_code','external_seconds','sampled_launcher_peak_RSS_bytes','stop_reason']}))
    print(out.read_text())
    if code:print(err.read_text())
    return code

if __name__=='__main__':raise SystemExit(main())
