"""Selected-face P3-bubble sensitivity on the actual L2 volume problem.

Two highest case6 force-resultant faces per patch and body are chosen before
solving. All XYZ coefficients are free. Other traces are not enriched: this is
NOT full contact-trace convergence. Original nodal load functionals are kept;
new bubbles vanish at every original node. No continuous pressure is invented.
The changed inverse is derived by an exact block Schur update, not copied H.
"""
from pathlib import Path
import argparse,gzip,json,sys,time
import numpy as np
from scipy.sparse import coo_matrix,csc_matrix,hstack,vstack,load_npz,save_npz
from scipy.sparse.linalg import splu
from scipy.linalg import cho_factor,cho_solve
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
from face_trace_space import trace_condense,FACES,face_values
from tetra_bubble_refinement import p2_nodes,REF,star_condense
from contact_patch_audit import triangle_coefficients,evaluate
from contact_exchange import ExactResponseCache,QuadraticGapBatch,select_violations,feasible_force_guess,sha256
from contact_dual_active import solve_force_qp
from cubic_trace_gap import audit_polygon

BASE='fb95a3b9a7d58849303287d7321bb7846254f029'
TOL=1e-7

def jsonable(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    raise TypeError(type(x).__name__)
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,default=jsonable,allow_nan=False)+'\n')
def col(n,idx,val):return coo_matrix((val,(idx,np.zeros(len(idx),dtype=int))),shape=(n,1)).tocsc()

