"""Builder-free native verification of low panel/frame bearing keys.

Whole rigid A-deck shifts preserve internal relative transforms. Recheck every
73-by-6 moving/fixed pair rather than holding the panel artificially grounded.
The frame and its four screws are still assumed fixed; unit equilibria do not
certify threads, preload, strength, finite-rotation capture or physical motion.
"""
from pathlib import Path
import argparse
import json
import math
import sys
import cadquery as cq
import verify_cover_backing as w
v=w.v
e=w.e
TOL=v.TOL
ROOT=Path(__file__).resolve().parents[1]


def key_blocks():
    return {s:v.single(v.hand(v.box((35.70,16.5,.50),(36.325,24.,2.)),s)) for s in 'LR'}


def groups(parts):
    fixed={k:b for k,b in parts.items() if k in ('A_FRAME','B_SHELL') or k.startswith('FRAME_')}
    moving={k:b for k,b in parts.items() if k not in fixed}
    if len(parts)!=79 or len(fixed)!=6 or len(moving)!=73:raise ValueError('unexpected deck partition')
    return moving,fixed


def cross_pairs(moving,fixed):
    return [{'moving':name,'fixed':other,'common_mm3':v.common(body,ob)}
            for name,body in sorted(moving.items()) for other,ob in sorted(fixed.items())]


def shift_deck(parts,dx):
    if type(dx) not in (int,float) or not math.isfinite(dx) or abs(dx)>.020000001:
        raise ValueError('outside explicit finite deck-shift family')
    moving,fixed=groups(parts)
    return {k:b.translate((dx,0,0)) for k,b in moving.items()},fixed


