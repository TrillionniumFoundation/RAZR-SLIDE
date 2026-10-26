#!/usr/bin/env python3
"""Scalar follow-up to first EP4 PREDOCK; no CAD or hardware execution.

Only b (B-anchor Y) and free length L vary. S interval, U lane separation,
A anchor, B board material coordinates, endpoint orientation and thickness
remain fixed. Native wall extents and rounded Common were supplied by root.
"""
import hashlib
import json
import math
from pathlib import Path


def integrate(fn, end=1., n=8192):
    step=end/n
    return step/3*math.fsum([fn(0.),fn(end),*[
        (4 if i%2 else 2)*fn(i*step) for i in range(1,n)]])


def cap_area(radius, chord_distance):
    return radius**2*math.acos(chord_distance/radius)-chord_distance*math.sqrt(radius**2-chord_distance**2)


def main():
    theta=lambda u:math.pi*(3*u*u-2*u*u*u)
    I=integrate(lambda u:math.sin(theta(u)))
    J=integrate(lambda u:math.cos(theta(u)),.5)
    U=3.4/I
    S=integrate(lambda u:math.sqrt(100+(8.2*30*u*u*(1-u)*(1-u))**2))
    excess=S-10
    head_extra=U*J+.05
    upper_sum=2*94-2*head_extra-51+excess+U
    lower_difference=2*3-51+79.75+excess+U
    b_upper=(upper_sum-lower_difference)/2
    b_required=36+15.35+.2
    L_upper=upper_sum-b_required
    L_lower=b_required+lower_difference
    assert b_required>b_upper and L_lower>L_upper
    assert abs(b_upper-(94-head_extra-79.75/2-3))<1e-12
    head_common=.25*cap_area(1.75,1.3)
    removed=.25*(cap_area(1.95,1.3)-cap_area(1.95,1.75))
    max_relief_x=math.sqrt(1.95**2-1.3**2)
    assert abs(head_common-.1808118563)<1e-9
    assert max_relief_x<5.4
    report={
        'scope':'put the complete PCB after the B transverse wall; fixed S+U and endpoint orientation; only B anchor Y and free length vary',
        'native_or_hardware_executed':False,
        'baseline_EP4_module_sha256':'f8286416e8d4f835b5a280f3c76e7dd69aaebda25ac2217f40f33e19e92251b8',
        'baseline_EP4_config_sha256':'7504d0714a6a61bf8742d2ab2f69dff245aa32dec449a34158c784803fe4240d',
        'parent_supplied_native_inputs':{
            'B_transverse_wall_local_Y_mm':[14.7,15.35],
            'requested_board_to_wall_Y_clearance_mm':.2,
            'A_M2_head_1_web_Common_mm3_rounded':.1808118563},
        'fixed_inputs':{'A_anchor_Y_mm':51.,'B_board_material_Y_mm':[24.,36.],
            'S_world_Y_mm':[80.,90.],'slide_mm':79.75,'stow_rise_mm':8.2,
            'U_lane_difference_mm':3.4,'thickness_mm':.1,
            'STOW_finite_head_limit_mm':94.,'PREDOCK_minimum_B_tail_mm':3.},
        'turn':{'I':I,'J':J,'U_length_mm':U,'S_STOW_length_mm':S,
            'S_excess_mm':excess,'finite_U_head_beyond_turn_start_mm':head_extra},
        'B_anchor_length_constraints':{
            'STOW_head_requires_L_plus_b_at_most_mm':upper_sum,
            'PREDOCK_tail_requires_L_minus_b_at_least_mm':lower_difference,
            'therefore_b_at_most_mm':b_upper,
            'board_after_wall_requires_b_at_least_mm':b_required,
            'incompatible_b_interval_gap_mm':b_required-b_upper,
            'at_required_b_L_at_least_mm':L_lower,
            'at_required_b_L_at_most_mm':L_upper,
            'incompatible_L_interval_gap_mm':L_lower-L_upper,
            'at_required_b_and_head_limited_L_B_tail_mm':(L_upper+51-b_required-79.75-excess-U)/2,
            'at_required_b_and_tail_limited_L_STOW_head_Y_mm':(L_lower+51+b_required-excess-U)/2+head_extra,
            'boundary_b_and_L_mm':[b_upper,upper_sum-b_upper],
            'decisive_identity':'Y_U(PREDOCK)=Y_U(STOW)+79.75/2; S excess and L cancel',
            'no_solution_with_only_b_and_L_changed':True,
            'placing_board_on_other_side_of_wall_evaluated':False,
            'other_stack_route_or_board_orientation_disproved':False},
        'A_head_web_and_relief':{
            'coordinate_frame':'A endpoint local, after factory Y reflection',
            'web_X_mm':[-6.,6.],'web_Y_mm':[-13.7,-13.25],'web_Z_mm':[.8,3.3],
            'existing_transfer_window_X_mm':[-5.4,5.4],
            'existing_transfer_window_Z_mm':[1.1,1.75],
            'head_center_XY_mm':[0.,-15.],'head_radius_mm':1.75,'head_Z_mm':[.85,1.45],
            'analytic_head_web_Common_mm3':head_common,
            'relief_radius_mm':1.95,'root_proposed_relief_Z_mm':[.85,1.65],
            'same_removed_material_for_relief_top_1_45_or_1_65':True,
            'predicted_removed_carrier_volume_mm3':removed,
            'maximum_relief_abs_X_inside_web_mm':max_relief_x,
            'remaining_lower_web_each_side_min_width_mm':6-max_relief_x,
            'unaffected_side_column_each_width_mm':.6,
            'unaffected_side_column_each_section_mm2':.6*.45,
            'positive_jaw_web_Z_overlap_mm':.05,
            'positive_web_plate_Z_overlap_mm':.4,
            'proposed_side_probe_each_volume_mm3':.2*.2*(3.2-.82),
            'proposed_bearing_annulus_volume_mm3':math.pi*(1.75**2-1.1**2)*.05,
            'nominal_radial_head_clearance_mm':.2,
            'both_side_connections_retained_in_declared_geometry':True,
            'native_validity_or_190_pairs_executed_here':False,
            'strength_retention_or_manufacturing_proved':False},
        'witness_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
