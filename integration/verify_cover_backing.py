"""Builder-free STEP verification of the panel-backed guide cover.

A normal-only unit-wrench equilibrium is a geometric load-path diagnostic,
NOT load capacity or stiffness. The panel is held fixed in these checks.
Existing detached-panel insertion assumptions are retained explicitly.
"""
from pathlib import Path
import argparse
import itertools
import json
import math
import sys
import numpy as np
from scipy.optimize import linprog
import cadquery as cq
import verify_pawl_box_guide as w
import verify_endpoint_joint_pawl as e
v=w.v
TOL=v.TOL


def backing_blocks():
    return {s+'_BACK_'+str(i):v.single(v.hand(v.box((17.43,a,.5),(18.43,b,7.0)),s))
            for s in 'LR' for i,(a,b) in enumerate(((18.3,19.5),(22.35,23.8)))}


def scene(parts,parent,prior,old,profiles,slots,slide=0.,descent=0.,u=0.,cover_shift=0.,pawl_shift=0.):
    p=e.scene(parts,parent,prior,old,profiles,slots,slide,descent,(u,u))
    for s in 'LR':
        sign=-1 if s=='L' else 1
        p[s+'_ROOT_INNER']=parts[s+'_ROOT_INNER']
        p[s+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=parts[s+'_ROOT_OUTER']
        p[s+'_OLD_COVER']=parts[s+'_OLD_COVER'].translate((sign*cover_shift,0,0))
        if pawl_shift:
            for r in ('PAWL','SHOULDER_PIN_NOMINAL'):p[s+'_'+r]=p[s+'_'+r].translate((sign*pawl_shift,0,0))
    if len(p)!=79:raise ValueError('complete 79-part scene required')
    return p


def planar_contacts(cover,neighbors):
    result=[]
    for name,body in sorted(neighbors.items()):
        if cover.distance(body)>1e-6:continue
        for fi,face in enumerate(cover.Faces()):
            if face.geomType()!='PLANE':continue
            normal=np.asarray(face.normalAt().toTuple());point=np.asarray(face.Center().toTuple())
            for gi,other in enumerate(body.Faces()):
                if other.geomType()!='PLANE':continue
                n2=np.asarray(other.normalAt().toTuple());p2=np.asarray(other.Center().toTuple())
                if np.dot(normal,n2)>-.999999 or abs(np.dot(normal,p2-point))>1e-6:continue
                for patch in face.intersect(other).Faces():
                    if patch.Area()<=1e-8:continue
                    bb=patch.BoundingBox()
                    points=[patch.Center().toTuple()]+[p.Center().toTuple() for p in patch.Vertices()]
                    result.append({'neighbor':name,'cover_face':fi,'neighbor_face':gi,'area_mm2':patch.Area(),
                        'normal_into_cover':(-normal).tolist(),'points_mm':points,
                        'bounds_mm':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]})
    return result


def equilibrium(contacts,center,force,point):
    center=np.asarray(center,dtype=float);force=np.asarray(force,dtype=float);point=np.asarray(point,dtype=float)
    if any(x.shape!=(3,) or not np.isfinite(x).all() for x in (center,force,point)):
        raise ValueError('finite three-dimensional wrench data required')
    columns=[]
    for row in contacts:
        n=np.asarray(row['normal_into_cover'],dtype=float)
        if n.shape!=(3,) or not np.isfinite(n).all() or abs(np.linalg.norm(n)-1)>1e-6:raise ValueError('unit contact normal required')
        for p in row['points_mm']:
            p=np.asarray(p,dtype=float)
            if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('finite contact point required')
            columns.append(np.r_[n,np.cross(p-center,n)])
    external=np.r_[force,np.cross(point-center,force)]
    if not columns:return {'feasible':False,'normal_rays':0,'external_wrench_N_Nmm':external.tolist()}
    matrix=np.array(columns).T
    fit=linprog(np.ones(len(columns)),A_eq=matrix,b_eq=-external,bounds=(0,None),method='highs')
    if fit.status not in (0,2):raise ValueError('equilibrium solver did not resolve feasibility')
    r={'feasible':bool(fit.success),'normal_rays':len(columns),'solver_status':int(fit.status),
       'external_wrench_N_Nmm':external.tolist(),'one_newton_is_basis_not_rating':True}
    if fit.success:
        residual=float(np.max(np.abs(matrix@fit.x+external)))
        if residual>1e-8 or min(fit.x)<-1e-8:raise ValueError('invalid compressive equilibrium certificate')
        r.update({'coefficients_N':fit.x.tolist(),'residual':residual,'sum_coefficients_N':float(sum(fit.x))})
    return r


