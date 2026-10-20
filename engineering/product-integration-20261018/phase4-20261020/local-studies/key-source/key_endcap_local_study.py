"""Independent, bounded KEY closed-endcap study; no shared source mutation.

Arithmetic mode is CAD-free. Native mode reads SHA-pinned project sources and
the actual mounted KEY parent, reconstructs the old factory, and studies one
new closed-slot outline while preserving the original arm/tab/KEY material.
It does not install the candidate into the phone or grant motion/manufacture.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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

TOL = 1e-7
CAM_SHA = '4a3bf1d2b86d31fa8e3d60d3412e15548bf42287ed95d756798f3d88c6c4e631'
PINS = {
    'integration/cam_coupling.py': CAM_SHA,
    'integration/product_assembly.py': '695073e313dae45edbb7cf8c305d31c167b4e24e1731bf8be8f1a91a77dbd77b',
    'integration/straight_envelope.py': '5fe5fa2238572123b292a940da9b2e8ec68734ce078a5cdf1c8e84c1e31047bf',
    'integration/verify_cam_coupling.py': '42c61f8a75cc8064b1038c02802cc60461c2e24cc281630d58f749b14f11b133',
    'integration/verify_endpoint_joint_pawl.py': 'cc26e35815229133a3d3f786be175678a6fc03970d0e96af7d3687d65b9d979c',
    'integration/product_routing_ep4.py': 'f8286416e8d4f835b5a280f3c76e7dd69aaebda25ac2217f40f33e19e92251b8'}
PARAMETERS = {
    'old_C_mm': [6.5, 78.25], 'C_mm': [7.15, 77.60], 'D_mm': [20., 64.75],
    'near_outer_radius_mm': .95, 'distal_outer_radius_mm': 1.1,
    'transition_length_mm': 1., 'inner_radius_mm': .425, 'neck_radius_mm': .4,
    'flange_radius_mm': .65, 'slot_Z_mm': [1.2, 1.6],
    'lower_flange_Z_mm': [1., 1.2], 'upper_flange_Z_mm': [1.6, 1.8],
    'slide_mm': 79.75, 'nominal_KEY_stroke_mm': 12.,
    'crosshead_origin_X_mm': 7.25, 'follower_Y_mm': 77.5,
    'flank_overtravel_normal_mm': .01, 'axial_overtravel_mm': .01,
    'unchanged_flex_width_mm': 12., 'requested_nominal_side_gap_mm': .2}
RELEASE = {'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False,
    'whole_scene_clearance_accepted': False, 'full_phone_motion_accepted': False,
    'actual_material_or_process_qualified': False, 'physical_prototype_executed': False,
    'current_PAWL_interlock_and_relocking_verified': False}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def dot(a, b): return sum(x*y for x, y in zip(a, b))
def add(a, b): return tuple(x+y for x, y in zip(a, b))
def scale(a, k): return tuple(x*k for x in a)
def sub(a, b): return tuple(x-y for x, y in zip(a, b))


def geometry_parameters():
    c, d = tuple(PARAMETERS['C_mm']), tuple(PARAMETERS['D_mm'])
    length = math.dist(c, d); tangent = scale(sub(d, c), 1./length)
    normal = (-tangent[1], tangent[0]); e = add(c, scale(tangent, PARAMETERS['transition_length_mm']))
    alpha = (PARAMETERS['distal_outer_radius_mm']-PARAMETERS['near_outer_radius_mm'])/PARAMETERS['transition_length_mm']
    if not 0. < alpha < 1.: raise ValueError('the declared two-disc tangent hull is invalid')
    normals = [add(scale(tangent, -alpha), scale(normal, sign*math.sqrt(1.-alpha*alpha))) for sign in (1., -1.)]
    first = [add(c, scale(n, PARAMETERS['near_outer_radius_mm'])) for n in normals]
    second = [add(e, scale(n, PARAMETERS['distal_outer_radius_mm'])) for n in normals]
    return {'C': c, 'D': d, 'E': e, 'tangent': tangent, 'normal': normal,
        'slot_centerline_length_mm': length, 'radius_slope': alpha,
        'external_tangent_normals': normals, 'C_tangent_points': first, 'E_tangent_points': second,
        'tangent_quadrilateral': [first[0], first[1], second[1], second[0]]}


def clearance_cases():
    gap = PARAMETERS['inner_radius_mm']-PARAMETERS['neck_radius_mm']
    k = PARAMETERS['nominal_KEY_stroke_mm']/PARAMETERS['slide_mm']
    half_x = gap*math.hypot(1., k)
    result = []
    for cam_flank, output_flank in itertools.product((-1, 1), repeat=2):
        dx = cam_flank*half_x
        # Signed output-flank coordinate n=(dx-dq)/sqrt(2).
        normal_offset = output_flank*gap
        dq = dx-normal_offset*math.sqrt(2.)
        result.append({'cam_flank': cam_flank, 'output_flank': output_flank,
            'dx_mm': dx, 'dq_mm': dq, 'slot_normal_offset_mm': normal_offset})
    return result


def pin_center(q, case):
    if not 0. <= q <= 12.: raise ValueError('nominal KEY q must be in [0,12]')
    return (7.25+q+case['dx_mm'], 77.5-q-case['dq_mm'])


def arithmetic_report():
    g = geometry_parameters(); cases = []
    for case in clearance_cases():
        values = []
        for q in (0., 12.):
            center = pin_center(q, case); delta = sub(center, g['C'])
            values.append({'q_mm': q, 'center_relative_to_KEY_mm': center,
                'along_slot_mm': dot(delta, g['tangent']), 'normal_mm': dot(delta, g['normal'])})
        cases.append({**case, 'endpoint_values': values})
    along = [r['along_slot_mm'] for c in cases for r in c['endpoint_values']]
    min_along, max_along = min(along), max(along)
    gap = .425-.4; half_q = max(abs(c['dq_mm']) for c in cases)
    # A small uniform disk witness proves axial flange blocking for every q:
    # center = pin + .55*N, radius=.05. Its normal distance from inner void
    # is at least .55-.025-.05=.475>.425; lambda stays inside both ends.
    witness_normal = .55; witness_radius = .05
    return {'schema': 'razr-key-endcap-local-arithmetic-v1', 'parameters': PARAMETERS,
        'geometry': g, 'four_flank_extremes': cases,
        'continuous_ideal_parameter_domain': {
            'nominal_q_mm': [0., 12.], 'crosshead_dx_mm': [-.025*math.hypot(1., 12./79.75), .025*math.hypot(1., 12./79.75)],
            'output_normal_offset_mm': [-gap, gap], 'actual_KEY_Y_translation_mm': [-half_q, 12.+half_q],
            'minimum_near_end_center_margin_mm': min_along,
            'minimum_far_end_center_margin_mm': g['slot_centerline_length_mm']-max_along,
            'finite_neck_inside_erosion_capsule_for_all_parameters': min_along >= 0. and max_along <= g['slot_centerline_length_mm'],
            'basis': 'along-slot center projection is affine in q, dx and output normal offset; endpoints of this box bound every continuous state; neck radius .4 plus normal offset <=.025 fits the closed .425 capsule',
            'closed_slot_finite_endcaps_not_removed': True,
            'manufacturing_tolerances_elasticity_and_preload_included': False},
        'nominal_near_radial_wall_mm': .95-.425,
        'new_outer_min_X_mm': 7.15-.95,
        'nominal_FPC_side_gap_mm': 7.15-.95-6.,
        'finite_flange_planar_cover_sufficient_bound_mm': .95-(.65+gap),
        'axial_blocking_witness': {'normal_offset_from_pin_mm': witness_normal, 'radius_mm': witness_radius,
            'minimum_distance_from_slot_centerline_mm': witness_normal-gap-witness_radius,
            'maximum_distance_from_slot_centerline_mm': witness_normal+gap+witness_radius,
            'minimum_along_slot_end_margin_mm': min(min_along, g['slot_centerline_length_mm']-max_along)-witness_radius,
            'fits_flange_annulus': witness_normal-witness_radius > .4 and witness_normal+witness_radius < .65,
            'lies_in_slot_wall_for_all_parameters': witness_normal-gap-witness_radius > .425 and witness_normal+gap+witness_radius < .95,
            'native_axial_overtravel_still_required': True},
        'reconstruction_changes_include_added_material': True,
        'reason_added_material_is_expected': 'shortening the inner capsule fills some former slot void with a new closed cap',
        'native_checks_executed': False, **RELEASE}


def new_output(path, source_root=None):
    path = Path(path).resolve()
    if path.exists() or path == Path(__file__).resolve().parent:
        raise ValueError('new output required')
    if source_root is not None and (path == source_root or source_root in path.parents):
        raise ValueError('output must be outside the source repository')
    path.mkdir(parents=True)
    return path


def native_run(repo_root, output):
    repo_root = Path(repo_root).resolve(); output = new_output(output, repo_root)
    before = {str(Path(__file__).resolve()): sha(__file__)}
    for relative, expected in PINS.items():
        actual = sha(repo_root/relative)
        if actual != expected: raise ValueError('source identity changed: '+relative)
        before[str(repo_root/relative)] = actual
    # Snapshot project Python before import/execution so late imports cannot
    # be retrospectively presented as pre-execution identities.
    for path in (repo_root/'integration').rglob('*.py'):
        before.setdefault(str(path.resolve()), sha(path))
    sys.path.insert(0, str(repo_root/'integration'))
    import cadquery as cq
    import cam_coupling as cam
    import product_assembly as p
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    for module, relative in ((cam, 'integration/cam_coupling.py'), (p, 'integration/product_assembly.py')):
        if Path(module.__file__).resolve() != repo_root/relative:
            raise ValueError('imported module is not the declared repository source')
    parent_manifest = cam.SOURCE/'geometry-manifest.json'
    parent_meta = json.loads(parent_manifest.read_text()); archive = cam.SOURCE/parent_meta['archive']
    if sha(archive) != parent_meta['archive_sha256']: raise ValueError('mounted archive identity mismatch')
    before.update({str(parent_manifest): sha(parent_manifest), str(archive): sha(archive)})
    versions = {}
    for name in ('cadquery', 'cadquery-ocp', 'numpy'):
        try: versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError: versions[name] = 'not installed'
    runtime = {'UTC': datetime.now(timezone.utc).isoformat(), 'PID': os.getpid(), 'PPID': os.getppid(),
        'python': sys.version, 'executable': sys.executable, 'packages': versions, 'argv': sys.argv}
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_root, text=True).strip()
    records = []; artifacts = {}; source_roles = {}

    def metric(body, empty=False):
        leaves, volume = p.whole_material(body, empty=empty)
        if not leaves: return {'empty': True, 'volume_mm3': 0., 'solids': [], 'bounds_mm': None}
        def one_metric(part):
            box = Bnd_Box(); BRepBndLib.AddOptimal_s(part.wrapped, box, False, False)
            x0, y0, z0, x1, y1, z1 = box.Get()
            return {'bounds_mm': [x0, x1, y0, y1, z0, z1], 'volume_mm3': float(part.Volume()), 'valid': bool(part.isValid())}
        return {'empty': False, **one_metric(body), 'volume_mm3': float(volume),
                'solids': [one_metric(s) for s in leaves], 'positive_valid_solids': len(leaves)}

    def save(name, body, *, empty=False):
        data = metric(body, empty=empty)
        if not data['empty']:
            path = output/'shapes'/(name+'.step'); path.parent.mkdir(exist_ok=True)
            cq.exporters.export(body, str(path))
            data.update(file=str(path.relative_to(output)), sha256=sha(path), independent_readback_executed=False)
        else: data.update(file=None, sha256=None)
        artifacts[name] = data
        return data

    def test(label, passed, **data):
        row = {'check': label, 'passed': bool(passed), **data}; records.append(row)
        write_json(output/'progress.json', {'source_commit': commit, 'runtime': runtime,
            'checks': records, 'artifacts': artifacts, 'complete': False, **RELEASE})
        return row

    def common(label, a, b, *, expect='zero'):
        try:
            body = a.intersect(b); data = metric(body, empty=True)
            volume = data['volume_mm3']
            if volume > min(metric(a)['volume_mm3'], metric(b)['volume_mm3'])+TOL:
                raise ValueError('Common volume exceeds complete participant')
            if not data['empty']: data = save(label+'-Common', body)
            passed = volume <= TOL if expect == 'zero' else volume > TOL
            return test(label, passed, expected=expect, common=data)
        except Exception as exc:
            return test(label, False, expected=expect, evaluation_failed=True,
                error_type=type(exc).__name__, error=str(exc))

    def difference(label, a, b, *, expected_zero=False):
        body = a.cut(b); data = save(label, body, empty=True)
        if expected_zero: test(label, data['volume_mm3'] <= TOL, difference=data)
        return body, data

    def same(label, a, b):
        _, first = difference(label+'-first-minus-second', a, b)
        _, second = difference(label+'-second-minus-first', b, a)
        return test(label, max(first['volume_mm3'], second['volume_mm3']) <= TOL,
                    first_minus_second=first, second_minus_first=second)

    def prism(points, z0, z1):
        wire = cq.Wire.makePolygon([cq.Vector(float(x), float(y), float(z0)) for x, y in points], close=True)
        return cam.one(cq.Solid.extrudeLinear(wire, [], cq.Vector(0., 0., float(z1-z0))))

    g = geometry_parameters(); z0, z1 = PARAMETERS['slot_Z_mm']
    near = cam.cylinder(.95, z0, z1, *g['C']); transition_end = cam.cylinder(1.1, z0, z1, *g['E'])
    tangent_bridge = prism(g['tangent_quadrilateral'], z0, z1)
    transition = cam.one(near.fuse(tangent_bridge).fuse(transition_end).clean())
    outer = cam.one(transition.fuse(cam.capsule(g['E'], g['D'], 1.1, z0, z1)).clean())
    inner = cam.capsule(g['C'], g['D'], .425, 1.1, 1.7)
    new_slot = cam.one(outer.cut(inner).clean())
    old_outer = cam.capsule(tuple(PARAMETERS['old_C_mm']), g['D'], 1.1, z0, z1)
    old_inner = cam.capsule(tuple(PARAMETERS['old_C_mm']), g['D'], .425, 1.1, 1.7)
    old_slot = cam.one(old_outer.cut(old_inner).clean())
    arm_specs = [((10.8, 39., 1.2), (11.4, 72.6, 1.6)),
        ((13.2, 39., 1.2), (13.45, 39.6, 4.35)),
        ((13.2, 15.8, 4.05), (13.45, 39.6, 4.35)),
        ((10.8, 39., 1.2), (13.45, 39.6, 1.6))]
    arm_parts = [cam.box(lo, hi) for lo, hi in arm_specs]
    arm_tab = arm_parts[0]
    for part in arm_parts[1:]: arm_tab = arm_tab.fuse(part)
    arm_tab = cam.one(arm_tab.clean())
    save('R-new-closed-slot', new_slot); save('R-old-closed-slot', old_slot)
    save('R-new-outer-linear-radius-transition', outer); save('R-new-inner-closed-capsule', inner)
    test('new-closed-slot-single-valid-solid', len(p.whole_material(new_slot)[0]) == 1, actual=metric(new_slot))
    test('new-closed-slot-near-outer-X-and-side-gap', abs(metric(outer)['bounds_mm'][0]-6.2) <= TOL,
         actual_min_X_mm=metric(outer)['bounds_mm'][0], nominal_gap_to_flex_edge_mm=metric(outer)['bounds_mm'][0]-6.)
    difference('new-outer-outside-old-outer', outer, old_outer, expected_zero=True)
    common('new-closed-slot-inner-void-remains-open', new_slot, inner)

    # Identify actual inner cylindrical caps and the two straight native planes.
    cylinders = []; planes = []
    center = scale(add(g['C'], g['D']), .5)
    for face in new_slot.Faces():
        if face.geomType() == 'CYLINDER':
            cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
            axis = cylinder.Axis().Direction(); origin = cylinder.Location()
            if abs(cylinder.Radius()-.425) <= TOL and abs(abs(axis.Z())-1.) <= TOL:
                cylinders.append({'radius_mm': cylinder.Radius(), 'center_xy_mm': [origin.X(), origin.Y()], 'area_mm2': face.Area()})
        elif face.geomType() == 'PLANE':
            n = face.normalAt(); projection = n.x*g['normal'][0]+n.y*g['normal'][1]
            point = face.Center()
            distance = abs(n.x*(center[0]-point.x)+n.y*(center[1]-point.y)+n.z*(1.4-point.z))
            if abs(abs(projection)-1.) <= TOL and abs(distance-.425) <= TOL:
                planes.append({'normal': list(n.toTuple()), 'point': list(point.toTuple()),
                    'centerline_distance_mm': distance, 'area_mm2': face.Area()})
    ends = sorted({(round(v['center_xy_mm'][0], 7), round(v['center_xy_mm'][1], 7)) for v in cylinders})
    test('actual-native-closed-inner-caps-and-straight-flanks',
        ends == sorted([tuple(g['C']), tuple(g['D'])]) and len(planes) == 2,
        inner_cylinder_faces=cylinders, straight_inner_planes=planes)

    # This oriented clipping region verifies distal equality; it does not cut
    # the candidate and is unrelated to a runtime Common bounding box.
    t, n = g['tangent'], g['normal']; L = g['slot_centerline_length_mm']
    region_points = [add(g['C'], add(scale(t, s), scale(n, v))) for s, v in ((1., -2.), (L+2., -2.), (L+2., 2.), (1., 2.))]
    distal_region = prism(region_points, z0, z1)
    same('distal-slot-material-from-E-retained', old_slot.intersect(distal_region), new_slot.intersect(distal_region))
    common('old-slot-positive-arm-joint', old_slot, arm_tab, expect='positive')
    common('new-slot-positive-arm-joint', new_slot, arm_tab, expect='positive')

    templates = cam.templates(); candidate = {}; mothers = {}; legacy_pawls = {}
    for side in 'LR':
        mother = cam.parent(side+'_KEY'); mothers[side] = mother
        old_factory = templates[side+'_KEY_YOKE']
        old_rebuilt = cam.one(mother.fuse(cam.handed(old_slot, side)).fuse(cam.handed(arm_tab, side)).clean())
        same(side+'-actual-old-KEY-factory-reconstruction', old_factory, old_rebuilt)
        new = cam.one(mother.fuse(cam.handed(new_slot, side)).fuse(cam.handed(arm_tab, side)).clean())
        candidate[side] = new
        save(side+'-actual-original-KEY-mother', mother); save(side+'-old-complete-KEY', old_factory)
        save(side+'-new-complete-KEY', new)
        test(side+'-new-complete-KEY-single-valid-solid', len(p.whole_material(new)[0]) == 1, actual=metric(new))
        # A narrower slot alone cannot establish clearance if any retained
        # mother or arm reaches farther inward. Use the complete native KEY,
        # with mirrored signed X, before asserting this limited separation.
        bounds = metric(new)['bounds_mm']
        signed_inner_x = bounds[0] if side == 'R' else -bounds[1]
        test(side+'-complete-KEY-central-width-12-nominal-separation',
             signed_inner_x >= 6.2-TOL, complete_KEY_bounds_mm=bounds,
             complete_KEY_signed_X_inner_edge_mm=signed_inner_x,
             central_object_required_X_interval_mm=[-6., 6.],
             nominal_minimum_X_gap_mm=signed_inner_x-6.,
             requested_nominal_gap_mm=.2,
             preserved_under_ideal_KEY_Y_translation=True,
             current_full_external_obstacle_field_checked=False,
             manufacturing_tolerance_or_strength_margin_verified=False)
        difference(side+'-original-KEY-material-lost', mother, new, expected_zero=True)
        difference(side+'-unchanged-arm-tab-material-lost', cam.handed(arm_tab, side), new, expected_zero=True)
        common(side+'-complete-KEY-inner-slot-void-remains-open', new, cam.handed(inner, side))
        common(side+'-arm-tab-positive-original-KEY-joint', mother, cam.handed(arm_tab, side), expect='positive')
        removed, rm = difference(side+'-removed-material', old_factory, new)
        added, ad = difference(side+'-added-material', new, old_factory)
        residual = metric(old_factory)['volume_mm3']-rm['volume_mm3']+ad['volume_mm3']-metric(new)['volume_mm3']
        test(side+'-whole-material-accounting', abs(residual) <= TOL,
             removed_mm3=rm['volume_mm3'], added_mm3=ad['volume_mm3'], signed_balance_error_mm3=residual,
             added_is_expected_new_closed_cap_material=True)
        same(side+'-changed-material-retains-distal-interface',
             old_factory.intersect(cam.handed(distal_region, side)), new.intersect(cam.handed(distal_region, side)))
        legacy_pawls[side] = cam.parent(side+'_PAWL')
    write_json(output/'construction-checkpoint.json', {'source_commit': commit, 'checks': records, 'artifacts': artifacts, **RELEASE})

    # Extract actual finite capture material from native CROSSHEAD. The box is
    # an inspection domain for a separately known source feature, never a cut
    # proposal. At z<=1.8 other CROSSHEAD material is outside this domain.
    inspection = cam.box((7.25-.66, 77.5-.66, 1.), (7.25+.66, 77.5+.66, 1.8))
    actual_capture = cam.one(templates['R_CROSSHEAD'].intersect(inspection).clean())
    expected_capture = cam.one(cam.cylinder(.4, 1., 1.8, 7.25, 77.5)
        .fuse(cam.cylinder(.65, 1., 1.2, 7.25, 77.5))
        .fuse(cam.cylinder(.65, 1.6, 1.8, 7.25, 77.5)).clean())
    same('actual-CROSSHEAD-finite-capture-feature', actual_capture, expected_capture)
    save('R-actual-finite-neck-and-two-flanges', actual_capture)
    for side in 'LR':
        sign = -1. if side == 'L' else 1.
        whole = candidate[side]
        for index, case in enumerate(clearance_cases()):
            start, end = pin_center(0., case), pin_center(12., case)
            sweep = cam.handed(cam.capsule(start, end, .4, 1.2, 1.6), side)
            common(f'{side}-flank{index}-finite-neck-exact-full-q-sweep', sweep, whole)
            save(f'{side}-flank{index}-neck-full-q-sweep', sweep)
            offset = scale(g['normal'], case['output_flank']*.01)
            over_sweep = cam.handed(cam.capsule(add(start, offset), add(end, offset), .4, 1.2, 1.6), side)
            common(f'{side}-flank{index}-normal-overtravel-full-q-sweep', over_sweep, whole, expect='positive')
            for q in (0., 12.):
                label = f'{side}-flank{index}-q{int(q)}'
                capture = cam.handed(actual_capture, side).translate((sign*(q+case['dx_mm']), -q-case['dq_mm'], 0.))
                common(label+'-actual-finite-capture-at-nominal-Z', capture, whole)
                for direction in (-1, 1):
                    shifted = capture.translate((0., 0., direction*.01))
                    common(label+f'-capture-axial-overtravel-{direction}', shifted, whole, expect='positive')
                    center = add(pin_center(q, case), scale(g['normal'], .55))
                    # For +Z travel the lower flange blocks at 1.2..1.21;
                    # for -Z travel the upper flange blocks at 1.59..1.6.
                    wz0, wz1 = ((1.2, 1.21) if direction > 0 else (1.59, 1.6))
                    witness = cam.handed(cam.cylinder(.05, wz0, wz1, *center), side)
                    difference(label+f'-axial-witness-{direction}-outside-slot-wall', witness, whole, expected_zero=True)
                    difference(label+f'-axial-witness-{direction}-outside-finite-capture', witness, shifted, expected_zero=True)

    # Exact swept boxes preserve the old arm/tab guide interfaces for the
    # entire enlarged ideal output band. Full KEY-to-phone clearance is absent.
    arithmetic = arithmetic_report(); qlo, qhi = arithmetic['continuous_ideal_parameter_domain']['actual_KEY_Y_translation_mm']
    arm_sweeps = [cam.box((lo[0], lo[1]+qlo, lo[2]), (hi[0], hi[1]+qhi, hi[2])) for lo, hi in arm_specs]
    # Exact translation envelope of the larger constant-R1.1 outer capsule.
    # It conservatively contains the new variable-radius closed-slot material
    # throughout q, including every ideal dx/dq case; it is not a swept void.
    envelope_points = [add(point, (0., q)) for point, q in
        ((g['C'], qlo), (g['D'], qlo), (g['D'], qhi), (g['C'], qhi))]
    outer_envelope = prism(envelope_points, z0, z1)
    for index, point in enumerate(envelope_points):
        outer_envelope = outer_envelope.fuse(cam.capsule(point, envelope_points[(index+1) % 4], 1.1, z0, z1))
    outer_envelope = cam.one(outer_envelope.clean())
    save('R-new-slot-conservative-outer-full-q-translation-envelope', outer_envelope)
    housing, _ = cam.housing_study()
    for side in 'LR':
        for y in (56., 62.):
            guide_parts = [cam.box((10.5, y, .60), (11.7, y+2., 1.15)),
                cam.box((10.5, y, 1.1), (10.75, y+2., 1.9)), cam.box((11.45, y, 1.1), (11.7, y+2., 1.9)),
                cam.box((10.5, y, 1.65), (11.7, y+2., 1.9))]
            guide = guide_parts[0]
            for part in guide_parts[1:]: guide = cam.one(guide.fuse(part).clean())
            guide = cam.handed(guide, side)
            difference(f'{side}-guide{int(y)}-not-in-actual-parent-panel', guide, housing['A_BACK_PANEL'], expected_zero=True)
            for index, sweep in enumerate(arm_sweeps):
                common(f'{side}-guide{int(y)}-original-arm{index}-full-q-sweep', cam.handed(sweep, side), guide)
            common(f'{side}-guide{int(y)}-new-slot-conservative-outer-full-q-envelope',
                cam.handed(outer_envelope, side), guide)
        # Reproduce and extend the historical added-arm/full-PAWL-rise scope.
        # This old mounted PAWL is not the later serviceable/endpoint PAWL.
        legacy = legacy_pawls[side]; b = metric(legacy)['bounds_mm']
        pawl_envelope = cam.box((b[0], b[2], b[4]), (b[1], b[3], b[5]+1.1))
        save(side+'-legacy-mounted-PAWL-complete-rise-envelope', pawl_envelope)
        extension = candidate[side].cut(mothers[side]); metric(extension)
        for q in (qlo, 0., (qlo+qhi)/2., 12., qhi):
            common(f'{side}-legacy-PAWL-added-extension-q{q:.9f}', extension.translate((0., q, 0.)), pawl_envelope)
        for index, sweep in enumerate(arm_sweeps):
            common(f'{side}-legacy-PAWL-original-arm{index}-full-q-sweep', cam.handed(sweep, side), pawl_envelope)
        common(side+'-legacy-PAWL-new-slot-conservative-outer-full-q-envelope',
            cam.handed(outer_envelope, side), pawl_envelope)

    # Include every project module actually loaded, not just the named entry.
    late_sources = {}
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path:
            path = Path(path).resolve()
            if path.is_file() and path.is_relative_to(repo_root):
                if str(path) not in before: late_sources[str(path)] = sha(path)
    unchanged = not late_sources and all(sha(path) == value for path, value in before.items())
    result = {'schema': 'razr-key-endcap-local-native-v1', 'source_commit': commit,
        'source_sha256': before, 'source_bytes_unchanged': unchanged, 'runtime': runtime,
        'loaded_sources_without_pre_execution_snapshot': late_sources,
        'parameters': PARAMETERS, 'arithmetic': arithmetic, 'checks': records, 'artifacts': artifacts,
        'native_checks_executed': True, 'all_declared_local_checks_passed': unchanged and all(r['passed'] for r in records),
        'declared_failures': [r for r in records if not r['passed']],
        'scope': 'local closed-slot reconstruction, preserved original mother/arm/guide interfaces, ideal two-flank neck sweep and finite axial capture; not phone integration',
        'reverse_ideal_parameter_set_reuses_same_rigid_geometry': True,
        'continuous_ideal_neck_sweep_is_not_forced_motion_or_friction_proof': True,
        'legacy_PAWL_return_scope': 'old mounted PAWL, complete 1.1mm axial bounding envelope; current endpoint/serviceable PAWL, tabs, spring loads and relocking remain unverified',
        'captured_flange_installation_and_retention_process_verified': False,
        'current_full_external_obstacle_field_checked': False,
        'actual_local_wall_strength_or_material_tolerance_verified': False, **RELEASE}
    write_json(output/'native-report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo-root', type=Path)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    if args.native and args.repo_root is None: parser.error('--native requires --repo-root')
    if args.repo_root and not args.repo_root.resolve().is_dir(): parser.error('repository root does not exist')
    output = new_output(args.output, args.repo_root.resolve() if args.repo_root else None)
    report = arithmetic_report(); report['script_sha256'] = sha(__file__)
    write_json(output/'arithmetic.json', report)
    if args.native:
        try:
            result = native_run(args.repo_root, output/'native')
            print(json.dumps({'native_completed': True, 'all_declared_local_checks_passed': result['all_declared_local_checks_passed'], **RELEASE}))
            if not result['all_declared_local_checks_passed']: return 2
        except Exception as exc:
            write_json(output/'native-execution-failure.json', {'error_type': type(exc).__name__, 'error': str(exc),
                'traceback': traceback.format_exc(), 'script_sha256': sha(__file__), 'native_report_completed': False, **RELEASE})
            raise
    else:
        print(json.dumps({'arithmetic_completed': True, 'native_executed': False, **RELEASE}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
