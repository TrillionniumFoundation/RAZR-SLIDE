"""EP5 research: forward B endpoint, two G2 turns, finite tapered ribbon.

This is a new geometry study; none of its FPC dimensions or shell channels is
supplier-qualified. The original EP4 route, complete endpoint parts, baseline
OLED and allocation solids are preserved as explicit references. All release
flags remain false. No sampled-pose success is a continuous-motion certificate.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys
import time
import traceback

import numpy as np
import product_routing_ep4 as ep4
import ep5_input_closure as input_closure

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'design/product_routing_ep5.json'
TOL = 1e-7
GO_KEYS = ep4.GO_KEYS
POSES = {'STOW': (0., 0.), 'PREDOCK': (79.75, 0.), 'OPEN': (79.75, 8.2)}
FIXED_ROUTE = {
    'A_anchor_local_mm': [0, 51, 1.45], 'B_anchor_local_mm': [0, 35, 1.8],
    'S_world_Y_interval_mm': [76, 86], 'B_low_lane_z_mm': .9,
    'B_high_lane_z_mm': 5.35, 'free_length_mm': 164,
    'total_material_length_mm': 188, 'stiffened_length_each_end_mm': 12,
    'middle_width_mm': 10.8, 'endpoint_width_mm': 12,
    'taper_length_each_end_mm': 4, 'thickness_assumption_mm': .1,
    'STOW_first_U_start_world_y_mm': 86.5,
    'PREDOCK_second_U_start_B_local_y_mm': 30,
    'base_stations': 129, 'curve_parameter_stations_each': 49,
    'taper_stations_each': 17, 'Gauss_Legendre_order': 96}

FIXED_RELIEF = {"A_head_web":True,"closed_KEY_endcaps":True,"A_center_channel_lo_hi_mm":[[-5.6,75.8,0.75],[5.6,94.4,8.1]],"B_floor_channel_lo_hi_mm":[[-5.6,-0.1,-1.2],[5.6,86.2,1.1]],"B_front_lap_channel_lo_hi_mm":[[-5.6,-0.1,1],[5.6,15.55,5.55]],"minimum_wall_strength_and_process_qualified":False}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def load_config(path=CONFIG):
    c = json.loads(Path(path).read_text())
    if c.get('schema') != 'razr-product-routing-ep5-v1':
        raise ValueError('unknown EP5 research configuration')
    if c.get('route') != FIXED_ROUTE:
        raise ValueError('EP5 research geometry differs from its implementation')
    if c.get('relief') != FIXED_RELIEF:
        raise ValueError('EP5 finite shell or KEY relief differs from its implemented identity')
    if any(c.get(k) is not False for k in GO_KEYS):
        raise ValueError('EP5 research cannot grant a release')
    if c.get('constraints') != ep4.load_config()['constraints']:
        raise ValueError('product constraints differ from the frozen baseline')
    if sha(ep4.__file__) != c['basis_ep4_sha256']:
        raise ValueError('EP4 reference source identity differs')
    if c['domain']['finished_cabin_outer_bounds_local_mm'] != [-36.995,36.995,0,94.25,-1.15,8]:
        raise ValueError('finished cabin bounds changed')
    changes = c['research_changes']
    if (changes['selected_supplier_FPC'] is not False or
            changes['26_individual_conductors_routed'] is not False or
            changes['new_material_dimensions_are_not_qualified_requirements'] is not True or
            c['relief']['minimum_wall_strength_and_process_qualified'] is not False):
        raise ValueError('research geometry cannot be relabelled as qualified')
    return c


def pose_numbers(slide, descent, c=None):
    c = c or load_config(); r = c['route']
    if isinstance(slide, bool) or isinstance(descent, bool):
        raise ValueError('boolean pose is not a physical distance')
    slide, descent = float(slide), float(descent)
    if not (0. <= slide <= 79.75 and 0. <= descent <= 8.2) or (descent > 0. and slide != 79.75):
        raise ValueError('outside ordered slide and seating program')
    a, b = r['A_anchor_local_mm'], r['B_anchor_local_mm']
    rise = 8.2-descent
    s_rise = rise+r['B_low_lane_z_mm']-a[2]
    order = r['Gauss_Legendre_order']
    integral = float(ep4.u_integral(order=order)[1])
    up = (r['B_high_lane_z_mm']-r['B_low_lane_z_mm'])/integral
    down = (r['B_high_lane_z_mm']-b[2])/integral
    ls = ep4.s_arc_length(s_rise, order=order)
    first = r['S_world_Y_interval_mm'][0]-a[1]
    by = b[1]+slide
    separation = (r['free_length_mm']-first-ls+r['S_world_Y_interval_mm'][1]-up-down-by)/2.
    home_ls = ep4.s_arc_length(8.2+r['B_low_lane_z_mm']-a[2], order=order)
    home_sep = (r['free_length_mm']-first-home_ls+r['S_world_Y_interval_mm'][1]-up-down-b[1])/2.
    second_start_local = r['STOW_first_U_start_world_y_mm']-home_sep
    second_end_local = r['PREDOCK_second_U_start_B_local_y_mm']
    c2local = second_start_local+(second_end_local-second_start_local)*slide/79.75
    c2 = slide+c2local
    c1 = c2+separation
    bridge = c1-r['S_world_Y_interval_mm'][1]
    final = by-c2
    if min(first, bridge, separation, final) < 0:
        raise ValueError('negative physical segment in EP5 route')
    if min(first, final) <= r['taper_length_each_end_mm']:
        raise ValueError('taper must remain wholly in each positive endpoint straight')
    maximum_k = max(1.5*math.pi/up, 1.5*math.pi/down,
                    abs(s_rise)/(10.*math.sqrt(3.)))
    return {
        'slide_mm':slide, 'descent_mm':descent, 'B_rise_mm':rise, 'S_rise_mm':s_rise,
        'A_endpoint_world_mm':list(a), 'B_endpoint_world_mm':[b[0],by,b[2]+rise],
        'A_straight_mm':first, 'S_length_mm':ls, 'bridge_straight_mm':bridge,
        'U1_length_mm':up, 'middle_reverse_straight_mm':separation,
        'U2_length_mm':down, 'B_straight_mm':final,
        'U1_start_world_Y_mm':c1, 'U2_start_world_Y_mm':c2,
        'U1_start_B_local_Y_mm':c1-slide, 'U2_start_B_local_Y_mm':c2local,
        'length_sum_mm':first+ls+bridge+up+separation+down+final,
        'target_free_length_mm':r['free_length_mm'],
        'continuous_abs_curvature_upper_bound_per_mm':maximum_k,
        'minimum_centerline_radius_continuous_lower_bound_mm':1./maximum_k,
        'finite_thickness_Jacobian_continuous_lower_bound':1.-r['thickness_assumption_mm']*maximum_k/2.,
        'Gauss_Legendre_order':order, 'formal_directed_rounding_certificate':False,
        'length_derivation':'first+S+(c1-S_end)+U1+(c1-c2)+U2+(B_y-c2)=164'}


def joins(numbers, c=None):
    c = c or load_config()
    lengths = [numbers[k] for k in ('A_straight_mm','S_length_mm','bridge_straight_mm',
                                   'U1_length_mm','middle_reverse_straight_mm','U2_length_mm',
                                   'B_straight_mm')]
    result = np.r_[0., np.cumsum(lengths)]
    result[-1] = c['route']['free_length_mm']
    return result


def evaluate_material_station(distance, numbers, c=None):
    c = c or load_config(); r = c['route']; d = float(distance)
    if not 0. <= d <= r['free_length_mm']:
        raise ValueError('material label outside the free ribbon')
    j = joins(numbers, c); a = np.asarray(r['A_anchor_local_mm'], float)
    angle = curvature = 0.; order = r['Gauss_Legendre_order']
    rise = numbers['B_rise_mm']
    if d <= j[1]:
        point = a+np.array([0., d, 0.])
    elif d < j[2]:
        u = ep4.s_parameter_at_arc(d-j[1], numbers['S_rise_mm'], order)
        slope = numbers['S_rise_mm']*ep4.quintic_d1(u)/10.
        angle = math.atan(slope)
        curvature = numbers['S_rise_mm']*ep4.quintic_d2(u)/100./(1.+slope*slope)**1.5
        point = np.array([0.,r['S_world_Y_interval_mm'][0]+10.*u,a[2]+numbers['S_rise_mm']*ep4.quintic(u)])
    elif d <= j[3]:
        point = np.array([0.,r['S_world_Y_interval_mm'][1]+d-j[2],rise+r['B_low_lane_z_mm']])
    elif d < j[4]:
        length = numbers['U1_length_mm']; u = (d-j[3])/length
        iy, iz = ep4.u_integral(u, order)
        point = np.array([0.,numbers['U1_start_world_Y_mm']+length*iy,rise+r['B_low_lane_z_mm']+length*iz])
        angle = math.pi*(3*u*u-2*u*u*u); curvature = math.pi*(6*u-6*u*u)/length
    elif d <= j[5]:
        point = np.array([0.,numbers['U1_start_world_Y_mm']-(d-j[4]),rise+r['B_high_lane_z_mm']])
        angle = math.pi
    elif d < j[6]:
        length = numbers['U2_length_mm']; u = (d-j[5])/length
        iy, iz = ep4.u_integral(u, order)
        point = np.array([0.,numbers['U2_start_world_Y_mm']-length*iy,rise+r['B_high_lane_z_mm']-length*iz])
        angle = math.pi+math.pi*(3*u*u-2*u*u*u); curvature = math.pi*(6*u-6*u*u)/length
    else:
        point = np.array([0.,numbers['U2_start_world_Y_mm']+d-j[6],numbers['B_endpoint_world_mm'][2]])
        angle = 2.*math.pi
    tangent = np.array([0.,math.cos(angle),math.sin(angle)])
    normal = np.cross([1.,0.,0.],tangent)
    return point,tangent,normal,float(curvature)


def material_width(distance, c=None):
    c = c or load_config(); r = c['route']
    d = np.asarray(distance, float); edge = np.minimum(d,r['free_length_mm']-d)
    u = np.clip(edge/r['taper_length_each_end_mm'],0.,1.)
    return r['endpoint_width_mm']+(r['middle_width_mm']-r['endpoint_width_mm'])*ep4.quintic(u)


def route_sections(slide, descent, c=None):
    c = c or load_config(); r = c['route']; n = pose_numbers(slide,descent,c); j = joins(n,c)
    q = np.linspace(0.,1.,r['curve_parameter_stations_each'])
    taper = np.linspace(0.,r['taper_length_each_end_mm'],r['taper_stations_each'])
    stations = ep4.merged_material_stations(np.r_[
        np.linspace(0.,r['free_length_mm'],r['base_stations']),j,taper,r['free_length_mm']-taper,
        [j[1]+ep4.s_arc_length(n['S_rise_mm'],float(u),r['Gauss_Legendre_order']) for u in q],
        j[3]+n['U1_length_mm']*q,j[5]+n['U2_length_mm']*q],j)
    values = [evaluate_material_station(float(s),n,c) for s in stations]
    center = np.asarray([v[0] for v in values]); tangent = np.asarray([v[1] for v in values])
    normal = np.asarray([v[2] for v in values]); k = np.asarray([v[3] for v in values])
    width_axis = np.tile([1.,0.,0.],(len(stations),1))
    widths = material_width(stations,c); t = r['thickness_assumption_mm']
    corners = center[:,None,:]+np.array([-1,1,1,-1])[None,:,None]*widths[:,None,None]/2.*width_axis[:,None,:]
    corners += np.array([-1,-1,1,1])[None,:,None]*t/2.*normal[:,None,:]
    jac = 1.-k[:,None]*np.array([-t/2,-t/2,t/2,t/2])[None,:]
    if not np.allclose(center[[0,-1]],[n['A_endpoint_world_mm'],n['B_endpoint_world_mm']],atol=1e-10,rtol=0):
        raise ValueError('arc-length construction missed an endpoint')
    if float(np.min(jac)) <= 0: raise ValueError('finite material Jacobian is nonpositive')
    sections = {'s':stations,'u':stations/r['free_length_mm'],'center':center,
        'tangent':tangent,'width_axis':width_axis,'normal':normal,'corners':corners,
        'material_width_mm':widths,'jacobian':jac,'curvature_per_mm':k,
        'normal_derivative':-k[:,None]*tangent,'twist_rad_per_mm':np.zeros(len(stations))}
    report = {**n,'material_station_count':len(stations),'exact_join_material_labels_mm':j.tolist(),
        'end_tangents':tangent[[0,-1]].tolist(),'end_normals':normal[[0,-1]].tolist(),
        'end_width_axes':width_axis[[0,-1]].tolist(),'minimum_sampled_Jacobian':float(np.min(jac)),
        'centerline_polygon_length_mm':float(np.sum(np.linalg.norm(np.diff(center,axis=0),axis=1))),
        'global_arc_length_material_labels':True,'G2_join_curvature_zero':True,
        'taper_in_straight_endpoint_regions_only':True,
        'width_taper_is_a_cut_shape_not_longitudinal_stretch':True,
        'smooth_between_station_clearance_proved':False,'actual_flex_stack_or_fatigue_qualified':False}
    return sections,report


def arithmetic_report(c=None):
    c = c or load_config(); r = c['route']
    states = {label:pose_numbers(*pose,c) for label,pose in POSES.items()}
    flat_d = 8.2+r['B_low_lane_z_mm']-r['A_anchor_local_mm'][2]
    critical = pose_numbers(79.75,flat_d,c)
    extrema = [*states.values(),critical]
    return {'schema':'razr-ep5-arithmetic-v1','candidate_id':c['candidate_id'],
        'source_sha256':{'integration/product_routing_ep5.py':sha(__file__),'design/product_routing_ep5.json':sha(CONFIG)},
        'poses':states,'interior_seating_S_flat_critical_point':critical,
        'research_changes':c['research_changes'],
        'continuous_necessary_bounds':{
            'minimum_bridge_straight_mm':min(n['bridge_straight_mm'] for n in extrema),
            'minimum_B_straight_mm':min(n['B_straight_mm'] for n in extrema),
            'minimum_turn_separation_mm':min(n['middle_reverse_straight_mm'] for n in extrema),
            'minimum_Jacobian_lower_bound':min(n['finite_thickness_Jacobian_continuous_lower_bound'] for n in extrema),
            'maximum_first_U_start_B_local_Y_mm':max(n['U1_start_B_local_Y_mm'] for n in extrema),
            'minimum_second_U_start_B_local_Y_mm':min(n['U2_start_B_local_Y_mm'] for n in extrema),
            'basis':'During slide all segment lengths and turn coordinates are affine; during seating S_length is monotone in abs(S_rise), whose interior zero is included.',
            'formal_interval_rounding_proved':False,'obstacle_or_self_clearance_proved':False},
        'native_checks_executed':False,'complete_motion_accepted':False,
        'actual_FPC_source_definition_changed':False,**{k:False for k in GO_KEYS}}


def continuous_route_certificate(c=None):
    """Analytic finite-thickness path/domain bounds, not obstacle clearance.

    Every nonadjacent segment pair is separated by Y or Z. Adjacent segments
    meet at the same G2 cross section. For the S and each U, 1-eta*kappa>0
    preserves the signed monotonic coordinate of both finite thickness edges.
    This establishes geometric non-self-intersection for this ideal planar
    family; it says nothing about FPC constitutive behavior or drive forces.
    """
    c = c or load_config(); r = c['route']; ar = arithmetic_report(c)
    values = [*ar['poses'].values(),ar['interior_seating_S_flat_critical_point']]
    b = r['B_anchor_local_mm']; a = r['A_anchor_local_mm']; t = r['thickness_assumption_mm']
    first_min_world = min(n['U1_start_world_Y_mm'] for n in values)
    first_min_local = min(n['U1_start_B_local_Y_mm'] for n in values)
    first_max_local = max(n['U1_start_B_local_Y_mm'] for n in values)
    second_min_local = min(n['U2_start_B_local_Y_mm'] for n in values)
    second_max_local = max(n['U2_start_B_local_Y_mm'] for n in values)
    uhalf = float(ep4.u_integral(.5,r['Gauss_Legendre_order'])[0])
    up,down = values[0]['U1_length_mm'],values[0]['U2_length_mm']
    separation = min(n['middle_reverse_straight_mm'] for n in values)
    second_seat_min_y = 79.75+second_max_local-down*uhalf-t/2.
    slide_s_max_z = a[2]+max(n['S_rise_mm'] for n in values)+t/2.
    slide_return_min_z = 8.2+b[2]-t/2.
    witnesses = [
        {'segments':['A_straight','bridge'],'method':'disjoint Y intervals','gap_lower_mm':r['S_world_Y_interval_mm'][1]-r['S_world_Y_interval_mm'][0]},
        {'segments':['A_straight','U1'],'method':'disjoint Y intervals','gap_lower_mm':first_min_world-r['S_world_Y_interval_mm'][0]},
        {'segments':['A_straight','upper_reverse/U2/B_final'],'phase':'SLIDE','method':'Z separation','gap_lower_mm':slide_return_min_z-(a[2]+t/2.)},
        {'segments':['A_straight','upper_reverse/U2/B_final'],'phase':'SEAT','method':'Y separation','gap_lower_mm':second_seat_min_y-r['S_world_Y_interval_mm'][0]},
        {'segments':['S','U1'],'method':'disjoint Y intervals','gap_lower_mm':first_min_world-r['S_world_Y_interval_mm'][1]},
        {'segments':['S','upper_reverse/U2/B_final'],'phase':'SLIDE','method':'Z separation','gap_lower_mm':slide_return_min_z-slide_s_max_z},
        {'segments':['S','upper_reverse/U2/B_final'],'phase':'SEAT','method':'Y separation','gap_lower_mm':second_seat_min_y-r['S_world_Y_interval_mm'][1]},
        {'segments':['bridge','upper_reverse'],'method':'Z separation','gap_lower_mm':r['B_high_lane_z_mm']-r['B_low_lane_z_mm']-t},
        {'segments':['bridge','U2/B_final'],'method':'Z separation','gap_lower_mm':b[2]-r['B_low_lane_z_mm']-t},
        {'segments':['U1','U2'],'method':'oppositely directed U turns have finite Y at or outside their starts','gap_lower_mm':separation},
        {'segments':['U1','B_final'],'method':'Y separation in B frame','gap_lower_mm':first_min_local-b[1]},
        {'segments':['upper_reverse','B_final'],'method':'Z separation','gap_lower_mm':r['B_high_lane_z_mm']-b[2]-t}]
    if min(row['gap_lower_mm'] for row in witnesses) <= 0:
        raise ValueError('a continuous nonadjacent path separation witness failed')
    # All downstream pieces after S lie inside B. Bound the U heads using
    # both maximum centerline excursions and the complete thickness offset.
    b_y_min = min(86.-79.75,second_min_local-down*uhalf-t/2.)
    b_y_max = max(b[1],first_max_local+up*uhalf+t/2.)
    b_z = [min(r['B_low_lane_z_mm'],b[2])-t/2.,r['B_high_lane_z_mm']+t/2.]
    # Any S point with Y below the furthest possible B front (79.75) has
    # center u <= (79.75+t/2-76)/10. It therefore lies well below A Z=8.
    early_u = (79.75+t/2.-r['S_world_Y_interval_mm'][0])/10.
    early_z_upper = a[2]+max(n['S_rise_mm'] for n in values)*float(ep4.quintic(early_u))+t/2.
    max_b_front_bottom = 8.2-1.15
    domain = {'A_S_Y_mm':[r['S_world_Y_interval_mm'][0]-t/2.,r['S_world_Y_interval_mm'][1]+t/2.],
        'S_all_motion_Z_lower_mm':min(a[2],r['B_low_lane_z_mm'])-t/2.,
        'S_before_possible_B_front_Z_upper_mm':early_z_upper,
        'S_below_B_bottom_is_also_below_A_top':max_b_front_bottom < 8.,
        'S_above_A_top_is_within_B_Y_and_Z':early_z_upper < 8.,
        'post_S_B_local_Y_enclosure_mm':[b_y_min,b_y_max],
        'post_S_B_local_Z_enclosure_mm':b_z,
        'two_separate_outer_prism_containment_established_for_ideal_route':
            0 <= b_y_min < b_y_max <= 94.25 and -1.15 <= b_z[0] < b_z[1] <= 8 and early_z_upper < 8.,
        'an_outer_prism_is_not_an_empty_internal_cavity':True}
    return {'schema':'razr-ep5-continuous-ideal-route-v1',
        'parameter_domain':{'SLIDE':{'slide_mm':[0,79.75],'descent_mm':0},
                            'SEAT':{'slide_mm':79.75,'descent_mm':[0,8.2]}},
        'reverse_path_uses_identical_geometric_parameter_set':True,
        'nonadjacent_segment_separation_witnesses':witnesses,
        'minimum_positive_nonadjacent_separation_lower_mm':min(row['gap_lower_mm'] for row in witnesses),
        'adjacent_join_argument':'All adjacent pairs share exactly the G2 end cross-section. The S has T_y>0; each U has monotone turning angle, and each eta offset keeps 1-eta*kappa>0, so the finite edges remain on the correct side of the shared Y plane.',
        'minimum_finite_thickness_Jacobian_lower':ar['continuous_necessary_bounds']['minimum_Jacobian_lower_bound'],
        'geometric_self_nonintersection_established_for_ideal_planar_family':True,
        'outer_domain':domain,'formal_directed_rounding_certificate':False,
        'full_external_obstacle_field_or_friction_or_material_qualification_proved':False,
        'real_cable_length_and_width_qualified':False,**{k:False for k in GO_KEYS}}


def endpoint_parts(end, c=None):
    """Reuse all 20 EP4 parts and integrate only the recorded A head relief."""
    c = c or load_config()
    import cadquery as cq
    import product_assembly as p
    parts = ep4.ep4_local_parts(end)
    record = {'end':end,'parts':list(ep4.PART_NAMES),'modified_parts':[]}
    if end == 'A' and c['relief']['A_head_web']:
        name = 'inner_carrier_jaw'; old = parts[name]
        tool = cq.Solid.makeCylinder(1.95,.8,cq.Vector(0.,-15.,.85))
        after = p.single(old.cut(tool).clean())
        removed = p.volume(old.cut(after)); added = p.volume(after.cut(old))
        if removed <= TOL or added > TOL:
            raise ValueError('A local head relief did not remove the declared finite material')
        parts[name] = after
        record['modified_parts'].append({'name':name,'removed_mm3':removed,'added_mm3':added,
            'before_volume_mm3':p.volume(old),'after_volume_mm3':p.volume(after),
            'one_valid_positive_solid':True,'local_strength_or_process_qualified':False})
    if tuple(sorted(parts)) != ep4.PART_NAMES:
        raise ValueError('endpoint inventory changed')
    return parts,record


def finite_material_solid(sections, c=None):
    """Native mid-width extrusion plus explicit planar endpoint taper wings.

    Tapers are confined to the analytically straight first/last four mm.
    The native body is compared with an independent polygon-area volume.
    No smooth loft is substituted for a listed finite station polygon.
    """
    c = c or load_config(); r = c['route']
    import cadquery as cq
    import product_assembly as p
    import product_fpc as f
    core = sections['corners'].copy()
    core[:,:,0] = np.array([-1,1,1,-1])[None,:]*r['middle_width_mm']/2.
    body,base = f.finite_material_solid(core)
    extra_volume = 0.; taper_records = []
    for end in ('A','B'):
        s = sections['s']; length = r['free_length_mm']; taper = r['taper_length_each_end_mm']
        mask = s <= taper+1e-12 if end == 'A' else s >= length-taper-1e-12
        q = sections['center'][mask]; widths = sections['material_width_mm'][mask]
        normals = sections['normal'][mask]; tangents = sections['tangent'][mask]
        if not (np.allclose(normals,[0,0,1],atol=1e-12,rtol=0)
                and np.allclose(tangents,[0,1,0],atol=1e-12,rtol=0)
                and np.ptp(q[:,2]) <= 1e-12):
            raise ValueError('a taper crossed out of its straight material region')
        z0 = float(q[0,2]-r['thickness_assumption_mm']/2.)
        points = [cq.Vector(float(-w/2.),float(v[1]),z0) for v,w in zip(q,widths)]
        points += [cq.Vector(float(w/2.),float(v[1]),z0) for v,w in zip(q[::-1],widths[::-1])]
        wire = cq.Wire.makePolygon(points,close=True)
        patch = cq.Solid.extrudeLinear(wire,[],cq.Vector(0,0,r['thickness_assumption_mm']))
        body = p.single(body.fuse(patch).clean())
        area_extra = float(np.sum(np.diff(q[:,1])*(widths[:-1]+widths[1:]-2.*r['middle_width_mm'])/2.))
        extra_volume += area_extra*r['thickness_assumption_mm']
        taper_records.append({'end':end,'stations':len(q),'extra_plan_area_mm2':area_extra})
    polygon = np.concatenate([core[:,0],core[::-1,3]])[:,1:]
    area = abs(float(np.sum(polygon[:,0]*np.roll(polygon[:,1],-1)-polygon[:,1]*np.roll(polygon[:,0],-1))))/2.
    expected = r['middle_width_mm']*area+extra_volume
    actual = p.volume(body)
    if abs(actual-expected) > 1e-6:
        raise ValueError('finite native ribbon volume differs from its independent polygon construction')
    return body,{'model':'fixed-width finite YZ extrusion plus explicit straight finite taper polygons',
        'native_volume_mm3':actual,'independent_polygon_volume_mm3':expected,
        'absolute_volume_error_mm3':abs(actual-expected),
        'continuous_analytic_material_volume_mm3':r['thickness_assumption_mm']*(r['middle_width_mm']*r['free_length_mm']+(r['endpoint_width_mm']-r['middle_width_mm'])*r['taper_length_each_end_mm']),
        'finite_polygon_discretization_is_not_exact_smooth_material':True,'positive_valid_solids':len(p.whole_material(body)[0]),
        'tapers':taper_records,'constant_middle_width_mm':r['middle_width_mm'],
        'smooth_material_fatigue_or_supplier_stack_qualified':False}


def _prism_xy(points, z0, z1):
    import cadquery as cq
    import product_assembly as p
    wire = cq.Wire.makePolygon([cq.Vector(float(x),float(y),float(z0)) for x,y in points],close=True)
    return p.single(cq.Solid.extrudeLinear(wire,[],cq.Vector(0.,0.,float(z1-z0))))



@lru_cache(maxsize=1)
def cam_v5_source_templates():
    """Read the exact 19 original cam-v5 STEP inputs with the original metric reader."""
    import tarfile
    import tempfile
    import verify_cam_coupling as reader
    folder = ep4.ROOT/'engineering/cam-coupling-20261015'
    gm = folder/'geometry-v5-manifest.json'; manifest = folder/'V5_NATIVE_MANIFEST.json'
    identities = {
        gm:'be2624f8b5a4cf51aa69761bb0834756fd6a2c77eb1fa2d619bbb2087d36ba0b',
        manifest:'26fa650061c10960a862f6bad10ef22fd15c130f127447ac9523c43b7ff4bb3a'}
    if any(sha(path)!=digest for path,digest in identities.items()):
        raise ValueError('original cam-v5 manifest bytes changed')
    entries = json.loads(gm.read_text()); archive = folder/entries['archive']
    if sha(archive)!='249f50dae36b591df189e17ed8f46b1d1e793d481b1d0fb57f0ff1a553dfbd07':
        raise ValueError('original cam-v5 archive bytes changed')
    with tempfile.TemporaryDirectory(prefix='ep5-cam-v5-') as td, tarfile.open(archive,'r:gz') as stream:
        expected = {row['path']:row for row in entries['files']}
        members = stream.getmembers()
        if len(members)!=19 or len(expected)!=19 or {m.name for m in members}!=set(expected):
            raise ValueError('complete cam-v5 archive member inventory differs')
        directory = Path(td)
        for member in members:
            if not member.isfile() or Path(member.name).name!=member.name:
                raise ValueError('unsafe cam-v5 member')
            raw = stream.extractfile(member).read(); record = expected[member.name]
            if len(raw)!=record['bytes'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:
                raise ValueError('original cam-v5 STEP identity differs')
            (directory/member.name).write_bytes(raw)
        (directory/'manifest.json').write_bytes(manifest.read_bytes())
        meta,parts,_ = reader.load(directory/'manifest.json')
    if meta['source_sha256']!=sha(ep4.ROOT/'integration/cam_coupling.py'):
        raise ValueError('cam-v5 geometry source changed')
    return parts,{'archive':str(archive),'archive_sha256':sha(archive),
        'geometry_manifest_sha256':sha(gm),'native_manifest_sha256':sha(manifest),
        'all_original_19_members_and_metrics_verified':True,
        'historical_mounted_tar_container_used':False,
        'full_mounted_mechanical_scene_substituted':False}


def key_geometry_parameters():
    """EP5's explicit two-disc tangent construction; no historical test result reused."""
    c,d = np.array([7.15,77.60]),np.array([20.,64.75])
    tangent = (d-c)/np.linalg.norm(d-c); normal = np.array([-tangent[1],tangent[0]])
    e = c+tangent; alpha = 1.1-.95
    ns = [-alpha*tangent+sign*math.sqrt(1-alpha*alpha)*normal for sign in (1,-1)]
    first = [c+.95*n for n in ns]; second = [e+1.1*n for n in ns]
    return {'C':c.tolist(),'D':d.tolist(),'E':e.tolist(),
            'tangent_quadrilateral':[first[0].tolist(),first[1].tolist(),second[1].tolist(),second[0].tolist()]}


