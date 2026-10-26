"""EP4: one bounded, complete-endpoint S+U geometric research candidate.

Default mode is arithmetic only. --native defaults to PREDOCK alone; each
selected pose retains the complete scene and tests every candidate/external
pair. Every positive native Common is exported, including its separate solid
bounds and a local material context. Completing these checks cannot authorize
physical parts, manufacture, material fatigue, or continuous motion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
from importlib import metadata
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np
from numpy.polynomial.legendre import leggauss

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'design/product_routing_ep4.json'
TOL = 1e-7
POSES = {'PREDOCK': (79.75, 0.), 'OPEN': (79.75, 8.2), 'STOW': (0., 0.)}
GO_KEYS = ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go',
           'supplier_dynamic_qualified', 'physical_hardware_test_executed',
           'full_cycle_internal_route_accepted')
BASELINE_EP3_SHA = 'dfee909ffe781036fb7cec84a2acabe4aada23409bb3ea721f402831462e90d2'
PART_NAMES = tuple(sorted(['tail', 'stiffener', 'outer_stiffener_jaw', 'inner_carrier_jaw',
    'mini_DP_PCB', 'mini_DS_PCB', 'mated_BM28_reservation', 'static_26wire_transfer_reservation'] +
    [f'M2_clamp_{role}_{i}' for role in ('screw', 'head') for i in (1, 2)] +
    [f'M1_board_{role}_{i}' for role in ('shaft', 'head') for i in (1, 2, 3, 4)]))
FIXED_ROUTE = {
    'A_anchor_local_mm': [0., 51., 1.45], 'B_anchor_local_mm': [0., 40., 4.85],
    'S_world_Y_interval_mm': [80., 90.],
    'S_height_formula': '1.45+(8.2-descent)*(10*u^3-15*u^4+6*u^5)',
    'U_angle_formula': 'pi*(3*u^2-2*u^3)', 'U_B_local_Z_interval_mm': [1.45, 4.85],
    'free_length_mm': 100., 'total_material_length_mm': 124.,
    'stiffened_length_each_end_mm': 12., 'width_mm': 12., 'thickness_assumption_mm': .1,
    'base_stations': 65, 'curve_parameter_stations_each': 33, 'Gauss_Legendre_order': 96,
    'minimum_B_straight_request_mm': 3., 'STOW_material_head_limit_mm': 94.}
FIXED_END = {
    'parts_per_end': 20, 'boards_per_end': 2, 'PCB_dimensions_mm': [12., 12., .8],
    'PCB_A_tail_coordinate_Y_mm': [24., 36.], 'PCB_B_tail_coordinate_Y_mm': [24., 36.],
    'A_carrier_plate_tail_Y_mm': [13.2, 36.], 'A_carrier_web_tail_Y_mm': [13.25, 13.7],
    'B_carrier_plate_tail_Y_mm': [7., 36.], 'B_carrier_web_tail_Y_mm': [12.05, 12.5],
    'DP_material_Z_mm': [.3, 1.1], 'DS_material_Z_mm': [1.7, 2.5],
    'BM28_mated_gap_mm': .6, 'stiffener_thickness_mm': .2,
    'outer_stiffener_jaw_thickness_mm': .35, 'inner_carrier_jaw_thickness_mm': .8,
    'carrier_width_mm': 12., 'carrier_plate_material_Z_mm': [2.9, 3.3],
    'board_support_ledge_thickness_mm': .2, 'static_transfer_gap_thickness_mm': .55,
    'M1_shaft_length_mm': 2.4, 'M1_head_height_mm': .4,
    'M2_shaft_length_mm': 1.4, 'M2_head_height_mm': .6}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def load_config(path=CONFIG):
    c = json.loads(Path(path).read_text())
    if c.get('schema') != 'razr-product-routing-ep4-v1':
        raise ValueError('unrecognized EP4 study')
    if any(c.get(k) is not False for k in GO_KEYS):
        raise ValueError('EP4 cannot grant a physical or continuous-motion release')
    expected = {'equal_finished_cabins': True, 'single_flexible_display': True,
        'independent_rear_display': False, 'OLED_storage_is_planar_in_B': True,
        'slide_mm': 79.75, 'normal_seating_mm': 8.2}
    if c.get('constraints') != expected or c.get('basis_EP3_module_sha256') != BASELINE_EP3_SHA:
        raise ValueError('identified product constraints or EP3 reference changed')
    for group, fixed in (('route', FIXED_ROUTE), ('endpoint', FIXED_END)):
        for key, value in fixed.items():
            if c[group].get(key) != value:
                raise ValueError('fixed EP4 geometry declaration changed: ' + group + '.' + key)
    for key in ('joint_material_process_and_nominal_short_M2_selected', 'individual_static_conductors_routed'):
        if c['endpoint'].get(key) is not False:
            raise ValueError('nominal reservation cannot become a qualified component')
    if c['domain']['finished_cabin_outer_bounds_local_mm'] != [-36.995, 36.995, 0., 94.25, -1.15, 8.]:
        raise ValueError('identified native cabin envelope changed')
    if c['domain']['actual_internal_cross_cabin_opening_defined'] is not False:
        raise ValueError('no physical internal crossing opening has been supplied')
    ns = c['native_scope']
    if (ns['default_poses'] != ['PREDOCK'] or ns['pose_order'] != list(POSES) or
            ns['candidate_parts'] != 41 or ns['common_context_margin_mm'] != 2. or
            ns['all_candidate_to_external_pairs_at_each_selected_pose'] is not True or
            ns['external_to_external_matrix_recomputed'] is not False):
        raise ValueError('native check scope changed without code change')
    return c


@lru_cache(maxsize=8)
def quadrature(order=96):
    if type(order) is not int or order < 16:
        raise ValueError('integer Gauss order >=16 required')
    return leggauss(order)


def quintic(u):
    return 10*u**3 - 15*u**4 + 6*u**5


def quintic_d1(u):
    return 30*u*u*(1-u)*(1-u)


def quintic_d2(u):
    return 60*u*(1-u)*(1-2*u)


def s_arc_length(rise, end_u=1., order=96):
    """Arc length, not the S polynomial parameter; returned as a Python float."""
    if not (0. <= end_u <= 1.) or not math.isfinite(float(rise)):
        raise ValueError('invalid S integration domain')
    x, w = quadrature(order)
    q = (x+1.)*end_u/2.
    return float(np.dot(w, np.sqrt(100. + (rise*quintic_d1(q))**2))*end_u/2.)


def u_integral(end_u=1., order=96):
    x, w = quadrature(order)
    q = (x+1.)*end_u/2.
    angle = np.pi*(3*q*q - 2*q*q*q)
    return np.array([np.dot(w, np.cos(angle)), np.dot(w, np.sin(angle))])*end_u/2.


def s_parameter_at_arc(distance, rise, order=96):
    total = s_arc_length(rise, order=order)
    if not (0. <= distance <= total):
        raise ValueError('S material station outside its arc length')
    if distance == 0.: return 0.
    if distance == total: return 1.
    lo, hi = 0., 1.
    u = distance/total
    for _ in range(48):
        residual = s_arc_length(rise, u, order) - distance
        if abs(residual) <= 2e-13: return float(u)
        if residual < 0.: lo = u
        else: hi = u
        candidate = u - residual/math.sqrt(100. + (rise*quintic_d1(u))**2)
        u = candidate if lo < candidate < hi else (lo+hi)/2.
    if abs(s_arc_length(rise, u, order)-distance) > 1e-11:
        raise ValueError('S inverse arc-length did not converge')
    return float(u)


def pose_numbers(slide, descent, c=None, *, order=None):
    c = c or load_config()
    if isinstance(slide, bool) or isinstance(descent, bool):
        raise ValueError('boolean pose is not a physical distance')
    slide, descent = float(slide), float(descent)
    if not (0. <= slide <= 79.75 and 0. <= descent <= 8.2) or (descent > 0. and slide != 79.75):
        raise ValueError('outside ordered slide and seating program')
    r = c['route']; order = order or r['Gauss_Legendre_order']
    a = r['A_anchor_local_mm']; b = r['B_anchor_local_mm']
    rise = 8.2-descent; by = b[1]+slide
    length_s = s_arc_length(rise, order=order)
    integrals = u_integral(order=order)
    dz = b[2]-a[2]; length_u = dz/float(integrals[1])
    first = r['S_world_Y_interval_mm'][0]-a[1]
    # All five terms are physical arc lengths, using one strict total budget.
    turn_y = (r['free_length_mm']-first-length_s+r['S_world_Y_interval_mm'][1]-length_u+by)/2.
    bridge = turn_y-r['S_world_Y_interval_mm'][1]
    final = turn_y-by
    if min(first, bridge, final) < 0.:
        raise ValueError('negative straight in fixed-length EP4 route')
    k_u = 1.5*math.pi/length_u
    # |q''| <= 10/sqrt(3), (1+z'^2)^(3/2) >=1: continuous conservative S bound.
    k_s_bound = abs(rise)/(10.*math.sqrt(3.))
    return {'slide_mm': slide, 'descent_mm': descent, 'S_rise_mm': rise,
        'A_endpoint_world_mm': list(a), 'B_endpoint_world_mm': [b[0], by, b[2]+rise],
        'A_straight_mm': first, 'S_length_mm': length_s, 'bridge_straight_mm': bridge,
        'U_length_mm': length_u, 'B_straight_mm': final, 'U_start_world_Y_mm': turn_y,
        'U_B_local_delta_Z_mm': dz,
        'U_finite_head_world_Y_mm': turn_y+length_u*float(u_integral(.5, order)[0])+r['thickness_assumption_mm']/2.,
        'length_sum_mm': first+length_s+bridge+length_u+final,
        'target_free_length_mm': r['free_length_mm'],
        'U_max_abs_curvature_per_mm': k_u, 'S_continuous_abs_curvature_upper_bound_per_mm': k_s_bound,
        'minimum_centerline_radius_continuous_lower_bound_mm': 1./max(k_u, k_s_bound),
        'finite_thickness_Jacobian_continuous_lower_bound': 1.-r['thickness_assumption_mm']/2.*max(k_u, k_s_bound),
        'Gauss_Legendre_order': order, 'formal_directed_rounding_certificate': False,
        'material_length_derivation': 'A_straight+S_length+(U_start-90)+U_length+(U_start-B_world_Y)=100'}


def evaluate_material_station(distance, numbers, c=None):
    """One global physical arc-length label; the S u coordinate is inverted."""
    c = c or load_config(); r = c['route']; a = np.asarray(r['A_anchor_local_mm'], float)
    length = r['free_length_mm']; d = float(distance)
    if not 0. <= d <= length: raise ValueError('material label outside free length')
    first, ls, bridge, lu = (numbers[k] for k in ('A_straight_mm', 'S_length_mm', 'bridge_straight_mm', 'U_length_mm'))
    rise = numbers['S_rise_mm']; order = r['Gauss_Legendre_order']
    joins = (first, first+ls, first+ls+bridge, first+ls+bridge+lu)
    angle = 0.; curvature = 0.
    if d <= joins[0]:
        point = a+np.array([0., d, 0.])
    elif d < joins[1]:
        u = s_parameter_at_arc(d-first, rise, order)
        slope = rise*quintic_d1(u)/10.
        angle = math.atan(slope)
        curvature = rise*quintic_d2(u)/100./(1.+slope*slope)**1.5
        point = np.array([a[0], 80.+10.*u, a[2]+rise*quintic(u)])
    elif d <= joins[2]:
        point = np.array([a[0], 90.+d-joins[1], a[2]+rise])
    elif d < joins[3]:
        u = (d-joins[2])/lu
        iy, iz = u_integral(u, order)
        point = np.array([a[0], numbers['U_start_world_Y_mm']+lu*iy, a[2]+rise+lu*iz])
        angle = math.pi*(3*u*u-2*u*u*u)
        curvature = math.pi*(6*u-6*u*u)/lu
    else:
        point = np.array([a[0], numbers['U_start_world_Y_mm']-(d-joins[3]), numbers['B_endpoint_world_mm'][2]])
        angle = math.pi
    tangent = np.array([0., math.cos(angle), math.sin(angle)])
    # This normal never flips when the S signed curvature changes sign.
    normal = np.cross([1., 0., 0.], tangent)
    return point, tangent, normal, float(curvature)


def merged_material_stations(values, exact_joins, tolerance=1e-10):
    """Merge numerically identical s labels while preserving every exact join.

    Equal-s stations and a curved midpoint can differ by one floating-point
    ulp. Keeping both creates near-zero native polygon edges. This tolerance
    is many orders below the real 0.174 mm shortest bridge, which is retained.
    """
    ordered = sorted(float(v) for v in values)
    groups = []
    for value in ordered:
        if not groups or value-groups[-1][0] > tolerance: groups.append([value])
        else: groups[-1].append(value)
    result = []
    for group in groups:
        protected = [float(join) for join in exact_joins if group[0] <= join <= group[-1]]
        if len(set(protected)) > 1: raise ValueError('distinct physical joins collapsed by station tolerance')
        result.append(protected[0] if protected else group[0])
    if any(not any(value == float(join) for value in result) for join in exact_joins):
        raise ValueError('exact material join omitted')
    return np.asarray(result, float)


def route_sections(slide, descent, c=None):
    c = c or load_config(); r = c['route']; n = pose_numbers(slide, descent, c)
    first, ls, bridge, lu = (n[k] for k in ('A_straight_mm', 'S_length_mm', 'bridge_straight_mm', 'U_length_mm'))
    q = np.linspace(0., 1., r['curve_parameter_stations_each'])
    joins = np.array([0., first, first+ls, first+ls+bridge, first+ls+bridge+lu, r['free_length_mm']])
    stations = merged_material_stations(np.r_[np.linspace(0., r['free_length_mm'], r['base_stations']), joins,
        [first+s_arc_length(n['S_rise_mm'], float(u), r['Gauss_Legendre_order']) for u in q],
        first+ls+bridge+lu*q], joins)
    values = [evaluate_material_station(float(s), n, c) for s in stations]
    center = np.asarray([v[0] for v in values]); tangent = np.asarray([v[1] for v in values])
    normal = np.asarray([v[2] for v in values]); k = np.asarray([v[3] for v in values])
    widths = np.tile([1., 0., 0.], (len(stations), 1))
    normal_s = -k[:, None]*tangent
    uv = np.array([[-r['width_mm']/2, -r['thickness_assumption_mm']/2],
                   [r['width_mm']/2, -r['thickness_assumption_mm']/2],
                   [r['width_mm']/2, r['thickness_assumption_mm']/2],
                   [-r['width_mm']/2, r['thickness_assumption_mm']/2]])
    corners = center[:, None, :]+uv[None, :, 0, None]*widths[:, None, :]+uv[None, :, 1, None]*normal[:, None, :]
    jac = 1.-k[:, None]*uv[None, :, 1]
    if not np.allclose(center[[0, -1]], [n['A_endpoint_world_mm'], n['B_endpoint_world_mm']], atol=1e-10, rtol=0.):
        raise ValueError('arc-length construction missed a declared endpoint')
    if np.min(jac) <= 0.: raise ValueError('finite material has nonpositive sampled Jacobian')
    sections = {'s': stations, 'u': stations/r['free_length_mm'], 'center': center,
        'tangent': tangent, 'width_axis': widths, 'normal': normal, 'corners': corners,
        'jacobian': jac, 'curvature_per_mm': k, 'twist_rad_per_mm': np.zeros(len(stations)),
        'width_derivative': np.zeros_like(widths), 'normal_derivative': normal_s,
        'corner_axial_stretch': np.abs(jac)-1.}
    report = {**n, 'material_station_count': len(stations), 'exact_join_material_labels_mm': joins.tolist(),
        'end_tangents': tangent[[0, -1]].tolist(), 'end_normals': normal[[0, -1]].tolist(),
        'end_width_axes': widths[[0, -1]].tolist(),
        'centerline_polygon_length_mm': float(np.sum(np.linalg.norm(np.diff(center, axis=0), axis=1))),
        'minimum_sampled_Jacobian': float(np.min(jac)), 'G2_join_curvature_zero': True,
        'S_parameter_is_arc_length': False, 'all_material_s_labels_are_global_arc_length': True,
        'coincident_material_station_merge_tolerance_mm': 1e-10,
        'finite_model': 'explicit station polygon; curved joins inserted; extrusion preserves the listed finite vertices',
        'smooth_between_station_clearance_proved': False,
        'actual_flex_stack_or_fatigue_qualified': False}
    return sections, report


def arithmetic_report(c=None):
    c = c or load_config(); states = {label: pose_numbers(*pose, c) for label, pose in POSES.items()}
    st, pre = states['STOW'], states['PREDOCK']
    # STOW: S arc >= chord. This upper-bounds U_start and therefore its head.
    ts_chord = math.hypot(10., 8.2)
    conservative_head = st['U_finite_head_world_Y_mm']+(st['S_length_mm']-ts_chord)/2.
    return {'schema': 'razr-ep4-arithmetic-v1', 'candidate_id': c['candidate_id'],
        'source_sha256': {'design/product_routing_ep4.json': sha(CONFIG), 'integration/product_routing_ep4.py': sha(__file__)},
        'poses': states, 'free_plus_stiffened_material_mm': [100., 12., 12.],
        'continuous_necessary_bounds': {
            'minimum_bridge_straight_mm': st['bridge_straight_mm'],
            'minimum_B_straight_mm': pre['B_straight_mm'],
            'STOW_U_finite_head_upper_bound_using_S_chord_mm': conservative_head,
            'STOW_head_limit_mm': 94.,
            'minimum_Jacobian_lower_bound': min(x['finite_thickness_Jacobian_continuous_lower_bound'] for x in states.values()),
            'basis': 'S length decreases with descent and is constant during slide; U length is fixed; bridge minimum is STOW, B straight minimum is PREDOCK',
            'S_finite_Y_interval_mm': [80., 90.],
            'S_Y_monotonicity_basis': 'positive (1-eta*kappa)*T_y at both signed thickness offsets; endpoint normal Y is zero',
            'maximum_STOW_bridge_if_head_limit_is_preserved_mm': 94.-90.-(st['U_finite_head_world_Y_mm']-st['U_start_world_Y_mm']),
            'three_mm_straight_request_applies_to_endpoint_tail_only': True,
            'three_mm_guide_cannot_fit_the_STOW_S_to_U_bridge': True,
            'empty_internal_channel_or_clearance_proved': False},
        'endpoint_changes': {'A_carrier_plate_tail_Y_mm': [13.2, 36.], 'A_web_tail_Y_mm': [13.25, 13.7],
            'B_board_carrier_transfer_tail_direction_mm': [24., 36.],
            'unchanged_local_part_names': list(PART_NAMES),
            'nominal_B_low_lane_to_complete_endpoint_Z_gap_mm': .05,
            'nominal_gap_is_not_manufacturing_margin': True},
        'OPEN_curve_matches_EP3_analytic_OPEN': True,
        'OPEN_implication': 'The S rise vanishes and its collinear stations do not remove old OPEN route-to-mechanism intersections; native Common still decides actual geometric rejection',
        'native_checks_executed': False, 'complete_motion_accepted': False,
        **{k: False for k in GO_KEYS}}


def ep4_local_parts(end, c=None):
    """Keep every finite endpoint body; only the declared EP4 geometry changes."""
    c = c or load_config()
    if end not in ('A', 'B'): raise ValueError('unknown endpoint')
    import cadquery as cq
    import product_assembly as p
    box = lambda x0, x1, y0, y1, z0, z1: p.box((x0, y0, z0), (x1, y1, z1))
    cyl = lambda x, y, z, h, radius: cq.Solid.makeCylinder(radius, h, cq.Vector(x, y, z))
    e = c['endpoint']; y0, y1 = e[f'PCB_{end}_tail_coordinate_Y_mm']
    plate_y = e[f'{end}_carrier_plate_tail_Y_mm']; web_y = e[f'{end}_carrier_web_tail_Y_mm']
    parts = {'tail': box(-6, 6, 0, 12, -.05, .05), 'stiffener': box(-6, 6, 0, 12, -.25, -.05)}
    outer = box(-6, 6, 7, 21, -.6, -.25)
    carrier = box(-6, 6, 7, 21, .05, .85)
    plate = box(-6, 6, *plate_y, 2.9, 3.3)
    web = box(-6, 6, *web_y, .8, 3.3)
    ledge = box(-6, 6, 23.6, 36, .1, .3)
    post = box(-6, 6, 23.6, 23.8, .1, 3.3)
    carrier = carrier.fuse(plate).fuse(web).fuse(ledge).fuse(post)
    carrier = carrier.cut(box(-5.4, 5.4, 5, 36, 1.1, 1.75))
    for i, y in enumerate((15., 19.), 1):
        hole = cyl(0, y, -1, 4.5, 1.1)
        outer, carrier = outer.cut(hole), carrier.cut(hole)
        parts[f'M2_clamp_screw_{i}'] = cyl(0, y, -.55, 1.4, 1.)
        parts[f'M2_clamp_head_{i}'] = cyl(0, y, .85, .6, 1.75)
    dp, ds = box(-6, 6, y0, y1, .3, 1.1), box(-6, 6, y0, y1, 1.7, 2.5)
    holes = [(-5, y0+1.3), (5, y0+1.3), (-5, y1-1.3), (5, y1-1.3)]
    for i, (x, y) in enumerate(holes, 1):
        hole = cyl(x, y, 0, 3, .7)
        dp, ds = dp.cut(hole), ds.cut(hole)
        carrier = carrier.cut(cyl(x, y, .05, .3, .55))
        parts[f'M1_board_shaft_{i}'] = cyl(x, y, .1, 2.4, .5)
        parts[f'M1_board_head_{i}'] = cyl(x, y, 2.5, .4, .9)
    mid = (y0+y1)/2.
    parts['mini_DP_PCB'], parts['mini_DS_PCB'] = dp, ds
    parts['mated_BM28_reservation'] = box(-3.5, 3.5, mid-.95, mid+.95, 1.1, 1.7)
    transfer = box(-5.3, 5.3, 5.3, y1-.05, 1.15, 1.7)
    transfer = transfer.fuse(box(-5.3, 5.3, 5.25, 5.5, .05, 1.7))
    transfer = transfer.fuse(box(-5.3, 5.3, 0, 5.5, .05, .25))
    for y in (15., 19.): transfer = transfer.cut(cyl(0, y, 1.1, .7, 1.85))
    transfer = transfer.cut(box(-3.7, 3.7, mid-1.15, mid+1.15, 1.1, 1.75))
    for x, y in holes: transfer = transfer.cut(cyl(x, y, 1.1, .7, .75))
    parts['outer_stiffener_jaw'] = outer.clean()
    parts['inner_carrier_jaw'] = carrier.clean()
    parts['static_26wire_transfer_reservation'] = transfer.clean()
    if end == 'A': parts = {name: body.mirror('XZ') for name, body in parts.items()}
    if tuple(sorted(parts)) != PART_NAMES: raise ValueError('complete endpoint inventory changed')
    for name, body in parts.items():
        leaves, value = p.whole_material(body)
        if len(leaves) != 1 or value <= 0.:
            raise ValueError('endpoint body is not one valid positive solid: ' + end + '_' + name)
    return parts


def native_metrics(body, *, require_single=True):
    import product_assembly as p
    leaves, value = p.whole_material(body)
    if require_single and len(leaves) != 1:
        raise ValueError('participant must be one positive solid')
    bounds = [float(x) for x in p.bounds(body)]
    if not all(math.isfinite(x) for x in bounds):
        raise ValueError('nonfinite native bounds')
    return {'bounds_mm': bounds, 'volume_mm3': float(value), 'positive_valid_solids': len(leaves)}


def export_shape(body, path):
    """Export actual material, including every disconnected Common solid."""
    import cadquery as cq
    import product_assembly as p
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    leaves, _ = p.whole_material(body)
    result = native_metrics(body, require_single=False)
    result['solids'] = [native_metrics(s) for s in leaves]
    cq.exporters.export(body, str(path))
    return {**result, 'file': str(path.name), 'sha256': sha(path),
            'independent_process_readback_executed': False}


def axis_gap(first, second):
    return max(max(first[2*i]-second[2*i+1], second[2*i]-first[2*i+1]) for i in range(3))


def local_wall_context(name):
    """An AABB depth is never substituted for actual local wall thickness."""
    nominal = None
    if name.endswith('inner_carrier_jaw'):
        nominal = {'carrier_plate_mm': .4, 'jaw_mm': .8, 'board_ledge_mm': .2,
                   'source': 'product_routing_ep4.ep4_local_parts; feature values are not a thickness map at the Common'}
    elif name.endswith('outer_stiffener_jaw'):
        nominal = {'jaw_mm': .35, 'source': 'product_routing_ep4.ep4_local_parts'}
    elif name in ('A_FRAME', 'A_BACK_PANEL', 'B_SHELL'):
        nominal = {'study_wall_parameter_mm': .65,
                   'source': 'design/product_geometry.json dimensions.study_wall_mm; not the local minimum of a modified shell'}
    return {'part': name, 'actual_local_wall_thickness_mm': None,
        'actual_local_wall_thickness_status': 'unknown',
        'reason': 'No measured wall or local opposing-face thickness calculation is supplied; inspect the exported finite native neighborhood',
        'nominal_design_context': nominal, 'thickness_inferred_from_bounds': False,
        'real_component_or_process_qualified': False}


def common_context(common, pair_names, context_parts, context_metrics, directory, c):
    import cadquery as cq
    import product_assembly as p
    bounds = p.bounds(common); margin = c['native_scope']['common_context_margin_mm']
    roi_bounds = [float(v-margin if i % 2 == 0 else v+margin) for i, v in enumerate(bounds)]
    roi = p.box((roi_bounds[0], roi_bounds[2], roi_bounds[4]), (roi_bounds[1], roi_bounds[3], roi_bounds[5]))
    wall_names = {'A_FRAME', 'A_BACK_PANEL', 'B_SHELL', 'A_DISPLAY_SUPPORT',
        'B_OPEN_DISPLAY_SUPPORT_ACCESSORY', 'L_CROSSHEAD', 'R_CROSSHEAD', 'L_KEY', 'R_KEY',
        'L_CROSSHEAD_TUBE_BOTTOM_CAP', 'R_CROSSHEAD_TUBE_BOTTOM_CAP',
        'L_KEY_FOLLOWER_LOWER_FLANGE', 'R_KEY_FOLLOWER_LOWER_FLANGE'}
    wall_names.update(name for name in context_parts if name.endswith(('inner_carrier_jaw', 'outer_stiffener_jaw')))
    included = sorted(set(pair_names) | {name for name in wall_names if name in context_parts
        and axis_gap(roi_bounds, context_metrics[name]['bounds_mm']) <= TOL})
    rows = []; assembly = cq.Assembly(name='NATIVE_COMMON_2MM_CONTEXT')
    for name in included:
        row = local_wall_context(name)
        try:
            crop = context_parts[name].intersect(roi)
            leaves, value = p.whole_material(crop, empty=True)
            row.update(crop_volume_mm3=float(value), crop_positive_solids=len(leaves))
            if leaves:
                row['crop_bounds_mm'] = [float(v) for v in p.bounds(crop)]
                row['crop_solids'] = [native_metrics(s) for s in leaves]
                assembly.add(crop, name=name)
        except Exception as exc:
            row.update(crop_evaluation_failed=True, error_type=type(exc).__name__, error=str(exc))
        rows.append(row)
    if any(row.get('crop_positive_solids', 0) > 0 for row in rows):
        path = Path(directory)/'neighborhood.step'
        assembly.export(str(path))
        exported = {'file': path.name, 'sha256': sha(path), 'independent_readback_executed': False}
    else:
        exported = None
    errors = [row for row in rows if row.get('crop_evaluation_failed', False)]
    return {'ROI_bounds_mm': roi_bounds, 'margin_each_face_mm': margin,
        'scope': 'native material clipped by a local review box; not a wall-removal proposal or minimum-thickness certificate',
        'parts': rows, 'neighborhood_STEP': exported,
        'crop_evaluation_errors': errors,
        'local_material_context_complete': not errors and exported is not None,
        'actual_local_wall_thickness_status': 'unknown'}


def native_pairs(parts_a, directory, c, *, parts_b=None, context_parts=None,
                 metrics_a=None, metrics_b=None, context_metrics=None, coordinate_frame='world'):
    """Validate once, cache exact geometry bounds, and reject Boolean errors.

    Positive native material is exported even when its volume is <=TOL.
    The broad phase uses a strictly positive >TOL gap; touching/near boxes
    still get an actual Common operation. No participant is dropped.
    """
    import product_assembly as p
    directory = Path(directory); directory.mkdir(parents=True)
    ma = metrics_a or {k: native_metrics(v) for k, v in parts_a.items()}
    mb = (metrics_b or {k: native_metrics(v) for k, v in parts_b.items()}) if parts_b is not None else ma
    context_parts = context_parts or ({**parts_a, **parts_b} if parts_b is not None else parts_a)
    context_metrics = context_metrics or {k: native_metrics(v) for k, v in context_parts.items()}
    pairs = itertools.product(sorted(parts_a), sorted(parts_b)) if parts_b is not None else itertools.combinations(sorted(parts_a), 2)
    rows = []; native_calls = 0
    for index, (a, b) in enumerate(pairs):
        first = parts_a[a]; second = parts_b[b] if parts_b is not None else parts_a[b]
        row = {'a': a, 'b': b, 'coordinate_frame': coordinate_frame,
               'a_bounds_mm': ma[a]['bounds_mm'], 'b_bounds_mm': mb[b]['bounds_mm']}
        try:
            gap = axis_gap(ma[a]['bounds_mm'], mb[b]['bounds_mm'])
            if gap > TOL:
                row.update(method='cached_native_geometry_bounds_positive_axis_gap', axis_gap_lower_mm=gap,
                           common_mm3=0., rejected=False)
            else:
                native_calls += 1
                common = first.intersect(second)
                leaves, value = p.whole_material(common, empty=True)
                value = float(value)
                if value > min(ma[a]['volume_mm3'], mb[b]['volume_mm3'])+TOL:
                    raise ValueError('Common volume exceeds a complete participant')
                row.update(method='native_Common', common_mm3=value,
                           common_positive_solids=len(leaves), rejected=value > TOL)
                if leaves:
                    folder = directory/f'{index:05d}-{a[:48]}--{b[:48]}'
                    artifact = export_shape(common, folder/'Common.step')
                    row['common_artifact_directory'] = folder.name
                    row['common_material'] = artifact
                    row['local_material_context'] = common_context(common, (a, b), context_parts, context_metrics, folder, c)
                    row['artifact_diagnostics_complete'] = row['local_material_context']['local_material_context_complete']
                    if not row['artifact_diagnostics_complete']:
                        row.update(diagnostic_artifact_failure=True, rejected=True)
        except Exception as exc:
            row.update(evaluation_failed=True, rejected=True, error_type=type(exc).__name__, error=str(exc))
        rows.append(row)
    result = {'pair_count': len(rows), 'native_Common_calls': native_calls,
        'cached_axis_gap_rejections_of_intersection': len(rows)-native_calls,
        'positive_Common_count_including_below_tolerance': sum(r.get('common_mm3', 0.) > 0. for r in rows),
        'rejection_volume_tolerance_mm3': TOL, 'rows': rows,
        'failures': [row for row in rows if row['rejected']],
        'no_Common_above_tolerance_or_evaluation_error': all(not row['rejected'] for row in rows),
        'all_positive_Common_artifact_diagnostics_complete': all(
            r.get('artifact_diagnostics_complete', False) for r in rows if r.get('common_mm3', 0.) > 0.),
        'coordinate_frame': coordinate_frame,
        'bounds_method': 'BRepBndLib.AddOptimal_s(useTriangulation=False, useShapeTolerance=False) via product_assembly.bounds',
        'artifact_paths_relative_to': str(directory), 'smooth_or_continuous_clearance_accepted': False}
    write_json(directory/'pairs.json', result)
    return result


def outer_domains(scene, c):
    import product_assembly as p
    b = [float(x) for x in p.bounds(scene['B_SHELL'])]
    boxes = [p.bounds(scene[k]) for k in ('A_FRAME', 'A_BACK_PANEL', 'A_DISPLAY_SUPPORT')]
    a = [float(min(v[2*i] for v in boxes) if side == 0 else max(v[2*i+1] for v in boxes))
         for i in range(3) for side in range(2)]
    expected = c['domain']['finished_cabin_outer_bounds_local_mm']
    if any(abs(x-y) > TOL for x, y in zip(a, expected)):
        raise ValueError('native A outer envelope changed')
    if any(abs((b[2*i+1]-b[2*i])-(a[2*i+1]-a[2*i])) > TOL for i in range(3)):
        raise ValueError('native cabin outer dimensions no longer equal')
    build = lambda q: p.box((q[0], q[2], q[4]), (q[1], q[3], q[5]))
    return [build(a), build(b)], {'A_bounds_mm': a, 'B_bounds_mm': b,
        'meaning': 'union of two separate optimistic outer prisms, not an empty internal cavity',
        'global_enclosing_box_used': False, 'actual_internal_cross_cabin_opening_proved': False}


def containment(parts, domains, output=None):
    import product_assembly as p
    rows = []
    for name, body in sorted(parts.items()):
        row = {'part': name}
        try:
            residual = body; leaves, original = p.whole_material(residual)
            if not leaves or original <= 0.: raise ValueError('positive containment participant required')
            outside = original; cuts = 0
            for domain in domains:
                if not leaves: break
                residual = residual.cut(domain)
                leaves, outside = p.whole_material(residual, empty=True)
                cuts += 1
            if outside > original+TOL: raise ValueError('outside volume exceeds original material')
            row.update(outside_outer_union_mm3=float(outside), native_domain_cuts_executed=cuts,
                validated_empty_result=not leaves, rejected=outside > TOL,
                method='sequential cuts by separate domains; stop only at validated empty material')
            if leaves and output is not None:
                row['outside_material'] = export_shape(residual, Path(output)/(name+'-outside.step'))
        except Exception as exc:
            row.update(evaluation_failed=True, rejected=True, error_type=type(exc).__name__, error=str(exc))
        rows.append(row)
    return {'parts': len(parts), 'rows': rows, 'failures': [row for row in rows if row['rejected']],
        'all_material_inside_optimistic_outer_union': all(not row['rejected'] for row in rows),
        'actual_internal_channel_clearance_accepted': False}


def runtime_identity():
    versions = {}
    for name in ('cadquery', 'cadquery-ocp', 'numpy'):
        try: versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError: versions[name] = 'not installed'
    return {'started_UTC': datetime.now(timezone.utc).isoformat(), 'PID': os.getpid(), 'PPID': os.getppid(),
        'python_executable': sys.executable, 'python_version': sys.version, 'packages': versions,
        'argv': sys.argv, 'source_root': str(ROOT)}


def source_identity():
    names = ['integration/product_routing_ep4.py', 'design/product_routing_ep4.json',
        'integration/product_routing_ep3.py', 'design/product_routing_ep3.json',
        'integration/product_split_assembly.py', 'integration/product_assembly.py',
        'integration/product_fpc.py', 'integration/product_interfaces.py', 'integration/oled_storage.py',
        'integration/product_motion.py', 'integration/cam_coupling.py', 'integration/straight_envelope.py',
        'engineering/product-integration-20261018/physical-test-followon-20261019/captured_follower_assembly.py',
        'design/product_geometry.json', 'design/product_interfaces.json']
    result = {name: sha(ROOT/name) for name in names}
    if result['integration/product_routing_ep3.py'] != BASELINE_EP3_SHA:
        raise ValueError('EP4 baseline must be actual repaired A33 EP3; frozen source identity differs')
    return result


def new_output(path):
    path = Path(path).resolve()
    if path.exists() or path == ROOT or ROOT in path.parents:
        raise ValueError('use a new output directory outside source')
    path.mkdir(parents=True)
    return path


def native_report(output, labels=('PREDOCK',), c=None):
    import cadquery as cq
    import product_assembly as p
    import product_fpc as f
    import product_split_assembly as split
    import oled_storage
    c = c or load_config(); output = new_output(output)
    if not labels or len(set(labels)) != len(labels) or any(label not in POSES for label in labels):
        raise ValueError('unique named EP4 poses required')
    if list(labels) != [name for name in POSES if name in labels]:
        raise ValueError('execute selected poses in PREDOCK, OPEN, STOW order')
    before = source_identity(); runtime = runtime_identity()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    local = {end: ep4_local_parts(end, c) for end in ('A', 'B')}
    endpoint_exports = {}; self_checks = {}
    for end, parts in local.items():
        compound = cq.Compound.makeCompound(list(parts.values()))
        endpoint_exports[end] = export_shape(compound, output/('EP4-'+end+'-complete.step'))
        endpoint_exports[end]['parts'] = {name: native_metrics(body) for name, body in sorted(parts.items())}
        named = {end+'_'+name: body for name, body in parts.items()}
        self_checks[end] = native_pairs(named, output/('local-'+end+'-self'), c, coordinate_frame=end+' endpoint local')
    completed = []
    for label in labels:
        folder = output/label; folder.mkdir()
        slide, descent = POSES[label]; accessories = label == 'OPEN'; tab = 0. if label == 'STOW' else 3.
        scene, scene_meta = split.split_scene(slide, descent, tab, tab,
            open_hold=accessories, open_support=accessories)
        mechanical = len(scene); expected_mechanical = 115 if accessories else 108
        if mechanical != expected_mechanical: raise ValueError('native mechanical inventory changed')
        scene.update(p.registered_components(p.load_config(), slide, descent))
        scene['OLED_GEOMETRIC_TRIAL'], oled_meta = oled_storage.geometry(slide, descent)
        if len(scene) != mechanical+5: raise ValueError('allocation or full OLED participant omitted')
        sections, route = route_sections(slide, descent, c)
        material, finite = f.finite_material_solid(sections['corners'])
        placed = {end: f.place_endpoint(local[end], sections, end) for end in ('A', 'B')}
        complete = {'EP4_finite_material': material, **placed['A'], **placed['B']}
        if len(complete) != 41: raise ValueError('complete endpoint or finite free material omitted')
        all_parts = {**scene, **complete}
        records = {name: native_metrics(body) for name, body in sorted(all_parts.items())}
        sm = {name: records[name] for name in scene}; cm = {name: records[name] for name in complete}
        # Export the entire review object before performing expensive diagnostics.
        assembly = cq.Assembly(name='EP4_BOUNDED_'+label)
        for name, body in sorted(all_parts.items()): assembly.add(body, name=name)
        step = folder/(label+'-complete-EP4.step'); assembly.export(str(step))
        npz = folder/'material-sections.npz'; np.savez_compressed(npz, **sections)
        common_args = {'context_parts': all_parts, 'context_metrics': records}
        external = native_pairs(complete, folder/'external-common', c, parts_b=scene,
            metrics_a=cm, metrics_b=sm, **common_args)
        endpoint_cross = native_pairs(placed['A'], folder/'A-to-B-common', c, parts_b=placed['B'],
            metrics_a={k: cm[k] for k in placed['A']}, metrics_b={k: cm[k] for k in placed['B']}, **common_args)
        material_to_ends = native_pairs({'EP4_finite_material': material}, folder/'material-to-ends-common', c,
            parts_b={**placed['A'], **placed['B']}, metrics_a={'EP4_finite_material': cm['EP4_finite_material']},
            metrics_b={k: cm[k] for k in complete if k != 'EP4_finite_material'}, **common_args)
        domains, domain_meta = outer_domains(scene, c)
        domain_check = containment(complete, domains, folder/'outside-domain')
        rejection = any(not v['no_Common_above_tolerance_or_evaluation_error']
            for v in [*self_checks.values(), external, endpoint_cross, material_to_ends]) or bool(domain_check['failures'])
        row = {'pose': label, 'mechanical_participants': mechanical, 'external_participants': len(scene),
            'candidate_participants': 41, 'combined_participants': len(all_parts),
            'scene': scene_meta, 'OLED': oled_meta, 'route': route, 'finite_material': finite,
            'parts': records, 'all_assembly_source_parts_have_native_bounds_and_volume': True,
            'complete_assembly_STEP': {'file': str(step.relative_to(output)), 'sha256': sha(step),
                'expected_solids': len(all_parts), 'independent_process_readback_executed': False},
            'material_sections': {'file': str(npz.relative_to(output)), 'sha256': sha(npz)},
            'external': external, 'A_to_B_endpoints': endpoint_cross, 'material_to_all_40_endpoint_parts': material_to_ends,
            'endpoint_self_checks_reused_under_validated_proper_rigid_placement': True,
            'outer_domain': domain_meta, 'containment': domain_check,
            'decisive_geometric_rejection_or_evaluation_failure': rejection,
            'all_declared_checks_clear_at_this_finite_pose': not rejection,
            'empty_internal_channel_or_continuous_motion_accepted': False}
        completed.append(row)
        write_json(output/'progress.json', {'source_commit': commit, 'source_sha256': before,
            'runtime': runtime, 'completed_poses': completed, 'complete': False, **{k: False for k in GO_KEYS}})
        print(json.dumps({'pose': label, 'assembly_solids': len(all_parts), 'external_pairs': external['pair_count'],
            'external_native_Common_calls': external['native_Common_calls'], 'external_failures': len(external['failures']),
            'outside_domain_parts': len(domain_check['failures']), 'decisive_rejection': rejection}), flush=True)
    after = source_identity()
    unchanged = before == after and all(p.source_unchanged(row['scene']) for row in completed)
    if not unchanged: raise ValueError('native inputs changed during EP4 execution')
    rejected = any(row['decisive_geometric_rejection_or_evaluation_failure'] for row in completed)
    result = {'schema': 'razr-ep4-bounded-native-v1', 'candidate_id': c['candidate_id'],
        'source_commit': commit, 'reference_commit_abbrev': c['basis_commit_abbrev'],
        'source_sha256': before, 'source_bytes_unchanged': unchanged, 'runtime': runtime,
        'native_checks_executed': True, 'selected_poses': list(labels), 'endpoint_exports': endpoint_exports,
        'endpoint_self_checks': self_checks, 'poses': completed,
        'scope': 'all 41 candidate bodies against every external participant at each selected finite pose; no external/external rerun',
        'geometric_rejection_found': rejected,
        'stop_reason': 'selected bounded pose list completed; geometric failures retained' if rejected else 'selected finite poses completed; continuous and physical qualification remain unproved',
        'fixed_free_material_length_mm': 100., 'total_material_length_including_two_stiffened_ends_mm': 124.,
        'real_donor_geometry_included': False, 'actual_OLED_COF_or_flex_stack_selected': False,
        'actual_local_wall_thickness_status': 'unknown', **{k: False for k in GO_KEYS}}
    write_json(output/'native-report.json', result)
    return result


def native_regressions(output, c=None):
    """Small geometry regressions. No complete mechanical pose is generated."""
    import product_assembly as p
    import product_fpc as f
    import product_routing_ep3 as old
    c = c or load_config(); output = new_output(output)
    before = source_identity(); runtime = runtime_identity(); rows = []
    local = {end: ep4_local_parts(end, c) for end in ('A', 'B')}
    old_local = {end: old.ep3_local_parts(end) for end in ('A', 'B')}
    for end in ('A', 'B'):
        carrier = native_metrics(local[end]['inner_carrier_jaw'])
        rows.append({'case': end+'_carrier_connected_after_plate_web_change',
                     'pass': carrier['positive_valid_solids'] == 1, 'actual': carrier})
    st_sections, _ = route_sections(0., 0., c)
    old_a = f.place_endpoint(old_local['A'], st_sections, 'A')['A_inner_carrier_jaw']
    new_a = f.place_endpoint(local['A'], st_sections, 'A')['A_inner_carrier_jaw']
    battery = p.registered_components(p.load_config(), 0., 0.)['A_BATTERY_ALLOCATION']
    old_overlap = p.strict_common(old_a, battery)['common_mm3']
    new_overlap = p.strict_common(new_a, battery)['common_mm3']
    negative_parts = {'A33_A_inner_carrier_jaw': old_a, 'A_BATTERY_ALLOCATION': battery}
    negative_context = common_context(old_a.intersect(battery), tuple(negative_parts), negative_parts,
        {name: native_metrics(body) for name, body in negative_parts.items()}, output, c)
    rows.append({'case': 'retained_A33_18mm3_negative_and_EP4_A_battery_pair',
        'old_common_mm3': old_overlap, 'new_common_mm3': new_overlap,
        'pass': abs(old_overlap-18.) <= 1e-6 and new_overlap <= TOL and negative_context['local_material_context_complete'],
        'old_Common_context': negative_context,
        'old_Common': export_shape(old_a.intersect(battery), output/'A33-A-carrier-battery-Common.step')})
    translated_names = ['mini_DP_PCB', 'mini_DS_PCB', 'mated_BM28_reservation'] + [
        f'M1_board_{role}_{i}' for role in ('shaft', 'head') for i in (1, 2, 3, 4)]
    relocation = []
    for name in translated_names:
        reference = old_local['B'][name].translate((0., 38., 0.))
        actual = local['B'][name]
        lost, added = p.volume(reference.cut(actual)), p.volume(actual.cut(reference))
        relocation.append({'part': name, 'reference_minus_EP4_mm3': lost, 'EP4_minus_reference_mm3': added})
    pre_sections, _ = route_sections(79.75, 0., c)
    placed_b = f.place_endpoint(local['B'], pre_sections, 'B')
    dp, ds = (p.bounds(placed_b['B_'+name]) for name in ('mini_DP_PCB', 'mini_DS_PCB'))
    frames_pass = (np.allclose(pre_sections['tangent'][-1], [0., -1., 0.], atol=1e-12) and
                   np.allclose(pre_sections['normal'][-1], [0., 0., -1.], atol=1e-12))
    rows.append({'case': 'complete_B_board_group_relocation_and_proper_world_frame',
        'translated_parts': relocation, 'world_DP_bounds_mm': dp, 'world_DS_bounds_mm': ds,
        'world_board_face_gap_mm': dp[4]-ds[5],
        'pass': bool(frames_pass and all(max(r['reference_minus_EP4_mm3'], r['EP4_minus_reference_mm3']) <= TOL for r in relocation)
            and np.allclose(dp[2:4], [83.75, 95.75], atol=1e-7, rtol=0.) and abs(dp[4]-ds[5]-.6) <= 1e-7)})
    transfer = local['B']['static_26wire_transfer_reservation']
    probes = [p.box((4., 1., .1), (4.2, 2., .2)), p.box((4., 29., 1.2), (4.2, 30., 1.6))]
    probe_metrics = [{'probe_mm3': p.volume(q), 'transfer_Common_mm3': p.strict_common(transfer, q)['common_mm3']} for q in probes]
    rows.append({'case': 'B_complete_static_transfer_connected_and_reaches_tail_and_board_reservations',
        'transfer': native_metrics(transfer), 'endpoint_volume_probes': probe_metrics,
        'pass': all(abs(r['probe_mm3']-r['transfer_Common_mm3']) <= TOL for r in probe_metrics),
        'individual_26_conductors_or_electrical_connection_proved': False})
    finite_rows = []
    for label, pose in POSES.items():
        sections, route = route_sections(*pose, c); material, _ = f.finite_material_solid(sections['corners'])
        polygon = np.concatenate([sections['corners'][:, 0], sections['corners'][::-1, 3]])[:, 1:]
        polygon_area = abs(float(np.sum(polygon[:, 0]*np.roll(polygon[:, 1], -1)-polygon[:, 1]*np.roll(polygon[:, 0], -1))))/2.
        volume = p.volume(material); expected = 12.*polygon_area
        finite_rows.append({'pose': label, 'native_volume_mm3': volume, 'independent_polygon_volume_mm3': expected,
            'positive_valid_solids': native_metrics(material)['positive_valid_solids'],
            'pass': abs(volume-expected) <= 1e-6 and route['minimum_sampled_Jacobian'] > 0.})
    rows.append({'case': 'finite_S_U_extrusion_preserves_declared_polygon_at_three_poses',
        'poses': finite_rows, 'pass': all(r['pass'] for r in finite_rows)})
    a_domain = p.box((0., 0., 0.), (2., 2., 2.)); b_domain = p.box((2., 0., 0.), (4., 2., 2.))
    tests = [('A_inside', .5, 1.5, 0., 1), ('B_inside', 2.5, 3.5, 0., 2),
             ('cross_two_domains', .5, 3.5, 0., 2), ('outside', 4.5, 5.5, 1., 2)]
    domain_rows = []
    for label, x0, x1, expected, cuts in tests:
        record = containment({label: p.box((x0, .5, .5), (x1, 1.5, 1.5))}, [a_domain, b_domain])['rows'][0]
        domain_rows.append({'case': label, 'actual': record,
            'pass': not record.get('evaluation_failed', False) and abs(record['outside_outer_union_mm3']-expected) <= TOL
                    and record['native_domain_cuts_executed'] == cuts})
    gap_b = p.box((3., 0., 0.), (5., 2., 2.))
    gap = containment({'gap': p.box((1., .5, .5), (4., 1.5, 1.5))}, [a_domain, gap_b])['rows'][0]
    domain_rows.append({'case': 'real_gap_not_global_enclosing_box', 'actual': gap,
        'pass': not gap.get('evaluation_failed', False) and abs(gap['outside_outer_union_mm3']-1.) <= TOL})
    rows.append({'case': 'validated_empty_short_circuit_and_separate_domain_regressions',
        'subcases': domain_rows, 'pass': all(r['pass'] for r in domain_rows)})
    unchanged = before == source_identity()
    result = {'schema': 'razr-ep4-small-native-regressions-v1', 'runtime': runtime,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_sha256': before, 'source_bytes_unchanged': unchanged, 'cases': rows,
        'native_regressions_passed': unchanged and all(row['pass'] for row in rows),
        'complete_phone_scene_or_full_motion_tested': False, **{k: False for k in GO_KEYS}}
    write_json(output/'native-regressions.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--native', action='store_true')
    mode.add_argument('--native-regression', action='store_true')
    parser.add_argument('--poses', nargs='+', choices=list(POSES), default=['PREDOCK'],
        help='finite selected scope, in PREDOCK OPEN STOW order; default PREDOCK alone')
    args = parser.parse_args(); c = load_config(); output = new_output(args.output)
    write_json(output/'arithmetic.json', arithmetic_report(c))
    try:
        if args.native:
            report = native_report(output/'native', args.poses, c)
            print(json.dumps({'native_completed': True, 'selected_poses': args.poses,
                'geometric_rejection_found': report['geometric_rejection_found'], **{k: False for k in GO_KEYS}}))
        elif args.native_regression:
            report = native_regressions(output/'native-regression', c)
            print(json.dumps({'native_regressions_passed': report['native_regressions_passed'], **{k: False for k in GO_KEYS}}))
            if not report['native_regressions_passed']: return 2
        else:
            print(json.dumps({'arithmetic_completed': True, 'native_executed': False, **{k: False for k in GO_KEYS}}))
    except Exception as exc:
        write_json(output/'native-execution-failure.json', {'error_type': type(exc).__name__, 'error': str(exc),
            'traceback': traceback.format_exc(), 'runtime': runtime_identity(),
            'completed_native_report': False, **{k: False for k in GO_KEYS}})
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
