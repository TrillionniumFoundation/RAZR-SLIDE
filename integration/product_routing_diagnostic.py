"""Diagnose whole-endpoint self-interference and bounded OLED/FPC requirements.

The original product_fpc route and its rejected evidence are not edited.  EP2
is a separately named *mechanical research arrangement* of the same four PCB
outlines, their mated connectors, all clamp hardware, stiffened ends, and a
finite static wiring reservation.  A clear reservation is not routed copper.

The default report is pure arithmetic.  --native additionally executes actual
CadQuery Boolean checks, using every participant of the current shared scene.
It stops after the three decisive poses; it never calls that a full-stroke pass.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'design/product_routing_followup.json'
GEOMETRY = ROOT / 'design/product_geometry.json'
INTERFACES = ROOT / 'design/product_interfaces.json'
TOL = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, *, nonnegative=False):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError('finite real number required')
    if nonnegative and value < 0:
        raise ValueError('nonnegative value required')
    return float(value)


def load_config(path=CONFIG):
    c = json.loads(Path(path).read_text())
    if c.get('schema') != 'razr-product-routing-followup-v1':
        raise ValueError('unrecognized routing diagnostic')
    expected = {'equal_finished_cabins': True, 'single_flexible_display': True,
                'independent_rear_display': False, 'OLED_storage_is_planar_in_B': True,
                'slide_mm': 79.75, 'normal_seating_mm': 8.2}
    if c['constraints'] != expected:
        raise ValueError('product constraints changed')
    for key in ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go',
                'supplier_dynamic_qualified', 'physical_hardware_test_executed'):
        if c[key] is not False:
            raise ValueError('diagnostic cannot issue a physical release')
    for request in c['OLED_retained_flat_tail_requests_mm']:
        number(request, nonnegative=True)
    ep = c['endpoint_candidate']
    # EP2 is a fixed identified geometry study, not a configurable builder.
    # JSON-only edits must never relabel unchanged native solids as resized.
    fixed_ep2 = {
        'id': 'EP2_separate_board_pair_and_clamp',
        'board_pair_unchanged_native_artwork': True,
        'boards_per_end': 2, 'boards_across_both_ends': 4,
        'board_x_mm': [-6.0, 6.0], 'board_y_mm': [-14.0, -2.0],
        'DP_z_mm': [.4, 1.2], 'DS_z_mm': [1.8, 2.6],
        'clamp_y_mm': [7., 21.], 'clamp_fastener_y_mm': [15., 19.],
        'carrier_width_mm': 14.6, 'carrier_exceeds_existing_12mm_B_allocation_by_mm': 2.6,
        'coupon_total_length_mm': 164., 'coupon_free_length_mm': 140.,
        'coupon_stiffened_end_length_mm': 12., 'nominal_hardware_only': True,
        'actual_wire_diameter_or_stackup_selected': False,
        'actual_COF_or_OEM_connector_assigned': False}
    if any(ep.get(key) != expected for key, expected in fixed_ep2.items()):
        raise ValueError('EP2 declaration differs from the fixed native geometry or physical scope')
    if ep['individual_static_conductors_routed'] is not False:
        raise ValueError('reservation is not a set of routed conductors')
    return c


def g2_coefficient(intervals=4096):
    """Composite Simpson with analytic fourth-derivative truncation bound.

    A separately stated 1e-10 arithmetic allowance is deliberately much wider
    than the observed floating-point integration differences. It is not a
    formal interval-arithmetic certification of Python's math.sin.
    """
    if type(intervals) is not int or intervals < 64 or intervals % 2:
        raise ValueError('even quadrature subdivision count of at least 64 required')
    f = lambda u: math.sin(math.pi * (3*u*u-2*u*u*u))
    terms = [f(i/intervals) * (4 if i % 2 else 2)
             for i in range(1, intervals)]
    integral = (f(0.) + f(1.) + math.fsum(terms)) / (3*intervals)
    d1, d2, d3 = 1.5*math.pi, 6*math.pi, 12*math.pi
    fourth_bound = d1**4 + 3*d2**2 + 4*d1*d3 + 6*d1*d1*d2
    truncation_bound = fourth_bound / (180*intervals**4)
    allowance = 1e-10
    lo, hi = integral-truncation_bound-allowance, integral+truncation_bound+allowance
    return {'integral_sin_theta_approx': integral,
            'R_per_delta_Z_approx': 1/(1.5*math.pi*integral),
            'R_per_delta_Z_conservative_numeric_interval': [1/(1.5*math.pi*hi), 1/(1.5*math.pi*lo)],
            'Simpson_intervals': intervals,
            'analytic_quadrature_truncation_bound': truncation_bound,
            'additional_arithmetic_allowance': allowance,
            'formal_directed_rounding_certificate': False,
            'theta': 'pi*(3*u^2-2*u^3)',
            'derivation': 'bend_length=delta_Z/integral(sin(theta)); max curvature=1.5*pi/bend_length'}


def oled_retention(spec, request_mm, *, height_mm=94.25, clearance_mm=.2):
    """Exact affine/semicircle budget for this fixed B-local turn family.

    A terminal reserve is flat OLED material beyond the turn. It never counts
    a COF or attached FPC as extra OLED length. COF and actual inactive border
    remain separately unknown. The zero-reserve lower bound is strict.
    """
    reserve = number(request_mm, nonnegative=True)
    c, ymin, a = (number(spec[k]) for k in
                  ('B_turn_center_y_mm', 'B_storage_y_min_mm', 'front_anchor_y_mm'))
    radius = (number(spec['B_return_z_mm']) + 8.2 - number(spec['front_z_mm'])) / 2
    length = number(spec['total_material_length_mm'])
    slide = 79.75
    front_stow = c-a
    arc = math.pi*radius
    lo = front_stow+slide+arc+reserve
    hi = front_stow+arc+c-ymin
    pre_tail = length-(front_stow+slide+arc)
    max_turn_c = height_mm-radius-number(spec['thickness_mm'])/2-clearance_mm
    turn_forward_allowance = max_turn_c-c
    cut_without_turn_change = max(0., reserve-(c-ymin-slide))
    return {'flat_tail_request_mm': reserve,
            'request_is_not_measured_COF_or_clamp': True,
            'whole_motion_material_interval_mm': [lo, hi],
            'lower_limit_is_strict_if_zero_reserve': reserve == 0.,
            'nonempty_interval': lo < hi if reserve == 0. else lo <= hi,
            'interval_width_mm': hi-lo,
            'current_material_length_mm': length,
            'current_PREDOCK_flat_tail_mm': pre_tail,
            'current_material_meets_flat_tail_request': pre_tail > 0. if reserve == 0. else pre_tail >= reserve,
            'minimum_added_material_to_current_trial_mm': max(0., lo-length),
            'minimum_storage_extension_toward_B_foot_if_turn_unchanged_mm': cut_without_turn_change,
            'maximum_B_storage_y_min_if_turn_unchanged_mm': c-slide-reserve,
            'optimistic_maximum_turn_center_y_from_outer_head_mm': max_turn_c,
            'optimistic_turn_forward_allowance_mm': turn_forward_allowance,
            'minimum_storage_extension_even_with_optimistic_turn_shift_mm':
                max(0., cut_without_turn_change-max(0., turn_forward_allowance)),
            'head_bound_is_not_a_free_cavity_or_native_clearance_proof': True,
            'current_COF_envelope': None,
            'actual_inactive_edge_available_for_clamp_mm': None,
            'physical_retention_or_traction_qualified': False,
            'derivation': 'L >= (c-a+slide)+pi*r+reserve; L <= (c-a)+pi*r+(c-y_min)'}


def endpoint_stack_bounds(variant='legacy', *, flipped=False):
    """Bounds derived from declared full endpoint solids, checked natively later."""
    if variant == 'legacy':
        lo, hi = -4.25, 1.45
        width, ybounds = {'A': 20., 'B': 12.}, {'A': [-12.5, 0.], 'B': [0., 21.]}
    elif variant == 'EP2':
        lo, hi = -1.65, 3.0
        width, ybounds = {'A': 14.6, 'B': 14.6}, {'A': [-21., 14.], 'B': [-14., 21.]}
    else:
        raise ValueError('unknown endpoint variant')
    if flipped:
        lo, hi = -hi, -lo
    return {'z_relative_mm': [lo, hi], 'height_mm': hi-lo,
            'width_by_end_mm': width, 'y_bounds_by_end_mm': ybounds,
            'entire_endpoint_rigidly_flipped': flipped}


def endpoint_anchor_interval(z_floor, z_ceiling, variant='legacy', *, flipped=False, gap=0.):
    floor, ceiling = number(z_floor), number(z_ceiling)
    gap = number(gap, nonnegative=True)
    if ceiling <= floor:
        raise ValueError('positive cavity height required')
    zlo, zhi = endpoint_stack_bounds(variant, flipped=flipped)['z_relative_mm']
    interval = [floor+gap-zlo, ceiling-gap-zhi]
    return {'anchor_z_interval_mm': interval,
            'necessary_envelope_fit_possible': interval[0] <= interval[1],
            'height_shortfall_mm': max(0., interval[0]-interval[1]),
            'cavity_is_not_proved_empty': True,
            'full_endpoint_z_span_mm': zhi-zlo,
            'normal_clearance_each_face_mm': gap}


def arithmetic_report(config=None):
    config = config or load_config()
    geom = json.loads(GEOMETRY.read_text())
    interface = json.loads(INTERFACES.read_text())
    coeff = g2_coefficient()
    route = interface['route_study']
    delta = route['B_anchor_local_mm'][2]-route['A_anchor_local_mm'][2]
    legacy = []
    ep2 = []
    floor, ceiling, guide = (config[k] for k in ('reference_interior_floor_z_mm',
                                                'reference_interior_ceiling_z_mm',
                                                'reference_B_return_guide_bottom_z_mm'))
    for variant, table in [('legacy', legacy), ('EP2', ep2)]:
        for gap in (0., .2):
            for flipped in (False, True):
                table.append({'variant': variant, 'flipped': flipped, 'gap_mm': gap,
                              'under_B_OLED_return_guide': endpoint_anchor_interval(floor, guide, variant, flipped=flipped, gap=gap),
                              'optimistic_whole_internal_thickness': endpoint_anchor_interval(floor, ceiling, variant, flipped=flipped, gap=gap)})
    return {'schema': 'razr-product-routing-arithmetic-v1',
            'inputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), CONFIG, GEOMETRY, INTERFACES)},
            'g2_turn': coeff,
            'legacy_endpoint_lanes': {'STOW_delta_Z_mm': delta+8.2, 'OPEN_delta_Z_mm': delta,
                 'STOW_minimum_radius_approx_mm': (delta+8.2)*coeff['R_per_delta_Z_approx'],
                 'OPEN_minimum_radius_approx_mm': delta*coeff['R_per_delta_Z_approx'],
                 'radius_depends_on_Z_lane_separation_not_total_material_length': True},
            'OLED_retention': [oled_retention(geom['oled_storage_study'], q,
                 height_mm=geom['dimensions']['height_mm'], clearance_mm=config['outer_head_clearance_request_mm'])
                 for q in config['OLED_retained_flat_tail_requests_mm']],
            'complete_endpoint_stack_necessary_conditions': {'legacy': legacy, 'EP2': ep2},
            'legacy_internal_interference_predictions': [
                {'end': 'A', 'a': 'lower_jaw', 'b': 'static_26wire_transfer_reservation',
                 'positive_common_mm3': 10.6*5.*1.35, 'native_executed_here': False},
                {'end': 'B', 'a': 'lower_jaw', 'b': 'static_26wire_transfer_reservation',
                 'positive_common_mm3': 10.6*11.5*1.35, 'native_executed_here': False}],
            'candidate_definition': config['endpoint_candidate'],
            'native_checks_executed': False,
            'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False,
            'full_cycle_internal_route_accepted': False,
            'selected_OLED_COF_and_dynamic_stack': False}


def ep2_local_parts(interface_config, end):
    """New complete endpoint: paired PCBs before tail, clamp after solder window.

    Existing board copper, J1 mating gap, four board holes and all hardware
    remain explicit. The static transfer is a *space reservation*, cut around
    J1 and all four screw shafts. It reaches the DS front-face probe plane and
    the exposed end-pad plane without passing through either clamp jaw.
    """
    import cadquery as cq
    import product_assembly as p
    if end not in ('A', 'B'):
        raise ValueError('unknown endpoint')
    c = interface_config['coupon']
    w, length, tf, ts = (c[k] for k in ('width_mm', 'end_stiffener_length_mm',
                                       'finished_flex_thickness_assumption_mm', 'stiffener_thickness_mm'))
    if (w, length, tf, ts) != (12., 12., .1, .2):
        raise ValueError('EP2 is bound to the current 12 mm nominal coupon end')
    if (c['length_mm'], c['free_length_mm']) != (164., 140.):
        raise ValueError('EP2 is bound to one 164 mm coupon with 140 mm free material')
    box = lambda x0,x1,y0,y1,z0,z1: p.box((x0,y0,z0),(x1,y1,z1))
    cyl = lambda x,y,z,h,r: cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
    parts = {'tail': box(-6,6,0,12,-.05,.05),
             'stiffener': box(-6,6,0,12,-.25,-.05)}
    upper = box(-6,6,7,21,.05,.85)
    lower = box(-6,6,7,21,-1.65,-.25)
    # The paired PCBs are carried around the *sides* of the free 12mm ribbon.
    # A central post from below to above that ribbon would be a new collision.
    # This real connected carrier costs 2.6mm extra width; the former 12mm B
    # allocation therefore cannot be reused as an asserted fit certificate.
    lower = lower.fuse(box(-7.3,7.3,-14,21,-1.65,-1.15))
    for sign in (-1,1):
        xs = sorted([sign*6.15, sign*7.3])
        lower = lower.fuse(box(*xs,-14,-2,-1.2,.4))
        xs = sorted([sign*4.1, sign*7.3])
        lower = lower.fuse(box(*xs,-14,-2,.2,.4))
    for i,y in enumerate((15.,19.),1):
        hole = cyl(0,y,-2,4,1.1)
        upper, lower = upper.cut(hole), lower.cut(hole)
        parts[f'M2_clamp_screw_{i}'] = cyl(0,y,-1.6,2.45,1.)
        parts[f'M2_clamp_head_{i}'] = cyl(0,y,.85,.6,1.75)
    dp = box(-6,6,-14,-2,.4,1.2)
    ds = box(-6,6,-14,-2,1.8,2.6)
    holes = [(-5,-12.7),(5,-12.7),(-5,-3.3),(5,-3.3)]
    for i,(x,y) in enumerate(holes,1):
        hole = cyl(x,y,0,3,.7)
        dp, ds = dp.cut(hole), ds.cut(hole)
        lower = lower.cut(cyl(x,y,.1,.4,.55))
        parts[f'M1_board_shaft_{i}'] = cyl(x,y,.2,2.4,.5)
        parts[f'M1_board_head_{i}'] = cyl(x,y,2.6,.4,.9)
    parts['upper_jaw'], parts['lower_jaw'] = upper.clean(), lower.clean()
    parts['mini_DP_PCB'], parts['mini_DS_PCB'] = dp, ds
    parts['mated_BM28_reservation'] = box(-3.5,3.5,-8.95,-7.05,1.2,1.8)
    transfer = box(-5.3,5.3,-13.95,-1.3,1.25,1.8)
    transfer = transfer.cut(box(-3.7,3.7,-9.15,-6.85,1.2,1.85))
    for x,y in holes:
        transfer = transfer.cut(cyl(x,y,1.2,.7,.75))
    transfer = transfer.fuse(box(-5.3,5.3,-1.5,-1.25,.05,1.8))
    transfer = transfer.fuse(box(-5.3,5.3,-1.4,5.5,.05,.25)).clean()
    parts['static_26wire_transfer_reservation'] = transfer
    # Same handed endpoint convention as product_fpc. The +X width and
    # endpoint tangent produce a proper rigid world frame in place_endpoint.
    # A flips Y, B flips Z; reflection here mirrors symmetric source solids.
    if end == 'A':
        parts = {name: body.mirror('XZ') for name,body in parts.items()}
    else:
        parts = {name: body.mirror('XY') for name,body in parts.items()}
    if len(parts) != 20:
        raise ValueError('incomplete endpoint participants')
    for name,body in parts.items():
        if len(body.Solids()) != 1 or not body.isValid() or body.Volume() <= 0:
            raise ValueError('invalid positive endpoint solid: '+name)
    return parts


def native_pair_checks(parts_a, parts_b=None):
    """All pairs; AABB separation is only a safe shortcut for nonintersection."""
    import product_assembly as p
    pairs = (itertools.combinations(sorted(parts_a.items()),2) if parts_b is None
             else itertools.product(sorted(parts_a.items()), sorted(parts_b.items())))
    rows = []
    for (name_a,a),(name_b,b) in pairs:
        try:
            r = p.strict_common(a,b)
            rows.append({'a': name_a, 'b': name_b, **r,
                         'positive_material_common': r['common_mm3'] > TOL})
        except Exception as exc:
            rows.append({'a': name_a, 'b': name_b, 'evaluation_failed': True,
                         'error_type': type(exc).__name__, 'error': str(exc),
                         'positive_material_common': False})
    failures = [r for r in rows if r.get('evaluation_failed') or r['positive_material_common']]
    return {'pair_count': len(rows), 'pairs': rows, 'failures': failures,
            'all_pairs_evaluated': True, 'no_positive_common_or_evaluation_error': not failures,
            'nonintersection_is_not_positive_clearance_or_assembly_retention': True}


def native_report(output, interface_config=None):
    import cadquery as cq
    import product_assembly as p
    import product_fpc as f
    from product_interfaces import load_config as load_interfaces
    cfg = interface_config or load_interfaces()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('new native output directory required')
    output.mkdir(parents=True)
    sources = [Path(__file__), CONFIG, GEOMETRY, INTERFACES,
               ROOT/'integration/product_fpc.py', ROOT/'integration/product_assembly.py',
               ROOT/'integration/oled_storage.py', ROOT/'integration/product_motion.py']
    before = {str(path.relative_to(ROOT)):sha(path) for path in sources}
    variants = {'legacy_retained_negative_endpoint': {}, 'EP2_separate_board_pair_and_clamp': {}}
    local = {}
    for name,builder in [('legacy_retained_negative_endpoint',f.local_endpoint_parts),
                         ('EP2_separate_board_pair_and_clamp',ep2_local_parts)]:
        local[name] = {end:builder(cfg,end) for end in ('A','B')}
        for end,parts in local[name].items():
            check = native_pair_checks(parts)
            compound = cq.Compound.makeCompound(list(parts.values()))
            info = {'parts':len(parts), 'PCB_parts':[k for k in parts if k.endswith('_PCB')],
                    'bounds_mm':p.bounds(compound), 'self_checks':check}
            if name.startswith('EP2'):
                step = output/(name+'_'+end+'.step')
                cq.exporters.export(compound,str(step))
                reopened = cq.importers.importStep(str(step)).val()
                if len(reopened.Solids()) != len(parts) or any(not s.isValid() or s.Volume()<=0 for s in reopened.Solids()):
                    raise ValueError('EP2 full endpoint export failed readback')
                info['STEP'] = {'path':step.name,'sha256':sha(step),'readback_valid_positive_solids':len(reopened.Solids()),
                                'reader_is_generator_process_same_CAD_kernel':True}
            variants[name][end] = info
            print(json.dumps({'variant':name,'end':end,'self_pair_count':check['pair_count'],
                              'self_rejected_pairs':len(check['failures'])}),flush=True)
    # Negative control is the actual intersecting legacy complete endpoint.
    for end,expected in [('A',71.55),('B',164.565)]:
        row = next(r for r in variants['legacy_retained_negative_endpoint'][end]['self_checks']['pairs']
                   if {r['a'],r['b']} == {'lower_jaw','static_26wire_transfer_reservation'})
        if not row['positive_material_common'] or abs(row['common_mm3']-expected)>1e-6:
            raise ValueError('legacy exact internal negative control differs from derived volume')
    pose_rows = []
    for label,slide,descent in [('STOW',0.,0.),('PREDOCK',79.75,0.),('OPEN',79.75,8.2)]:
        sections,material_metadata = f.route_pose(cfg,slide,descent)
        material,finite_metadata = f.finite_material_solid(sections['corners'])
        # OPEN includes all physical accessories: 106 total participants.
        manual = {'slide':slide,'descent':descent,'left_tab':3. if slide else 0.,
                  'right_tab':3. if slide else 0.,'hold_screws':2 if label=='OPEN' else 0,
                  'support_insert':label=='OPEN'}
        scene,scene_meta = f.current_shared_scene(slide,descent,manual)
        for variant,ends in local.items():
            placed = {end:f.place_endpoint(ends[end],sections,end) for end in ('A','B')}
            checks = {'A_to_B_endpoints':native_pair_checks(placed['A'],placed['B']),
                      'material_to_A_endpoint':native_pair_checks({'finite_material':material},placed['A']),
                      'material_to_B_endpoint':native_pair_checks({'finite_material':material},placed['B'])}
            # All complete endpoint part sets are retained. For the external
            # scene one actual decisive native witness per complete group is
            # sufficient to reject; unchecked further collisions stay unknown.
            external = {'material':f.shape_witness(material,scene)}
            for end in ('A','B'):
                body = cq.Compound.makeCompound(list(placed[end].values()))
                external[end+'_complete_endpoint'] = f.shape_witness(body,scene)
            row = {'pose':label,'variant':variant,'scene_participants':len(scene),
                   'manual_state':manual,'scene_metadata':scene_meta,
                   'material_metadata':material_metadata,'finite_material_metadata':finite_metadata,
                   'endpoints_PCB_count':4,
                   'internal_checks':checks,'external_checks':external,
                   'all_complete_checks_clear_at_this_pose':
                        all(v['no_positive_common_or_evaluation_error'] for v in checks.values())
                        and all(v['sampled_pose_clear'] for v in external.values())
                        and all(variants[variant][e]['self_checks']['no_positive_common_or_evaluation_error'] for e in ('A','B'))}
            pose_rows.append(row)
            print(json.dumps({'pose':label,'variant':variant,'participants':len(scene),
                              'clear':row['all_complete_checks_clear_at_this_pose']}),flush=True)
    if any(sha(ROOT/name)!=digest for name,digest in before.items()):
        raise ValueError('native diagnostic source changed during execution')
    result = {'schema':'razr-complete-endpoint-routing-diagnostic-native-v1',
              'input_sha256':before,'source_bytes_unchanged':True,
              'variants':variants,'key_pose_checks':pose_rows,
              'native_checks_executed':True,'original_evidence_overwritten':False,
              'pose_scope':'three decisive assembly states with all current obstacles; no full-motion clearance claim',
              'fixed_free_material_length_mm':140.,'complete_material_including_stiffened_ends_mm':164.,
              'EP2_changes_original_G2_radius':False,
              'individual_static_conductors_routed':False,
              'supplier_dynamic_qualified':False,
              'full_cycle_internal_route_accepted':False,
              'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (output/'native-routing-diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error('use a new output directory')
    result = arithmetic_report()
    out.mkdir(parents=True)
    (out/'routing-arithmetic.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.native:
        actual = native_report(out/'native')
        print(json.dumps({'native_diagnostic':True,'key_pose_records':len(actual['key_pose_checks']),
                          'full_cycle_internal_route_accepted':False,'candidate_go':False}))
    else:
        print(json.dumps({'arithmetic_diagnostic':True,'native_executed':False,'candidate_go':False}))
