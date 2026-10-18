"""Optional original-body rigid-bearing comparison, using the existing exact oracle.

Replaces prescribed head/nut pressure functionals with unknown unilateral point
reactions and eight free normal/tilt planes. The frame fixture remains unchanged.
Only zero-external-load, simultaneous force-controlled installation is covered.
"""
from pathlib import Path
import json,time
import numpy as np
from scipy.sparse import csc_matrix,hstack,save_npz
from contact_exchange import ExactResponseCache,QuadraticGapBatch,select_violations,sha256
from contact_patch_audit import triangle_coefficients,evaluate
from cubic_trace_gap import audit_polygon
from surface_load_functional import shape_values
from bearing_contact import equilibrium_map,split_coordinates,axial_adjustment,resultants,bearing_id,plane_basis,bearing_coefficients
from installation_control import force_equalities
from contact_dual_active import solve_force_qp

def run(ctx):
    a=ctx['a'];out=ctx['out'];root=ctx['ROOT'];dump=ctx['dump'];target=ctx['target']
    if not ctx['force_mode'] or ctx['external_scale']!=0 or ctx['load_mode']!='consistent':
        raise ValueError('rigid bearing comparison requires explicit unloaded force targets and consistent external loads')
    pbody=ctx['P'];fbody=ctx['F'];bodies={'panel':pbody,'frame':fbody};nP=ctx['nP'];n=ctx['n'];R=ctx['R']
    points=[dict(p) for p in ctx['points']];old_count=len(points);hashes=dict(ctx['hashes'])
    for rel in ['integration/bearing_contact.py','engineering/trace-enrichment-20261017/rigid_bearing_probe.py']:
        hashes[str(root/rel)]=sha256(root/rel)
    faces=[];centers=np.empty((4,2));bybearing={k:[] for k in range(8)}
    for body in ['panel','frame']:
        source=ctx['surface'].root/(body+'-faces.json');hashes[str(source)]=sha256(source)
        br=bodies[body];offset=0 if body=='panel' else nP
        for raw in json.loads(source.read_text()):
            if raw['kind']!='C':continue
            assert raw['axis']==2 and raw['direction']==([0,0,-1] if body=='panel' else [0,0,1])
            center=np.array(raw['density_target']);idx=raw['index'];bi=bearing_id(body,idx);centers[idx]=center
            face=dict(raw);face.update(body=body,bearing=bi,offset=offset,normal_sign=(-1 if body=='panel' else 1),trace_index=br['lookup'].get(tuple(sorted(raw['vertices']))))
            face['origin']=center;face['label']='bearing_'+body+'_'+str(idx);bybearing[bi].append(len(faces));faces.append(face)
    assert len(faces)>0 and all(bybearing.values());dump(out/'bearing-domains.json',faces)
    def descriptor(fi,xy):
        f=faces[fi];return {'kind':'bearing','body':f['body'],'index':f['index'],'face':fi,'patch':f['label'],'xy':list(map(float,xy)),'gap':0.}
    def one_map(p):
        if p['kind']=='bolt':return csc_matrix((n,1))
        if p['kind']=='contact':return ctx['one_map'](p)
        f=faces[p['face']];assert p['body']==f['body'] and p['index']==f['index'] and p['patch']==f['label']
        br=bodies[f['body']];w=shape_values(f['triangle_xy'],[p['xy']])[0];ids=list(f['offset']+np.asarray(f['dofs']));vals=list(f['normal_sign']*w[:6])
        if f['trace_index'] is not None:ids.append(f['offset']+br['N']+3*f['trace_index']+2);vals.append(f['normal_sign']*w[6])
        return csc_matrix((vals,(ids,np.zeros(len(ids),dtype=int))),shape=(n,1))
    # Preserve the exact member-contact block; remove old prescribed bolt columns.
    old=ctx['cache'];C=hstack((csc_matrix((n,4)),old.C[:,4:]),format='csc');H=old.H.copy();H[:4,:]=0.;H[:,:4]=0.
    identity={**old.identity,'bearing_model':'eight free rigid planes, axial-only bolts','bearing_domains':sha256(out/'bearing-domains.json')}
    cache=ExactResponseCache(n,ctx['response'],identity,response_block=ctx['response'],response_batch_size=8)
    check=cache.restore(C,H,identity,probes=5)
    seen={p['patch']:[] for p in points[4:]}
    for p in points[4:]:seen[p['patch']].append(p['xy'])
    new=[]
    for bi,fis in bybearing.items():
        vertices=[(fi,np.array(v)) for fi in fis for v in faces[fi]['polygon']]
        for angle in np.arange(12)*2*np.pi/12:
            direction=np.array([np.cos(angle),np.sin(angle)]);fi,xy=max(vertices,key=lambda z:float(z[1]@direction))
            label=faces[fi]['label'];seen.setdefault(label,[])
            if not any(np.linalg.norm(xy-np.array(q))<1e-10 for q in seen[label]):new.append(descriptor(fi,xy));seen[label].append(xy.tolist())
    cache.append(hstack([one_map(p) for p in new],format='csc'));points.extend(new)
    dump(out/'bearing-initialization.json',{'old_member_contact_columns':old_count-4,'new_bearing_seed_points':len(new),'prescribed_pressure_columns_removed':4,'exact_body_response_check':vars(check),'rigid_bearing_tilts_free':True,'shaft_bending_torsion_shear_absent':True,'frame_fixture_unchanged':True})
    qb=QuadraticGapBatch([f['polygon'] for f in faces],[f['origin'] for f in faces])
    def surface_values(fi,u,xy):
        f=faces[fi];br=bodies[f['body']];w=shape_values(f['triangle_xy'],xy);v=w[:,:6]@u[f['offset']+np.array(f['dofs'])]
        if f['trace_index'] is not None:v+=w[:,6]*u[f['offset']+br['N']+3*f['trace_index']+2]
        return v
    def bearing_audit(u,planes):
        coef=[]
        for f in faces:
            d=u[f['offset']+np.array(f['dofs'])];c=-f['normal_sign']*bearing_coefficients(f['triangle_xy'],d,f['origin']);c[:3]-=planes[f['bearing']];coef.append(c)
        z=qb.extrema(coef);minimum=z['minimum'].copy();where=z['minimum_at'].copy();lower=minimum.copy();unresolved=[];cubic=[]
        for i,f in enumerate(faces):
            if f['trace_index'] is None:continue
            def value(xy):return -f['normal_sign']*surface_values(i,u,xy)-plane_basis(xy,f['origin'])@planes[f['bearing']]
            r=audit_polygon(f['polygon'],value,gap_tolerance=target);minimum[i]=r['minimum_witness'];where[i]=r['minimum_at'];lower[i]=r.get('covered_lower_bound',r.get('unresolved_lower_bound',minimum[i]));cubic.append({'face':i,**r})
            if r['status'] not in ('negative_witness','all_subtriangles_bounded'):unresolved.append(i)
        return {'minimum':minimum,'minimum_at':where,'covered_lower_bounds':lower,'negative_cells':np.flatnonzero(minimum < -target),'unresolved_cells':unresolved,'cubic_checks':cubic}
    external=ctx['external'];Uext=ctx['Uext'];control=ctx['control'];history=[];guess=None;success=False
    for iteration in range(a.max_exchanges):
        start=time.monotonic();physical=np.asarray(cache.C.T@R);G=equilibrium_map(physical,points,centers);load=np.r_[ctx['loadG'],np.zeros(24)]
        eq,rhs=force_equalities(G,load,control['targets']);S=cache.H.copy();S[np.arange(4),np.arange(4)]+=control['compliance']
        gap0=np.array([p.get('gap',0.) for p in points]);d=np.asarray(cache.C.T@Uext).ravel()-gap0
        if guess is not None:guess=np.pad(guess,(0,len(points)-len(guess)))
        qp=solve_force_qp(S,d,eq,rhs,initial=guess,tolerance=2e-10,factor_reuse=True,rank_fallback=a.rank_fallback)
        dump(out/f'bearing-qp-{iteration:03d}.json',qp)
        if not qp['passed']:dump(out/'bearing-report.json',{'passed':False,'status':'finite_bearing_QP_failed','history':history,'qp_status':qp.get('status')});return False
        lam=np.array(qp['forces']);z=np.array(qp['rigid_mode_coordinates']);rigid,planes=split_coordinates(z[:-4],R.shape[1]);actuator=z[-4:]
        u,applied=cache.reconstruct(external,lam,rigid_displacement=R@rigid);bodygap=ctx['audit'](u);bg=bearing_audit(u,planes)
        success=not len(bodygap['negative_cells']) and not len(bg['negative_cells']) and not bodygap['unresolved_cells'] and not bg['unresolved_cells']
        row={'exchange':iteration,'body_contacts':sum(p['kind']=='contact' for p in points),'bearing_contacts':sum(p['kind']=='bearing' for p in points),'body_negative':len(bodygap['negative_cells']),'bearing_negative':len(bg['negative_cells']),'unresolved':len(bodygap['unresolved_cells'])+len(bg['unresolved_cells']),'body_bound':float(bodygap['covered_lower_bounds'].min()),'bearing_bound':float(bg['covered_lower_bounds'].min()),'seconds':time.monotonic()-start}
        history.append(row);dump(out/'bearing-progress.json',history);dump(out/f'bearing-gaps-{iteration:03d}.json',bg);dump(out/f'body-gaps-{iteration:03d}.json',bodygap)
        np.savez_compressed(out/f'bearing-field-{iteration:03d}.npz',u=u,applied=applied,forces=lam,rigid=rigid,planes=planes,actuator=actuator)
        print('BEARING_EXCHANGE',row,flush=True)
        if success or row['unresolved'] or len(points)>=a.max_points+4:break
        violations=[]
        for i in bodygap['negative_cells']:violations.append({'patch':ctx['cells'][i]['label'],'cell':int(i),'minimum':float(bodygap['minimum'][i]),'minimum_at':bodygap['minimum_at'][i].tolist()})
        shift=len(ctx['cells'])
        for i in bg['negative_cells']:violations.append({'patch':faces[i]['label'],'cell':int(i)+shift,'minimum':float(bg['minimum'][i]),'minimum_at':bg['minimum_at'][i].tolist()})
        chosen=select_violations(violations,seen,maximum_new=min(128,a.max_points+4-len(points)));new=[]
        for q in chosen:
            i=q['cell']
            if i>=shift:new.append(descriptor(i-shift,q['minimum_at']))
            else:new.append({'kind':'contact','cell':i,'patch':q['patch'],'xy':q['minimum_at'],'gap':ctx['cells'][i]['gap']})
        if not new:break
        cache.append(hstack([one_map(p) for p in new],format='csc'));points.extend(new)
        for p in new:seen[p['patch']].append(p['xy'])
        guess=lam.copy()
    # Do not conceal untested whole-field assumptions with a pass flag.
    loads=cache.C[:,:len(lam)]@lam;assert np.max(abs(applied-(external-loads)))<1e-12
    equilibrium=resultants(lam,points[:len(lam)],centers);forceerror=np.max(abs(equilibrium[:,0]-np.tile(lam[:4],2)));momenterror=np.max(abs(equilibrium[:,1:]))
    delta=axial_adjustment(lam[:4],control['compliance'],planes);assert np.max(abs(delta-actuator))<1e-8
    cg=gap0[:len(lam)]-np.asarray(cache.C[:,:len(lam)].T@u).ravel()-G[:len(lam),R.shape[1]:]@planes.ravel();comp=float(np.max(abs(lam[4:]*cg[4:])))
    assert forceerror<1e-10 and momenterror<1e-10 and comp<1e-11
    checks={}
    for name,b,offset in [('panel',pbody,0),('frame',fbody,nP)]:
        uu=u[offset:offset+b['N']];bb=u[offset+b['N']:offset+b['N']+b['nb']];f=applied[offset:offset+b['N']];fb=applied[offset+b['N']:offset+b['N']+b['nb']]
        rr=b['K']@uu+b['A']@bb-f;rb=b['A'].T@uu+b['B']@bb-fb;en=float(uu@(b['K']@uu)+2*uu@(b['A']@bb)+bb@b['B']@bb);work=float(uu@f+bb@fb)
        assert np.max(abs(rr[b['free']]))<1e-9 and np.max(abs(rb))<1e-9 and abs(en-work)<1e-5*max(abs(en),abs(work),1e-20)
        checks[name]={'free_residual':float(np.max(abs(rr[b['free']]))),'new_residual':float(np.max(abs(rb))),'gauge_or_fixture':float(np.max(abs(rr[b['D']]))),'twice_energy':en}
        if name=='panel':assert checks[name]['gauge_or_fixture']<1e-9
    dump(out/'bearing-report.json',{'passed':bool(success),'history':history,'target_mm':target,'case':ctx['case'],'external_scale':ctx['external_scale'],'selected_faces':len(ctx['selection']),'trace_coefficients':pbody['nb']+fbody['nb'],'body_regions':5255,'bearing_regions':len(faces),'points':points[:len(lam)],'centers':centers,'planes':planes,'rigid':rigid,'forces':lam,'adjustment':delta,'actuator':actuator,'target_forces':control['targets'],'compliance':control['compliance'],'bearing_resultants':equilibrium,'bearing_force_error':float(forceerror),'bearing_moment_error':float(momenterror),'complementarity':comp,'full_condensed_checks':checks,'input_sha256':hashes,'source_sha256':sha256(__file__),'ideal_rigid_frictionless_head_nut_and_axial_only_bolt':True,'pressure_not_prescribed':True,'frame_fixture_unchanged':True,'independent_audit_still_required':True,'hardware_or_actual_preload_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False})
    np.savez_compressed(out/'bearing-full-fields.npz',up=u[:ctx['npanel']],bp=u[ctx['npanel']:nP],uf=u[nP:nP+ctx['nframe']],bf=u[nP+ctx['nframe']:],load=applied,forces=lam,rigid=rigid,planes=planes)
    for path,h in hashes.items():assert sha256(path)==h
    print('RIGID_BEARING_TERMINAL',success,flush=True);return bool(success)
