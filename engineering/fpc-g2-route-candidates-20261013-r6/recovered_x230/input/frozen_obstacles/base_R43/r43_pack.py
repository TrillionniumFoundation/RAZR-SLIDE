#!/usr/bin/env python3
"""Produce verified R43 delta and full bundle atomically; exclude parent self-generated data."""
from pathlib import Path
import hashlib,zipfile,shutil,json,os,tempfile,time
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data')
STAGE=OUT/'R43_delivery_stage'
DELTA=OUT/'RAZR_SLIDE_R43_FPC_delta_20261013.zip'
FULL=OUT/'RAZR_SLIDE_R43_FPC_full_verified_20261013.zip'
FILES=['R43_REPRODUCE.sh','r43_prepare.py','r43_corridor_screen.py','r43_occ_counterexample.py',
 'r43_radius_space_budget.py','r43_vendor_gate.py','r43_attest.py','r43_pack.py','test_r43.py',
 'R43_results_20261013.json','R43_hardgate_audit_20261013.md','R43_supplier_RFQ.md',
 'README_先读_R43.md','R43_vendor_input_template.json']
VERS=['verification/R43_shifted_2U_screen.json','verification/R43_OCC_2layout_counterexamples.json',
 'verification/R43_sidewall_180deg_transverse_bound.json','verification/R43_vendor_gate.json',
 'verification/R43_new_tests.log','verification/R43_screen_run.log','verification/R43_occ_run.log',
 'verification/R43_attest_run.log','verification/R43_attest.json','verification/R43_shift_heatmap.png',
 'verification/R43_scan_PROGRESS.json',
 'evidence/R43_full_parent_replay_20261013.log','evidence/R42_attest_846_tests_20261013.json']
GHOST=sorted((ROOT/'cad').glob('R43_GHOST_*.step'))
assert len(GHOST)==4

def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def make_stage():
 if STAGE.exists():shutil.rmtree(STAGE)
 STAGE.mkdir(parents=True)
 for name in FILES+VERS+[f'cad/{p.name}' for p in GHOST]:
  source=ROOT/name;dest=STAGE/name
  assert source.is_file(),name
  dest.parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(source,dest)
 manifest={p.relative_to(STAGE).as_posix():{'size':p.stat().st_size,'sha256':sha(p)} for p in STAGE.rglob('*') if p.is_file()}
 (STAGE/'audit').mkdir()
 (STAGE/'audit/R43_MEMBER_SHA256.json').write_text(json.dumps({'revision':'R43','files':manifest,'exclude_self':True},ensure_ascii=False,indent=2)+'\n')
 return len(manifest)

def build_zip(outfile,include_baseline):
 with tempfile.NamedTemporaryFile(dir=OUT,prefix=f'.r43_{"full" if include_baseline else "delta"}_',suffix='.tmp',delete=False) as f:tmp=Path(f.name)
 items=sorted(p for p in STAGE.rglob('*') if p.is_file())
 with zipfile.ZipFile(tmp,'w',allowZip64=True) as z:
  for p in items:
   # STEP & logs compress well, small manifest also; don't recompress baseline zip.
   z.write(p,p.relative_to(STAGE).as_posix(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=7)
  if include_baseline:
   par=ROOT/'baseline/RAZR_SLIDE_R42_FPC_full_verified_20261013.zip'
   assert sha(par)=='4daf4f6cf63ffe3c4222c71726f66da4b99ae121410322954b41362fcee1f513'
   z.write(par,'baseline/'+par.name,compress_type=zipfile.ZIP_STORED)
 # Independently reopen the final contents before publishing.
 with zipfile.ZipFile(tmp) as z:
  assert z.testzip() is None
  m=json.loads(z.read('audit/R43_MEMBER_SHA256.json'))['files']
  for name,entry in m.items():
   content=z.read(name);assert len(content)==entry['size'] and hashlib.sha256(content).hexdigest()==entry['sha256'],name
  assert len(z.namelist())==len(m)+1+(1 if include_baseline else 0)
  if include_baseline:
   assert hashlib.sha256(z.read('baseline/RAZR_SLIDE_R42_FPC_full_verified_20261013.zip')).hexdigest()=='4daf4f6cf63ffe3c4222c71726f66da4b99ae121410322954b41362fcee1f513'
 digest=sha(tmp)
 os.replace(tmp,outfile)
 assert sha(outfile)==digest
 (OUT/(outfile.name+'.sha256')).write_text(f'{digest}  {outfile.name}\n')
 print(outfile.name,'members',len(m)+1+(1 if include_baseline else 0),'bytes',outfile.stat().st_size,'sha256',digest,flush=True)
 return {'file':outfile.name,'members':len(m)+1+(1 if include_baseline else 0),'size_bytes':outfile.stat().st_size,'sha256':digest}

if __name__=='__main__':
 n=make_stage();print('stage source members',n)
 results=[build_zip(DELTA,False),build_zip(FULL,True)]
 (OUT/'R43_package_receipt_20261013.json').write_text(json.dumps({'packaged_at':'2026-10-13','parent_archive_sha256':'4daf4f6cf63ffe3c4222c71726f66da4b99ae121410322954b41362fcee1f513','files':results,'manufacturing_go':False},indent=2)+'\n')
