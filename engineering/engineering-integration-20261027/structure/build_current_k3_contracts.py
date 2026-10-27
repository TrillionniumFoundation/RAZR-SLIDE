"""Freeze current K3 evidence identities and unsatisfied engineering inputs.

This is an evidence/readiness contract, not FE, a physical test or release.
No old structural material assignment or unobserved device value is invented.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
CP2='a9c6b67ddb96fb603512135d1ed2846fcaa97428'
EXPECTED={
    'design/product_interfaces.json':'a5eeba7042ee44d1b8317e5e5d084b0bddbf6609550652a50f721a29af6f1bd7',
    'engineering/engineering-integration-20261025/structural/CURRENT_EP5_INPUT_CONTRACT.json':'c71a2b3ed07b00d9d467fea747fbf0d429310b772cae7777421f450afee0bbbd',
    'engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py':'51b3d8c3385fe249ed938418ce5ba69ee8ee41e7b12a901c3c34e9421985c16d',
    'integration/product_qualification.py':'74cf704a68f5de17904f2df1265ae79c7e08e715b940c84dbd757af459b6e078',
    'integration/ep5_input_closure.py':'b9e352d38690ac91b2bd3928f9ca7d3f0ecf7b64ba4a00487568accb77df37b2',
    'integration/product_assembly.py':'fc5391d3be98810ada06ca27e65de9a77d2f599c4d1890bb31a4d87ef14791b4',
    'engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity/record.json':'b4200d53ab68ec95733eb00d26b3e53ee35a3055d448c8b70d81b024910cad7f',
    'engineering/engineering-integration-20261025/product/OLED_SOURCE_RECHECK.json':'e8084435bb87080fd3996b17158eb0eb3b1648dbba7cc4d7484d65e8a866daf3',
}
CANDIDATE_SOURCES={
    'key_forward_loop_v1.py':'3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578',
    'KEY_FORWARD_LOOP_V1_CONTRACT.json':'17e1532ed82eff1298e9525456d6953df56437082ef2918f3d04839cff200455',
    'panel_key_travel_stops_v1.py':'59946f42f8bff88b0cdb8bcd2ad7f578e22e6f64e65832a6b6087426e282e5a5',
    'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json':'0f3ec4af155a2e92650f49ada7042e6d1fc1f8ad94cb43f6716a77985ecc5b84',
}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(path):
    raw=path.read_bytes()
    return {'bytes':len(raw),'sha256':sha(raw)}
def read(path):return json.loads(path.read_text())
def write(root,name,data):
    p=root/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return {'name':name,**identity(p)}
def constants(path):
    out={}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            try:out[node.targets[0].id]=ast.literal_eval(node.value)
            except (ValueError,TypeError):pass
    return out
def criterion(unit,direction):
    return {'unit':unit,**{k:None for k in (('minimum','maximum') if direction=='range' else (direction,))},'source':None,'source_locator':None}
def requirement():return {'value':None,'source':None,'source_locator':None}


def build(root,inspection,domain,baseline_source_root=None,candidate_source_root=None):
    repo=baseline_source_root or root/'repository-source'/S4
    candidate_root=candidate_source_root or root/'source'
    bindings={}
    for path,digest in EXPECTED.items():
        info=identity(repo/path)
        if info['sha256']!=digest:raise ValueError('immutable source changed: '+path)
        bindings[path]={'source_commit':S4,**info}
    candidate={}
    for name,digest in CANDIDATE_SOURCES.items():
        info=identity(candidate_root/name)
        if info['sha256']!=digest:raise ValueError('named candidate changed: '+name)
        candidate[name]=info
    structural=read(repo/'engineering/engineering-integration-20261025/structural/CURRENT_EP5_INPUT_CONTRACT.json')
    interfaces=read(repo/'design/product_interfaces.json')
    original_record=read(repo/'engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity/record.json')
    g3=constants(repo/'engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py')
    g45=constants(repo/'integration/product_qualification.py')
    assert len(g3['METRICS'])==14 and len(g45['G4_METRICS'])==14 and len(g45['G5_METRICS'])==8
    specimens=['mainboard','display','touch','COF','pack_A','pack_B','USB_port_board']
    missing_identity=[k for k,v in interfaces['donor'].items() if v is None]
    assert len(missing_identity)==10 and len(interfaces['interfaces'])==12
    assert all(x['actual_pinmap'] is None and x['extension_approved'] is False for x in interfaces['interfaces'])
    poses={};inventory={}
    for p in sorted(inspection.glob('K3FULL_*_INSPECTION.json')):
        d=read(p);pose=d['pose']
        if d['run_id']!=40285103942 or d['actual_finite_state_clear'] is not True or d['official_ZIP_SHA_size_all_CRC_and_member_SHA_verified'] is not True:
            raise ValueError('only actual fully inspected finite records can be bound')
        mp=inspection/('K3FULL_'+pose+'_ENGINEERING_MANIFEST.json');mi=identity(mp)
        if mi['sha256']!=d['engineering_manifest_sha256']:raise ValueError('original manifest binding differs')
        members=read(mp)['members'];bodies={}
        for name,member in members.items():
            if name.startswith('factory/worker/bodies/') and name.endswith('.step'):
                if len(Path(name).parts)!=4:raise ValueError('unexpected body export hierarchy')
                bodies[Path(name).stem]={'member_path':name,**member}
        if len(bodies)!=d['declared_pose']['expected_bodies']:raise ValueError('complete current body count differs')
        poses[pose]={'artifact_id':d['artifact_id'],'artifact_name':d['artifact_name'],
            'original_execution_run_id':d['run_id'],'original_diagnostic_head_sha':d['head_sha'],
            'ZIP_bytes':d['official_ZIP_bytes'],'ZIP_sha256':d['official_ZIP_sha256'],
            'manifest':{'name':mp.name,**mi},'inspection':{'name':p.name,**identity(p)},
            'declared_controls':d['declared_pose'],'full_body_count':len(bodies),
            'unordered_pair_count_per_worker':len(bodies)*(len(bodies)-1)//2,
            'original_finite_state_passed_and_independently_read':True,
            'current_task_reexecuted_native_pairs':False}
        inventory[pose]=bodies
    if len(poses)!=10:raise ValueError('all ten original inspections required')
    stow=inventory['stow_tabs_3'];opened=inventory['open_installed'];roles=sorted(set().union(*(set(x) for x in inventory.values())))
    assert len(stow)==154 and len(opened)==161 and len(roles)==161 and set(stow)<=set(opened)
    material_template=copy.deepcopy(next(iter(structural['all_nominal_material_assignments'].values())))
    assert all(v is None for v in material_template.values())
    materials={name:{'current_whole_geometry_reference':(stow[name] if name in stow else opened[name]),
                     'inventory_pose':'stow_tabs_3' if name in stow else 'open_installed',
                     'physical_material_inputs':copy.deepcopy(structural['all_nominal_material_assignments'].get(name,material_template))} for name in roles}
    if any(any(x is not None for x in r['physical_material_inputs'].values()) for r in materials.values()):
        raise ValueError('unexpected sourced material must be explicitly reviewed before contract regeneration')
    domain_names=['S4_TELESCOPE_BINARY64_SOURCE_DOMAIN_REBUILT.json','S4_TELESCOPE_OUTER_VERTICES_DUAL_CHECK_REBUILT.json']
    domain_binding={name:identity(domain/name) for name in domain_names}
    assert domain_binding[domain_names[0]]['sha256']=='f403e94ad24987a5d6ea04840df22324ad383e9c824562b560d61d1ac8bb2550'
    assert domain_binding[domain_names[1]]['sha256']=='9476fd2dc63c96820e7fafbb45ab56bb9bfad48a0c0803d697821b8033aaf521'
    current_binding={'functional_baseline_commit':S4,'named_KEY_candidate':'key_forward_loop_v1',
        'named_panel_candidate':'panel_key_travel_stops_v1','candidate_source_and_contract_bytes':candidate,
        'current_geometry_reference_poses':poses,'all_ten_manifests_reused_not_native_rerun':True,
        'named_candidate_code_and_actual_material_bytes_required_in_every_physical_plan':True,
        'S4_EP5_routing_candidate_id_alone_sufficient_to_identify_K3':False,
        'main_or_default_geometry_changed_by_contract':False}
    coverage={'schema':'razr-current-K3-independent-domain-coverage-ledger-v1',
        'candidate_binding':current_binding,
        'source_control_ranges':{'shared_slide_mm':[0,79.75],'shared_descent_mm':[0,8.2],
            'descent_positive_requires_slide_79p75':True,'left_and_right_tab_each_mm':[0,3],
            'left_and_right_slot_flank_each':[-1,1],
            'independent_offsets_for_each_side':['dx_crosshead','dq_KEY'],
            'slot_predicates_in_source_order':['abs(dx) <= (cam.G-cam.R)*math.hypot(1,cam.K)+TOL','abs(dx-dq) <= (cam.G-cam.R)*math.sqrt(2)+TOL'],
            'KEY_q_source_expression':'cam.K*slide_mm+dq, then each original ContactProfile.evaluate(q); never clamp',
            'independent_explicit_telescope_joint_arrays_per_side':3,
            'standalone_planner_predicate_tolerances':{'per_joint':1e-9,'sum':1e-8},
            'actual_factory_predicates_preserved_in_order':['product_assembly.native_scene: each .1-TOL <= x <= 2.9+TOL; abs(sum(values)-8.5+descent_mm)<=TOL',
                'verify_cam_coupling.prototype: each .1-TOL <= x <= 2.9+TOL; abs(sum(j)-.3-(8.2-d))<=TOL'],
            'actual_factory_TOL':1e-7,'standalone_planner_is_not_actual_full_factory_domain':True},
        'domain_evidence_reused':domain_binding,
        'exact_outer_telescope_domain':{'variables':['d','j_L1','j_L2','j_L3','j_R1','j_R2','j_R3'],
            'halfspaces':18,'vertices':216,'continuous_relaxation_dimension':7,
            'ideal_zero_tolerance_28_vertices_are_not_full_factory_coverage':True,
            'joint_total_halfwidth_expression':'Fraction(float(1e-7)) + 14 * 2**(-48)',
            'vertices_reenumerated_in_this_task':False,'exact_outer_vertices_imply_collision_clear':False},
        'complete_stage_relaxation':{'SLIDE_dimension':15,'SEATING_dimension':15,
            'counted_coordinates':'one continuous stage coordinate + 2 tabs + 2 flanks + 2 KEY offsets + 2 crosshead offsets + 6 telescope joints',
            'binary64_acceptance_not_replaced_by_algebraic_equality':True,
            'physical_mechanism_domain_proved':False},
        'positive_q_piecewise_evidence':{'source_commit':CP2,
            'repository_path':'engineering/engineering-integration-20261026/domain/POSITIVE_Q_BRANCH_DOMAIN.json',
            'git_blob_sha':'e3a157479c557cb3e655898e816a0b204010205c','bytes':277493,
            'interior_branch_interval_breaks_mm':[0,.0011145618000001356,.09055728089999172,.6429179606749895,.64291796067499,12],
            'branch_labels_in_interiors':[['plateau','plateau'],['rounded_corner','rounded_corner'],['ramp','ramp'],['lower_stop','ramp'],['lower_stop','lower_stop']],
            'breakpoint_and_nextafter_semantics_remain_in_original_source_evidence':True,
            'tiny_distinct_last_breakpoint_interval_removed':False,
            'nominal_shared_slide_branch_combinations':25,'nominal_feasible_combinations':17,
            'nominal_17_cell_proof_extended_to_factory_tolerance_shell':False,
            'spring_OD_envelope_is_physical_constitutive_model':False},
        'pair_coverage':{'STOW_or_SLIDE_154_body_total_pairs':11781,
            'pairs_with_at_least_one_of_3_K3_changed_bodies':456,
            'OPEN_161_body_total_pairs':12880,'OPEN_pairs_with_at_least_one_changed_body':477,
            'ten_finite_states_actual_passed':10,
            'new_exact_rectangular_subset_component_pairs_per_coordinate_interpretation':48,
            'subset_pair_proof_equals_whole_body_pair_proof':False,
            'full_15D_all_pair_continuous_proof_complete':False,
            'remaining_checks':['all current panel/KEY/STOP/SPRING whole materials with independent q_L,q_R and original piecewise branches',
                'K3 new panel components vs every current other whole body, including ROOT_INNER and accessories',
                'all telescope allocations over true native/prototype tolerance shells with original shared controls',
                'all remaining unchanged-body pairs without assuming nominal L1/K1 coverage extends to independent controls',
                'assembly, disassembly, holding, reversal and actual tolerances/contact loading']},
        'software_source_domain_reduced_by_this_contract':False,
        'K3_native_endstop_negative_controls_establish_physical_stop_force_or_tolerance':False,
        'physical_allowed_domain_proved':False,'candidate_go':False}
    thresholds={'G3':{'schema_reference':g3['CURRENT_PLAN_SCHEMA'],'required_roles':g3['CURRENT_REQUIRED_ROLES'],
        'requirements':{k:requirement() for k in ('minimum_cycles','minimum_samples_per_phase','minimum_hands_off_duration_s','maximum_sampling_gap_s','maximum_alignment_error_s')},
        'criteria':{m:criterion(u,d) for m,(u,d) in g3['METRICS'].items()},
        'actual_execution':False,'status':'unknown_missing_same_candidate_physical_inputs_and_execution'},
        'G4':{'schema_reference':'razr-product-qualification-plan-v1','phase_order':list(g45['PHASES']),'power_modes':list(g45['MODES']),
            'function_protocols':{f:{'identity':None,'source':None,'source_locator':None} for f in g45['FUNCTIONS']},
            'requirements':{k:requirement() for k in ('minimum_cycles_per_mode','minimum_samples_per_phase','maximum_sampling_gap_s','maximum_alignment_error_s')},
            'criteria':{m:criterion(u,d) for m,(_,u,d) in g45['G4_METRICS'].items()},
            'prerequisite':'actual G3 pass of same specimen and exact current K3 binding','actual_execution':False,'status':'blocked_missing_real_G3_and_OEM_inputs'},
        'G5':{'schema_reference':'razr-product-qualification-plan-v1','phase_order':list(g45['PHASES']),
            'requirements':{k:requirement() for k in ('required_cycles','minimum_specimens','maximum_exposure_sampling_gap_s','minimum_samples_per_exposure_phase','maximum_alignment_error_s')},
            'criteria':{m:criterion(u,d) for m,(u,d) in g45['G5_METRICS'].items()},
            'exposure':{m:criterion(u,'range') for m,(u,_,_) in g45['EXPOSURE'].items()},
            'checkpoints_cycles':[],'critical_dimensions':{},
            'prerequisite':'actual G3 and G4 pass for each same specimen and exact current K3 binding',
            'actual_execution':False,'status':'blocked_missing_real_G3_G4_life_and_process_inputs'}}
    old_observation=interfaces['donor_evidence']
    physical={'schema':'razr-current-K3-same-specimen-and-qualification-input-contract-v1',
        'immutable_source_bindings':bindings,'current_K3_binding':current_binding,
        'old_donor_identity_projection':{'original_record_sha256':EXPECTED['engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity/record.json'],
            'donor_model':original_record['donor']['model'],'observed_utc':old_observation['observed_utc'],
            'software_and_transport_observation_reused':True,'physical_platform_frozen':False,
            'raw_runtime_or_serial_material_republished':False},
        'current_endpoint_observation':identity(root/'KNOWN_DEVICE_ENDPOINT_OBSERVATION.json'),
        'targeted_source_search':identity(root/'TARGETED_SAME_SPECIMEN_SOURCE_SEARCH.json'),
        'new_same_specimen_physical_observations':0,
        'ten_identity_fields':{k:None for k in missing_identity},
        'seven_part_originals':{role:{'same_specimen_record':None,'original_photos_and_label':None,
            'PN_revision':None,'measured_dimensions_and_uncertainties':None,
            'orientation_and_datum':None,'OEM_terminal_source':None,'original_phone_function_baseline':None} for role in specimens},
        'twelve_interfaces':{x['id']:{'intended_function':x['function'],'source_kind':x['source_kind'],
            'actual_OEM_terminal_map':None,'actual_orientation_and_contact_side':None,
            'source_document_PN_revision_locator':None,'same_specimen_continuity_and_function_originals':None,
            'extension_qualified':False} for x in interfaces['interfaces']},
        'flex_and_OLED':{'coupon_owned_identity':interfaces['coupon']['nets'],
            'coupon_is_OEM_assignment':False,'reference_CAD_stackup_mm':interfaces['coupon']['reference_CAD_stackup_mm'],
            'requested_copper_um':interfaces['coupon']['copper_thickness_requested_um'],
            'supplier_complete_stackup_confirmed':False,'actual_PI_adhesive_coverlay_and_lots':None,
            'actual_finished_thickness_and_uncertainty':None,'actual_neutral_axis_radius_strain_cycles_temperature':None,
            'same_specimen_OLED_COF_FPC_final_envelope_PN_revision':None,
            'selected_connector_mating_direction_contact_numbering_and_ratings':None,
            'published_OLED_screening_is_not_same_specimen_selection':True,
            'existing_screening_record':bindings['engineering/engineering-integration-20261025/product/OLED_SOURCE_RECHECK.json'],
            'cell_budget':interfaces['cell_budget'],
            'low_current_coupon_test_limit_is_G3_G5_or_OEM_rating':False},
        'physical_gate_contracts':thresholds,
        'all_limit_values_require_predeclared_source_path_SHA_and_locator':True,
        'required_acquisition_contract':{'sample_rate_and_gaps':None,'synchronized_timebase':None,
            'calibration_validity_and_uncertainty':None,'measured_channel_positions':None,
            'raw_data_originals_and_video':None,'preregistration_and_review_originals':None,
            'failure_missing_data_repair_and_replacement_kept_separate':True,
            'missing_or_limit_crossing_uncertainty_is_unknown_not_pass':True},
        'original_metrics_units_directions_and_gate_order_changed':False,
        'complete_current_physical_contract_freeze_possible':False,
        'source_and_missing_input_schema_frozen_for_review':True,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    current_structural={'schema':'razr-current-K3-structural-and-tolerance-input-contract-v1',
        'current_K3_binding':current_binding,'immutable_baseline_structural_contract':bindings['engineering/engineering-integration-20261025/structural/CURRENT_EP5_INPUT_CONTRACT.json'],
        'STOW_body_count':154,'OPEN_installed_body_count':161,
        'OPEN_only_roles':sorted(set(opened)-set(stow)),
        'all_current_roles_material_inputs':materials,
        'material_roles_with_no_selected_physical_values':len(materials),
        'original_13_loadcases_retained':structural['loadcases'],
        'K3_additional_stop_load_and_tolerance_cases':{name:{'force_N':None,'moment_N_mm':None,'application_and_support':None,
            'impact_or_quasistatic_basis':None,'material_process_and_clearance_sources':None} for name in
            ('left_lower_stop','right_lower_stop','left_upper_stop','right_upper_stop','asymmetric_or_simultaneous_LR_end_contact')},
        'contact_requirements':structural['contact_requirements'],
        'tolerance_contract':structural['tolerance_contract'],
        'current_geometry_evidence':{'whole_STOW_three_body_STEP_readback':identity(root/'K3_WHOLE_STEP_SUBSET_READBACK.json'),
            'all_482_faces_inventory':identity(root/'CURRENT_K3_STEP_FACE_AUDIT.json'),
            'local_exact_serialized_boundary_separations':identity(root/'CURRENT_K3_LOCAL_SERIALIZED_SECTIONS.json'),
            'exact_declared_source_prism_continuous_subproblem':identity(root/'K1_K3_EXACT_SOURCE_FEATURE_AUDIT.json')},
        'functional_surface_coverage':{'old_cover_support_patches_native_checked':4,
            'new_lower_and_upper_contact_patches_native_checked_per_side':2,
            'all_482_faces_semantic_function_assigned':False,
            'additional_required_roles':['all KEY pawl/contact/cam/yoke surfaces and guide/retention interfaces',
                'all panel bearing/fastener/cover interfaces and new stop load transfer regions',
                'all assembly and service/removal interfaces over source control domains'],
            'material_protection_masks_are_not_complete_contact_surface_inventory':True},
        'wall_metric_contract':{'global_wall_definition':None,'edge_or_corner_exclusion_rule':None,
            'manufacturing_minimum_rule_source':None,'local_0p38x0p36_equals_global_minimum':False,
            'bounding_box_extent_equals_wall':False,'selected_LOCAL_serialized_0p25_chord_equals_global_minimum':False,
            'all_unresolved_faces_must_remain_in_coverage_ledger':True},
        'verification_requirements':structural['verification_requirements']+[
            'bind actual K1 KEY and K3 panel geometry; remesh any changed material/contact region',
            'check all current 154/161 participants, contact regimes, real factory tolerance shells and worst-case tolerances',
            'verify independent current full fields and physical input traceability; original normalized solver qualification alone is insufficient'],
        'existing_FE_inherited_as_current_K3_qualification':False,
        'current_K3_complete_FE_mesh_built':False,'real_inputs_complete':False,
        'current_K3_structural_qualification_passed':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    return [write(root,'CURRENT_K3_FULL_DOMAIN_COVERAGE.json',coverage),
            write(root,'CURRENT_K3_PHYSICAL_AND_GATE_INPUT_CONTRACT.json',physical),
            write(root,'CURRENT_K3_STRUCTURAL_INPUT_CONTRACT.json',current_structural)]


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--task-root',type=Path,required=True);ap.add_argument('--inspection-dir',type=Path,required=True);ap.add_argument('--domain-dir',type=Path,required=True)
    ap.add_argument('--baseline-source-root',type=Path);ap.add_argument('--candidate-source-root',type=Path)
    a=ap.parse_args();print(json.dumps({'written':build(a.task_root,a.inspection_dir,a.domain_dir,a.baseline_source_root,a.candidate_source_root),'native_executed':False},indent=2))
