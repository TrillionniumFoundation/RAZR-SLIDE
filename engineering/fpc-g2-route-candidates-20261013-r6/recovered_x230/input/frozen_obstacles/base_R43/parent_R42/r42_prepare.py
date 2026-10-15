"""Portable frozen-parent importer for R42 full ZIP, never edits parent ZIP."""
from pathlib import Path
import hashlib,zipfile,subprocess,sys
ROOT=Path(__file__).resolve().parent
ORIGINAL=ROOT/'baseline/RAZR_SLIDE_R41_FPC_full_verified_20261013.zip'
EXPECTED='f0be97f2661a59d9db87adca18ecc4d961dcb6142b65f9a17b0f452b461dbef6'

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run():
 assert ORIGINAL.exists() and sha(ORIGINAL)==EXPECTED,'R41 parent zip missing/changed'
 with zipfile.ZipFile(ORIGINAL) as z:
  assert len(z.namelist())==57 and z.testzip() is None
  for item in z.infolist():
   target=(ROOT/'parent_R41'/item.filename)
   assert target.resolve().is_relative_to((ROOT/'parent_R41').resolve()),'invalid archive path'
   if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
   if target.exists():
    if sha(target)!=hashlib.sha256(z.read(item)).hexdigest():raise AssertionError('modified restored parent: '+item.filename)
    continue
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
 q=subprocess.run([sys.executable,'r41_prepare.py'],cwd=ROOT/'parent_R41',capture_output=True,text=True,timeout=240)
 assert q.returncode==0,q.stdout[-1000:]+q.stderr[-1500:]
 return True
if __name__=='__main__':print('R42 immutable R41→R40→R38 recovered',run())