@lru_cache(maxsize=1)
def closed_key_templates():
    """Reconstruct both complete original KEYs before installing the EP4 study.

    The historical local study is reused geometrically, including its closed
    endcaps and original mother/arm. The current phone PAWL is never replaced
    by the old mounted PAWL used in that historical local study.
    """
    import cam_coupling as cam
    import product_assembly as p
    source = ep4.ROOT/'engineering/product-integration-20261018/phase4-20261020/local-studies/key-source/key_endcap_local_study.py'
    # The historical study pinned entire source files now changed only to add
    # explicit verified-member input. Its qualification/result is not reused.
    # EP5 rederives the fixed construction and tests complete original STEP material.
    g = key_geometry_parameters()
    transition = cam.one(cam.cylinder(.95,1.2,1.6,*g['C'])
        .fuse(_prism_xy(g['tangent_quadrilateral'],1.2,1.6))
        .fuse(cam.cylinder(1.1,1.2,1.6,*g['E'])).clean())
    outer = cam.one(transition.fuse(cam.capsule(g['E'],g['D'],1.1,1.2,1.6)).clean())
    new_slot = cam.one(outer.cut(cam.capsule(g['C'],g['D'],.425,1.1,1.7)).clean())
    old_slot = cam.one(cam.capsule((6.5,78.25),g['D'],1.1,1.2,1.6)
        .cut(cam.capsule((6.5,78.25),g['D'],.425,1.1,1.7)).clean())
    arm_specs = [((10.8,39.,1.2),(11.4,72.6,1.6)),
        ((13.2,39.,1.2),(13.45,39.6,4.35)),
        ((13.2,15.8,4.05),(13.45,39.6,4.35)),
        ((10.8,39.,1.2),(13.45,39.6,1.6))]
    arm = p.fuse([cam.box(lo,hi) for lo,hi in arm_specs])
    old = {}; new = {}; records = []
    factory,source_inputs = cam_v5_source_templates()
    for side in 'LR':
        mother = factory[side+'_ORIGINAL_KEY']
        old[side] = factory[side+'_KEY_YOKE']
        rebuilt = p.single(mother.fuse(cam.handed(old_slot,side)).fuse(cam.handed(arm,side)).clean())
        differences = [p.volume(old[side].cut(rebuilt)),p.volume(rebuilt.cut(old[side]))]
        if max(differences) > TOL:
            raise ValueError('actual old KEY cannot be reconstructed from pinned parts')
        new[side] = p.single(mother.fuse(cam.handed(new_slot,side)).fuse(cam.handed(arm,side)).clean())
        retained = [p.volume(mother.cut(new[side])),p.volume(cam.handed(arm,side).cut(new[side]))]
        if max(retained) > TOL:
            raise ValueError('closed KEY candidate lost original mother or arm')
        removed,added = p.volume(old[side].cut(new[side])),p.volume(new[side].cut(old[side]))
        b = p.bounds(new[side]); inner = b[0] if side == 'R' else -b[1]
        if inner < 6.2-TOL: raise ValueError('complete KEY does not preserve central corridor')
        records.append({'part':side+'_KEY','old_source_STEP_reconstruction_differences_mm3':differences,
            'mother_and_arm_lost_mm3':retained,'removed_mm3':removed,'added_mm3':added,
            'before_volume_mm3':p.volume(old[side]),'after_volume_mm3':p.volume(new[side]),
            'one_valid_positive_solid':True,'signed_inner_X_mm':inner,
            'current_PAWL_replaced':False,'material_process_or_strength_qualified':False})
    return old,new,{'reference_geometry_source':str(source.relative_to(ep4.ROOT)),'reference_source_sha256':sha(source),
        'historical_study_native_results_reused':False,'new_construction_rederived_in_EP5':True,
        'original_complete_KEY_source':source_inputs,'parts':records}


