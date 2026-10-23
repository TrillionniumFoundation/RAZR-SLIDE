"""Wait within this active task for the approved guarded panel continuation."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
from supervise_response_mapped import memory,write,digest

BASE=Path(__file__).resolve().parent
PRIVATE=Path('/tmp/razr-fe-20261023')
report=PRIVATE/'supervision/panel-memory-window.json'
assert not report.exists()
start=time.monotonic();stable=0;last=-100.
state={'schema':'razr-panel-resource-window-v1','completed':False,
       'maximum_wait_seconds':600,'incremental_memory_reserve_GiB':2.4,
       'whole_cgroup_limit_GiB':6.8,'worker_started':False,
       'source_sha256':digest(Path(__file__)),
       'worker_source_sha256':digest(BASE/'rebuild_base_response_mapped.py'),
       'supervisor_source_sha256':digest(BASE/'supervise_response_mapped.py')}
while time.monotonic()-start<600:
    current=memory();available=current['estimated_unreclaimable_bytes']+int(2.4*1024**3)<=int(6.8*1024**3)
    stable=stable+1 if available else 0
    if time.monotonic()-last>=30 or stable>=3:
        state.update(seconds=time.monotonic()-start,memory=current,consecutive_safe_samples=stable)
        write(report,state);print(json.dumps({'seconds':state['seconds'],'unreclaimable_bytes':current['estimated_unreclaimable_bytes'],'safe_samples':stable}),flush=True)
        last=time.monotonic()
    if stable>=3:
        assert digest(BASE/'rebuild_base_response_mapped.py')==state['worker_source_sha256']
        assert digest(BASE/'supervise_response_mapped.py')==state['supervisor_source_sha256']
        command=[sys.executable,'-B',str(BASE/'supervise_response_mapped.py'),'--body','panel',
                 '--attempt-label','panel-mapped-resume2','--resume-manifest',
                 str(PRIVATE/'base-response-425/panel/partial-linear-response-manifest.json'),
                 '--resume-sha256','e64d3102eff7239a11d1e512c8711c78e4637e2af851fd7efee0aefe2a7a6520']
        state.update(worker_started=True,command=command);write(report,state)
        code=subprocess.call(command,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
        state.update(completed=True,worker_supervisor_exit_code=code,seconds=time.monotonic()-start)
        write(report,state);raise SystemExit(code)
    time.sleep(5)
state.update(completed=True,status='resource_window_not_available_within_wait_budget',seconds=time.monotonic()-start)
write(report,state);print(json.dumps(state),flush=True)
raise SystemExit(3)
