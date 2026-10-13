#!/usr/bin/env python3
"""Restore immutable R42 full parent for the R43 delta package.
Never modifies the original parent ZIP. Rejects pre-existing modified parent files.
"""
import hashlib,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ORIGINAL=ROOT/'baseline/RAZR_SLIDE_R42_FPC_full_verified_20261013.zip'
EXPECTED='4daf4f6cf63ffe3c4222c71726f66da4b99ae121410322954b41362fcee1f513'

def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run():
 if not ORIGINAL.exists():raise FileNotFoundError('Please supply the unmodified R42 full ZIP under baseline/')
 assert sha(ORIGINAL)==EXPECTED, 'R42 parent zip checksum mismatch'
 restore=ROOT/'parent_R42'; restore.mkdir(exist_ok=True)
 with zipfile.ZipFile(ORIGINAL) as z:
  assert len(z.namelist())==56 and z.testzip() is None
  for info in z.infolist():
   dest=(restore/info.filename).resolve()
   assert dest.is_relative_to(restore.resolve())
   if info.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
   if dest.exists():
    assert sha(dest)==hashlib.sha256(z.read(info)).hexdigest(), f'Parent file changed: {info.filename}'
    continue
   dest.parent.mkdir(parents=True,exist_ok=True)
   dest.write_bytes(z.read(info))
 result=subprocess.run([sys.executable,'r42_prepare.py'],cwd=restore,capture_output=True,text=True,timeout=180)
 assert result.returncode==0,result.stderr[-2000:]+result.stdout[-500:]
 print('R43 immutable R42→R41→R40→R38 nested parents verified')
 return True
if __name__=='__main__':run()