def apply_scene_relief(scene, slide, descent, c=None):
    """Finite, auditable material changes; no collision participant is dropped."""
    c = c or load_config()
    import product_assembly as p
    changed = dict(scene); records = []
    original_names = set(scene)
    shift = p.b_transform(slide,descent)
    for name,tools in (
        ('A_FRAME',[p.box(*c['relief']['A_center_channel_lo_hi_mm'])]),
        ('B_SHELL',[p.box(*c['relief']['B_floor_channel_lo_hi_mm']).translate(shift),
                    p.box(*c['relief']['B_front_lap_channel_lo_hi_mm']).translate(shift)])):
        before = scene[name]; after = before
        for tool in tools: after = p.single(after.cut(tool).clean())
        removed,added = p.volume(before.cut(after)),p.volume(after.cut(before))
        balance = p.volume(before)-removed+added-p.volume(after)
        if added > TOL or abs(balance) > 1e-6:
            raise ValueError('shell relief material accounting failed: '+name)
        if not np.allclose(p.bounds(before),p.bounds(after),atol=TOL,rtol=0):
            raise ValueError('shell relief changed a finished outer bound: '+name)
        changed[name] = after
        records.append({'part':name,'removed_mm3':removed,'added_mm3':added,
            'before_volume_mm3':p.volume(before),'after_volume_mm3':p.volume(after),
            'signed_material_balance_error_mm3':balance,'one_valid_positive_solid':True,
            'finished_bounds_unchanged':True,'local_minimum_wall_or_strength_qualified':False})
    if c['relief']['closed_KEY_endcaps']:
        old,new,key_meta = closed_key_templates()
        for side in 'LR':
            name = side+'_KEY'; before = scene[name]
            delta = p.bounds(before)[2]-p.bounds(old[side])[2]
            reference = old[side].translate((0.,delta,0.))
            differences = [p.volume(before.cut(reference)),p.volume(reference.cut(before))]
            if max(differences) > TOL:
                raise ValueError('current complete KEY is not the pinned rigid template')
            changed[name] = new[side].translate((0.,delta,0.))
            records.append({'part':name,'Y_translation_mm':delta,
                'current_scene_to_pinned_template_difference_mm3':differences,
                'local_change':next(row for row in key_meta['parts'] if row['part']==name)})
    else: key_meta = None
    if set(changed) != original_names:
        raise ValueError('a mechanical participant was removed by relief')
    return changed,{'changes':records,'KEY_source':key_meta,
        'all_mechanical_participants_retained':True,'actual_internal_channel_defined_as_finite_research_cuts':True,
        'qualified_empty_cavity_proved':False,'material_or_manufacturing_qualified':False}


