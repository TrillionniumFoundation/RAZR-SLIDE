"""Adaptive pointwise Signorini constraints on complete existing P2 body meshes.

Full component stiffness solves supply each spatial response, no fabricated
basis stiffness. Discrete nonnegative normal forces are added at violated
quadratic gap extrema. A positive node-only result is never a domain pass:
every common-cell quadratic is re-audited. This remains a reference-plane,
small-displacement, finite-mesh model with discrete force multipliers, not
converged continuum pressure/stress, real materials or rated service loads.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,gzip,hashlib,json,sys,time,gc
import numpy as np
from scipy.sparse import csc_matrix,hstack
from scipy.sparse.linalg import splu
from skfem import MeshTet,Basis,ElementVector,ElementTetP2
from skfem.models.elasticity import linear_elasticity,lame_parameters
from skfem import asm
from shapely.geometry import Polygon

ROOT=Path('/home/qian-qi/RAZR-SLIDE-spatial-contact-20261015')
BASE=Path('/tmp/razr-support-coupling-20261015')
OLD=ROOT/'engineering/contact-field-20261015'
sys.path.insert(0,str(ROOT/'integration'))
from spatial_contact import solve_reactions
from contact_patch_audit import triangle_coefficients,evaluate,extrema

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--cases',default='0,4')
parser.add_argument('--iterations',type=int,default=35)
parser.add_argument('--batch',type=int,default=32)
parser.add_argument('--max-points',type=int,default=1200)
a=parser.parse_args();OUT=a.output.resolve();OUT.mkdir(exist_ok=False)
CASE_IDS=[int(x) for x in a.cases.split(',')];assert CASE_IDS and len(set(CASE_IDS))==len(CASE_IDS) and all(0<=x<8 for x in CASE_IDS)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(path,x):
    text=json.dumps(x,indent=2,allow_nan=False,default=lambda v:v.item() if hasattr(v,'item') else v.tolist())+'\n'
    path.write_text(text)
source_hashes={str(Path(__file__)):sha(__file__),str(ROOT/'integration/spatial_contact.py'):sha(ROOT/'integration/spatial_contact.py'),str(ROOT/'integration/contact_patch_audit.py'):sha(ROOT/'integration/contact_patch_audit.py')}
rawpath=OLD/'common-cell-results.json.gz';raw=json.loads(gzip.decompress(rawpath.read_bytes()))
summary=json.loads(gzip.decompress((OLD/'coupled-field-audit.json.gz').read_bytes()))
assert sha(rawpath)==summary['common_cell_file_sha256']
CELLS=[];PATCHES=summary['contact_patches'];patch_ranges=[]
for patchid,(group,meta) in enumerate(zip(raw,PATCHES)):
    assert group['patch']==meta['patch'];start=len(CELLS)
    for cell in group['cells']:
        CELLS.append({'patch':patchid,'polygon':np.array(cell['polygon']),
                     'p_tri':cell['panel_triangle'],'f_tri':cell['frame_triangle'],
                     'p_dofs':np.array(cell['panel_P2_dofs'],dtype=int),'f_dofs':np.array(cell['frame_P2_dofs'],dtype=int),
                     'origin':np.array(meta['origin_tangent_mm']),'normal':meta['normal_sign'],'gap':meta['initial_gap_mm']})
    patch_ranges.append((start,len(CELLS)))
assert len(CELLS)==5255
source_hashes[str(rawpath)]=sha(rawpath)
print('DOMAIN',len(CELLS),'CELLS',len(PATCHES),'PATCHES','CASES',CASE_IDS,flush=True)

class Body:
    def __init__(self,name):
        self.name=name;self.prefix='p' if name=='panel' else 'f'
        folder=BASE/(name+'-final3');report=json.loads((folder/'report.json').read_text())
        self.input_hashes={}
        for fn,key in [('fields.npz','fields_sha256'),('reduced.npz','reduced_sha256')]:
            path=folder/fn;assert sha(path)==report[key];self.input_hashes[str(path)]=sha(path)
        fields=np.load(folder/'fields.npz',allow_pickle=False)
        meshpath=BASE/('input/mesh.npz' if name=='panel' else 'frame-mesh3/mesh.npz')
        assert sha(meshpath)==report['mesh_sha256'];self.input_hashes[str(meshpath)]=sha(meshpath)
        data=np.load(meshpath,allow_pickle=False);self.mesh=MeshTet(data['points'].T,data['tetra'].T)
        self.basis=Basis(self.mesh,ElementVector(ElementTetP2()),intorder=4);self.N=self.basis.N
        self.xyz=self.basis.doflocs;assert np.array_equal(self.xyz,fields['dof_xyz'])
        self.axes=[fields['axis'+str(i)] for i in range(3)];self.D=fields['D'];self.free=np.setdiff1d(np.arange(self.N),self.D)
        self.R=fields['rigid_modes'] if name=='panel' else np.zeros((self.N,6))
        self.C=csc_matrix(fields['port_forces'][:,:4]);self.F=fields['external_forces'] if name=='panel' else np.zeros((self.N,4))
        trace=np.unique(np.r_[np.concatenate([c[self.prefix+'_dofs'] for c in CELLS]),self.C.indices])
        self.trace=trace;self.trmap=np.full(self.N,-1,dtype=int);self.trmap[trace]=np.arange(len(trace));self.Rtrace=self.R[trace]
        self.Ct=self.C[trace];self.V=np.zeros((len(trace),0))
        L,mu=lame_parameters(1.,.3);t=time.monotonic();self.K=asm(linear_elasticity(L,mu),self.basis).tocsc()
        print('ASSEMBLED',name,self.N,self.K.nnz,round(time.monotonic()-t,2),flush=True)
        self.factor=splu(self.K[self.free][:,self.free],permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True})
        print('FACTORED',name,round(time.monotonic()-t,2),flush=True)
        init=self.solve(self.C.toarray());self.V=init[trace]
        ext=self.solve(self.F);self.Vext=ext[trace]
        self.ext_rigid=self.R.T@self.F
        self.original_reduction=report
        del init,ext,fields;gc.collect()
    def solve(self,rhs):
        out=np.zeros_like(rhs);out[self.free]=self.factor.solve(rhs[self.free]);return out
    def add(self,pts):
        if not pts:return
        rr=[];cc=[];vv=[]
        for j,p in enumerate(pts):
            cell=CELLS[p['cell']];poly=cell[self.prefix+'_poly'];n=cell['normal']*(1 if self.name=='panel' else -1)
            vals=evaluate(poly,np.array([p['xy']]),cell['origin'])[0]*n
            assert abs(vals.sum()-n)<1e-8
            rr.extend(cell[self.prefix+'_dofs']);cc.extend([j]*6);vv.extend(vals)
        new=csc_matrix((vv,(rr,cc)),shape=(self.N,len(pts)))
        blocks=[]
        for start in range(0,len(pts),8):
            solution=self.solve(new[:,start:start+8].toarray());blocks.append(solution[self.trace]);del solution
        self.C=hstack([self.C,new],format='csc');self.Ct=self.C[self.trace]
        self.V=np.column_stack([self.V,*blocks])
        print('RESPONSE_COLUMNS',self.name,self.V.shape,flush=True)
    def final_field(self,lam,rigid,j,F):
        load=self.F[:,j]*F-self.C@lam
        u=self.solve(load[:,None])[:,0]
        if self.name=='panel':u+=self.R@rigid
        residual=self.K@u-load
        energy=.5*float(u@(self.K@u));work=.5*float(u@load)
        nf=np.stack([(load+residual)[ax] for ax in self.axes],axis=1)
        xyz=self.xyz[:,self.axes[0]].T
        balance=np.r_[nf.sum(axis=0),np.cross(xyz,nf).sum(axis=0)]
        audit={'free_residual_max':float(np.max(abs(residual[self.free]))),'constraint_reaction_max':float(np.max(abs(residual[self.D]))),
               'strain_energy':energy,'external_work_over2':work,'relative_work_error':abs(energy-work)/max(abs(energy),1e-30),
               'body_force_moment_balance':balance.tolist()}
        return u,load,residual,audit

with ThreadPoolExecutor(max_workers=2) as pool:
    fut={name:pool.submit(Body,name) for name in ('panel','frame')}
    bodies={name:f.result() for name,f in fut.items()}
pb,fb=bodies['panel'],bodies['frame']
for name,b in bodies.items():source_hashes.update(b.input_hashes)
for cell in CELLS:
    axis=PATCHES[cell['patch']]['normal_axis'];tan=[x for x in range(3) if x!=axis]
    for prefix,b in [('p',pb),('f',fb)]:
        xy=b.mesh.p.T[cell[prefix+'_tri']][:,tan]
        cell[prefix+'_poly']=triangle_coefficients(xy,np.eye(6),cell['origin'])
        cell[prefix+'_index']=b.trmap[cell[prefix+'_dofs']];assert min(cell[prefix+'_index'])>=0
print('READY_FACTORS_AND_POLYNOMIALS',flush=True)
points=[];pointkeys=set()
def addpoint(ci,xy,collection):
    cell=CELLS[ci];key=(cell['patch'],*np.round(xy,8))
    if key in pointkeys:return False
    pointkeys.add(key);collection.append({'patch':cell['patch'],'cell':int(ci),'xy':np.asarray(xy).tolist()});return True
# Seed real points spread within each audited footprint, never a hole centroid.
new=[]
for pi,(start,end) in enumerate(patch_ranges):
    inds=np.arange(start,end);centers=np.array([Polygon(CELLS[i]['polygon']).centroid.coords[0] for i in inds]);o=PATCHES[pi]['origin_tangent_mm']
    offsets=[(-.8,-.8),(-.8,.8),(.8,-.8),(.8,.8)] if pi<4 else [(-.5,-.35),(-.5,.35),(.5,-.35),(.5,.35)]
    for delta in offsets:
        target=np.array(o)+delta;ii=int(inds[np.argmin(np.linalg.norm(centers-target,axis=1))]);addpoint(ii,Polygon(CELLS[ii]['polygon']).centroid.coords[0],new)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda b:b.add(new),[pb,fb]))
points.extend(new)

# Precompute each cell's full nodal-to-polynomial maps. Kept independent of QP.
pindex=np.array([c['p_index'] for c in CELLS]);findex=np.array([c['f_index'] for c in CELLS]);pmat=np.array([c['p_poly'] for c in CELLS]);fmat=np.array([c['f_poly'] for c in CELLS]);normals=np.array([c['normal'] for c in CELLS]);g0=np.array([c['gap'] for c in CELLS])

def audit(up,uf):
    coeff=-normals[:,None,None]*(np.einsum('cij,cjk->cik',pmat,up[pindex])-np.einsum('cij,cjk->cik',fmat,uf[findex]));coeff[:,0,:]+=g0[:,None]
    lows=np.zeros((len(CELLS),len(CASE_IDS)));locs=np.zeros((len(CELLS),len(CASE_IDS),2));types=[]
    for i,c in enumerate(CELLS):
        for j in range(len(CASE_IDS)):
            x=extrema(coeff[i,:,j],c['polygon'],c['origin']);lows[i,j]=x['minimum'];locs[i,j]=x['minimum_at']
    return lows,locs,coeff

iterations=[];warm=[None]*len(CASE_IDS);final=[];tstart=time.monotonic();success=False
for it in range(a.iterations):
    Hraw=np.asarray(pb.Ct.T@pb.V+fb.Ct.T@fb.V)
    asym=np.max(abs(Hraw-Hraw.T))/max(np.max(abs(Hraw)),1e-30)
    assert asym<1e-7,('nonreciprocal full response',asym)
    H=(Hraw+Hraw.T)/2;G=np.asarray(pb.Ct.T@pb.Rtrace)
    q0=np.asarray(pb.Ct.T@pb.Vext);gaps=np.array([CELLS[p['cell']]['gap'] for p in points])
    ups=[];ufs=[];solutions=[]
    for k,cid in enumerate(CASE_IDS):
        j=cid%4;P=0. if cid<4 else 2e-4;F=1e-5
        w=warm[k]
        if w is not None:w=np.pad(w,(0,len(H)-len(w)))
        result=solve_reactions(H,G,q0[:,j]*F,pb.ext_rigid[:,j]*F,np.full(4,5.),np.full(4,P),gaps,warm_start=w,tolerance=2e-11,max_iterations=6000)
        if not result['passed']:
            dump(OUT/f'failed-QP-{it}-{cid}.json',result);raise RuntimeError(('contact QP did not converge',it,cid,result))
        lam=np.array(result['forces']);r=np.array(result['rigid_coordinates']);warm[k]=lam
        ups.append(pb.Vext[:,j]*F-pb.V@lam+pb.Rtrace@r);ufs.append(-fb.V@lam)
        solutions.append({'case':cid,'load_index':j,'force_over_Epanel_mm2':F,'spring_initial_over_Epanel_mm2':P,'result':result})
    Up=np.column_stack(ups);Uf=np.column_stack(ufs);lo,xy,coeff=audit(Up,Uf)
    worst=lo.min(axis=0);row={'iteration':it,'point_count':len(points),'case_ids':CASE_IDS,'minimum_gaps_mm':worst.tolist(),
                            'negative_cells_per_case':(lo<-1e-7).sum(axis=0).tolist(),'QP_iterations':[s['result']['iterations'] for s in solutions],
                            'response_reciprocity_relative_error':float(asym),'elapsed_seconds':time.monotonic()-tstart}
    iterations.append(row);dump(OUT/'progress.json',{'iterations':iterations,'not_yet_accepted':bool(np.min(lo)<-1e-7)})
    dump(OUT/f'iteration-{it:02d}.json',{'summary':row,'solutions':solutions})
    np.savez_compressed(OUT/'latest-traces.npz',panel=Up,frame=Uf,panel_trace=pb.trace,frame_trace=fb.trace,minimum_gaps=lo,minimum_xy=xy)
    print('EXCHANGE',json.dumps(row),flush=True)
    final=solutions
    if float(np.min(lo))>=-1e-7:
        success=True;break
    if len(points)>=a.max_points:break
    new=[]
    # Most severe violations first, bounded batch, but all cells are rechecked.
    order=np.argsort(lo.ravel());patchadded=np.zeros(len(PATCHES),dtype=int)
    for flat in order:
        ci,k=np.unravel_index(flat,lo.shape)
        if lo[ci,k]>=-1e-7:break
        pi=CELLS[ci]['patch']
        if patchadded[pi]>=max(4,a.batch//4):continue
        candidate=xy[ci,k]
        if any(p['patch']==pi and np.linalg.norm(np.array(p['xy'])-candidate)<1e-5 for p in points+new):continue
        if addpoint(ci,candidate,new):patchadded[pi]+=1
        if len(new)>=a.batch or len(points)+len(new)>=a.max_points:break
    if not new:
        print('NO_NEW_DISTINCT_CONSTRAINTS',flush=True);break
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda b:b.add(new),[pb,fb]))
    points.extend(new)

# Full fields for the last actually solved point set (not a pending enrichment).
solved_points=len(final[0]['result']['forces'])-4;point_records=points[:solved_points]
fullaudits=[]
for k,case in enumerate(final):
    lam=np.array(case['result']['forces']);r=np.array(case['result']['rigid_coordinates']);j=case['load_index'];F=case['force_over_Epanel_mm2'];fields={}
    # If the last loop appended untested points, zero their forces explicitly.
    lam=np.pad(lam,(0,pb.C.shape[1]-len(lam)))
    for name,b in bodies.items():
        u,load,residual,metrics=b.final_field(lam,r,j,F);fields[name]=(u,load,residual);fullaudits.append({'case':case['case'],'body':name,**metrics})
        assert metrics['free_residual_max']<1e-8
        if name=='panel':assert metrics['constraint_reaction_max']<1e-8
    np.savez_compressed(OUT/f'case-{case["case"]}-full-fields.npz',panel_u=fields['panel'][0],panel_load=fields['panel'][1],panel_residual=fields['panel'][2],
                        frame_u=fields['frame'][0],frame_load=fields['frame'][1],frame_residual=fields['frame'][2],lambda_all=lam,rigid=r)
    assert np.max(abs(fields['panel'][0][pb.trace]-Up[:,k]))<1e-7
    assert np.max(abs(fields['frame'][0][fb.trace]-Uf[:,k]))<1e-7
np.savez_compressed(OUT/'final-system.npz',H=H,G=G,q0=q0,gaps=gaps,panel_trace=pb.trace,frame_trace=fb.trace)
dump(OUT/'points.json',point_records)
for path,h in source_hashes.items():assert sha(path)==h,('input changed',path)
report={'input_sha256':source_hashes,'method':'adaptive pointwise nonnegative contact reaction exchange over complete unchanged P2 body meshes',
        'cases':CASE_IDS,'solved_contact_points':solved_points,'iterations':iterations,'case_results':final,'full_field_checks':fullaudits,
        'nonpenetration_on_audited_domain':success,'gap_tolerance_mm':1e-7,'discrete_contact_solution_accepted':success,
        'same_old_mesh_no_FE_mesh_convergence':True,'finite_point_force_multipliers_not_continuum_pressure_or_stress':True,
        'common_cell_domain_only':True,'uncovered_pad_strips_not_qualified':True,'frame_end_face_ideal_fixity':True,
        'E_normalization':1.,'nu_assumption':.3,'real_material_preload_or_service_load':False,
        'no_CAD_change':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
dump(OUT/'report.json',report);print('FINAL_ACCEPTED_DISCRETE_CONTACT',success,'POINTS',solved_points,flush=True)
