"""Complete explicit manual study sequence and geometric assembly checks.

Controls, two separate OPEN hold screws and a separate support insert are real
candidate solids. The sequence requires hands/temporary forming support during
motion, and specifies nominal threads. It never labels an unmodeled automatic
lock, following deck, thread preload or selected display as physically proved.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict,dataclass,replace
import itertools
import json
from pathlib import Path

import product_assembly as p
import oled_storage as oled
import verify_serviceable_pawl as translated
from straight_envelope import fuse, single

TOL=1e-7


@dataclass(frozen=True)
class Pose:
    slide:float=0.
    descent:float=0.
    left_tab:float=0.
    right_tab:float=0.
    hold_screws:int=0
    support_insert:bool=False

    def __post_init__(self):
        p.b_transform(self.slide,self.descent)
        if any(not 0<=p.finite(x)<=3 for x in (self.left_tab,self.right_tab)):raise ValueError('invalid manual tab stroke')
        if type(self.hold_screws) is not int or self.hold_screws not in (0,1,2):raise ValueError('zero, one or two actual hold screws required')
        if type(self.support_insert) is not bool:raise ValueError('explicit support state required')
        if (self.hold_screws or self.support_insert) and (self.slide!=79.75 or self.descent!=8.2):
            raise ValueError('OPEN accessories cannot travel with the closed mechanism')


def transition(before,after):
    if not isinstance(before,Pose) or not isinstance(after,Pose):raise ValueError('explicit poses required')
    changes=[k for k in asdict(before) if getattr(before,k)!=getattr(after,k)]
    if len(changes)!=1:raise ValueError('one independent manual action per transition')
    key=changes[0]
    if key in ('slide','descent'):
        if min(before.left_tab,before.right_tab,after.left_tab,after.right_tab)!=3:
            raise ValueError('both independent PAWL tabs must be released before B motion')
        if before.hold_screws or after.hold_screws or before.support_insert or after.support_insert:
            raise ValueError('remove actual OPEN accessories before reverse travel')
    if key in ('left_tab','right_tab') and (before.slide or before.descent):
        raise ValueError('this demonstrated sequence operates PAWL tabs at STOW only')
    if key=='hold_screws' and abs(after.hold_screws-before.hold_screws)!=1:
        raise ValueError('install or remove one manual hold screw at a time')
    return {'action':key,'from':asdict(before),'to':asdict(after),
            'requires_manual_holding':key in ('slide','descent','hold_screws'),
            'requires_temporary_front_strip_forming_support':key in ('slide','descent'),
            'nominal_thread_engagement_action_not_instant_lock':key=='hold_screws',
            'geometric_state_program_only':True}


def manual_program():
    poses=[Pose()]
    for update in ({'left_tab':3.},{'right_tab':3.},{'slide':79.75},{'descent':8.2},
                   {'hold_screws':1},{'hold_screws':2},{'support_insert':True},
                   {'support_insert':False},{'hold_screws':1},{'hold_screws':0},
                   {'descent':0.},{'slide':0.},{'right_tab':0.},{'left_tab':0.}):
        poses.append(replace(poses[-1],**update))
    return {'poses':[asdict(x) for x in poses],'actions':[transition(a,b) for a,b in zip(poses,poses[1:])],
            'returns_to_same_locked_STOW_state':poses[0]==poses[-1],
            'closed_unlock_slide_seat_hold_support_remove_unseat_return_relock_all_explicit':True,
            'separate_accessories':['B_OPEN_DISPLAY_SUPPORT_ACCESSORY','four support screws','two hold screws'],
            'onboard_accessory_storage':False,'automatic_following_front_support_implemented':False,
            'physical_cycle_completed_on_hardware':False,'hands_free_OPEN_load_capacity_verified':False}


def joined_bounds(shapes):
    bs=[p.bounds(b) for b in shapes]
    bounds=[v for i in range(3) for v in (min(b[2*i] for b in bs),max(b[2*i+1] for b in bs))]
    return {'bounds_mm':bounds,'size_mm':[bounds[2*i+1]-bounds[2*i] for i in range(3)]}


def finished_envelopes():
    state,_=p.product_scene();b=state['B_SHELL'].translate((0,0,-8.2))
    # Six inherited telescopic stages bridge the cabins and are excluded from
    # individual rigid-cabin allocation; their actual bodies remain in scenes.
    a_names=[k for k in state if k!='B_SHELL' and 'TELESCOPE_' not in k]
    a=joined_bounds([state[k] for k in a_names]);br=joined_bounds([b])
    equal=all(abs(x-y)<=TOL for x,y in zip(a['size_mm'],br['size_mm']))
    sheet,meta=oled.geometry(79.75,8.2)
    whole,_=p.product_scene(79.75,8.2,3,3,open_hold=True,open_support=True)
    rigid_whole=joined_bounds(whole.values());with_sheet=joined_bounds([*whole.values(),sheet])
    stow_sheet,_=oled.geometry();stow=joined_bounds([*state.values(),stow_sheet])
    return {'A_fixed_parts':a,'B_fixed_body':br,'equal_fixed_cabin_bounds':equal,
            'A_fixed_part_names':a_names,'telescopes_are_cross_cabin_participants_not_battery_space':True,
            'OPEN_all_101_mechanical_parts':rigid_whole,'OPEN_with_trial_OLED':with_sheet,
            'STOW_all_94_parts_with_trial_OLED':stow,
            'trial_OLED_front_z_mm':meta['front_z_mm'],'OLED_finished_module_is_unknown':True,
            'OPEN_each_cabin_with_shared_flat_trial_OLED_depth_mm':8.-(meta['front_z_mm']-.1),
            'physical_finished_product_bounds_qualified':False}


def compare_pairs(scene,selected=None):
    # Validate each complete participant once in this immutable local scene.
    # Repeated topology validation of the same 100-face shell in every pair
    # obscures actual Boolean time without adding a different check.
    rows=[];info={name:(single(body),p.bounds(body),p.volume(body)) for name,body in scene.items()}
    for (na,a),(nb,b) in itertools.combinations(sorted(scene.items()),2):
        if selected is not None and na not in selected and nb not in selected:continue
        _,aa,va=info[na];_,bb,vb=info[nb]
        gap=max(max(aa[2*i]-bb[2*i+1],bb[2*i]-aa[2*i+1]) for i in range(3))
        if gap>0:r={'common_mm3':0.,'method':'positive_axis_gap','axis_gap_lower_mm':gap}
        else:
            volume=p.volume(a.intersect(b))
            if volume<0 or volume>min(va,vb)+TOL:raise ValueError('invalid signed intersection')
            r={'common_mm3':volume,'method':'native_common','axis_gap_lower_mm':0.}
        rows.append({'a':na,'b':nb,**r})
    return rows


def path(label,body,vector,fixed):
    row=translated.motion(label,body,vector,fixed)
    row['positive_common_is_rejection_not_automatically_a_collision_witness']=True
    row['nominal_no_penetration_does_not_assert_positive_clearance']=True
    return row


def verify():
    home,meta=p.product_scene();new,changes=p.product_templates();alloc=p.registered_components();strip,_=oled.geometry()
    print('PRODUCT_INITIALIZED',len(home),flush=True)
    changed=set(changes['changed_native_parts'])|set(home)-set(p.native_scene()[0]);states=[];failed=[]
    for label,s,d,u,held in (('STOW',0.,0.,0.,False),('RELEASED',0.,0.,3.,False),('PREDOCK',79.75,0.,3.,False),('OPEN_SUPPORTED',79.75,8.2,3.,True)):
        current,_=p.product_scene(s,d,u,u,open_hold=held,open_support=held)
        current.update(p.registered_components(slide_mm=s,descent_mm=d));current['OLED_GEOMETRIC_TRIAL']=oled.geometry(s,d)[0]
        rows=compare_pairs(current,changed|set(alloc)|{'OLED_GEOMETRIC_TRIAL'}|{k for k in current if '_OPEN_' in k or '_B_SUPPORT_' in k})
        bad=[r for r in rows if r['common_mm3']>TOL];failed+=bad
        states.append({'pose':label,'participants':len(current),'checked_pairs':len(rows),'rejected_pairs':bad})
        print('PRODUCT_STATE',label,len(current),'REJECTED',len(bad),flush=True)
    controls=[];access=[]
    fixed={**home,**alloc,'OLED_GEOMETRIC_TRIAL':strip}
    for side,sign in (('L',-1),('R',1)):
        moving={side+'_'+role for role in ('TAB','THUMB_PAD','PAD_SCREW_M06_NOMINAL','PAWL','SHOULDER_PIN_NOMINAL')}
        controls.append(path(side+'_SIDE_TAB_FULL_3MM',home[side+'_THUMB_PAD'],(0,3.,0),{k:b for k,b in fixed.items() if k not in moving}))
        for u in (0.,3.):
            # Finite nail/tool contact prism approaches from outside the side;
            # this is not a whole hand or an ergonomics qualification.
            probe=p.box((36.985,23.4+u,-.70),(44.,25.2+u,-.20))
            if sign<0:probe=single(probe.mirror('YZ'))
            current,_=p.product_scene(0,0,u,u);current.update(alloc);current['OLED_GEOMETRIC_TRIAL']=strip
            hit=p.strict_common(probe,current[side+'_THUMB_PAD'])['common_mm3']
            obstacles=[{'obstacle':k,**p.strict_common(probe,b)} for k,b in current.items() if k!=side+'_THUMB_PAD']
            bad=[r for r in obstacles if r['common_mm3']>TOL]
            access.append({'side':side,'tab_mm':u,'contact_volume_witness_mm3':hit,'other_body_penetrations':bad,
                           'finite_probe_size_not_human_hand_model':True,'accessible_to_this_probe':hit>TOL and not bad})
    # Finite front approach to the old pad crosses the actual OLED. This is
    # why a functioning bare-deck thumb tab was insufficient after integration.
    old_access=[]
    for x in (-11.6,11.6):
        probe=p.box((x-.4,24.2,-8.),(x+.4,24.8,.2))
        old_access.append({'x_mm':x,'OLED_blocking_common_mm3':p.strict_common(probe,strip)['common_mm3']})
    # New controls assembled before the removable A front support and OLED.
    assembly=[];removed={'A_DISPLAY_SUPPORT'}|{k for k in home if '_A_SUPPORT_' in k or '_SIDE_GUIDE' in k or k.endswith('_THUMB_PAD') or k.endswith('_PAD_SCREW_M06_NOMINAL')}
    installed={k:b for k,b in home.items() if k not in removed}
    for side in 'LR':
        for role in ('THUMB_PAD','PAD_SCREW_M06_NOMINAL','SIDE_GUIDE','SIDE_GUIDE_0_M1_NOMINAL','SIDE_GUIDE_1_M1_NOMINAL'):
            name=side+'_'+role;assembly.append(path(name+'_INSERT_FROM_FRONT',home[name],(0,0,-8.),installed));installed[name]=home[name]
    assembly.append(path('A_DISPLAY_SUPPORT_INSERT',home['A_DISPLAY_SUPPORT'],(0,0,-8.),installed));installed['A_DISPLAY_SUPPORT']=home['A_DISPLAY_SUPPORT']
    for name in sorted(k for k in home if '_A_SUPPORT_' in k):
        assembly.append(path(name+'_INSERT',home[name],(0,0,-8.),installed));installed[name]=home[name]
    opened,_=p.product_scene(79.75,8.2,3,3);opened.update(p.registered_components(slide_mm=79.75,descent_mm=8.2));opened['OLED_GEOMETRIC_TRIAL']=oled.geometry(79.75,8.2)[0]
    holds=[];negative_threads=[]
    for side in 'LR':
        name=side+'_OPEN_HOLD_M1_NOMINAL';body=new[name]
        holds.append(path(name+'_INSERT_FROM_REAR',body,(0,0,10.),opened));opened[name]=body
        # With screw held by its specified A thread, the finite B head seat
        # opposes normal lift. A smooth nominal hole alone does not anchor it.
        b=opened['B_SHELL'];a=opened['A_FRAME']
        negative_threads.append({'side':side,'B_lift_0p01_vs_fixed_screw_mm3':p.strict_common(b.translate((0,0,.01)),body)['common_mm3'],
            'B_slide_plus_0p1_vs_fixed_screw_mm3':p.strict_common(b.translate((0,.1,0)),body)['common_mm3'],
            'B_descent_0p01_vs_A_shoulder_mm3':p.strict_common(b.translate((0,0,-.01)),a)['common_mm3'],
            'screw_lift_0p01_vs_smooth_A_hole_mm3':p.strict_common(body.translate((0,0,.01)),a)['common_mm3'],
            'actual_thread_axial_retention_proved':False})
    support=new['B_OPEN_DISPLAY_SUPPORT_ACCESSORY'].translate((0,79.75,0))
    holds.append(path('B_OPEN_SUPPORT_RIGHT_SIDE_INSERT',support,(80.,0,0),opened));opened['B_OPEN_DISPLAY_SUPPORT_ACCESSORY']=support
    for name in sorted(k for k in new if '_B_SUPPORT_' in k):
        body=new[name].translate((0,79.75,0));holds.append(path(name+'_INSERT_FROM_FRONT',body,(0,0,-8.),opened));opened[name]=body
    # Removing the accessories reverses the identical finite geometric sets.
    # Continuous B rim translation covers the newly added front-depth material.
    rim_paths=[]
    for sign in (-1,1):
        source=p.box((35.8,14.7,7.05),(36.995,94.25,8.3))
        if sign<0:source=single(source.mirror('YZ'))
        cage=translated.broad_sweep(source,(0,79.75,0))
        checks=[{'fixed':name,**p.strict_common(cage,body)} for name,body in home.items() if name!='B_SHELL']
        bad=[r for r in checks if r['common_mm3']>TOL]
        rim_paths.append({'side':sign,'method':'complete added-rim box superset, even retained at removed right-side port',
                          'slide_checks':checks,'failed':bad,'seating_min_Y_gap_to_A_mm':.2})
    packing={'A_mm3':p.volume(alloc['A_BATTERY_ALLOCATION']),'B_mm3':p.volume(alloc['B_BATTERY_ALLOCATION']),
             'capacities_mAh':{'A':None,'B':None},'4700mAh_target_met':None,'larger_A_allocation_is_capacity_proof':False}
    packing['A_larger_allocation_volume']=packing['A_mm3']>packing['B_mm3']
    # Full translation supersets for actual allocated volume, including the
    # intermediate B follower crossings that three endpoint views can miss.
    allocation_paths=[]
    endpoint_scenes=[p.product_scene(s,d,u,u)[0] for s,d,u in ((0.,0.,0.),(0.,0.,3.),(79.75,0.,3.),(79.75,8.2,3.))]
    shell_regions=[p.box((-36.995,0.,0.),(36.995,94.25,8.)),
                   p.box((-36.995,14.7,-1.15),(-35.8,94.25,0.)),
                   p.box((35.8,14.7,-1.15),(36.995,94.25,0.))]
    remainder=home['B_SHELL'].translate((0,0,-8.2))
    for region in shell_regions:remainder=remainder.cut(region)
    shell_uncovered=p.volume(remainder)
    if shell_uncovered>TOL:raise ValueError('B shell material omitted from full slide cover')
    for record in p.load_config()['components']:
        fixed=alloc[record['name']]
        for role in home:
            boxes=[]
            for index,scene in enumerate(endpoint_scenes):
                body=scene[role]
                if record['cabin']=='B':body=body.translate(tuple(-x for x in ((0,0,8.2) if index<2 else (0,79.75,8.2 if index==2 else 0))))
                boxes.append(p.bounds(body))
            if record['cabin']=='B':fixed= p.box(record['lo_mm'],record['hi_mm'])
            for phase,(first,last) in enumerate(((0,1),(1,2),(2,3))):
                pair=[boxes[first],boxes[last]]
                lo=[min(x[2*i] for x in pair) for i in range(3)];hi=[max(x[2*i+1] for x in pair) for i in range(3)]
                cage=p.box(lo,hi);row={'allocation':record['name'],'obstacle':role,'phase':('UNLOCK','SLIDE','SEAT')[phase],
                    'method':'complete per-stage affine endpoint bounding-box superset',**p.strict_common(cage,fixed)}
                if row['common_mm3']>TOL:
                    # A cage containing the inside of its own hollow cabin is
                    # only a broad rejection. Its actual material is fixed.
                    if (record['cabin']=='B' and role=='B_SHELL') or (record['cabin']=='A' and role in ('A_FRAME','A_BACK_PANEL')):
                        body=home[role].translate((0,0,-8.2)) if role=='B_SHELL' else home[role]
                        row={**row,**p.strict_common(body,fixed),'method':'actual fixed same-cabin material'}
                    elif record['cabin']=='A' and role=='B_SHELL':
                        shifts=((0.,0.,8.2),(0.,0.,8.2),(0.,79.75,8.2),(0.,79.75,0.))
                        values=[]
                        for region in shell_regions:
                            br=p.bounds(region)
                            lower=[br[2*i]+min(shifts[first][i],shifts[last][i]) for i in range(3)]
                            upper=[br[2*i+1]+max(shifts[first][i],shifts[last][i]) for i in range(3)]
                            values.append(p.strict_common(p.box(lower,upper),fixed)['common_mm3'])
                        row={**row,'method':'native B material covered by three finite boxes, then complete per-stage translations',
                             'region_common_mm3':values,'common_mm3':max(values),'common_field_is_max_region_not_union_volume':True,
                             'B_material_not_covered_mm3':shell_uncovered}
                allocation_paths.append(row)
    allocation_bad=[r for r in allocation_paths if r['common_mm3']>TOL]
    # Preserve the rejected wide B allocation and its real midpoint witness.
    prior_path=p.ROOT/'engineering/product-integration-20261018/mechanical/geometry-trial-r1.json'
    prior=p.load_config(prior_path);mid,_=p.product_scene(40.,0.,3.,3.);old_alloc=p.registered_components(prior,40.,0.)
    allocation_negatives=[{'configuration_sha256':p.sha(prior_path),'pose':{'slide_mm':40.,'descent_mm':0.},'allocation':name,'obstacle':role,**p.strict_common(body,mid[role])}
        for name,body in old_alloc.items() if name in ('B_BATTERY_ALLOCATION','B_ELECTRONICS_ALLOCATION') for role in mid if 'TELESCOPE_' in role]
    allocation_negatives=[r for r in allocation_negatives if r['common_mm3']>TOL]
    allpaths=controls+assembly+holds
    pathfail=[{'label':r['label'],'failed':r['failed']} for r in allpaths if r['failed']]
    return {'schema':'razr-product-motion-study-v1','source_sha256':p.sha(__file__),'assembly_source_sha256':p.sha(p.__file__),
            'configuration_sha256':p.sha(p.CONFIG),'program':manual_program(),'finished_envelopes':finished_envelopes(),
            'four_state_checks':states,'state_rejected_pairs':failed,'full_control_paths':controls,'side_access':access,
            'old_front_access_negative_controls':old_access,'new_control_and_A_support_assembly':assembly,
            'OPEN_accessory_paths':holds,'OPEN_nominal_retention_and_thread_negative':negative_threads,'added_B_rim_full_paths':rim_paths,
            'allocation_priority':packing,'allocation_complete_path_checks':allocation_paths,'allocation_path_rejections':allocation_bad,'wide_B_allocation_midpath_negative_controls':allocation_negatives,'rejected_paths':pathfail,
            'all_requested_geometry_checks_nonpenetrating':not failed and not pathfail and not allocation_bad and not any(r['failed'] for r in rim_paths) and all(x['accessible_to_this_probe'] for x in access),
            'upstream_cartridge_telescopes_full_assembly_reverified':False,
            'new_assembly_scope':'candidate pads/bridges/A support on already assembled native cartridge scene, followed by OLED trial and reversible OPEN accessories',
            'selected_OLED_COF_and_following_front_support_installed':False,'physical_hold_and_strength_qualified':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--program-only',action='store_true');a=ap.parse_args()
    r={'program':manual_program(),'finished_envelopes':finished_envelopes()} if a.program_only else verify()
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'report':str(a.output),'geometry_checks_nonpenetrating':r.get('all_requested_geometry_checks_nonpenetrating'),'manufacturing_go':False}))
