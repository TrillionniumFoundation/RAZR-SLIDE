"""Read-only STEP topology and exact serialized rectangular-face audit.

This is a deliberately restricted ISO-10303-21 reader, not a geometry kernel.
All ADVANCED_FACE records in each whole-body CLOSED_SHELL are inventoried.
Unsupported, nonrectangular, curved and nonexactly axis-aligned surfaces remain
explicitly unresolved. Opposed-face separations are not global wall thickness.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path
import re
import time

EXPECTED = {
    'A_BACK_PANEL.step': (937636, '90f035bc9a033f467f17259e449786ae9519a4a4ad5f08db784c27551e26bd32'),
    'L_KEY.step': (336902, '348e68445442c0286dd0d531dc3c2d8fb661f38b0f68810e81252ab216a24179'),
    'R_KEY.step': (343291, '253b91c1f7858d667aeece23b64a0806f092ff25d8d26519f63181522d715494'),
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def as_json(x):
    if isinstance(x, F):
        return {'exact_rational': str(x), 'float_display_only': float(x)}
    if isinstance(x, dict):
        return {k: as_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [as_json(v) for v in x]
    return x


def split_fields(text):
    fields, start, depth, string = [], 0, 0, False
    i = 0
    while i < len(text):
        c = text[i]
        if c == "'":
            if string and i + 1 < len(text) and text[i + 1] == "'":
                i += 2
                continue
            string = not string
        elif not string:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            elif c == ',' and depth == 0:
                fields.append(text[start:i].strip())
                start = i + 1
        if depth < 0:
            raise ValueError('unbalanced entity arguments')
        i += 1
    if depth or string:
        raise ValueError('unterminated entity arguments')
    fields.append(text[start:].strip())
    return fields


def reference(text):
    if not re.fullmatch(r'#[0-9]+', text):
        raise ValueError('direct STEP reference required')
    return int(text[1:])


def references(text):
    if not text.startswith('(') or not text.endswith(')'):
        raise ValueError('reference aggregate required')
    return [reference(x) for x in split_fields(text[1:-1])]


def logical(text):
    if text not in ('.T.', '.F.'):
        raise ValueError('explicit STEP boolean required')
    return text == '.T.'


class Reader:
    def __init__(self, raw):
        text = raw.decode('ascii')
        self.entities = {}
        # These exact frozen files have no entity-argument string semicolons.
        for m in re.finditer(r'(?m)^#([0-9]+)\s*=\s*(.*?);', text, re.S):
            key, payload = int(m.group(1)), m.group(2).strip()
            if key in self.entities:
                raise ValueError('duplicate entity id')
            simple = re.fullmatch(r'([A-Z][A-Z0-9_]*)\s*\((.*)\)', payload, re.S)
            if simple:
                kind, fields = simple.group(1), split_fields(simple.group(2))
            else:
                if not payload.startswith('('):
                    raise ValueError('unparsed STEP entity')
                kind, fields = 'COMPLEX', []
            self.entities[key] = (kind, fields, payload)
        self.counts = Counter(e[0] for e in self.entities.values())
        if self.counts['MANIFOLD_SOLID_BREP'] != 1 or self.counts['CLOSED_SHELL'] != 1:
            raise ValueError('one complete manifold solid/shell required')
        forbidden = ('MAPPED_ITEM', 'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION',
                     'CONTEXT_DEPENDENT_SHAPE_REPRESENTATION', 'BREP_WITH_VOIDS')
        if any(self.counts[k] for k in forbidden):
            raise ValueError('unresolved instance transform or extra shell')
        if len(re.findall(r'LENGTH_UNIT\s*\(\s*\)\s+NAMED_UNIT\s*\(\s*\*\s*\)\s+SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)', text)) != 1:
            raise ValueError('explicit one millimetre length unit required')
        solid_id = next(k for k, e in self.entities.items() if e[0] == 'MANIFOLD_SOLID_BREP')
        solid = self.get(solid_id, 'MANIFOLD_SOLID_BREP')
        self.shell_id = reference(solid[1])
        shell = self.get(self.shell_id, 'CLOSED_SHELL')
        self.face_ids = references(shell[1])
        if len(set(self.face_ids)) != len(self.face_ids):
            raise ValueError('duplicate shell face')
        all_faces = {k for k, e in self.entities.items() if e[0] == 'ADVANCED_FACE'}
        if set(self.face_ids) != all_faces:
            raise ValueError('unaccounted ADVANCED_FACE outside complete shell')
        self.solid_id = solid_id

    def get(self, key, kind=None):
        item = self.entities[key]
        if kind and item[0] != kind:
            raise ValueError('entity type mismatch: expected ' + kind)
        return item[1]

    def coordinates(self, key, kind):
        fields = self.get(key, kind)
        text = fields[1]
        if not text.startswith('(') or not text.endswith(')'):
            raise ValueError('coordinate aggregate required')
        return tuple(F(x) for x in split_fields(text[1:-1]))

    def point(self, vertex):
        return self.coordinates(reference(self.get(vertex, 'VERTEX_POINT')[1]), 'CARTESIAN_POINT')

    def underlying_curve(self, key):
        seen = set()
        while self.entities[key][0] in ('SURFACE_CURVE', 'SEAM_CURVE'):
            if key in seen:
                raise ValueError('curve-reference cycle')
            seen.add(key)
            key = reference(self.get(key)[1])
        return key, self.entities[key][0]

    def edge(self, oriented):
        args = self.get(oriented, 'ORIENTED_EDGE')
        if args[1:3] != ['*', '*']:
            raise ValueError('unsupported explicit oriented endpoints')
        edge_id = reference(args[3])
        edge = self.get(edge_id, 'EDGE_CURVE')
        a, b = reference(edge[1]), reference(edge[2])
        if not logical(args[4]):
            a, b = b, a
        curve_id, kind = self.underlying_curve(reference(edge[3]))
        p, q = self.point(a), self.point(b)
        result = {'oriented_edge_id': oriented, 'edge_curve_id': edge_id,
                  'start_vertex_id': a, 'end_vertex_id': b,
                  'start_mm': p, 'end_mm': q, 'curve_id': curve_id, 'curve_type': kind}
        if kind == 'LINE':
            line = self.get(curve_id, 'LINE')
            origin = self.coordinates(reference(line[1]), 'CARTESIAN_POINT')
            vec = self.get(reference(line[2]), 'VECTOR')
            direction = self.coordinates(reference(vec[1]), 'DIRECTION')
            if len(direction) != 3 or not any(direction) or F(vec[2]) == 0:
                raise ValueError('degenerate line')
            def on_line(point):
                delta = tuple(x-y for x,y in zip(point, origin))
                return all(delta[i] * direction[j] == delta[j] * direction[i]
                           for i,j in itertools.combinations(range(3), 2))
            result['endpoints_on_serialized_3D_line_exactly'] = on_line(p) and on_line(q)
        return result

    def face(self, fid):
        f = self.get(fid, 'ADVANCED_FACE')
        sid = reference(f[2])
        kind = self.entities[sid][0]
        bounds = []
        edges = []
        for bound_id in references(f[1]):
            bound_kind = self.entities[bound_id][0]
            if bound_kind not in ('FACE_BOUND', 'FACE_OUTER_BOUND'):
                raise ValueError('unsupported face-bound type')
            b = self.get(bound_id)
            loop_id = reference(b[1])
            loop = self.get(loop_id, 'EDGE_LOOP')
            group = [self.edge(x) for x in references(loop[1])]
            connected = all(group[i]['end_vertex_id'] == group[(i+1) % len(group)]['start_vertex_id']
                            for i in range(len(group)))
            if not connected:
                raise ValueError('topological edge loop is not closed and ordered')
            bounds.append({'bound_id': bound_id, 'kind': bound_kind, 'loop_id': loop_id,
                           'orientation': logical(b[2]), 'edge_count': len(group), 'closed_ordered': True})
            edges.extend(group)
        points = [e['start_mm'] for e in edges]
        bbox = [[min(x[i] for x in points) for i in range(3)],
                [max(x[i] for x in points) for i in range(3)]]
        row = {'face_id': fid, 'surface_id': sid, 'surface_type': kind,
               'same_sense': logical(f[3]), 'bound_loops': bounds,
               'edge_type_counts': dict(Counter(e['curve_type'] for e in edges)),
               'endpoint_bounds_only_not_curve_bounds_mm': bbox,
               'entity_expression_sha256': sha(self.entities[fid][2].encode()),
               'serialized_rectangular_face': None,
               'unresolved_reason': None}
        if kind != 'PLANE':
            row['unresolved_reason'] = 'nonplanar_surface'
            return row
        plane = self.get(sid, 'PLANE')
        placement = self.get(reference(plane[1]), 'AXIS2_PLACEMENT_3D')
        origin = self.coordinates(reference(placement[1]), 'CARTESIAN_POINT')
        normal = self.coordinates(reference(placement[2]), 'DIRECTION')
        row['plane_origin_mm'] = origin
        row['surface_axis_direction'] = normal
        row['outward_plane_direction'] = tuple(x if row['same_sense'] else -x for x in normal)
        axes = [i for i,x in enumerate(normal) if x]
        if len(axes) != 1:
            row['unresolved_reason'] = 'plane_normal_not_exactly_coordinate_axis_in_serialized_data'
            return row
        axis = axes[0]
        if len(bounds) != 1:
            row['unresolved_reason'] = 'multiple_bound_loops'
            return row
        if any(e['curve_type'] != 'LINE' or not e['endpoints_on_serialized_3D_line_exactly'] for e in edges):
            row['unresolved_reason'] = 'curved_edge_or_exact_line_endpoint_inconsistency'
            return row
        if any(p[axis] != origin[axis] for p in points):
            row['unresolved_reason'] = 'serialized_vertices_not_exactly_on_axis_plane'
            return row
        uv = [i for i in range(3) if i != axis]
        lo = [bbox[0][i] for i in uv]
        hi = [bbox[1][i] for i in uv]
        if any(a >= b for a,b in zip(lo,hi)):
            row['unresolved_reason'] = 'degenerate_projected_region'
            return row
        # Every edge must be one exact perimeter interval; these intervals must
        # form each full rectangle side once. Concave/holey polygons are rejected.
        sides = {(i,j): [] for i in range(2) for j in range(2)}
        for e in edges:
            p, q = ([e['start_mm'][i] for i in uv], [e['end_mm'][i] for i in uv])
            varying = [i for i in range(2) if p[i] != q[i]]
            if len(varying) != 1:
                row['unresolved_reason'] = 'projected_edge_not_axis_rectangle_perimeter'
                return row
            i = varying[0]; j = 1-i
            if p[j] not in (lo[j], hi[j]):
                row['unresolved_reason'] = 'projected_edge_not_on_rectangle_boundary'
                return row
            sides[(j, 0 if p[j] == lo[j] else 1)].append(tuple(sorted((p[i],q[i]))))
        for (constant_axis, side), intervals in sides.items():
            intervals.sort()
            varying = 1-constant_axis
            if not intervals or intervals[0][0] != lo[varying] or intervals[-1][1] != hi[varying] or any(a[1] != b[0] for a,b in zip(intervals,intervals[1:])):
                row['unresolved_reason'] = 'rectangle_perimeter_interval_coverage_failed'
                return row
        row['serialized_rectangular_face'] = {
            'normal_axis': 'XYZ'[axis], 'normal_axis_index': axis,
            'plane_coordinate_mm': origin[axis],
            'outward_sign': 1 if row['outward_plane_direction'][axis] > 0 else -1,
            'tangent_axes': ['XYZ'[i] for i in uv],
            'tangent_bounds_mm': [lo, hi], 'area_mm2': (hi[0]-lo[0])*(hi[1]-lo[1]),
            'whole_loop_exact_rectangle': True,
        }
        return row


def separated_rectangles(rows):
    result = []
    rectangles = [r for r in rows if r['serialized_rectangular_face']]
    for a,b in itertools.combinations(rectangles,2):
        x, y = a['serialized_rectangular_face'], b['serialized_rectangular_face']
        if x['normal_axis'] != y['normal_axis']:
            continue
        if x['plane_coordinate_mm'] > y['plane_coordinate_mm']:
            a,b,x,y = b,a,y,x
        gap = y['plane_coordinate_mm'] - x['plane_coordinate_mm']
        if gap <= 0 or x['outward_sign'] != -1 or y['outward_sign'] != 1:
            continue
        lo = [max(x['tangent_bounds_mm'][0][i],y['tangent_bounds_mm'][0][i]) for i in range(2)]
        hi = [min(x['tangent_bounds_mm'][1][i],y['tangent_bounds_mm'][1][i]) for i in range(2)]
        if any(lo[i] >= hi[i] for i in range(2)):
            continue
        result.append({'lower_face_id': a['face_id'], 'upper_face_id': b['face_id'],
                       'normal_axis': x['normal_axis'], 'plane_coordinates_mm': [x['plane_coordinate_mm'],y['plane_coordinate_mm']],
                       'opposed_plane_separation_mm': gap,
                       'projected_rectangular_overlap_mm': [lo, hi],
                       'projected_overlap_area_mm2': (hi[0]-lo[0])*(hi[1]-lo[1]),
                       'intervening_whole_material_verified': False,
                       'qualified_minimum_wall': False})
    return sorted(result,key=lambda p:(p['opposed_plane_separation_mm'],p['lower_face_id'],p['upper_face_id']))


def run(root, output):
    started=time.monotonic()
    bodies={}
    for name,(size,digest) in EXPECTED.items():
        raw=(root/name).read_bytes()
        if len(raw)!=size or sha(raw)!=digest:
            raise ValueError('immutable complete whole-body STEP differs: '+name)
        reader=Reader(raw)
        faces=[reader.face(fid) for fid in reader.face_ids]
        pairs=separated_rectangles(faces)
        known={}
        side=-1 if name=='L_KEY.step' else 1
        if name.endswith('_KEY.step'):
            candidates=[p for p in pairs if p['normal_axis']=='X'
                and p['plane_coordinates_mm']==sorted([side*F('13.2'),side*F('13.45')])]
            known['inherited_yoke_tab_0p25_X_separation']=candidates
            known['new_bridge_0p38_X_separations']=[p for p in pairs if p['normal_axis']=='X' and p['opposed_plane_separation_mm']==F('.38') and any(p['plane_coordinates_mm']==sorted([side*F(a),side*F(b)]) for a,b in [('16.96','17.34'),('18.52','18.90')])]
        bodies[name[:-5]]={
            'whole_STEP_identity':{'bytes':size,'sha256':digest},
            'solid_id':reader.solid_id,'closed_shell_id':reader.shell_id,
            'complete_face_count':len(faces),'all_ADVANCED_FACE_entities_in_exact_one_shell':True,
            'surface_type_counts':dict(Counter(f['surface_type'] for f in faces)),
            'exact_serialized_axis_rectangle_count':sum(f['serialized_rectangular_face'] is not None for f in faces),
            'unresolved_face_reason_counts':dict(Counter(f['unresolved_reason'] for f in faces if f['unresolved_reason'])),
            'faces':faces,'all_opposed_axis_rectangle_pairs':pairs,
            'minimum_of_this_restricted_pair_catalogue_mm':min((p['opposed_plane_separation_mm'] for p in pairs),default=None),
            'source_feature_correspondences':known,
            'native_geometry_kernel_used':False,'global_minimum_wall_proved':False,
        }
    result={
        'schema':'razr-current-K3-complete-STEP-face-inventory-and-restricted-separations-v1',
        'execution_kind':'pure_STEP_serialized_entities_exact_rational_no_native',
        'scientific_input_artifact_id':12633972884,'scientific_input_run_id':40285103942,
        'scientific_input_ZIP_sha256':'bd237005fcb5749eacf7592e71256b4128e5b0e00fbd260f5252b24bbc1bb0e1',
        'scientific_input_pose':'stow_tabs_3','key_q_mm':[0,0],
        'bodies':bodies,'complete_face_total':sum(b['complete_face_count'] for b in bodies.values()),
        'all_faces_retained_even_if_not_supported':True,
        'boundary_vertices_and_analytic_planes_read_from_original_STEP':True,
        'serialized_decimal_numbers_are_exact_rationals_for_this_audit':True,
        'input_STEP_numbers_are_not_interval_enclosures_of_original_kernel_coordinates':True,
        'native_tolerances_were_not_used_to_snap_or_erase_serialized_discrepancies':True,
        'whole_body_validity_and_material_identity_reused_from_original_native_evidence_not_recomputed':True,
        'global_wall_definition':None,
        'remaining_requirements':[
            'define functional/manufacturing wall metric, edge exclusions and sourced minimum rule',
            'verify interior material segments, trimmed curved faces and every unresolved planar face',
            'native independent readback of wall/section constructions with topology and errors retained',
            'current material/process/tolerance/load inputs and current-geometry FE qualification',
        ],
        'global_minimum_wall_measured':False,'global_minimum_wall_qualified':False,
        'strength_qualified':False,'physical_allowed_domain_proved':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
        'elapsed_seconds':time.monotonic()-started,
    }
    output.write_text(json.dumps(as_json(result),indent=2)+'\n')
    print(json.dumps({'output_name':output.name,'bytes':output.stat().st_size,'sha256':sha(output.read_bytes()),
        'complete_faces':result['complete_face_total'],
        'bodies':{k:{'faces':v['complete_face_count'],'exact_rectangles':v['exact_serialized_axis_rectangle_count'],
                     'restricted_pairs':len(v['all_opposed_axis_rectangle_pairs']),
                     'inherited_tab_pair_count':len(v['source_feature_correspondences'].get('inherited_yoke_tab_0p25_X_separation',[]))} for k,v in bodies.items()},
        'native_executed':False,'global_wall_qualified':False}))


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--step-dir',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    run(args.step_dir,args.output)
