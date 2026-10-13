"""Reproducible, independently-verified R26 research engineering archive.

Never calls the resulting package manufacturing-qualified. ZIP plus external hash
are distinct from internal per-file audit manifest.
"""
from pathlib import Path
import json,zipfile,hashlib,shutil,os
ROOT=Path(__file__).resolve().parent
DST=ROOT.parent
ARCH=DST/'RAZR_SLIDE_R26_engineering_package_20261011.zip'
REPORT=DST/'R26_hardgate_audit_20261011.md'
RESULT=DST/'R26_results_20261011.json'
SHA=DST/'RAZR_SLIDE_R26_engineering_package_20261011.sha256'
V=ROOT/'verification'
receipt=json.loads((V/'R26_results.json').read_text())
assert receipt['total_regression_tests']==191
assert receipt['manufacturing_go'] is False
assert json.loads((V/'R26_STEP_manifest.json').read_text())['exported_scenes']==10
assert (V/'R26_inherited_done.flag').read_text().strip()=='FINISHED'
assert (V/'R26_geometry_export_done.flag').read_text().strip()=='FINISHED'

SKIP={'R26_SHA256_MANIFEST.json','R26_pack_run.log'}
files=[]
for f in sorted(ROOT.rglob('*')):
 if not f.is_file():continue
 if '__pycache__' in f.parts or f.suffix in ('.pyc','.pyo') or f.name in SKIP:continue
 # Refuse links, no outside-tree content may be archived.
 if f.is_symlink():raise RuntimeError(f'Symlink not allowed: {f}')
 files.append(f)
assert len(files)>190,len(files)
items=[]
for p in files:
 rel=p.relative_to(ROOT).as_posix()
 items.append(dict(relative_path=rel,size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
manifest=dict(revision='R26 native geometry and fault source package',
    files_hashed=len(items),files=items,contains_unmanufacturable_fail_counterexamples=True,
    intentional_STEP_fault_ghost_count=sum(x['deliberate_fault_GHOST'] for x in json.loads((V/'R26_STEP_manifest.json').read_text())['scenes']),
    user_target_4700mAh_not_proven=True,manufacturing_go=False)
internal=ROOT/'audit/R26_SHA256_MANIFEST.json'
internal.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
files.append(internal)
with zipfile.ZipFile(ARCH,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
 for f in files:
  rel='RAZR_SLIDE_R26/'+f.relative_to(ROOT).as_posix()
  z.write(f,arcname=rel)
with zipfile.ZipFile(ARCH,'r') as z:
 assert z.testzip() is None
 names=set(z.namelist())
 assert len(names)==len(files)
 for item in items:
  payload=z.read('RAZR_SLIDE_R26/'+item['relative_path'])
  assert hashlib.sha256(payload).hexdigest()==item['sha256'],item['relative_path']
 assert 'RAZR_SLIDE_R26/audit/R26_SHA256_MANIFEST.json' in names
 print('ZIP_READBACK',len(names),'files, verified individually',flush=True)
SHA.write_text(f'{hashlib.sha256(ARCH.read_bytes()).hexdigest()}  {ARCH.name}\n')
shutil.copy2(ROOT/'audit/R26_硬门槛对抗审计.md',REPORT)
shutil.copy2(V/'R26_results.json',RESULT)
assert hashlib.sha256(ARCH.read_bytes()).hexdigest()==SHA.read_text().split()[0]
print(json.dumps(dict(archive=str(ARCH),files=len(files),zip_bytes=ARCH.stat().st_size,
    report=str(REPORT),result=str(RESULT),sha256=str(SHA),manufacturing_go=False),indent=2))