def is_project_source_path(path):
    """Project source areas only; an in-repository .venv is a runtime dependency."""
    path = Path(path).resolve()
    return any(path.is_relative_to(root/directory) for root in (ROOT,ep4.ROOT)
               for directory in ('integration','design','engineering'))


def _snapshot_sources(mode='local', verified_mounted_members=False):
    """Snapshot project source/config bytes and every declared payload role."""
    names = {}
    for root in (ROOT,ep4.ROOT):
        for directory in ('integration','design'):
            for path in sorted((root/directory).rglob('*')):
                if path.is_file() and path.suffix in ('.py','.json'):
                    names[str(path.resolve())] = sha(path)
        for path in sorted((root/'engineering').rglob('*.py')):
            if path.is_file():
                names[str(path.resolve())] = sha(path)
    # The closed list is selected by the execution mode, never by which
    # historical files happen to exist. This includes the consumed .json.gz.
    for relative, role in input_closure.native_input_roles(mode,verified_mounted_members).items():
        path = ep4.ROOT/relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ep4.ROOT.resolve()):
            raise ValueError('missing or unsafe declared EP5 input '+relative+' ('+role+')')
        names[str(path.resolve())] = sha(path)
    return names


def validate_factory_input_coverage(scene_meta,before):
    """Every original payload actually declared by the scene factory was pinned first."""
    declared = dict(scene_meta['source_inputs'])
    declared[scene_meta['archive']] = scene_meta['archive_sha256']
    for relative, digest in declared.items():
        path = (ep4.ROOT/relative).resolve()
        if not path.is_relative_to(ep4.ROOT.resolve()) or before.get(str(path)) != digest:
            raise ValueError('native factory input absent from declared pre-execution identity: '+relative)
    for name, digest in scene_meta.get('external_verified_source_inputs',{}).items():
        if before.get(str(Path(name).resolve())) != digest:
            raise ValueError('external native factory input was not pinned before execution: '+name)


