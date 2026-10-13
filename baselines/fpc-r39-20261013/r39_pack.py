"""Immutable R38 + R39-only research delta, with complete member SHA and atomic packaging.
Do not use an evolving pack log as a manifest member. No frozen member changes.
"""
import hashlib,zipfile,json,os,shutil
from pathlib import Path
from r39_verify_release import verify
ROOT=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('R39_R38_ZIP','/mnt/data/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip'))
OUT=Path('/mnt/data/RAZR_SLIDE_R39_verified_engineering_package_20261013.zip')
EXPECTED='649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6'
MANIFEST='audit/R39_package_member_manifest.json'

def files_to_package():
    tops=['r39_path.py','r39_screen.py','r39_export.py','r39_ribbon_brep.py',
          'r39_regression.py','r39_attest.py','r39_occ_confirm.py','r39_verify_release.py',
          'r39_pack.py','test_r39.py','README_先读_R39.md','R39_hardgate_audit_20261013.md','R39_supplier_RfQ_20261013.md']
    extras=[f for f in (ROOT/'cad').glob('R39_*') if f.is_file()]
    extras+= [f for f in (ROOT/'verification').glob('R39_*') if f.is_file()]
    extras+= [f for f in (ROOT/'audit').glob('R39_*') if f.is_file() and f.name!='R39_package_member_manifest.json']
    new=[ROOT/n for n in tops]+extras
    assert all(p.exists() for p in new)
    return sorted(set(new),key=lambda p:p.relative_to(ROOT).as_posix())

def run():
    assert hashlib.file_digest(SOURCE.open('rb'),'sha256').hexdigest()==EXPECTED
    data=json.loads((ROOT/'verification/R39_results.json').read_text())
    assert data['total_fresh_test_assertions']==746 and data['R38_ancestor_bytes_unchanged']
    assert data['scenario_STEP_count']==6 and data['ribbon_BREP_count']==6 and data['manufacturing_go'] is False
    with zipfile.ZipFile(SOURCE) as original:
        assert original.testzip() is None
        ancestor_names=original.namelist();assert len(ancestor_names)==1094
        newfiles=files_to_package();newnames=[p.relative_to(ROOT).as_posix() for p in newfiles]
        assert not set(newnames).intersection(ancestor_names)
        entries=[]
        tmp=OUT.with_suffix('.zip.building')
        if tmp.exists():tmp.unlink()
        with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as dest:
            for n in ancestor_names:
                content=original.read(n)
                assert content==(ROOT/n).read_bytes(),f'R38 drift {n}'
                dest.writestr(n,content)
                entries.append(dict(name=n,sha256=hashlib.sha256(content).hexdigest(),origin='immutable_R38'))
            for path in newfiles:
                name=path.relative_to(ROOT).as_posix();content=path.read_bytes()
                dest.writestr(name,content)
                entries.append(dict(name=name,sha256=hashlib.sha256(content).hexdigest(),origin='new_R39'))
            manifest=dict(revision='R39 verified research-level NO-GO',
               source_R38_archive_sha256=EXPECTED,R38_ancestor_member_count=len(ancestor_names),
               new_R39_member_count=len(newfiles),non_manifest_member_count=len(entries),
               members=entries,physical_manufacturing_go=False)
            payload=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
            dest.writestr(MANIFEST,payload.encode())
        if OUT.exists():OUT.unlink()
        os.replace(tmp,OUT)
    source_for_verify=str(SOURCE)
    sha=verify(OUT,source_for_verify)
    sha_file=OUT.with_suffix('.sha256')
    sha_file.write_text(f'{sha}  {OUT.name}\n')
    receipt=dict(archive=str(OUT),sha256=sha,size_bytes=OUT.stat().st_size,
       source_original=source_for_verify,source_sha256=EXPECTED,
       ancestor_files_unchanged=len(ancestor_names),added_R39_files=len(newfiles),
       zip_total_members=len(entries)+1,all_member_sha256_verified=True,
       original_frozen_member_bytes_compared=True,physical_manufacturing_go=False)
    (ROOT/'verification/R39_package_receipt_postrelease.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (Path('/mnt/data')/'R39_package_receipt_20261013.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('R39 ATOMIC PACKAGE DONE',json.dumps(receipt,indent=2),flush=True)
    return receipt
if __name__=='__main__':run()
