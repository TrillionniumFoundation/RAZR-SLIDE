"""Prepare exact immutable numerical sources with bounded selective extraction."""
import hashlib, json, os, pathlib, resource, shutil, sys, tarfile, time, zipfile

BASE=pathlib.Path(__file__).resolve().parent
ARCHIVES=BASE/'original_archives'
WORK=BASE/'original_inputs'
OUT=BASE/'evidence'
OUT.mkdir(exist_ok=True)

def ident(p):
    p=pathlib.Path(p)
    with p.open('rb') as f: h=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(p),bytes=p.stat().st_size,sha256=h)

def unpack_member(z,name,target):
    target=pathlib.Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    with z.open(name) as src,target.open('xb') as dst: shutil.copyfileobj(src,dst)

def main():
    archives={
      'RAZR-SLIDE_N13_original_five_science_20261027.zip':'0eafd8bed644679680d8a05cbfd64f883db968e3d26b6780549850c4ca7b83f5',
      'RAZR-SLIDE_N14_frame_original_five_checkpoint_20261027.zip':'da653030541b93b2abaf838285fa7456d7474d4a2dd2b377394355774c2b0e6e',
      'frame-full-L2-rebuild-20261023.tar.xz':'1c41ae773f93e7259293e3e09db78099f4dce574c05cdc2c5d46b093ad36d90b'}
    inputs={}
    for name,expected in archives.items():
        value=ident(ARCHIVES/name); assert value['sha256']==expected
        inputs[name]=value
    cg=pathlib.Path('/sys/fs/cgroup')
    stats=dict(line.split() for line in (cg/'memory.stat').read_text().splitlines())
    plan=dict(schema='r12.original_numeric_selective_replay_preflight.v1',recorded_unix=time.time(),
        source=ident(__file__),archives=inputs,disk_free_bytes=shutil.disk_usage(BASE).free,
        memory_max=(cg/'memory.max').read_text().strip(),memory_current=(cg/'memory.current').read_text().strip(),
        memory_stat=stats,threads=1,reader_wall_limit_seconds=180,
        historical_panel_worker_peak_KiB=909960,historical_frame_worker_peak_KiB=1204456,
        selected_extraction_estimate_bytes=1050000000,total_own_disk_limit_bytes=2*1024**3,
        algorithm='Same original CSC scalar float64 products with exact original K/b/C/full fields; unchanged N13 reader and R9 frame reader; no factorization or new solver.',
        historical_passes_preserved=True,original_float64_gate=1e-7)
    (OUT/'CAPACITY_AND_ALGORITHM_BASIS.json').write_text(json.dumps(plan,indent=2)+'\n')
    assert plan['disk_free_bytes']>1500000000
    z=zipfile.ZipFile(ARCHIVES/'RAZR-SLIDE_N13_original_five_science_20261027.zip')
    report=json.loads(z.read('native/N13-v3/N13_REPORT.json'))
    run=WORK/'n13/native/N13-v3'
    for name in sorted(set(report['files'])|{'N13_REPORT.json'}):
        unpack_member(z,'native/N13-v3/'+name,run/name)
    unpack_member(z,'source/current/readback_n13.py',WORK/'n13/source/current/readback_n13.py')
    with z.open('original/N12-engineering-40474654390.zip') as nested:
        inner=zipfile.ZipFile(nested)
        needed=set(report['original_input_identities'])|{x['file'] for x in report['baseline_field_references']}
        needed.update(['EXPORT_MANIFEST.json','source/probe_n12_coordinates.py','source/n12_contract.py',
            'frozen/frozen/frozen/frozen/frozen/volume/panel/level-2/loads.npz'])
        for name in sorted(needed): unpack_member(inner,name,WORK/'n12'/name)
    z=zipfile.ZipFile(ARCHIVES/'RAZR-SLIDE_N14_frame_original_five_checkpoint_20261027.zip')
    for info in z.infolist():
        name=info.filename
        if name.startswith(('native/frame-numeric/','inputs/')) and not name.endswith('/'):
            unpack_member(z,name,WORK/'n14'/name)
    expected={'frame/level-2/K.npz','frame/level-2/loads.npz'}
    got=set()
    with tarfile.open(ARCHIVES/'frame-full-L2-rebuild-20261023.tar.xz','r:xz') as tf:
        for member in tf:
            if member.name in expected:
                assert member.isfile()
                dest=WORK/'frame-volume'/member.name
                dest.parent.mkdir(parents=True,exist_ok=True)
                with tf.extractfile(member) as src,dest.open('xb') as dst: shutil.copyfileobj(src,dst)
                got.add(member.name)
    assert got==expected
    manifest=[ident(p) for p in sorted(WORK.rglob('*')) if p.is_file()]
    payload=sum(x['bytes'] for x in manifest)
    total=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())
    assert total<2*1024**3,(payload,total)
    result=dict(schema='r12.original_numeric_selective_recovery.v1',completed=True,
        files=manifest,file_count=len(manifest),extracted_bytes=payload,own_total_bytes=total,
        historical_inputs_recovered_byte_for_byte=True,preflight=ident(OUT/'CAPACITY_AND_ALGORITHM_BASIS.json'))
    (OUT/'SELECTIVE_RECOVERY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['completed','file_count','extracted_bytes','own_total_bytes']}))

if __name__=='__main__': main()
