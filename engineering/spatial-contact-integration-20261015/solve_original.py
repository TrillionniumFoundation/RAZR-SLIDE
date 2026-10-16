"""Original two-body sparse elastic-response contact exchange.

Uses all original volume DOFs. Point responses are solved with each complete
K, never an old twelve-port contact pressure ansatz. Contact forces optimize
complementary energy with explicit rigid equilibrium. Four bolt pressure
shapes and the remote frame fixture remain stated inherited assumptions.
"""
from pathlib import Path
import argparse,json,gzip,hashlib,sys,time,gc
import numpy as np
from scipy.sparse import load_npz
from scipy.sparse.linalg import splu

ROOT=Path('/home/qian-qi/RAZR-SLIDE-spatial-integration-20261015')
BASE=Path('/tmp/razr-spatial-integration-20261015')
sys.path.insert(0,str(ROOT/'integration'))
from contact_patch_audit import triangle_coefficients,evaluate,extrema
from contact_dual_active import solve_force_qp
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else x.tolist())+'\n')
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cases',type=int,nargs='+',default=[0]);parser.add_argument('--max-exchanges',type=int,default=100);parser.add_argument('--max-points',type=int,default=1200);parser.add_argument('--batch-per-patch',type=int,default=3)
a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
inputs={};bodies={}
for name in ('panel','frame'):
 folder=BASE/'elastic'/name;r=json.loads((folder/'report.json').read_text())
 for f,k in [('K.npz','K_sha256'),('loads.npz','loads_sha256')]:
  path=folder/f;assert sha(path)==r[k];inputs[str(path)]=sha(path)
 data=np.load(folder/'loads.npz',allow_pickle=False);K=load_npz(folder/'K.npz').tocsc();D=data['D'];free=np.setdiff1d(np.arange(K.shape[0]),D)
 t=time.monotonic();factor=splu(K[free][:,free],permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True});print('FACTOR',name,K.shape,time.monotonic()-t,flush=True)
 def response(v,factor=factor,free=free,N=K.shape[0]):
  ans=np.zeros(N);ans[free]=factor.solve(v[free]);return ans
 bodies[name]={'K':K,'D':D,'free':free,'data':{k:data[k] for k in data.files},'solve':response,'U':[],'C':[],'factor':factor}
P=bodies['panel'];F=bodies['frame'];Np=P['K'].shape[0];Nf=F['K'].shape[0]
# Original physical input hashes and precise FE connection coordinates are immutable.
for n,h in {'assembly_inputs.json':'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b','roof_joint_load_inputs.json':'09f7b392b00a59ca1fdb5fa97ad10e6b4d5361ae0f440afb8dd4e9ee225a2640','frame_thread_actual_inputs.json':'4dcb50162bd25a7507a3afb4ba7e0f7aa33b8c233c0a366e68b8adec51a13609'}.items():
 path=ROOT/'integration'/n;assert sha(path)==h;inputs[str(path)]=h
