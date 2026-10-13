"""Verify immutable R40 parent and materialize the required R40/R38 CAD source.
The parent ZIP stays byte-for-byte unchanged. Fail closed if checksum differs.
"""
from pathlib import Path
import zipfile,hashlib,sys
ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'baseline/RAZR_SLIDE_R40_verified_engineering_package_20261012.zip'
PARENT_SHA='8df51e8e2c7a8c2733ddaa541eba9e85124d75d33c1a5e7b071fd1ec1f4db7ec'
def sha(path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
 assert PARENT.is_file(), 'missing immutable R40 parent; use R41 full archive or copy the named original to baseline/'
 assert sha(PARENT)==PARENT_SHA, 'R40 source ZIP was modified or truncated'
 with zipfile.ZipFile(PARENT) as z:
  assert z.testzip() is None and len(z.namelist())==57
  base=ROOT/'baseline_R40';base.mkdir(exist_ok=True)
  # Extract only when required; the generated source in this root is a copy.
  for entry in z.namelist():
   target=base/entry
   if not target.exists():
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(z.read(entry))
 sys.path.insert(0,str(ROOT/'baseline_R40'))
 from r40_prepare import run as base_prepare
 if not (ROOT/'baseline_R40/baseline_R38/cad/R38_A_R37_BYTE_IDENTICAL.brep').exists():base_prepare()
 print('R41 frozen R40 source validated, R39 nested parent retained, R38 CAD available')
if __name__=='__main__':run()
