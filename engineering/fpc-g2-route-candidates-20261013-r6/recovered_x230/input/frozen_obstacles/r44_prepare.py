#!/usr/bin/env python3
"""Extract immutable R43 FULL ZIP and verify nested R42 provenance for independent R44 replay."""
from pathlib import Path
import zipfile,hashlib,subprocess,sys,json
ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT/'baseline/RAZR_SLIDE_R43_FPC_full_verified_20261013.zip'
EXPECTED='d79c33b2a0e8eae2d05c5dc318b442bdffb1420e5361e87e0317a4d9191de7a0'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
 assert ARCHIVE.exists(),'original R43 full archive missing; supply under baseline/'
 assert sha(ARCHIVE)==EXPECTED,'R43 immutable source SHA mismatch'
 target=ROOT/'base_R43';target.mkdir(exist_ok=True)
 with zipfile.ZipFile(ARCHIVE) as z:
  assert z.testzip() is None and len(z.infolist())==33
  for m in z.infolist():
   p=(target/m.filename).resolve()
   assert p.is_relative_to(target.resolve()),'zip traversal blocked'
   if m.is_dir():p.mkdir(parents=True,exist_ok=True);continue
   if p.exists():
    assert hashlib.sha256(z.read(m)).hexdigest()==sha(p),f'Extracted frozen R43 modified: {m.filename}'
   else:
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(m))
 r=subprocess.run([sys.executable,'r43_prepare.py'],cwd=target,capture_output=True,text=True,timeout=240)
 assert r.returncode==0,r.stderr[-2500:]
 assert (target/'parent_R42/r42_double_loop.py').is_file()
 return {'R43_full_parent_sha256':EXPECTED,'R43_parent_members':33,'nested_R42_restored':True}
if __name__=='__main__':print(json.dumps(run(),indent=2))
