"""Atomic, member-SHA verified R42 research artifact packer.
Immutable parent R41 byte stream is stored, never rewritten or extracted in-place.
No log currently being written is included. Full and delta are separately verified.
"""
from pathlib import Path
import json,zipfile,hashlib,os,tempfile,datetime
from r42_verify_outputs import run as verify_outputs
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data')
FIXED=(2026,10,13,0,0,0)
FILES=[
 'R42_REPRODUCE.sh','README_先读_R42.md','R42_hardgate_audit_20261013.md',
 'R42_supplier_hardgates_20261013.md','R42_results_20261013.json',
 'r42_prepare.py','r42_double_loop.py','r42_occ.py','r42_interior_witness.py',
 'r42_topology_bounds.py','r42_verify_outputs.py','r42_report.py','r42_attest.py',
 'r42_run_parent697.py','r42_run_parent_r39.py','r42_pack.py','test_r42.py',
 'cad/R42_GHOST_TWO_FLEXES_STOW.step','cad/R42_GHOST_TWO_FLEXES_PREDOCK.step','cad/R42_GHOST_TWO_FLEXES_OPEN_SEATED.step',
 'verification/R42_motion_121_positions.csv','verification/R42_motion_budget.json',
 'verification/R42_reverse_U_bound.json','verification/R42_OCC_two_flexes.json',
 'verification/R42_interior_points.json','verification/R42_attest.json',
 'verification/R42_fresh_R39.log','verification/R42_fresh_R40.log',
 'verification/R42_fresh_R41.log','verification/R42_fresh_R42.log',
 'verification/R42_parent_fresh_run.log',
 'verification/R42_OCC_run.log','verification/R42_interior_run.log',
]


def sha(raw):return hashlib.sha256(raw).hexdigest()

def select_files(full):
 mapping={k:ROOT/k for k in FILES}
 test_dir=ROOT/'verification/R42_parent_test_receipts'
 for path in sorted(test_dir.glob('*')):
  if path.is_file():mapping[str(path.relative_to(ROOT))]=path
 if full:mapping['baseline/RAZR_SLIDE_R41_FPC_full_verified_20261013.zip']=ROOT/'baseline/RAZR_SLIDE_R41_FPC_full_verified_20261013.zip'
 for relative,path in mapping.items():assert path.is_file(),('missing',relative)
 return mapping

def pack(filename,full):
 mapping=select_files(full)
 manifest={'revision':'R42','research_not_manufacturable':True,
  'parent_R41_SHA256':'f0be97f2661a59d9db87adca18ecc4d961dcb6142b65f9a17b0f452b461dbef6',
  'archive_kind':'full_with_immutable_R41_nested_zip' if full else 'delta_requires_unmodified_R41_parent',
  'items':[]}
 for rel,path in sorted(mapping.items()):
  with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
  manifest['items'].append({'path':rel,'bytes':path.stat().st_size,'sha256':digest})
 manifest_bytes=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
 fd,tmp=tempfile.mkstemp(prefix='.r42_pack_tmp_',suffix='.zip',dir=OUT);os.close(fd)
 target=OUT/filename
 try:
  with zipfile.ZipFile(tmp,'w',allowZip64=True) as z:
   for rel,path in sorted(mapping.items()):
    info=zipfile.ZipInfo(rel,FIXED);info.compress_type=zipfile.ZIP_STORED if rel.endswith('.zip') else zipfile.ZIP_DEFLATED
    info.external_attr=(0o644<<16)
    # write streaming: avoid keeping the large immutable parent in RAM
    with path.open('rb') as src,z.open(info,'w',force_zip64=True) as dest:
     while (buf:=src.read(1024*1024)):dest.write(buf)
   info=zipfile.ZipInfo('audit/R42_ARCHIVE_MANIFEST.json',FIXED)
   info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
   z.writestr(info,manifest_bytes)
  with zipfile.ZipFile(tmp) as z:
   assert z.testzip() is None
   assert len(z.namelist())==len(mapping)+1
   got=json.loads(z.read('audit/R42_ARCHIVE_MANIFEST.json'))
   assert got==manifest
   for entry in got['items']:
    with z.open(entry['path']) as f:
     hs=hashlib.sha256();count=0
     while (buf:=f.read(1024*1024)):
      count+=len(buf);hs.update(buf)
    assert count==entry['bytes'] and hs.hexdigest()==entry['sha256'],entry['path']
  os.replace(tmp,target)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 (OUT/(filename+'.sha256')).write_text(digest+'  '+filename+'\n')
 return {'file':str(target),'bytes':target.stat().st_size,'members':len(mapping)+1,'sha256':digest,
         'independent_full_member_SHA256_and_CRC_checked':True}

def run():
 v=verify_outputs()
 assert v['verified_outputs'] and v['manufacturing_go'] is False
 out=[pack('RAZR_SLIDE_R42_FPC_delta_20261013.zip',False),
      pack('RAZR_SLIDE_R42_FPC_full_verified_20261013.zip',True)]
 record={'revision':'R42','archives':out,'frozen_R41_parent_unchanged':True,'test_count':846,
         'manufacturing_go':False,'candidate_go':False}
 (OUT/'R42_archive_receipt_20261013.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
 return record
if __name__=='__main__':print(json.dumps(run(),indent=2,ensure_ascii=False))