def source_completion_check(before):
    """Report source failures explicitly, including missing or late project inputs."""
    late = []
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path:
            path = Path(path).resolve()
            if path.is_file() and is_project_source_path(path) and str(path) not in before:
                late.append(str(path))
    changed = []
    for name, expected in before.items():
        path = Path(name)
        actual = sha(path) if path.is_file() else None
        if actual != expected:
            changed.append({'path':name,'expected_sha256':expected,'observed_sha256':actual})
    return {'checked_source_count':len(before),'late_project_sources':sorted(set(late)),
            'changed_or_missing_sources':changed,'source_bytes_unchanged':not late and not changed}


def native_report(output, labels=('STOW','PREDOCK','OPEN'), c=None, *, verified_mounted_members=None):
    """Run one complete pair matrix, including external/external, at each pose."""
    started = time.perf_counter()
    c = c or load_config(); output = Path(output).resolve()
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError('new native output outside the stage source required')
    if not labels or len(set(labels)) != len(labels) or any(label not in POSES for label in labels):
        raise ValueError('unique named EP5 poses required')
    output.mkdir(parents=True)
    before = _snapshot_sources('full',verified_mounted_members is not None); runtime = ep4.runtime_identity()
    verified_input = None
    if verified_mounted_members is not None:
        from verified_native_members import verify_mounted_members
        verified_input = verify_mounted_members(verified_mounted_members,ep4.ROOT)
        before.update(verified_input['source_sha256'])
    import cadquery as cq
    import product_assembly as p
    import product_fpc as f
    import product_split_assembly as split
    import oled_storage
    local = {}; endpoint_changes = {}
    for end in ('A','B'):
        local[end],endpoint_changes[end] = endpoint_parts(end,c)
    completed = []
    for label in labels:
        folder = output/label; folder.mkdir()
        s,d = POSES[label]; accessories = label == 'OPEN'; tab = 0. if label == 'STOW' else 3.
        baseline,scene_meta = split.split_scene(s,d,tab,tab,open_hold=accessories,open_support=accessories,verified_mounted_members=verified_mounted_members)
        validate_factory_input_coverage(scene_meta,before)
        expected = 115 if accessories else 108
        if len(baseline) != expected: raise ValueError('complete mechanical inventory changed')
        scene,relief = apply_scene_relief(baseline,s,d,c)
        scene.update(p.registered_components(p.load_config(),s,d))
        scene['OLED_GEOMETRIC_TRIAL'],oled_meta = oled_storage.geometry(s,d)
        sections,route = route_sections(s,d,c)
        material,finite = finite_material_solid(sections,c)
        placed = {end:f.place_endpoint(local[end],sections,end) for end in ('A','B')}
        candidate = {'EP5_finite_material':material,**placed['A'],**placed['B']}
        all_parts = {**scene,**candidate}
        if len(candidate) != 41 or len(all_parts) != expected+46:
            raise ValueError('complete native participant inventory changed')
        metrics = {name:ep4.native_metrics(body) for name,body in sorted(all_parts.items())}
        assembly = cq.Assembly(name='EP5_COMPLETE_'+label)
        for name,body in sorted(all_parts.items()): assembly.add(body,name=name)
        step = folder/(label+'-complete-EP5.step'); assembly.export(str(step))
        npz = folder/'material-sections.npz'; np.savez_compressed(npz,**sections)
        matrix = ep4.native_pairs(all_parts,folder/'all-pairs',c,metrics_a=metrics,context_metrics=metrics)
        domains,domain_meta = ep4.outer_domains(scene,c)
        contained = ep4.containment(candidate,domains,folder/'outside-domain')
        n = len(all_parts)
        if matrix['pair_count'] != n*(n-1)//2:
            raise ValueError('full n-choose-2 pair inventory incomplete')
        failures = matrix['failures']
        categories = {
            'candidate_external':sum((row['a'] in candidate) != (row['b'] in candidate) for row in failures),
            'candidate_candidate':sum(row['a'] in candidate and row['b'] in candidate for row in failures),
            'external_external':sum(row['a'] in scene and row['b'] in scene for row in failures)}
        rejected = bool(failures or contained['failures'])
        row = {'pose':label,'mechanical_participants':expected,'external_participants':len(scene),
            'candidate_participants':len(candidate),'combined_participants':n,
            'scene':scene_meta,'research_relief':relief,'OLED':oled_meta,'route':route,'finite_material':finite,
            'parts':metrics,'complete_assembly_STEP':{'file':str(step.relative_to(output)),
                'sha256':sha(step),'expected_solids':n,'independent_process_readback_executed':False},
            'material_sections':{'file':str(npz.relative_to(output)),'sha256':sha(npz)},
            'complete_pair_matrix':matrix,'failure_categories':categories,
            'outer_domain':domain_meta,'containment':contained,
            'decisive_geometric_rejection_or_evaluation_failure':rejected,
            'all_declared_finite_pose_checks_clear':not rejected,
            'continuous_motion_or_physical_qualification_proved':False}
        completed.append(row)
        write_json(output/'progress.json',{'source_sha256':before,'runtime':runtime,
            'endpoint_changes':endpoint_changes,'poses':completed,'complete':False,**{k:False for k in GO_KEYS}})
        print(json.dumps({'pose':label,'parts':n,'pairs':matrix['pair_count'],
            'native_Common_calls':matrix['native_Common_calls'],'failures':categories,
            'outside_parts':len(contained['failures'])}),flush=True)
    source_check = source_completion_check(before)
    unchanged = source_check['source_bytes_unchanged']
    write_json(output/'source-check.json',source_check)
    try:
        verified_after = verify_mounted_members(verified_mounted_members,ep4.ROOT) if verified_input else None
        if verified_input != verified_after:
            raise ValueError('verified original member input changed during native execution')
    except Exception as exc:
        source_check['verified_member_revalidation_error'] = str(exc)
        source_check['source_bytes_unchanged'] = False
        write_json(output/'source-check.json',source_check)
        raise
    if not unchanged: raise ValueError('native source identity failed; see source-check.json')
    result = {'schema':'razr-ep5-full-pair-native-v1','candidate_id':c['candidate_id'],'native_checks_executed':True,
        'baseline_claimed_commit':c['basis_commit'],'baseline_git_commit_verified_by_this_runner':False,
        'input_closure_schema':input_closure.SCHEMA,
        'input_closure_helper_sha256':sha(input_closure.__file__),
        'declared_input_roles':input_closure.native_input_roles('full',verified_mounted_members is not None),
        'source_sha256':before,'source_bytes_unchanged':unchanged,'source_check':source_check,
        'runtime':runtime,'elapsed_seconds':time.perf_counter()-started,
        'verified_mounted_members_before':verified_input,'verified_mounted_members_after':verified_after,
        'original_mounted_archive_container_recovered':False,
        'endpoint_changes':endpoint_changes,'selected_poses':list(labels),'poses':completed,
        'scope':'Every unordered pair of all finite candidate, mechanism, OLED and allocation bodies at each selected pose.',
        'geometric_rejection_found':any(row['decisive_geometric_rejection_or_evaluation_failure'] for row in completed),
        'actual_hardware_or_supplier_material_included':False,'continuous_motion_proved':False,
        'research_changes':c['research_changes'],**{k:False for k in GO_KEYS}}
    write_json(output/'native-report.json',result)
    return result


