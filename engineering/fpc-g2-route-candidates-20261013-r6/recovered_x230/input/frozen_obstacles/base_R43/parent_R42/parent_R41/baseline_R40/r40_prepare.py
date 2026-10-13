"""Restore immutable R38 CAD and source from SHA-verified R39 parent ZIP."""
from pathlib import Path
import json,hashlib,zipfile,io
ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'baseline/RAZR_SLIDE_R39_FPC_motion_hardgate_20261012.zip'
R39_SHA='6eb43c691f7ec900f63006f837667c55cbf9137ac0a49067a93e61f12e14a4fd'
R38_SHA='649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6'
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
 assert sha(PARENT)==R39_SHA
 with zipfile.ZipFile(PARENT) as z:
  assert z.testzip() is None and len(z.namelist())==37
  b=z.read('baseline/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip')
  assert hashlib.sha256(b).hexdigest()==R38_SHA
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  assert z.testzip() is None and len(z.namelist())==1094
  ROOT.joinpath('baseline_R38').mkdir(exist_ok=True)
  z.extractall(ROOT/'baseline_R38')
 print('R40 frozen baseline verified: R39 37 ZIP members, original R38 1094 members')
if __name__=='__main__':run()
