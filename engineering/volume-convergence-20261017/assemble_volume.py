"""Reassemble original P2 K, then two nested face-preserving volume enrichments.

All original boundary/trace coordinates, surface loads, gauges and fixture
DOFs remain exact. New internal DOFs are statically condensed, not anchored.
This is a volume-space sensitivity experiment, not full h/trace convergence.
"""
from pathlib import Path
import argparse,json,time,sys,shutil
import numpy as np
from scipy.sparse import coo_matrix,save_npz,load_npz
from skfem import MeshTet,Basis,ElementVector,ElementTetP2
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import sha256
from tetra_bubble_refinement import REF,p2_nodes,p2_stiffness,star_condense

def main(a):
    src=a.inputs/a.body;out=a.output;out.mkdir(parents=True,exist_ok=False)
    registered=json.loads((ROOT/'engineering/spatial-contact-integration-20261015'/f'{a.body}-elastic-input.json').read_text())
    for file,key in [('mesh.npz','mesh_sha256'),('loads.npz','loads_sha256'),('K.npz','K_sha256')]:
        assert sha256(src/file)==registered[key],(file,'source identity differs')
    data=np.load(src/'mesh.npz',allow_pickle=False);mesh=MeshTet(data['points'].T,data['tetra'].T)
    b=Basis(mesh,ElementVector(ElementTetP2()),intorder=2);ld=np.load(src/'loads.npz',allow_pickle=False)
    assert np.array_equal(b.doflocs,ld['xyz']) and b.N==registered['dofs']
    loc=ElementTetP2().doflocs;perm=np.array([np.argmin(np.linalg.norm(loc-x,axis=1)) for x in p2_nodes(REF)])
    assert np.max(abs(loc[perm]-p2_nodes(REF)))<1e-15
    ids=b.element_dofs[(3*perm[:,None]+np.arange(3)).ravel()].T
    vertices=mesh.p.T[mesh.t.T];nt=len(vertices)
    boundary=b.get_dofs(mesh.boundary_facets()).all()
    applied=np.unique(np.r_[np.flatnonzero(np.any(ld['C']!=0,axis=1)),np.flatnonzero(np.any(ld['F']!=0,axis=1))])
    # The frozen nodal vectors contain tiny nonboundary entries (~1e-17).
    # Retain every byte/value: all original P2 DOFs lie on parent cell faces,
    # and none is an introduced internal DOF. Do not zero the old entries.
    inside=np.setdiff1d(np.arange(b.N),boundary)
    nonboundary={key:float(np.max(abs(ld[key][inside]),initial=0.)) for key in ('C','F')}
    assert np.array_equal(np.unique(ids),np.arange(b.N)), 'all old nodal loads must map to retained skeleton DOFs'
    np.savez_compressed(out/'mapping.npz',element_dofs=ids,vertices=vertices)
    rows=np.broadcast_to(ids[:,:,None],(nt,30,30)).ravel();cols=np.broadcast_to(ids[:,None,:],(nt,30,30)).ravel()
    reports=[]
    for level in (0,1,2):
        start=time.monotonic();values=np.empty((nt,30,30));max_recover_residual=0.
        for lo in range(0,nt,256):
            hi=min(lo+256,nt);v=vertices[lo:hi]
            if level==0:values[lo:hi]=p2_stiffness(v)
            else:values[lo:hi]=star_condense(v,level=level).stiffness
            if lo%8192==0:print('ASSEMBLE',a.body,level,lo,nt,flush=True)
        K=coo_matrix((values.ravel(),(rows,cols)),shape=(b.N,b.N)).tocsc();K.sum_duplicates();K.sort_indices()
        folder=out/f'level-{level}';folder.mkdir()
        rec={'body':a.body,'level':level,'original_tetrahedra':nt,'subtetrahedra':nt*4**level,'condensed_dofs':int(b.N),
             'full_uncondensed_dofs':int(b.N)+15*nt*((4**level-1)//3),'E_normalization':1.,'nu':.3,
             'body_loads_on_added_internal_DOFs':False,'old_nonboundary_entries_preserved':nonboundary,'original_faces_and_surface_P2_traces_unchanged':True,
             'input_sha256':{str(src/n):sha256(src/n) for n in ('K.npz','mesh.npz','loads.npz')},
             'module_sha256':sha256(ROOT/'integration/tetra_bubble_refinement.py'),'assembler_sha256':sha256(__file__),
             'is_uniform_h_refinement':False,'full_contact_or_mesh_convergence_qualified':False}
        if level==0:
            original=load_npz(src/'K.npz');delta=K-original
            rec['original_K_reassembly_max_error']=float(np.max(abs(delta.data),initial=0.))
            rec['original_K_relative_max_error']=rec['original_K_reassembly_max_error']/float(np.max(abs(original.data)))
            assert rec['original_K_relative_max_error']<1e-11
            del original,delta
        save_npz(folder/'K.npz',K,compressed=False)
        for name in ('loads.npz','mesh.npz'):shutil.copyfile(src/name,folder/name)
        rec['K_sha256']=sha256(folder/'K.npz');rec['loads_sha256']=sha256(folder/'loads.npz');rec['mesh_sha256']=sha256(folder/'mesh.npz');rec['dofs']=int(b.N);rec['seconds']=time.monotonic()-start
        (folder/'report.json').write_text(json.dumps(rec,indent=2)+'\n');reports.append(rec)
        print('LEVEL_DONE',a.body,level,rec['subtetrahedra'],rec['full_uncondensed_dofs'],rec['seconds'],flush=True)
        del values,K
    (out/'SUMMARY.json').write_text(json.dumps({'body':a.body,'levels':reports,'passed':True},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--body',choices=['panel','frame'],required=True);p.add_argument('--output',type=Path,required=True)
    main(p.parse_args())