def continuous_OLED_enclosure(c=None, intervals=512):
    """Conservative all-u boxes, not samples, bound the first U radial extent.

    U Y is monotone on each half and Z is monotone on the full curve. Every
    cell therefore lies inside its endpoint coordinate box. The box is
    expanded by the full thickness radius and a numerical guard. During
    slide U1 moves inward relative to B; during seat all FPC turns are before
    the OLED half-circle Y plane. No supplier fatigue/radius claim follows.
    """
    c = c or load_config(); r = c['route']
    import product_assembly as p
    spec = p.load_config()['oled_storage_study']
    if type(intervals) is not int or intervals < 32 or intervals % 2:
        raise ValueError('even interval count >=32 required')
    n = pose_numbers(0.,0.,c); q = np.linspace(0.,1.,intervals+1)
    yz = np.asarray([ep4.u_integral(float(u),r['Gauss_Legendre_order']) for u in q])*n['U1_length_mm']
    yz += np.array([r['STOW_first_U_start_world_y_mm'],r['B_low_lane_z_mm']])
    radius = (spec['B_return_z_mm']+8.2-spec['front_z_mm'])/2.
    center = np.array([spec['B_turn_center_y_mm'],(spec['B_return_z_mm']+spec['front_z_mm']-8.2)/2.])
    inner = radius-spec['thickness_mm']/2.
    guard = 1e-7; pad = r['thickness_assumption_mm']/2.+guard
    maxima = []
    for a,b in zip(yz[:-1],yz[1:]):
        lo,hi = np.minimum(a,b)-pad,np.maximum(a,b)+pad
        maxima.append(max(float(np.linalg.norm(np.array([y,z])-center))
                          for y in (lo[0],hi[0]) for z in (lo[1],hi[1])))
    ar = arithmetic_report(c); values = [*ar['poses'].values(),ar['interior_seating_S_flat_critical_point']]
    first_max_seat = max(ar['poses'][k]['U1_start_B_local_Y_mm'] for k in ('PREDOCK','OPEN'))
    first_max_seat = max(first_max_seat,ar['interior_seating_S_flat_critical_point']['U1_start_B_local_Y_mm'])
    head = n['U1_length_mm']*float(ep4.u_integral(.5,r['Gauss_Legendre_order'])[0])+pad
    rows = {
        'SLIDE_U1_to_OLED_inner_circle_radial_gap_lower_mm':inner-max(maxima),
        'SEAT_all_turns_to_OLED_halfcircle_Y_gap_lower_mm':spec['B_turn_center_y_mm']-first_max_seat-head,
        'B_high_lane_to_OLED_planar_return_Z_gap_lower_mm':spec['B_return_z_mm']-spec['thickness_mm']/2.-r['B_high_lane_z_mm']-pad,
        'FPC_to_OLED_front_Z_gap_lower_mm':min(r['A_anchor_local_mm'][2],r['B_low_lane_z_mm'])-pad-(spec['front_z_mm']+spec['thickness_mm']/2.)}
    if min(rows.values()) <= 0:raise ValueError('continuous OLED separation bound failed')
    return {'schema':'razr-ep5-continuous-OLED-geometric-envelope-v1',
        'OLED_source_sha256':sha(ep4.ROOT/'integration/oled_storage.py'),
        'OLED_configuration_sha256':sha(ep4.ROOT/'design/product_geometry.json'),
        'OLED_is_unqualified_geometric_trial':True,'source_model':spec['topology'],
        'U_parameter_cells':intervals,'each_cell_covers_its_continuous_parameter_interval':True,
        'interval_basis':'cos(theta) changes sign only at u=.5; sin(theta)>=0. Both halves are explicitly partitioned.',
        'numerical_guard_mm':guard,'formal_directed_rounding_certificate':False,
        'maximum_U1_finite_cell_radius_upper_mm':max(maxima),'OLED_inner_radius_mm':inner,
        'continuous_separation_bounds':rows,
        'slide_monotonicity':'B-local U1 Y decreases affinely; while Y>=OLED center, moving inward reduces radial distance; below the center plane no OLED half-arc exists.',
        'other_slide_segments':'S/bridge lie below U1 start height or left of its start; upper return stays at high-lane Z and Y<=U1 start; U2 and B final lie before B Y=35.',
        'only_identified_ideal_geometric_models_covered':True,
        'actual_OLED_COF_touch_flex_stack_or_dynamic_qualification_proved':False}


