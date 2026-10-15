"""Freeze R36 only after full exit-0 receipts, using atomic ZIP publication.
Does not self-include growing log, ZIP or SHA; manifest excludes itself.
"""
import hashlib,json,os,zipfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DEST=ROOT.parent/'RAZR_SLIDE_R36_verified_engineering_package_20261011.zip'
SHAFILE=ROOT.parent/(DEST.name+'.sha256')
MANIFEST=ROOT/'audit/R36_package_member_manifest.json'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(2<<20),b''): h.update(data)
    return h.hexdigest()

def run():
    assert (ROOT/'verification/R36_inherited_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R36_new_exit.code').read_text().strip()=='0'
    assert json.loads((ROOT/'verification/R36_results.json').read_text())['total_research_tests_reexecuted']==613
    immutable=json.loads((ROOT/'audit/R36_R35_immutable.json').read_text())
    assert immutable['original_file_count']==853
    for r in immutable['members']:
        p=ROOT/r['path'];assert p.is_file() and p.stat().st_size==r['size'] and sha(p)==r['sha256'],r['path']
    members=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or p==MANIFEST:continue
        relative=p.relative_to(ROOT).as_posix()
        assert not relative.startswith('../') and not relative.startswith('/')
        members.append(dict(path=relative,size_bytes=p.stat().st_size,sha256=sha(p)))
    manifest=dict(revision='R36 immutable research release; manufacturing NO-GO',
        R35_source_sha256=immutable['ancestor_archive_sha256'],
        R35_frozen_member_count=853,release_members_excluding_manifest=len(members),members=members)
    MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    all_files=members+[dict(path=MANIFEST.relative_to(ROOT).as_posix(),size_bytes=MANIFEST.stat().st_size,sha256=sha(MANIFEST))]
    fd,tempfile_path=tempfile.mkstemp(prefix='.R36_verified_build_',suffix='.zip',dir=DEST.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(tempfile_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
            for r in all_files:
                z.write(ROOT/r['path'],arcname=r['path'])
        with zipfile.ZipFile(tempfile_path,'r') as z:
            assert z.testzip() is None
            assert len(z.infolist())==len(all_files)
            assert len(set(z.namelist()))==len(all_files)
            for r in all_files:
                b=z.read(r['path']);assert len(b)==r['size_bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
        with open(tempfile_path,'rb') as f:os.fsync(f.fileno())
        os.replace(tempfile_path,DEST)
    finally:
        if os.path.exists(tempfile_path):os.unlink(tempfile_path)
    digest=sha(DEST)
    SHAFILE.write_text(f'{digest}  {DEST.name}\n')
    with zipfile.ZipFile(DEST) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(all_files)
        assert z.read('audit/R36_package_member_manifest.json')==MANIFEST.read_bytes()
    assert sha(DEST)==digest
    print(json.dumps(dict(path=str(DEST),member_count=len(all_files),size_bytes=DEST.stat().st_size,
        sha256=digest,source_member_count=853,zip_crc='ok',member_hashes='ok'),ensure_ascii=False),flush=True)
    return DEST
if __name__=='__main__':run()
