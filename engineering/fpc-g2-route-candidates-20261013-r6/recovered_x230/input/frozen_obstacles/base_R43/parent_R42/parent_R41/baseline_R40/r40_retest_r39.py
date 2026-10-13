"""Fresh R39 31 tests in isolated copy recovered from frozen R39 ZIP."""
import zipfile,shutil,subprocess,os,sys,re
from pathlib import Path
from r40_prepare import ROOT,PARENT,sha,R39_SHA
CELL=Path('/mnt/data/R40_fresh_R39_test_cell')
def run():
 assert sha(PARENT)==R39_SHA
 shutil.rmtree(CELL,ignore_errors=True);CELL.mkdir()
 with zipfile.ZipFile(PARENT) as z:z.extractall(CELL)
 q=subprocess.run([sys.executable,'r39_prepare_baseline.py'],cwd=CELL,
      capture_output=True,text=True,timeout=90,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
 if q.returncode:raise RuntimeError(q.stderr[-2000:])
 p=subprocess.run([sys.executable,'-m','unittest','-q','test_r39.py'],cwd=CELL,
      capture_output=True,text=True,timeout=120,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
 log=ROOT/'verification/R40_fresh_R39.log';log.write_text((p.stdout or '')+(p.stderr or ''))
 assert p.returncode==0 and re.search(r'Ran 31 tests?',log.read_text()) and log.read_text().rstrip().endswith('OK')
 print('R39 fresh independently: 31/31 passed')
if __name__=='__main__':run()
