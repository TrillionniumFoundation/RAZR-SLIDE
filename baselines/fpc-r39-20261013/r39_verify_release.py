"""Offline verification of the R39 archive itself (not hardware qualification)."""
import os,sys,zipfile,json,hashlib
from pathlib import Path
MANIFEST='audit/R39_package_member_manifest.json'
def verify(path,source=None):
    path=Path(path);sha=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
    with zipfile.ZipFile(path) as z:
        bad=z.testzip(); assert bad is None,('CRC',bad)
        names=z.namelist();assert len(names)==len(set(names))
        doc=json.loads(z.read(MANIFEST));assert len(names)==doc['non_manifest_member_count']+1
        wanted=set(row['name'] for row in doc['members']); assert wanted==set(names)-{MANIFEST}
        for row in doc['members']:
            assert hashlib.sha256(z.read(row['name'])).hexdigest()==row['sha256'],('member',row['name'])
        assert not json.loads(z.read('verification/R39_results.json'))['manufacturing_go']
        if source is not None:
            with zipfile.ZipFile(source) as frozen:
                assert hashlib.file_digest(open(source,'rb'),'sha256').hexdigest()==doc['source_R38_archive_sha256']
                assert len(frozen.namelist())==doc['R38_ancestor_member_count']==1094
                for name in frozen.namelist(): assert z.read(name)==frozen.read(name),('R38 ancestor corruption',name)
        print('R39 release verified members',len(names),'zip_size',path.stat().st_size,'sha256',sha,'source_frozen_compared',source is not None,flush=True)
    return sha
if __name__=='__main__':
    verify(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
