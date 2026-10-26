"""Prospective additive panel travel stops for the verified K1 whole KEYs.

Not adopted by S4/K1/K2. Full factories, native oriented contact patches,
material accounts, complete pair records and independent STEP readback remain
required. No source domain is reduced and no physical qualification is given.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

NAME='panel_key_travel_stops_v1'
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
K1_SOURCE_SHA='3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578'
K1_CONTRACT_SHA='17e1532ed82eff1298e9525456d6953df56437082ef2918f3d04839cff200455'
VOLUME_TOL_MM3=1e-7
AREA_IDENTITY_TOL_MM2=1e-7
PLANE_IDENTITY_TOL_MM=1e-7
NORMAL_COMPONENT_TOL=1e-9


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_design(k1_contract_path):
    """Bind both stop Y planes to the frozen K1 crossbar."""
    require(sha(k1_contract_path)==K1_CONTRACT_SHA,'frozen original K1 contract bytes differ')
    k1=json.loads(Path(k1_contract_path).read_text())
    require(k1['candidate_source_sha256']==K1_SOURCE_SHA,'named K1 source identity differs')
    lo,hi=k1['design_contract']['added_boxes_R_local_q0_mm']['front_crossbar']
    require(lo==[16.96,5.,4.02] and hi==[18.90,5.38,4.38],'original K1 crossbar differs')
    # Strict X inset preserves the original cover-support plane |X|=17.43.
    x0,x1=17.48,18.38;lower_plane=lo[1];upper_plane=hi[1]+12.
    pieces={'lower_post':[[x0,lower_plane-.60,.50],[x1,lower_plane,hi[2]]],
            'upper_toe':[[x0,upper_plane,lo[2]],[x1,18.50,hi[2]]]}
    return {'candidate_name':NAME,'functional_source_commit':S4,
        'required_whole_KEY_candidate':'key_forward_loop_v1','required_K1_source_sha256':K1_SOURCE_SHA,
        'required_K1_contract_sha256':K1_CONTRACT_SHA,'additive_boxes_R_mm':pieces,
        'front_crossbar_R_q0_mm':[lo,hi],
        'original_front_post_R_mm':[[17.43,18.30,.50],[18.43,19.50,7.]],
        'original_rear_post_R_mm':[[17.43,22.35,.50],[18.43,23.80,7.]],
        'declared_stop_contact_planes_Y_mm':{'lower':lower_plane,'upper':upper_plane},
        'declared_contact_patch_XZ_R_mm':[[x0,lo[2]],[x1,hi[2]]],
        'declared_contact_patch_area_mm2':(x1-x0)*(hi[2]-lo[2]),
        'declared_panel_contact_outward_normals':{'lower':[0.,1.,0.],'upper':[0.,-1.,0.]},
        'declared_KEY_contact_outward_normals':{'lower':[0.,-1.,0.],'upper':[0.,1.,0.]},
        'upper_toe_original_front_post_overlap_Y_mm':18.50-18.30,
        'lower_post_positive_join_to_actual_panel_required_not_assumed':True,
        'panel_change_is_addition_only':True,'all_other_participants_and_K1_KEY_material_retained':True,
        'existing_cover_functional_planes_abs_X_mm':17.43,
        'unmodified_existing_cover_patch_Y_mm':{'front':[18.30,19.50],'rear':[22.35,23.80]},
        'unmodified_existing_cover_patch_Z_search_mm':[.50,7.],
        'local_clearance_prisms_only_not_whole_KEY':True,'negative_control_overtravel_mm':[.001,.01],
        'negative_controls_are_whole_KEY_panel_tests_not_out_of_profile_factory_motion':True,
        'new_contact_area_identity_tolerance_mm2':AREA_IDENTITY_TOL_MM2,
        'new_contact_plane_identity_tolerance_mm':PLANE_IDENTITY_TOL_MM,
        'original_all_pair_Common_gate_mm3':VOLUME_TOL_MM3,
        'current_S4_or_K1_allowed_domain_reduced':False,
        'q_limits_are_candidate_constraints_pending_native_and_physical_evidence':True,
        'physical_stop_added_or_proved_on_real_specimen':False,
        'material_preload_fatigue_tolerances_known':False,'strength_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}


def handed_bounds(side,bounds):
    require(side in 'LR' and len(side)==1,'explicit side required')
    lo,hi=map(list,bounds)
    if side=='L':lo[0],hi[0]=-hi[0],-lo[0]
    return lo,hi


def planar_patch(p,axis,plane,first,second):
    others=[i for i in range(3) if i!=axis];points=[]
    for a,b in ((first[0],second[0]),(first[1],second[0]),(first[1],second[1]),(first[0],second[1])):
        point=[0.,0.,0.];point[axis]=plane;point[others[0]]=a;point[others[1]]=b;points.append(p.cq.Vector(*point))
    return p.cq.Face.makeFromWires(p.cq.Wire.makePolygon([*points,points[0]]))


def face_area(shape):
    values=[float(f.Area()) for f in shape.Faces()]
    require(shape.isValid() and all(math.isfinite(x) and x>=0 for x in values),'invalid complete face material')
    return math.fsum(values)


def measured_patch(body,p,axis,plane,first,second,outward):
    patch=planar_patch(p,axis,plane,first,second);pieces=[];records=[]
    for index,face in enumerate(body.Faces()):
        if face.geomType()!='PLANE':continue
        normal=face.normalAt().toTuple();vertices=[v.Center().toTuple() for v in face.Vertices()]
        if not vertices or abs(normal[axis]-outward)>NORMAL_COMPONENT_TOL:continue
        if any(abs(normal[i])>NORMAL_COMPONENT_TOL for i in range(3) if i!=axis):continue
        if any(abs(v[axis]-plane)>PLANE_IDENTITY_TOL_MM for v in vertices):continue
        overlap=face.intersect(patch);area=face_area(overlap)
        if area>0:
            pieces.extend(overlap.Faces());records.append({'native_face_index':index,
                'outward_unit_normal':list(normal),'clipped_native_area_mm2':area,
                'maximum_vertex_plane_error_mm':max(abs(v[axis]-plane) for v in vertices)})
    require(pieces,'required native oriented contact patch absent')
    result=p.cq.Compound.makeCompound(pieces)
    return result,{'plane_axis':axis,'plane_coordinate_mm':plane,'outward_normal_component':outward,
        'patch_other_coordinate_intervals_mm':[list(first),list(second)],
        'observed_native_faces':records,'total_actual_patch_area_mm2':face_area(result)}


def compare_face_material(a,b):
    values=[face_area(a.cut(b)),face_area(b.cut(a))]
    require(max(values)<=AREA_IDENTITY_TOL_MM2,'native functional/contact face material differs')
    return {'a_minus_b_area_mm2':values[0],'b_minus_a_area_mm2':values[1]}


def apply(parts,metadata,p,k1_contract_path):
    """Add four material boxes to the complete factory without altering KEYs."""
    c=frozen_design(k1_contract_path);proof=metadata.get('named_KEY_candidate',{})
    require(len(parts) in (154,161) and proof.get('candidate_name')=='key_forward_loop_v1'
            and proof.get('candidate_source_sha256')==K1_SOURCE_SHA
            and proof.get('actual_K1_run_id')==40276423445,
            'complete actual factory through dual-clear K1 adapter required')
    old=p.single(parts['A_BACK_PANEL']);new=old;materials={'original_panel':old};joins={}
    for side in 'LR':
        front=p.box(*handed_bounds(side,c['original_front_post_R_mm']))
        require(p.volume(front.cut(old))<=VOLUME_TOL_MM3,'complete original front post absent from actual panel')
        for role,bounds in c['additive_boxes_R_mm'].items():
            label=side+'_'+role;body=p.box(*handed_bounds(side,bounds));join=body.intersect(old)
            value=p.volume(join);require(value>VOLUME_TOL_MM3,'stop has no positive material join to actual panel')
            added=body.cut(old);require(p.volume(added)>VOLUME_TOL_MM3,'new stop adds no actual material')
            materials[label]=body;materials[label+'_join_to_original_panel']=join
            materials[label+'_material_outside_original_panel']=added
            joins[label]={'actual_join_to_original_panel_mm3':value,'actual_added_component_mm3':p.volume(added)}
            if role=='upper_toe':
                expected=(bounds[1][0]-bounds[0][0])*(18.50-18.30)*(bounds[1][2]-bounds[0][2])
                actual=p.volume(body.intersect(front))
                require(abs(actual-expected)<=VOLUME_TOL_MM3,'toe is not joined through original front post')
                joins[label].update(expected_join_to_declared_front_post_mm3=expected,
                    actual_join_to_declared_front_post_mm3=actual)
            new=p.single(new.fuse(body).clean())
    removed=p.volume(old.cut(new));added=p.volume(new.cut(old));balance=p.volume(old)+added-p.volume(new)
    require(removed<=VOLUME_TOL_MM3 and abs(balance)<=VOLUME_TOL_MM3,'additive panel material conservation failed')
    materials.update(candidate_panel=new,actual_added_panel_material=new.cut(old));preserved={}
    for side,sign in (('L',-1),('R',1)):
        for role,y in c['unmodified_existing_cover_patch_Y_mm'].items():
            args=(p,0,sign*c['existing_cover_functional_planes_abs_X_mm'],y,c['unmodified_existing_cover_patch_Z_search_mm'],-sign)
            before,brec=measured_patch(old,*args);after,arec=measured_patch(new,*args)
            preserved[side+'_'+role]={'before':brec,'after':arec,'whole_planar_material_difference':compare_face_material(before,after)}
    result=dict(parts);result['A_BACK_PANEL']=new
    require(set(result)==set(parts),'complete factory participant inventory changed')
    receipt={'candidate_name':NAME,'source_sha256':sha(__file__),'design_contract':c,
        'actual_added_only_panel_account':{'original_mm3':p.volume(old),'removed_mm3':removed,
            'added_mm3':added,'new_mm3':p.volume(new),'signed_balance_error_mm3':balance},
        'actual_positive_joins':joins,'original_cover_functional_face_material_preserved':preserved,
        'all_other_participants_unchanged':sorted(set(parts)-{'A_BACK_PANEL'}),
        'new_panel_single_valid_positive_solid':True,'all_pairs_complete':False,
        'physical_allowed_domain_proved':False,'strength_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    return result,materials,receipt


def endpoint_and_overtravel_checks(parts,keys,p,k1_contract_path,q_by_side):
    """Native contact and whole-KEY controls; never extend a source profile."""
    c=frozen_design(k1_contract_path);panel=parts['A_BACK_PANEL'];results={};materials={}
    for side in 'LR':
        q=q_by_side[side];require(0<=q<=12,'actual factory q must remain source-defined');contacts={}
        for end,at,normal in (('lower',0.,1.),('upper',12.,-1.)):
            if abs(q-at)>PLANE_IDENTITY_TOL_MM:continue
            lo,hi=handed_bounds(side,[[17.48,0.,4.02],[18.38,1.,4.38]])
            plane=c['declared_stop_contact_planes_Y_mm'][end]
            panel_patch,pr=measured_patch(panel,p,1,plane,[lo[0],hi[0]],[lo[2],hi[2]],normal)
            key_patch,kr=measured_patch(parts[side+'_KEY'],p,1,plane,[lo[0],hi[0]],[lo[2],hi[2]],-normal)
            equality=compare_face_material(panel_patch,key_patch)
            area=face_area(panel_patch.intersect(key_patch));expected=c['declared_contact_patch_area_mm2']
            require(abs(area-expected)<=AREA_IDENTITY_TOL_MM2,'actual native stop contact area differs')
            at_contact=p.strict_common(parts[side+'_KEY'],panel)
            require(at_contact['common_mm3']<=VOLUME_TOL_MM3,'nominal endpoint has positive penetration')
            controls=[]
            for delta in c['negative_control_overtravel_mm']:
                outside=at+(-delta if end=='lower' else delta);inside=at+(delta if end=='lower' else -delta)
                rejected=p.single(keys.candidate_q0[side].translate((0.,outside,0.)))
                free=p.single(keys.candidate_q0[side].translate((0.,inside,0.)))
                rejection=p.strict_common(rejected,panel);clear=p.strict_common(free,panel);expected_overlap=expected*delta
                require(rejection['common_mm3']>VOLUME_TOL_MM3 and rejection['common_mm3']>=expected_overlap-VOLUME_TOL_MM3,
                        'complete KEY/panel overtravel control did not reject')
                require(clear['common_mm3']<=VOLUME_TOL_MM3,'inward release control has panel penetration')
                label=side+'_'+end+'_'+str(delta).replace('.','p')
                materials[label+'_overtravel_KEY']=rejected;materials[label+'_overtravel_Common']=rejected.intersect(panel)
                materials[label+'_inward_KEY']=free
                controls.append({'overtravel_mm':delta,'KEY_q_outside_original_profile_mm':outside,
                    'KEY_q_inward_mm':inside,'expected_crossbar_stop_overlap_mm3':expected_overlap,
                    'whole_KEY_panel_overtravel_Common':rejection,'whole_KEY_panel_inward_Common':clear,
                    'complete_factory_outside_profile_constructed':False,'physical_motion_admissibility_claimed':False})
            contacts[end]={'panel_patch':pr,'KEY_patch':kr,'actual_contact_area_mm2':area,
                'actual_coplanar_material_identity':equality,'whole_KEY_panel_at_contact_Common':at_contact,
                'geometric_overtravel_and_inward_controls':controls}
        results[side]={'actual_q_mm':q,'endpoint_contacts':contacts}
    return results,materials
