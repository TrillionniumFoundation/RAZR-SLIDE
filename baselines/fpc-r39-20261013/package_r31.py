"""R31 deterministic source+CAD+log package, immutable 504 R30 source files.
Re-verifies the whole archive and self-contained SHA256 manifest. NO-GO.
"""
from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data/RAZR_SLIDE_R31_engineering_package_20261011.zip')
freeze=json.loads((ROOT/'audit'/'R31_R30_ORIGINAL_ZIP_MEMBERS.json').read_text())
assert len(freeze['entries'])==504
paths=set(ROOT/x['path'] for x in freeze['entries'])
paths.update(ROOT.glob('r31_*.py'))
paths.update(ROOT.glob('r31_*.sh'))
paths.update(ROOT.glob('test_r31.py'))
paths.update(ROOT.glob('package_r31.py'))
paths.update(ROOT.glob('README_先读_R31.md'))
paths.update((ROOT/'cad').glob('R31_*'))
paths.update((ROOT/'verification').glob('R31_*'))
paths.update((ROOT/'verification').glob('r31_*_final.log'))
paths.update((ROOT/'audit').glob('R31_*'))
paths.update((ROOT/'vendor').glob('R31_*'))
paths={p for p in paths if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
record=[]
for p in sorted(paths,key=lambda p:p.relative_to(ROOT).as_posix()):
    data=p.read_bytes()
    record.append(dict(path=p.relative_to(ROOT).as_posix(),size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest={'revision':'R31 source bundle with 504 fixed R30 ancestors',
          'R30_immutable_files':len(freeze['entries']),
          'file_count_excluding_manifest':len(record),'entries':record}
m=ROOT/'audit'/'R31_SHA256_MANIFEST.json'
m.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
paths.add(m)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(paths,key=lambda q:q.relative_to(ROOT).as_posix()):
        info=zipfile.ZipInfo(p.relative_to(ROOT).as_posix(),date_time=(2026,10,11,8,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
        z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(paths)
    manifest_from_zip=json.loads(z.read('audit/R31_SHA256_MANIFEST.json'))
    assert manifest_from_zip==manifest
    for r in record:
        assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256'],r['path']
    recorded={r['path']:r for r in record}
    for f in freeze['entries']:
        assert recorded[f['path']]['sha256']==f['sha256'],f['path']
sha=hashlib.sha256(OUT.read_bytes()).hexdigest()
(Path('/mnt/data')/'RAZR_SLIDE_R31_engineering_package_20261011.sha256').write_text(f'{sha}  {OUT.name}\n')
print('R31 PACKAGE',len(paths),'members',OUT.stat().st_size,'bytes, SHA256',sha,flush=True)
