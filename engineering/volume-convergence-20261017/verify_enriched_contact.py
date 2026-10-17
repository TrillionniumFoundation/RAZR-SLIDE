"""Independent reconstruction of point forces and original-mesh gap extrema.

No primal or dual contact solver is imported. Point-force maps use tetrahedral
P2 library interpolation, not the candidate's surface coefficient evaluator.
Full K, action/reaction, numerical gauges, energies, point complementarity and
all supplied common cells are checked. This is not mesh/stress convergence.
"""
from pathlib import Path
import argparse,gzip,json,hashlib,sys
import numpy as np
from scipy.sparse import load_npz
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
ROOT=Path(__file__).resolve().parents[2]
BASE=Path('/tmp/razr-preload-contact-20261016')
OLD=Path('/tmp/razr-support-coupling-20261015')
sys.path.insert(0,str(ROOT/'integration'))
from contact_patch_audit import triangle_coefficients,extrema
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--volume',type=Path,required=True);parser.add_argument('--level',type=int,choices=[1,2],required=True);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
assert not a.output.exists();r=json.loads((a.run/'report.json').read_text());fields=np.load(a.run/'full-fields.npz',allow_pickle=False)
inputs={str(a.run/'report.json'):sha(a.run/'report.json'),str(a.run/'full-fields.npz'):sha(a.run/'full-fields.npz')}
for path,want in r['input_sha256'].items():
 assert sha(path)==want,(path,'changed source');inputs[path]=want
