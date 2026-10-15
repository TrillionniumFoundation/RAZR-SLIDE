"""R32 deterministic full engineering bundle, known manufacturer NO-GO."""
from __future__ import annotations
import hashlib,json,zipfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DEST=Path('/mnt/data')
OUT=DEST/'RAZR_SLIDE_R32_engineering_package_20261011.zip'
freeze=json.loads((ROOT/'audit/R32_R31_FROZEN_SHA256.json').read_text())
assert freeze['verified_R31_original_files']==564
assert (ROOT/'verification/R32_geometry_exit.code').read_text().strip()=='0'
assert (ROOT/'verification/R32_inherited_exit.code').read_text().strip()=='0'
assert (ROOT/'verification/R32_new_40_exit.code').read_text().strip()=='0'
R32=json.loads((ROOT/'verification/R32_results.json').read_text())
assert R32['total_reexecuted_and_passed']==433 and R32['manufacturing_go'] is False
paths={ROOT/f['path'] for f in freeze['entries']}
for pattern in ('r32_*.py','r32_*.sh','test_r32.py','package_r32.py','README_先读_R32.md',
                'cad/R32_*','verification/R32_*','audit/R32_*','vendor/R32_*'):
    paths.update(ROOT.glob(pattern))
manifest_path=ROOT/'audit'/'R32_SHA256_MANIFEST.json'
paths={p for p in paths if p.is_file() and p!=manifest_path and p.suffix!='.pyc' and '__pycache__' not in p.parts}
rec=[]
for p in sorted(paths,key=lambda x:x.relative_to(ROOT).as_posix()):
    data=p.read_bytes()
    rec.append(dict(path=p.relative_to(ROOT).as_posix(),size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=dict(revision='R32 full research CAD/negative-safety-evidence bundle, manufacturing NO-GO',
              R31_ancestor_files=564,
              files_excluding_manifest=len(rec),entries=rec)
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
paths.add(manifest_path)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(paths,key=lambda x:x.relative_to(ROOT).as_posix()):
        n=p.relative_to(ROOT).as_posix()
        i=zipfile.ZipInfo(n,date_time=(2026,10,11,8,0,0))
        i.compress_type=zipfile.ZIP_DEFLATED
        i.external_attr=0o644<<16
        z.writestr(i,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(paths)
    stored=json.loads(z.read('audit/R32_SHA256_MANIFEST.json'))
    assert stored==manifest
    for f in rec:
        assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256'],f['path']
    frozen={f['path']:f for f in freeze['entries']}
    rec_map={f['path']:f for f in rec}
    assert all(rec_map[p]['sha256']==f['sha256'] for p,f in frozen.items())
hash_value=hashlib.sha256(OUT.read_bytes()).hexdigest()
(DEST/'RAZR_SLIDE_R32_engineering_package_20261011.sha256').write_text(f'{hash_value}  {OUT.name}\n')
for p,target in ((ROOT/'audit/R32_硬门槛对抗审计.md','R32_hardgate_audit_20261011.md'),
                 (ROOT/'verification/R32_results.json','R32_results_20261011.json'),
                 (ROOT/'verification/R32_tolerance.json','R32_tolerance_20261011.json'),
                 (ROOT/'verification/R32_faults.json','R32_faults_20261011.json'),
                 (ROOT/'verification/R32_envelope.json','R32_envelope_20261011.json'),
                 (ROOT/'vendor/R32_机械电源USB与OLED实物门槛.md','R32_supplier_gates_20261011.md')):
    shutil.copyfile(p,DEST/target)
print('R32 PACKAGE',len(paths),'files',OUT.stat().st_size,'bytes',hash_value,'ancestor564 verified, tests433, MANUFACTURING NO-GO',flush=True)
