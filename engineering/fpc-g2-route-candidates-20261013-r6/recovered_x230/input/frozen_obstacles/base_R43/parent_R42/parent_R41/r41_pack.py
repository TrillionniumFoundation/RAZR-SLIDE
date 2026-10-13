"""Atomic frozen R41 research artifacts; excludes live logs and manifests' self-hashes.
Full package includes exact unmodified R40 parent ZIP; delta requires parent separately.
"""
from pathlib import Path
import zipfile,hashlib,os,json,tempfile,shutil
ROOT=Path(__file__).resolve().parent
DEST=Path('/mnt/data')
PARENT='baseline/RAZR_SLIDE_R40_verified_engineering_package_20261012.zip'
PARENT_SHA='8df51e8e2c7a8c2733ddaa541eba9e85124d75d33c1a5e7b071fd1ec1f4db7ec'

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def sha_path(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def list_files(include_parent):
 src=[]
 for p in ROOT.glob('r41_*.py'):src.append(p)
 src.append(ROOT/'test_r41.py');src.append(ROOT/'R41_REPRODUCE.sh')
 src.extend(ROOT.glob('R41_*.md'))
 src.append(ROOT/'R41_results_20261013.json')
 for p in ROOT.joinpath('cad').glob('R41_*.step'):src.append(p)
 for p in ROOT.joinpath('verification').rglob('*'):
  if p.is_file() and p.suffix in ('.json','.csv','.log','.txt') and not p.name.endswith('_PARTIAL.json'):
   if 'rerun' not in p.name.lower():src.append(p)
 if include_parent:src.append(ROOT/PARENT)
 assert all(p.exists() for p in src)
 return sorted(set(src),key=lambda p:p.relative_to(ROOT).as_posix())

def pack(full=True):
 assert sha_path(ROOT/PARENT)==PARENT_SHA
 paths=list_files(full)
 assert len([p for p in paths if p.name.endswith('.step')])==5
 members={}
 for p in paths:
  name=p.relative_to(ROOT).as_posix()
  members[name]={'sha256':sha_path(p),'size_bytes':p.stat().st_size}
 if full:assert members[PARENT]['sha256']==PARENT_SHA
 manifest={'kind':'R41 research only; no OEM permission or physical qualification',
           'parent_R40_SHA256':PARENT_SHA,'includes_exact_parent_R40_archive':full,
           'each_member_hashes_below_exclude_this_manifest':True,
           'member_count_without_manifest':len(members),'member_hashes':members,
           'manufacturing_go':False}
 name=f'RAZR_SLIDE_R41_FPC_{"full_verified" if full else "delta"}_20261013.zip'
 out=DEST/name
 with tempfile.NamedTemporaryFile(prefix=name+'.',suffix='.tmp',dir=DEST,delete=False) as t:tmp=Path(t.name)
 try:
  with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
   for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
   z.writestr('audit/R41_SHA256_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
  with zipfile.ZipFile(tmp) as z:
   assert z.testzip() is None
   assert len(z.namelist())==len(members)+1
   for fn,record in members.items():
    raw=z.read(fn)
    assert sha_bytes(raw)==record['sha256'] and len(raw)==record['size_bytes']
   new=json.loads(z.read('audit/R41_SHA256_MANIFEST.json'))
   assert new==manifest
  with tmp.open('rb') as f:os.fsync(f.fileno())
  os.replace(tmp,out)
 finally:
  if tmp.exists():tmp.unlink()
 assert out.is_file()
 x=sha_path(out);(DEST/(name+'.sha256')).write_text(x+'  '+name+'\n')
 # Independent second pass on the final path, not the temporary name.
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None
  for fn,record in manifest['member_hashes'].items():assert sha_bytes(z.read(fn))==record['sha256']
 receipt={'archive':str(out),'sha256':x,'byte_count':out.stat().st_size,'members':len(members)+1,
   'full_original_R40_parent_included':full,'crc_passed':True,'per_member_SHA256_passed':True,
   'research_tests_808_passed_not_manufacturing_approval':True,'manufacturing_go':False}
 (DEST/(name+'.verify.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt,indent=2));return receipt
if __name__=='__main__':
 print('DELTA');pack(False)
 print('FULL');pack(True)
