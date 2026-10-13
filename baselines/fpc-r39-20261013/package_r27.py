"""Deterministic-path R27 source/evidence archive + independent member integrity.

ZIP timestamps preserved but SHA256 manifest is complete for every archived
member (self-manifest is excluded from its list to avoid self reference).
"""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DEST=ROOT.parent/'RAZR_SLIDE_R27_engineering_package_20261011.zip'
SHA=ROOT.parent/'RAZR_SLIDE_R27_engineering_package_20261011.sha256'
MANIFEST=ROOT/'audit/R27_SHA256_MANIFEST.json'
EXCLUDE={str(MANIFEST.relative_to(ROOT))}
def eligible(p):
 rel=p.relative_to(ROOT)
 return (p.is_file() and '__pycache__' not in rel.parts and p.suffix not in ('.pyc','.pyo')
    and rel.as_posix() not in EXCLUDE)
files=sorted((p for p in ROOT.rglob('*') if eligible(p)),key=lambda p:p.relative_to(ROOT).as_posix())
rows=[]
for p in files:
 rel=p.relative_to(ROOT).as_posix()
 rows.append(dict(path=rel,size_bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
manifest=dict(revision='RAZR SLIDE R27 SOURCE+EVIDENCE, never qualified manufacturing drawing',
  archived_items_excluding_manifest=len(rows),files=rows,
  excludes_only=['__pycache__','*.pyc','*.pyo','self-manifest'],
  manuscript_sha256_self_excluded=True,manufacturing_go=False)
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
allfiles=files+[MANIFEST]
with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
 for p in sorted(allfiles,key=lambda p:p.relative_to(ROOT).as_posix()):
  z.write(p,arcname=f'RAZR_SLIDE_R27/{p.relative_to(ROOT).as_posix()}')
with zipfile.ZipFile(DEST) as z:
 assert z.testzip() is None
 names=z.namelist();assert len(names)==len(allfiles)
 assert all(x.startswith('RAZR_SLIDE_R27/') and '..' not in Path(x).parts for x in names)
 for row in rows:
  assert hashlib.sha256(z.read('RAZR_SLIDE_R27/'+row['path'])).hexdigest()==row['sha256']
 assert z.read('RAZR_SLIDE_R27/audit/R27_SHA256_MANIFEST.json')==MANIFEST.read_bytes()
digest=hashlib.sha256(DEST.read_bytes()).hexdigest()
SHA.write_text(digest+'  '+DEST.name+'\n')
receipt=dict(revision='R27 research CAD archive checked',path=DEST.name,size_bytes=DEST.stat().st_size,
 sha256=digest,archived_files=len(allfiles),archived_uncompressed_bytes=sum(p.stat().st_size for p in allfiles),
 archive_members_SHA256_100_percent_verified=True,zip_testzip_ok=True,manufacturing_go=False)
(ROOT.parent/'R27_package_receipt_20261011.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