def _rectangle_union_yz(rectangles, width):
    """Exact planar union of connected horizontal sections, then native extrusion."""
    import cadquery as cq
    import product_assembly as p
    levels = sorted(set(float(z) for lo,hi in rectangles for z in (lo[1],hi[1])))
    left = []; right = []
    for z0,z1 in zip(levels[:-1],levels[1:]):
        if z1-z0 <= 1e-13: continue
        mid = (z0+z1)/2.
        active = sorted((lo[0],hi[0]) for lo,hi in rectangles if lo[1] <= mid <= hi[1])
        if not active: raise ValueError('enclosure rectangle union is disconnected')
        reach = active[0][1]
        for lo,hi in active[1:]:
            if lo > reach+1e-12:raise ValueError('enclosure cross-section has an unrepresented gap')
            reach = max(reach,hi)
        low = active[0][0]; high = max(hi for lo,hi in active)
        left.extend([(low,z0),(low,z1)]); right.extend([(high,z0),(high,z1)])
    points = []
    for point in left+list(reversed(right)):
        if not points or point != points[-1]:points.append(point)
    if points[0] == points[-1]:points.pop()
    # Delete strictly collinear intermediate vertices only; no tolerance simplification.
    changed = True
    while changed and len(points)>3:
        changed = False; keep = []
        for i,b in enumerate(points):
            a,d = points[i-1],points[(i+1)%len(points)]
            if (a[0]==b[0]==d[0]) or (a[1]==b[1]==d[1]):
                changed = True
            else:keep.append(b)
        points = keep
    wire = cq.Wire.makePolygon([cq.Vector(-width/2.,float(y),float(z)) for y,z in points],close=True)
    body = p.single(cq.Solid.extrudeLinear(wire,[],cq.Vector(width,0.,0.)))
    return body,{'rectangle_cells':len(rectangles),'polygon_vertices':len(points),
        'all_horizontal_union_sections_verified_connected':True}


