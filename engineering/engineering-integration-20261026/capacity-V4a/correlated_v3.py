"""Correlated nominal contact enclosures on complete retained L1 input bodies.

This is a separately scoped method, not an affine-box L1 result relabeling.
Every native carrier check and summed-volume threshold uses original S4 code.
"""
from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path
import gzip
import json
import cadquery as cq
import product_assembly as p
import cam_contact_native as native
from cam_contact_profile import ContactProfile
from translation_regions import sum_common_upper_bound
import validate_product_nominal_report as original_postguard

TOL=1e-7


def require(x,message):
    if not x:raise ValueError(message)


def compare(a,b):
    values=[p.volume(a.cut(b)),p.volume(b.cut(a))]
    require(max(values)<=TOL,'bidirectional whole material identity differs')
    return {'a_minus_b_mm3':values[0],'b_minus_a_mm3':values[1],
            'within_original_volume_gate':True}


def source_profile(root,side,index):
    source=Path(root)/'engineering/thin-mechanism-20261015/native-verification.json.gz'
    data=json.loads(gzip.decompress(source.read_bytes()))
    saved=data['sides'][side]['contacts'][index]['profile']
    return ContactProfile(**{k:saved[k] for k in ContactProfile.__dataclass_fields__})


def unmount(body,side):
    """Inverse of original placement plus mounted SHIFT_Y=6, in source order."""
    shift=(-13.85 if side=='L' else 13.85,16.,-30.55)
    return p.single(body.translate(tuple(-x for x in shift)).rotate((0,0,0),(0,0,1),-180)
                    .rotate((0,0,0),(0,1,0),-90 if side=='L' else 90))


def mount(body,side):
    return p.single(body.rotate((0,0,0),(0,1,0),90 if side=='L' else -90)
                    .rotate((0,0,0),(0,0,1),180)
                    .translate((-13.85 if side=='L' else 13.85,16.,-30.55)))


def static_common(carrier,fixed):
    result=p.strict_common(carrier,fixed)
    v=result['common_mm3']
    # This is the original postguard applied to the STATIC complete carrier
    # against the obstacle, not to the new nonlinear time-domain construction.
    if v<=TOL:
        record={'disposition':'clear','method':'identical_relative_pose','region_count':1,
                'maximum_region_common_mm3':v,'common_upper_bound_mm3':v,
                'common_upper_bound_is_sum_not_union_volume':True}
    else:
        record={'disposition':'unresolved_enclosure_overlap','method':'identical_relative_pose',
                'positive_enclosure_common_mm3':v,'examined_region_common_sum_mm3':v,
                'regions_examined':1,'total_region_count':1,'collision_proved':False}
    original_postguard.validate_frame(record)
    return {'strict_common':result,'original_static_carrier_postguard_record':record,
            'original_static_carrier_postguard_passed':True}


