"""Complete-body quadratic elasticity reduced to explicitly assumed pressure ports.

Panel pin gauges remove only rigid modes. They are not physical anchors: their
final reactions must vanish after coupling. Frame has an explicit remote end
fixture at Y=94.25. Surface pressure shapes are prescribed, not solved local
contact pressure; nonnegative pressure and matched first moments are checked.
"""
from pathlib import Path
import argparse,json,hashlib,time,gc
import numpy as np
from scipy.sparse.linalg import splu
from skfem import MeshTet,Basis,FacetBasis,ElementVector,ElementTetP2,LinearForm,asm
from skfem.models.elasticity import linear_elasticity,lame_parameters

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else x.tolist())+'\n')
p=argparse.ArgumentParser();p.add_argument('--mesh',type=Path,required=True);p.add_argument('--body',choices=('panel','frame'),required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--targets',type=Path);p.add_argument('--ports-only',action='store_true');a=p.parse_args();a.output.mkdir(exist_ok=False)
data=np.load(a.mesh,allow_pickle=False);mesh=MeshTet(data['points'].T,data['tetra'].T);elem=ElementVector(ElementTetP2());basis=Basis(mesh,elem,intorder=4);axes=basis.split_indices();xyz=basis.doflocs
bf=mesh.boundary_facets();tri=mesh.p[:,mesh.facets[:,bf]];boundslo=tri.min(axis=1);boundshi=tri.max(axis=1)
refs=json.loads(a.targets.read_text()) if a.targets else {}
ports=[];columns=[];targets={}
def patch(name,axis,plane,selector,direction,target):
 ids=bf[(abs(boundslo[axis]-plane)<1e-7)&(abs(boundshi[axis]-plane)<1e-7)]
 if not len(ids):raise ValueError('missing planar surface '+name)
 fb=FacetBasis(mesh,elem,facets=ids,intorder=6);q=np.asarray(fb.global_coordinates());mask=selector(q);area=float(np.sum(fb.dx*mask))
 if area<=1e-8:raise ValueError('empty pressure port '+name)
 center=np.sum(q*(fb.dx*mask)[None,:,:],axis=(1,2))/area
 if target is None:target=center
 target=np.array(target,dtype=float);target[axis]=plane;tan=[x for x in range(3) if x!=axis]
 V=np.stack([np.ones_like(fb.dx),q[tan[0]]-target[tan[0]],q[tan[1]]-target[tan[1]]])
 gram=np.einsum('aij,bij,ij->ab',V,V,fb.dx*mask);coeff=np.linalg.solve(gram,np.array([1.,0.,0.]));density=np.einsum('a,aij->ij',coeff,V)*mask
 if np.min(density)<-1e-10:raise ValueError('chosen port pressure becomes tensile: '+name+' '+str(np.min(density)))
 @LinearForm
 def traction(v,w):return sum(direction[i]*v[i] for i in range(3))*density
 f=asm(traction,fb);resultant=np.array([sum(f[ix]) for ix in axes]);nodal=np.zeros((basis.N,3))
 for i,ix in enumerate(axes):nodal[ix,i]=f[ix]
 moment=np.cross(xyz.T,nodal).sum(axis=0);expected=np.cross(target,np.array(direction))
 if np.linalg.norm(resultant-direction)>1e-8 or np.linalg.norm(moment-expected)>1e-6:raise ValueError('load resultant/first moment mismatch '+name)
 ports.append({'name':name,'normal':direction,'plane':float(plane),'clipped_quadrature_area_mm2':area,'uncorrected_centroid_mm':center.tolist(),'resultant_center_mm':target.tolist(),'pressure_affine_coefficients':coeff.tolist(),'minimum_quadrature_pressure_per_unit':float(density.min()),'nodal_resultant':resultant.tolist(),'nodal_moment':moment.tolist(),'pressure_is_prescribed_not_contact_solution':True})
 targets[name]=target.tolist();columns.append(f);print('PORT',a.body,name,'area',area,'center',target.tolist(),flush=True)
centers=[(-34.8,50.),(34.8,50.),(-34.8,70.),(34.8,70.)]
# Four bolt force pairs, four compression-pad pairs, four selected shear patches.
for i,(x,y) in enumerate(centers):
 z=.55 if a.body=='panel' else 2.55;r=.9 if a.body=='panel' else 1.7
 def inside(q,x=x,y=y,r=r):
  if a.body=='panel':return (q[0]-x)**2+(q[1]-y)**2<=r*r+1e-10
  return np.logical_and.reduce([abs(np.cos(t)*(q[0]-x)+np.sin(t)*(q[1]-y))<=1.25+1e-10 for t in np.arange(6)*np.pi/3+np.pi/6])
 patch('bolt'+str(i),2,z,inside,[0,0,-1 if a.body=='panel' else 1],[x,y,z])
for i,(x,y) in enumerate(centers):
 def inside(q,x=x,y=y):return (q[0]-x)**2+(q[1]-y)**2<=1.8**2+1e-10
 patch('pad'+str(i),2,1.2,inside,[0,0,1 if a.body=='panel' else -1],[x,y,1.2])
for side,sign in [('L',-1),('R',1)]:
 for segment,y0,y1 in [('front',16.5,20.5),('rear',22.5,24.)]:
  name='key_'+side+'_'+segment;plane=sign*(36.325 if a.body=='panel' else 36.345)
  def inside(q,y0=y0,y1=y1):return (q[1]>=y0-1e-9)&(q[1]<=y1+1e-9)&(q[2]>=.65-1e-9)&(q[2]<=2.+1e-9)
  target=None if a.body=='panel' else refs[name]
  patch(name,0,plane,inside,[sign if a.body=='panel' else -sign,0,0],target)
C=np.stack(columns,axis=1);nports=len(columns)
if a.body=='panel':
 for side,sign in [('L',-1),('R',1)]:
  for segment,y0,y1 in [('front',18.30,19.50),('rear',22.35,23.80)]:
   def inside(q,y0=y0,y1=y1):return (q[1]>=y0-1e-9)&(q[1]<=y1+1e-9)&(q[2]>.64)
   patch('load_'+side+'_'+segment,0,sign*17.43,inside,[sign,0,0],None)
F=np.stack(columns[nports:],axis=1) if len(columns)>nports else np.zeros((basis.N,0))
dump(a.output/'ports.json',ports);dump(a.output/'targets.json',targets)
if a.ports_only:raise SystemExit(0)
# Six rigid modes for a free panel. Rotations are scaled by100mm to reduce conditioning.
R=np.zeros((basis.N,6));origin=np.array([0.,47.125,0.]);length=100.
for d,ix in enumerate(axes):
 R[ix,d]=1.
 for j in range(3):R[ix,3+j]=np.cross(np.eye(3)[j],(xyz[:,ix].T-origin)/length)[:,d]
if a.body=='panel':
 desired=[[-36.995,0,0],[36.995,0,0],[-36.995,94.25,0]];nodes=[int(np.argmin(np.linalg.norm(mesh.p.T-np.array(v),axis=1))) for v in desired]
 D=np.array([*basis.nodal_dofs[:,nodes[0]],*basis.nodal_dofs[[1,2],nodes[1]],basis.nodal_dofs[2,nodes[2]]],dtype=int)
 if np.linalg.matrix_rank(R[D])!=6:raise ValueError('pin gauges do not span rigid modes')
else:
 ids=bf[(abs(boundslo[1]-94.25)<1e-7)&(abs(boundshi[1]-94.25)<1e-7)];D=basis.get_dofs(facets=ids).all();assert len(D)>6
L,mu=lame_parameters(1.,.3);tic=time.monotonic();K=asm(linear_elasticity(L,mu),basis).tocsc();print('ASSEMBLE',a.body,basis.N,K.nnz,time.monotonic()-tic,flush=True)
free=np.setdiff1d(np.arange(basis.N),D);B=np.column_stack([C,F]);tic=time.monotonic();factor=splu(K[free][:,free],permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True});print('FACTOR',a.body,time.monotonic()-tic,flush=True)
U=np.zeros_like(B)
for j in range(B.shape[1]):U[free,j]=factor.solve(B[free,j])
del factor;gc.collect();KU=K@U;reaction=KU-B;residual=float(np.max(abs(reaction[free])));H=C.T@U[:,:nports];sym=float(np.max(abs(H-H.T))/max(np.max(abs(H)),1e-20))
if residual>2e-5 or sym>1e-6:raise ValueError(('reduction residual',residual,sym))
np.savez_compressed(a.output/'fields.npz',dof_xyz=xyz,axis0=axes[0],axis1=axes[1],axis2=axes[2],D=D,port_forces=C,external_forces=F,solutions=U,reactions=reaction,rigid_modes=R)
np.savez_compressed(a.output/'reduced.npz',H=(H+H.T)/2,q0=C.T@U[:,nports:],G=C.T@R,external_rigid_resultants=R.T@F,external_compliance=F.T@U[:,nports:],observation_port_response=F.T@U[:,:nports],observation_rigid=F.T@R)
report={'body':a.body,'solver_sha256':sha(__file__),'mesh_sha256':sha(a.mesh),'dofs':basis.N,'tetrahedra':mesh.nelements,'quadratic_displacement_linear_geometry':True,'E_normalization':1.,'nu_assumption':.3,'ports':ports,'free_residual_max':residual,'reciprocity_relative_error':sym,'gauge_or_fixture_dofs':len(D),'boundary':'six numerical pin gauges, final reactions must vanish' if a.body=='panel' else 'whole remote Y94.25 end face ideally held, not actual hand fixture','fields_sha256':sha(a.output/'fields.npz'),'reduced_sha256':sha(a.output/'reduced.npz'),'candidate_go':False,'manufacturing_go':False}
dump(a.output/'report.json',report);print('REDUCED_COMPLETE',a.body,residual,sym,flush=True)
