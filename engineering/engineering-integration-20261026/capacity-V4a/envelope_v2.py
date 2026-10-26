"""Conservative straight-translation carriers, V2 research implementation.

No manufactured material is changed. A near-degenerate temporary sweep is
replaced by an outward carrier, not reoriented, discarded or assigned abs(V).
The original signed-solid and 1e-7 Common predicates remain authoritative.

Coverage: start/end solids and swept boundary faces cover the entire sweep.
For an ordinary planar face its native prism is used. For a nearly tangential
face its entire native bound, in that face's orthogonal frame, is expanded by
the complete translation interval and by GUARD. Extrusion/other curved faces
use a whole-face native geometric bound with the same interval extension.
These are supersets; their positive overlap never proves an actual collision.
Tiny nonzero translations are enlarged in BOTH directions along the same
line. The original segment is explicitly contained in that longer segment.
All returned regions must have valid topology and strictly positive signed
solid volume. Bounds use unmeshed OCCT geometry, not sampled vertices.

Floating point BRep bounds and Boolean operations remain numerical. This is
not a certified interval-arithmetic or independent-kernel proof.
"""
from __future__ import annotations

import math
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.gp import gp_Vec
import cadquery as cq
import product_assembly as p
from straight_envelope import single, whole_material
from translation_regions import sum_common_upper_bound

TOL = 1e-7
GUARD = 1e-5
MAX_REGIONS = 4096


def geometric_bounds(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, box, False, True)
    a, b, c, d, e, f = box.Get()
    vals = (a, d, b, e, c, f)
    if not all(math.isfinite(x) for x in vals):
        raise ValueError('finite geometric carrier bounds required')
    return vals


def outward_box(shape, vector, *, plane=None):
    """Enclose an entire face/solid sweep by interval extrema in one frame."""
    vector = cq.Vector(vector)
    local = shape if plane is None else plane.toLocalCoords(shape)
    if plane is not None:
        vector = cq.Vector(vector.dot(plane.xDir), vector.dot(plane.yDir),
                           vector.dot(plane.zDir))
    bound = geometric_bounds(local)
    lo = []; hi = []
    for i, step in enumerate(vector.toTuple()):
        lo.append(math.nextafter(bound[2*i]+min(0., step)-GUARD, -math.inf))
        hi.append(math.nextafter(bound[2*i+1]+max(0., step)+GUARD, math.inf))
    result = p.box(lo, hi)
    if plane is not None:
        result = single(result.transformShape(plane.rG))
    return result, {'bounds_local_mm': [*lo, *hi], 'padding_mm': GUARD,
                    'native_bounds_include_shape_tolerances': True,
                    'unmeshed_complete_geometry_bound': True,
                    'local_frame': plane is not None}


def regions(shape, vector, *, audit=None):
    single(shape)
    move = cq.Vector(vector)
    if not all(math.isfinite(x) for x in move.toTuple()):
        raise ValueError('finite displacement required')
    records = []
    if move.Length == 0:
        return [shape], {'translation_mm': move.toTuple(), 'region_count': 1,
                         'region_kinds': ['whole_start'], 'exact_zero_path': True}
    source = shape
    extension = None
    if move.Length < 2*GUARD:
        unit = move.normalized()
        source = shape.translate(unit.multiply(-GUARD))
        original_length = move.Length
        move = move.add(unit.multiply(2*GUARD))
        extension = {'original_length_mm': original_length,
                     'outward_each_end_mm': GUARD,
                     'source_shift_mm': unit.multiply(-GUARD).toTuple(),
                     'extended_translation_mm': move.toTuple(),
                     'original_segment_parameters_in_extended_segment':
                        [GUARD/(original_length+2*GUARD),
                         (GUARD+original_length)/(original_length+2*GUARD)]}
    out = [shape, single(shape.translate(cq.Vector(vector)))]
    kinds = ['whole_start', 'whole_end']
    if extension is not None:
        out.extend([source, single(source.translate(move))])
        kinds.extend(['extended_whole_start', 'extended_whole_end'])
    for index, face in enumerate(source.Faces()):
        kind = face.geomType()
        row = {'face_index': index, 'surface_type': kind}
        carrier = None
        if kind == 'PLANE':
            normal = face.normalAt()
            projection = normal.dot(move)
            row['normal_displacement_mm'] = projection
            if abs(projection) >= GUARD:
                prism = BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*move.toTuple()), True)
                try:
                    if not prism.IsDone():
                        raise ValueError('native face prism construction failed')
                    carrier = single(cq.Shape.cast(prism.Shape()))
                    row['method'] = 'native_complete_planar_face_prism'
                except Exception as exc:
                    row['native_prism_rejected'] = type(exc).__name__+': '+str(exc)
                    carrier = None
            if carrier is None:
                # Bound the complete trimmed face in its own plane. The padded
                # normal interval also contains an exactly tangential sweep.
                plane = cq.Plane(origin=face.Center(), normal=normal)
                carrier, detail = outward_box(face, move, plane=plane)
                row.update(method='whole_planar_face_local_interval_carrier', **detail)
        else:
            # This includes the real EXTRUSION counterexample and cylindrical
            # surfaces. No partial curve sampling or unsupported-face omission.
            carrier, detail = outward_box(face, move)
            row.update(method='whole_curved_face_world_interval_carrier', **detail)
        single(carrier)
        row['signed_volume_mm3'] = float(carrier.Volume())
        out.append(carrier)
        kinds.append(row['method']+'_'+str(index))
        records.append(row)
    if audit is not None:
        audit.append({'original_translation_mm': cq.Vector(vector).toTuple(),
                      'extended_path': extension, 'faces': records,
                      'source_signed_volume_mm3': shape.Volume(),
                      'region_count': len(out)})
    return out, {'translation_mm': move.toTuple(), 'region_count': len(out),
                 'region_kinds': kinds, 'complete_boundary_faces_included': True,
                 'extended_path': extension, 'new_method': 'all_boundary_carriers_v2',
                 'overlaps_allowed_sum_not_union_volume': True,
                 'complete_translation_not_pose_samples': True}


