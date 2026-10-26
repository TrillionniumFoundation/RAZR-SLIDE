"""Independent v2 research cut package for the two measured STOW KEY Y layers.

This module does not modify production defaults or the original admissible
coupled slot domain. The secondary nominal KEY face at Y=13.7 mm is inferred
from the measured full-band Common and the byte-pinned rigid displacement.
It is not a new direct nominal-plane measurement. The 0.020 mm construction
gap and 0.001 mm cutter padding are research values, not process tolerances.
This draft has not executed native CAD or proved a continuous collision domain.
"""
from __future__ import annotations

import math
from pathlib import Path

FACE_Y = 14.73
KEY_FACE_Y = 14.75
Z_RANGE = (2.7, 3.1)
EDGE_PADDING = .001
POSITIVE_X_STRIPS = {'CAP_0': ((26.87, 27.17),),
                     'ROOT_INNER': ((22.85, 23.05), (27.85, 28.05))}
SECONDARY_FIXED_FACE_Y = 13.645
SECONDARY_KEY_FACE_Y_INFERRED = 13.7
SECONDARY_Z_RANGE = (3.6, 4.0)
SECONDARY_X_STRIPS = ((23.57, 23.69), (24.01, 25.33),
                      (28.57, 28.69), (29.01, 30.33))
SECONDARY_CONSTRUCTION_GAP = .020


def definition():
    cam = (.425-.4)*math.hypot(1., 12./79.75)
    yoke = (.425-.4)*math.sqrt(2.)
    half = cam+yoke
    secondary_cut_y = SECONDARY_KEY_FACE_Y_INFERRED-half-SECONDARY_CONSTRUCTION_GAP
    rows = []
    for side in 'LR':
        for role, strips in POSITIVE_X_STRIPS.items():
            boxes = []
            for lo, hi in strips:
                x0, x1 = (lo, hi) if side == 'R' else (-hi, -lo)
                boxes.append({'lo_mm': [x0-EDGE_PADDING, FACE_Y-half, Z_RANGE[0]-EDGE_PADDING],
                              'hi_mm': [x1+EDGE_PADDING, KEY_FACE_Y, Z_RANGE[1]+EDGE_PADDING],
                              'measured_layer': 'primary_Y_14p73_Z_2p7_to_3p1'})
            if role == 'ROOT_INNER':
                for lo, hi in SECONDARY_X_STRIPS:
                    x0, x1 = (lo, hi) if side == 'R' else (-hi, -lo)
                    boxes.append({'lo_mm': [x0-EDGE_PADDING, secondary_cut_y,
                                             SECONDARY_Z_RANGE[0]-EDGE_PADDING],
                                  'hi_mm': [x1+EDGE_PADDING, SECONDARY_KEY_FACE_Y_INFERRED,
                                             SECONDARY_Z_RANGE[1]+EDGE_PADDING],
                                  'measured_layer': 'secondary_Y_13p645_Z_3p6_to_4p0'})
            rows.append({'part': side+'_'+role, 'cut_boxes': boxes})
    vertices = [{'dx_mm': dx, 'dq_mm': dx-difference,
                 'cam_flank_sign': sx, 'yoke_flank_sign': sy}
                for sx, dx in ((-1, -cam), (1, cam))
                for sy, difference in ((-1, -yoke), (1, yoke))]
    return {
        'schema': 'razr-STOW-local-two-layer-face-relief-research-20261025-v2',
        'original_native_face_Y_mm': FACE_Y,
        'original_KEY_face_Y_mm': KEY_FACE_Y,
        'original_nominal_face_gap_mm': KEY_FACE_Y-FACE_Y,
        'original_cam_halfwidth_mm': cam,
        'original_yoke_halfwidth_mm': yoke,
        'KEY_full_negative_offset_mm': -half,
        'cut_face_Y_mm': FACE_Y-half,
        'nominal_full_band_face_gap_mm': KEY_FACE_Y-half-(FACE_Y-half),
        'cut_box_XZ_padding_mm': EDGE_PADDING,
        'secondary_layer': {
            'measured_fixed_face_Y_mm': SECONDARY_FIXED_FACE_Y,
            'inferred_nominal_KEY_face_Y_mm': SECONDARY_KEY_FACE_Y_INFERRED,
            'inference': 'actual full-band Common minimum Y minus original negative rigid dq',
            'new_nominal_plane_measurement_executed': False,
            'measured_Z_range_mm': list(SECONDARY_Z_RANGE),
            'measured_R_X_strips_mm': [list(x) for x in SECONDARY_X_STRIPS],
            'nominal_face_gap_mm': SECONDARY_KEY_FACE_Y_INFERRED-SECONDARY_FIXED_FACE_Y,
            'full_band_penetration_before_this_cut_mm': half-(SECONDARY_KEY_FACE_Y_INFERRED-SECONDARY_FIXED_FACE_Y),
            'cut_face_Y_mm': secondary_cut_y,
            'cut_depth_from_measured_fixed_face_mm': SECONDARY_FIXED_FACE_Y-secondary_cut_y,
            'full_band_local_construction_gap_mm': SECONDARY_CONSTRUCTION_GAP,
            'construction_gap_is_manufacturing_tolerance': False},
        'parts': rows,
        'unchanged_per_side_slot_constraints': ['abs(dx_side)<=cam', 'abs(dx_side-dq_side)<=yoke'],
        'full_per_side_offset_projection_mm': {'dq': [-half, half], 'dx': [-cam, cam]},
        'full_per_side_slot_polytope_vertices': vertices,
        'left_and_right_controls_remain_independent': True,
        'rigid_motion': {'KEY': '(0,dq_side,0)',
                        'other_original_moving_bodies': '(side_sign*dx_side,0,0)'},
        'cut_coordinate_frame': 'frozen nominal STOW factory assembly',
        'other_pose_cut_placement_verified': False,
        'q_or_other_control_domain_removed': False,
        'contact_law_changed': False,
        'production_default_changed': False,
        'all_participant_names_retained': True,
        'continuous_backlash_domain_proved': False,
        'strength_or_tolerance_qualified': False,
        'physical_qualification': False,
        'manufacturing_go': False}


