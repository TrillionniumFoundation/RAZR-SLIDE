"""Byte-preserving R33 ancestor provenance verification (706 ZIP members)."""
from __future__ import annotations
import json,hashlib,zipfile
from r25_capture import ROOT
ARCHIVE=ROOT.parent/'files/RAZR_SLIDE_R33_engineering_package_20261011.zip'
CHECK=ROOT.parent/'files/RAZR_SLIDE_R33_engineering_package_20261011.sha256'

def run(write=True):
    digest=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    expected=CHECK.read_text().strip().split()[0]
    assert digest==expected,('R33 original ZIP changed',digest,expected)
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        originals=[]
        for member in z.infolist():
            if member.is_dir():continue
            p=ROOT/member.filename
            raw=z.read(member.filename)
            assert p.is_file() and p.read_bytes()==raw,('ancestor file altered',member.filename)
            originals.append(dict(path=member.filename,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    assert len(originals)==706, len(originals)
    out=dict(revision='R34 R33 immutable imported ancestor, bytewise checked',
             ancestor_zip_sha256=digest,ancestor_files_verified=len(originals),
             all_ancestor_bytes_unchanged=True,originals=originals)
    if write:(ROOT/'audit/R34_R33_immutable.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('R34 ancestor immutable',len(originals),digest,flush=True)
    return out
if __name__=='__main__':run()