def translation_bounds(coefficients, domain):
    if len(coefficients) != len(domain) or not coefficients:
        raise ValueError('complete nonempty affine domain required')
    result = []
    for axis in range(3):
        terms = [(c[axis]*lo, c[axis]*hi) for c,(lo,hi) in zip(coefficients, domain)]
        if any(not math.isfinite(x) for pair in terms for x in pair):
            raise ValueError('finite coefficient/domain required')
        result.extend((math.fsum(min(t) for t in terms), math.fsum(max(t) for t in terms)))
    return result


def enclosure_regions(body, coefficients, domain, *, audit=None):
    active = [i for i,c in enumerate(coefficients) if any(c) and domain[i][1]>domain[i][0]]
    start = tuple(math.fsum(c[j]*interval[0] for c,interval in zip(coefficients,domain))
                  for j in range(3))
    pieces = [single(body.translate(start))]
    for i in active:
        c = coefficients[i]; lo,hi = domain[i]
        move = tuple(x*(hi-lo) for x in c)
        expanded = []
        for piece in pieces:
            expanded.extend(regions(piece, move, audit=audit)[0])
            if len(expanded)>MAX_REGIONS:
                raise ValueError('4096-region research cap exceeded')
        pieces = expanded
    return pieces


def _frame(a,b,coefficients,domain,*,frame_name,evidence_callback=None):
    """Original strict Common and upper-sum acceptance, with new carriers."""
    audit = []; region = None; index = None
    try:
        single(a);single(b)
        boxes = enclosure_regions(a,coefficients,domain,audit=audit)
        values = []; rows = []
        for index, region in enumerate(boxes):
            result = p.strict_common(region,b)
            value = result['common_mm3']; values.append(value)
            rows.append({'region_index':index, **result})
            upper = sum_common_upper_bound(values)
            if upper>TOL:
                evidence = evidence_callback(region,b,{'frame':frame_name,'region_index':index,
                    'strict_common':result,'recomputed_after_failure':False}) if evidence_callback else None
                return {'disposition':'unresolved_enclosure_overlap',
                        'method':'continuous_relative_affine_box_translation_enclosure',
                        'positive_enclosure_common_mm3':max(values),
                        'examined_region_common_sum_mm3':upper,
                        'regions_examined':len(values),'total_region_count':len(boxes),
                        'collision_proved':False,'v2_carrier_audit':audit,
                        'v2_region_checks':rows,'v2_retained_materials':evidence}
        return {'disposition':'clear','method':'continuous_relative_affine_box_translation_enclosure',
                'region_count':len(boxes),'maximum_region_common_mm3':max(values),
                'common_upper_bound_mm3':upper,'common_upper_bound_is_sum_not_union_volume':True,
                'v2_carrier_audit':audit,'v2_region_checks':rows}
    except Exception as exc:
        retained=None
        if evidence_callback is not None and region is not None:
            try:
                retained=evidence_callback(region,b,{'frame':frame_name,'region_index':index,
                    'error':type(exc).__name__+': '+str(exc),'recomputed_after_failure':True})
            except Exception as export_exc:
                retained={'retention_failed':type(export_exc).__name__+': '+str(export_exc)}
        return {'disposition':'unresolved_evaluation','error':type(exc).__name__+': '+str(exc),
                'collision_proved':False,'v2_carrier_audit':audit,'v2_retained_materials':retained}


def continuous_pair(a,b,coefficients,*,domain,evidence_callback=None):
    first=_frame(a,b,coefficients,domain,frame_name='initial',evidence_callback=evidence_callback)
    if first['disposition']=='clear':return first
    reverse=_frame(b,a,[[-x for x in v] for v in coefficients],domain,
                   frame_name='opposite',evidence_callback=evidence_callback)
    if reverse['disposition']=='clear':
        return {**reverse,'relative_reference_frame_reversed':True,
                'initial_reference_frame_result':first}
    return {**first,'opposite_reference_frame_result':reverse}