cellpath=ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz';raw=json.loads(gzip.decompress(cellpath.read_bytes()));inputs[str(cellpath)]=sha(cellpath)
old=json.loads(gzip.decompress((ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz').read_bytes()));patchmeta={p['patch']:p for p in old['contact_patches']}
cells=[];patch_indices={}
for group in raw:
 label=group['patch'];meta=patchmeta[label];origin=np.array(meta['origin_tangent_mm']);normal=meta['normal_sign'];axis=meta['normal_axis'];tan=[i for i in range(3) if i!=axis]
 patch_indices[label]=[]
 for c in group['cells']:
  dp=np.array(c['panel_P2_dofs']);df=np.array(c['frame_P2_dofs']);xyP=P['data']['xyz'][tan][:,dp[:3]].T;xyF=F['data']['xyz'][tan][:,df[:3]].T
  tp=triangle_coefficients(xyP,np.eye(6),origin);tf=triangle_coefficients(xyF,np.eye(6),origin)
  cells.append({'label':label,'vertices':np.array(c['polygon']),'origin':origin,'dp':dp,'df':df,'tp':tp,'tf':tf,'normal':normal,'gap':meta['initial_gap_mm'],'axis':axis})
  patch_indices[label].append(len(cells)-1)
assert len(cells)==5255
TP=np.stack([c['tp'] for c in cells]);TF=np.stack([c['tf'] for c in cells]);DP=np.stack([c['dp'] for c in cells]);DF=np.stack([c['df'] for c in cells]);normal=np.array([c['normal'] for c in cells]);gap0=np.array([c['gap'] for c in cells])
print('CELLS',len(cells),'DOFS',Np,Nf,flush=True)
Uext=np.stack([P['solve'](P['data']['F'][:,i]) for i in range(4)],axis=1)
loadG=P['data']['R'].T@P['data']['F'];M=a.max_points+4
H=np.zeros((M,M));G=np.zeros((M,6));qfree=np.zeros((M,4));initialgap=np.zeros(M);points=[];seen={name:[] for name in patch_indices}
def dotcol(col,v):idx,w=col;return w@v[idx]
def add_column(cp,cf,meta):
 i=len(points);assert i<M
 up=P['solve'](np.bincount(cp[0],weights=cp[1],minlength=Np));uf=F['solve'](np.bincount(cf[0],weights=cf[1],minlength=Nf))
 for j in range(i):
  h1=dotcol(P['C'][j],up)+dotcol(F['C'][j],uf);h2=dotcol(cp,P['U'][j])+dotcol(cf,F['U'][j])
  if abs(h1-h2)>2e-7*max(abs(h1),abs(h2),1.):raise ValueError('nonreciprocal new point response')
  H[i,j]=H[j,i]=(h1+h2)/2
 H[i,i]=dotcol(cp,up)+dotcol(cf,uf)
 G[i]=cp[1]@P['data']['R'][cp[0]];gf=cf[1]@F['data']['R'][cf[0]]
 if np.max(abs(G[i]+gf))>2e-8:raise ValueError('point-pair action/reaction moment mismatch')
 qfree[i]=cp[1]@Uext[cp[0]];initialgap[i]=meta.get('gap',0.)
 for body,col,u in ((P,cp,up),(F,cf,uf)):body['C'].append(col);body['U'].append(u)
 points.append(meta)
for i in range(4):
 cp=P['data']['C'][:,i];cf=F['data']['C'][:,i];ip=np.flatnonzero(cp);iff=np.flatnonzero(cf);add_column((ip,cp[ip]),(iff,cf[iff]),{'kind':'bolt','index':i})
def add_point(ci,xy,reason):
 c=cells[ci];xy=np.asarray(xy,float)
 if any(np.linalg.norm(xy-old)<1e-9 for old in seen[c['label']]):return False
 wP=evaluate(c['tp'],xy[None,:],c['origin'])[0]*c['normal'];wF=-evaluate(c['tf'],xy[None,:],c['origin'])[0]*c['normal']
 if abs(wP.sum()-c['normal'])>2e-9 or abs(wF.sum()+c['normal'])>2e-9:raise ValueError('invalid P2 point load partition')
 add_column((c['dp'],wP),(c['df'],wF),{'kind':'contact','patch':c['label'],'cell':ci,'xy':xy.tolist(),'gap':c['gap'],'reason':reason});seen[c['label']].append(xy.copy());return True
# Seed only finite geometric extreme points, not an assumption that these suffice.
for label,ids in patch_indices.items():
 candidates=[(ci,xy) for ci in ids for xy in cells[ci]['vertices']]
 for direction in np.array([[1.,1.],[1.,-1.],[-1.,1.],[-1.,-1.]]):
  ci,xy=max(candidates,key=lambda it:it[1]@direction);add_point(ci,xy,'seed_extreme')
print('SEEDS',len(points)-4,flush=True)

def field(lam,r,j,force):
 up=Uext[:,j]*force+P['data']['R']@r;uf=np.zeros(Nf)
 for i,value in enumerate(lam):
  if value!=0:up-=P['U'][i]*value;uf-=F['U'][i]*value
 return up,uf

def audit(up,uf):
 coeff=-normal[:,None]*(np.einsum('ijk,ik->ij',TP,up[DP])-np.einsum('ijk,ik->ij',TF,uf[DF]));coeff[:,0]+=gap0
 results=[]
 for i,c in enumerate(cells):results.append({'cell':i,'patch':c['label'],**extrema(coeff[i],c['vertices'],c['origin'])})
 return coeff,results

def full_check(up,uf,lam,j,force,r):
 loads={};states={};allbalances=[];work=0.;energy=0.
 for name,body,u in [('panel',P,up),('frame',F,uf)]:
  f=P['data']['F'][:,j]*force if name=='panel' else np.zeros(Nf)
  for i,v in enumerate(lam):
   idx,w=body['C'][i];np.add.at(f,idx,-v*w)
  res=body['K']@u-f;free_res=float(np.max(abs(res[body['free']])));reac=float(np.max(abs(res[body['D']])))
  if free_res>1e-9 or (name=='panel' and reac>1e-9):raise ValueError('full-field equilibrium or numerical-gauge reaction failed')
  axes=[body['data']['axis'+str(k)] for k in range(3)];xyz=body['data']['xyz'][:,axes[0]].T
  ext=f.copy()
  if name=='frame':ext[body['D']]+=res[body['D']]
  nodal=np.stack([ext[i] for i in axes],axis=1);allbalances.append(np.r_[nodal.sum(axis=0),np.cross(xyz,nodal).sum(axis=0)])
  e=float(.5*u@(body['K']@u));w=float(.5*u@f);energy+=e;work+=w
  states[name]={'free_residual_max':free_res,'gauge_or_fixture_reaction_max':reac,'strain_energy':e,'half_work':w,'relative_work_error':abs(e-w)/max(abs(e),abs(w),1e-20)};loads[name]=f
 balance=np.sum(allbalances,axis=0)
 if np.max(abs(balance))>1e-8:raise ValueError('global force/moment balance failed')
 q=np.array([dotcol(P['C'][i],up)+dotcol(F['C'][i],uf) for i in range(len(lam))]);contactgap=initialgap[4:len(lam)]-q[4:]
 return {'bodies':states,'total_force_moment_balance':balance.tolist(),'energy':energy,'half_work':work,'bolt_relative_displacements':q[:4].tolist(),'minimum_enforced_point_gap':float(np.min(contactgap)),'contact_complementarity_max':float(np.max(abs(lam[4:]*contactgap))),'minimum_contact_reaction':float(np.min(lam[4:])),'minimum_bolt_tension':float(np.min(lam[:4]))},loads

for case in a.cases:
 if not 0<=case<8:raise ValueError('unknown original synthetic case')
 out=a.output/f'case-{case}';out.mkdir();j=case%4;force=1e-5;pre=0. if case<4 else 2e-4;oldlam=None;history=[];success=False
 for exchange in range(a.max_exchanges):
  m=len(points);S=H[:m,:m].copy();S[np.arange(4),np.arange(4)]+=5.;d=qfree[:m,j]*force-initialgap[:m];d[:4]+=5.*pre
  if oldlam is not None:oldlam=np.pad(oldlam,(0,m-len(oldlam)))
  q=solve_force_qp(S,d,G[:m],loadG[:,j]*force,initial=oldlam,tolerance=2e-10)
  if not q['passed']:
   dump(out/'failure-qp.json',q);print('QP_FAILED',case,exchange,q['status'],flush=True);break
  lam=np.array(q['forces']);r=np.array(q['rigid_mode_coordinates']);up,uf=field(lam,r,j,force);co,checks=audit(up,uf)
  bad=[x for x in checks if x['minimum'] < -1e-7]
  row={'exchange':exchange,'point_constraints':m-4,'minimum_gap_mm':min(x['minimum'] for x in checks),'negative_cells':len(bad),'nonzero_contact_reactions':int(np.sum(lam[4:]>1e-11)),'minimum_bolt_tension':float(lam[:4].min()),'qp_iterations':q['iterations']}
  history.append(row);dump(out/'progress.json',{'history':history});print('EXCHANGE',case,row,flush=True)
  if not bad:
   success=True;break
  (out/f'failed-exchange-{exchange}.json.gz').write_bytes(gzip.compress(json.dumps({'row':row,'negative_cells':bad,'forces':lam.tolist(),'rigid':r.tolist()},allow_nan=False).encode(),mtime=0))
  if len(points)>=M-24:print('POINT_LIMIT',case,flush=True);break
  added=0
  for label in patch_indices:
   chosen=[]
   for candidate in sorted((x for x in bad if x['patch']==label),key=lambda x:x['minimum']):
    xy=np.array(candidate['minimum_at'])
    if any(np.linalg.norm(xy-y)<.08 for y in chosen):continue
    if add_point(candidate['cell'],xy,'actual_quadratic_minimum'):
     chosen.append(xy);added+=1
    if len(chosen)>=a.batch_per_patch:break
  if not added:print('NO_NEW_POINT',case,flush=True);break
  oldlam=lam
 if 'lam' not in locals():break
 m=len(lam);physical,loads=full_check(up,uf,lam,j,force,r)
 bolt_branch=lam[:4].min()>=-1e-10
 point_gaps=initialgap[4:m]-np.array([dotcol(P['C'][i],up)+dotcol(F['C'][i],uf) for i in range(4,m)])
 report={'case':case,'load_index':j,'force_over_Epanel_mm2':force,'spring_initial_over_Epanel_mm2':pre,'spring_compliance_times_Epanel_per_mm':5.,'Epanel_over_Eframe':1.,'nu':.3,
  'all_original_cells_nonpenetrating':success,'bolt_tension_branch_valid':bool(bolt_branch),'full_field_checks':physical,'history':history,'contact_points':points[:m],'forces':lam.tolist(),'rigid':r.tolist(),'enforced_gaps':point_gaps.tolist(),'qp':q,'input_sha256':inputs,'source_sha256':sha(__file__),'dual_solver_sha256':sha(ROOT/'integration/contact_dual_active.py'),'original_auditor_sha256':sha(ROOT/'integration/contact_patch_audit.py'),
  'audited_cells':len(cells),'mean_pressure_contact_replaced_by_point_reactions':True,'full_volume_energy_retained':True,'primal_stiffness_not_replaced_by_old_port_compliance':True,'neutral_Y_mode_not_physically_fixed':True,'frame_end_ideal_fixture_unchanged':True,'circles_common_planar_domain_only':True,'force_is_not_area_pressure':True,'FE_mesh_convergence':False,'point_contact_convergence':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'passed':bool(success and bolt_branch)}
 dump(out/'report.json',report);(out/'gap-extrema.json.gz').write_bytes(gzip.compress(json.dumps(checks,allow_nan=False).encode(),mtime=0))
 np.savez_compressed(out/'full-fields.npz',up=up,uf=uf,load_panel=loads['panel'],load_frame=loads['frame'],lambda_forces=lam,rigid=r)
 print('CASE_TERMINAL',case,report['passed'],len(points),flush=True)
 if not report['passed']:break
reports=[json.loads(p.read_text()) for p in sorted(a.output.glob('case-*/report.json'))]
dump(a.output/'SUMMARY.json',{'requested_cases':a.cases,'finished_cases':[r['case'] for r in reports],'all_requested_passed':len(reports)==len(a.cases) and all(r['passed'] for r in reports),'cases':[{k:r[k] for k in ['case','passed','audited_cells','all_original_cells_nonpenetrating','bolt_tension_branch_valid','full_field_checks']} for r in reports],'input_sha256':inputs})