def run(a):
    sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
    from surface_archive import checked_study_controls, frozen_trace_selection, checked_external_load_scale
    case,target,load_index,spring_initial=checked_study_controls(getattr(a,'case',6),getattr(a,'gap_tolerance',TOL))
    external_scale=checked_external_load_scale(getattr(a,'external_load_scale',None))
    from installation_control import binding_digest,read_control,force_equalities,split_coordinates,adjustment_from_state
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    fieldroot=ROOT/'engineering/nested-contact-20261017/level-2'
    seedfile=fieldroot/'case-6/report.json.gz';seed=json.loads(gzip.decompress(seedfile.read_bytes()))
    assert seed['passed'];points=json.loads((a.state/'points.json').read_text());state=np.load(a.state/'response.npz',allow_pickle=False)
    sm=json.loads((a.state/'manifest.json').read_text())
    assert sha256(a.state/'points.json')==sm['points_sha256'] and sha256(a.state/'response.npz')==sm['response_sha256']
    assert points==seed['contact_points'],'case6 and response columns differ'
    hashes={str(p):sha256(p) for p in [seedfile,a.state/'points.json',a.state/'response.npz',a.state/'manifest.json']}
    for name in ('assembly_inputs.json','roof_joint_load_inputs.json','frame_thread_actual_inputs.json'):
        p=ROOT/'integration'/name;hashes[str(p)]=sha256(p)
    cf=ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz';mf=ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
    raw=json.loads(gzip.decompress(cf.read_bytes()));metas=json.loads(gzip.decompress(mf.read_bytes()))['contact_patches']
    hashes[str(cf)]=sha256(cf);hashes[str(mf)]=sha256(mf)
    byname={m['patch']:m for m in metas};flat=[(byname[g['patch']],c) for g in raw for c in g['cells']];assert len(flat)==5255
    surface=None;load_mode=getattr(a,'surface_load_mode','discrete')
    if getattr(a,'surface_loads',None) is not None:
        sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
        from surface_archive import SurfaceArchive
        surface=SurfaceArchive(a.surface_loads);hashes.update(surface.hashes)
    elif load_mode!='discrete':raise ValueError('consistent loading requires a verified surface archive')
    frozen_path=getattr(a,'frozen_selection',None);frozen=None
    if frozen_path is not None:
        frozen_path=Path(frozen_path).resolve();frozen=json.loads(frozen_path.read_text());hashes[str(frozen_path)]=sha256(frozen_path)
    oldforce=np.asarray(seed['forces']);bodies={};selection=[]
    for name in ('panel','frame'):
        folder=a.volume/name/'level-2';report=json.loads((folder/'report.json').read_text())
        for file,key in [('K.npz','K_sha256'),('loads.npz','loads_sha256'),('mesh.npz','mesh_sha256')]:
            p=folder/file;assert sha256(p)==report[key];hashes[str(p)]=report[key]
            prior=[h for f,h in sm['input_sha256'].items() if f.endswith('/'+name+'/level-2/'+file)]
            assert prior==[report[key]],('base checkpoint energy differs',name,file)
        hashes[str(folder/'report.json')]=sha256(folder/'report.json')
        md=np.load(folder/'mesh.npz',allow_pickle=False);mesh=MeshTet(md['points'].T,md['tetra'].T)
        basis=Basis(mesh,ElementVector(ElementTetP2()),intorder=2);data=dict(np.load(folder/'loads.npz',allow_pickle=False))
        assert np.array_equal(basis.doflocs,data['xyz'])
        loc=ElementTetP2().doflocs;perm=np.array([np.argmin(np.linalg.norm(loc-x,axis=1)) for x in p2_nodes(REF)])
        ids=basis.element_dofs[(3*perm[:,None]+np.arange(3)).ravel()].T
        scores={m['patch']:{} for m in metas}
        for p,force in zip(points[4:],oldforce[4:]):
            mm,cell=flat[p['cell']];key=tuple(sorted(cell[name+'_triangle']))
            scores[mm['patch']][key]=scores[mm['patch']].get(key,0.)+float(force)
        chosen=[]
        for patch in sorted(scores):
            ranked=sorted(scores[patch],key=lambda key:(-scores[patch][key],key))
            for key in ranked[:a.faces_per_patch]:chosen.append({'body':name,'patch':patch,'vertices':list(key),'prior_resultant':scores[patch][key]})
        if frozen is not None:chosen=frozen_trace_selection(frozen,name,report['mesh_sha256'])
        elif surface is not None:chosen=surface.extend_selection(name,chosen,a.load_face_cap)
        chosen.sort(key=lambda x:(x['patch'],x['vertices']));lookup={tuple(x['vertices']):i for i,x in enumerate(chosen)}
        assert len(lookup)==len(chosen)
        face_lookup={tuple(sorted(tri)):i for i,tri in enumerate(mesh.facets.T)}
        affected={};nb=3*len(chosen)
        for i,desc in enumerate(chosen):
            fi=face_lookup[tuple(desc['vertices'])];adj=mesh.f2t[:,fi];adj=adj[adj>=0]
            assert len(adj)==1,'this preselected experiment enriches only exterior contact faces'
            ti=int(adj[0]);tet=mesh.t[:,ti];local=next(f for f,ix in enumerate(FACES) if set(tet[list(ix)])==set(desc['vertices']))
            desc.update(tet=ti,local_face=local,coefficient_indices=[3*i,3*i+1,3*i+2])
            affected.setdefault(ti,[]).append((local,i))
            xyz=mesh.p[:,desc['vertices']].T;desc['area_mm2']=float(np.linalg.norm(np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]))/2)
        I=[];J=[];V=[];B=np.zeros((nb,nb));oldmax=0.;oldrel=0.
        local_records=[]
        for ti,roles in sorted(affected.items()):
            vertices=mesh.p.T[mesh.t[:,ti]][None];k=trace_condense(vertices,level=2).stiffness[0]
            old=star_condense(vertices,level=2).stiffness[0];delta=float(np.max(abs(k[:30,:30]-old)))
            oldmax=max(oldmax,delta);oldrel=max(oldrel,delta/max(np.max(abs(old)),1e-300));assert oldrel<1e-10
            localidx=np.array([30+3*f+j for f,_ in roles for j in range(3)]);globalidx=np.array([3*i+j for _,i in roles for j in range(3)])
            cross=k[:30,localidx];bb=k[np.ix_(localidx,localidx)]
            I.extend(np.repeat(ids[ti],len(globalidx)));J.extend(np.tile(globalidx,30));V.extend(cross.ravel())
            B[np.ix_(globalidx,globalidx)]+=bb
            local_records.append({'tet':ti,'roles':roles,'vertices':vertices[0],'retained_dofs':ids[ti],'extended_stiffness':k})
        A=coo_matrix((V,(I,J)),shape=(basis.N,nb)).tocsc();K=load_npz(folder/'K.npz').tocsc()
        D=data['D'];free=np.setdiff1d(np.arange(basis.N),D)
        assert np.max(abs(A[D].data),initial=0.)<1e-11,'new trace interacts with an unexamined fixed support'
        start=time.monotonic();factor=splu(K[free][:,free],permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True})
        Z=np.zeros((basis.N,nb))
        for j in range(0,nb,8):Z[free,j:j+8]=factor.solve(A[free,j:j+8].toarray(order='F'))
        residual=K@Z-A.toarray();freeerr=float(np.max(abs(residual[free])));assert freeerr<1e-8*max(1.,np.max(abs(A.data)))
        S=B-np.asarray(A.T@Z);asym=float(np.max(abs(S-S.T)));assert asym<1e-8*max(np.max(abs(S)),1e-300)
        S=(S+S.T)/2;sf=cho_factor(S,lower=True)
        bodyout=out/name;bodyout.mkdir();save_npz(bodyout/'coupling.npz',A)
        np.savez_compressed(bodyout/'local-blocks.npz',B=B,S=S,selected_tetrahedra=np.array(sorted(affected)),
            local_stiffness=np.stack([x['extended_stiffness'] for x in local_records]))
        dump(bodyout/'selection.json',chosen);dump(bodyout/'local-records.json',local_records)
        dump(bodyout/'assembly.json',{'old_dofs':basis.N,'new_trace_dofs':nb,'selected_faces':len(chosen),
            'old_energy_block_error_max':oldmax,'old_energy_block_error_relative':oldrel,'schur_min_eigenvalue':float(np.linalg.eigvalsh(S).min()),
            'extension_free_residual_max':freeerr,'seconds':time.monotonic()-start,
            'old_discrete_nodal_loads_unchanged_new_coefficients_zero_at_old_nodes':True,
            'new_traction_pressure_not_assigned':True,'all_new_components_free':True})
        if surface is None:
            lc=data['C'][:,:4].copy();lf=data['F'].copy();lcb=np.zeros((nb,4));lfb=np.zeros((nb,lf.shape[1]))
        else:lc,lcb,lf,lfb=surface.vectors(name,chosen,data,load_mode)
        np.savez_compressed(bodyout/'effective-loads.npz',C=lc,Cb=lcb,F=lf,Fb=lfb)
        bodies[name]={'K':K,'A':A,'B':B,'Z':Z,'sf':sf,'data':data,'free':free,'D':D,'factor':factor,
            'C':lc,'Cb':lcb,'F':lf,'Fb':lfb,
            'N':int(basis.N),'nb':nb,'lookup':lookup,'chosen':chosen,'mesh':mesh,'ids':ids}
        selection.extend(chosen);print('BODY_READY',name,basis.N,nb,'relative_oldblock',oldrel,'seconds',time.monotonic()-start,flush=True)
    dump(out/'selection.json',selection)
    model_payload={'bodies':{name:{file:sha256(a.volume/name/'level-2'/file) for file in ['K.npz','loads.npz','mesh.npz']} for name in ['panel','frame']},
        'selection':selection,'common_regions':sha256(cf),'contact_patches':sha256(mf),
        'surface_mode':load_mode,'surface_manifest':sha256(surface.root/'manifest.json') if surface else None}
    model_identity=binding_digest(model_payload)
    control={'mode':'legacy_initial_parameter','compliance':np.full(4,5.),'targets':None,'adjustment':np.full(4,5.*spring_initial)}
    control_path=getattr(a,'installation_control',None)
    if control_path is not None:
        control,control_hashes=read_control(control_path,model_identity=model_identity,external_scale=external_scale)
        hashes.update(control_hashes)
    force_mode=control['mode']=='force_targets'
    hashes[str(ROOT/'integration/installation_control.py')]=sha256(ROOT/'integration/installation_control.py')
    dump(out/'installation-model-identity.json',{'model_identity':model_identity,'payload':model_payload})
    P,F=bodies['panel'],bodies['frame'];npanel=P['N'];nframe=F['N'];n0=npanel+nframe
    nP=npanel+P['nb'];nF=nframe+F['nb'];n=nP+nF
    def base_body(b,rhs):
        u=np.zeros_like(rhs);u[b['free']]=b['factor'].solve(np.array(rhs[b['free']],order='F'));return u
    def body_response(b,rhs):
        u=base_body(b,rhs[:b['N']]);v=cho_solve(b['sf'],rhs[b['N']:]-b['A'].T@u)
        return np.concatenate((u-b['Z']@v,v),axis=0)
    def response(rhs):return np.concatenate((body_response(P,rhs[:nP]),body_response(F,rhs[nP:])),axis=0)
    cells=[]
    for mm,cell in flat:
        axis=mm['normal_axis'];tan=[k for k in range(3) if k!=axis];origin=np.array(mm['origin_tangent_mm']);dp=np.array(cell['panel_P2_dofs']);df=np.array(cell['frame_P2_dofs'])
        row={'label':mm['patch'],'origin':origin,'vertices':cell['polygon'],'normal':mm['normal_sign'],'gap':mm['initial_gap_mm'],'axis':axis,'tan':tan,'dp':dp,'df':df}
        for name,b,dofs in [('panel',P,dp),('frame',F,df)]:
            row[name+'_q']=triangle_coefficients(b['data']['xyz'][tan][:,dofs[:3]].T,np.eye(6),origin)
            key=tuple(sorted(cell[name+'_triangle']));row[name+'_face']=b['lookup'].get(key)
            xy=b['mesh'].p.T[cell[name+'_triangle']][:,tan]
            row[name+'_inv']=np.linalg.inv((xy[1:]-xy[0]).T);row[name+'_x0']=xy[0]
        cells.append(row)
    def bubble(c,name,xy):
        tail=(np.asarray(xy)-c[name+'_x0'])@c[name+'_inv'].T
        return 27*tail[:,0]*tail[:,1]*(1-tail.sum(axis=1))
    def one_map(p,*,old_only=False):
        if p['kind']=='bolt':
            idx=p['index'];assert 0<=idx<4
            c0=np.r_[P['C'][:,idx],P['Cb'][:,idx],F['C'][:,idx],F['Cb'][:,idx]]
            return csc_matrix(c0[:,None])
        c=cells[p['cell']];xy=np.array(p['xy'])[None];sign=c['normal'];assert p['patch']==c['label'] and p['gap']==c['gap']
        idx=[];weights=[]
        for name,b,offset,sg in [('panel',P,0,sign),('frame',F,nP,-sign)]:
            d=c['dp' if name=='panel' else 'df'];idx.extend(offset+d);weights.extend(sg*evaluate(c[name+'_q'],xy,c['origin'])[0])
            fi=c[name+'_face']
            if fi is not None:idx.append(offset+b['N']+3*fi+c['axis']);weights.append(sg*bubble(c,name,xy)[0])
        return col(n,np.array(idx,dtype=int),np.array(weights))
    C=hstack([one_map(p) for p in points],format='csc')
    oldC=vstack([C[:npanel],C[nP:nP+nframe]],format='csc');oldH=state['H'];assert oldH.shape==(len(points),)*2
    def base_response(rhs):return np.concatenate((base_body(P,rhs[:npanel]),base_body(F,rhs[npanel:])),axis=0)
    identity={'base':BASE,'input_sha256':hashes,'trace_selection':selection,'space':'L2 plus selected cubic face bubbles'}
    original=ExactResponseCache(n0,base_response,{'base_K_and_maps':hashes})
    referenceC=oldC.tolil(copy=True)
    referenceC[:,:4]=csc_matrix(np.vstack([P['data']['C'][:,:4],F['data']['C'][:,:4]]))
    referenceC=referenceC.tocsc()
    check0=original.restore(referenceC,oldH,original.identity,probes=5);print('BASE_RESPONSE_VERIFIED',check0,flush=True)
    H=oldH.copy()
    # Only four base force functionals changed. Recompute their COMPLETE
    # operator columns; old contact/contact entries still have the same K/maps.
    if surface is not None and load_mode=='consistent':
        responses=base_response(oldC[:,:4].toarray(order='F'))
        columns=np.asarray(oldC.T@responses);H[:,:4]=columns;H[:4,:]=columns.T
        H[:4,:4]=(H[:4,:4]+H[:4,:4].T)/2
    for name,b,off in [('panel',P,0),('frame',F,nP)]:
        c0=C[off:off+b['N']];cb=C[off+b['N']:off+b['N']+b['nb']].toarray()
        T=cb-np.asarray(c0.T@b['Z']).T
        H+=T.T@cho_solve(b['sf'],T)
    cache=ExactResponseCache(n,response,identity,response_block=response,response_batch_size=8)
    updated=cache.restore(C,H,identity,probes=5)
    dump(out/'exact-energy-update.json',{'base_check':vars(check0),'augmented_check':vars(updated),
        'old_H_directly_used_as_new_energy':False,'formula':'Hnew=Hbase+sum(T.T S^-1 T), T=Cb-Z.T C0',
        'selected_faces':len(selection),'additional_trace_dofs':P['nb']+F['nb']})
    external=np.r_[P['F'][:,load_index]*external_scale,P['Fb'][:,load_index]*external_scale,np.zeros(nF)]
    R=np.vstack([P['data']['R'],np.zeros((P['nb']+nF,6))]);G=np.asarray(C.T@R)
    loadG=R.T@external
    Uext=response(external);qfree=np.asarray(C.T@Uext).ravel();initialgap=np.array([p.get('gap',0.) for p in points])
    qb=QuadraticGapBatch([c['vertices'] for c in cells],[c['origin'] for c in cells])
    tp=np.stack([c['panel_q'] for c in cells]);tf=np.stack([c['frame_q'] for c in cells]);dp=np.stack([c['dp'] for c in cells]);df=np.stack([c['df'] for c in cells]);normal=np.array([c['normal'] for c in cells]);gap0=np.array([c['gap'] for c in cells])
    enriched_cells=[i for i,c in enumerate(cells) if c['panel_face'] is not None or c['frame_face'] is not None]
    def audit(u):
        up=u[:npanel];uf=u[nP:nP+nframe]
        coefficients=-normal[:,None]*(np.einsum('ijk,ik->ij',tp,up[dp])-np.einsum('ijk,ik->ij',tf,uf[df]));coefficients[:,0]+=gap0
        result=qb.extrema(coefficients);minimum=result['minimum'].copy();where=result['minimum_at'].copy();lower=minimum.copy();checks=[];unresolved=[]
        for i in enriched_cells:
            c=cells[i]
            def val(xy):
                v=evaluate(coefficients[i],xy,c['origin'])
                for name,b,offset,sg in [('panel',P,0,-c['normal']),('frame',F,nP,c['normal'])]:
                    fi=c[name+'_face']
                    if fi is not None:v=v+sg*u[offset+b['N']+3*fi+c['axis']]*bubble(c,name,xy)
                return v
            r=audit_polygon(c['vertices'],val,gap_tolerance=target)
            minimum[i]=r['minimum_witness'];where[i]=r['minimum_at'];lower[i]=r.get('covered_lower_bound',r.get('unresolved_lower_bound',minimum[i]))
            checks.append({'cell':i,**r})
            if r['status'] not in ('negative_witness','all_subtriangles_bounded'):unresolved.append(i)
        bad=np.flatnonzero(minimum < -target)
        return {'minimum':minimum,'minimum_at':where,'covered_lower_bounds':lower,'cubic_checks':checks,
            'negative_cells':bad,'unresolved_cells':unresolved,'enriched_common_cells':len(enriched_cells)}
    if getattr(a,'rigid_bearing_contact',False):
        from rigid_bearing_probe import run as bearing_probe
        return bearing_probe({**locals(),'ROOT':ROOT,'dump':dump})
    frozen_u,frozen_f=cache.reconstruct(external,oldforce,rigid_displacement=R@np.array(seed['rigid']))
    fa=audit(frozen_u);dump(out/'old-tractions-new-space.json',{'minimum_gap_witness_mm':float(fa['minimum'].min()),'negative_cells':len(fa['negative_cells']),
        'unresolved_cells':fa['unresolved_cells'],'old_fixed_tractions_are_not_new_contact_solution':True})
    old=feasible_force_guess(G,loadG,oldforce)['forces'];seen={m['patch']:[] for m in metas}
    for p in points[4:]:seen[p['patch']].append(p['xy'])
    if force_mode:old=None
    history=[];success=False
    for iteration in range(a.max_exchanges):
        start=time.monotonic();S=cache.H.copy();S[np.arange(4),np.arange(4)]+=control['compliance']
        d=qfree-initialgap;d[:4]+=control['adjustment']
        QG,QL=force_equalities(G,loadG,control['targets']) if force_mode else (G,loadG)
        if old is not None:old=np.pad(old,(0,len(points)-len(old)))
        qp=solve_force_qp(S,d,QG,QL,initial=old,tolerance=2e-10,factor_reuse=True,rank_fallback=getattr(a,'rank_fallback','svd'))
        if not qp['passed']:
            dump(out/'failed-qp.json',qp)
            dump(out/'report.json',{'passed':False,'case':case,'load_index':load_index,
                'external_load_scale_over_Epanel_mm2':external_scale,'spring_initial_over_Epanel_mm2':spring_initial,
                'status':'finite_contact_QP_failed','qp_status':qp.get('status'),'history':history,
                'gap_tolerance_mm':target,'no_final_field_qualification':True,
                'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False})
            return False
        lam=np.array(qp['forces']);rigid,actuator=split_coordinates(qp['rigid_mode_coordinates'],R.shape[1],force_control=force_mode)
        u,applied=cache.reconstruct(external,lam,rigid_displacement=R@rigid)
        dump(out/f'qp-{iteration:03d}.json',qp)
        gaps=audit(u);bad=gaps['negative_cells'];success=not len(bad) and not len(gaps['unresolved_cells'])
        row={'exchange':iteration,'contacts':len(points)-4,'negative_cells':len(bad),'unresolved_cells':len(gaps['unresolved_cells']),
            'minimum_witness_mm':float(gaps['minimum'].min()),'minimum_covered_bound_mm':float(gaps['covered_lower_bounds'].min()),'seconds':time.monotonic()-start}
        history.append(row);dump(out/'progress.json',history);print('TRACE_EXCHANGE',row,flush=True)
        np.savez_compressed(out/f'field-{iteration:03d}.npz',u=u,applied=applied,forces=lam,rigid=rigid)
        dump(out/f'gaps-{iteration:03d}.json',gaps)
        if success:break
        if len(gaps['unresolved_cells']):break
        if len(points)>=a.max_points+4:
            break
        selected=select_violations([{'patch':cells[i]['label'],'cell':int(i),'minimum':float(gaps['minimum'][i]),'minimum_at':gaps['minimum_at'][i].tolist()} for i in bad],seen,maximum_new=min(128,a.max_points+4-len(points)))
        if not selected:break
        newpoints=[{'kind':'contact','cell':p['cell'],'patch':p['patch'],'xy':p['minimum_at'],'gap':cells[p['cell']]['gap']} for p in selected]
        nc=hstack([one_map(p) for p in newpoints],format='csc');cache.append(nc);points.extend(newpoints)
        for p in newpoints:seen[p['patch']].append(p['xy'])
        G=np.vstack([G,np.asarray(nc.T@R)]);qfree=np.r_[qfree,np.asarray(nc.T@Uext).ravel()];initialgap=np.r_[initialgap,[p['gap'] for p in newpoints]];old=lam
    checks={};balances=[]
    for name,b,offset in [('panel',P,0),('frame',F,nP)]:
        u0=u[offset:offset+b['N']];ub=u[offset+b['N']:offset+b['N']+b['nb']];f0=applied[offset:offset+b['N']];fb=applied[offset+b['N']:offset+b['N']+b['nb']]
        r0=b['K']@u0+b['A']@ub-f0;rb=b['A'].T@u0+b['B']@ub-fb
        energy=float(u0@(b['K']@u0)+2*u0@(b['A']@ub)+ub@b['B']@ub);work=float(u0@f0+ub@fb)
        residual=float(np.max(abs(r0[b['free']])));bubres=float(np.max(abs(rb)));gauge=float(np.max(abs(r0[b['D']])));err=abs(energy-work)/max(abs(energy),abs(work),1e-20)
        assert residual<1e-9 and bubres<1e-9 and err<1e-5 and (name!='panel' or gauge<1e-9)
        checks[name]={'old_free_residual':residual,'new_trace_residual':bubres,'gauge_or_fixture_reaction':gauge,'energy_work_relative':err,'twice_strain_energy':energy,'maximum_trace_coefficient_mm':float(np.max(abs(ub)))}
    pgap=initialgap[:len(lam)]-np.asarray(cache.C[:,:len(lam)].T@u).ravel();comp=float(np.max(abs(lam[4:]*pgap[4:])));assert comp<1e-11
    success=success and bool(lam[:4].min()>=-1e-10)
    measured_q=np.asarray(cache.C[:,:4].T@u).ravel()
    inferred_adjustment=adjustment_from_state(lam[:4],measured_q,control['compliance'])
    if force_mode:
        assert np.max(abs(lam[:4]-control['targets']))<1e-10
        assert np.max(abs(actuator-inferred_adjustment))<1e-9
    else:assert np.max(abs(inferred_adjustment-control['adjustment']))<1e-9
    installation={'mode':control['mode'],'model_identity':model_identity,
        'compliance_Epanel_over_k_per_mm':control['compliance'].tolist(),
        'target_force_over_Epanel_mm2':control['targets'].tolist() if force_mode else None,
        'assembly_force_over_Epanel_mm2':lam[:4].tolist(),'assembly_separation_mm':measured_q.tolist(),
        'adjustment_mm':inferred_adjustment.tolist() if force_mode else control['adjustment'].tolist(),
        'actuator_multipliers_mm':actuator.tolist(),'additional_equations_are_force_controls_not_displacement_supports':force_mode,
        'physical_measurement':False,'prescribed_pressure_weighted_connector_not_resolved_head_contact':True}

    dump(out/'report.json',{'base_main':BASE,'passed':success,'case':case,'face_per_patch_body':a.faces_per_patch,'selected_faces':selection,
        'old_volume_level':2,'new_trace_dofs':P['nb']+F['nb'],'audited_common_regions':5255,'enriched_common_regions':len(enriched_cells),'gap_tolerance_mm':target,'load_index':load_index,'spring_initial_over_Epanel_mm2':spring_initial,
        'external_load_scale_over_Epanel_mm2':external_scale,'unloaded_assembly_reference':external_scale==0,
        'initial_spring_force_not_equilibrated_installed_preload':True,'installation_control':installation,
        'frozen_selection_sha256':sha256(frozen_path) if frozen_path is not None else None,
        'history':history,'contact_points':points[:len(lam)],'forces':lam,'rigid':rigid,'full_condensed_checks':checks,'complementarity_max':comp,
        'rank_fallback':getattr(a,'rank_fallback','svd'),'minimum_bolt_force_over_E':float(lam[:4].min()),'input_sha256':hashes,'source_sha256':sha256(__file__),
        'not_full_P3_or_all_interface_refinement':True,'old_discrete_nodal_load_functionals_preserved':load_mode=='discrete',
        'continuous_load_projection_not_claimed':load_mode=='discrete',
        'surface_load_archive':str(surface.root) if surface is not None else None,'surface_load_mode':load_mode,
        'load_face_cap':getattr(a,'load_face_cap',0),'surface_integration_scope':'declared planar polygon and affine research density; not actual measured traction',
        'load_map_change_not_mesh_convergence':surface is not None,
        'full_private_interior_recovery_still_required':True,'independent_mixed_element_full_field_audit_still_required':True,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False})
    np.savez_compressed(out/'full-fields.npz',up=u[:npanel],bp=u[npanel:nP],uf=u[nP:nP+nframe],bf=u[nP+nframe:],load=applied,forces=lam,rigid=rigid)
    for p,h in hashes.items():assert sha256(p)==h
    print('TRACE_PROBE_TERMINAL',success,flush=True)
    return success

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--volume',type=Path,required=True);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--faces-per-patch',type=int,default=2);p.add_argument('--max-exchanges',type=int,default=30);p.add_argument('--max-points',type=int,default=5500)
    p.add_argument('--surface-loads',type=Path);p.add_argument('--surface-load-mode',choices=('discrete','consistent'),default='discrete');p.add_argument('--load-face-cap',type=int,default=0)
    p.add_argument('--case',type=int,default=6);p.add_argument('--gap-tolerance',type=float,default=TOL);p.add_argument('--frozen-selection',type=Path)
    p.add_argument('--rank-fallback',choices=('svd','qr','qr_pivot'),default='svd')
    p.add_argument('--external-load-scale',type=float,default=None)
    p.add_argument('--installation-control',type=Path)
    p.add_argument('--rigid-bearing-contact',action='store_true')
    a=p.parse_args();assert 1<=a.faces_per_patch<=4 and a.max_exchanges>0 and a.max_points>=4000 and 0<=a.load_face_cap<=4
    raise SystemExit(0 if run(a) else 1)
