"""Deterministic package verification for R21 research candidate."""
from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parent
ZIP=ROOT.parent/'RAZR_SLIDE_R21_complete_engineering_package.zip'
KEEP={'cad','drawings','verification','viewer','baselines'}
INCLUDE={'r21_geom.py','r21_verify.py','r21_export.py','r21_report.py','test_r21.py',
         'package_r21.py','run_checks.sh','README_先读_R21.md','R21_接点仓与屏幕装配工程审查.pdf'}
items=[]
for f in sorted(ROOT.rglob('*')):
 if not f.is_file():continue
 rel=f.relative_to(ROOT)
 if any(x in rel.parts for x in ('__pycache__','pdf_render','preview')):continue
 if rel.name=='pdf_contact.png':continue
 if rel.parts[0] not in KEEP and rel.name not in INCLUDE:continue
 items.append((f,'RAZR_SLIDE_R21/'+str(rel)))
with zipfile.ZipFile(ZIP,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for src,tar in items:z.write(src,tar)
with zipfile.ZipFile(ZIP) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(items)
 assert len(set(z.namelist()))==len(items)
 for src,tar in items:assert hashlib.sha256(z.read(tar)).hexdigest()==hashlib.sha256(src.read_bytes()).hexdigest()
print('ZIP',ZIP,'bytes',ZIP.stat().st_size,'items',len(items),'sha256',hashlib.sha256(ZIP.read_bytes()).hexdigest())