def apply(parts, assembly, output, sha):
    import cadquery as cq
    out = Path(output)
    out.mkdir()
    result = dict(parts)
    record = definition()
    changes = []
    for item in record['parts']:
        name = item['part']
        before = parts[name]
        tools = [assembly.box(box['lo_mm'], box['hi_mm']) for box in item['cut_boxes']]
        tool = tools[0] if len(tools) == 1 else cq.Compound.makeCompound(tools)
        after = before
        for cutter in tools:
            after = assembly.single(after.cut(cutter).clean())
        before_volume, after_volume = assembly.volume(before), assembly.volume(after)
        removed, added = assembly.volume(before.cut(after)), assembly.volume(after.cut(before))
        tool_removed = assembly.volume(before.intersect(tool))
        balance = before_volume-removed+added-after_volume
        if (not all(math.isfinite(value) for value in (removed, added, tool_removed, balance))
                or removed <= 0 or added > 1e-7 or abs(balance) > 1e-7
                or abs(removed-tool_removed) > 1e-7):
            raise ValueError('complete finite relief material accounting failed: '+name)
        if len(assembly.whole_material(after)[0]) != 1:
            raise ValueError('local relief disconnected or omitted actual material: '+name)
        exports = {}
        for kind, body in (('before', before), ('after', after), ('cut_envelope', tool)):
            path = out/(name+'-'+kind+'.step')
            cq.exporters.export(body, str(path))
            exports[kind] = {'path': str(path.relative_to(out.parent)), 'sha256': sha(path),
                             'volume_mm3': assembly.volume(body), 'bounds_mm': assembly.bounds(body),
                             'solid_count': len(assembly.whole_material(body)[0])}
        changes.append({'part': name, 'before_volume_mm3': before_volume,
                        'after_volume_mm3': after_volume, 'removed_mm3': removed, 'added_mm3': added,
                        'actual_tool_intersection_mm3': tool_removed, 'balance_error_mm3': balance,
                        'one_valid_positive_after_solid': True, 'exports': exports})
        result[name] = after
    if set(result) != set(parts):
        raise ValueError('candidate omitted an original participant')
    record['material_changes'] = changes
    record['unchanged_participant_names'] = sorted(set(parts)-{row['part'] for row in changes})
    return result, record
