"""Fresh elasticity assembly applied to reconstructed coupled full fields.

No new linear-system solve, pinning, regularization, input force or geometry.
Independent of the archived residual matrix and reduced observation matrix.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from skfem import MeshTet,Basis,ElementVector,ElementTetP2,asm
from skfem.models.elasticity import linear_elasticity,lame_parameters
p=argparse.ArgumentParser();p.add_argument('--body',choices=('panel','frame'),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
ROOT=Path('/tmp/razr-support-coupling-20261015');OUT=Path('/tmp/razr-contact-field-20261015/audit-v1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
mf=ROOT/('input/mesh.npz' if a.body=='panel' else 'frame-mesh3/mesh.npz');cf=OUT/(a.body+'-coupled.npz');rf=ROOT/(a.body+'-final3/report.json');ref=json.loads(rf.read_text());assert sha(mf)==ref['mesh_sha256']
d=np.load(mf,allow_pickle=False);s=np.load(cf,allow_pickle=False);mesh=MeshTet(d['points'].T,d['tetra'].T);b=Basis(mesh,ElementVector(ElementTetP2()),intorder=4);assert b.N==ref['dofs']
L,mu=lame_parameters(1.,.3);tic=time.monotonic();K=asm(linear_elasticity(L,mu),b).tocsr();print('ASSEMBLED',a.body,b.N,K.nnz,round(time.monotonic()-tic,2),flush=True)
U=s['displacement'];F=s['load'];D=s['D'];free=np.setdiff1d(np.arange(b.N),D);KU=K@U;R=KU-F;axes=b.split_indices();xyz=b.doflocs[:,axes[0]].T
rows=[]
for j in range(U.shape[1]):
 residual=float(np.max(abs(R[free,j])));gauge=float(np.max(abs(R[D,j])))
 nodal=np.stack([R[k,j]+F[k,j] for k in axes],axis=1);balance=np.r_[nodal.sum(axis=0),np.cross(xyz,nodal).sum(axis=0)]
 energy=.5*U[:,j]@KU[:,j];work=.5*U[:,j]@F[:,j];error=abs(energy-work)/max(abs(energy),abs(work),1e-30)
 assert residual<1e-9 and error<1e-7 and np.max(abs(balance))<1e-8
 if a.body=='panel':assert gauge<1e-9
 else:assert np.max(abs(U[D,j]))<1e-15
 rows.append({'case':j,'fresh_free_residual_max':residual,'gauge_or_actual_fixture_reaction_max':gauge,'fresh_vs_saved_residual_max':float(np.max(abs(R[:,j]-s['saved_residual'][:,j]))),'strain_energy':float(energy),'external_work_over2':float(work),'relative_work_energy_error':float(error),'global_force_moment_balance':balance.tolist()})
 print('FRESH_CASE',j,'FREE',residual,'SUPPORT',gauge,'WORK_ERROR',error,flush=True)
report={'body':a.body,'mesh_sha256':sha(mf),'reconstructed_fields_sha256':sha(cf),'source_sha256':sha(__file__),'rows':rows,'fresh_K_assembly':True,'same_P2_linear_geometry_not_new_mesh':True,'passed':True,'panel_gauges_not_physical_anchors':a.body=='panel','frame_boundary_is_still_ideal_far_face':a.body=='frame','actual_load_or_material_assigned':False,'candidate_go':False,'manufacturing_go':False}
with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print('AUDIT_COMPLETE',a.body,flush=True)
