"""Package the two immutable, fully assembled research K matrices in /tmp.

Every member is hashed before compression and verified by streaming extraction.
The complete original execution sources and failed-publication receipt remain
visible. No old contact convergence, inverse probe, or physical pass is claimed.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import resource
import sys
import tarfile
import time

BASE=Path(__file__).resolve().parent
ROOT=Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
PRIVATE=Path('/tmp/razr-fe-20261023/volume-rebuild')
ARCHIVES=Path('/tmp/razr-fe-20261023/archives')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def free_bytes(path):
    s=os.statvfs(path)
    return s.f_bfree*s.f_frsize


class ReserveWriter:
    def __init__(self,path):
        self.path=path
        self.file=path.open('wb')
    def write(self,value):
        if free_bytes(self.path.parent)<500*1024**2:
            raise RuntimeError('500MiB disk reserve reached while compressing stable archive')
        return self.file.write(value)
    def flush(self):
        return self.file.flush()
    def close(self):
        self.file.close()


def main(args):
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    body=args.body
    ARCHIVES.mkdir(parents=True,exist_ok=True)
    archive=ARCHIVES/f'{body}-full-L2-rebuild-20261023.tar.xz'
    assert not archive.exists()
    folder=PRIVATE/body
    report=json.loads((folder/'level-2/report.json').read_text())
    assert digest(folder/'level-2/K.npz')==report['K_sha256']
    files={f'{body}/level-2/{name}':folder/'level-2'/name
           for name in ('K.npz','loads.npz','mesh.npz','report.json')}
    files[body+'/mapping.npz']=folder/'mapping.npz'
    for name in ('frozen-elastic-recovery.json','real-mesh-bounded-probe.json','K-private-relocation.json'):
        files['provenance/'+name]=BASE/name
    files['provenance/'+body+'-assembly-progress.json']=BASE/'l2-rebuild'/body/'progress.json'
    if body=='frame':
        files['provenance/frame-delivery-finalization.json']=BASE/'l2-rebuild/frame/delivery-finalization.json'
    for name in ('rebuild_l2_only.py','rebuild_l2_tmp.py','finalize_frame_matrix.py','real_mesh_bounded_probe.py',Path(__file__).name):
        files['execution-sources/'+name]=BASE/name
    for name in ('tetra_bubble_refinement.py','contact_exchange.py','contact_patch_audit.py'):
        files['repository-sources/integration/'+name]=ROOT/'integration'/name
    for name in ('assemble_volume.py','frozen_load_response.py'):
        files['repository-sources/volume-convergence/'+name]=ROOT/'engineering/volume-convergence-20261017'/name
    for name in ('pyproject.toml','uv.lock'):
        files['runtime/'+name]=ROOT/name
    members={name:{'sha256':digest(path),'bytes':path.stat().st_size,'source_path':str(path)}
             for name,path in sorted(files.items())}
    # Prove the exact version executed is present, even when a later script
    # handled only file publication or relocated an unchanged matrix.
    for path,expected in report['source_sha256'].items():
        assert digest(path)==expected
        assert any(row['sha256']==expected for row in members.values())
    manifest={'schema':'razr-new-full-L2-matrix-artifact-v1','body':body,'members':members,
              'K_sha256':report['K_sha256'],'original_mesh_sha256':report['mesh_sha256'],
              'original_loads_sha256':report['loads_sha256'],'material':{'E_normalization':1.0,'nu':0.3},
              'new_rebuild_identity':True,'historical_K_restored':False,
              'global_assembly_energy_probes':5,'rigid_modes_checked':6,
              'original_five_inverse_operator_probes_executed':False,
              'new_QP_executed':False,'contact_convergence_qualified':False,
              'hardware_or_current_EP5_structural_qualification':False,
              'environment':'Repository uv.lock; original run Python 3.12.14, NumPy 2.5.4, SciPy 1.18.1; no new solver installed.',
              'source_location_note':'Exact execution sources retain original absolute paths. Recreating at other paths requires an explicit new adapter identity; no historical source hash may be relabeled.'}
    payload=json.dumps(manifest,indent=2,allow_nan=False).encode()+b'\n'
    temporary=archive.with_suffix(archive.suffix+'.partial')
    writer=ReserveWriter(temporary)
    print(json.dumps({'phase':'compression_started','body':body,'uncompressed_bytes':sum(r['bytes'] for r in members.values()),'root_free_bytes':free_bytes(ARCHIVES)}),flush=True)
    try:
        with tarfile.open(mode='w:xz',fileobj=writer,preset=3) as tar:
            info=tarfile.TarInfo('ARTIFACT_MANIFEST.json');info.size=len(payload);info.mode=0o644
            tar.addfile(info,io.BytesIO(payload))
            for name,path in sorted(files.items()):
                info=tarfile.TarInfo(name);info.size=members[name]['bytes'];info.mode=0o644
                with path.open('rb') as source:
                    tar.addfile(info,source)
        writer.flush()
    finally:
        writer.close()
    verified=[]
    with tarfile.open(temporary,'r:xz') as tar:
        assert json.load(tar.extractfile('ARTIFACT_MANIFEST.json'))==manifest
        for member in tar.getmembers():
            if member.name=='ARTIFACT_MANIFEST.json':continue
            expected=members[member.name];h=hashlib.sha256();size=0
            source=tar.extractfile(member)
            for block in iter(lambda:source.read(1048576),b''):
                h.update(block);size+=len(block)
            assert h.hexdigest()==expected['sha256'] and size==expected['bytes']
            verified.append(member.name)
    assert set(verified)==set(members)
    for name,path in files.items():
        assert digest(path)==members[name]['sha256'],'input changed during packaging'
    os.replace(temporary,archive)
    receipt={'schema':'razr-verified-L2-artifact-receipt-v1','body':body,'archive':str(archive),
             'archive_sha256':digest(archive),'archive_bytes':archive.stat().st_size,
             'manifest_sha256':hashlib.sha256(payload).hexdigest(),'verified_member_count':len(verified),
             'every_member_stream_hash_verified':True,'K_sha256':report['K_sha256'],
             'seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'full_inverse_operator_probes_executed':False,'new_QP_executed':False,
             'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (BASE/f'{body}-L2-artifact-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body',choices=('panel','frame'),required=True)
    main(parser.parse_args())
