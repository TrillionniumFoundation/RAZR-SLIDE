"""Reclaim only a verified redundant engineering expansion after durable sealing."""
import hashlib,json,os,resource,signal,stat,time,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
directory=root/'r7-native/full-near-attempt1-engineering'
archive=root/'r7-deliverables/RAZR-R7-near-full-factory-and-independent-originals-20261028.zip'
seal_path=root/'r7-native/R7_NEAR_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json'
receipt_path=root/'r7-publication/R7_NEAR_ENGINEERING_ARCHIVE_MIGRATION_V1.json'
assert not receipt_path.exists()
started=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('120sverifiedarchivecopyreclaim')));signal.alarm(120)
def ident(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}
def available():s=os.statvfs(root);return s.f_bavail*s.f_frsize
def state(p):
    s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    return {'inode':s.st_ino,'device':s.st_dev,'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
preserved=json.loads((root/'r7-deliverables/R7_NEAR_COMPLETE_PRESERVATION_V1.json').read_text())
assert preserved['saved_file']['status']=='succeeded' and preserved['saved_file']['library_file_id']=='libfile_03369f15bb2c819189c055031babf4ad'
assert os.getxattr(archive,'user.library-file-id').decode()==preserved['saved_file']['library_file_id']
assert ident(archive)=={'bytes':126771580,'sha256':'711db7175ea364735f337ecc575b7d7ee479df9287d78c7cec08a147120533ae'}
seal=json.loads(seal_path.read_text());expected=seal['engineering_members'];keep={'ENGINEERING_MANIFEST.json','EXPORT_SCOPE.json'}
actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() or p.is_symlink()}
assert actual==set(expected) and keep<=set(expected)
rows=[]
with zipfile.ZipFile(archive) as z:
    infos={i.filename:i for i in z.infolist()};assert len(infos)==9433
    for name,e in sorted(expected.items()):
        p=directory/name;assert p.resolve().is_relative_to(directory.resolve());before=state(p)
        assert ident(p)==e
        member='engineering/'+name;assert infos[member].file_size==e['bytes']
        h=hashlib.sha256();length=0
        with z.open(member) as f:
            while b:=f.read(1048576):h.update(b);length+=len(b)
        assert {'bytes':length,'sha256':h.hexdigest()}==e and state(p)==before
        rows.append({'relative_path':name,'archive_member':member,'identity':e,'before_lstat':before,'action':'retain' if name in keep else 'reclaim_verified_expanded_copy'})
report={'schema':'razr-r7-verified-near-engineering-archive-migration-v1','wall_seconds':120,'address_space_bytes':268435456,
        'engineering_expansion_path':str(directory),'archive_path':str(archive),'archive_identity':ident(archive),
        'library_file_id':preserved['saved_file']['library_file_id'],'historical_near_seal_identity':ident(seal_path),
        'full_archive_and_every_engineering_member_CRC_SHA_before_reclaim_verified':True,
        'historical_near_scientific_pass_reclassified':False,'near_raw_modified':False,'far_or_S4_or_runtime_modified':False,
        'durable_original_members_deleted':False,'current_engineering_expansion_complete':True,
        'available_before_bytes':available(),'verified_members':rows,'removed_members':[],'completed':False}
receipt_path.write_text(json.dumps(report,indent=2)+'\n')
try:
    for row in rows:
        if row['action']=='retain':continue
        p=directory/row['relative_path'];assert state(p)==row['before_lstat'] and ident(p)==row['identity']
        p.unlink();report['removed_members'].append(row['relative_path'])
    for p in sorted((p for p in directory.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        try:p.rmdir()
        except OSError:pass
    remaining={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() or p.is_symlink()}
    assert remaining==keep and all(ident(directory/n)==expected[n] for n in keep)
    report.update(completed=True,current_engineering_expansion_complete=False,
        retained_expanded_members=sorted(keep),removed_expanded_member_count=len(report['removed_members']),
        reclaimed_expanded_bytes=sum(row['identity']['bytes'] for row in rows if row['action']!='retain'),
        retained_expanded_bytes=sum(expected[n]['bytes'] for n in keep),
        restoration_method='Read the complete verified engineering/<relative_path> members from the retained local or saved full original ZIP; preserve original bytes and relative paths.')
finally:
    signal.alarm(0);report.update(available_after_bytes=available(),elapsed_seconds=time.monotonic()-started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    receipt_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('verified_members','removed_members')}))
