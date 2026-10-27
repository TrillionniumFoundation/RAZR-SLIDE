"""Extend the preserved rectangle-only audit to exact orthogonal face trims.

The local thickness witnesses below concern selected whole-STEP segments only.
Every other analytic boundary surface is screened against each open segment.
They remain serialized-model certificates, not interval certificates for OCCT,
not an exhaustive global minimum and not material/process qualification.
"""
from __future__ import annotations
import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path
import time

import audit_current_step_faces as core

PARSER_SHA = 'a87db5585c5e98cc062810298443cf8b499c8105192803920b0fc4b8b20b78aa'


def exact_point_in_polygon(p, vertices):
    # All edge/vertex coordinates are partition breakpoints, so cell midpoints
    # cannot lie on an edge. The selected interior probes are checked likewise.
    crossings = 0
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if a[0] == b[0]:
            if p[0] == a[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]):
                raise ValueError('strict interior point is on polygon boundary')
            # The half-open crossing rule counts a shared vertex only once.
            if (a[1] > p[1]) != (b[1] > p[1]) and a[0] > p[0]:
                crossings += 1
        elif a[1] == b[1]:
            if p[1] == a[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]):
                raise ValueError('strict interior point is on polygon boundary')
        else:
            raise ValueError('nonorthogonal edge')
    return bool(crossings % 2)


def polygon_face(reader, row):
    if row['surface_type'] != 'PLANE' or len(row['bound_loops']) != 1:
        return None
    normal = row['surface_axis_direction']
    indices = [i for i, x in enumerate(normal) if x]
    if len(indices) != 1:
        return None
    axis = indices[0]
    uv = [i for i in range(3) if i != axis]
    loop_id = row['bound_loops'][0]['loop_id']
    loop = reader.get(loop_id, 'EDGE_LOOP')
    edges = [reader.edge(x) for x in core.references(loop[1])]
    if any(e['curve_type'] != 'LINE' or not e['endpoints_on_serialized_3D_line_exactly'] for e in edges):
        return None
    points = [e['start_mm'] for e in edges]
    if any(p[axis] != row['plane_origin_mm'][axis] for p in points):
        return None
    polygon = [tuple(p[i] for i in uv) for p in points]
    segments = list(zip(polygon, polygon[1:] + polygon[:1]))
    if any(sum(x != y for x, y in zip(a, b)) != 1 for a, b in segments):
        return None
    # Strict simple polygon: nonadjacent closed edges must not intersect.
    for i, (a, b) in enumerate(segments):
        for j, (c, d) in enumerate(segments):
            if j <= i or (j - i) in (1, len(segments) - 1):
                continue
            if all(max(min(a[k], b[k]), min(c[k], d[k])) <= min(max(a[k], b[k]), max(c[k], d[k])) for k in range(2)):
                raise ValueError('orthogonal trim is not a simple polygon')
    axes = [sorted({p[i] for p in polygon}) for i in range(2)]
    cells = []
    for i, j in itertools.product(range(len(axes[0])-1), range(len(axes[1])-1)):
        lo = (axes[0][i], axes[1][j]); hi = (axes[0][i+1], axes[1][j+1])
        middle = tuple((x+y)/2 for x, y in zip(lo, hi))
        if exact_point_in_polygon(middle, polygon):
            cells.append({'bounds_mm': [lo, hi], 'area_mm2': (hi[0]-lo[0])*(hi[1]-lo[1])})
    area = abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in segments))/2
    if area != sum((c['area_mm2'] for c in cells), F()):
        raise ValueError('polygon shoelace/coordinate-cell area disagreement')
    return {'face_id': row['face_id'], 'normal_axis_index': axis,
            'normal_axis': 'XYZ'[axis], 'plane_coordinate_mm': row['plane_origin_mm'][axis],
            'outward_sign': 1 if row['outward_plane_direction'][axis] > 0 else -1,
            'tangent_axes': uv, 'polygon_vertices_mm': polygon,
            'exact_area_mm2': area, 'coordinate_cells': cells,
            'independent_shoelace_and_partition_areas_equal': True}


def dot(a, b):
    return sum((x*y for x,y in zip(a,b)),F())


