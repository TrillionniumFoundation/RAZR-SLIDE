"""Separate ideal rigid-root post comparator, not a second whole-panel boundary.

Same E=1,nu=.3 and full-face unit load as the full-panel diagnostic. Rectangular
posts are isolated on purpose to measure the effect of the ideal rigid-root
assumption; this is not deleting panel geometry from the full-panel model.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.sparse.linalg import splu
from skfem import MeshTet,Basis,FacetBasis,ElementVector,ElementTetP2,LinearForm,asm
from skfem.models.elasticity import linear_elasticity,lame_parameters
O=Path(__file__).resolve().parent;rows=[]
for width,label in ((1.2,'front'),(1.45,'rear')):
    for level,nx,ny,nz in ((0,3,4,16),(1,5,6,28)):
        mesh=MeshTet.init_tensor(np.linspace(0,1,nx+1),np.linspace(0,width,ny+1),np.linspace(0,6.35,nz+1));el=ElementVector(ElementTetP2());basis=Basis(mesh,el,intorder=4)
        K=asm(linear_elasticity(*lame_parameters(1.,.3)),basis).tocsc()
        @LinearForm
        def traction(v,w):return v[0]
        fb=FacetBasis(mesh,el,facets=mesh.facets_satisfying(lambda x:np.isclose(x[0],0.)),intorder=4);f=asm(traction,fb)/float(fb.dx.sum())
        D=basis.get_dofs(facets=mesh.facets_satisfying(lambda x:np.isclose(x[2],0.))).all();free=np.setdiff1d(np.arange(basis.N),D);lu=splu(K[free][:,free],permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True})
        u=np.zeros(basis.N);u[free]=lu.solve(f[free]);r=K@u-f;c=float(f@u);energy=float(u@(K@u)/2);res=float(np.max(np.abs(r[free])));axes=basis.split_indices();force=np.array([f[i].sum() for i in axes]);reaction=np.array([r[i].sum() for i in axes]);force_balance=float(np.linalg.norm(force+reaction))
        assert res<1e-7 and force_balance<1e-7 and abs(c-2*energy)/c<1e-8
        path=O/f'post-{label}-{level}.npz';np.savez_compressed(path,points=mesh.p,tetra=mesh.t,dof_xyz=basis.doflocs,u=u,f=f,reaction=r,constrained_dofs=D)
        row={'post':label,'width_mm':width,'height_mm':6.35,'thickness_mm':1.,'level':level,'elements':int(mesh.nelements),'dofs':int(basis.N),'E_delta_over_F_per_mm':c,'free_residual_max_N':res,'force_balance_norm_N':force_balance,'work_energy_relative_error':abs(c-2*energy)/c,'checkpoint_sha256':hashlib.sha256(path.read_bytes()).hexdigest()};rows.append(row);print('POST',row,flush=True)
        del lu,K,basis
fine=json.loads((O/'solve2p2-fixed-recovered.json').read_text());comparisons=[]
for item in fine['loads']:
    label=item['label'].split('_')[1];local=next(x for x in rows if x['post']==label and x['level']==1);coarse=next(x for x in rows if x['post']==label and x['level']==0)
    comparisons.append({'location':item['label'],'complete_panel_ring_clamped_coefficient':item['E_delta_over_F_per_mm'],'isolated_rigid_root_coefficient':local['E_delta_over_F_per_mm'],'panel_to_isolated_ratio':item['E_delta_over_F_per_mm']/local['E_delta_over_F_per_mm'],'isolated_two_mesh_relative_change':abs(local['E_delta_over_F_per_mm']-coarse['E_delta_over_F_per_mm'])/local['E_delta_over_F_per_mm']})
report={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':rows,'comparison':comparisons,'scope':__doc__,'E_is_normalization':True,'actual_material_load_preload_or_joint_capacity':False,'not_exact_whole_panel_rigid_skin_solution':True,'candidate_go':False,'manufacturing_go':False}
(O/'post-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print('COMPARISON',json.dumps(comparisons),flush=True)
