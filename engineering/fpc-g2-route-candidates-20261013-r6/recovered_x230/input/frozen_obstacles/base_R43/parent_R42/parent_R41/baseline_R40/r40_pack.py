"""Freeze R40 deliverables atomically with SHA256 manifest, CRC and parent ZIP."""
from pathlib import Path
import hashlib,zipfile,json,os
from r40_motion import ROOT
FULL=Path('/mnt/data/RAZR_SLIDE_R40_verified_engineering_package_20261012.zip')
DELTA=Path('/mnt/data/RAZR_SLIDE_R40_delta_20261012.zip')
R39='baseline/RAZR_SLIDE_R39_FPC_motion_hardgate_20261012.zip'
expected='6eb43c691f7ec900f63006f837667c55cbf9137ac0a49067a93e61f12e14a4fd'
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def files():
 pnames=[
  'README_先读_R40.md','R40_REPRODUCE.sh','R40_hardgate_audit_20261012.md',
  'R40_supplier_gates_20261012.md','R40_independent_replay_20261012.md','R40_results_20261012.json',
  'r40_motion.py','r40_occ.py','r40_pocket.py','r40_faults.py',
  'r40_prepare.py','r40_inherited.py','r40_retest_r39.py',
  'r40_attest.py','r40_pack.py','r40_verify_offline.py','test_r40.py',R39]
 pnames+=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'cad').glob('R40_GHOST*'))
 pnames+=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'verification').glob('R40_*') if p.name not in {'R40_pack_receipt.json'})
 out=sorted(set(pnames))
 assert all((ROOT/p).is_file() for p in out)
 return out

def pack(dest,include_baseline):
 paths=[p for p in files() if include_baseline or p!=R39]
 parents={'R39_full_frozen_SHA256':expected,'parent_embedded':include_baseline,'manufacturing_go':False}
 entries=[]
 for rel in paths:
  p=ROOT/rel;entries.append({'path':rel,'size':p.stat().st_size,'sha256':sha(p)})
 manifest=json.dumps({'revision':'R40 rolling-U FPC research negative gate','entry_count':len(entries),
       'entries':entries,'provenance':parents},ensure_ascii=False,indent=2).encode('utf-8')+b'\n'
 name='audit/R40_SHA256_MANIFEST.json'
 temp=dest.with_suffix(dest.suffix+'.partial')
 if temp.exists():temp.unlink()
 with zipfile.ZipFile(temp,'w',allowZip64=True) as z:
  for e in entries:
   rel=e['path'];typ=zipfile.ZIP_STORED if Path(rel).suffix.lower() in ('.zip','.step','.brep') else zipfile.ZIP_DEFLATED
   z.write(ROOT/rel,arcname=rel,compress_type=typ,compresslevel=6 if typ==zipfile.ZIP_DEFLATED else None)
  z.writestr(name,manifest,compress_type=zipfile.ZIP_DEFLATED)
 # Independent direct member CRC and per-byte member checks on closed file.
 with zipfile.ZipFile(temp) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(paths)+1
  assert z.read(name)==manifest
  for e in entries:
   info=z.getinfo(e['path']);assert info.file_size==e['size']
   assert sha_bytes(z.read(e['path']))==e['sha256']
 os.replace(temp,dest)
 digest=sha(dest)
 with zipfile.ZipFile(dest) as z:assert z.testzip() is None and len(z.namelist())==len(entries)+1
 dest.with_suffix(dest.suffix+'.sha256').write_text(digest+'  '+dest.name+'\n')
 return {'file':str(dest),'sha256':digest,'size_bytes':dest.stat().st_size,'members':len(entries)+1,
         'matched_member_hashes':len(entries),'parent_frozen_embedded':include_baseline}

if __name__=='__main__':
 assert sha(ROOT/R39)==expected
 print(json.dumps({'full':pack(FULL,True),'delta':pack(DELTA,False)},ensure_ascii=False,indent=2))
