#!/usr/bin/env python3
"""Run the frozen STEP-only independent checker on the actual X230 runtime."""
import hashlib,json,platform,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
PAYLOAD_ROOT=HERE.parents[2]
PYTHON='/home/qian/RAZR-SLIDE-work-20261013/cad-venv/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snapshot(m):
 result={}
 for r in m['files']:
  p=PAYLOAD_ROOT/r['path']
  if p.stat().st_size!=r['size'] or sha(p)!=r['sha256']:raise ValueError('Transferred input size/SHA differs: '+r['path'])
  result[r['path']]=sha(p)
 return result
def main():
 m=json.loads((HERE/'transfer-input-manifest.json').read_text())
 before=snapshot(m);started=time.monotonic()
 with (HERE/'independent.stdout.log').open('wb') as out,(HERE/'independent.stderr.log').open('wb') as err:
  r=subprocess.run([PYTHON,str(PROJECT/'independent/verify-r3-step.py')],cwd=PAYLOAD_ROOT,stdout=out,stderr=err,check=False)
 after=snapshot(m)
 result={'configured_host':'x230','actual_host':platform.node(),'python_runtime':PYTHON,'native_exit_code':r.returncode,
  'elapsed_monotonic_seconds':time.monotonic()-started,'input_file_count':len(before),'transfer_manifest_sha256':sha(HERE/'transfer-input-manifest.json'),
  'before_source_and_STEP_sha256':before,'after_source_and_STEP_sha256':after,'all_transferred_source_and_STEP_bytes_unchanged':before==after,
  'actual_whole_payload_and_motion_report_sha256':sha(PROJECT/'independent/final-independent-export-check.json') if r.returncode==0 else None,
  'stdout_sha256':sha(HERE/'independent.stdout.log'),'stderr_sha256':sha(HERE/'independent.stderr.log'),'manufacturing_go':False}
 (HERE/'remote-native-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2),flush=True)
 if before!=after or r.returncode!=0:raise SystemExit(1)
if __name__=='__main__':main()