def screen_boundary(reader, face_rows, p, q, endpoint_faces):
    """Exclude all *infinite* analytic surfaces from the selected open chord.

    Passing is conservative for every trimmed face. A failure is unresolved,
    since its infinite plane/cylinder may intersect outside the actual trim.
    No endpoint-bound box is used to discard a curved face.
    """
    delta = tuple(y-x for x,y in zip(p,q))
    rows=[]
    for face in face_rows:
        fid=face['face_id']
        if fid in endpoint_faces:
            rows.append({'face_id':fid,'status':'selected_endpoint_surface','interior_surface_crossing_excluded':True})
            continue
        sid=face['surface_id']; kind=face['surface_type']
        if kind=='PLANE':
            n=face['surface_axis_direction']; o=face['plane_origin_mm']
            a=dot(n,tuple(x-y for x,y in zip(p,o)))
            b=dot(n,tuple(x-y for x,y in zip(q,o)))
            clear=a*b>=0 and (a!=0 or b!=0)
            rows.append({'face_id':fid,'surface_type':kind,'endpoint_signed_unnormalized_plane_values':[a,b],
                         'interior_surface_crossing_excluded':clear,
                         'status':'excluded_by_linear_same_sign' if clear else 'unresolved_infinite_plane_crosses_or_contains_chord'})
        elif kind=='CYLINDRICAL_SURFACE':
            s=reader.get(sid,kind); placement=reader.get(core.reference(s[1]),'AXIS2_PLACEMENT_3D')
            o=reader.coordinates(core.reference(placement[1]),'CARTESIAN_POINT')
            n=reader.coordinates(core.reference(placement[2]),'DIRECTION'); radius=F(s[2])
            if len(n)!=3 or dot(n,n)<=0 or radius<=0:
                raise ValueError('invalid serialized cylinder')
            w=tuple(x-y for x,y in zip(p,o)); nn=dot(n,n)
            A=nn*dot(delta,delta)-dot(delta,n)**2
            B=2*(nn*dot(w,delta)-dot(w,n)*dot(delta,n))
            C=nn*(dot(w,w)-radius**2)-dot(w,n)**2
            assert A>=0
            evaluation=[(F(),C),(F(1),A+B+C)]
            if A:
                critical=-B/(2*A)
                if 0<critical<1:
                    evaluation.append((critical,A*critical**2+B*critical+C))
            low=min(x[1] for x in evaluation);high=max(x[1] for x in evaluation)
            clear=low>0 or high<0
            rows.append({'face_id':fid,'surface_type':kind,'implicit_quadratic_ABC':[A,B,C],
                         'exact_extrema_values':evaluation,'interior_surface_crossing_excluded':clear,
                         'status':'excluded_by_quadratic_strict_sign' if clear else 'unresolved_infinite_cylinder_may_intersect_chord'})
        else:
            rows.append({'face_id':fid,'surface_type':kind,'interior_surface_crossing_excluded':False,'status':'unsupported_surface_retained'})
    return {'all_whole_boundary_faces_screened':len(rows)==len(face_rows),
            'selected_endpoint_face_count':len(endpoint_faces),
            'other_analytic_surface_interior_crossings_excluded':all(r['interior_surface_crossing_excluded'] for r in rows),
            'unresolved_face_ids':[r['face_id'] for r in rows if not r['interior_surface_crossing_excluded']],
            'rows':rows}


