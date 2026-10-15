"""R33 deterministic archival list + ZIP full-member SHA check.
Includes all R32 frozen content as independent original copied members.
"""
from __future__ import annotations
import zipfile,hashlib,json,shutil
from pathlib import Path
from r33_attest import run as attest
from r33_freeze import run as freeze
ROOT=Path(__file__).resolve().parent
DEST=Path('/mnt/data/RAZR_SLIDE_R33_engineering_package_20261011.zip')
HASHFILE=DEST.with_suffix('.sha256')
MANIFEST=ROOT/'audit/R33_FINAL_MEMBER_SHA256.json'
EXCLUDE_NAMES={'__pycache__','.DS_Store'}

def included():
    return sorted((p for p in ROOT.rglob('*') if p.is_file() and
                   not any(k in EXCLUDE_NAMES for k in p.relative_to(ROOT).parts)
                   and not p.name.endswith('.pyc')),
                  key=lambda f:f.relative_to(ROOT).as_posix())

def sha(raw): return hashlib.sha256(raw).hexdigest()

def run():
    attest(False);freeze(False)
    files=[p for p in included() if p!=MANIFEST]
    manifest=dict(revision='R33 final archive manifest',
        original_R32_frozen_source_sha=sha(Path('/mnt/data/RAZR_SLIDE_R32_engineering_package_20261011.zip').read_bytes()),
        member_excluding_this_manifest=len(files),
        excluded_dynamic_cache='__pycache__ and *.pyc',
        items=[dict(path=p.relative_to(ROOT).as_posix(),size=p.stat().st_size,sha256=sha(p.read_bytes())) for p in files],
        manufacturing_go=False)
    MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    allfiles=included()
    with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for p in allfiles:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(DEST) as z:
        assert z.testzip() is None
        actual=z.namelist()
        assert len(actual)==len(allfiles)==len(files)+1
        for item in manifest['items']:
            raw=z.read(item['path'])
            assert len(raw)==item['size'] and sha(raw)==item['sha256'],item['path']
        assert sha(z.read('audit/R33_FINAL_MEMBER_SHA256.json'))==sha(MANIFEST.read_bytes())
    digest=sha(DEST.read_bytes())
    HASHFILE.write_text(f'{digest}  {DEST.name}\n')
    for src,target in [
        ('R33_hardgate_audit_20261011.md','R33_hardgate_audit_20261011.md'),
        ('README_先读_R33.md','R33_README_20261011.md'),
        ('vendor/R33_真实连接器_机械保持_电源USB_OLED准入.md','R33_supplier_gates_20261011.md'),
        ('verification/R33_results.json','R33_results_20261011.json'),
        ('verification/R33_retention.json','R33_retention_20261011.json'),
        ('verification/R33_catalogue.json','R33_catalogue_fit_20261011.json'),
        ('verification/R33_expansion_rejected.json','R33_expansion_rejected_20261011.json'),
    ]:
        shutil.copyfile(ROOT/src,Path('/mnt/data')/target)
    print('R33 ARCHIVED',len(allfiles),'files',DEST.stat().st_size,'bytes',digest,flush=True)
    print('R33 SHA',HASHFILE.read_text().strip(),flush=True)
    return len(allfiles),digest
if __name__=='__main__':run()
