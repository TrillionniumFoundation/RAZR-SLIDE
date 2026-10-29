"""Explicit non-scientific real-process exit-control fixture."""
import argparse,atexit,json,os,time
from pathlib import Path
p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--contract',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
c=json.loads(a.contract.read_text());a.output.mkdir(exist_ok=False)
def finish():
    time.sleep(c['exit_delay_seconds'])
    if c.get('mutate_math_after_receipt'):a.contract.write_text(json.dumps({**c,'actual_mutation_after_receipt':True})+'\n')
    if c.get('nonzero_after_receipt'):os._exit(7)
atexit.register(finish)
time.sleep(c['worker_delay_seconds'])
(a.output/'fixture.json').write_text(json.dumps({'fixture_only':True,'scientific_geometry_executed':False})+'\n')
