"""Independent trace field audit: library tetrahedral maps and flat local energy.

No contact solver or candidate trace-energy builder imported. The cubic
Bernstein audit is shared with separately checked tests; physical evaluations
are independently reconstructed. This is not directed-rounding certification.
"""
from pathlib import Path
import argparse,gzip,json,hashlib,sys
import numpy as np
from scipy.sparse import load_npz,coo_matrix
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-20261018')
sys.path.insert(0,str(R/'integration'));sys.path.insert(0,str(R/'engineering/trace-enrichment-20261017'))
sys.path.insert(0,str(R/'engineering/volume-convergence-20261017'))
from contact_patch_audit import triangle_coefficients,extrema
from cubic_trace_gap import audit_polygon
from independent_trace_elements import flat_matrix,REFERENCE,nodes
from frozen_load_response import recovered
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item(),allow_nan=False)+'\n')

p=argparse.ArgumentParser();p.add_argument('--case-id',required=True);p.add_argument('--expected-target',type=float,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--volume',type=Path,required=True);p.add_argument('--element-check',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--force-check',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
r=json.loads((a.run/'report.json').read_text());assert r['passed']
plan_path=R/'engineering/loadcases-20261018/EXPERIMENT_PLAN.json'
plan=json.loads(plan_path.read_text());entries={v['id']:v for v in plan['cases']};definition=entries[a.case_id]
expected_case=definition['case'];load_index=definition['load_index'];external_scale=definition['external_load_scale_over_Epanel_mm2'];initial_force=definition['initial_spring_force_over_Epanel_mm2']
gap_target=r['gap_tolerance_mm'];assert type(gap_target) in (int,float) and 0<gap_target<=1e-7 and gap_target==a.expected_target and r['case']==expected_case
assert r['load_index']==load_index and r['external_load_scale_over_Epanel_mm2']==external_scale and r['spring_initial_over_Epanel_mm2']==initial_force
assert r['frozen_selection_sha256']==sha(R/'engineering/joint-sensitivity-20261017/frozen-selection.json')
x=np.load(a.run/'full-fields.npz',allow_pickle=False);inputhash={str(a.run/f):sha(a.run/f) for f in ['report.json','full-fields.npz']};inputhash[str(plan_path)]=sha(plan_path)
for path,want in r['input_sha256'].items():assert sha(path)==want;inputhash[path]=want
raw=json.loads(gzip.decompress((R/'engineering/contact-field-20261015/common-cell-results.json.gz').read_bytes()))
metas=json.loads(gzip.decompress((R/'engineering/contact-field-20261015/coupled-field-audit.json.gz').read_bytes()))['contact_patches'];byname={m['patch']:m for m in metas}
flat=[(byname[g['patch']],c) for g in raw for c in g['cells']];assert len(flat)==5255
model={}
for name in ('panel','frame'):
    folder=a.volume/name/'level-2';d=np.load(folder/'mesh.npz',allow_pickle=False);mesh=MeshTet(d['points'].T,d['tetra'].T)
    scalar=Basis(mesh,ElementTetP2(),intorder=2);vector=Basis(mesh,ElementVector(ElementTetP2()),intorder=2);axes=vector.split_indices()
    loads=dict(np.load(folder/'loads.npz',allow_pickle=False));u=x['up' if name=='panel' else 'uf'];b=x['bp' if name=='panel' else 'bf']
    chosen=json.loads((a.run/name/'selection.json').read_text());lookup={tuple(v['vertices']):i for i,v in enumerate(chosen)}
    assert len(lookup)*3==len(b)
    records=json.loads((a.run/name/'local-records.json').read_text());I=[];J=[];V=[];B=np.zeros((len(b),len(b)));private={};blocks={}
    for rec in records:
        pp=a.element_check/f'{name}-tet-{rec["tet"]}.npz';ind=np.load(pp,allow_pickle=False);inputhash[str(pp)]=sha(pp)
        kb=ind['stiffness'];assert np.max(abs(kb-np.array(rec['extended_stiffness'])))<1e-8*max(np.max(abs(kb)),1e-300)
        role=rec['roles'];ii=np.array([30+3*f+j for f,k in role for j in range(3)]);jj=np.array([3*k+j for f,k in role for j in range(3)])
        cross=kb[:30,ii];I.extend(np.repeat(rec['retained_dofs'],len(jj)));J.extend(np.tile(jj,30));V.extend(cross.ravel())
        B[np.ix_(jj,jj)]+=kb[np.ix_(ii,ii)]
        face=np.zeros(12)
        for f,k in role:face[3*f:3*f+3]=b[3*k:3*k+3]
        ub=np.r_[u[rec['retained_dofs']],face];K=ind['uncondensed'];size=K.shape[0]-12;keep=np.r_[np.arange(30),np.arange(size,size+12)];inside=np.arange(30,size)
        q=np.zeros(K.shape[0]);q[keep]=ub;q[inside]=-np.linalg.solve(K[np.ix_(inside,inside)],K[np.ix_(inside,keep)]@ub)
        res=float(np.max(abs((K@q)[inside])));assert res<1e-9
        private[rec['tet']]={'interior_dofs':len(inside),'residual':res,'twice_energy':float(q@K@q)}
        np.savez_compressed(a.output/f'{name}-selected-tet-{rec["tet"]}-private.npz',private=q[inside],face_coefficients=face,reference_nodes=ind['reference_nodes'])
        blocks[rec['tet']]=rec
    A=coo_matrix((V,(I,J)),shape=(len(u),len(b))).tocsc()
    originalA=load_npz(a.run/name/'coupling.npz');difference=A-originalA
    assert np.max(abs(difference.data),initial=0.)<1e-8
    K=load_npz(folder/'K.npz');offset=0 if name=='panel' else len(x['up'])+len(x['bp'])
    supplied=x['load'][offset:offset+len(u)+len(b)]
    model[name]={'mesh':mesh,'scalar':scalar,'vector':vector,'axes':axes,'face':{tuple(sorted(v)):i for i,v in enumerate(mesh.facets.T)},'loads':loads,'u':u,'b':b,'lookup':lookup,'chosen':chosen,'K':K,'A':A,'B':B,'private':private,'blocks':blocks,'supplied':supplied,'expected':np.r_[-loads['C']@x['forces'][:4],np.zeros(len(b))]}
fr=json.loads((a.force_check/'report.json').read_text());assert fr['passed'] and fr['candidate_integration_not_imported']
inputhash[str(a.force_check/'report.json')]=sha(a.force_check/'report.json')
for file,h in fr['input_sha256'].items():assert sha(file)==h;inputhash[file]=h
for file,h in fr['files_sha256'].items():assert sha(a.force_check/file)==h;inputhash[str(a.force_check/file)]=h
for name,m in model.items():
    C=m['loads']['C'][:,:4].copy();F=m['loads']['F'].copy();Cb=np.zeros((len(m['b']),4));Fb=np.zeros((len(m['b']),F.shape[1]))
    if r['surface_load_mode']=='consistent':
        z=np.load(a.force_check/(name+'.npz'),allow_pickle=False);C=z['C'];F=z['F']
        for rec in json.loads((a.force_check/(name+'-bubble-loads.json')).read_text()):
            fi=m['lookup'].get(tuple(sorted(rec['vertices'])))
            if fi is not None:(Cb if rec['kind']=='C' else Fb)[3*fi:3*fi+3,rec['index']]+=np.asarray(rec['bubble_load'])
    elif r['surface_load_mode']!='discrete':raise ValueError('unknown load mode')
    m['effective_C']=C;m['effective_Cb']=Cb;m['effective_F']=F;m['effective_Fb']=Fb
    m['expected']=-np.r_[C,Cb]@x['forces'][:4]
model['panel']['expected']+=np.r_[model['panel']['effective_F'][:,load_index],model['panel']['effective_Fb'][:,load_index]]*external_scale

def point_data(name,triangle,point,axis):
    m=model[name];mesh=m['mesh'];fi=m['face'][tuple(sorted(triangle))];ti=int(mesh.f2t[0,fi]);v=mesh.p[:,mesh.t[:,ti]]
    local=np.linalg.solve(v[:,1:]-v[:,:1],point-v[:,0]);bary=np.r_[1-local.sum(),local]
    assert bary.min()>-1e-7 and bary.max()<1+1e-7
    shape=np.array([m['scalar'].elem.lbasis(local[:,None],i)[0][0] for i in range(10)])
    idx=m['axes'][axis][m['scalar'].element_dofs[:,ti]]
    newidx=m['lookup'].get(tuple(sorted(triangle)));bv=0.
    if newidx is not None:
        chosen=m['chosen'][newidx];facevertices=set(triangle);face_local=[j for j,node in enumerate(mesh.t[:,ti]) if node in facevertices]
        bv=float(27*np.prod(bary[face_local]))
    return idx,shape,newidx,bv

def gap(mm,c,xy):
    xy=np.atleast_2d(xy);vals=np.full(len(xy),mm['initial_gap_mm'],dtype=float);axis=mm['normal_axis'];tan=[j for j in range(3) if j!=axis];sg=mm['normal_sign']
    for j,pt in enumerate(xy):
        for name,sign in [('panel',1.),('frame',-1.)]:
            m=model[name];point=np.zeros(3);point[tan]=pt;point[axis]=1.2 if axis==2 else sg*(36.325 if name=='panel' else 36.345)
            idx,w,fi,bv=point_data(name,c[name+'_triangle'],point,axis);v=float(w@m['u'][idx])
            if fi is not None:v+=bv*m['b'][3*fi+axis]
            vals[j]-=sg*sign*v
    return vals

contactgap=[]
for reaction,point in zip(x['forces'][4:],r['contact_points'][4:]):
    mm,c=flat[point['cell']];assert mm['patch']==point['patch'];axis=mm['normal_axis'];sg=mm['normal_sign'];tan=[j for j in range(3) if j!=axis]
    contactgap.append(float(gap(mm,c,point['xy'])[0]))
    for name,sign in [('panel',1.),('frame',-1.)]:
        m=model[name];physical=np.zeros(3);physical[tan]=point['xy'];physical[axis]=1.2 if axis==2 else sg*(36.325 if name=='panel' else 36.345)
        idx,w,fi,bv=point_data(name,c[name+'_triangle'],physical,axis);np.add.at(m['expected'],idx,-reaction*sg*sign*w)
        if fi is not None:m['expected'][len(m['u'])+3*fi+axis]+=-reaction*sg*sign*bv
contactgap=np.array(contactgap);assert contactgap.min()>=-gap_target
assert np.min(x['forces'][4:])>=-1e-12 and np.min(x['forces'][:4])>=-1e-10
complementarity=float(np.max(abs(x['forces'][4:]*contactgap)));assert complementarity<1e-11
checks={};balance=[]
for name,m in model.items():
    N=len(m['u']);u,b=m['u'],m['b'];f0,fb=m['expected'][:N],m['expected'][N:]
    err=float(np.max(abs(m['supplied']-m['expected'])));assert err<1e-12
    q=m['K']@u+m['A']@b-f0;qb=m['A'].T@u+m['B']@b-fb;D=m['loads']['D'];free=np.setdiff1d(np.arange(N),D)
    fre=float(np.max(abs(q[free])));bre=float(np.max(abs(qb)));react=float(np.max(abs(q[D])))
    energy=float(u@(m['K']@u)+2*u@(m['A']@b)+b@m['B']@b);work=float(u@f0+b@fb)
    ee=abs(energy-work)/max(abs(energy),abs(work),1e-20);assert fre<1e-9 and bre<1e-9 and ee<1e-5
    if name=='panel':assert react<1e-9
    ext=f0.copy()
    if name=='frame':ext[D]+=q[D]
    nodal=np.stack([ext[idx] for idx in m['axes']],axis=1);xyz=m['vector'].doflocs[:,m['axes'][0]].T
    # Generalized face forces act on bubbles that are zero for rigid motion;
    # force/moment resultants are obtained with the complete rigid basis (new coefficients zero).
    balance.append(np.r_[nodal.sum(axis=0),np.cross(xyz,nodal).sum(axis=0)])
    checks[name]={'independent_load_error':err,'retained_free_residual':fre,'new_trace_residual':bre,'gauge_or_fixture_reaction':react,'relative_energy_error':ee,'twice_strain_energy':energy}
assert np.max(abs(np.sum(balance,axis=0)))<1e-8
qbolt=sum(m['effective_C'].T@m['u']+m['effective_Cb'].T@m['b'] for m in model.values());assert np.max(abs(x['forces'][:4]-initial_force-qbolt/5))<1e-10

regions=[];worst=1.;lowbound=1.;affected=0
for i,(mm,c) in enumerate(flat):
    special=any(tuple(sorted(c[name+'_triangle'])) in m['lookup'] for name,m in model.items())
    if special:
        z=audit_polygon(c['polygon'],lambda xy:gap(mm,c,xy),gap_tolerance=gap_target);affected+=1
        assert z['passed'],(i,z)
        low=float(z['covered_lower_bound']);lo=float(z['minimum_witness'])
    else:
        coef={};tan=[j for j in range(3) if j!=mm['normal_axis']]
        for name,m in model.items():coef[name]=triangle_coefficients(m['mesh'].p.T[c[name+'_triangle']][:,tan],m['u'][c[name+'_P2_dofs']],mm['origin_tangent_mm'])
        cf=-mm['normal_sign']*(coef['panel']-coef['frame']);cf[0]+=mm['initial_gap_mm']
        z=extrema(cf,c['polygon'],mm['origin_tangent_mm']);lo=low=float(z['minimum']);assert lo>=-gap_target
        assert abs(float(gap(mm,c,z['minimum_at'])[0])-lo)<1e-10
    worst=min(worst,lo);lowbound=min(lowbound,low);regions.append({'cell':i,'enriched_trace':special,'minimum_witness':lo,'covered_lower_bound':low})
dump(a.output/'regions.json',regions)
print('INDEPENDENT_ALL_REGIONS',len(regions),'ENRICHED',affected,'BOUND',lowbound,flush=True)

# Recover ALL untouched parents on the inherited nested space. Selected parents
# use the independent flat stiffness and private maps above, not the candidate.
for name,m in model.items():
    mesh=m['mesh'];v=mesh.p.T[mesh.t.T];elem=ElementTetP2();canonical=nodes(REFERENCE)
    perm=np.array([np.argmin(np.linalg.norm(elem.doflocs-pt,axis=1)) for pt in canonical]);ids=m['vector'].element_dofs[(3*perm[:,None]+np.arange(3)).ravel()].T
    remain=np.array([i for i in range(len(v)) if i not in m['private']],dtype=int);array=np.empty((len(remain),75));maxres=0.;energy=sum(z['twice_energy'] for z in m['private'].values())
    for lo in range(0,len(remain),256):
        at=remain[lo:lo+256];val,res,en=recovered(v[at],m['u'][ids[at]],2);array[lo:lo+len(at)]=val;maxres=max(maxres,res);energy+=float(en.sum())
    maxres=max(maxres,max(z['residual'] for z in m['private'].values()));assert maxres<1e-9
    error=abs(energy-checks[name]['twice_strain_energy'])/max(abs(energy),1e-20);assert error<1e-5
    target=a.output/(name+'-all-unselected-private.npz');np.savez_compressed(target,parent_tetrahedra=remain,private_coefficients=array)
    checks[name]['internal_recovery']={'unselected_parents':len(remain),'selected_parents':len(m['private']),'total_parents':len(v),
        'private_DOFs_recovered':75*len(v),'selected_private_maps':'independent flat child mesh; separate arrays with reference coordinates',
        'maximum_private_residual':maxres,'relative_integrated_energy_error':error,'private_file_sha256':sha(target)}
    print('RECOVERED',name,75*len(v),'ENERGY_ERROR',error,flush=True)
# Each field has its own declared load. Do not compare it with unrelated case6.
newenergy=sum(z['twice_strain_energy'] for z in checks.values())
F=model['panel']['effective_F'];Fb=model['panel']['effective_Fb']
observations=F.T@x['up']+Fb.T@x['bp']
result={'passed':True,'case_id':a.case_id,'full_discrete_case':expected_case,'definition':definition,
    'gap_tolerance_mm':gap_target,'frozen_selection_sha256':r['frozen_selection_sha256'],
    'total_regions':len(regions),'cubic_regions':affected,'minimum_covered_bound_mm':lowbound,'minimum_witness_mm':worst,
    'full_checks':checks,'contact_complementarity':complementarity,'balance':np.sum(balance,axis=0),
    'per_body_force_moment_balance':balance,'input_sha256':inputhash,
    'load_weighted_observations':observations,'load_weighted_response':float(observations[load_index]),
    'twice_elastic_energy':newenergy,'bolt_forces_over_Epanel_mm2':x['forces'][:4],
    'bolt_weighted_displacements_mm':qbolt,'initial_force_is_not_installed_equilibrated_force':True,
    'surface_load_mode':r['surface_load_mode'],'surface_projection_independently_rebuilt':True,
    'frozen_displacement_space_not_full_interface_convergence':True,
    'shared_bernstein_checker_with_independent_tetra_evaluation':True,'point_reactions_not_area_pressure':True,
    'source_sha256':sha(__file__),'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for path,want in inputhash.items():assert sha(path)==want
assert 'contact_dual_active' not in sys.modules and 'spatial_contact' not in sys.modules
dump(a.output/'report.json',result);print('INDEPENDENT_CASE_PASSED',a.case_id,result['load_weighted_response'],result['twice_elastic_energy'],flush=True)
