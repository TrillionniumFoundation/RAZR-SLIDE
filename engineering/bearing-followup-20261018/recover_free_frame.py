"""Recover frame private L2 coefficients for the frozen-load restraint diagnostic.
No bearing/contact solver or candidate selected-element builder is imported.
"""
from pathlib import Path
import sys,hashlib,json
import numpy as np
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
ROOT=Path('/home/qian-qi/RAZR-SLIDE-bearing-orderfix-20261018')
sys.path[:0]=[str(ROOT/'engineering/trace-enrichment-20261017'),str(ROOT/'engineering/volume-convergence-20261017'),str(ROOT/'integration')]
from independent_trace_elements import nodes,REFERENCE
from frozen_load_response import recovered
SOURCE=ROOT/'engineering/installation-control-20261018/install-force/frame'
V=Path('/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3/frame/level-2')
IROOT=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018/current/independent-elements')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/bearing-followup-20261018/frame-release-block')
OUT=O/'private-recovery';OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((O/'report.json').read_text());assert r['passed_frozen_load_linear_diagnostic']
z=np.load(O/'frame-release-field.npz',allow_pickle=False);whole=z['u'];md=np.load(V/'mesh.npz',allow_pickle=False);mesh=MeshTet(md['points'].T,md['tetra'].T)
vec=Basis(mesh,ElementVector(ElementTetP2()));N=vec.N;u=whole[:N];b=whole[N:];assert len(b)==120
inputs={str(p):sha(p) for p in [O/'report.json',O/'frame-release-field.npz',V/'mesh.npz',SOURCE/'local-records.json']}
assert sha(O/'frame-release-field.npz')==r['field_sha256']
records=json.loads((SOURCE/'local-records.json').read_text());energy=0.;worst=0.;chosen=[];rows=[]
for rec in records:
    path=IROOT/f'frame-tet-{rec["tet"]}.npz';data=np.load(path,allow_pickle=False);inputs[str(path)]=sha(path)
    K=data['uncondensed'];face=np.zeros(12)
    for fi,ki in rec['roles']:face[3*fi:3*fi+3]=b[3*ki:3*ki+3]
    size=K.shape[0]-12;keep=np.r_[np.arange(30),np.arange(size,size+12)];private=np.arange(30,size)
    q=np.zeros(K.shape[0]);q[keep]=np.r_[u[rec['retained_dofs']],face];q[private]=-np.linalg.solve(K[np.ix_(private,private)],K[np.ix_(private,keep)]@q[keep])
    residual=float(np.max(abs((K@q)[private])));assert residual<1e-9
    en=float(q@K@q);energy+=en;worst=max(worst,residual);chosen.append(rec['tet']);rows.append({'tet':rec['tet'],'private_residual':residual,'twice_energy':en})
    np.savez_compressed(OUT/f'frame-tet-{rec["tet"]}.npz',private=q[private],reference_nodes=data['reference_nodes'],face_coefficients=face)
vertices=mesh.p.T[mesh.t.T];elem=ElementTetP2();canonical=nodes(REFERENCE);perm=np.array([np.argmin(np.linalg.norm(elem.doflocs-p,axis=1)) for p in canonical]);ids=vec.element_dofs[(3*perm[:,None]+np.arange(3)).ravel()].T
remain=np.array([i for i in range(len(vertices)) if i not in set(chosen)]);array=np.empty((len(remain),75))
for lo in range(0,len(remain),256):
    at=remain[lo:lo+256];values,res,en=recovered(vertices[at],u[ids[at]],2);array[lo:lo+len(at)]=values;worst=max(worst,res);energy+=float(en.sum())
assert worst<1e-9
relative=abs(energy-2*r['released_frame_elastic_energy'])/max(abs(energy),1e-25);assert relative<1e-5
np.savez_compressed(OUT/'frame-unselected.npz',parent_tetrahedra=remain,private_coefficients=array)
assert 'bearing_contact' not in sys.modules and 'rigid_bearing_probe' not in sys.modules and 'contact_dual_active' not in sys.modules
result={'passed':True,'frame_parent_tetrahedra':len(vertices),'selected_parents':len(chosen),'unselected_parents':len(remain),'private_coefficients':75*len(vertices),'maximum_private_residual':worst,'twice_integrated_energy':energy,'relative_to_retained_energy':relative,'input_sha256':inputs,'source_sha256':sha(__file__),'selected_element_checks':rows,'files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.glob('*.npz'))],'frozen_old_member_loads_not_recoupled_contact':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for p,h in inputs.items():assert sha(p)==h
(OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n');print('FREE_FRAME_PRIVATE_RECOVERY_PASSED',len(vertices),75*len(vertices),worst,relative,flush=True)
