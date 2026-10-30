"""Read-only K1/K3 material and source-domain audit; no CAD import or execution."""
import argparse
import ast
import datetime as dt
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile


def need(value,message):
    if not value:raise ValueError(message)


def ident(path):
    path=Path(path);data=path.read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def literal(path,name):
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('literal assignment absent:'+name)


def exact(value):
    return {'exact_rational':str(value),'display':float(value)}


def independent_profile(raw,q):
    r,hf,qc,m,p,stop=(raw[k] for k in ('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height'))
    need(0<=q<=raw['q_max'],'original finite profile domain')
    intercept=hf-m*qc+r*math.hypot(1,m)
    a=p-qc;b=a+r*m/math.hypot(1,m);c=p+(intercept-stop)/m
    need([a,b,c]==raw['breakpoints_q_mm'],'original binary64 breakpoints unchanged')
    if q>=c:return stop,0.,'lower_stop'
    if q>=b:return intercept+m*(p-q),-m,'ramp'
    if q<=a:return hf+r,0.,'plateau'
    dx=p-q-qc;root=math.sqrt(r*r-dx*dx)
    return hf+root,dx/root,'rounded_corner'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--s4',type=Path,required=True)
    parser.add_argument('--original-remote',type=Path,required=True)
    parser.add_argument('--r7-near-archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();need(not args.output.exists(),'new independent review name required')
    geo=args.repo/'engineering/engineering-followup-20261029-r9/geometry'
    helpers=geo/'source-originals'
    old=args.original_remote/'engineering/engineering-followup-20261028-r7/independent-review/blocker-ledger/positive-q-source-readback'
    k1=args.original_remote/'engineering/engineering-next-20261026/key-forward-loop-k1/key_forward_loop_v1.py'
    k3=helpers/'panel_key_travel_stops_v1.py'
    kc=json.loads((helpers/'KEY_FORWARD_LOOP_V1_CONTRACT.json').read_text())
    pc=json.loads((helpers/'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json').read_text())
    kb=json.loads((helpers/'K3FULL_K1_BINDING.json').read_text())
    need(ident(k1)['sha256']==kc['candidate_source_sha256']==pc['design_contract']['required_K1_source_sha256'],'frozen named K1 source')
    need(ident(k3)['sha256']==pc['candidate_source_sha256'],'frozen named K3 source')
    need(ident(helpers/'KEY_FORWARD_LOOP_V1_CONTRACT.json')['sha256']==pc['design_contract']['required_K1_contract_sha256'],'exact K1 contract')
    source_names=['cam_contact_profile.py','product_assembly.py','product_nominal_motion.py','verify_cam_coupling.py',
                  'product_split_assembly.py','verify_pawl_actuator.py','verify_serviceable_pawl.py','verify_endpoint_joint_pawl.py']
    source_bindings={}
    for name in source_names:
        s4=args.s4/'integration'/name;prior=old/'originals/source'/name
        need(s4.read_bytes()==prior.read_bytes(),'S4 and R7 retained source equality:'+name)
        source_bindings[name]={'S4':ident(s4),'R7_retained':ident(prior)}
    source_bindings['cam_coupling.py']={'S4':ident(args.s4/'integration/cam_coupling.py')}
    domain=json.loads((geo/'SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json').read_text())
    need(domain['source_model_only'] and not domain['physical_allowed_domain_proved'] and not domain['restoring_force_or_preload_proved'],'source domain scope retained')
    need(domain['profile_source']=={k:ident(args.s4/'integration/cam_contact_profile.py')[k] for k in ('bytes','sha256')},'profile source identity')
    states=literal(helpers/'full_stop_states.py','STATES')
    expected_stops=literal(helpers/'full_stop_states.py','EXPECTED_CONTACT_ENDS')
    need(set(states)==set(domain['states']) and len(states)==10,'complete original ten-state source roster')
    profiles={};state_rows={}
    for side in 'LR':
        profiles[side]=[]
        for index in range(2):
            path=old/'originals/profiles'/f'{side}_contact{index}.profile.original.json'
            raw=json.loads(path.read_text());retained=domain['profiles'][side][index]
            need(retained['complete_original_values']==raw,'complete original profile equality')
            independent_profile(raw,0.)
            a,b,c=raw['breakpoints_q_mm']
            branches=[{'branch':'plateau','interval':'(0,a]','a_mm':a},
                      {'branch':'rounded_corner','interval':'(a,b)','a_mm':a,'b_mm':b},
                      {'branch':'ramp','interval':'[b,c)','b_mm':b,'c_mm':c},
                      {'branch':'lower_stop','interval':'[c,12]','c_mm':c}]
            need(retained['positive_q_branches']==branches,'exact positive-q branch partition')
            profiles[side].append({'source':ident(path),'original':raw,'independently_checked_branches':branches})
    K=12/79.75;cam_half=(.425-.4)*math.hypot(1,K);yoke_half=(.425-.4)*math.sqrt(2)
    for name,spec in states.items():
        actual_q=[K*spec['slide']+v for v in spec['key_offsets']]
        need(actual_q==spec['actual_binary64_q_from_declared_factory_inputs'],'actual original state q:'+name)
        need(domain['states'][name]['source_state_inputs']==spec,'unaltered source state inputs:'+name)
        need(domain['states'][name]['K3_panel_Y_travel_stop_contacts']==expected_stops[name],'distinct K3 contact labels')
        checked={}
        for side,q in zip('LR',actual_q):
            checked[side]=[]
            for index,entry in enumerate(profiles[side]):
                h,slope,branch=independent_profile(entry['original'],q)
                h0=independent_profile(entry['original'],0.)[0];move=(-1 if side=='L' else 1)*(h-h0)
                independent={'contact_index':index,'q_mm':q,'q_binary64_hex':q.hex(),'selected_source_branch':branch,
                             'height_mm':h,'height_slope':slope,'reference_height_mm':h0,
                             'STOP_X_translation_mm':move,'SPRING_X_lower_endpoint_delta_mm':min(0.,move),
                             'SPRING_X_upper_endpoint_delta_mm':max(0.,move),'SPRING_is_OD_tolerance_envelope':True,
                             'physical_contact_or_force_implied':False}
                need(independent==domain['states'][name]['cam_STOP_i_and_SPRING'][side][index],'independent complete source motion mapping:'+name+side+str(index))
                checked[side].append(independent)
        state_rows[name]={'q_L_R_mm':actual_q,'K3_Y_travel_contacts':expected_stops[name],'cam_X_profiles':checked}
    k1_accounts={};member_bindings=[]
    with zipfile.ZipFile(args.r7_near_archive) as archive:
        for pose in ('near','far'):
            base=f'engineering/prerequisite-stow_tabs_3/prerequisite-{pose}'
            producer=None
            for kind in ('factory','readback'):
                name=base+f'/{kind}/worker/report.engineering.json';data=archive.read(name);wrapper=json.loads(data);record=wrapper['engineering_record']
                expected=kb['poses'][pose]['actual_'+('factory' if kind=='factory' else 'reader')+'_projection_sha256']
                need(hashlib.sha256(data).hexdigest()==expected,'original K1 saved projection identity')
                need(wrapper['derived_projection_not_raw_original'] and record['execution_completed'] and record['finite_pose_clear'],'actual inherited K1 finite completion')
                member_bindings.append({'archive_member':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'raw_original_reference':wrapper['original'],'projection_not_raw_runtime':True})
                if kind=='factory':producer=record
                else:need(record['native_STEP_readback_executed'] and not record['mismatches_to_factory'],'original independent K1 readback')
            accounts=producer['candidate_application']['material_accounts']
            for side in 'LR':
                row=accounts[side+'_KEY']
                need(abs(row['removed_mm3']-.594)<=1e-7 and abs(row['added_mm3']-2.623824)<=1e-7,'original actual K1 material account')
                need(all(row[k]==0 for k in ('retained_original_material_loss_mm3','unintended_loss_outside_declared_cutter_mm3','material_restored_inside_clearance_cut_mm3')),'retained K1 complete material checks')
            k1_accounts[pose]=accounts
    completed=[('lower_L_contact_R_free','producer-attempt1','reader-first-v2-attempt1'),
               ('lower_R_contact_L_free','producer-v2-attempt1','reader-lower-R-v2-attempt1'),
               ('upper_L_contact_R_free','producer-v2-attempt1','reader-upper-L-v2-attempt1')]
    k3_states=[]
    for name,pdir,rdir in completed:
        pp=geo/pdir/name/'report.json';rp=geo/rdir/'report.json'
        record=json.loads(pp.read_text());reader_campaign=json.loads(rp.read_text());reader=reader_campaign['states'][name]
        need(record['completed'] and record['finite_pose_clear'] and reader_campaign['completed'] and reader['completed'] and reader['finite_pose_clear'],'completed finite R9 state and independent readback')
        need(record['pairs']['count']==reader['pairs']['count']==11781 and len(reader['body_readbacks'])==154,'whole state inventory recorded')
        receipt=record['candidate_application'];account=receipt['actual_added_only_panel_account']
        need(account['removed_mm3']==0 and abs(account['added_mm3']-4.62456)<=1e-7,'complete recorded K3 addition-only account')
        patches=receipt['original_cover_functional_face_material_preserved']
        need(len(patches)==4 and all(all(value==0 for value in patch['whole_planar_material_difference'].values()) for patch in patches.values()),'four original oriented cover patches unchanged')
        need(all(row['actual_join_to_original_panel_mm3']>1e-7 for row in receipt['actual_positive_joins'].values()),'positive recorded K3 joins')
        native_contacts=record['endpoint_and_overtravel_checks']
        for side in 'LR':
            contact=expected_stops[name][side]
            need(set(native_contacts[side]['endpoint_contacts'])==({contact} if contact else set()),'recorded independent travel contact matches source state')
        k3_states.append({'state':name,'producer_report':ident(pp),'independent_reader_report':ident(rp),
                          'observed_added_panel_account':account,'observed_positive_joins':receipt['actual_positive_joins'],
                          'four_old_functional_patches':patches,'observed_endpoint_contacts':native_contacts,
                          'finite_state_complete_and_clear':True,'all_continuous_states_inferred':False})
    native_mapping=json.loads((geo/'NATIVE_PROFILE_FIRST_STATE.json').read_text())
    need(native_mapping['all_source_native_bounds_mappings_pass'] and not native_mapping['real_spring_free_length_stiffness_preload_or_force_proved'],'native mapping scope')
    gap=F(float(17.38))-(F(float(5.38))+12)
    need(gap==F(-1,2**50),'binary64 upper-stop real-coordinate distinction')
    result={'schema':'razr-r9-independent-k1-k3-material-and-domain-crossreview-v1','completed':True,
            'reviewed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'review_source':ident(__file__),
            'execution_kind':'read-only JSON/source/archived-projection inspection and independent standard-library arithmetic',
            'new_CAD_execution':False,'frozen_envelope_files_modified':False,
            'sources':{'K1':ident(k1),'K3':ident(k3),'K1_contract':ident(helpers/'KEY_FORWARD_LOOP_V1_CONTRACT.json'),
                       'K3_contract':ident(helpers/'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'),'S4_vs_R7':source_bindings,
                       'R9_ten_state_domain':ident(geo/'SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json'),
                       'R9_native_first_state_mapping':ident(geo/'NATIVE_PROFILE_FIRST_STATE.json'),
                       'original_state_roster':ident(helpers/'full_stop_states.py'),'K1_original_archive':ident(args.r7_near_archive),
                       'K1_original_projection_members':member_bindings},
            'K1':{'cut_box_R_q0_mm':literal(k1,'CUT'),'new_boxes_R_q0_mm':literal(k1,'ADDITIONS'),
                  'mirrored_L_by_X':True,'cutter_nominal_XYZ_mm':[1.10,1.52,.38],
                  'actual_original_web_nominal_XYZ_mm':[1.10,1.50,.36],
                  'nominal_removed_per_KEY_mm3':exact(F('1.10')*F('1.50')*F('.36')),
                  'inherited_actual_complete_material_accounts':k1_accounts,
                  'local_U_leg_section_XZ_mm':[.38,.36],'local_U_leg_area_mm2':exact(F('.38')*F('.36')),
                  'old_transverse_bridge_section_YZ_mm':[1.50,.36],'old_transverse_bridge_area_mm2':exact(F('1.50')*F('.36')),
                  'declared_local_section_ratio':exact(F('.38')/F('1.50')),
                  'inherited_yoke_tab_source_box_mm':[[13.2,15.8,4.05],[13.45,39.6,4.35]],
                  'inherited_yoke_tab_nominal_XZ_area_mm2':exact(F('.25')*F('.30')),
                  'local_dimensions_are_whole_KEY_minwall':False,'nominal_length_is_measured_unsupported_span':False,
                  'section_ratio_is_strength_ratio':False,'all_functional_faces_catalogued_by_protection_masks':False},
            'K3':{'declared_boxes_R_mm':pc['design_contract']['additive_boxes_R_mm'],
                  'nominal_contact_area_mm2':exact(F('.90')*F('.36')),
                  'panel_Y_planes_mm':{'lower_q0':5.,'upper_q12':17.38},
                  'panel_normals':{'lower':[0,1,0],'upper':[0,-1,0]},'KEY_normals_opposite':True,
                  'existing_cover_functional_planes_abs_X_mm':17.43,
                  'independently_read_completed_R9_states':k3_states,
                  'four_oriented_cover_patches_equal_complete_functional_surface_inventory':False,
                  'all_profile_states_or_real_specimen_stop_proved':False,
                  'binary64_frozen_upper_plane_minus_exact_real_5p38_plus_12_mm':exact(gap),
                  'native_zero_Common_results_overwritten_by_symbolic_gap':False,'uniform_transform_rounding_bound_proved':False},
            'positive_q_cam_profiles':profiles,'independent_ten_state_source_mapping':state_rows,
            'distinct_stops':{'cam_lower_stop':'height reaches lower_stop_height at q>=c around 0.642918; applied as side-signed X translation of STOP_i',
                              'K3_upper_travel_stop':'whole KEY front-crossbar upper Y face contacts fixed panel toe at q=12, Y=17.38',
                              'same_stop_or_same_axis':False,
                              'SPRING_representation':'radius 0.43 mm OD tolerance cylinder expanded between original and translated X endpoints; not force/deformation solution'},
            'software_domain':{'shared_slide_mm':[0.,79.75],'shared_descent_mm':[0.,8.2],'positive_descent_requires_slide_79p75':True,
                               'tabs_per_side_mm':[0.,3.],'flanks_per_side':[-1.,1.],
                               'q_each_side':'q_side=K*shared_slide+dq_side, 0<=q_side<=12, no clamping',
                               'K_binary64':K,'within_side_constraints':['abs(dx_side)<=cam_half+1e-7','abs(dx_side-dq_side)<=yoke_half+1e-7'],
                               'cam_half_mm':cam_half,'yoke_half_mm':yoke_half,
                               'real_relaxation_dq_half_with_two_TOL_additions_mm':cam_half+yoke_half+2e-7,
                               'real_projection_equals_binary64_accepted_set_proved':False,
                               'left_right_q_equality_required':False,'left_right_arbitrary_q_rectangle_independent_of_shared_slide':False,
                               'telescope_per_side':'three j in [.1-1e-7,2.9+1e-7], abs(sum(j)-8.5+descent)<=1e-7; both sides share descent',
                               'equal_telescope_allocation_physically_enforced':False,
                               'OPEN_accessories_require_slide_descent':[79.75,8.2],
                               'tabs_source_range_implies_collision_free_motion_or_correct_release_order':False,
                               'finite_contact_samples_prove_continuous_independent_domain':False},
            'physical_allowed_domain_proved':False,'force_friction_preload_or_restoring_branch_qualified':False,
            'full_tolerance_domain_proved':False,'global_minimum_wall_or_section_proved':False,
            'current_geometry_FE_strength_fatigue_qualified':False,'assembly_repair_domain_complete':False,
            'full_continuous_G2':False,'candidate_go':False,'manufacturing_go':False,
            'crossreview_disagreements_found':[],
            'new_execution_scope':'independent arithmetic and stored-evidence readback only; no new material construction or Boolean calls'}
    need('cadquery' not in sys.modules and not any(k.startswith('OCP') for k in sys.modules),'no CAD kernel loaded')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'completed':True,'original_profiles':4,'source_states':10,'reviewed_completed_native_states':len(k3_states),'CAD_loaded':False,'physical_allowed_domain_proved':False}))


if __name__=='__main__':main()
