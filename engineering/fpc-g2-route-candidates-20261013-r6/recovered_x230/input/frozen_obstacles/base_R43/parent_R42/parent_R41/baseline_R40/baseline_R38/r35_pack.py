"""Atomic, member-verified R35 artifact packaging; do not archive mutable packaging logs."""
from pathlib import Path
import os,hashlib,json,zipfile
from r25_capture import ROOT

OUTDIR=ROOT.parent
TARGET=OUTDIR/'RAZR_SLIDE_R35_verified_engineering_package_20261011.zip'
PART=OUTDIR/'.RAZR_SLIDE_R35_verified_engineering_package_20261011.zip.part'
SHA=OUTDIR/'RAZR_SLIDE_R35_verified_engineering_package_20261011.sha256'
SUMMARY=OUTDIR/'R35_packaging_receipt_20261011.json'
MANIFEST_PATH=ROOT/'audit/R35_member_manifest.json'
R34=OUTDIR/'RAZR_SLIDE_R34_verified_engineering_package_20261011.zip'

def allowed_new(rel):
    path=Path(rel);p=path.as_posix();name=path.name
    if p in {'README_先读_R35.md','R35_hardgate_audit_20261011.md','R35_supplier_gates_20261011.md','test_r35.py'}:return True
    if len(path.parts)==1 and name.startswith('r35_') and name.endswith(('.py','.sh')):return True
    if len(path.parts)==2 and path.parts[0]=='cad' and name.startswith('R35_') and name.endswith(('.brep','.step')):return True
    if len(path.parts)==2 and path.parts[0]=='verification' and name.startswith('R35_') and not name.startswith(('R35_packaging','R35_atomic')):return True
    if len(path.parts)==2 and path.parts[0]=='audit' and name.startswith('R35_'):return True
    return False

def run():
    assert (ROOT/'verification/R35_geometry_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R35_inherited_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R35_new_exit.code').read_text().strip()=='0'
    from r35_freeze import run as freeze
    imm=freeze(False)
    from r35_attest import run as attest
    att=attest(False)
    assert att['total_research_tests_reexecuted']==559 and att['manufacturing_go'] is False
    with zipfile.ZipFile(R34) as z:
        old={i.filename for i in z.infolist() if not i.is_dir()}
    assert len(old)==783
    newer=set()
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(ROOT).as_posix()
        if rel in old or allowed_new(rel):newer.add(rel)
    assert old<=newer
    newer.discard('audit/R35_member_manifest.json')
    rows=[]
    for rel in sorted(newer):
        f=ROOT/rel
        b=f.read_bytes()
        rows.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),ancestor_R34=rel in old))
    manifest=dict(version='R35 verified engineering archive manifest',
       ancestor_zip_sha256=imm['R34_original_zip_sha256'],ancestor_members=len(old),
       numbered_members_excluding_this_manifest=len(rows),
       all_research_tests=att['total_research_tests_reexecuted'],
       manufacturing_go=False,files=rows)
    MANIFEST_PATH.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    if PART.exists():PART.unlink()
    with zipfile.ZipFile(PART,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for rel in sorted(newer):z.write(ROOT/rel,arcname=rel)
        z.write(MANIFEST_PATH,arcname='audit/R35_member_manifest.json')
    with zipfile.ZipFile(PART) as z:
        assert z.testzip() is None
        files={i.filename for i in z.infolist() if not i.is_dir()}
        assert len(files)==len(rows)+1 and files==newer|{'audit/R35_member_manifest.json'}
        for row in rows:
            raw=z.read(row['path'])
            assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
        embedded=json.loads(z.read('audit/R35_member_manifest.json'))
        assert embedded==manifest
        for old_member in old:
            assert (ROOT/old_member).read_bytes()==z.read(old_member),old_member
    os.replace(PART,TARGET)
    sha=hashlib.sha256(TARGET.read_bytes()).hexdigest()
    SHA.write_text(f'{sha}  {TARGET.name}\n')
    # Post-publish separate open/read/hash, not based only on the file before os.replace.
    with zipfile.ZipFile(TARGET) as z:
        assert z.testzip() is None and len(z.infolist())==len(rows)+1
    assert hashlib.sha256(TARGET.read_bytes()).hexdigest()==SHA.read_text().split()[0]
    result=dict(artifact=TARGET.name,sha256=sha,bytes=TARGET.stat().st_size,
       archive_members=len(rows)+1,manifest_members=len(rows),ancestor_R34_members_unchanged=len(old),
       test_reexecuted=att['total_research_tests_reexecuted'],
       R35_surrogate_STEP_count=att['step_scenes'],GHOST_STEP_count=att['intentional_ghost_scenes'],
       zip_crc_pass=True,per_member_hash_pass=True,post_publish_sha256_pass=True,
       manufacturing_go=False)
    SUMMARY.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print('R35 VERIFIED',json.dumps(result,ensure_ascii=False),flush=True)
    return result
if __name__=='__main__':run()
