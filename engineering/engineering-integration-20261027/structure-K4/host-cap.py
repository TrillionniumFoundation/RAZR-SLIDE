"""Outer hosted cap only; never change a S4/original worker or its gates."""
import hashlib, json, os, pathlib, signal, subprocess, sys, time
target = pathlib.Path(sys.argv[1])
command = sys.argv[2:]
target.parent.mkdir(parents=True, exist_ok=True)
deadline = float(os.environ['HOST_JOB_START']) + 3240
def resource():
    stat = os.statvfs(target.parent)
    files = {}
    for name in ('memory.current', 'memory.max', 'memory.stat'):
        p = pathlib.Path('/sys/fs/cgroup')/name
        files[name] = p.read_text()
    return {'epoch': time.time(), 'writeable_disk_bytes': stat.f_bavail*stat.f_frsize,
            'root_reserved_free_bytes_diagnostic_only': stat.f_bfree*stat.f_frsize,
            'cgroup': files}
receipt = {'argv': command, 'cwd': os.getcwd(), 'started_epoch': time.time(),
    'external_deadline_epoch': deadline, 'platform_maximum_job_seconds': 3600,
    'finite_native_trial_budget_seconds_unchanged': 1200,
    'F1_complete_STEP_readback_budget_seconds': 1200,
  'original_90_second_positive_only_KEY_reader_used': False,
    'canonical_unit_suite_timeouts_unchanged': True,
    'outer_hosted_cap_reached': False, 'process_started': False,
    'resource_before': None, 'source_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
child = None
code = 2
def external_term(signum, frame):
    raise KeyboardInterrupt('external SIGTERM mapped to original cleanup')
signal.signal(signal.SIGTERM, external_term)
try:
    receipt['resource_before'] = resource()
    if time.time() >= deadline-30:
        raise RuntimeError('insufficient hosted time remains; no command started')
    with target.with_suffix('.log').open('xb') as log, target.with_suffix('.resources.jsonl').open('x') as samples:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        receipt.update(process_started=True, owned_child_pid=child.pid)
        while child.poll() is None:
            samples.write(json.dumps(resource())+'\n'); samples.flush()
            if time.time() >= deadline:
                receipt['outer_hosted_cap_reached'] = True
                child.send_signal(signal.SIGINT)
                try: child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    receipt['SIGINT_cleanup_timed_out'] = True
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                break
            try: child.wait(timeout=min(5, max(.05, deadline-time.time())))
            except subprocess.TimeoutExpired: pass
        receipt['child_exit_code'] = child.returncode
        code = 124 if receipt['outer_hosted_cap_reached'] else child.returncode
except BaseException as exc:
    receipt['failure'] = type(exc).__name__+': '+str(exc)
    if child is not None and child.poll() is None:
        child.send_signal(signal.SIGINT)
        try: child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=5)
finally:
    try: receipt['resource_after'] = resource()
    except BaseException as exc:
        receipt['resource_after'] = None
        receipt['resource_after_error'] = type(exc).__name__+': '+str(exc)
        code = 2
    receipt.update(exit_code=code, finished_epoch=time.time())
    target.with_suffix('.json').write_text(json.dumps(receipt, indent=2)+'\n')
raise SystemExit(code)
