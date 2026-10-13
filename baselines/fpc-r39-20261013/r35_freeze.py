"""R35 immutable R34 ZIP source byte validation; never silently updates ancestors."""
import hashlib,json,zipfile
from pathlib import Path
from r25_capture import ROOT
ARCH=ROOT.parent/'RAZR_SLIDE_R34_verified_engineering_package_20261011.zip'
HASH=ROOT.parent/'RAZR_SLIDE_R34_verified_engineering_package_20261011.sha256'

def run(write=True):
    expected=HASH.read_text().split()[0]; actual=hashlib.sha256(ARCH.read_bytes()).hexdigest()
    assert actual==expected,('R34 ZIP hash differs',actual,expected)
    rows=[]
    with zipfile.ZipFile(ARCH) as z:
        assert z.testzip() is None
        for info in z.infolist():
            if info.is_dir():continue
            original=z.read(info.filename); dst=ROOT/info.filename
            assert dst.is_file() and dst.read_bytes()==original,('ancestor changed',info.filename)
            rows.append(dict(path=info.filename,size_bytes=len(original),sha256=hashlib.sha256(original).hexdigest()))
    assert len(rows)==783,len(rows)
    out=dict(version='R35 immutable R34 ancestor',R34_original_zip_sha256=actual,original_member_count=len(rows),
             all_ancestor_bytes_unchanged=True,entries=rows)
    if write:(ROOT/'audit/R35_R34_immutable.json').write_text(json.dumps(out,indent=2)+'\n')
    print('R35 R34 ANCESTOR VERIFIED',len(rows),flush=True)
    return out
if __name__=='__main__':run()