def key_stop(key,stop,spec,target,emit,root,audit):
    side=target['a'][0];index=int(target['b'][-1]);sign=-1 if side=='L' else 1
    require(target['a']==side+'_KEY' and target['b']==side+'_STOP_'+str(index),'same-side whole KEY/STOP pair required')
    law=spec['relative_law'];wanted=['0']*4;wanted[2*'LR'.index(side)+index]=str(-sign)
    require(law['q_xyz']==['0','1','0'] and law['height_x']==wanted
            and not any(Fraction(v) for v in law['joint_z']+law['flank_z']),
            'unrepresented independent motion in KEY/STOP source law')
    require(0<=Fraction(target['q_interval_exact'][0])<=Fraction(target['q_interval_exact'][1])<=12,
            'original exact interval is outside complete source contact domain')
    original_profile=source_profile(root,side,index)
    lo,hi=(float(Fraction(x)) for x in target['q_interval_exact'])
    hmin,hmax=original_profile.height_bounds(lo,hi);home=original_profile.evaluate(0.)[0]
    require(spec['parameter_intervals']==[[lo,hi],[hmin-home,hmax-home]],
            'original KEY/STOP parameter interval not bound to factory source profile')
    audit.update(method='whole_STOP_pin_and_remainder_correlated_contact_path',
                 original_source_profile=original_profile.receipt(),
                 original_profile_index=index,original_profile_side=side)
    k,s=unmount(key,side),unmount(stop,side)
    audit['contact_frame_whole_bodies']=[emit('contact-key',k),emit('contact-stop',s)]
    transforms={'key_roundtrip':compare(mount(k,side),key),'stop_roundtrip':compare(mount(s,side),stop)}
    extracted,pin,remainder,geometry=native.extract_profile(k,s,side)
    audit['native_material_decomposition']=geometry
    audit['native_pin_and_remainder']=[emit('decomposition-pin',pin),emit('decomposition-remainder',remainder)]
    require(extracted.pin_radius==original_profile.pin_radius,
            'native disk radius differs from source contact-path disk radius')
    # The factory applies h_source(q)-h_source(0) to the ACTUAL whole STOP.
    # Translate the original source graph to the observed native pin home;
    # do not replace that law with a profile fitted after a numerical unmount.
    qshift=extracted.pin_q-original_profile.pin_q
    rshift=geometry['native_pin_center_qr'][1]-home
    profile=ContactProfile(original_profile.pin_radius,original_profile.floor_height+rshift,
        original_profile.floor_corner_q+qshift,original_profile.ramp_slope,extracted.pin_q,
        original_profile.lower_stop_height+rshift,original_profile.q_max)
    alignment={'source_profile':original_profile.receipt(),'native_extracted_profile':extracted.receipt(),
               'source_graph_shift_qr_mm':[qshift,rshift],'path_profile':profile.receipt(),
               'ideal_relation':'path_h(q) = source_h(q) + native_pin_home_r - source_h(0); path_pin_q = native_pin_home_q',
               'native_binary64_translation_is_not_interval_certificate':True}
    audit['profile_alignment_to_actual_whole_STOP']=alignment
    require(profile.q_max==12.,'original complete finite contact domain required')
    sweep,construction=native.pin_path_envelope(profile,side,*geometry['pin_e_extent_mm'])
    cages=native.remainder_cages(remainder,profile,side)
    require(len(cages)==3,'all three complete STOP remainder cages required')
    complete=[sweep,*[x[0] for x in cages]];checks=[]
    audit.update(pin_path_construction=construction,remainder_carrier_constructions=[r for _,r in cages],carrier_checks=checks)
    for i,carrier in enumerate(complete):
        local_export=emit('carrier-contact-'+str(i),carrier)
        global_carrier=mount(carrier,side);global_export=emit('carrier-'+str(i),global_carrier)
        item={'part':'complete_pin_path' if i==0 else 'complete_remainder_'+str(i),
              'contact_frame_BREP':local_export,'phone_frame_BREP':global_export}
        checks.append(item)
        check=static_common(carrier,k)
        item['contact_frame']=check
        global_check=static_common(global_carrier,key);item['phone_frame']=global_check
        require(abs(check['strict_common']['common_mm3']-global_check['strict_common']['common_mm3'])<=TOL,
                'contact-frame and phone-frame Common differ')
    upper_phone=sum_common_upper_bound(x['phone_frame']['strict_common']['common_mm3'] for x in checks)
    upper_contact=sum_common_upper_bound(x['contact_frame']['strict_common']['common_mm3'] for x in checks)
    upper=max(upper_phone,upper_contact)
    # A lowered pin at q=0 must actually intersect the same complete native KEY.
    negative_stop=p.single(s.translate((0.,0.,-.01)))
    negative_local=emit('negative-contact-stop',negative_stop)
    negative_global=emit('negative-stop',mount(negative_stop,side))
    negative=static_common(negative_stop,k)
    audit['negative_control']=negative
    require(negative['strict_common']['common_mm3']>TOL,'KEY/STOP penetration negative control did not reject')
    return {'method':'whole_STOP_pin_and_remainder_correlated_contact_path',
            'disposition':'clear' if upper<=TOL else 'unresolved_enclosure_overlap',
            'covered_q_interval_mm':[0.,12.],'original_q_interval_exact':target['q_interval_exact'],
            'original_interval_is_subset':0<=Fraction(target['q_interval_exact'][0])<=Fraction(target['q_interval_exact'][1])<=12,
            'whole_STOP_decomposition':geometry,'pin_path_construction':construction,
            'profile_alignment_to_actual_whole_STOP':alignment,
            'remainder_carrier_constructions':[r for _,r in cages],
            'frame_roundtrip_checks':transforms,'carrier_checks':checks,
            'common_upper_bound_mm3':upper,'common_upper_bound_is_sum_not_union_volume':True,
            'frame_common_sums_mm3':{'contact':upper_contact,'phone':upper_phone},
            'both_full_frame_sums_must_satisfy_original_gate':True,
            'negative_control':negative,'negative_control_STOP_BREP':negative_global,
            'negative_control_contact_STOP_BREP':negative_local,
            'selected_lower_contact_branch_requires_restoring_force':True,
            'same_side_q_height_correlation_preserved':True,
            'full_independent_product_domain_or_dynamic_branch_selection_proved':False}


