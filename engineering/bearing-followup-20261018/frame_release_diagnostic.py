"""Frozen-load frame-restraint sensitivity, NOT a re-equilibrated contact model.

Retain the exact PR34 member load and elastic energy, remove the 777 physical
frame-face constraints, and choose six numerical rigid-motion coordinates.
No material, pressure, contact force or geometric data are changed or fitted.
"""
from pathlib import Path
import datetime, hashlib, json, time
import numpy as np
from scipy.sparse import load_npz, bmat, csc_matrix
from scipy.sparse.linalg import splu
from scipy.linalg import qr
ROOT=Path('/home/qian-qi/RAZR-SLIDE-bearing-orderfix-20261018')
SOURCE=ROOT/'engineering/installation-control-20261018/install-force'
VOLUME=Path('/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3/frame/level-2')
OUT=Path('/home/qian-qi/.local/share/razr-slide-evidence/bearing-followup-20261018/frame-release')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
OUT.mkdir(exist_ok=False)
paths=[SOURCE/'full-fields.npz',SOURCE/'report.json',SOURCE/'independent-report.json',SOURCE/'frame/coupling.npz',SOURCE/'frame/local-blocks.npz',VOLUME/'K.npz',VOLUME/'loads.npz',VOLUME/'mesh.npz',VOLUME/'report.json']
identity={str(p):sha(p) for p in paths}
r=json.loads((SOURCE/'report.json').read_text());ir=json.loads((SOURCE/'independent-report.json').read_text());vr=json.loads((VOLUME/'report.json').read_text())
assert r['passed'] and ir['passed'] and r['external_load_scale_over_Epanel_mm2']==0
for f,k in [('K.npz','K_sha256'),('loads.npz','loads_sha256'),('mesh.npz','mesh_sha256')]:assert sha(VOLUME/f)==vr[k]
for f in ['report.json','full-fields.npz']:
    wanted=[v for p,v in ir['input_sha256'].items() if p.endswith('/install-force/'+f)]
    assert len(wanted)==1 and wanted[0]==sha(SOURCE/f)
z=dict(np.load(SOURCE/'full-fields.npz',allow_pickle=False));L=dict(np.load(VOLUME/'loads.npz',allow_pickle=False))
N=len(z['uf']);nb=len(z['bf']);off=len(z['up'])+len(z['bp'])
u0=np.r_[z['uf'],z['bf']];force=z['load'][off:].copy();assert len(force)==N+nb
K=load_npz(VOLUME/'K.npz');A=load_npz(SOURCE/'frame/coupling.npz');B=np.load(SOURCE/'frame/local-blocks.npz',allow_pickle=False)['B']
M=bmat([[K,A],[A.T,csc_matrix(B)]],format='csc');del K,A,B
assert M.shape==(N+nb,N+nb);sym=M-M.T
assert np.max(abs(sym.data),initial=0.)<1e-8;del sym
axes=[L['axis0'],L['axis1'],L['axis2']];xyz=L['xyz'][:,axes[0]].T
assert all(np.array_equal(L['xyz'][:,ax].T,xyz) for ax in axes)
center=(xyz.max(axis=0)+xyz.min(axis=0))/2;length=float(np.linalg.norm(xyz.max(axis=0)-xyz.min(axis=0)));relative=(xyz-center)/length
R=np.zeros((N+nb,6))
for axis,ids in enumerate(axes):
    R[ids,axis]=1
    for rot in range(3):
        w=np.eye(3)[rot];R[ids,3+rot]=np.cross(np.broadcast_to(w,relative.shape),relative)[:,axis]
