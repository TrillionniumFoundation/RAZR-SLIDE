"""Finish immutable delivery of the already-computed complete frame matrix.

The original computation passed its global checks; its publication failed with
EXDEV.  This script preserves that receipt, validates the saved K, and copies
verified stable bytes without repeating FE assembly or changing its history.
"""
from pathlib import Path
import gc
import json
import os
import resource
import shutil
import sys
import time
import numpy as np
import scipy
from scipy.sparse import load_npz
from scipy.spatial import cKDTree
from rebuild_l2_only import sha, save_json, free_bytes, ROOT, BASE
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'integration'))
from tetra_bubble_refinement import p2_nodes


def main():
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    out=BASE/'l2-rebuild/frame';level=out/'level-2'
    receipt=out/'progress.json'
    old=json.loads(receipt.read_text())
    assert old['phase']=='interrupted_or_failed' and old['error_type']=='OSError'
    assert 'Invalid cross-device link' in old['error']
    assert old['assembled_elements']==old['total_elements']==79628
    assert old['five_global_assembly_energy_probes_relative_error']<1e-11
    assert old['six_rigid_modes_action_absolute_max']<1e-9
    prior_hash=sha(receipt)
    src=Path(old['private_temporary_directory'])/'K.npz'
    assert src.is_file() and not (src.parent/'partial-elements.npy').exists()
    sources={**old['source_sha256'],str(Path(__file__)):sha(Path(__file__))}
    for path,digest in {**old['input_sha256'],**sources}.items():
        assert sha(path)==digest
    source_K_sha=sha(src)
    if free_bytes(out)<2*src.stat().st_size+500*1024**2:
        raise RuntimeError('copy plus possible sync copy would violate 500MiB reserve')
    original=BASE/'frozen-original/frame'
    with np.load(original/'mesh.npz',allow_pickle=False) as mesh:
        vertices=mesh['points'][mesh['tetra']]
    with np.load(original/'loads.npz',allow_pickle=False) as ld:
        xyz=ld['xyz'];rigid=ld['R']
    n=xyz.shape[1]
    tree=cKDTree(xyz[:,::3].T)
    ids=np.empty((len(vertices),30),dtype=np.int32)
    maximum_error=0.0
    for lo in range(0,len(vertices),2048):
        hi=min(lo+2048,len(vertices))
        distance,index=tree.query(p2_nodes(vertices[lo:hi]).reshape(-1,3))
        maximum_error=max(maximum_error,float(distance.max()))
        ids[lo:hi]=(3*index.reshape(-1,10,1)+np.arange(3)).reshape(-1,30)
    assert maximum_error==old['coordinate_mapping_error_mm']
    assert np.array_equal(np.unique(ids),np.arange(n))
    del tree,xyz
    K=load_npz(src)
    assert K.shape==(474726,474726) and K.nnz==old['K_nnz']
    assert np.isfinite(K.data).all()
    difference=K-K.T
    asym=float(np.max(abs(difference.data),initial=0.0))
    assert asym==old['K_symmetry_absolute_max']
    rigid_action=float(np.max(abs(K@rigid)))
    assert rigid_action==old['six_rigid_modes_action_absolute_max']
    del difference,K,rigid
    gc.collect()
    final=level/'K.npz'
    assert not final.exists()
    # K is now immutable; this is one copy, never a changing memmap.
    temporary=level/'K.npz.writing'
    shutil.copyfile(src,temporary)
    assert sha(temporary)==source_K_sha
    os.replace(temporary,final)
    np.savez_compressed(out/'mapping.npz',element_dofs=ids,vertices=vertices)
    for name in ('mesh.npz','loads.npz'):
        os.link(original/name,level/name)
    for path,digest in {**old['input_sha256'],**sources}.items():
        assert sha(path)==digest
    assert sha(receipt)==prior_hash
    finalized={'schema':'razr-frame-matrix-delivery-finalization-v1',
               'assembly_receipt':str(receipt),'assembly_receipt_sha256':prior_hash,
               'original_publication_error_preserved':True,'FE_reassembled':False,
               'source_K_sha256':source_K_sha,'destination_K_sha256':sha(final),
               'serialized_matrix_symmetry_and_six_rigid_modes_rechecked':True,
               'source_sha256':sources,'seconds':time.monotonic()-started,
               'completed':True}
    save_json(out/'delivery-finalization.json',finalized)
    report={'schema':'razr-fresh-L2-reconstruction-v1','body':'frame','level':2,
            'original_tetrahedra':79628,'subtetrahedra':16*79628,'dofs':n,'condensed_dofs':n,
            'full_uncondensed_dofs':n+75*79628,'E_normalization':1.0,'nu':0.3,
            'body_loads_on_added_internal_DOFs':False,'original_faces_and_surface_P2_traces_unchanged':True,
            'K_sha256':source_K_sha,'loads_sha256':sha(original/'loads.npz'),
            'mesh_sha256':sha(original/'mesh.npz'),'mapping_sha256':sha(out/'mapping.npz'),
            'K_bytes':final.stat().st_size,'K_nnz':old['K_nnz'],'K_symmetry_absolute_max':asym,
            'global_directional_energy_probes':5,
            'global_energy_relative_error_max':old['five_global_assembly_energy_probes_relative_error'],
            'rigid_modes_checked':6,'rigid_mode_action_max':rigid_action,
            'coordinate_mapping_max_error_mm':maximum_error,
            'minimum_scalar_DOF_separation_mm':old['minimum_scalar_dof_separation_mm'],
            'input_sha256':old['input_sha256'],'source_sha256':sources,
            'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},
            'element_assembly_seconds':old['element_assembly_seconds'],
            'seconds_to_original_publication_error':old['elapsed_seconds'],
            'peak_rss_kib':old['peak_rss_kib'],'delivery_finalization_sha256':sha(out/'delivery-finalization.json'),
            'new_rebuild_identity':True,'original_historical_artifact_restored':False,
            'full_inverse_operator_probes_executed':False,'new_QP_executed':False,
            'contact_or_mesh_convergence_qualified':False,'candidate_go':False,
            'fixture_fabrication_go':False,'manufacturing_go':False}
    save_json(level/'report.json',report)
    # Keep the verified workspace matrix; no longer need a duplicate in /tmp.
    with src.open('r+b') as f:f.truncate(0)
    src.unlink();src.parent.rmdir()
    print(json.dumps({'completed':True,'K_sha256':source_K_sha,'K_bytes':report['K_bytes'],
                      'root_free_bytes':free_bytes(out),'report':str(level/'report.json')}),flush=True)


if __name__=='__main__':
    main()
