"""Conservative finite straight envelope for planar/cylindrical solid boundaries.

Forward planar faces are extruded with their inner wires. Each cylindrical
face is enclosed by its finite full cylindrical carrier; sweeping that carrier
may add material not in the true sweep. Therefore clearance can certify only
nominal non-interference of this subset, while positive overlap may be a
conservative rejection. All non-planar/non-cylindrical surfaces are refused.
"""
from __future__ import annotations
import math
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

TOL = 1e-7


def whole_material(shape, *, empty=False):
    leaves = []
    def visit(node):
        if not node.isValid():
            raise ValueError('invalid topology')
        kind = node.ShapeType()
        if kind == 'Solid':
            v = float(node.Volume())
            if not math.isfinite(v) or v <= 0:
                raise ValueError('nonpositive signed solid')
            leaves.append(node)
        elif kind in ('Compound', 'CompSolid'):
            kids = list(node)
            if not kids and not empty:
                raise ValueError('empty topology')
            for child in kids:
                visit(child)
        else:
            raise ValueError('free non-solid topology: '+kind)
    visit(shape)
    total = sum(s.Volume() for s in leaves)
    raw = float(shape.Volume())
    if not math.isfinite(raw) or raw < 0 or abs(total-raw) > TOL or (not leaves and not empty):
        raise ValueError('whole signed volume mismatch')
    return leaves, raw


def single(shape):
    if len(whole_material(shape)[0]) != 1:
        raise ValueError('one complete positive solid required')
    return shape


def fuse(parts):
    result = parts[0]
    for p in parts[1:]:
        single(p); result = result.fuse(p)
    return single(result.clean())


def swept_cylinder(base, axis, radius, height, move):
    """Exact swept volume of a complete cylinder for axial/orthogonal motion."""
    if not all(math.isfinite(v) for v in (*base.toTuple(), *axis.toTuple(), radius, height, *move.toTuple())):
        raise ValueError('nonfinite cylinder input')
    if radius <= 0 or height <= 0 or abs(axis.Length-1) > 1e-9 or move.Length <= 1e-12:
        raise ValueError('invalid cylinder or displacement')
    dot = axis.dot(move)
    perpendicular = move.sub(axis.multiply(dot))
    if perpendicular.Length <= 1e-10:
        return single(cq.Solid.makeCylinder(radius, height+abs(dot), base.add(axis.multiply(min(0., dot))), axis)), 'axial'
    if abs(dot) > 1e-10:
        raise ValueError('oblique cylinder motion unsupported; not silently approximated')
    tangent = axis.cross(move.normalized()).normalized().multiply(radius)
    points = [base.add(tangent), base.sub(tangent), base.add(move).sub(tangent), base.add(move).add(tangent)]
    face_wire = cq.Wire.makePolygon(points, close=True)
    bridge = cq.Solid.extrudeLinear(face_wire, [], axis.multiply(height))
    first = cq.Solid.makeCylinder(radius, height, base, axis)
    last = first.translate(move)
    return fuse([first, last, bridge]), 'orthogonal_capsule'


def envelope(shape, vector):
    single(shape)
    move = cq.Vector(vector)
    if not all(math.isfinite(v) for v in move.toTuple()) or move.Length <= 1e-12:
        raise ValueError('finite nonzero straight translation required')
    parts = [shape]; planes = []; cylinders = []
    for index, face in enumerate(shape.Faces()):
        kind = face.geomType()
        if kind == 'PLANE':
            if face.normalAt().dot(move) > 1e-12:
                prism = single(cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), move))
                parts.append(prism); planes.append({'face_index': index, 'volume_mm3': prism.Volume()})
        elif kind == 'CYLINDER':
            adaptor = BRepAdaptor_Surface(face.wrapped)
            cyl = adaptor.Cylinder(); d = cyl.Axis().Direction()
            axis = cq.Vector(d.X(), d.Y(), d.Z()); point = cyl.Location()
            v0, v1 = adaptor.FirstVParameter(), adaptor.LastVParameter()
            if not all(math.isfinite(v) for v in (v0,v1)) or v1 <= v0:
                raise ValueError('finite cylindrical carrier not available')
            base = cq.Vector(point.X(),point.Y(),point.Z()).add(axis.multiply(v0))
            swept, method = swept_cylinder(base, axis, cyl.Radius(), v1-v0, move)
            parts.append(swept); cylinders.append({'face_index':index,'axis':axis.toTuple(),'radius_mm':cyl.Radius(),'height_mm':v1-v0,'method':method,'carrier_swept_volume_mm3':swept.Volume()})
        else:
            raise ValueError('unsupported boundary type: '+kind)
    result = fuse(parts)
    if whole_material(shape.cut(result), empty=True)[1] > TOL or whole_material(shape.translate(move).cut(result), empty=True)[1] > TOL:
        raise ValueError('envelope loses endpoint material')
    return result, {'translation_mm':move.toTuple(),'planar_prisms':planes,'cylindrical_carriers':cylinders,
        'source_volume_mm3':shape.Volume(),'envelope_volume_mm3':result.Volume(),
        'construction':'initial solid plus forward planar-face prisms and swept full cylindrical carriers',
        'conservative_superset_not_exact_for_partial_or_inner_cylinders':bool(cylinders),
        'not_discrete_pose_union':True,'toleranced_or_physical_qualification':False,'manufacturing_go':False}
