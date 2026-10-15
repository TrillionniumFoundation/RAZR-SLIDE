"""Verify exact R36 predecessor archive and every inherited member byte for byte."""
from pathlib import Path
import zipfile,hashlib,json
from r25_capture import ROOT
SOURCE=ROOT.parent/'files/RAZR_SLIDE_R36_verified_engineering_package_20261011.zip'
EXPECTED_SHA='0f5219663e6eae8c6817e6082c0d60172dcd9228386d3ec661fdbc9b9c2cf74d'

def hash_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()

def run(write=True):
    assert hash_file(SOURCE)==EXPECTED_SHA,'R36 source archive SHA differs'
    rows=[]
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        for a in z.infolist():
            assert not a.is_dir()
            raw=z.read(a.filename)
            path=ROOT/a.filename
            assert path.is_file() and path.read_bytes()==raw,'Inherited file modified: '+a.filename
            rows.append(dict(path=a.filename,size=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    result=dict(revision='R37 strict R36 ZIP provenance and immutable content',
         R36_source_archive=SOURCE.name,source_sha256=EXPECTED_SHA,
         immutable_original_files=len(rows),all_bytes_identical=True,source_zip_crc_ok=True,
         entries=rows,manufacturing_go=False)
    if write:(ROOT/'audit/R37_R36_immutable.json').write_text(json.dumps(result,indent=2)+'\n')
    print('R37 frozen predecessor',len(rows),EXPECTED_SHA,flush=True)
    return result
if __name__=='__main__':run()
