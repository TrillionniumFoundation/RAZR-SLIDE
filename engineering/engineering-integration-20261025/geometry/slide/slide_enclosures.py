"""Complete finite EP5/OLED SLIDE cages; arithmetic import never imports CAD.

q is the original KEY coordinate [0,12]; slide s=79.75*q/12 and descent=0.
Frame A is the unchanged STOW world frame. Frame B subtracts only (0,s,0),
so its material still uses the original STOW-world Z datum. Every interval
bound is derived from affine endpoint extrema, not sampled poses.
"""
from __future__ import annotations

from fractions import Fraction as F
from functools import lru_cache
import math
from pathlib import Path
import sys

import numpy as np

SEATING = Path(__file__).resolve().parent.parent / 'seating'
if str(SEATING) not in sys.path:
    sys.path.insert(0, str(SEATING))
import seating_domain as shared_domain
import seating_enclosures as shared

ROOT = shared.ROOT
GUARD = shared.GUARD
ep5 = shared.ep5
box_record = shared.box_record
record_bounds = shared.record_bounds
Q_MAX = F(12)
SLIDE_MAX = F('79.75')


def q_interval(q_low=0, q_high=12):
    low, high = map(shared_domain.fraction, (q_low, q_high))
    if not 0 <= low <= high <= Q_MAX:
        raise ValueError('SLIDE KEY interval must lie in [0,12]')
    return low, high


def slide_at_q(q):
    q = q_interval(q, q)[0]
    return SLIDE_MAX * q / Q_MAX


def _range(values):
    values = tuple(values)
    return min(values), max(values)


