"""Audit-gated R34 ZIP, original 706 R33 files unchanged, manifest members SHA."""
from __future__ import annotations
import hashlib,json,shutil,zipfile,os
from pathlib import Path
from r25_capture import ROOT
from r34_attest import run as attest
from r34_freeze import run as freeze
DEST=Path('/mnt/data/RAZR_SLIDE_R34_verified_engineering_package_20261011.zip')
STAGED=Path('/mnt/data/.R34_verified_stage.zip.part')
SHAFILE=DEST.with_suffix('.sha256')
MANIFEST=ROOT/'audit/R34_FINAL_MEMBER_SHA256.json'
EXCLUDED={'__pycache__','.DS_Store'}
EXCLUDE_PATHS={'verification/R34_packaging_run.log','verification/R34_packaging_exit.code','verification/R34_atomic_packaging_run.log','verification/R34_atomic_packaging_exit.code'}

def included():
    return sorted((p for p in ROOT.rglob('*') if p.is_file() and
                   not any(k in EXCLUDED for k in p.relative_to(ROOT).parts) and
                   not p.name.endswith('.pyc') and p.relative_to(ROOT).as_posix() not in EXCLUDE_PATHS),
                  key=lambda f:f.relative_to(ROOT).as_posix())

def sha(b):return hashlib.sha256(b).hexdigest()

def run():
    freeze(False);attest(False)
    assert (ROOT/'verification/R34_full_geometry_wrapper_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R34_geometry_exit.code').read_text().strip()=='0'
    immutable=json.loads((ROOT/'audit/R34_R33_immutable.json').read_text())
    assert immutable['ancestor_files_verified']==706 and immutable['all_ancestor_bytes_unchanged']
    files=[p for p in included() if p!=MANIFEST]
    obj=dict(revision='R34 complete research archive, failure counterexamples retained',
             R33_original_zip_SHA256=immutable['ancestor_zip_sha256'],
             inherited_original_files=706,
             archive_members_excluding_manifest=len(files),
             items=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in files],
             manufacturing_go=False)
    MANIFEST.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    files=included()
    with zipfile.ZipFile(STAGED,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for i,p in enumerate(files):
            z.write(p,p.relative_to(ROOT).as_posix())
            if i%100==0:print('R34 ZIP write',i,'/',len(files),flush=True)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)==len(obj['items'])+1
        for i,meta in enumerate(obj['items']):
            data=z.read(meta['path'])
            assert len(data)==meta['bytes'] and sha(data)==meta['sha256'],meta['path']
            if i%100==0:print('R34 ZIP verify',i,'/',len(obj['items']),flush=True)
        assert sha(z.read('audit/R34_FINAL_MEMBER_SHA256.json'))==sha(MANIFEST.read_bytes())
    digest=sha(STAGED.read_bytes())
    os.replace(STAGED,DEST)
    assert DEST.stat().st_size>60_000_000 and sha(DEST.read_bytes())==digest
    with zipfile.ZipFile(DEST) as verified_final:
        assert verified_final.testzip() is None and len(verified_final.namelist())==len(files)
    SHAFILE.write_text(f'{digest}  {DEST.name}\n')
    for src,dst in [
      ('R34_hardgate_audit_20261011.md','R34_hardgate_audit_20261011.md'),
      ('README_先读_R34.md','R34_README_20261011.md'),
      ('vendor/R34_供应商真实器件_机械电源_USB_OLED门槛.md','R34_supplier_gates_20261011.md'),
      ('verification/R34_results.json','R34_results_20261011.json'),
      ('verification/R34_integration.json','R34_integration_20261011.json'),
      ('verification/R34_dynamic.json','R34_dynamic_20261011.json'),
      ('verification/R34_tolerance.json','R34_tolerance_20261011.json'),
      ('verification/R34_faults.json','R34_faults_20261011.json'),
      ('verification/R34_STEP_manifest.json','R34_STEP_manifest_20261011.json'),
    ]:
        shutil.copyfile(ROOT/src,Path('/mnt/data')/dst)
    print('R34 PACKAGED',len(files),'members',DEST.stat().st_size,'bytes',digest,flush=True)
    return len(files),digest
if __name__=='__main__':run()
