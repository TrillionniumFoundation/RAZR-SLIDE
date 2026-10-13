"""Verify R40 package file member checksums and safety qualifications are NO-GO."""
import sys,zipfile,json,hashlib
from pathlib import Path

def sha_file(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify(p):
 p=Path(p)
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  manifest=json.loads(z.read('audit/R40_SHA256_MANIFEST.json'))
  assert len(z.namelist())==manifest['entry_count']+1
  assert manifest['provenance']['manufacturing_go'] is False
  for e in manifest['entries']:
   data=z.read(e['path']);assert len(data)==e['size']
   assert hashlib.sha256(data).hexdigest()==e['sha256']
  if manifest['provenance']['parent_embedded']:
   original=z.read('baseline/RAZR_SLIDE_R39_FPC_motion_hardgate_20261012.zip')
   assert hashlib.sha256(original).hexdigest()==manifest['provenance']['R39_full_frozen_SHA256']
 digest=sha_file(p)
 side=p.with_suffix(p.suffix+'.sha256')
 if side.exists():assert side.read_text().split()[0]==digest
 print(f'R40 ZIP integrity OK: {len(z.namelist())} files SHA256 {digest}; manufacturing NO-GO')
if __name__=='__main__':verify(sys.argv[1] if len(sys.argv)>1 else '/mnt/data/RAZR_SLIDE_R40_verified_engineering_package_20261012.zip')