def selected_chord(reader, face_rows, polygons, side, label, axis, ends, other_coordinates):
    ends=sorted(F(str(x)) for x in ends)
    uv=[i for i in range(3) if i!=axis]
    witnesses=[]
    for coordinate, outward in zip(ends,(-1,1)):
        eligible=[f for f in polygons if f['normal_axis_index']==axis and f['plane_coordinate_mm']==coordinate and f['outward_sign']==outward and exact_point_in_polygon(tuple(other_coordinates),f['polygon_vertices_mm'])]
        witnesses.append(eligible)
    row={'label':label,'side':side,'axis':'XYZ'[axis],'plane_coordinates_mm':ends,
         'specified_interior_other_coordinates_mm':other_coordinates,
         'separation_mm':ends[1]-ends[0],
         'endpoint_trim_candidates':[len(x) for x in witnesses],
         'serialized_face_separation_and_open_chord_exclusion_proved':False,
         'material_interior_interpretation_conditional_on_exact_valid_oriented_boundary':True,
         'exact_serialized_closed_solid_validity_proved':False,
         'whole_material_chord_unconditionally_proved':False,
         'global_minimum_wall_proved':False,'native_interval_enclosure_proved':False}
    if any(len(x)!=1 for x in witnesses):
        row['status']='unresolved_endpoint_trim_not_exactly_supported'
        return row
    points=[]
    for coordinate in ends:
        p=[F(),F(),F()];p[axis]=coordinate
        for i,x in zip(uv,other_coordinates):p[i]=x
        points.append(tuple(p))
    endpoint_ids=[x[0]['face_id'] for x in witnesses]
    screen=screen_boundary(reader,face_rows,*points,endpoint_ids)
    row.update({'endpoint_face_ids':endpoint_ids,'whole_boundary_screen':screen,'endpoints_mm':points,
                'outward_endpoint_normals_have_opposite_required_signs':True})
    row['serialized_face_separation_and_open_chord_exclusion_proved']=screen['other_analytic_surface_interior_crossings_excluded']
    row['status']='serialized_endpoint_face_separation_and_open_chord_surface_exclusion_proved' if row['serialized_face_separation_and_open_chord_exclusion_proved'] else 'unresolved_other_boundary_surface_could_intersect'
    return row


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--step-dir',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();started=time.monotonic()
    parser_raw=Path(core.__file__).read_bytes()
    if hashlib.sha256(parser_raw).hexdigest()!=PARSER_SHA:raise ValueError('preserved exact parser source changed')
    bodies={}
    for name,(size,digest) in core.EXPECTED.items():
        raw=(args.step_dir/name).read_bytes()
        if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('frozen complete STEP differs')
        reader=core.Reader(raw);faces=[reader.face(fid) for fid in reader.face_ids]
        polygons=[p for f in faces if (p:=polygon_face(reader,f)) is not None]
        chords=[]
        if name.endswith('_KEY.step'):
            sign=-1 if name.startswith('L') else 1
            for label,axis,ends,other in [
                ('inherited_yoke_tab_X',0,[sign*F('13.2'),sign*F('13.45')],[F(20),F('4.2')]),
                ('inboard_bridge_leg_X',0,[sign*F('16.96'),sign*F('17.34')],[F(10),F('4.2')]),
                ('outboard_bridge_leg_X',0,[sign*F('18.52'),sign*F('18.90')],[F(10),F('4.2')]),
                ('inherited_yoke_tab_Z',2,[F('4.05'),F('4.35')],[sign*F('13.325'),F(20)]),
            ]:chords.append(selected_chord(reader,faces,polygons,name[0],label,axis,ends,other))
        bodies[name[:-5]]={'whole_STEP_sha256':digest,'whole_STEP_bytes':size,
            'complete_face_count':len(faces),'exact_supported_simple_orthogonal_trim_count':len(polygons),
            'unresolved_face_ids_for_this_trim_method':[f['face_id'] for f in faces if f['face_id'] not in {p['face_id'] for p in polygons}],
            'orthogonal_trim_partitions':polygons,'selected_local_chords':chords}
    report={'schema':'razr-current-K3-local-serialized-boundary-separation-audit-v2',
            'audit_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'preserved_complete_face_inventory_parser_sha256':PARSER_SHA,
            'preserved_original_rectangle_only_audit_superseded_or_overwritten':False,
            'source_artifact_id':12633972884,'source_run_id':40285103942,
            'all_arithmetic_exact_for_serialized_decimal_coordinates':True,
            'native_tolerances_used_to_snap_discrepancies':False,'native_geometry_kernel_used':False,
            'bodies':bodies,
            'whole_solid_validity_orientation_precondition':'native validity/orientation passed within the original kernel tolerances; exact serialized decimal surfaces forming a valid oriented closed solid are NOT proved, so material-interior inference remains conditional',
            'native_validity_implies_exact_serialized_closed_solid_validity':False,
            'exact_boundary_separation_count':sum(c['serialized_face_separation_and_open_chord_exclusion_proved'] for b in bodies.values() for c in b['selected_local_chords']),
            'attempted_chord_count':sum(len(b['selected_local_chords']) for b in bodies.values()),
            'global_minimum_wall_metric_defined':False,'global_minimum_wall_measured':False,
            'global_minimum_wall_qualified':False,'native_geometry_interval_enclosure_proved':False,
            'complete_continuous_motion_proved':False,'physical_allowed_domain_proved':False,
            'strength_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
            'elapsed_seconds':time.monotonic()-started}
    args.output.write_text(json.dumps(core.as_json(report),indent=2)+'\n')
    print(json.dumps({'output_name':args.output.name,'bytes':args.output.stat().st_size,
        'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'attempted_chords':report['attempted_chord_count'],
        'exact_endpoint_separation_and_open_chord_exclusions':report['exact_boundary_separation_count'],
        'body_results':{k:[{'label':c['label'],'separation':float(c['separation_mm']),'status':c['status'],'unresolved_surfaces':c.get('whole_boundary_screen',{}).get('unresolved_face_ids')} for c in v['selected_local_chords']] for k,v in bodies.items()},
        'native_executed':False,'global_minimum_wall_qualified':False}))


if __name__=='__main__':main()
