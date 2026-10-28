"""Complete finite native inventories, adding positive-weight BSpline curves.

This records native representations; validity and geometric set coherence are
separate claims. No tolerance is changed and no approximate mesh is used.
"""
from collections import Counter
from fractions import Fraction as Q
import importlib.util
import math


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load_inventory(path):
    spec = importlib.util.spec_from_file_location('original_l8_inventory_r3', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def complete_curve(record, adaptor, dimension):
    kind = record['type'].split('.')[-1]
    if kind in ('GeomAbs_Line', 'GeomAbs_Circle'):
        record['complete_supported_representation'] = True
        return
    if kind != 'GeomAbs_BSplineCurve':
        record['complete_supported_representation'] = False
        return
    curve = adaptor.BSpline()
    n = curve.NbPoles()
    weights = [float(curve.Weight(i)) for i in range(1, n + 1)]
    poles = [tuple(float(v) for v in curve.Pole(i).Coord()) for i in range(1, n + 1)]
    require(all(len(v) == dimension and all(map(math.isfinite, v)) for v in poles),
            'invalid BSpline control point')
    require(all(math.isfinite(w) and w > 0 for w in weights), 'nonpositive BSpline weight')
    knots = [float(curve.Knot(i)) for i in range(1, curve.NbKnots() + 1)]
    multiplicities = [int(curve.Multiplicity(i)) for i in range(1, curve.NbKnots() + 1)]
    require(all(math.isfinite(v) for v in knots) and all(a < b for a, b in zip(knots, knots[1:])),
            'invalid BSpline knot order')
    record['bspline'] = {
        'degree': int(curve.Degree()), 'dimension': dimension,
        'is_rational': bool(curve.IsRational()), 'is_periodic': bool(curve.IsPeriodic()),
        'poles_exact': [[str(Q(v)) for v in p] for p in poles],
        'weights_exact': [str(Q(w)) for w in weights],
        'knots_exact': [str(Q(k)) for k in knots], 'multiplicities': multiplicities,
        'all_weights_strictly_positive': True,
        'convex_hull_bounds_whole_curve_on_its_defined_knot_domain': True,
    }
    record['complete_supported_representation'] = True


def inspect(shape, original):
    """Retain every original row and add the previously unsupported curves."""
    result = original.inspect(shape)
    for rec, edge in zip(result['edges'], shape.Edges(), strict=True):
        local = original.TopoDS.Edge_s(edge.wrapped.Located(original.TopLoc_Location()))
        complete_curve(rec['local_curve'], original.BRepAdaptor_Curve(local), 3)
        complete_curve(rec['native_global_curve'], original.BRepAdaptor_Curve(edge.wrapped), 3)
    usages = Counter()
    orientations = {}
    unsupported = []
    for frec, face in zip(result['faces'], shape.Faces(), strict=True):
        for wrec, wire in zip(frec['wires'], face.Wires(), strict=True):
            iterator = original.TopoDS_Iterator(wire.wrapped, True, True)
            index = 0
            while iterator.More():
                edge = original.TopoDS.Edge_s(iterator.Value())
                occurrence = wrec['edge_occurrences'][index]
                complete_curve(occurrence['pcurve'], original.BRepAdaptor_Curve2d(edge, face.wrapped), 2)
                ei = occurrence['edge_index']
                usages[ei] += 1
                orientations.setdefault(ei, []).append(occurrence['orientation'].split('.')[-1])
                if not occurrence['pcurve']['complete_supported_representation']:
                    unsupported.append({'face': frec['index'], 'wire': wrec['index'],
                                        'occurrence': index, 'type': occurrence['pcurve']['type']})
                index += 1
                iterator.Next()
            require(index == len(wrec['edge_occurrences']), 'native trim inventory changed')
    for rec in result['edges']:
        for role in ('local_curve', 'native_global_curve'):
            if not rec[role]['complete_supported_representation']:
                unsupported.append({'edge': rec['index'], 'role': role, 'type': rec[role]['type']})
    result['r3_complete_curve_inventory'] = {
        'unsupported': unsupported,
        'complete': not unsupported and not result['incomplete_inventory'],
        'edge_use_counts': {str(k): v for k, v in sorted(usages.items())},
        'edge_occurrence_orientations': {str(k): v for k, v in sorted(orientations.items())},
        'each_edge_two_opposite_oriented_occurrences': bool(
            len(usages) == result['counts']['edges'] and
            all(v == 2 and sorted(orientations[k]) == ['TopAbs_FORWARD', 'TopAbs_REVERSED']
                for k, v in usages.items())),
        'topological_incidence_is_not_exact_geometric_seam_coherence': True,
    }
    return result