def spring_stop(stop,spring,spec,target,emit,root,audit):
    descriptor=spec['fixed'];name=descriptor['material'];side=name[0];i=int(name.split('_')[2]);sign=-1 if side=='L' else 1
    require(name==side+'_SPRING_'+str(i)+'_OD_TOL_ENVELOPE' and spec['moving']['material']==side+'_STOP_'+str(i),
            'matched same-side spring/STOP required')
    require(descriptor['kind']=='complete_growing_spring_cylinder','whole original growing cylinder required')
    profile=source_profile(root,side,i)
    audit.update(method='matched_spring_STOP_co_moving_nested_complete_cylinder',
                 original_source_profile=profile.receipt(),original_profile_index=i,original_profile_side=side)
    lo,hi=map(lambda x:float(Fraction(x)),target['q_interval_exact'])
    hmin,hmax=profile.height_bounds(lo,hi);home=profile.evaluate(0.)[0]
    require([hmin,hmax]==descriptor['profile_height_bounds_mm'] and home==descriptor['profile_home_height_mm'],
            'original maximal cylinder not bound to current source contact profile')
    require(descriptor['radius_mm']==.43 and hmin<=hmax<=home+1e-12,'original monotone envelope family required')
    law=spec['relative_law'];wanted=['0']*4;wanted[2*'LR'.index(side)+i]=str(sign)
    require(law['q_xyz']==['0','0','0'] and law['height_x']==wanted
            and not any(Fraction(v) for v in law['joint_z']+law['flank_z']),
            'unrepresented motion in matched spring/STOP pair')
    a,b=descriptor['axis_start_mm'],descriptor['axis_end_mm']
    require(a[1:]==b[1:] and b[0]>a[0],'whole X cylinder required')
    represented=p.single(cq.Solid.makeCylinder(.43,b[0]-a[0],cq.Vector(*a),cq.Vector(1,0,0)))
    identity=compare(represented,spring)
    displacement=sign*(hmin-home)
    carrier=p.single(spring.translate((-displacement,0.,0.)))
    carrier_export=emit('carrier-0',carrier)
    check=static_common(carrier,stop)
    audit['static_carrier_check']=check
    base=descriptor['base_bounds_mm'];delta_min=sign*(hmax-home)
    nested={'side':side,'STOP_X_displacement_at_q_high_mm':displacement,
            'STOP_X_displacement_at_q_low_mm':delta_min,
            'relative_cylinder_X_endpoints_mm':([base[0]-displacement,base[1]] if side=='L'
                                             else [base[0],base[1]-displacement]),
            'cylinder_radius_mm':.43,
            'proof':'Subtract the SAME STOP displacement from the complete spring cylinder. The growing endpoint becomes constant. The opposite endpoint is monotone; the high-q cylinder in this frame contains the entire interval.',
            'q_and_height_not_independent':True}
    sampled=[];audit.update(nesting=nested,finite_crosschecks=sampled)
    for n,q in enumerate((lo,(lo+hi)/2,hi)):
        delta=sign*(profile.evaluate(q)[0]-home)
        start=base[0]+min(0.,delta);end=base[1]+max(0.,delta)
        actual=p.single(cq.Solid.makeCylinder(.43,end-start,cq.Vector(start,(base[2]+base[3])/2,(base[4]+base[5])/2),cq.Vector(1,0,0)))
        relative=p.single(actual.translate((-delta,0.,0.)))
        actual_stop=p.single(stop.translate((delta,0.,0.)))
        sample={'q_mm':q,'whole_pair_BREP':[emit('sample-'+str(n)+'-spring',actual),
                emit('sample-'+str(n)+'-stop',actual_stop)],
                'relative_cylinder_BREP':emit('sample-'+str(n)+'-relative',relative),
                'finite_crosscheck_not_the_continuous_nesting_proof':True}
        sampled.append(sample)
        outside=p.volume(relative.cut(carrier));require(outside<=TOL,'relative complete cylinder escaped correlated carrier')
        actual_check=static_common(actual,actual_stop)
        sample.update(whole_relative_cylinder_outside_mm3=outside,whole_actual_pair_common=actual_check)
        require(actual_check['strict_common']['common_mm3']<=check['strict_common']['common_mm3']+TOL,
                'finite actual pair Common exceeds correlated carrier Common bound')
    negative=p.single(carrier.translate((.01 if side=='L' else -.01,0.,0.)))
    negative_export=emit('negative-spring',negative)
    negative_check=static_common(negative,stop)
    audit['negative_control']=negative_check
    require(negative_check['strict_common']['common_mm3']>TOL,'spring/STOP penetration negative control did not reject')
    value=check['strict_common']['common_mm3']
    finite_max=max(x['whole_actual_pair_common']['strict_common']['common_mm3'] for x in sampled)
    return {'method':'matched_spring_STOP_co_moving_nested_complete_cylinder',
            'disposition':'clear' if max(value,finite_max)<=TOL else 'unresolved_enclosure_overlap',
            'original_q_interval_exact':target['q_interval_exact'],'profile':profile.receipt(),
            'maximum_spring_whole_material_identity':identity,'nesting':nested,
            'static_carrier_check':check,'common_upper_bound_mm3':sum_common_upper_bound([value]),
            'finite_actual_pair_maximum_common_mm3':finite_max,
            'common_upper_bound_is_sum_not_union_volume':True,
            'carrier_BREP':carrier_export,'finite_crosschecks':sampled,
            'negative_control':negative_check,'negative_control_cylinder_BREP':negative_export,
            'all_original_source_predicates_passed':True,
            'physical_spring_wire_force_fatigue_qualification':False}


def evaluate(moving,fixed,spec,target,emit,root,audit):
    if spec['fixed']['kind']=='complete_growing_spring_cylinder':
        return spring_stop(moving,fixed,spec,target,emit,root,audit)
    return key_stop(moving,fixed,spec,target,emit,root,audit)
