#!/usr/bin/env python3
"""R44 immutable atomic packaging with member-level SHA/CRC verification.
Never packages its own growing log or parent expansion directories.
"""
from pathlib import Path
import hashlib,zipfile,json,os,sys,time
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent
PARENT='baseline/RAZR_SLIDE_R43_FPC_full_verified_20261013.zip'
PARENT_SHA='d79c33b2a0e8eae2d05c5dc318b442bdffb1420e5361e87e0317a4d9191de7a0'

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def archive(kind):
 assert kind in ('full','delta')
 parent=ROOT/PARENT;assert sha(parent)==PARENT_SHA
 files=sorted(p for p in ROOT.rglob('*') if p.is_file() and not p.name.endswith(('.tmp','.partial')) and not any(k in p.parts for k in ['__pycache__','base_R43','parent_R42']))
 files=[p for p in files if p.name!='r44_pack.py' or kind in ('full','delta')]
 if kind=='delta':files=[p for p in files if p.relative_to(ROOT).as_posix()!=PARENT]
 src={p.relative_to(ROOT).as_posix():p for p in files}
 member={n:{'size_bytes':p.stat().st_size,'sha256':sha(p)} for n,p in src.items()}
 manifest={'revision':'R44','archive_type':kind,'parent_R43_sha256':PARENT_SHA,
           'archive_contains_parent':kind=='full','member_count_excluding_manifest':len(src),
           'files':member,'candidate_go':False,'manufacturing_go':False}
 name=f'RAZR_SLIDE_R44_FPC_{kind}_verified_20261013.zip'
 dest=OUT/name;tmp=dest.with_suffix('.zip.partial')
 marker=f'audit/R44_MEMBER_SHA256_{kind.upper()}.json';markerdata=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
 try:
  with zipfile.ZipFile(tmp,'w') as z:
   for n,p in src.items():
    comp=zipfile.ZIP_STORED if n==PARENT else zipfile.ZIP_DEFLATED
    z.write(p,arcname=n,compress_type=comp,compresslevel=6 if comp==zipfile.ZIP_DEFLATED else None)
   z.writestr(marker,markerdata,compress_type=zipfile.ZIP_DEFLATED)
  with zipfile.ZipFile(tmp) as z:
   assert z.testzip() is None
   assert len(z.namelist())==len(src)+1
   assert not set(z.namelist()).symmetric_difference(set(src)|{marker})
   t=json.loads(z.read(marker));assert t['member_count_excluding_manifest']==len(src)
   for n,s in member.items():
    contents=z.read(n)
    assert len(contents)==s['size_bytes']
    assert hashlib.sha256(contents).hexdigest()==s['sha256'],n
  with tmp.open('rb') as f:os.fsync(f.fileno())
  os.replace(tmp,dest)
  digest=sha(dest)
  (OUT/(name+'.sha256')).write_text(digest+'  '+name+'\n')
  # verify post-publish disk digest + zip again
  assert sha(dest)==digest
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None
  return {'filename':name,'sha256':digest,'file_size_bytes':dest.stat().st_size,
          'zip_file_count_including_manifest':len(src)+1,
          'members_verified':len(src),'integrity_ok':True}
 finally:
  if tmp.exists():tmp.unlink()

if __name__=='__main__':
 results=[archive(k) for k in ('delta','full')]
 report={'R44_release':results,'source_parent_sha256':PARENT_SHA,'manifests_exclude_themselves':True,
         'candidate_go':False,'manufacturing_go':False}
 (OUT/'R44_archive_integrity_20261013.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