def continuous_endpoint_checks(output,c=None):
    """Complete B endpoint native comparison with an all-pose smooth U1 cage."""
    c = c or load_config(); r = c['route']; output = Path(output); output.mkdir(parents=True)
    import product_assembly as p
    ar = arithmetic_report(c); values = [*ar['poses'].values(),ar['interior_seating_S_flat_critical_point']]
    low = min(n['U1_start_B_local_Y_mm'] for n in values)
    high = max(n['U1_start_B_local_Y_mm'] for n in values)
    length = values[0]['U1_length_mm']; count = 64; guard = 1e-7
    yz = np.asarray([ep4.u_integral(float(u),r['Gauss_Legendre_order']) for u in np.linspace(0,1,count+1)])*length
    yz[:,1] += r['B_low_lane_z_mm']
    pad = r['thickness_assumption_mm']/2.+guard
    rectangles = [(np.array([low+min(a[0],b[0])-pad,min(a[1],b[1])-pad]),
                   np.array([high+max(a[0],b[0])+pad,max(a[1],b[1])+pad]))
                  for a,b in zip(yz[:-1],yz[1:])]
    cage,construction = _rectangle_union_yz(rectangles,r['middle_width_mm'])
    b_local,_ = endpoint_parts('B',c)
    b_parts = {'B_'+name:shape.translate(tuple(r['B_anchor_local_mm'])) for name,shape in b_local.items()}
    a_parts,_ = endpoint_parts('A',c)
    a_parts = {'A_'+name:shape.translate(tuple(r['A_anchor_local_mm'])) for name,shape in a_parts.items()}
    bm = {name:ep4.native_metrics(shape) for name,shape in b_parts.items()}
    am = {name:ep4.native_metrics(shape) for name,shape in a_parts.items()}
    b_min_y = min(v['bounds_mm'][2] for v in bm.values()); b_max_z = max(v['bounds_mm'][5] for v in bm.values())
    b_min_z = min(v['bounds_mm'][4] for v in bm.values()); a_max_y = max(v['bounds_mm'][3] for v in am.values())
    a_max_z = max(v['bounds_mm'][5] for v in am.values())
    pair = ep4.native_pairs({'U1_ALL_POSES_SMOOTH_ENCLOSURE':cage},output/'U1-to-complete-B',c,parts_b=b_parts,coordinate_frame='B local')
    artifact = ep4.export_shape(cage,output/'U1-all-pose-enclosure.step')
    pad0 = r['thickness_assumption_mm']/2.
    margins = {
        'A_endpoint_to_B_endpoint_SLIDE_Z_gap_mm':8.2+b_min_z-a_max_z,
        'A_endpoint_to_B_endpoint_SEAT_Y_gap_mm':79.75+b_min_y-a_max_y,
        'B_endpoint_to_low_bridge_Z_gap_mm':b_min_z-r['B_low_lane_z_mm']-pad0,
        'B_endpoint_to_S_SLIDE_Z_gap_mm':b_min_z-r['B_low_lane_z_mm']-pad0,
        'B_endpoint_to_S_SEAT_Y_gap_mm':b_min_y-(86.-79.75+pad0),
        'B_endpoint_to_high_return_Z_gap_mm':r['B_high_lane_z_mm']-pad0-b_max_z,
        'B_endpoint_to_U2_Y_gap_mm':b_min_y-max(n['U2_start_B_local_Y_mm'] for n in values)-pad0,
        'A_endpoint_to_S_bridge_U1_Y_gap_mm':r['S_world_Y_interval_mm'][0]-pad0-a_max_y,
        'A_endpoint_to_return_SLIDE_Z_gap_mm':8.2+r['B_anchor_local_mm'][2]-pad0-a_max_z,
        'A_endpoint_to_return_SEAT_Y_gap_mm':79.75+r['PREDOCK_second_U_start_B_local_y_mm']-values[0]['U2_length_mm']*float(ep4.u_integral(.5)[0])-pad0-a_max_y}
    if min(margins.values()) <= 0:raise ValueError('continuous endpoint separation margin failed')
    return {'schema':'razr-ep5-continuous-complete-endpoint-geometry-v1',
        'U1_cage':artifact,'U1_cage_construction':construction,'U1_B_local_translation_interval_mm':[low,high],
        'each_curve_cell_is_a_full_parameter_coordinate_enclosure':True,'coordinate_box_normal_pad_mm':pad,
        'U1_to_all_20_B_endpoint_parts':pair,'endpoint_metrics':{'A':am,'B':bm},
        'other_segment_axis_separation_margins':margins,
        'endpoint_tail_join_nonpenetration':'A free material has Y>=A join and A endpoint Y<=join; B final material has Y<=B join and B endpoint Y>=join. Shared end faces are permitted, no positive volume is waived.',
        'all_declared_continuous_endpoint_geometric_checks_clear':not pair['failures'],
        'current_PAWL_or_full_external_field_checked':False,
        'friction_strain_tolerance_and_physical_qualification_proved':False,
        **{k:False for k in GO_KEYS}}


def local_motion_report(output,c=None):
    """Regenerate the local native evidence with bound sources and a negative control."""
    started = time.perf_counter(); runtime = ep4.runtime_identity()
    c = c or load_config(); output = Path(output).resolve()
    if output.exists():raise ValueError('new local native output required')
    output.mkdir(parents=True); before = _snapshot_sources()
    import cadquery as cq
    import product_assembly as p
    import product_fpc as f
    import oled_storage
    local = {}; modifications = {}
    for end in ('A','B'):
        local[end],modifications[end] = endpoint_parts(end,c)
    rows = []
    for label,pose in POSES.items():
        folder = output/label; folder.mkdir()
        sec,route = route_sections(*pose,c); material,finite = finite_material_solid(sec,c)
        placed = {end:f.place_endpoint(local[end],sec,end) for end in ('A','B')}
        candidate = {'EP5_finite_material':material,**placed['A'],**placed['B']}
        external = {'OLED_GEOMETRIC_TRIAL':oled_storage.geometry(*pose)[0],**p.registered_components(p.load_config(),*pose)}
        all_parts = {**candidate,**external}; metrics = {name:ep4.native_metrics(shape) for name,shape in all_parts.items()}
        if len(all_parts)!=46:raise ValueError('local participant count changed')
        assembly = cq.Assembly(name='EP5_LOCAL_'+label)
        for name,shape in all_parts.items():assembly.add(shape,name=name)
        step = folder/(label+'-local-EP5.step'); assembly.export(str(step))
        pairs = ep4.native_pairs(all_parts,folder/'all-pairs',c,metrics_a=metrics,context_metrics=metrics)
        row = {'pose':label,'candidate_participants':41,'external_participants':5,'combined_participants':46,
            'route':route,'finite_material':finite,'parts':metrics,
            'complete_assembly_STEP':{'file':str(step.relative_to(output)),'sha256':sha(step),'expected_solids':46},
            'complete_pair_matrix':pairs,'containment':{'rows':[],'executed':False},
            'whole_phone_obstacle_field_tested':False}
        rows.append(row)
        print(json.dumps({'local_pose':label,'pairs':pairs['pair_count'],'failures':len(pairs['failures'])}),flush=True)
    continuous = continuous_endpoint_checks(output/'continuous-endpoints',c)
    oled = continuous_OLED_enclosure(c)
    ideal = continuous_route_certificate(c)
    source_check = source_completion_check(before)
    unchanged = source_check['source_bytes_unchanged']
    write_json(output/'source-check.json',source_check)
    if not unchanged:raise ValueError('source changed during local native execution; see source-check.json')
    result = {'schema':'razr-ep5-local-motion-native-v1','candidate_id':c['candidate_id'],
        'native_checks_executed':True,'source_sha256':before,'source_bytes_unchanged':unchanged,
        'input_closure_schema':input_closure.SCHEMA,
        'input_closure_helper_sha256':sha(input_closure.__file__),
        'declared_input_roles':input_closure.native_input_roles('local'),
        'runtime':runtime,'elapsed_seconds':time.perf_counter()-started,'source_check':source_check,
        'research_changes':c['research_changes'],
        'selected_poses':list(POSES),'poses':rows,'endpoint_modifications':modifications,
        'continuous_complete_endpoints':continuous,'continuous_trial_OLED':oled,'continuous_ideal_route':ideal,
        'all_declared_local_geometry_checks_clear':not any(row['complete_pair_matrix']['failures'] for row in rows)
            and continuous['all_declared_continuous_endpoint_geometric_checks_clear'],
        'whole_phone_obstacle_field_tested':False,'shell_channels_generated_or_validated_by_this_mode':False,
        **{k:False for k in GO_KEYS}}
    write_json(output/'native-report.json',result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--verified-mounted-members',type=Path,
        help='explicit directory of all 64 byte-identical original mounted STEP members with sibling recovery receipt')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--native',action='store_true')
    modes.add_argument('--native-local-motion',action='store_true')
    parser.add_argument('--poses',nargs='+',choices=list(POSES),default=list(POSES))
    args = parser.parse_args()
    if args.verified_mounted_members is not None and not args.native:
        raise ValueError('verified-mounted-members only applies to explicit complete-phone native mode')
    if args.native_local_motion:
        report = local_motion_report(args.output)
        print(json.dumps({'local_native_completed':True,'all_declared_local_geometry_checks_clear':report['all_declared_local_geometry_checks_clear'],**{k:False for k in GO_KEYS}}))
        return 0
    if args.native:
        result = native_report(args.output,args.poses,verified_mounted_members=args.verified_mounted_members)
        print(json.dumps({'native_completed':True,'geometric_rejection_found':result['geometric_rejection_found'],**{k:False for k in GO_KEYS}}))
        return 0
    if args.output.exists(): raise ValueError('new output directory required')
    args.output.mkdir(parents=True)
    write_json(args.output/'arithmetic.json',arithmetic_report())
    write_json(args.output/'continuous-ideal-route.json',continuous_route_certificate())
    print(json.dumps({'arithmetic_completed':True,'native_executed':False,**{k:False for k in GO_KEYS}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
