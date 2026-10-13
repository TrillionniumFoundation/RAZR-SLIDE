"""Independent source-archive byte-for-byte verifier for R31 ancestors."""
from __future__ import annotations
import zipfile,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=Path('/mnt/data/files/RAZR_SLIDE_R31_engineering_package_20261011.zip')

def run():
    rows=[]
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        for n in sorted(z.namelist()):
            raw=z.read(n)
            p=ROOT/n
            assert p.is_file() and p.read_bytes()==raw, n
            rows.append({'path':n,'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    assert len(rows)==564,len(rows)
    m={'revision':'R32 byte immutable R31 baseline','R31_original_SHA256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
       'verified_R31_original_files':len(rows),'original_unchanged':True,'entries':rows}
    (ROOT/'audit'/'R32_R31_FROZEN_SHA256.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print('R32 FROZEN',len(rows),m['R31_original_SHA256'],flush=True)
    return m
if __name__=='__main__':run()
