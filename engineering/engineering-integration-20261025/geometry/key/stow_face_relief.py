"""Explicit research cuts at the four reproduced STOW KEY interference faces.

No production default or contact law is modified. Coordinates come from the
actual baseline positive Common solids, and the relief depth is the original
coupled-groove full KEY offset band. Strength and tolerances remain unqualified.
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


def definition():
    cam = (.425-.4)*math.hypot(1., 12./79.75)
    yoke = (.425-.4)*math.sqrt(2.)
    half = cam+yoke
    rows = []
    for side in 'LR':
        for role, strips in POSITIVE_X_STRIPS.items():
            boxes = []
            for lo, hi in strips:
                x0, x1 = (lo, hi) if side == 'R' else (-hi, -lo)
                boxes.append({'lo_mm': [x0-EDGE_PADDING, FACE_Y-half, Z_RANGE[0]-EDGE_PADDING],
                              'hi_mm': [x1+EDGE_PADDING, KEY_FACE_Y, Z_RANGE[1]+EDGE_PADDING]})
            rows.append({'part': side+'_'+role, 'cut_boxes': boxes})
    return {'schema': 'razr-STOW-local-face-relief-research-20261025-v1',
            'original_native_face_Y_mm': FACE_Y, 'original_KEY_face_Y_mm': KEY_FACE_Y,
            'original_nominal_face_gap_mm': KEY_FACE_Y-FACE_Y,
            'original_cam_halfwidth_mm': cam, 'original_yoke_halfwidth_mm': yoke,
            'KEY_full_negative_offset_mm': -half, 'cut_face_Y_mm': FACE_Y-half,
            'nominal_full_band_face_gap_mm': KEY_FACE_Y-half-(FACE_Y-half),
            'cut_box_XZ_padding_mm': EDGE_PADDING, 'parts': rows,
            'control_domain': {'dq_mm': [-half, 0.], 'dx_mm': [-cam, cam],
                               'coupled_constraints': ['abs(dx)<=cam', 'abs(dx-dq)<=yoke']},
            'q_or_other_control_domain_removed': False, 'contact_law_changed': False,
            'production_default_changed': False, 'all_participant_names_retained': True,
            'strength_or_tolerance_qualified': False, 'manufacturing_go': False}


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