@lru_cache(maxsize=128)
def fpc_cells(q_low=0, q_high=12, frame='A'):
    """All finite-polygon core cells plus complete planar taper polygons.

    The original 49 mandatory stations split each curve into 48 intervals,
    including the U midpoint. A straight finite polygon edge lies within
    one such interval (plus <=1e-10 mm station merge slack). At fixed u,
    every SLIDE Y coordinate is affine in q and every Z coordinate is
    constant. S Y and its quintic Z are monotone; U Y is monotone on each
    half and U Z over the whole turn. Coordinate endpoint extrema plus
    the complete normal thickness bound cover every actual finite corner.
    The oriented 2-chain/winding cancellation argument from the frozen
    SEATING helper covers the whole original YZ polygon interior, then its
    full X extrusion. These are not cages for an idealized smooth loft.
    """
    low, high = q_interval(q_low, q_high)
    slides = tuple(float(slide_at_q(q)) for q in (low, high))
    reference = shared.frame_factor(frame)
    c = shared.configuration(); r = c['route']
    states = [ep5.pose_numbers(s, 0., c) for s in slides]
    count = r['curve_parameter_stations_each'] - 1
    t = r['thickness_assumption_mm']; pad = t / 2. + GUARD
    width = r['middle_width_mm']; x = (-width / 2., width / 2.)
    endpoint_x = (-r['endpoint_width_mm'] / 2., r['endpoint_width_mm'] / 2.)
    a = r['A_anchor_local_mm']; rise = states[0]['S_rise_mm']
    sy0, sy1 = r['S_world_Y_interval_mm']
    shift_min, shift_max = _range(-reference * s for s in slides)
    first_min, first_max = _range(n['U1_start_world_Y_mm'] - reference * s for n, s in zip(states, slides))
    second_min, second_max = _range(n['U2_start_world_Y_mm'] - reference * s for n, s in zip(states, slides))
    endpoint_min, endpoint_max = _range(n['B_endpoint_world_mm'][1] - reference * s for n, s in zip(states, slides))
    rows = [box_record('A_straight_core', x, (a[1] + shift_min, sy0 + shift_max),
                       (a[2] - t / 2., a[2] + t / 2.), 'whole original straight core; affine q extrema'),
            box_record('A_taper_wings', endpoint_x,
                       (a[1] + shift_min, a[1] + r['taper_length_each_end_mm'] + shift_max),
                       (a[2] - t / 2., a[2] + t / 2.), 'whole finite planar taper polygon; affine q extrema')]
    stations = np.linspace(0., 1., count + 1)
    integrals = np.asarray([ep5.ep4.u_integral(float(u), r['Gauss_Legendre_order']) for u in stations])
    for i, (u0, u1) in enumerate(zip(stations[:-1], stations[1:])):
        z = [a[2] + rise * float(ep5.ep4.quintic(float(u))) for u in (u0, u1)]
        rows.append(box_record('S_%02d' % i, x,
                    (sy0 + (sy1 - sy0) * u0 + shift_min - pad,
                     sy0 + (sy1 - sy0) * u1 + shift_max + pad),
                    (min(z) - pad, max(z) + pad), 'whole mandatory finite S cell; affine q and monotone u extrema'))
    lowz = 8.2 + r['B_low_lane_z_mm']; highz = 8.2 + r['B_high_lane_z_mm']
    rows.append(box_record('bridge', x, (sy1 + shift_min, first_max + GUARD),
                           (lowz - t / 2., lowz + t / 2.), 'whole variable-length straight; affine q endpoints'))
    for i, (v0, v1) in enumerate(zip(integrals[:-1], integrals[1:])):
        length = states[0]['U1_length_mm']
        rows.append(box_record('U1_%02d' % i, x,
                    (first_min + length * min(v0[0], v1[0]) - pad,
                     first_max + length * max(v0[0], v1[0]) + pad),
                    (lowz + length * min(v0[1], v1[1]) - pad,
                     lowz + length * max(v0[1], v1[1]) + pad),
                    'whole finite U1 cell; monotone half-U extrema and affine q endpoints'))
    rows.append(box_record('upper_reverse', x, (second_min, first_max + GUARD),
                           (highz - t / 2., highz + t / 2.), 'whole reverse straight; affine q endpoints'))
    for i, (v0, v1) in enumerate(zip(integrals[:-1], integrals[1:])):
        length = states[0]['U2_length_mm']
        rows.append(box_record('U2_%02d' % i, x,
                    (second_min - length * max(v0[0], v1[0]) - pad,
                     second_max - length * min(v0[0], v1[0]) + pad),
                    (highz - length * max(v0[1], v1[1]) - pad,
                     highz - length * min(v0[1], v1[1]) + pad),
                    'whole finite U2 cell; monotone half-U extrema and affine q endpoints'))
    finalz = 8.2 + r['B_anchor_local_mm'][2]
    rows.append(box_record('B_final_core', x, (second_min, endpoint_max),
                           (finalz - t / 2., finalz + t / 2.), 'whole forward final core; affine q endpoints'))
    rows.append(box_record('B_taper_wings', endpoint_x,
                           (endpoint_min - r['taper_length_each_end_mm'], endpoint_max),
                           (finalz - t / 2., finalz + t / 2.), 'whole finite B taper; affine q endpoints'))
    return tuple(rows)


def fpc_grouped(q_low=0, q_high=12, frame='A'):
    cells = fpc_cells(q_low, q_high, frame)
    result = []
    for prefix in ('S_', 'U1_', 'U2_'):
        group = [row for row in cells if row['label'].startswith(prefix)]
        result.append({'label': prefix[:-1], 'kind': 'rectangle_union_yz',
                       'width_mm': shared.configuration()['route']['middle_width_mm'],
                       'rectangles_yz': [[row['low_mm'][1:], row['high_mm'][1:]] for row in group],
                       'bounds_mm': shared._bounds(group), 'cell_count': len(group)})
    result.extend(row for row in cells if not any(row['label'].startswith(p) for p in ('S_', 'U1_', 'U2_')))
    return result


def oled_state(q):
    s = float(slide_at_q(q))
    spec = shared.oled_state(0)['spec']
    front = spec['front_z_mm']; returned = spec['B_return_z_mm'] + 8.2
    radius = (returned - front) / 2.
    turn = spec['B_turn_center_y_mm'] + s
    tail = spec['total_material_length_mm'] - (turn - spec['front_anchor_y_mm']) - math.pi * radius
    if radius <= spec['thickness_mm'] / 2. or tail <= 0.:
        raise ValueError('original finite OLED strip is invalid in the SLIDE domain')
    return {'slide_mm': s, 'turn_y_mm': turn, 'front_z_mm': front, 'return_z_mm': returned,
            'radius_mm': radius, 'center_z_mm': (front + returned) / 2., 'tail_length_mm': tail, 'spec': spec}


