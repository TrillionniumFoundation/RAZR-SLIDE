"""Read-only complete native axis-box inventory. No geometric acceptance rules."""
import hashlib
from fractions import Fraction
from pathlib import Path
from OCP.BinTools import BinTools
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepGProp import BRepGProp
from OCP.BRepTools import BRepTools
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Shape, TopoDS_Iterator
from OCP.TopTools import TopTools_IndexedMapOfShape


def enum(value):
    return str(value).split('.')[-1]


def exact(value):
    return str(Fraction(float(value)))


def xyz(value):
    return [exact(value.X()), exact(value.Y()), exact(value.Z())]


def xy(value):
    return [exact(value.X()), exact(value.Y())]


def identity(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': digest}


def read_binary(path):
    shape = TopoDS_Shape()
    if not BinTools.Read_s(shape, str(path)):
        raise ValueError('native binary read failed')
    return shape


def write_binary(shape, path):
    if not BinTools.Write_s(shape, str(path)):
        raise ValueError('native binary write failed')
    return identity(path)


def unique(shape, kind):
    mapping = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, mapping)
    return mapping


def children(shape):
    iterator = TopoDS_Iterator(shape)
    result = []
    while iterator.More():
        result.append(enum(iterator.Value().ShapeType()))
        iterator.Next()
    return result


def metrics(shape):
    if shape.IsNull():
        return {'null': True}
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    counts = {}
    for name, kind in [('solids', TopAbs_SOLID), ('shells', TopAbs_SHELL), ('faces', TopAbs_FACE),
                       ('wires', TopAbs_WIRE), ('edges', TopAbs_EDGE), ('vertices', TopAbs_VERTEX)]:
        counts[name] = unique(shape, kind).Extent()
    infinity = None
    if counts['solids']:
        classifier = BRepClass3d_SolidClassifier(shape)
        classifier.PerformInfinitePoint(0.0)
        infinity = enum(classifier.State())
    return {'null': False, 'shape_type': enum(shape.ShapeType()), 'orientation': enum(shape.Orientation()),
            'native_valid': BRepCheck_Analyzer(shape).IsValid(), 'signed_volume_float': props.Mass(),
            'infinity_state_at_tolerance_zero': infinity, 'counts': counts,
            'root_children': children(shape), 'location_identity': shape.Location().IsIdentity()}


def inventory(shape):
    result = {'metrics': metrics(shape), 'vertices': [], 'edges': [], 'faces': []}
    vertices = unique(shape, TopAbs_VERTEX)
    edges = unique(shape, TopAbs_EDGE)
    faces = unique(shape, TopAbs_FACE)
    for index in range(1, vertices.Extent() + 1):
        vertex = TopoDS.Vertex_s(vertices.FindKey(index))
        result['vertices'].append({'id': index, 'point_exact': xyz(BRep_Tool.Pnt_s(vertex)),
                                   'tolerance_exact': exact(BRep_Tool.Tolerance_s(vertex)),
                                   'location_identity': vertex.Location().IsIdentity()})
    for index in range(1, edges.Extent() + 1):
        edge = TopoDS.Edge_s(edges.FindKey(index))
        curve = BRepAdaptor_Curve(edge)
        record = {'id': index, 'type': enum(curve.GetType()),
                  'interval_exact': [exact(curve.FirstParameter()), exact(curve.LastParameter())],
                  'tolerance_exact': exact(BRep_Tool.Tolerance_s(edge)),
                  'children': children(edge), 'location_identity': edge.Location().IsIdentity(),
                  'vertices': []}
        endpoints = unique(edge, TopAbs_VERTEX)
        for j in range(1, endpoints.Extent() + 1):
            record['vertices'].append(vertices.FindIndex(endpoints.FindKey(j)))
        if record['type'] == 'GeomAbs_Line':
            line = curve.Line()
            record.update(origin_exact=xyz(line.Location()), direction_exact=xyz(line.Direction()))
        result['edges'].append(record)
    for index in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(index))
        surface = BRepAdaptor_Surface(face, False)
        record = {'id': index, 'type': enum(surface.GetType()), 'orientation': enum(face.Orientation()),
                  'tolerance_exact': exact(BRep_Tool.Tolerance_s(face)),
                  'UV_exact': [exact(x) for x in BRepTools.UVBounds_s(face)],
                  'children': children(face), 'location_identity': face.Location().IsIdentity(),
                  'edge_uses': []}
        if record['type'] == 'GeomAbs_Plane':
            position = surface.Plane().Position()
            record.update(origin_exact=xyz(position.Location()), X_exact=xyz(position.XDirection()),
                          Y_exact=xyz(position.YDirection()), normal_exact=xyz(position.Direction()))
        iterator = TopExp_Explorer(face, TopAbs_EDGE)
        while iterator.More():
            edge = TopoDS.Edge_s(iterator.Current())
            curve = BRepAdaptor_Curve2d(edge, face)
            use = {'edge_id': edges.FindIndex(edge), 'orientation': enum(edge.Orientation()),
                   'type': enum(curve.GetType()),
                   'interval_exact': [exact(curve.FirstParameter()), exact(curve.LastParameter())]}
            if use['type'] == 'GeomAbs_Line':
                line = curve.Line()
                use.update(origin_exact=xy(line.Location()), direction_exact=xy(line.Direction()))
            record['edge_uses'].append(use)
            iterator.Next()
        result['faces'].append(record)
    return result
