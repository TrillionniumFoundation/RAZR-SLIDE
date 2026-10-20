#!/usr/bin/env python3
"""Independent EP4 scalar witness; no CAD, network, or native execution.

Uses standard-library composite Simpson/trapezoidal quadrature, independently
of the candidate's Gauss rule. Optional --source-root records identities and
compares only the candidate's arithmetic functions. Geometry bounds below are
derived analytically; sampled implementation checks do not certify obstacles
between poses. Writes JSON to stdout; caller can archive that exact output.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path


def simpson(fn, end=1., n=4096):
    step = end/n
    return step/3*math.fsum([fn(0.), fn(end), *[
        (4 if i % 2 else 2)*fn(i*step) for i in range(1, n)]])


def q(u):
    return 10*u**3-15*u**4+6*u**5


def qp(u):
    return 30*u*u*(1-u)*(1-u)


def qpp(u):
    return 60*u*(1-u)*(1-2*u)


def theta(u):
    return math.pi*(3*u*u-2*u*u*u)


def s_length(h, end=1., n=4096):
    return simpson(lambda u: math.sqrt(100+h*h*qp(u)**2), end, n)


def numbers(slide, descent, I, J):
    h=8.2-descent
    ts=s_length(h)
    tu=3.4/I
    turn=(201+slide-ts-tu)/2
    return {
        'slide_mm': slide, 'descent_mm': descent, 'S_rise_mm': h,
        'S_length_mm': ts, 'U_length_mm': tu,
        'U_start_world_Y_mm': turn,
        'bridge_straight_mm': turn-90,
        'B_straight_mm': turn-40-slide,
        'U_finite_head_world_Y_mm': turn+tu*J+.05,
        'length_sum_mm': 29+ts+(turn-90)+tu+(turn-40-slide),
    }


def independent_report():
    I=simpson(lambda u: math.sin(theta(u)))
    J=simpson(lambda u: math.cos(theta(u)), .5)
    tu=3.4/I
    states={label:numbers(s,d,I,J) for label,s,d in (
        ('STOW',0.,0.),('PREDOCK',79.75,0.),('OPEN',79.75,8.2))}
    ts_upper=math.sqrt(100+(10/7)*8.2**2)
    ts_lower=math.hypot(10,8.2)
    k_s=8.2/(10*math.sqrt(3))
    k_u=1.5*math.pi/tu
    n=4096
    f=lambda u: math.sin(theta(u))
    trap=(.5*(f(0.)+f(1.))+math.fsum(f(i/n) for i in range(1,n)))/n
    trap_error=((1.5*math.pi)**2+6*math.pi)/(12*n*n)
    tu_upper=3.4/(trap-trap_error)
    tu_lower=3.4/(trap+trap_error)
    # This bound survives the analytic integration truncation budget, not
    # only agreement between two numerical quadrature rules.
    middle_lower=(201-ts_upper-tu_upper)/2-90
    assert middle_lower > 0
    assert min(x['B_straight_mm'] for x in states.values()) > 3
    assert max(abs(x['length_sum_mm']-100) for x in states.values()) < 1e-10
    assert 1-.05*max(k_s,k_u) > 0
    return {
        'scope': 'independent mathematical necessary conditions; no CAD or hardware executed',
        'declared_inputs': {'A_YZ_mm':[51.,1.45], 'B_local_YZ_mm':[40.,4.85],
            'S_world_Y_mm':[80.,90.], 'L_mm':100., 'W_mm':12., 't_mm':.1,
            'ordered_slide_mm':[0.,79.75], 'ordered_descent_at_full_slide_mm':[0.,8.2]},
        'quadrature': {'method':'stdlib composite Simpson, 4096 panels',
            'I':I,'J':J,'U_length_mm':tu,
            'S_length_difference_4096_vs_8192_mm':s_length(8.2)-s_length(8.2,n=8192),
            'U_I_trapezoidal_4096_estimate':trap,
            'U_I_analytic_trapezoidal_truncation_bound':trap_error,
            'U_length_interval_from_truncation_bound_mm':[tu_lower,tu_upper],
            'machine_directed_rounding_used':False},
        'poses':states,
        'continuous_bounds': {
            'basis':'monotonicity in ordered motion, Jensen/chord, polynomial derivative bounds',
            'S_length_at_h8_2_chord_lower_mm':ts_lower,
            'S_length_at_h8_2_Jensen_upper_mm':ts_upper,
            'middle_straight_lower_including_U_truncation_budget_mm':middle_lower,
            'B_tail_lower_using_Jensen_mm':(201+79.75-ts_upper-tu_upper)/2-119.75,
            'STOW_finite_head_upper_using_S_chord_mm':(201-ts_lower-tu)/2+tu*J+.05,
            'S_max_abs_curvature_upper_per_mm':k_s,
            'S_radius_lower_mm':1/k_s,
            'U_max_abs_curvature_per_mm':k_u,
            'U_min_radius_mm':1/k_u,
            'finite_offset_Jacobian_lower':1-.05*max(k_s,k_u),
            'S_finite_Y_range_mm':[80.,90.],
            'S_to_return_lane_min_Z_separation_mm':3.3,
            'max_middle_with_S_end90_and_head94_independent_of_L_mm':4-tu*J-.05,
            'reverse_uses_same_geometric_parameter_set':True,
            'continuous_external_obstacle_clearance_proved':False},
        'endpoint_bounds': {
            'old_A_plate_battery_overlap_mm3':12*6*.25,
            'new_A_plate_world_Y_mm':[15.,37.8],
            'new_A_plate_battery_nominal_Y_gap_mm':.2,
            'new_A_web_world_Y_mm':[37.3,37.75],
            'new_A_web_M2_hole_nominal_Y_gap_mm':.2,
            'B_low_lane_to_endpoint_nominal_Z_gap_mm':.05,
            'A_endpoint_to_OPEN_return_lane_nominal_Z_gap_mm':.05},
        'OPEN_comparison': {
            'S_is_straight_at_h_zero':True,
            'single_U_straight_A_mm':(100-tu+68.75)/2,
            'S_plus_U_accumulated_straight_A_mm':29+10+states['OPEN']['bridge_straight_mm'],
            'same_analytic_free_material_path_as_frozen_EP3_OPEN':True,
            'implication':'OPEN obstacle intersections are not eliminated merely by adding S or changing endpoints'},
        'unresolved':['real stack and fatigue','finite guides/support and their occupied volume',
            'actual shell crossings','continuous clearance from all external parts',
            'manufacturing tolerance and loads','physical motion and reverse forces'],
    }


def compare_implementation(root, report):
    config_path=root/'design/product_routing_ep4.json'
    module_path=root/'integration/product_routing_ep4.py'
    sources=(config_path,module_path)
    initial_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    config=json.loads(config_path.read_text())
    expected={'A_anchor_local_mm':[0.,51.,1.45],'B_anchor_local_mm':[0.,40.,4.85],
        'S_world_Y_interval_mm':[80.,90.],'free_length_mm':100.,'width_mm':12.,
        'thickness_assumption_mm':.1,'U_B_local_Z_interval_mm':[1.45,4.85]}
    for key,value in expected.items():
        if config['route'].get(key) != value:
            raise ValueError('independent witness inputs do not match source: '+key)
    spec=importlib.util.spec_from_file_location('ep4_review_arithmetic_only', module_path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config=module.load_config(config_path)
    keys=('S_length_mm','U_length_mm','U_start_world_Y_mm','bridge_straight_mm',
          'B_straight_mm','U_finite_head_world_Y_mm','length_sum_mm')
    differences={}
    inversion_position=0.
    inversion_tangent=0.
    inversion_normal=0.
    inversion_curvature=0.
    exact_join_position=0.
    exact_join_curvature=0.
    minimum_station_gap=math.inf
    polygon_lengths={}
    # These extra states exercise the numerical S inverse at different rise;
    # they are explicitly not a sweep or a continuous collision certificate.
    poses=[('STOW',0.,0.),('PREDOCK',79.75,0.),('OPEN',79.75,8.2),
           ('SLIDE_MID',39.875,0.),('SEAT_MID',79.75,4.1)]
    for label,s,d in poses:
        actual=module.pose_numbers(s,d,config)
        reference=numbers(s,d,report['quadrature']['I'],report['quadrature']['J'])
        differences[label]={key:actual[key]-reference[key] for key in keys}
        assert max(abs(v) for v in differences[label].values()) < 1e-9
        h=8.2-d
        for j in range(17):
            u=j/16
            physical_s=29+s_length(h,u)
            point,tangent,normal,k=module.evaluate_material_station(physical_s,actual,config)
            slope=h*qp(u)/10
            scale=math.sqrt(1+slope*slope)
            inversion_position=max(inversion_position,math.dist(point,(0,80+10*u,1.45+h*q(u))))
            inversion_tangent=max(inversion_tangent,math.dist(tangent,(0,1/scale,slope/scale)))
            inversion_normal=max(inversion_normal,math.dist(normal,(0,-slope/scale,1/scale)))
            inversion_curvature=max(inversion_curvature,abs(k-h*qpp(u)/100/scale**3))
        sections,sections_report=module.route_sections(s,d,config)
        labels=sections_report['exact_join_material_labels_mm']
        turn=actual['U_start_world_Y_mm']
        expected_points=[(0,51,1.45),(0,80,1.45),(0,90,1.45+h),
                         (0,turn,1.45+h),(0,turn,4.85+h),(0,40+s,4.85+h)]
        for physical_s,point in zip(labels,expected_points):
            result=module.evaluate_material_station(physical_s,actual,config)
            exact_join_position=max(exact_join_position,math.dist(result[0],point))
            exact_join_curvature=max(exact_join_curvature,abs(result[3]))
        gaps=[float(b-a) for a,b in zip(sections['s'],sections['s'][1:])]
        minimum_station_gap=min(minimum_station_gap,min(gaps))
        polygon_lengths[label]=sections_report['centerline_polygon_length_mm']
        assert all(v>0 for v in gaps)
    assert max(inversion_position,inversion_tangent,inversion_normal,inversion_curvature) < 1e-9
    assert max(exact_join_position,exact_join_curvature) < 1e-9
    if minimum_station_gap <= 1e-10:
        raise ValueError('numerically duplicate material stations would enter the finite polygon')
    final_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    if final_hashes != initial_hashes:
        raise RuntimeError('EP4 source changed during the arithmetic comparison; rerun after it is frozen')
    return {
        'scope':'pure arithmetic implementation comparison; no native functions called',
        'source_sha256':initial_hashes,
        'pose_numeric_difference_from_independent_Simpson':differences,
        'S_inverse_at_17_independent_arc_labels_each_pose':{
            'max_point_error_mm':inversion_position,'max_unit_tangent_error':inversion_tangent,
            'max_unit_normal_error':inversion_normal,'max_curvature_error_per_mm':inversion_curvature},
        'max_exact_join_position_error_mm':exact_join_position,
        'max_exact_join_abs_curvature_per_mm':exact_join_curvature,
        'minimum_distinct_station_spacing_in_checked_poses_mm':minimum_station_gap,
        'finite_centerline_polygon_lengths_mm':polygon_lengths,
        'all_requested_arithmetic_comparisons_passed':True,
        'native_or_hardware_executed':False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,help='Optional EP4 source root; only pure arithmetic is imported')
    args=parser.parse_args()
    report=independent_report()
    report['witness_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.source_root:
        report['implementation_comparison']=compare_implementation(args.source_root.resolve(),report)
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