def verify(baseline,manifest,output,*,full=False):
    output=Path(output)
    if output.exists():raise ValueError('new report path required')
    _,base,h=w.w.load_new(baseline);meta,new,h2=w.w.load_new(manifest);h.update(h2)
    if meta['baseline_manifest_sha256']!=v.sha(baseline):raise ValueError('wrong baseline identity')
    panel=base['A_BACK_PANEL'];blocks=backing_blocks();joins=[]
    for name,b in blocks.items():
        overlap=v.common(b,base['A_BACK_PANEL'])
        if overlap<=TOL:raise ValueError('disconnected panel backing')
        joins.append({'post':name,'overlap_with_original_panel_mm3':overlap})
        panel=v.single(panel.fuse(b).clean())
    v.equal(panel,new['A_BACK_PANEL'])
    for name in set(base)-{'A_BACK_PANEL'}:v.equal(base[name],new[name])
    removed=v.vol(base['A_BACK_PANEL'].cut(panel));added=v.vol(panel.cut(base['A_BACK_PANEL']))
    if removed>TOL or abs(added-33.655)>1e-6:raise ValueError('unexpected fixed post material')
    probes=[];forces=[];old_forces=[]
    for s in 'LR':
        sign=-1 if s=='L' else 1;cover=new[s+'_OLD_COVER']
        for d in (0.,.02,.03,.05):
            moved=cover.translate((sign*d,0,0));current=v.common(moved,panel);old_hit=v.common(moved,base['A_BACK_PANEL'])
            distance=moved.distance(panel)
            if old_hit>TOL or (d<=.02 and current>TOL) or (d>.02 and current<=TOL):raise ValueError('cover stop or retained old escape witness differs')
            if d==.02 and distance>1e-6:raise ValueError('nominal cover stop not reached')
            probes.append({'side':s,'outward_mm':d,'new_panel_common_mm3':current,'old_panel_common_mm3':old_hit,'distance_mm':distance})
        moved=cover.translate((sign*.02,0,0));patches=planar_contacts(moved,{'A_BACK_PANEL':panel})
        if len(patches)!=4 or any(row['normal_into_cover'][0]*sign>-.999999 for row in patches):raise ValueError('actual inward reacting contact patches missing')
        for y,z in ((20.15,5.5),(18.65,5.5),(21.65,5.5)):
            fit=equilibrium(patches,moved.Center().toTuple(),(sign,0,0),(sign*16.67,y,z))
            if not fit['feasible']:raise ValueError('post contacts cannot balance selected outward unit wrench')
            forces.append({'side':s,'point_yz_mm':[y,z],'actual_contact_patches':patches,'unit_normal_diagnostic':fit})
        before=planar_contacts(cover,{s+'_ROOT_INNER':base[s+'_ROOT_INNER'],s+'_ROOT_OUTER':base[s+'_ROOT_OUTER'],'A_BACK_PANEL':base['A_BACK_PANEL']})
        fit=equilibrium(before,cover.Center().toTuple(),(sign,0,0),(sign*16.65,20.15,5.5))
        if fit['feasible']:raise ValueError('old missing holding path counterexample lost')
        old_forces.append({'side':s,'contacts':before,'unit_normal_diagnostic':fit})
    print('POSTS',len(blocks),'COVER_PROBES',len(probes),'UNIT_WRENCHES',len(forces),flush=True)
    integration={};failures=[]
    if full:
        parent,prior,old,profiles=e.v.parent_native(h);slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
        selected={'A_BACK_PANEL'}|{s+'_'+r for s in 'LR' for r in ('OLD_COVER','PAWL','SHOULDER_PIN_NOMINAL')}
        cases=[(0,0,0,0,0),(0,0,3,0,0),(40,0,3,0,0),(79.75,8.2,3,0,0),
               (0,0,0,.02,.07),(0,0,3,.02,.07),(40,0,3,.02,.07),(79.75,8.2,3,.02,.07)]
        states=[]
        for i,args in enumerate(cases):
            p=scene(new,parent,prior,old,profiles,slots,*args);rows=e.v.w.pairs(p,None if i==0 else selected)
            bad=[r for r in rows if r['common_mm3']>TOL];failures.extend(bad)
            states.append({'coordinates_slide_descent_u_cover_PAWL':args,'participants':79,'pairs':rows,'bad':bad})
            print('SCENE',i,len(rows),'BAD',bad,flush=True)
            if i==0:home=p
        # Compare old complete escape with new complete take-up using all neighbors.
        paths=[]
        for s in 'LR':
            sign=-1 if s=='L' else 1;key=s+'_OLD_COVER'
            for label,shift,bodypanel in [('old_escape',.05,base['A_BACK_PANEL']),('new_takeup',.02,panel)]:
                fixed={k:b for k,b in home.items() if k!=key};fixed['A_BACK_PANEL']=bodypanel
                row=e.v.motion(key,home[key],(sign*shift,0,0),fixed);row['case']=label
                paths.append(row);failures.extend(row['failed'])
        # Existing detached-panel insertions, now including the monolithic backing.
        detachable={s+'_'+r for s in 'LR' for r in e.v.INSERT_ROLES}
        installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}}
        prior_service=e.frozen(h);assembly=[]
        for s in 'LR':
            for name,move in e.v.plan(s):
                if name.endswith('_ROOF'):
                    kept=v.single(prior_service[name].cut(w.relief(s)).clean())
                    row=e.roof_motion_partition(name,home[name],kept,move,installed)
                else:row=e.v.motion(name,home[name],move,installed)
                assembly.append(row);failures.extend(row['failed']);installed[name]=home[name]
                print('ASSEMBLY',name,'BAD',len(row['failed']),flush=True)
        # New material must not block the old cartridge's top-admission subset.
        # Do not claim the whole cartridge can drop into the old captured KEY guide.
        changed_paths=[]
        for s in 'LR':
            for role in sorted(e.v.w.v.PARTS):
                key=s+'_'+role
                row=e.v.motion(key,home[key],(0,0,12.),blocks)
                changed_paths.append(row);failures.extend(row['failed'])
        frame=e.v.motion('A_FRAME',home['A_FRAME'],(0,0,12.),blocks)
        failures.extend(frame['failed'])
        stop_paths=[]
        for s in 'LR':
            sign=-1 if s=='L' else 1
            for i in (0,1):
                profile=profiles[s][i];delta=profile.lower_stop_height-profile.floor_height-profile.pin_radius
                row=e.v.motion(s+'_STOP_'+str(i),old[f'{s}_STOP_{i}'],(sign*delta,0,0),blocks)
                stop_paths.append(row);failures.extend(row['failed'])
        outside=v.vol(panel.cut(old['A_OUTER']))
        if outside>TOL:failures.append({'new_panel_outside_A_mm3':outside})
        integration={'states':states,'complete_cover_paths':paths,'detached_panel_control_insertions':assembly,
            'original_cartridge_against_new_material_only':changed_paths,'frame_against_new_material':frame,
            'STOP_against_new_material':stop_paths,'new_panel_outside_A_mm3':outside,
            'full_upstream_cartridge_assembly_not_proved':True}
    if any(v.sha(p)!=value for p,value in h.items()):raise ValueError('input changed during readback')
    if 'cover_backing' in sys.modules:raise ValueError('candidate builder imported')
    r={'source_sha256':meta['source_sha256'],'reader_sha256':v.sha(__file__),'input_sha256':h,'templates':25,'unchanged_templates':24,
       'material':{'removed_mm3':removed,'added_mm3':added,'connections':joins},'cover_shift_probes':probes,
       'at_stop_normal_load_diagnostics':forces,'old_normal_load_rejections':old_forces,'integration':integration,
       'failure_pairs':failures,'passed':not failures,'pass_scope':'nominal one-piece backing and explicit conditional paths, no structural or tolerance qualification',
       'same_CAD_kernel':True,'candidate_builder_imported':False,'nominal_cover_takeup_mm':.02,
       'nominal_inboard_PAWL_limit_mm':-.05,'nominal_outboard_PAWL_limit_at_cover_stop_mm':.07,
       'old_fixed_cover_plus0p05_limit_not_reused':True,'panel_ground_constraint_is_assumed':True,
       'actual_panel_anchor_thread_preload_stiffness_force_process_qualified':False,
       'whole_upstream_assembly_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with output.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print('COVER_BACKING_RESULT',r['passed'],flush=True);return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true')
    a=p.parse_args();r=verify(a.baseline,a.manifest,a.output,full=a.full);raise SystemExit(0 if r['passed'] else 1)