def frame_planes(frame):
    records=[]
    for side in 'LR':
        sign=-1 if side=='L' else 1;x=sign*36.345;matches=[]
        for face in frame.Faces():
            if face.geomType()!='PLANE':continue
            b=face.BoundingBox();n=face.normalAt()
            if max(abs(b.xmin-x),abs(b.xmax-x),abs(n.x+sign),abs(n.y),abs(n.z))>1e-6:continue
            if b.ymin>16.5+TOL or b.ymax<24.-TOL or b.zmin>.65+TOL or b.zmax<2.-TOL:continue
            matches.append({'area_mm2':face.Area(),'normal':n.toTuple(),'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]})
        if len(matches)!=1:raise ValueError('unique finite frame receiving plane missing')
        records.append({'side':side,'plane':matches[0]})
    return records


def reaction_by_part(patches,fit):
    if not fit['feasible']:return {}
    coefficients=fit['coefficients_N'];index=0;totals={}
    for patch in patches:
        count=len(patch['points_mm']);load=sum(coefficients[index:index+count]);index+=count
        name=patch['neighbor'];normal=patch['normal_into_cover']
        old=totals.setdefault(name,[0.,0.,0.])
        for i in range(3):old[i]+=load*normal[i]
    if index!=len(coefficients):raise ValueError('reaction indexing differs')
    return totals


def verify(baseline,manifest,output,*,full=False):
    out=Path(output)
    if out.exists():raise ValueError('new report path required')
    bm,base,h=w.w.w.load_new(baseline);meta,new,h2=w.w.w.load_new(manifest);h.update(h2)
    if meta['baseline_manifest_sha256']!=v.sha(baseline):raise ValueError('wrong baseline binding')
    if bm['source_sha256']!=v.sha(ROOT/'integration/cover_backing.py'):raise ValueError('not current backing source')
    blocks=key_blocks();panel=base['A_BACK_PANEL'];joins=[]
    for side,block in blocks.items():
        overlap=v.common(block,base['A_BACK_PANEL'])
        if abs(overlap-.703125)>1e-7:raise ValueError('native key/panel join differs')
        panel=v.single(panel.fuse(block).clean());joins.append({'side':side,'join_mm3':overlap})
    v.equal(panel,new['A_BACK_PANEL'])
    for key in set(base)-{'A_BACK_PANEL'}:v.equal(base[key],new[key])
    loss=v.vol(base['A_BACK_PANEL'].cut(panel));gain=v.vol(panel.cut(base['A_BACK_PANEL']))
    if loss>TOL or abs(gain-12.65625)>1e-6:raise ValueError('new key material differs')
    parent,prior,old,profiles=e.v.parent_native(h);slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
    home=w.scene(new,parent,prior,old,profiles,slots)
    planes=frame_planes(home['A_FRAME']);frame=home['A_FRAME'];probes=[];forces=[];contacts=[]
    for dx in (-.05,-.03,-.02,0.,.02,.03,.05):
        shifted=panel.translate((dx,0,0));old_hit=v.common(base['A_BACK_PANEL'].translate((dx,0,0)),frame)
        hit=v.common(shifted,frame);distance=shifted.distance(frame);within=abs(dx)<=.02
        if old_hit>TOL or (within and hit>TOL) or (not within and hit<=TOL):raise ValueError('old gap or new stop witness differs')
        if abs(dx)==.02 and distance>1e-6:raise ValueError('frame contact not reached')
        probes.append({'deck_dx_mm':dx,'old_panel_frame_mm3':old_hit,'new_panel_frame_mm3':hit,'distance_mm':distance})
        if abs(dx)!=.02:continue
        _,fixed=groups(home);support={k:b for k,b in fixed.items() if k!='B_SHELL'}
        patches=w.planar_contacts(shifted,support);sign=1 if dx>0 else -1
        if not any(r['neighbor']=='A_FRAME' and r['normal_into_cover'][0]*sign<-.999999 for r in patches):
            raise ValueError('actual inward frame reaction plane missing')
        contacts.append({'dx_mm':dx,'patches':patches})
        for y in (18.65,20.15,21.65):
            point=(sign*17.43+dx,y,5.5);force=(sign,0.,0.)
            fit=w.equilibrium(patches,shifted.Center().toTuple(),force,point)
            frame_only=w.equilibrium([r for r in patches if r['neighbor']=='A_FRAME'],shifted.Center().toTuple(),force,point)
            if not fit['feasible']:raise ValueError('selected full-support unit equilibrium failed')
            forces.append({'deck_dx_mm':dx,'point_mm':point,'fixed_frame_and_screws':fit,'fixed_frame_only':frame_only,
                           'one_feasible_reaction_by_part_N':reaction_by_part(patches,fit),
                           'not_unique_or_stiffness_resolved_load_sharing':True})
    if v.vol(panel.cut(old['A_OUTER']))>TOL:raise ValueError('panel keys exceed original study envelope')
    admission=[]
    for side,block in blocks.items():
        actual=block.cut(base['A_BACK_PANEL']);expected=v.hand(v.box((35.70,16.5,.65),(36.325,24.,2.)),side)
        v.equal(actual,expected)
        sweep=v.hand(v.box((35.70,16.5,.65-12.),(36.325,24.,2.)),side)
        hit=v.common(sweep,frame)
        if hit>TOL:raise ValueError('exact new material blocks full frame admission')
        admission.append({'side':side,'relative_full_Z_mm':-12.,'new_material_frame_common_mm3':hit})
    print('NATIVE_KEYS',2,'CONTACT_PROBES',len(probes),'UNIT_WRENCHES',len(forces),flush=True)
    integration={};failures=[]
    if full:
        centers=[];translated=[];paths=[];allstates={};selected={'A_BACK_PANEL'}|{s+'_'+r for s in 'LR' for r in ('OLD_COVER','PAWL','SHOULDER_PIN_NOMINAL')}
        cases=[(s,d,u,c,p) for s,d,u in ((0.,0.,0.),(0.,0.,3.),(40.,0.,3.),(79.75,8.2,3.)) for c,p in ((0.,0.),(.02,.07))]
        for index,args in enumerate(cases):
            scene=w.scene(new,parent,prior,old,profiles,slots,*args);allstates[index]=scene
            pairs=e.v.w.pairs(scene,None if index==0 else selected);bad=[r for r in pairs if r['common_mm3']>TOL]
            failures+=bad;centers.append({'arguments_slide_descent_u_cover_pawl':args,'participants':79,'pairs':pairs,'bad':bad})
            print('CENTER_STATE',index,'PAIRS',len(pairs),'BAD',bad,flush=True)
            for dx in (-.02,.02):
                moving,fixed=shift_deck(scene,dx);rows=cross_pairs(moving,fixed);bad=[r for r in rows if r['common_mm3']>TOL]
                failures+=bad;translated.append({'arguments_slide_descent_u_cover_pawl':args,'deck_dx_mm':dx,
                    'moving_participants':73,'fixed_participants':6,'internal_pairs_rigidly_unchanged':True,'pairs':rows,'bad':bad})
                print('DECK_STATE',index,dx,'PAIRS',len(rows),'BAD',bad,flush=True)
        # Whole straight deck X take-up, at home and seated cover-stop poses.
        for index in (0,7):
            moving,fixed=shift_deck(allstates[index],-.02)
            for name,body in moving.items():
                row=e.v.motion(name,body,(.04,0,0),fixed);row['state_index']=index
                paths.append(row);failures+=row['failed']
            print('CONTINUOUS_DECK',index,'GROUPS',len(moving),'FAILURES',sum(len(p['failed']) for p in paths if p['state_index']==index),flush=True)
        # Existing controls assembled on detached panel; add no new parts.
        prior_service=e.frozen(h);detachable={s+'_'+r for s in 'LR' for r in e.v.INSERT_ROLES}
        installed={k:b for k,b in home.items() if k not in detachable|{'A_FRAME','B_SHELL'}};assembly=[]
        for side in 'LR':
            for name,move in e.v.plan(side):
                if name.endswith('_ROOF'):
                    kept=v.single(prior_service[name].cut(w.w.relief(side)).clean())
                    row=e.roof_motion_partition(name,home[name],kept,move,installed)
                else:row=e.v.motion(name,home[name],move,installed)
                assembly.append(row);failures+=row['failed'];installed[name]=home[name]
                print('ASSEMBLY',name,'BAD',len(row['failed']),flush=True)
        changed_paths=[]
        for side in 'LR':
            for role in sorted(e.v.w.v.PARTS):
                name=side+'_'+role;row=e.v.motion(name,home[name],(0,0,12.),blocks)
                changed_paths.append(row);failures+=row['failed']
        frame_motion=e.v.motion('A_FRAME',home['A_FRAME'],(0,0,12.),blocks);failures+=frame_motion['failed']
        stop_paths=[]
        for side in 'LR':
            for i in (0,1):
                pr=profiles[side][i];delta=pr.lower_stop_height-pr.floor_height-pr.pin_radius
                row=e.v.motion(f'{side}_STOP_{i}',old[f'{side}_STOP_{i}'],((1 if side=='R' else -1)*delta,0,0),blocks)
                stop_paths.append(row);failures+=row['failed']
        integration={'centered_scenes':centers,'translated_deck_scenes':translated,'continuous_deck_X_paths':paths,
            'detached_control_insertions':assembly,'cartridge_against_only_new_material':changed_paths,
            'frame_against_new_material':frame_motion,'STOP_against_new_material':stop_paths,
            'upstream_cartridge_admission_still_unqualified':True}
    if any(v.sha(p)!=value for p,value in h.items()):raise ValueError('native inputs changed during verification')
    if 'panel_shear_key' in sys.modules:raise ValueError('candidate builder imported by reader')
    result={'source_sha256':meta['source_sha256'],'reader_sha256':v.sha(__file__),'input_sha256':h,
            'templates':25,'unchanged_templates':24,'material':{'removed_mm3':loss,'added_mm3':gain,'joins':joins},
            'native_frame_planes':planes,'panel_shift_probes':probes,'native_panel_support_contacts':contacts,
            'unit_wrench_diagnostics':forces,'new_material_frame_admission':admission,
            'integration':integration,'failure_pairs':failures,'passed':not failures,
            'scope':'full current integration plus pure deck translation' if full else 'native key and support subset, not full operating scenes',
            'candidate_builder_imported':False,'same_CAD_kernel':True,
            'nominal_panel_X_takeup_mm':.02,'nominal_cover_outward_takeup_mm':.02,
            'maximum_outward_X_coordinate_sum_mm':.09,'sum_not_a_full_rotation_or_reachable_set_certificate':True,
            'frame_and_its_four_screws_held_fixed':True,'actual_threads_preload_anchor_strength_deflection_qualified':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('PANEL_SHEAR_RESULT',result['passed'],flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true')
    a=p.parse_args();r=verify(a.baseline,a.manifest,a.output,full=a.full);raise SystemExit(0 if r['passed'] else 1)