@lru_cache(maxsize=128)
def oled_cages(q_low=0, q_high=12, frame='A'):
    low, high = q_interval(q_low, q_high)
    reference = shared.frame_factor(frame)
    start, end = oled_state(low), oled_state(high)
    spec = start['spec']; w, t = spec['width_mm'], spec['thickness_mm']
    s0, s1 = start['slide_mm'], end['slide_mm']
    center0 = start['turn_y_mm'] - reference * s0
    center1 = end['turn_y_mm'] - reference * s1
    front = box_record('OLED_front', (-w / 2., w / 2.),
              (spec['front_anchor_y_mm'] - reference * s1, center1),
              (start['front_z_mm'] - t / 2., start['front_z_mm'] + t / 2.),
              'whole finite front leg; exact monotone union in the selected frame')
    returned = box_record('OLED_planar_return', (-w / 2., w / 2.),
                  (center0 - start['tail_length_mm'], center1),
                  (start['return_z_mm'] - t / 2., start['return_z_mm'] + t / 2.),
                  'whole fixed-material-length return; exact connected interval union')
    outer, inner = start['radius_mm'] + t / 2., start['radius_mm'] - t / 2.
    turn = {'label': 'OLED_turn', 'kind': 'translated_half_annulus', 'width_mm': w,
            'center_Y_interval_mm': [center0, center1], 'center_z_mm': start['center_z_mm'],
            'outer_radius_mm': outer, 'inner_radius_mm': inner,
            'bounds_mm': [-w / 2., w / 2., center0, center1 + outer,
                          start['center_z_mm'] - outer, start['center_z_mm'] + outer],
            'method': 'original half-annulus translation union: rectangle plus last outer half-disk minus first inner disk',
            'whole_finite_annulus_not_centerline': True}
    return front, turn, returned


def native_cage(row):
    """Native construction is lazy and must run only in a coordinated CAD slot."""
    if row['kind'] != 'translated_half_annulus':
        return shared.native_cage(row)
    import cadquery as cq
    import product_assembly as p
    import oled_storage as oled
    lo, hi = row['center_Y_interval_mm']
    w, z, outer, inner = (row[k] for k in ('width_mm', 'center_z_mm', 'outer_radius_mm', 'inner_radius_mm'))
    body = oled.half_cylinder(w, outer, hi, z)
    if hi > lo:
        rectangle = p.box((-w / 2., lo, z - outer), (w / 2., hi, z + outer))
        body = p.single(body.fuse(rectangle).clean())
    exclusion = p.single(cq.Solid.makeCylinder(inner, w + .2,
                         cq.Vector(-w / 2. - .1, lo, z), cq.Vector(1., 0., 0.)))
    return p.single(body.cut(exclusion).clean())


def material_contract():
    return {'schema': 'razr-slide-finite-material-cage-contract-v1',
            'KEY_q_interval_mm': [0., 12.], 'slide_mm': [0., 79.75], 'descent_mm': 0.,
            'q_to_slide_exact': '319*q/48', 'A_frame': 'unchanged STOW world',
            'B_frame': 'STOW world with (0,s,0) subtracted; original Z datum retained',
            'FPC_mandatory_curve_intervals_each': 48, 'FPC_cell_count': 150,
            'FPC_native_group_count': 9, 'OLED_native_region_count': 3,
            'finite_polygon_2chain_coverage_argument_retained': True,
            'complete_straight_endpoint_taper_polygons_included': True,
            'affine_q_extrema_use_interval_endpoints': True,
            'native_checks_executed': False, 'all_external_pairs_checked': False,
            'continuous_native_self_validity_not_claimed': True,
            'formal_directed_rounding_certificate': False,
            'complete_G2_qualification': False, 'candidate_go': False,
            'fixture_fabrication_go': False, 'manufacturing_go': False}
