"""Read-only verification of all 504 R30 frozen files against exact source ZIP.
The archive is intentionally external, never modified or implicitly copied.
"""
from __future__ import annotations
import zipfile,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ORIGINAL=Path('/mnt/data/RAZR_SLIDE_R30_engineering_package_20261011.zip')
SHA_FILE=Path('/mnt/data/RAZR_SLIDE_R30_engineering_package_20261011.sha256')

def run():
    expected=SHA_FILE.read_text().split()[0]
    actual=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    if expected!=actual:raise AssertionError(f'original R30 zip hash mismatch: {expected} vs {actual}')
    with zipfile.ZipFile(ORIGINAL) as z:
        if z.testzip() is not None:raise ValueError('corrupt R30 source')
        rows=[]
        for filename in sorted(z.namelist()):
            b=z.read(filename)
            p=ROOT/filename
            if not p.is_file() or p.read_bytes()!=b:raise AssertionError(filename)
            rows.append(dict(path=filename,size_bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    if len(rows)!=504:raise AssertionError(len(rows))
    d={'revision':'R31 R30 bit-for-bit immutable frozen baseline',
       'original_zip_sha256':actual,'entries':rows,'verified_count':len(rows),
       'original_ZIP_verified':True,'prior_files_unchanged':True}
    dest=ROOT/'audit'/'R31_R30_ORIGINAL_ZIP_MEMBERS.json'
    dest.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print('R31 FROZEN',len(rows),'SHA256',actual,flush=True)
    return d
if __name__=='__main__':run()
