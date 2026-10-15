"""Standalone ZIP/CRC/member-SHA256 verification, never relies on ChatGPT logs."""
import json,zipfile,hashlib,sys
from pathlib import Path
P=Path(sys.argv[1]);expected=Path(str(P)+'.sha256')
with P.open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
if expected.is_file():assert d==expected.read_text().split()[0]
with zipfile.ZipFile(P) as z:
 assert z.testzip() is None
 manifest=json.loads(z.read('audit/R41_SHA256_MANIFEST.json'))
 assert len(z.namelist())==manifest['member_count_without_manifest']+1
 for k,v in manifest['member_hashes'].items():
  data=z.read(k)
  assert hashlib.sha256(data).hexdigest()==v['sha256'] and len(data)==v['size_bytes']
 if manifest['includes_exact_parent_R40_archive']:
  data=z.read('baseline/RAZR_SLIDE_R40_verified_engineering_package_20261012.zip')
  assert hashlib.sha256(data).hexdigest()==manifest['parent_R40_SHA256']
 assert not manifest['manufacturing_go']
print(json.dumps({'archive':str(P),'sha256':d,'zip_and_member_sha256':'PASS',
                  'contains_R40_parent':manifest['includes_exact_parent_R40_archive'],
                  'manufacturing_go':False},indent=2))
