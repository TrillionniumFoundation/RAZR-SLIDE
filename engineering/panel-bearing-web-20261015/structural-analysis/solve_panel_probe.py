from pathlib import Path
import argparse,hashlib,json,time,gc
import numpy as np
from scipy.sparse.linalg import splu
from skfem import MeshTet, Basis, FacetBasis, ElementVector, ElementTetP1, ElementTetP2, LinearForm, asm
from skfem.models.elasticity import linear_elasticity, lame_parameters

p=argparse.ArgumentParser();p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--order',type=int,default=2);p.add_argument('--nu',type=float,default=.3);p.add_argument('--boundary',choices=('rings','both'),default='rings');a=p.parse_args()
a.output.mkdir(exist_ok=False);data=np.load(a.mesh,allow_pickle=False);mesh=MeshTet(data['points'].T,data['tetra'].T);elem=ElementVector(ElementTetP2() if a.order==2 else ElementTetP1());basis=Basis(mesh,elem,intorder=4)
facemap={tuple(sorted(f)):i for i,f in enumerate(mesh.facets.T)}
ids={k:np.asarray([facemap[tuple(sorted(f))] for f in data[k]],dtype=np.int32) for k in data.files if k not in ('points','tetra')}
L,mu=lame_parameters(1.,a.nu);tic=time.monotonic();K=asm(linear_elasticity(L,mu),basis).tocsc();print('ASSEMBLED',basis.N,'DOFS',K.nnz,'NNZ','SECONDS',time.monotonic()-tic,flush=True)
indices=basis.split_indices();coords=basis.doflocs;labels=['L_front','L_rear','R_front','R_rear'];forces=[];loadmeta=[]
for label in labels:
 sign=-1 if label.startswith('L') else 1
 @LinearForm
 def traction(v,w):return sign*v[0]
 fb=FacetBasis(mesh,elem,facets=ids[label],intorder=4);area=float(fb.dx.sum());f=asm(traction,fb)/area
 force=np.array([f[k].sum() for k in indices]);xyz=np.stack([coords[:,k] for k in indices])
 # Full applied moment from the nodal-consistent load vector.
 nodal_forces=np.zeros((basis.N,3))
 for d,k in enumerate(indices):nodal_forces[k,d]=f[k]
 moment=np.cross(coords.T,nodal_forces).sum(axis=0)
 assert np.linalg.norm(force-[sign,0,0])<1e-10
 forces.append(f);loadmeta.append({'name':label,'surface_area_mm2':area,'resultant_N':force.tolist(),'moment_about_origin_Nmm':moment.tolist()})
F=np.stack(forces,axis=1);results=[]
modes=('four_bearing_rings_ideal_clamp',) if a.boundary=='rings' else ('four_bearing_rings_ideal_clamp','entire_bottom_skin_ideal_clamp')
for mode in modes:
 if mode=='four_bearing_rings_ideal_clamp':D=basis.get_dofs(facets=ids['support']).all()
 else:D=np.flatnonzero(coords[2]<=.65000001)
 free=np.setdiff1d(np.arange(basis.N),D);tic=time.monotonic();factor=splu(K[free][:,free],permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True});U=np.zeros_like(F);U[free]=factor.solve(F[free]);print('SOLVED',mode,time.monotonic()-tic,flush=True)
 reaction=K@U-F;residual=float(np.max(np.abs(reaction[free])));matrix=F.T@U;energy=np.sum(U*(K@U),axis=0)/2
 perload=[]
 for i,label in enumerate(labels):
  applied_m=np.array(loadmeta[i]['moment_about_origin_Nmm']);rf=np.array([reaction[k,i].sum() for k in indices]);forces_r=np.zeros((basis.N,3))
  for d,k in enumerate(indices):forces_r[k,d]=reaction[k,i]
  rm=np.cross(coords.T,forces_r).sum(axis=0)
  vec=np.stack([U[k,i] for k in indices],axis=1);peak=float(np.linalg.norm(vec,axis=1).max())
  perload.append({'label':label,'normalized_loaded_surface_compliance_E_delta_per_F_per_mm':float(matrix[i,i]),'maximum_displacement_coefficient_E_mm_per_N':peak,'reaction_force_N':rf.tolist(),'force_balance_norm_N':float(np.linalg.norm(rf+loadmeta[i]['resultant_N'])),'moment_balance_norm_Nmm':float(np.linalg.norm(rm+applied_m)),'work_2energy_relative_error':float(abs(matrix[i,i]-2*energy[i])/max(abs(matrix[i,i]),1e-20))})
 symmetry=float(np.max(np.abs(matrix-matrix.T))/np.max(np.abs(matrix)));eig=np.linalg.eigvalsh(matrix)
 assert residual<1e-6 and symmetry<1e-6 and eig.min()>0,(residual,symmetry,eig)
 assert max(x['force_balance_norm_N'] for x in perload)<1e-5
 assert max(x['moment_balance_norm_Nmm'] for x in perload)<1e-3
 np.savez_compressed(a.output/(mode+'.npz'),dof_xyz=coords,axis0=indices[0],axis1=indices[1],axis2=indices[2],displacements=U,reactions=reaction,forces=F,constrained_dofs=D)
 results.append({'boundary':mode,'constraint_dofs':len(D),'displacement_dofs':basis.N,'residual_free_max_N':residual,'reciprocity_relative_error':symmetry,'compliance_eigenvalues':eig.tolist(),'compliance_matrix_scaled_by_E_per_mm':matrix.tolist(),'load_responses':perload})
 del factor;gc.collect()
 (a.output/'partial.json').write_text(json.dumps({'complete':False,'completed_boundaries':results},indent=2,default=lambda x:x.item() if hasattr(x,'item') else x.tolist())+'\n')
report={'solver_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'complete':True,'mesh_sha256':hashlib.sha256(a.mesh.read_bytes()).hexdigest(),'E_normalization_N_per_mm2':1.,'poisson_ratio_assumption':a.nu,'actual_material_or_force':False,'solution_degree':a.order,'curved_geometry_order':1,'mesh_volume_mm3':float(basis.dx.sum()),'tetrahedra':mesh.nelements,'nodes':mesh.nvertices,'load_cases':loadmeta,'results':results,'no_contact_threads_or_preload_solved':True,'candidate_go':False,'manufacturing_go':False}
(a.output/'report.json').write_text(json.dumps(report,indent=2,default=lambda x:x.item() if hasattr(x,'item') else x.tolist())+'\n');print('REPORT',json.dumps([{r['boundary']:[p['normalized_loaded_surface_compliance_E_delta_per_F_per_mm'] for p in r['load_responses']]} for r in results]),flush=True)
