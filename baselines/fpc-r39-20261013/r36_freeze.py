"""Record and verify byte-for-byte immutable R35 source from verified ZIP.
Does not overwrite any ancestor path. Requires external original ZIP for initial attestation.
"""
import zipfile,hashlib,json
from pathlib import Path
from r25_capture import ROOT
ARCH=Path('/mnt/data/files/RAZR_SLIDE_R35_verified_engineering_package_20261011.zip')
KNOWN='ee0b2eedc9f4b36c1e832b8d5dbdd3bbf121eb724e126d8fb84981f3ebd2a8c9'
def run(write=True,archive=ARCH):
    archive=Path(archive)
    if not archive.is_file():
        raise FileNotFoundError('For initial freeze require original R35 archive, not a cached path')
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest==KNOWN,(digest,KNOWN)
    rows=[]
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for info in z.infolist():
            if info.is_dir():continue
            data=z.read(info.filename);loc=ROOT/info.filename
            assert loc.is_file() and loc.read_bytes()==data, ('R35 ancestor mutated',info.filename)
            rows.append(dict(path=info.filename,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    assert len(rows)==853,len(rows)
    out=dict(revision='R36 bytewise verified ancestor from R35 immutable archive',
      ancestor_archive_name=archive.name,ancestor_archive_sha256=digest,
      original_file_count=len(rows),original_bytes_unchanged=True,members=rows)
    if write:(ROOT/'audit/R36_R35_immutable.json').write_text(json.dumps(out,indent=2)+'\n')
    print('R36 R35 FREEZE',len(rows),digest,flush=True)
    return out
if __name__=='__main__':run()
