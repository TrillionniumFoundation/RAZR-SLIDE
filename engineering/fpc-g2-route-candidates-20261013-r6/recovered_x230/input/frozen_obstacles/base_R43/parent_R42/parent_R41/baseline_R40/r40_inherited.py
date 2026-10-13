"""Independent real R21-R38 fresh tests; no historical logs counted as fresh.
Test cell separated from R39 frozen archive; 2 workers prevent OCC memory storms.
"""
from pathlib import Path
import sys,os,zipfile,hashlib,subprocess,re,json,time,shutil,concurrent.futures
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'baseline_R38'))
from r37_regression import CASES as PREVIOUS
CASES=PREVIOUS+[('R37',48,'.','test_r37.py'),('R38',36,'.','test_r38.py')]
SRC37=Path(os.environ.get('R37_SOURCE_ZIP','/mnt/data/RAZR_SLIDE_R37_verified_engineering_package_20261011.zip'))
CELL=Path('/mnt/data/R40_fresh_R37_regression_cell')
OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
EXPECTED='b0013a530c980d10a53a48fb25db0919636ac81184b8f20c1e98a0704838b487'
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
 shutil.rmtree(CELL,ignore_errors=True); CELL.mkdir()
 if SRC37.exists():
  assert sha(SRC37)==EXPECTED
  with zipfile.ZipFile(SRC37) as z:
   assert z.testzip() is None and len(z.namelist())==1043
   z.extractall(CELL)
  provenance='independent_original_R37_zip_verified'
 else:
  # Re-run real tests from R38 embedded archived R37 members, but this does
  # not independently authenticate the separate original R37 zip's provenance.
  frozen=json.loads((ROOT/'baseline_R38/audit/R38_R37_frozen_manifest.json').read_text())
  assert len(frozen['entries'])==1043 and frozen['R37_original_zip_sha256']==EXPECTED
  for entry in frozen['entries']:
   src=ROOT/'baseline_R38'/entry['path']
   assert sha(src)==entry['sha256']
   dest=CELL/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
  provenance='only_R38_embedded_manifest_R37_provenance_not_independently_proved'
 # Test R38 must run in independent R38 base folder with its own generated BRep; copy only R38
 # code into separate destination and execute test_r38 there.
 def case_run(c):
  name,num,path,script=c
  cwd=CELL/path if name!='R38' else ROOT/'baseline_R38'
  start=time.monotonic()
  try:
   x=subprocess.run([sys.executable,'-m','unittest','-q',script],cwd=cwd,
     env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},
     capture_output=True,text=True,timeout=380)
   err=None
  except subprocess.TimeoutExpired as ex:
   x=None;err=f'timed out >380s: {str(ex)[:100]}'
  content=((x.stdout or '')+(x.stderr or '')) if x else (err or '')
  log=OUT/f'R40_fresh_{name}.log';log.write_text(content)
  match=re.search(r'Ran\s+(\d+)\s+tests?',content)
  actual=int(match.group(1)) if match else None
  ok=x is not None and x.returncode==0 and actual==num and content.rstrip().endswith('OK')
  return {'name':name,'expected_tests':num,'actual_tests':actual,'success':ok,'exit_code':x.returncode if x else None,
          'log':log.name,'log_sha256':sha(log),'seconds':round(time.monotonic()-start,2),'error':err}
 results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futs={pool.submit(case_run,c):c[0] for c in CASES}
  for fut in concurrent.futures.as_completed(futs):
   res=fut.result();results.append(res)
   (OUT/'R40_inherited_progress.json').write_text(json.dumps({'done':len(results),'total':len(CASES),'rows':results},indent=2)+'\n')
   print('FRESH',res['name'],res['actual_tests'],res['success'],'s',res['seconds'],flush=True)
 total=sum(q['actual_tests'] or 0 for q in results)
 status=all(q['success'] for q in results) and total==697
 report={'success':status,'R37_expected_checksum':EXPECTED,'provenance':provenance,'independent_zip_extract':str(CELL),
         'actual_fresh_parent_reexecuted':total,'expected_count':697,'groups':len(CASES),
         'rows':results,'manufacturing_go':False}
 (OUT/'R40_inherited_results.json').write_text(json.dumps(report,indent=2)+'\n')
 print('R40 FRESH PARENT',total,status,flush=True)
 if not status:raise SystemExit(1)
if __name__=='__main__':run()
