"""Continuous material enclosures for the original SEATING flex families.

Arithmetic helpers import the original EP5/EP4 route definitions but no CAD.
Native cage construction is a separate, lazy function for a later guarded run.
The finite EP5 polygon and its straight taper wings are explicitly covered.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import math
from pathlib import Path
import sys

import numpy as np

from seating_domain import interval, SEATING

ROOT = Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True
if str(ROOT / 'integration') not in sys.path:
    sys.path.insert(0, str(ROOT / 'integration'))
import product_routing_ep5 as ep5

GUARD = 1e-7


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configuration():
    c = ep5.load_config()
    # These exact mandatory stations, joins and finite polygon semantics
    # are part of the enclosure proof, not arbitrary plotting resolution.
    if c['route']['curve_parameter_stations_each'] != 49:
        raise ValueError('the 48 mandatory curve intervals changed')
    return c


def frame_factor(frame):
    if frame not in ('A', 'B'):
        raise ValueError('only original A/B reference frames are supported')
    return 0. if frame == 'A' else 1.


def box_record(label, x, y, z, method):
    low = [float(x[0]), float(y[0]), float(z[0])]
    high = [float(x[1]), float(y[1]), float(z[1])]
    if any(not math.isfinite(v) for v in low + high) or any(a >= b for a, b in zip(low, high)):
        raise ValueError('finite positive material enclosure required')
    return {'label': label, 'kind': 'box', 'low_mm': low, 'high_mm': high, 'method': method}


def _bounds(rows):
    return [min(row['low_mm'][i] for row in rows) if end == 0 else max(row['high_mm'][i] for row in rows)
            for i in range(3) for end in (0, 1)]


def _range(values):
    values = tuple(values)
    return float(min(values)), float(max(values))


@lru_cache(maxsize=128)
def fpc_cells(low=0., high=8.2, frame='A'):
    """Bounds of every finite-polygon cell, over an entire d subinterval.

    The route always inserts 49 stations on each curved segment and retains
    every exact join. Thus no finite edge can span more than one mandatory
    curve interval, except the <=1e-10 mm merge slack covered by GUARD.
    On S, Y and the quintic parameter are monotone. On each half of a U,
    Y is monotone; U Z is monotone over the whole turn. Endpoint coordinate
    extrema plus the complete normal thickness bound enclose every corner
    and therefore each finite straight edge and convex section cell.

    This also encloses the entire actual polygon interior: the oriented
    boundaries of consecutive section quadrilaterals sum to the original
    lower-chain/reversed-upper-chain polygon, because internal section
    edges cancel. Triangulate each quadrilateral as an oriented 2-chain.
    A point outside every cell box has zero winding in every such triangle
    and hence in the original polygon. Thus every valid polygon interior
    point lies in the box union. No ideal smooth loft is substituted.
    """
    low, high = map(float, interval(low, high))
    ref = frame_factor(frame)
    c = configuration()
    route = c['route']
    count = route['curve_parameter_stations_each'] - 1
    width = route['middle_width_mm']
    t = route['thickness_assumption_mm']
    pad = t / 2. + GUARD
    x = (-width / 2., width / 2.)
    flat = 8.2 + route['B_low_lane_z_mm'] - route['A_anchor_local_mm'][2]
    extrema = sorted({low, high, *([flat] if low <= flat <= high else [])})
    numbers = [ep5.pose_numbers(79.75, d, c) for d in extrema]
    first_low, first_high = _range(n['U1_start_world_Y_mm'] for n in numbers)
    base = numbers[0]
    samples = np.linspace(0., 1., count + 1)
    integrals = np.asarray([ep5.ep4.u_integral(float(u), route['Gauss_Legendre_order']) for u in samples])
    rows = []
    a = route['A_anchor_local_mm']
    # Planar straight/taper end faces remain exact. Isotropic normal padding
    # at their Y ends would invent penetration into the adjoining endpoint.
    az = _range(a[2] + ref * d for d in (low, high))
    rows.append(box_record('A_straight_core', x, (a[1], 76.),
                           (az[0] - t / 2., az[1] + t / 2.), 'complete straight core'))
    ew = route['endpoint_width_mm']
    rows.append(box_record('A_taper_wings', (-ew / 2., ew / 2.),
                           (a[1], a[1] + route['taper_length_each_end_mm']),
                           (az[0] - t / 2., az[1] + t / 2.), 'complete planar finite taper polygon superset'))
    for i, (u0, u1) in enumerate(zip(samples[:-1], samples[1:])):
        qs = [float(ep5.ep4.quintic(float(u))) for u in (u0, u1)]
        z = [a[2] + (flat - d) * q + ref * d for q in qs for d in (low, high)]
        rows.append(box_record('S_%02d' % i, x, (76. + 10. * u0 - pad, 76. + 10. * u1 + pad),
                               (min(z) - pad, max(z) + pad),
                               'bilinear (quintic-u,d) extrema over mandatory finite-edge interval'))
    bz = _range(8.2 + route['B_low_lane_z_mm'] + (ref - 1.) * d for d in (low, high))
    rows.append(box_record('bridge', x, (86., first_high + GUARD),
                           (bz[0] - t / 2., bz[1] + t / 2.), 'complete variable-length straight'))
    for i, (v0, v1) in enumerate(zip(integrals[:-1], integrals[1:])):
        length = base['U1_length_mm']
        rows.append(box_record('U1_%02d' % i, x,
                               (first_low + length * min(v0[0], v1[0]) - pad,
                                first_high + length * max(v0[0], v1[0]) + pad),
                               (bz[0] + length * min(v0[1], v1[1]) - pad,
                                bz[1] + length * max(v0[1], v1[1]) + pad),
                               'full mandatory U interval; shared-d extrema include interior flat-S critical point'))
    highz = _range(8.2 + route['B_high_lane_z_mm'] + (ref - 1.) * d for d in (low, high))
    second = 79.75 + route['PREDOCK_second_U_start_B_local_y_mm']
    rows.append(box_record('upper_reverse', x, (second, first_high + GUARD),
                           (highz[0] - t / 2., highz[1] + t / 2.), 'complete variable-length high straight'))
    for i, (v0, v1) in enumerate(zip(integrals[:-1], integrals[1:])):
        length = base['U2_length_mm']
        rows.append(box_record('U2_%02d' % i, x,
                               (second - length * max(v0[0], v1[0]) - pad,
                                second - length * min(v0[0], v1[0]) + pad),
                               (highz[0] - length * max(v0[1], v1[1]) - pad,
                                highz[1] - length * min(v0[1], v1[1]) + pad),
                               'full mandatory downward-U interval'))
    endpoint = 79.75 + route['B_anchor_local_mm'][1]
    finalz = _range(8.2 + route['B_anchor_local_mm'][2] + (ref - 1.) * d for d in (low, high))
    rows.append(box_record('B_final_core', x, (second, endpoint),
                           (finalz[0] - t / 2., finalz[1] + t / 2.), 'complete final straight core'))
    rows.append(box_record('B_taper_wings', (-ew / 2., ew / 2.),
                           (endpoint - route['taper_length_each_end_mm'], endpoint),
                           (finalz[0] - t / 2., finalz[1] + t / 2.), 'complete planar finite taper polygon superset'))
    return tuple(rows)


def fpc_grouped(low=0., high=8.2, frame='A'):
    """Compact native representation of the same proven cell union."""
    cells = fpc_cells(low, high, frame)
    result = []
    for prefix in ('S_', 'U1_', 'U2_'):
        group = [row for row in cells if row['label'].startswith(prefix)]
        result.append({'label': prefix[:-1], 'kind': 'rectangle_union_yz',
                       'width_mm': configuration()['route']['middle_width_mm'],
                       'rectangles_yz': [[row['low_mm'][1:], row['high_mm'][1:]] for row in group],
                       'bounds_mm': _bounds(group), 'cell_count': len(group)})
    result.extend(row for row in cells if not any(row['label'].startswith(p) for p in ('S_', 'U1_', 'U2_')))
    return result


def oled_state(descent):
    """Original OLED algebra, in world coordinates at s=79.75, without CAD."""
    import json
    spec = json.loads((ROOT / 'design/product_geometry.json').read_text())['oled_storage_study']
    d = float(interval(descent, descent)[0])
    front = spec['front_z_mm']
    returned = spec['B_return_z_mm'] + 8.2 - d
    radius = (returned - front) / 2.
    y = spec['B_turn_center_y_mm'] + 79.75
    length = y - spec['front_anchor_y_mm']
    tail = spec['total_material_length_mm'] - length - math.pi * radius
    if radius <= spec['thickness_mm'] / 2. or tail <= 0.:
        raise ValueError('original OLED trial does not form a valid finite strip')
    return {'d': d, 'spec': spec, 'front_z': front, 'return_z': returned,
            'radius': radius, 'turn_y': y, 'center_z': (returned + front) / 2., 'tail': tail}


@lru_cache(maxsize=128)
def oled_cages(low=0., high=8.2, frame='A'):
    low, high = map(float, interval(low, high))
    ref = frame_factor(frame)
    pre, post = oled_state(low), oled_state(high)
    spec = pre['spec']
    w, t = spec['width_mm'], spec['thickness_mm']
    front_z = _range(pre['front_z'] + ref * d for d in (low, high))
    return_z = _range(oled_state(d)['return_z'] + ref * d for d in (low, high))
    front = box_record('OLED_front', (-w / 2., w / 2.),
                        (spec['front_anchor_y_mm'], pre['turn_y']),
                        (front_z[0] - t / 2., front_z[1] + t / 2.), 'whole fixed front leg in the chosen relative frame')
    tail = box_record('OLED_planar_return', (-w / 2., w / 2.),
                       (pre['turn_y'] - post['tail'], pre['turn_y']),
                       (return_z[0] - t / 2., return_z[1] + t / 2.),
                       'whole return; monotone constant-length material endpoint plus exact Z interval')
    center_max = pre['center_z'] + ref * low
    center_min = post['center_z'] + ref * high
    outer_r = pre['radius'] + t / 2.
    inner_r = post['radius'] - t / 2.
    # Internal tangency holds for both source frames. The largest outer
    # half-disk minus the smallest inner disk encloses the complete family.
    if abs(abs(center_max - center_min) + post['radius'] - pre['radius']) > 1e-12:
        raise ValueError('nested-disk premise failed')
    turn = {'label': 'OLED_turn', 'kind': 'nested_half_disks', 'width_mm': w,
            'turn_y_mm': pre['turn_y'], 'outer_radius_mm': outer_r,
            'outer_center_z_mm': center_max, 'inner_radius_mm': inner_r,
            'inner_center_z_mm': center_min,
            'bounds_mm': [-w / 2., w / 2., pre['turn_y'], pre['turn_y'] + outer_r,
                          center_max - outer_r, center_max + outer_r],
            'method': 'original internally tangent nested half-disk construction, restricted to this d interval'}
    return (front, turn, tail)


def record_bounds(row):
    return row.get('bounds_mm') or [v for pair in zip(row['low_mm'], row['high_mm']) for v in pair]


def flex_flex_certificate():
    """Complete finite FPC versus all three OLED regions throughout SEATING."""
    fa, fb = fpc_cells(frame='A'), fpc_cells(frame='B')
    oa, ob = oled_cages(frame='A'), oled_cages(frame='B')
    full_a, full_b = _bounds(fa), _bounds(fb)
    front = record_bounds(oa[0])
    turn = record_bounds(oa[1])
    tail = record_bounds(ob[2])
    gaps = {'FPC_to_complete_front_Z_gap_mm': full_a[4] - front[5],
            'FPC_to_complete_turn_Y_gap_mm': turn[2] - full_a[3],
            'FPC_to_complete_planar_return_Z_gap_mm': tail[4] - full_b[5]}
    if min(gaps.values()) <= 0.:
        raise ValueError('full finite FPC/OLED regional separation not established')
    return {'method': 'full finite station-polygon/taper cages against all three OLED material regions',
            'gap_lower_mm': gaps, 'whole_seating_parameter_domain': True,
            'actual_native_Common_executed': False, 'formal_directed_rounding_certificate': False,
            'complete_G2_or_physical_qualification': False}


def chord_cell_contract():
    """Positive finite section-cell Jacobian bound, independent of CAD samples.

    For an edge arc of length L, tangent turn <=kappa_max*L. The bilinear
    interpolation of the actual endpoint cross-sections has signed
    Jacobian >= L*(cos(turn)-t/2*kappa_max). Exact joins prevent a cell
    straddling unrelated path pieces. The mandatory grids bound L.
    """
    c = configuration(); r = c['route']; n = ep5.pose_numbers(79.75, 0., c)
    count = r['curve_parameter_stations_each'] - 1
    max_rise = 7.65
    s_k = max_rise / (10. * math.sqrt(3.))
    s_step = math.hypot(10., max_rise * 1.875) / count + 2e-10
    rows = []
    for name, k, length in [('S', s_k, s_step),
                            ('U1', 1.5 * math.pi / n['U1_length_mm'], n['U1_length_mm'] / count + 2e-10),
                            ('U2', 1.5 * math.pi / n['U2_length_mm'], n['U2_length_mm'] / count + 2e-10)]:
        turn = k * length
        bound = math.cos(turn) - r['thickness_assumption_mm'] / 2. * k
        if turn >= math.pi / 2. or bound <= 0.:
            raise ValueError('finite polygon cell can no longer be certified nonfolding')
        rows.append({'segment': name, 'maximum_arc_step_mm': length,
                     'maximum_tangent_turn_rad': turn, 'signed_cell_Jacobian_over_arc_length_lower': bound})
    return {'mandatory_curve_intervals_each': count, 'normal_padding_mm': r['thickness_assumption_mm'] / 2. + GUARD,
            'material_station_merge_tolerance_mm': 1e-10, 'records': rows,
            'convex_coordinate_boxes_enclose_entire_linear_cell_not_only_vertices': True,
            'straight_endpoint_taper_polygons_included': True,
            'finite_polygon_not_replaced_by_an_ideal_smooth_loft': True,
            'native_evaluation_executed': False, 'formal_directed_rounding_certificate': False}


def native_cage(row):
    """Only called by the later explicitly requested native diagnostic."""
    import cadquery as cq
    import product_assembly as p
    import oled_storage as oled
    if row['kind'] == 'box':
        return p.box(row['low_mm'], row['high_mm'])
    if row['kind'] == 'rectangle_union_yz':
        rectangles = [(np.asarray(a), np.asarray(b)) for a, b in row['rectangles_yz']]
        return ep5._rectangle_union_yz(rectangles, row['width_mm'])[0]
    if row['kind'] == 'nested_half_disks':
        w = row['width_mm']
        outer = oled.half_cylinder(w, row['outer_radius_mm'], row['turn_y_mm'], row['outer_center_z_mm'])
        inner = p.single(cq.Solid.makeCylinder(row['inner_radius_mm'], w + .2,
                           cq.Vector(-w / 2. - .1, row['turn_y_mm'], row['inner_center_z_mm']), cq.Vector(1, 0, 0)))
        return p.single(outer.cut(inner).clean())
    raise ValueError('unrecognized whole-material cage')
