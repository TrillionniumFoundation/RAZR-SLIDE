"""R38 atomic pack: original R37 ZIP bytes per member, never extracted pyc.
Externally verify exact SHA256/CRC and every manifest-recorded member.
"""
from pathlib import Path
import os,json,zipfile,hashlib,fnmatch,datetime
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/data/files/RAZR_SLIDE_R37_verified_engineering_package_20261011.zip')
DEST=Path('/mnt/data/RAZR_SLIDE_R38_verified_engineering_package_20261011.zip')
SHA='b0013a530c980d10a53a48fb25db0919636ac81184b8f20c1e98a0704838b487'

def hash_bytes(x):return hashlib.sha256(x).hexdigest()
def pack():
    with open(BASE,'rb') as b: assert hashlib.file_digest(b,'sha256').hexdigest()==SHA
    with zipfile.ZipFile(BASE) as old:
        assert old.testzip() is None
        frozen=[]
        old_entries={}
        for entry in old.infolist():
            if entry.is_dir():continue
            raw=old.read(entry.filename)
            old_entries[entry.filename]=raw
            frozen.append({'path':entry.filename,'size':len(raw),'sha256':hash_bytes(raw)})
    assert len(frozen)==1043
    (ROOT/'audit').mkdir(exist_ok=True)
    froze={'R37_original_zip_name':BASE.name,'R37_original_zip_sha256':SHA,'member_count':len(frozen),
           'source_provenance':'externally verified original R37 ZIP, identical original uncompressed member bytes',
           'entries':frozen}
    (ROOT/'audit/R38_R37_frozen_manifest.json').write_text(json.dumps(froze,ensure_ascii=False,indent=2)+'\n')
    roots=['r38_parts.py','r38_integration.py','r38_faults.py','r38_export.py','r38_inherited.py','r38_verify_offline.py','r38_pack.py','test_r38.py','R38_REPRODUCE.sh','README_先读_R38.md','R38_hardgate_audit_20261011.md','R38_supplier_requests_20261011.md','audit/R38_R37_frozen_manifest.json']
    roots += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'cad').glob('R38_*')) if p.is_file()]
    roots += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'verification').glob('R38_*')) if p.is_file()]
    roots=sorted(set(roots))
    assert not any(p in old_entries for p in roots)
    new_entries={p:(ROOT/p).read_bytes() for p in roots}
    assert all(new_entries[p] for p in roots)
    payload={**old_entries,**new_entries}
    manifests={'format':'RAZR_SLIDE_R38_MEMBER_SHA256_V1','R37_original_source_sha256':SHA,
      'inherited_members':len(old_entries),'new_R38_members':len(new_entries),
      'entries':[{'path':n,'sha256':hash_bytes(payload[n]),'size_bytes':len(payload[n]),'kind':'inherited_exact_R37' if n in old_entries else 'new_R38'} for n in sorted(payload)]}
    mn='audit/R38_package_member_manifest.json'
    payload[mn]=(json.dumps(manifests,ensure_ascii=False,indent=2)+'\n').encode()
    tmp=DEST.with_suffix('.zip.partial')
    with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as out:
        for n in sorted(payload): out.writestr(n,payload[n])
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert len(names)==len(payload) and set(names)==set(payload)
        m=json.loads(z.read(mn))
        assert len(m['entries'])==len(payload)-1
        for row in m['entries']:
            assert hash_bytes(z.read(row['path']))==row['sha256']
        for n,data in old_entries.items():assert z.read(n)==data
    os.replace(tmp,DEST)
    with open(DEST,'rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    with zipfile.ZipFile(DEST) as z:
        assert z.testzip() is None
        zmanifest=json.loads(z.read(mn))
        assert len(zmanifest['entries'])==len(z.namelist())-1
    checksum_file=DEST.with_suffix('.sha256')
    checksum_file.write_text(f'{sha}  {DEST.name}\n')
    return {'archive':str(DEST),'bytes':DEST.stat().st_size,'sha256':sha,
        'members_total':len(payload),'members_sha256_manifested':len(manifests['entries']),
        'R37_original_members_unchanged':len(old_entries),'new_R38_files':len(new_entries),
        'zip_crc_passed':True,'all_member_hashes_passed':True,'manufacturing_go':False}
if __name__=='__main__':
    result=pack();print(json.dumps(result,indent=2))
    Path('/mnt/data/R38_pack_receipt_20261011.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
