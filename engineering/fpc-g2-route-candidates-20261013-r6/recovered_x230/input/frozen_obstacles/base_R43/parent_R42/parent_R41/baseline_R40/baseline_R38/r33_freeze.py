"""Every R32 member must match its ORIGINAL sealed ZIP, byte for byte."""
from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=Path('/mnt/data/RAZR_SLIDE_R32_engineering_package_20261011.zip')
EXTERNAL=Path('/mnt/data/RAZR_SLIDE_R32_engineering_package_20261011.sha256')

def run(write=True):
    expected=EXTERNAL.read_text().split()[0]
    actual=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert expected==actual,(expected,actual)
    records=[]
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        for n in sorted(z.namelist()):
            b=z.read(n)
            p=ROOT/n
            assert p.is_file() and p.read_bytes()==b,n
            records.append({'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    assert len(records)==636,len(records)
    d={'R32_zip_sha256':actual,'R32_ancestor_count':len(records),
       'R32_all_members_unchanged':True,'records':records,'manufacturing_go':False}
    if write:(ROOT/'audit/R33_R32_immutable.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print('R33 FREEZE',len(records),actual,flush=True)
    return d
if __name__=='__main__':run()
