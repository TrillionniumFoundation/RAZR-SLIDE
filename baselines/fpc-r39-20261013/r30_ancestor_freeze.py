"""Independent exact R29 ZIP-member freeze. Never mutates the source archive."""
from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT.parent/'RAZR_SLIDE_R29_engineering_package_20261011.zip'
SHA=ROOT.parent/'RAZR_SLIDE_R29_engineering_package_20261011.sha256'

def run(write=True):
    archive_sha=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    expected=SHA.read_text().split()[0]
    assert archive_sha==expected, 'R29 source archive hash changed'
    entries=[]
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        for n in sorted(x for x in z.namelist() if not x.endswith('/')):
            original=z.read(n)
            candidate=ROOT/n
            assert candidate.is_file(),f'R29 member missing {n}'
            content=candidate.read_bytes()
            digest=hashlib.sha256(original).hexdigest()
            if hashlib.sha256(content).hexdigest()!=digest:
                raise ValueError(f'R29 frozen member differs: {n}')
            entries.append({'path':n,'sha256':digest,'size_bytes':len(original)})
    r={'revision':'R30 R29 immutable input evidence',
       'R29_zip_sha256':archive_sha,'R29_zip_member_count_verified':len(entries),
       'entries':entries,'prior_artifacts_unchanged':True,
       'new_R30_work_does_not_change_R29_source':True}
    if write:
        p=ROOT/'audit'/'R30_R29_ORIGINAL_ZIP_MEMBERS.json';p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    return r
if __name__=='__main__':
    r=run();print('R30 ORIGINAL R29',r['R29_zip_member_count_verified'],'SHA verified',flush=True)
