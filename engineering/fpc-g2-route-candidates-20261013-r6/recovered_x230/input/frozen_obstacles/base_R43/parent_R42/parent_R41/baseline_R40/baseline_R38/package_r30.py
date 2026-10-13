"""Deterministic R30 complete ancestor+incremental archive with member digest checks."""
from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'RAZR_SLIDE_R30_engineering_package_20261011.zip'

frozen=json.loads((ROOT/'audit'/'R30_R29_ORIGINAL_ZIP_MEMBERS.json').read_text())
paths=set(ROOT/p['path'] for p in frozen['entries'])
paths.update(ROOT.glob('r30_*.py'))
paths.update(ROOT.glob('r30_*.sh'))
paths.update(ROOT.glob('package_r30.py'))
paths.update(ROOT.glob('test_r30.py'))
paths.update(ROOT.glob('README_先读_R30.md'))
paths.update((ROOT/'cad').glob('R30_*'))
paths.update((ROOT/'verification').glob('R30_*'))
paths.update((ROOT/'verification').glob('r30_*_final.log'))
paths.update((ROOT/'vendor').glob('R30_*'))
paths.update((ROOT/'audit').glob('R30_R29_ORIGINAL_ZIP_MEMBERS.json'))
paths.update((ROOT/'audit').glob('R30_*'))
paths={p for p in paths if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
records=[]
for p in sorted(paths,key=lambda q:str(q.relative_to(ROOT))):
 content=p.read_bytes();records.append({'path':p.relative_to(ROOT).as_posix(),
  'sha256':hashlib.sha256(content).hexdigest(),'size_bytes':len(content)})
manifest={'revision':'R30 sealed files manifest','frozen_R29_member_count':len(frozen['entries']),
 'file_count_excluding_manifest':len(records),'entries':records}
m=ROOT/'audit'/'R30_SHA256_MANIFEST.json'
m.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
paths.add(m)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(paths,key=lambda q:str(q.relative_to(ROOT))):
  rel=p.relative_to(ROOT).as_posix()
  info=zipfile.ZipInfo(rel,date_time=(2026,10,11,3,0,0))
  info.compress_type=zipfile.ZIP_DEFLATED
  info.external_attr=0o644<<16
  z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
with zipfile.ZipFile(OUT) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(paths)
 for r in records:
  assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256'],r['path']
 expected={r['path']:r for r in records}
 for r in frozen['entries']:
  assert expected[r['path']]['sha256']==r['sha256'],r['path']
sha=hashlib.sha256(OUT.read_bytes()).hexdigest()
(ROOT.parent/'RAZR_SLIDE_R30_engineering_package_20261011.sha256').write_text(f'{sha}  {OUT.name}\n')
print('R30 PACKAGE',len(paths),'members',OUT.stat().st_size,'bytes','SHA256',sha,flush=True)