raw=json.loads(gzip.decompress((ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz').read_bytes()))
meta=json.loads(gzip.decompress((ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz').read_bytes()))['contact_patches']
flat=[(m,c) for m,g in zip(meta,raw) for c in g['cells']];assert len(flat)==5255
models={}
for name in ('panel','frame'):
 path=a.volume/name/f'level-{a.level}'/'mesh.npz';d=np.load(path,allow_pickle=False);m=MeshTet(d['points'].T,d['tetra'].T)
 bs=Basis(m,ElementTetP2(),intorder=2);bv=Basis(m,ElementVector(ElementTetP2()),intorder=2);axes=bv.split_indices()
 assert np.array_equal(bs.doflocs,bv.doflocs[:,axes[0]])
 face={tuple(sorted(tri)):i for i,tri in enumerate(m.facets.T)}
 loads=np.load(a.volume/name/f'level-{a.level}'/'loads.npz',allow_pickle=False)
 u=fields['up' if name=='panel' else 'uf'];assert len(u)==bv.N
 models[name]={'mesh':m,'bs':bs,'bv':bv,'axes':axes,'face':face,'u':u,'loads':loads}

def point_map(name,triangle,point,axis):
 m=models[name];mesh=m['mesh'];cell=int(mesh.f2t[0,m['face'][tuple(sorted(triangle))]])
 tet=mesh.p[:,mesh.t[:,cell]];x=np.linalg.solve(tet[:,1:]-tet[:,0,None],np.array(point)-tet[:,0]);bary=np.r_[1-x.sum(),x]
 if min(bary)<-1e-8 or max(bary)>1+1e-8:raise ValueError('reaction or witness outside original tetrahedron')
 shape=np.array([m['bs'].elem.lbasis(x[:,None],i)[0][0] for i in range(10)])
 assert abs(shape.sum()-1)<1e-12
 return m['axes'][axis][m['bs'].element_dofs[:,cell]],shape
lam=np.array(r['forces']);pts=r['contact_points'];assert len(lam)==len(pts)
assert lam[:4].min()>=-1e-10 and lam[4:].min()>=-1e-12
expected={name:-m['loads']['C']@lam[:4] for name,m in models.items()}
expected['panel']+=models['panel']['loads']['F'][:,r['load_index']]*r['force_over_Epanel_mm2']
contact_gaps=[]
for i,p in enumerate(pts[4:],4):
 mm,cell=flat[p['cell']];assert p['patch']==mm['patch'];axis=mm['normal_axis'];tan=[k for k in range(3) if k!=axis];n=mm['normal_sign'];relative=0.
 for name,m in models.items():
  xyz=np.zeros(3);xyz[tan]=p['xy'];xyz[axis]=1.2 if axis==2 else n*(36.325 if name=='panel' else 36.345)
  idx,w=point_map(name,cell[name+'_triangle'],xyz,axis);w=w*n*(1 if name=='panel' else -1)
  np.add.at(expected[name],idx,-lam[i]*w);relative+=w@m['u'][idx]
 contact_gaps.append(mm['initial_gap_mm']-relative)
contact_gaps=np.array(contact_gaps);comp=float(np.max(abs(lam[4:]*contact_gaps)))
assert contact_gaps.min()>-1e-7 and comp<1e-11
forceaudits={};balances=[]
for name,m in models.items():
 given=fields['load_'+name];err=float(np.max(abs(given-expected[name])));assert err<1e-12
 K=load_npz(a.volume/name/f'level-{a.level}'/'K.npz');u=m['u'];D=m['loads']['D'];res=K@u-expected[name];free=np.setdiff1d(np.arange(len(u)),D)
 fre=float(np.max(abs(res[free])));reaction=float(np.max(abs(res[D])));assert fre<1e-9
 if name=='panel':assert reaction<1e-9
 e=float(.5*u@(K@u));w=float(.5*u@expected[name]);energyerr=abs(e-w)/max(abs(e),abs(w),1e-20);assert energyerr<1e-5
 ext=expected[name].copy()
 if name=='frame':ext[D]+=res[D]
 nodal=np.stack([ext[idx] for idx in m['axes']],axis=1);xyz=m['bv'].doflocs[:,m['axes'][0]].T
 balances.append(np.r_[nodal.sum(axis=0),np.cross(xyz,nodal).sum(axis=0)])
 forceaudits[name]={'independent_tetra_load_error_max':err,'fresh_K_free_residual_max':fre,'gauge_or_fixture_reaction_max':reaction,'energy_work_relative_error':energyerr}
 del K
balance=np.sum(balances,axis=0);assert np.max(abs(balance))<1e-8
qbolt=sum(m['loads']['C'].T@m['u'] for m in models.values())
assert np.max(abs(lam[:4]-r['spring_initial_over_Epanel_mm2']-qbolt/5.))<1e-10
patches=[];worst=1.;count=0
for mm,g in zip(meta,raw):
 n=mm['normal_sign'];axis=mm['normal_axis'];tan=[k for k in range(3) if k!=axis];origin=mm['origin_tangent_mm'];best=None;hi=-np.inf
 for cell in g['cells']:
  poly={}
  for name,m in models.items():
   xy=m['mesh'].p.T[cell[name+'_triangle']][:,tan]
   poly[name]=triangle_coefficients(xy,m['u'][cell[name+'_P2_dofs']],origin)
  coeff=-n*(poly['panel']-poly['frame']);coeff[0]+=mm['initial_gap_mm'];e=extrema(coeff,cell['polygon'],origin);count+=1
  if best is None or e['minimum']<best[0]:best=(e['minimum'],e['minimum_at'],cell)
  hi=max(hi,e['maximum'])
 lo,point,cell=best;worst=min(worst,lo);direct=mm['initial_gap_mm']
 for name,m in models.items():
  xyz=np.zeros(3);xyz[tan]=point;xyz[axis]=1.2 if axis==2 else n*(36.325 if name=='panel' else 36.345)
  idx,shape=point_map(name,cell[name+'_triangle'],xyz,axis)
  direct-=n*(1 if name=='panel' else -1)*float(shape@m['u'][idx])
 assert abs(direct-lo)<1e-10
 patches.append({'patch':mm['patch'],'minimum_gap_mm':lo,'maximum_gap_mm':hi,'minimum_at':point,'independent_tetra_gap_mm':direct,'witness_difference_mm':abs(direct-lo),'nonpenetration':lo>=-1e-7})
print('INDEPENDENT_CASE',r['case'],'ALL_CELLS',count,'WORST',worst,'POINTS',len(contact_gaps),'REACTION_MIN',lam[4:].min(),flush=True)
assert count==5255
for f,h in inputs.items():assert sha(f)==h
assert 'contact_dual_active' not in sys.modules and 'spatial_contact' not in sys.modules
# Recover every added interior DOF and integrate actual finest-element strains.
# This does not reuse the candidate contact force mapping or its gap extrema.
from frozen_load_response import recovered
from tetra_bubble_refinement import p2_nodes,REF
internal_audits={}
ref=ElementTetP2().doflocs;perm=np.array([np.argmin(np.linalg.norm(ref-x,axis=1)) for x in p2_nodes(REF)])
for name,m in models.items():
 vertices=m['mesh'].p.T[m['mesh'].t.T];ids=m['bv'].element_dofs[(3*perm[:,None]+np.arange(3)).ravel()].T
 extra=np.empty((len(ids),15*((4**a.level-1)//3)));maximum=0.;strain=0.
 for lo in range(0,len(ids),256):
  hi=min(lo+256,len(ids));values,res,en=recovered(vertices[lo:hi],m['u'][ids[lo:hi]],a.level);extra[lo:hi]=values;maximum=max(maximum,res);strain+=float(en.sum())
 work=float(m['u']@expected[name]);relative=abs(strain-work)/max(abs(work),1e-20)
 assert maximum<1e-9 and relative<1e-5
 target=a.output.parent/('recovered-'+name+'-internal.npz');assert not target.exists()
 np.savez_compressed(target,internal_displacement=extra)
 internal_audits[name]={'added_displacement_DOFs':int(extra.size),'full_uncondensed_DOFs':int(len(m['u'])+extra.size),'maximum_internal_residual':maximum,'integrated_finest_twice_strain_energy':strain,'external_work':work,'relative_energy_error':relative,'internal_field_sha256':sha(target)}
out={'case':r['case'],'audit_completed':True,'discrete_solution_passed':bool(worst>=-1e-7),'original_common_cells':count,'minimum_gap_mm':worst,'independent_tetra_witnesses':len(patches),'contact_force_count':len(contact_gaps),'minimum_reaction':float(lam[4:].min()),'minimum_enforced_point_gap_mm':float(contact_gaps.min()),'complementarity_max':comp,'full_field_checks':forceaudits,'net_force_moment':balance.tolist(),'patches':patches,'input_sha256':inputs,'verifier_sha256':sha(__file__),'solver_imported':False,'same_original_trace_mesh':True,'nested_volume_level':a.level,'interior_recovery':internal_audits,'mesh_convergence_certified':False,'point_forces_not_area_pressure':True,'gap_tolerance_mm':1e-7,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
raise SystemExit(0 if out['discrete_solution_passed'] else 1)
