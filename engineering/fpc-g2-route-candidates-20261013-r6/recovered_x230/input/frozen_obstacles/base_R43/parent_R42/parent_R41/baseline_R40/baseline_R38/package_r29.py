"""R29 self-contained, hash-attested research package; never fabrication released."""
from __future__ import annotations
import json,hashlib,zipfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'RAZR_SLIDE_R29_engineering_package_20261011.zip'
MAN=ROOT/'audit'/'R29_SHA256_MANIFEST.json'
SHA=ROOT.parent/'RAZR_SLIDE_R29_engineering_package_20261011.sha256'

def permitted(p):
    rel=p.relative_to(ROOT)
    if any(x=='__pycache__' for x in rel.parts) or p.suffix in ('.pyc','.pyo'):
        return False
    if rel.as_posix()=='audit/R29_SHA256_MANIFEST.json':return False
    return True

sources=sorted((p for p in ROOT.rglob('*') if p.is_file() and permitted(p)),key=lambda p:p.relative_to(ROOT).as_posix())
if len(sources)<374:raise RuntimeError('Truncated source folder')
entries=[{'path':p.relative_to(ROOT).as_posix(),'size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources]
manifest={'revision':'R29 research CAD engineering archive; MANUFACTURING NO-GO',
 'files_excluding_manifest':len(entries),'R28_prior_unchanged_entries':374,
 'all_new_results_are_CAD_research_only':True,'manufacturing_go':False,
 'entries':entries}
MAN.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for p in [OUT,SHA]:
 if p.exists():raise FileExistsError(f'Never overwrite earlier R29 release without explicit decision: {p}')
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
 for p in sources+[MAN]:
  z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(OUT,'r') as z:
 problems=z.testzip()
 if problems:raise RuntimeError(f'ZIP member CRC failed {problems}')
 names=set(z.namelist())
 if len(names)!=len(entries)+1:raise AssertionError('Extra/missing zip member')
 for obj in entries:
  blob=z.read(obj['path'])
  if len(blob)!=obj['size_bytes'] or hashlib.sha256(blob).hexdigest()!=obj['sha256']:
   raise AssertionError(f'In ZIP content mismatch {obj["path"]}')
 if json.loads(z.read('audit/R29_SHA256_MANIFEST.json'))['manufacturing_go'] is not False:
  raise AssertionError('manufacturing hold erased')
digest=hashlib.sha256(OUT.read_bytes()).hexdigest()
SHA.write_text(f'{digest}  {OUT.name}\n')
# Verify as an independent file-size+digest check after closing ZIP handle.
assert hashlib.sha256(OUT.read_bytes()).hexdigest()==digest
print('R29 ARCHIVE:',OUT,'members=',len(entries)+1,'bytes=',OUT.stat().st_size,'sha256=',digest)