null_error=float(np.max(abs(M@R)));assert null_error<1e-7,('matrix contains non-rigid supports',null_error)
load_modes=R.T@force;assert np.max(abs(load_modes))<1e-10
# Rank-revealing selection only fixes rigid coordinates, not physical supports.
_,_,piv=qr(R[:N].T,mode='economic',pivoting=True,check_finite=False);gauges=np.asarray(piv[:6]);assert np.linalg.matrix_rank(R[gauges])==6
free=np.setdiff1d(np.arange(N+nb),gauges)
oldD=L['D'];oldfree=np.setdiff1d(np.arange(N+nb),oldD)
oldres=M@u0-force;assert np.max(abs(oldres[oldfree]))<1e-9
oldenergy=float(.5*u0@(M@u0));assert abs(2*oldenergy-ir['full_checks']['frame']['twice_strain_energy'])<1e-14
start=time.monotonic();print('FACTOR_FRAME_FREE',len(free),'OLD_CONSTRAINTS',len(oldD),flush=True)
factor=splu(M[free][:,free].tocsc(),permc_spec='MMD_AT_PLUS_A')
u=np.zeros(N+nb);u[free]=factor.solve(force[free]);seconds=time.monotonic()-start
residual=M@u-force;free_error=float(np.max(abs(residual[free])));gauge_reaction=float(np.max(abs(residual[gauges])))
assert free_error<1e-9 and gauge_reaction<1e-9
energy=float(.5*u@(M@u));work=float(.5*u@force);energy_error=abs(energy-work)/max(abs(energy),abs(work),1e-25);assert energy_error<1e-5
# Express exactly the same field under a second complete coordinate gauge.
reverse=np.arange(N-1,-1,-1);_,_,otherpiv=qr(R[reverse].T,mode='economic',pivoting=True,check_finite=False);other=reverse[otherpiv[:6]]
alpha=np.linalg.solve(R[other],-u[other]);alternative=u+R@alpha;alt_res=float(np.max(abs(M@alternative-force)))
assert alt_res<1e-9
work_invariance=abs(float(force@(alternative-u)));assert work_invariance<1e-12
# Meaningful motion comparison removes arbitrary global translation/rotation.
align=np.linalg.lstsq(R[:N],(u-u0)[:N],rcond=None)[0];difference=u-u0-R@align
np.savez_compressed(OUT/'frame-release-field.npz',u=u,force=force,original=u0,gauges=gauges,alternate_gauges=other,align_rigid=align)
result={'passed_frozen_load_linear_diagnostic':True,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source':'PR34 force-controlled unloaded installation; old member tractions held fixed',
 'original_physical_fixed_dofs':len(oldD),'new_physical_fixed_dofs':0,'numerical_gauge_dofs':gauges.tolist(),'gauge_mode_rank':6,
 'full_selected_frame_dofs':N+nb,'matrix_rigid_null_max':null_error,'force_rigid_mode_resultants':load_modes.tolist(),
 'free_node_residual_max':free_error,'gauge_reaction_max':gauge_reaction,'energy_work_relative':energy_error,
 'old_frame_elastic_energy':oldenergy,'released_frame_elastic_energy':energy,'energy_relative_change':energy/oldenergy-1,
 'original_fixture_reaction_L1':float(np.sum(abs(oldres[oldD]))),'original_fixture_reaction_max':float(np.max(abs(oldres[oldD]))),
 'rigid_removed_member_displacement_max_mm':float(np.max(abs(difference[:N]))),'trace_difference_max_mm':float(np.max(abs(difference[N:]))),
 'second_gauge_is_reexpression_not_second_factorization':True,'second_gauge_residual':alt_res,'rigid_work_change':work_invariance,
 'factor_and_solve_seconds':seconds,'input_sha256':identity,'source_sha256':sha(__file__),'field_sha256':sha(OUT/'frame-release-field.npz'),
 'contact_and_bolt_forces_not_re_equilibrated':True,'released_frame_fields_not_passed_contact_solution':True,
 'no_actual_restraint_material_or_service_load_assigned':True,'not_head_nut_compliance_or_capacity':True,
 'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for p,h in identity.items():assert sha(p)==h
assert energy>=oldenergy-1e-12
print('FRAME_RELEASE_DIAGNOSTIC_DONE',json.dumps({k:v for k,v in result.items() if k not in ['input_sha256']}),flush=True)
dump(OUT/'report.json',result)
