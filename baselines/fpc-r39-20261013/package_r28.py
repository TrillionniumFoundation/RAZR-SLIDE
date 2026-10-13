"""Package research R28 with exact per-member SHA checks. NO-GO independent."""
from __future__ import annotations
import json,hashlib,zipfile,shutil,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'RAZR_SLIDE_R28_engineering_package_20261011.zip'
CHECK=ROOT.parent/'RAZR_SLIDE_R28_engineering_package_20261011.sha256'
MAN=ROOT/'audit'/'R28_SHA256_MANIFEST.json'

def include(p):
 if not p.is_file():return False
 r=p.relative_to(ROOT)
 if p==MAN:return False
 if '__pycache__' in r.parts or '.pytest_cache' in r.parts:return False
 if p.suffix.lower() in ('.pyc','.pyo','.swp','.tmp'):return False
 if p.name.startswith('.'):return False
 return True

files=sorted((p for p in ROOT.rglob('*') if include(p)),key=lambda p:p.relative_to(ROOT).as_posix())
archive=[dict(path=p.relative_to(ROOT).as_posix(),size_bytes=p.stat().st_size,
              sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
manifest=dict(revision='R28 provenance, never manufacturing release',files_excluding_self=len(archive),
 archived_exact_R27_original_file_count=329,
 sources_archived_without_edits='audit/R27_SHA256_MANIFEST.json verifies the exact R27 ancestor',
 entries=archive,excluded=['__pycache__','*.pyc','*.pyo','itself'],manufacturing_go=False)
MAN.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
packfiles=files+[MAN]
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
 for p in packfiles:
  z.write(p,arcname=(Path('RAZR_SLIDE_R28')/p.relative_to(ROOT)).as_posix())
with zipfile.ZipFile(OUT) as z:
 assert z.testzip() is None
 names=z.namelist()
 assert len(names)==len(packfiles), (len(names),len(packfiles))
 for row in archive:
  name=f"RAZR_SLIDE_R28/{row['path']}"
  data=z.read(name)
  assert len(data)==row['size_bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],name
 assert hashlib.sha256(z.read('RAZR_SLIDE_R28/audit/R28_SHA256_MANIFEST.json')).digest()==hashlib.sha256(MAN.read_bytes()).digest()
sha=hashlib.sha256(OUT.read_bytes()).hexdigest()
CHECK.write_text(f'{sha}  {OUT.name}\n')
# User-facing extracts are ordinary files, copied from the exact archived source.
for src,dst in [
 ('audit/R28_硬门槛对抗审计.md','R28_hardgate_audit_20261011.md'),
 ('verification/R28_results.json','R28_results_20261011.json'),
 ('verification/R28_faults.json','R28_faults_20261011.json'),
 ('verification/R28_clearance.json','R28_clearance_20261011.json'),
 ('verification/R28_STEP_manifest.json','R28_STEP_manifest_20261011.json'),
]:
 shutil.copyfile(ROOT/src,ROOT.parent/dst)
print('PACKAGE',OUT,'size',OUT.stat().st_size,'members',len(packfiles),'sha',sha)
