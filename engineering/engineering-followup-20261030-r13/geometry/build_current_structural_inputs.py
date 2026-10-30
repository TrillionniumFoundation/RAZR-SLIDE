"""Bind nominal material routes and complete local section evidence to originals."""
from fractions import Fraction as F
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
R11=Path('/workspace/scratch/f11ac2a81fe4/RAZR-SLIDE/engineering/engineering-followup-20261030-r11/geometry-proof')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def file(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def enc(x):
    if isinstance(x,F):return {'exact':str(x),'display':float(x)}
    if isinstance(x,dict):return {k:enc(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [enc(v) for v in x]
    return x
def rectangle(u,v):
    u,v=F(u),F(v)
    return {'rectangle_dimensions_mm':[u,v],'area_mm2':u*v,
            'central_second_moments_mm4':[u*v**3/12,v*u**3/12],
            'elastic_rectangle_section_moduli_mm3':[u*v*v/6,v*u*u/6],
            'axial_average_stress_per_applied_force_per_mm2':1/(u*v),
            'no_force_value_or_material_allowable_assigned':True}
def main():
    factory=json.loads((HERE/'inputs/report.json').read_text());decl=json.loads((HERE/'MODIFIED_REGION_DECLARATIONS.json').read_text())
    sections=json.loads((HERE/'exact-sections-attempt1/report.json').read_text())
    native=[json.loads((HERE/f'native-{fmt}-attempt1/report.json').read_text()) for fmt in ('brep','step')]
    assert all(r['completed'] and not r['failures'] for r in native)
    lineage={'reports':[file(R11/'roi-producer-v2/report.json'),file(R11/'roi-reader-v2/report.json')],'same_complete_input_BREP_bytes':{}}
    for side in 'LR':
        old=R11/f'roi-inputs-v1/{side}_KEY.brep';current=HERE/f'inputs/{side}_KEY.brep'
        assert old.read_bytes()==current.read_bytes()
        lineage['same_complete_input_BREP_bytes'][side]={'old':file(old),'current':file(current)}
    previous=json.loads((R11/'roi-producer-v2/report.json').read_text());assert previous['completed'] and previous['all_registered_native_material_gates_passed']
    inherited_neck={s:previous['sides'][s]['ROIs']['neck'] for s in 'LR'}
    # These are exact geometric rectangle integrals, not strength results.
    sections_named={
        'each_new_U_leg_normal_Y':rectangle('.38','.36'),
        'front_crossbar_normal_X':rectangle('.38','.36'),
        'old_transverse_web_normal_X_before_K1_cut':rectangle('1.5','.36'),
        'inherited_yoke_neck_normal_Y':rectangle('.25','.30'),
        'K3_lower_post_normal_Z':rectangle('.9','.6'),
        'K3_upper_toe_normal_Y_and_each_contact_patch_XZ':rectangle('.9','.36'),
        'original_front_post_normal_Z':rectangle('1.0','1.2')}
    source_changed_regions={
        'K1_entire_source_cutter':{'R_bounds_mm':[[F('17.38'),F('13.99'),F('4.01')],[F('18.48'),F('15.51'),F('4.39')]],
            'source_cutter_volume_mm3':F('1.10')*F('1.52')*F('.38'),'actual_original_web_target_removed_mm3':F('1.10')*F('1.5')*F('.36'),
            'entire_cutter_empty_in_declared_current_window_model':True,'current_new_native_actual_removed_volume_recomputed':False},
        'K1_three_new_prisms':{'all_covered_in_full_modified_windows':True,
            'each_leg_to_old_web_positive_overlap_dimensions_mm':[F('.38'),F('1.5'),F('.36')],
            'each_leg_to_old_web_positive_overlap_mm3':F('.38')*F('1.5')*F('.36'),
            'each_front_crossbar_to_leg_overlap_mm3':F('.38')*F('.38')*F('.36'),
            'open_leg_span_between_crossbar_end_and_old_web_start_mm':F('14')-F('5.38'),
            'span_is_geometric_not_qualified_beam_end_condition':True},
        'K3_lower_post':{'entire_added_prism_and_local_original_panel_thickness_covered':True,
            'declared_panel_local_thickness_mm':F('.65'),'post_embed_into_original_panel_mm':F('.65')-F('.5'),
            'positive_join_to_panel_mm3':F('.9')*F('.6')*(F('.65')-F('.5')),
            'contact_Z_interval_mm':[F('4.02'),F('4.38')],
            'geometric_contact_to_panel_top_lever_interval_mm':[F('4.02')-F('.65'),F('4.38')-F('.65')],
            'native_original_join_readback_mm3':{s:factory['candidate_application']['actual_positive_joins'][s+'_lower_post']['actual_join_to_original_panel_mm3'] for s in 'LR'}},
        'K3_upper_toe':{'entire_added_prism_and_entire_original_front_post_overlap_covered':True,
            'post_overlap_Y_mm':F('18.5')-F('18.3'),'positive_join_mm3':F('.9')*F('.36')*F('.2'),
            'toe_geometric_length_outside_original_front_post_mm':F('18.3')-F('17.38'),
            'native_original_join_readback_mm3':{s:factory['candidate_application']['actual_positive_joins'][s+'_upper_toe']['actual_join_to_original_panel_mm3'] for s in 'LR'},
            'not_a_joint_strength_or_bond_life_result':True}}
    paths=[
        {'id':'KEY_modified_material_route','nodes':['old inboard transverse web','inboard U leg','front crossbar','outboard U leg','old outboard transverse web'],
         'all_four_adjacent_links_have_positive_volume_overlap_in_complete_region_model':True,
         'route_is_part_of_the_current_whole_KEY':True,'actual_force_sharing_between_legs_known':False},
        {'id':'lower_travel_stop_nominal_reaction_route','nodes':['KEY front crossbar at q=0','Y=5 coplanar contact patch','K3 lower post','positive embedded post/base overlap','local panel base'],
         'contact_is_unilateral_and_force_requires_external_boundary_conditions':True,'crossbar_contact_and_panel_material_routes_are_distinct':True,
         'through_panel_to_actual_frame_fastener_reactions_qualified':False},
        {'id':'upper_travel_stop_nominal_reaction_route','nodes':['KEY front crossbar near q=12','Y=17.38 coplanar contact patch','K3 upper toe','positive overlap with old front post','front post and local panel base'],
         'contact_is_unilateral_and_force_requires_external_boundary_conditions':True,
         'source_binary64_q12_plane_gap_is_not_silently_snapped':True,'through_panel_to_actual_frame_fastener_reactions_qualified':False},
        {'id':'inherited_input_transmission_context','nodes':['B cam groove','captured telescope/crosshead follower','KEY diagonal yoke','0.25 x 0.30 neck','original KEY contact features'],
         'inherited_neck_complete_native_ROI_is_bound_to_same_KEY_bytes':True,
         'complete_functional_force_path_or_actuator_relocking_proved':False}]
    required={k:None for k in ('material_PN_grade_revision_lot','elastic_plastic_fatigue_and_creep_properties','process_build_direction_heat_treatment_and_surface_finish',
        'actual_joint_method_and_residual_stress','slide_and_stop_force_time_histories','impact_mass_velocity_and_energy','left_right_asymmetric_and_simultaneous_loads',
        'contact_pressure_distribution_friction_and_wear','spring_PN_free_solid_lengths_wire_diameter_active_coils_stiffness_preload_end_fixity',
        'manufacturing_tolerances_datums_and_correlations','minimum_wall_definition_and_acceptance_limit','full_current_FE_mesh_contact_BCs_solver_and_validation')}
    report={'schema':'razr-r13-current-K1-K3-nominal-load-route-and-local-section-inputs-v1','completed':True,'source_sha256':sha(__file__),
        'current_geometry_binding':file(HERE/'INPUT_MANIFEST.json'),'whole_factory_original_report':file(HERE/'inputs/report.json'),
        'complete_region_declarations':file(HERE/'MODIFIED_REGION_DECLARATIONS.json'),
        'complete_section_ledger':file(HERE/'exact-sections-attempt1/report.json'),'independent_section_review':file(HERE/'MODIFIED_SECTIONS_INDEPENDENT_REVIEW.json'),
        'native_region_readbacks':[file(HERE/f'native-{fmt}-attempt1/report.json') for fmt in ('brep','step')],
        'nominal_material_and_contact_routes':paths,'all_current_named_K1_K3_cut_add_regions':source_changed_regions,
        'exact_declared_decimal_rectangle_section_properties':sections_named,
        'each_new_leg_section_area_ratio_to_inherited_neck':F('.38')*F('.36')/(F('.25')*F('.30')),
        'ratio_is_not_strength_or_global_minimum_ratio':True,
        'complete_local_directional_chords':[{k:v for k,v in r.items() if k in ('region','coordinate_interpretation','directional_chord_minima_mm','directional_chord_minima_without_window_planes_mm')} for r in sections['results']],
        'inherited_neck_evidence':{'lineage':lineage,'old_actual_native_ROI_records':inherited_neck,
            'prior_execution_relabelled_as_R13':False,'full_Y_interval_mm':[15.945,39.0],'native_boolean_identity_is_not_exact_mathematical_filling':True},
        'original_K3_additive_material_account':factory['candidate_application']['actual_added_only_panel_account'],
        'original_cover_face_material_evidence':factory['candidate_application']['original_cover_functional_face_material_preserved'],
        'functional_surface_scope':{'new_stop_contact_rectangle_XZ_R_mm':[[17.48,4.02],[18.38,4.38]],'nominal_area_mm2':F('.324'),
            'contact_normals_panel_lower_upper':[[0,1,0],[0,-1,0]],'contact_normals_KEY_lower_upper':[[0,-1,0],[0,1,0]],
            'cover_support_planes_abs_X_mm':F('17.43'),'source_masks_are_not_a_complete_all_functional_face_catalogue':True},
        'required_actual_inputs_not_filled':required,
        'scope':{'complete_current_named_modified_window_models':True,'complete_axis_sections_and_directional_chords_of_those_models':True,
            'all_inherited_part_cuts_and_full_parent_CSG_reconstructed':False,'actual_native_material_filling_identity_bridge_proved':False,
            'whole_KEY_or_panel_global_minimum_wall':False,'whole_structure_weakest_effective_load_section':False,
            'material_strength_stiffness_fatigue_or_current_FE_qualified':False,'physical_allowed_domain':False,
            'full_15D_G2':False,'G3':False,'G4':False,'G5':False,'manufacturing_go':False}}
    p=HERE/'CURRENT_NOMINAL_LOAD_PATH_AND_SECTION_INPUTS.json';assert not p.exists();p.write_text(json.dumps(enc(report),indent=2)+'\n')
    print(json.dumps({'completed':True,'complete_modified_windows':len(decl['regions']),'actual_missing_input_fields':len(required),'sha256':sha(p)}))
if __name__=='__main__':main()
