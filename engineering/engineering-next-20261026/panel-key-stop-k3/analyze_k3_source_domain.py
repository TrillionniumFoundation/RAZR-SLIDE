"""Freeze the prospective K3 contact geometry and independent-domain derivation.

Pure source arithmetic only. This does not run a CAD kernel, establish physical
contact, reduce S4/K1 domains, or provide force/material/strength qualification.
"""
from __future__ import annotations
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def exact(x):return str(F(float(x)))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--k1-contract',type=Path,required=True)
    ap.add_argument('--source-domain',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    spec=importlib.util.spec_from_file_location('prepared_k3',HERE/'panel_key_travel_stops_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    c=module.frozen_design(args.k1_contract)
    lower,upper=c['front_crossbar_R_q0_mm'];pieces=c['additive_boxes_R_mm']
    x0,z0=c['declared_contact_patch_XZ_R_mm'][0];x1,z1=c['declared_contact_patch_XZ_R_mm'][1]
    nominal_area=(F(str(x1))-F(str(x0)))*(F(str(z1))-F(str(z0)))
    binary_area=(F(x1)-F(x0))*(F(z1)-F(z0))
    lower_plane=c['declared_stop_contact_planes_Y_mm']['lower'];upper_plane=c['declared_stop_contact_planes_Y_mm']['upper']
    nominal_q_bounds=[F(str(lower_plane))-F(str(lower[1])),F(str(upper_plane))-F(str(upper[1]))]
    binary_q_bounds=[F(lower_plane)-F(lower[1]),F(upper_plane)-F(upper[1])]
    assert nominal_q_bounds==[F(0),F(12)]
    K=12/79.75
    base={'descent':0.,'left_tab':3.,'right_tab':3.,'flanks':[0.,0.],
          'key_offsets':[0.,0.],'crosshead_offsets':[0.,0.],
          'telescope_offsets':None,'open_hold':False,'open_support':False,'expected_bodies':154}
    states={}
    def add(name,slide,**changes):
        state={**base,'slide':slide,**changes};state['actual_binary64_q_from_declared_factory_inputs']=[K*slide+d for d in state['key_offsets']]
        assert all(0<=q<=12 for q in state['actual_binary64_q_from_declared_factory_inputs'])
        assert all(abs(d)<=.035355339059327334 for d in state['key_offsets'])
        states[name]=state
    add('stow_tabs_0',0.,left_tab=0.,right_tab=0.)
    add('stow_tabs_3',0.)
    add('near',23.142044210239405)
    add('far',60.880681403413135)
    add('predock',79.75)
    add('open_installed',79.75,descent=8.2,open_hold=True,open_support=True,expected_bodies=161)
    slide_low=.1;dq_low=K*slide_low
    add('lower_L_contact_R_free',slide_low,key_offsets=[-dq_low,dq_low])
    add('lower_R_contact_L_free',slide_low,key_offsets=[dq_low,-dq_low])
    slide_high=79.65;dq_high=12.-K*slide_high
    add('upper_L_contact_R_free',slide_high,key_offsets=[dq_high,-dq_high])
    add('upper_R_contact_L_free',slide_high,key_offsets=[-dq_high,dq_high])
    contacts={}
    for pose,state in states.items():
        contacts[pose]={side:('lower' if q==0 else 'upper' if q==12 else None)
            for side,q in zip('LR',state['actual_binary64_q_from_declared_factory_inputs'])}
    lower_width=pieces['lower_post'][1][1]-pieces['lower_post'][0][1]
    upper_join_width=18.50-18.30
    plan={'schema':'razr-K3-prospective-independent-travel-stops-plan-v1',
        'functional_source_commit':module.S4,'candidate_name':module.NAME,
        'candidate_source_sha256':sha(HERE/'panel_key_travel_stops_v1.py'),
        'K1_source_sha256':module.K1_SOURCE_SHA,'K1_contract_sha256':sha(args.k1_contract),
        'pure_analysis_source_sha256':sha(__file__),'original_domain_evidence_sha256':sha(args.source_domain),
        'design_contract':c,
        'contact_geometry_derivation':{
            'declared_decimal_contact_area_exact_mm2':str(nominal_area),
            'binary64_coordinate_contact_area_exact_mm2':str(binary_area),
            'nominal_lower_clearance_function_mm':'q_side',
            'nominal_upper_clearance_function_mm':'12 - q_side',
            'declared_decimal_candidate_q_bounds_exact_mm':list(map(str,nominal_q_bounds)),
            'binary64_scalar_plane_minus_vertex_bounds_exact_mm':list(map(str,binary_q_bounds)),
            'binary64_scalar_upper_limit_minus_12_exact_mm':str(binary_q_bounds[1]-12),
            'native_transform_and_boolean_tolerance_not_certified_by_scalar_arithmetic':True,
            'source_ideal_bounds_do_not_define_current_physical_allowed_domain':True,
            'KEY_bridge_leg_to_stop_X_gap_nominal_mm':[.14,.14],
            'retained_split_original_crossbar_to_stop_X_gap_nominal_mm':[.10,.10],
            'axis_gaps_apply_only_to_declared_local_prisms':True,
            'upper_toe_original_front_post_expected_overlap_mm3':float(nominal_area*F('0.20')),
            'upper_toe_new_material_if_original_front_post_is_only_overlap_mm3':float(nominal_area*F('0.92')),
            'actual_panel_addition_and_lower_anchor_overlap_must_be_native_measured':True,
            'negative_controls':[{'delta_q_mm':d,'expected_crossbar_stop_penetration_mm3':float(nominal_area*F(str(d))),
                'larger_whole_KEY_panel_Common_must_be_retained_if_present':True} for d in c['negative_control_overtravel_mm']]},
        'independent_source_domain':{
            'variables':['s','dx_L','dq_L','dx_R','dq_R'],
            'shared_slide_mm':[0.,79.75],
            'slot_crosshead_abs_bound_mm':.0252814320072192,
            'slot_difference_abs_bound_mm':.035355339059327334,
            'side_coordinates':['q_L=K*s+dq_L','q_R=K*s+dq_R'],
            'prospective_contact_halfspaces':['q_L>=0','12-q_L>=0','q_R>=0','12-q_R>=0'],
            'no_L_R_offset_equality_or_contact_synchronization_added':True,
            'original_unclipped_slot_32_vertices_and_24_out_of_profile_retained_as_original_evidence':True,
            'corresponds_to_previous_60_vertex_clipped_nominal_model_only_if_new_contact_constraints_are_validated':True,
            'actual_reachability_force_branch_selection_and_tolerance_domain_proved':False,
            'zero_penetration_nominal_contact_is_unilateral_not_a_motion_schedule':True},
        'ten_finite_full_factory_states':states,'expected_contact_end_by_side':contacts,
        'original_complete_factory_and_STEP_pair_evaluations_planned':sum(s['expected_bodies']*(s['expected_bodies']-1) for s in states.values()),
        'retained_checks':['whole original panel and all K1 participants before modification',
            'four positive stop/panel material joins; upper toes through preserved original front posts',
            'one valid positive whole candidate panel; zero original material loss and signed volume balance',
            'four original cover contact patches: outward normals, clipped actual faces, both directed area differences',
            'actual endpoint KEY/panel contact patches and opposite unit normals, nominal area 0.324 mm2',
            'whole KEY/panel overtravel penetration at delta 0.001 and 0.01 mm, and inward-release Common',
            'all 11781 or 12880 pairs with original signed Common <=1e-7 predicate',
            'separate-process complete STEP readback and independent box reconstruction from frozen contract',
            'full source/43-package environment/owned lifecycle and original finite resource gates'],
        'overtravel_full_factory_outside_ContactProfile_domain_called':False,
        'runtime_policy':{'worker_seconds':1200,'worker_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,
            'startup_disk_MiB':256,'runtime_disk_MiB':100,'startup_incremental_memory_MiB':2048,
            'max_parallel_jobs':2,'hard_gates_may_not_be_raised_to_obtain_completion':True},
        'pre_execution_order':['review actual K2 finite endpoint results and retain any real failure',
            'screen proposed boxes against complete actual factory material records without claiming fit from AABBs',
            'root review of named K3 source/contract/reader/engineering-only export before native work'],
        'actual_native_K3_execution':False,'current_S4_or_K1_domain_reduced':False,
        'full_continuous_domain_clear':False,'physical_allowed_domain_proved':False,'strength_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json').write_text(json.dumps({
        'schema':'razr-K3-frozen-additive-panel-contract-v1','candidate_source_sha256':plan['candidate_source_sha256'],
        'design_contract':c,'actual_native_K3_execution':False},indent=2)+'\n')
    (args.output/'K3_SOURCE_DOMAIN_AND_EXECUTION_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'candidate_sha256':plan['candidate_source_sha256'],'nominal_q_bounds':list(map(str,nominal_q_bounds)),
        'binary64_upper_minus_12_exact_mm':str(binary_q_bounds[1]-12),'finite_states':len(states),
        'planned_full_pair_evaluations':plan['original_complete_factory_and_STEP_pair_evaluations_planned'],
        'native_K3_executed':False},indent=2))


if __name__=='__main__':main()
