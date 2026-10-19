"""Resolve one explicit captured-follower assembly topology in separate parts.

The original integral, capped tubes and closed-slot heads are negative controls
for straight axial insertion.  This does not prove that every conceivable
forming/manufacturing process is impossible.  A split-floor/retainer study then
demonstrates complete axial insertion sweeps with all original final material
restored.  Seven added pieces per hand require actual joining process design;
contacting CAD surfaces do not establish a retained or manufacturable joint.

No product geometry or old evidence is modified.  The isolated cylindrical
stages/slot strips are reconstructed from SHA-pinned cam_coupling.py.  With
--verify-native, the original builder is independently executed and the local
reconstructions are compared to its real templates by Boolean differences.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

SOURCE_SHA = '4a3bf1d2b86d31fa8e3d60d3412e15548bf42287ed95d756798f3d88c6c4e631'
TOL = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cylinder(outer, inner, z0, z1):
    result = cq.Solid.makeCylinder(outer, z1-z0, cq.Vector(0, 0, z0))
    if inner:
        result = result.cut(cq.Solid.makeCylinder(inner, z1-z0, cq.Vector(0, 0, z0)))
    return result


def volume(body):
    values = body.Solids()
    if any(not x.isValid() or x.Volume() <= 0 for x in values):
        raise ValueError('invalid complete material')
    return sum(x.Volume() for x in values)


def union(bodies):
    bodies = list(bodies)
    result = bodies[0]
    for body in bodies[1:]:
        result = result.fuse(body)
    result = result.clean()
    volume(result)
    return result


def body(intervals):
    # Each tuple is (outer radius, inner radius, lower Z, upper Z).
    return union(cylinder(*row) for row in intervals)


def shifted(intervals, dz):
    return [(r, ri, z0+dz, z1+dz) for r, ri, z0, z1 in intervals]


def axial_sweep(intervals, q0, q1):
    """Exact set union over a continuous axial translation of these annuli."""
    low, high = min(q0, q1), max(q0, q1)
    return body([(r, ri, z0+low, z1+high) for r, ri, z0, z1 in intervals])


def common(a, b):
    value = volume(a.intersect(b))
    if value > min(volume(a), volume(b))+TOL:
        raise ValueError('impossible intersection volume')
    return value


def difference(a, b):
    return {'first_minus_second_mm3': volume(a.cut(b)),
            'second_minus_first_mm3': volume(b.cut(a))}


def box(lo, hi):
    return cq.Solid.makeBox(*(b-a for a, b in zip(lo, hi)), cq.Vector(*lo))


def capsule(a, b, radius, z0, z1):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = (dx*dx+dy*dy)**.5
    vx, vy = -dy*radius/length, dx*radius/length
    points = [cq.Vector(a[0]+vx, a[1]+vy, z0), cq.Vector(a[0]-vx, a[1]-vy, z0),
              cq.Vector(b[0]-vx, b[1]-vy, z0), cq.Vector(b[0]+vx, b[1]+vy, z0)]
    wire = cq.Wire.makePolygon(points, close=True)
    bridge = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, z1-z0))
    return union([bridge, cylinder(radius, 0, z0, z1).translate((*a, 0)),
                  cylinder(radius, 0, z0, z1).translate((*b, 0))])


def slot(a, b, outer, z0, z1):
    return capsule(a, b, outer, z0, z1).cut(capsule(a, b, .425, z0-.1, z1+.1)).clean()


def slot_sweep(a, b, outer, z0, z1, dz):
    return slot(a, b, outer, z0+min(0, dz), z1+max(0, dz))


def bounds(shape):
    result = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, result, False, False)
    xmin, ymin, zmin, xmax, ymax, zmax = result.Get()
    return [xmin, xmax, ymin, ymax, zmin, zmax]


def source_geometry():
    specs = [(1.4, 1.2, 1.05, None), (1., .8, .65, 1.15), (.6, .4, .25, .75)]
    original, split = {}, {}
    for i, (outer, bore, throat, collar) in enumerate(specs):
        lower_outer = outer if collar is None else collar
        intervals = [(lower_outer, 0., 0., .1), (lower_outer, bore, .1, .2),
                     (outer, bore, .2, 3.1), (outer, throat, 3.1, 3.2)]
        original[f'TUBE_{i}'] = intervals
        split[f'TUBE_{i}_OPEN_BOTTOM'] = [(lower_outer, bore, 0., .2),
            (outer, bore, .2, 3.1), (outer, throat, 3.1, 3.2)]
        split[f'TUBE_{i}_BOTTOM_CAP'] = [(bore, 0., 0., .1)]
    original['CORE'] = [(.35, 0., 0., .2), (.2, 0., .2, 3.15),
        (.4, 0., 3.15, 3.3), (.65, 0., 3.3, 3.5),
        (.4, 0., 3.5, 3.8), (.65, 0., 3.8, 4.)]
    split['CORE_STEM'] = [(.2, 0., 0., 3.15), (.4, 0., 3.15, 4.)]
    split['CORE_BOTTOM_SHOULDER'] = [(.35, .2, 0., .2)]
    split['CAM_LOWER_FLANGE'] = [(.65, .4, 3.3, 3.5)]
    split['CAM_UPPER_FLANGE'] = [(.65, .4, 3.8, 4.)]
    original['KEY_FOLLOWER'] = [(.65, 0., 1., 1.2), (.4, 0., 1.2, 1.6),
        (.65, 0., 1.6, 1.8), (.4, 0., 1.8, 2.1)]
    split['KEY_FOLLOWER_WITHOUT_LOWER_FLANGE'] = [(.4, 0., 1., 1.6),
        (.65, 0., 1.6, 1.8), (.4, 0., 1.8, 2.1)]
    split['KEY_LOWER_FLANGE'] = [(.65, .4, 1., 1.2)]
    return specs, original, split


def run(source, output, verify_native=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    if sha(source) != SOURCE_SHA:
        raise ValueError('source changed; rederive the local annular constructions')
    if output.exists():
        raise ValueError('new output directory required')
    specs, original, split = source_geometry()
    src = {k: body(v) for k, v in original.items()}
    pieces = {k: body(v) for k, v in split.items()}
    reconstruction = []
    for i in range(3):
        rejoined = union([pieces[f'TUBE_{i}_OPEN_BOTTOM'], pieces[f'TUBE_{i}_BOTTOM_CAP']])
        reconstruction.append({'part': f'TUBE_{i}', **difference(src[f'TUBE_{i}'], rejoined)})
    reconstruction.append({'part': 'CORE', **difference(src['CORE'], union(pieces[k] for k in
        ('CORE_STEM', 'CORE_BOTTOM_SHOULDER', 'CAM_LOWER_FLANGE', 'CAM_UPPER_FLANGE')))})
    reconstruction.append({'part': 'KEY_FOLLOWER', **difference(src['KEY_FOLLOWER'], union(pieces[k] for k in
        ('KEY_FOLLOWER_WITHOUT_LOWER_FLANGE', 'KEY_LOWER_FLANGE')))})
    if any(max(r['first_minus_second_mm3'], r['second_minus_first_mm3']) > TOL for r in reconstruction):
        raise ValueError('split reassembly did not preserve original material')
    # Original finished parts cannot take these simple axial insertion paths.
    negatives = []
    for i, child in enumerate(('TUBE_1', 'TUBE_2', 'CORE')):
        for direction in (-1., 1.):
            sweep = axial_sweep(original[child], .1, .1+6.*direction)
            v = common(sweep, src[f'TUBE_{i}'])
            negatives.append({'parent': f'TUBE_{i}', 'child': child,
                'entry': 'bottom' if direction < 0 else 'top',
                'complete_axial_translation_mm': [6.*direction, 0.],
                'common_mm3': v, 'blocked': v > TOL})
    if not all(r['blocked'] for r in negatives):
        raise ValueError('expected original axial-entry negative control disappeared')
    paths = []
    def insert(label, moving_intervals, final_shift, withdrawal, installed):
        sweep = axial_sweep(moving_intervals, final_shift, final_shift+withdrawal)
        comparisons = [{'fixed': k, 'common_mm3': common(sweep, v)} for k, v in installed.items()]
        row = {'action': label, 'moving_final_shift_z_mm': final_shift,
               'withdrawal_z_mm': withdrawal, 'sweep_method': 'exact union of axially translated annular intervals',
               'moving_annular_sections_r_outer_r_inner_z_lo_z_hi_mm': moving_intervals,
               'all_obstacles': comparisons, 'rejected': [r for r in comparisons if r['common_mm3'] > TOL],
               'joining_strength_or_process_verified': False}
        paths.append(row)
        if row['rejected']:
            raise ValueError(label+': positive volume along assembly path')
        return body(shifted(moving_intervals, final_shift))
    # Deepest joint is closed before entering the next larger shell.
    assembly2 = {'TUBE_2_OPEN_BOTTOM': pieces['TUBE_2_OPEN_BOTTOM']}
    assembly2['CORE_STEM'] = insert('1 insert bare core from top into open tube 2', split['CORE_STEM'], .1, 6., assembly2)
    assembly2['CORE_BOTTOM_SHOULDER'] = insert('2 install core bottom shoulder through open base', split['CORE_BOTTOM_SHOULDER'], .1, -6., assembly2)
    assembly2['TUBE_2_BOTTOM_CAP'] = insert('3 close tube 2 bottom before next nesting', split['TUBE_2_BOTTOM_CAP'], 0., -6., assembly2)
    unit2_intervals = split['TUBE_2_OPEN_BOTTOM']+split['TUBE_2_BOTTOM_CAP']+shifted(split['CORE_STEM']+split['CORE_BOTTOM_SHOULDER'], .1)
    assembly1 = {'TUBE_1_OPEN_BOTTOM': pieces['TUBE_1_OPEN_BOTTOM']}
    assembly1['INNER_UNIT'] = insert('4 insert closed inner unit from tube 1 bottom', unit2_intervals, .1, -8., assembly1)
    assembly1['TUBE_1_BOTTOM_CAP'] = insert('5 close tube 1 bottom before outer nesting', split['TUBE_1_BOTTOM_CAP'], 0., -6., assembly1)
    unit1_intervals = split['TUBE_1_OPEN_BOTTOM']+split['TUBE_1_BOTTOM_CAP']+shifted(unit2_intervals, .1)
    assembly0 = {'TUBE_0_OPEN_BOTTOM': pieces['TUBE_0_OPEN_BOTTOM']}
    assembly0['MIDDLE_AND_INNER_UNIT'] = insert('6 insert middle/inner unit from outer bottom', unit1_intervals, .1, -10., assembly0)
    assembly0['TUBE_0_BOTTOM_CAP'] = insert('7 close crosshead outer bottom before housing installation', split['TUBE_0_BOTTOM_CAP'], 0., -6., assembly0)
    assembly0['CAM_LOWER_FLANGE'] = insert('8 install lower cam flange over bare top stem', split['CAM_LOWER_FLANGE'], .3, 6., assembly0)
    # Actual finite cam strip; its coordinates are relative to the outer tube.
    ratio = 12./79.75
    a = (ratio*(81.5-1.), 1.-81.5)
    b = (ratio*(81.5-82.25), 82.25-81.5)
    cam = slot(a, b, .95, 3.8, 4.1)
    cam_swept = slot_sweep(a, b, .95, 3.8, 4.1, 6.)
    rows = [{'fixed': k, 'common_mm3': common(cam_swept, v)} for k, v in assembly0.items()]
    paths.append({'action': '9 lower finite B cam strip over bare upper neck',
        'withdrawal_z_mm': 6., 'sweep_method': 'exact constant cross-section slot extrusion',
        'all_obstacles': rows, 'rejected': [r for r in rows if r['common_mm3'] > TOL],
        'whole_B_shell_insertion_verified': False})
    if paths[-1]['rejected']:
        raise ValueError('cam strip insertion failed')
    assembly0['CAM_SLOT_REFERENCE'] = cam
    # The retainer's annular trajectory must also avoid the entire cam strip.
    assembly0['CAM_UPPER_FLANGE'] = insert('10 install upper cam flange after slot strip', split['CAM_UPPER_FLANGE'], .3, 6., assembly0)
    original_head = src['CORE'].translate((0., 0., .3))
    original_cam_negative = common(cam_swept, original_head)
    negatives.append({'parent': 'complete integral core top heads', 'child': 'finite B cam strip',
        'entry': 'axial from top', 'common_mm3': original_cam_negative, 'blocked': original_cam_negative > TOL})
    # Second groove uses its real finite diagonal capsule, without pretending
    # the original KEY arm and housing have been inserted by this strip study.
    c, d = (-.75, .75), (12.75, -12.75)
    key_slot = slot(c, d, 1.1, 1.2, 1.6)
    key_sweep = slot_sweep(c, d, 1.1, 1.2, 1.6, -6.)
    key_fixed = pieces['KEY_FOLLOWER_WITHOUT_LOWER_FLANGE']
    new_key_common = common(key_sweep, key_fixed)
    original_key_common = common(key_sweep, src['KEY_FOLLOWER'])
    negatives.append({'parent': 'complete integral KEY follower heads', 'child': 'finite KEY groove strip',
        'entry': 'axial from bottom', 'common_mm3': original_key_common, 'blocked': original_key_common > TOL})
    paths.append({'action': '11 raise finite KEY groove strip over bare lower follower neck',
        'withdrawal_z_mm': -6., 'sweep_method': 'exact constant cross-section slot extrusion',
        'all_obstacles': [{'fixed': 'KEY_FOLLOWER_WITHOUT_LOWER_FLANGE', 'common_mm3': new_key_common}],
        'rejected': [] if new_key_common <= TOL else [{'common_mm3': new_key_common}],
        'whole_KEY_yoke_and_housing_insertion_verified': False})
    if new_key_common > TOL or min(original_cam_negative, original_key_common) <= TOL:
        raise ValueError('slot-head positive or negative control failed')
    insert('12 install KEY lower flange after groove strip', split['KEY_LOWER_FLANGE'], 0., -6.,
           {'KEY_FOLLOWER': key_fixed, 'KEY_SLOT_REFERENCE': key_slot})
    # Original offset limits remain exactly as before after joining the parts.
    limits = []
    for i, child in enumerate(('TUBE_1', 'TUBE_2', 'CORE')):
        for offset in (.1, 2.9, .09, 2.91):
            v = common(src[f'TUBE_{i}'], src[child].translate((0, 0, offset)))
            allowed = offset in (.1, 2.9)
            if (allowed and v > TOL) or (not allowed and v <= TOL):
                raise ValueError('reconstructed joint changed an original axial stop')
            limits.append({'joint': i+1, 'offset_mm': offset, 'common_mm3': v, 'at_permitted_limit': allowed})
    native_rows = None
    if verify_native:
        sys.path.insert(0, str(source.parent))
        import cam_coupling as native
        templates = native.templates()
        native_rows = []
        native0 = templates['R_CROSSHEAD'].intersect(cylinder(1.4, 0., .7, 3.9).translate((7.25, 81.5, 0.))).translate((-7.25, -81.5, -.7))
        candidates = [('TUBE_0', native0), ('TUBE_1', templates['R_TELESCOPE_1']),
                      ('TUBE_2', templates['R_TELESCOPE_2']), ('CORE', templates['R_TELESCOPE_3'])]
        for name, native_body in candidates:
            item = {'part': name, **difference(src[name], native_body)}
            if max(item['first_minus_second_mm3'], item['second_minus_first_mm3']) > TOL:
                raise ValueError('actual native template differs: '+name)
            native_rows.append(item)
        exact_cam = templates['R_B_CAM'].translate((-7.25, -81.5, -.7))
        item = {'part': 'CAM_SLOT_REFERENCE', **difference(cam, exact_cam)}
        if max(item['first_minus_second_mm3'], item['second_minus_first_mm3']) > TOL:
            raise ValueError('actual native cam strip differs')
        native_rows.append(item)
        for name, local_body, offset, native_name in (
            ('KEY_FOLLOWER', src['KEY_FOLLOWER'], (7.25, 77.5, 0.), 'R_CROSSHEAD'),
            ('KEY_SLOT_REFERENCE', key_slot, (7.25, 77.5, 0.), 'R_KEY_YOKE')):
            omitted = volume(local_body.translate(offset).cut(templates[native_name]))
            if omitted > TOL:
                raise ValueError('isolated local body is absent from the actual native part: '+name)
            native_rows.append({'part': name, 'actual_native_container': native_name,
                'local_material_not_in_actual_native_part_mm3': omitted,
                'comparison_kind': 'contained source primitive, not the entire native part'})
    output.mkdir(parents=True)
    exports = []
    for name, item in sorted({**pieces, 'CAM_SLOT_REFERENCE': cam, 'KEY_SLOT_REFERENCE': key_slot}.items()):
        if len(item.Solids()) != 1:
            raise ValueError('each split manufacturing body must be one connected solid')
        f = output/(name+'.step')
        cq.exporters.export(item, str(f))
        if name.startswith('TUBE_'):
            index = int(name[5]); outer, bore, throat, collar = specs[index]
            features = {'nominal_minimum_axial_wall_or_lip_mm': .1,
                'nominal_main_barrel_radial_wall_mm': outer-bore,
                'nominal_bottom_join_diameter_mm': 2*bore,
                'nominal_maximum_outside_diameter_mm': 2*(outer if collar is None else collar)}
            if name.endswith('_BOTTOM_CAP'):
                features = {'nominal_disk_thickness_mm': .1,
                    'nominal_disk_diameter_mm': 2*bore, 'nominal_seam_diameter_mm': 2*bore}
        elif name == 'CORE_BOTTOM_SHOULDER':
            features = {'nominal_axial_thickness_mm': .2, 'nominal_ring_radial_width_mm': .15,
                        'nominal_shaft_join_diameter_mm': .4}
        elif name.endswith('_FLANGE'):
            features = {'nominal_axial_thickness_mm': .2, 'nominal_ring_radial_width_mm': .25,
                        'nominal_shaft_join_diameter_mm': .8}
        elif name == 'CORE_STEM':
            features = {'nominal_minimum_stem_diameter_mm': .4,
                        'nominal_top_neck_diameter_mm': .8, 'joint_transition_fillet_specified': False}
        else:
            features = {'nominal_pin_diameter_mm': .8, 'nominal_closed_slot_width_mm': .85,
                        'applies_to': 'pin or slot according to this part role'}
        exports.append({'part': name, 'file': f.name, 'sha256': sha(f),
                        'bounds_mm': bounds(item), 'volume_mm3': volume(item), 'valid_solids': 1,
                        'process_features': features, 'measured_as_built_features_mm': None})
    assembly = cq.Assembly(name='isolated_seated_captured_telescopic_subassembly')
    part_placement = {'TUBE_0_OPEN_BOTTOM': 0., 'TUBE_0_BOTTOM_CAP': 0.,
        'TUBE_1_OPEN_BOTTOM': .1, 'TUBE_1_BOTTOM_CAP': .1,
        'TUBE_2_OPEN_BOTTOM': .2, 'TUBE_2_BOTTOM_CAP': .2,
        'CORE_STEM': .3, 'CORE_BOTTOM_SHOULDER': .3,
        'CAM_LOWER_FLANGE': .3, 'CAM_UPPER_FLANGE': .3}
    for name, offset in part_placement.items():
        assembly.add(pieces[name].translate((0, 0, offset)), name=name)
    assembly.add(cam, name='CAM_SLOT_REFERENCE')
    assembly_file = output/'isolated-cam-telescope-assembly.step'
    assembly.export(str(assembly_file))
    report = {'schema': 'razr-captured-follower-assembly-study-v1',
        'construction_source': 'integration/cam_coupling.py', 'construction_source_sha256': SOURCE_SHA,
        'study_source_sha256': sha(__file__),
        'runtime': {'python': platform.python_version(), 'cadquery': cq.__version__},
        'source_template_comparisons': native_rows, 'native_builder_comparison_executed': verify_native,
        'original_axial_insertion_negative_controls': negatives,
        'split_part_reassembly_material_differences': reconstruction,
        'split_parts_added_per_hand': 7,
        'original_nominal_geometry_changes_mm3': {'added': 0., 'removed': 0.},
        'assembly_actions': paths, 'original_axial_limits_rechecked': limits,
        'subassembly_members': {
            'INNER_UNIT_relative_to_tube_2': {'TUBE_2_OPEN_BOTTOM': 0., 'TUBE_2_BOTTOM_CAP': 0.,
                'CORE_STEM': .1, 'CORE_BOTTOM_SHOULDER': .1},
            'MIDDLE_AND_INNER_UNIT_relative_to_tube_1': {'TUBE_1_OPEN_BOTTOM': 0., 'TUBE_1_BOTTOM_CAP': 0.,
                'TUBE_2_OPEN_BOTTOM': .1, 'TUBE_2_BOTTOM_CAP': .1,
                'CORE_STEM': .2, 'CORE_BOTTOM_SHOULDER': .2},
            'placement_values_are_axial_translation_mm': True,
            'all_CAM_flanges_left_off_until_nested_tube_assembly_complete': True},
        'parts': exports,
        'combined': {'file': assembly_file.name, 'sha256': sha(assembly_file), 'expected_solids': 11},
        'joining': {
            'selected_material': None, 'selected_process': None, 'qualified_process_tolerance_mm': None,
            'joint_load_capacity_N': None,
            'bottom_caps': [{'tube': i, 'plug_diameter_mm': 2*bore, 'plug_thickness_mm': .1,
                'nominal_circular_seam_radius_mm': bore, 'seam_face_local_z_mm': 0.,
                'access_direction': '-Z, before this unit is nested into the next larger tube',
                'bottom_face_unobstructed_in_isolated_assembly': True} for i, (_, bore, _, _) in enumerate(specs)],
            'core_shoulder': {'outer_diameter_mm': .7, 'inner_diameter_mm': .4, 'thickness_mm': .2,
                'access': 'through open tube 2 base before installing its bottom cap'},
            'cam_and_KEY_flanges': {'outer_diameter_mm': 1.3, 'inner_diameter_mm': .8, 'thickness_mm': .2,
                'cam_access': 'isolated strip only; whole B shell access remains unverified',
                'KEY_access': 'isolated strip only; whole KEY/housing installation remains unverified'},
            'CAD_interface': 'nominal touching cylinder surfaces; no thread, weld bead, fillet, adhesive thickness, or interference fit is invented',
            'minimum_remaining_work': 'select real material/process, define joint prep and distortion allowances, prove accessible joining in full housing, measure retention and repeat insertion after redesign'},
        'limitations': ['straight axial insertion demonstrated for isolated stages and finite groove strips',
            'original finished integral bodies rejected only for the declared axial paths, not all fabrication processes',
            'no complete 94-part assembly order or whole-shell insertion proof',
            'split seams require actual joining design before this is a manufacturable mechanism',
            'zero material change assumes mathematically rejoined surfaces; physical bond lines need their own geometry',
            'no material, actual force, preload, fatigue, process yield, or physical fabrication results'],
        'new_product_candidate_selected': False, 'full_product_assembly_proved': False,
        'physical_fabrication_occurred': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
    if sha(source) != SOURCE_SHA:
        raise ValueError('construction source changed during execution')
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-native', action='store_true')
    args = parser.parse_args()
    result = run(args.native_source, args.output, args.verify_native)
    print(json.dumps({'negative_controls': len(result['original_axial_insertion_negative_controls']),
        'assembly_actions': len(result['assembly_actions']), 'parts': len(result['parts']),
        'native_builder_comparison_executed': result['native_builder_comparison_executed'],
        'physical_fabrication_occurred': False}))
