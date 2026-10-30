"""Independent exact verifier of filled carriers, not a producer import."""
from fractions import Fraction as F
from itertools import product


def need(value, message):
    if not value:
        raise ValueError(message)


def bounds(items):
    need(len(items) == 3 and all(len(iv) == 2 for iv in items), "three complete box axes")
    B = tuple(tuple(F(v) for v in iv) for iv in items)
    need(all(a <= b for a, b in B), "finite ordered closed bounds")
    return B


def dimensions_volume(B):
    return (B[0][1] - B[0][0]) * (B[1][1] - B[1][0]) * (B[2][1] - B[2][0])


def expected_partition(values):
    endpoints = sorted(set(values))
    return sorted([(x, x) for x in endpoints] + list(zip(endpoints, endpoints[1:])))


def check_completion(proof):
    need(proof["axis"] == 0 and proof["singleton_atoms_retained"], "complete X-fibre interpretation")
    original = [bounds(B) for B in proof["boundary_boxes_exact"]]
    need(original, "nonempty full boundary-box list")
    partitions = []
    for axis, name in ((1, "Y_atoms_exact"), (2, "Z_atoms_exact")):
        actual = [tuple(map(F, iv)) for iv in proof[name]]
        expected = expected_partition(x for B in original for x in B[axis])
        need(actual == expected, "all singleton and open-interval atoms must remain")
        partitions.append(actual)
    records = {}
    for record in proof["cells"]:
        key = (record["y_atom"], record["z_atom"])
        need(key not in records, "unique filled-fibre cell")
        records[key] = record
    required = set()
    for yi, zi in product(range(len(partitions[0])), range(len(partitions[1]))):
        y, z = partitions[0][yi], partitions[1][zi]
        # A representative determines incidence on each open atom because every
        # projected-box endpoint is in this partition. Singleton representatives
        # include all closed projections meeting only at one coordinate.
        p, q = (y[0] + y[1]) / 2, (z[0] + z[1]) / 2
        active = [i for i, B in enumerate(original) if B[1][0] <= p <= B[1][1] and B[2][0] <= q <= B[2][1]]
        key = (yi, zi)
        if not active:
            need(key not in records, "no undeclared inactive fibre cell")
            continue
        required.add(key)
        need(key in records, "missing nonempty closed fibre")
        record = records[key]
        need(record["active_boxes"] == active, "entire boundary cover participates in fibre extrema")
        B = bounds(record["bounds_exact"])
        need(B[1] == y and B[2] == z, "exact original projected atom closure")
        need(B[0][0] <= min(original[i][0][0] for i in active), "left material endpoint omitted")
        need(B[0][1] >= max(original[i][0][1] for i in active), "right material endpoint omitted")
    need(set(records) == required, "no unreachable or duplicate fibre records")
    cells = [bounds(r["bounds_exact"]) for r in proof["cells"]]
    volume = sum(dimensions_volume(B) for B in cells)
    return {"complete_boundary_fibre_hull_contained": True,
            "compact_material_containment_implication_proved": True,
            "cell_count": len(cells), "positive_volume_cells": sum(dimensions_volume(B) > 0 for B in cells),
            "singleton_boundary_cells": sum(dimensions_volume(B) == 0 for B in cells),
            "filled_carrier_volume_exact": str(volume)}


def all_box_union_volume(boxes):
    data = [bounds(b) for b in boxes]
    grids = [sorted({v for B in data for v in B[k]}) for k in range(3)]
    total = F(0)
    for intervals in product(*(list(zip(v, v[1:])) for v in grids)):
        point = [(a + b) / 2 for a, b in intervals]
        if any(all(a <= x <= b for x, (a, b) in zip(point, B)) for B in data):
            total += dimensions_volume(intervals)
    return total


def carrier_intersection_volume(proof, fixed):
    target = bounds(fixed)
    result = F(0)
    for cell in proof["cells"]:
        B = bounds(cell["bounds_exact"])
        width = [max(F(0), min(b, d) - max(a, c)) for (a, b), (c, d) in zip(B, target)]
        result += width[0] * width[1] * width[2]
    return result


def local_filling(row, result, certificate, original_checker):
    need(certificate["case_id"] == row["case_id"], "case identity")
    need(certificate["compact_filling_implication_only"] is True, "conditional mathematical scope preserved")
    need(certificate["native_boundary_set_identity_proved"] is False, "unproved native set identity cannot be promoted")
    need(certificate["uniform_compiled_geometry_error_proved"] is False, "unproved compiled error cannot be promoted")
    verified = original_checker.verify_tree(row, result)
    support = tuple(tuple(map(F, iv)) for iv in row["source_support"]["support_exact"])
    need(certificate["source_support_exact"] == row["source_support"]["support_exact"], "entire source support")
    need(F(certificate["source_ratio_exact"]) == F(row["source_support"]["ratio_exact"]), "exact sheared-coordinate law")
    metrics = row["source_inventory"]["metrics"]
    if metrics["counts"]["solids"]:
        need(certificate["source_kind"] == "compact_filling_of_complete_affine_boundary", "solid filling contract")
        need(metrics["counts"]["solids"] == metrics["counts"]["shells"] == 1 and metrics["native_valid"]
             and metrics["signed_volume_float"] > 0 and metrics["infinity_state_at_tolerance_zero"] == "TopAbs_OUT",
             "actual original bounded positive solid diagnostics")
    else:
        need(certificate["source_kind"] == "complete_affine_face" and metrics["counts"]["faces"] == 1,
             "original face must not be relabelled solid")
    fixed = row["fixed_inventory"]
    profile = row["fixed_profile"]
    need(certificate["fixed_center_xy_exact"] == profile["center_xy_exact"], "whole fixed exact axis")
    C = tuple(map(F, profile["center_xy_exact"]))
    edge = {e["index"]: e for e in fixed["edges"]}
    vertex = {v["index"]: v for v in fixed["vertices"]}
    trim_checks = radial_points = 0
    for face, item in zip(fixed["faces"], profile["faces"]):
        radius = F(item["radius_upper_exact"])
        zlo, zhi = map(F, item["z_exact"])
        points = []
        for index in set(face["edge_indices"]):
            q = edge[index]["curve"]
            if q["type"] == "GeomAbs_Line":
                points += original_checker.line_points(q)
        points += [tuple(map(F, vertex[i]["point_exact"])) for i in set(face["vertex_indices"])]
        surface = face["surface"]
        if surface["type"] == "GeomAbs_Plane":
            O, X, Y = [tuple(map(F, surface[k])) for k in ("origin_exact", "X_exact", "Y_exact")]
            need(X[2] == Y[2] == 0, "horizontal complete cap")
            for use in face["pcurves"]:
                q = use["curve"]
                if q["type"] == "GeomAbs_Line":
                    points += [tuple(O[k] + X[k]*p[0] + Y[k]*p[1] for k in range(3))
                               for p in original_checker.line_points(q)]
                else:
                    need(q["type"] == "GeomAbs_Circle", "every original cap trim represented")
                    o, x, y = [tuple(map(F, q[k])) for k in ("origin_exact", "X_exact", "Y_exact")]
                    world = {"origin_exact": [str(O[k] + X[k]*o[0] + Y[k]*o[1]) for k in range(3)],
                             "X_exact": [str(X[k]*x[0] + Y[k]*x[1]) for k in range(3)],
                             "Y_exact": [str(X[k]*y[0] + Y[k]*y[1]) for k in range(3)],
                             "radius_exact": q["radius_exact"]}
                    original_checker.circular_support(world, C, radius)
                    need(zlo <= F(world["origin_exact"][2]) <= zhi, "entire cap trim axial support")
                trim_checks += 1
        for p in points:
            need((p[0]-C[0])**2 + (p[1]-C[1])**2 <= radius**2,
                 "whole fixed straight trim or vertex outside radial support")
            need(zlo <= p[2] <= zhi, "whole fixed straight trim or vertex outside axial support")
            radial_points += 1
    expected = expected_partition(F(v) for p in profile["faces"] for v in p["z_exact"])
    need([tuple(map(F, p)) for p in certificate["fixed_Z_atoms_exact"]] == expected,
         "all fixed-profile endpoints and intervals retained")
    fibres = certificate["fixed_fibres"]
    need(len(fibres) == len(expected), "complete fixed fibre partition")
    for i, (atom, record) in enumerate(zip(expected, fibres)):
        need(record["atom"] == i and tuple(map(F, record["z_exact"])) == atom, "fixed atom order and bounds")
        q = sum(atom)/2
        active = [p for p in profile["faces"] if F(p["z_exact"][0]) <= q <= F(p["z_exact"][1])]
        need(record["active_faces"] == [p["face_index"] for p in active], "all boundary faces at every exact Z atom")
        if active:
            need(F(record["radius_square_upper_exact"]) >= max(F(p["radius_square_upper_exact"]) for p in active),
                 "complete radial support across fixed section")
        else:
            need(record["radius_square_upper_exact"] is None, "empty fixed section explicit")
    leaves = [n for n in row["nodes"] if n["kind"] == "leaf"]
    need(certificate["original_nodes"] == [{k: n[k] for k in ("id", "kind", "y_exact", "box_exact")} for n in leaves],
         "all original complete-carrier leaves retained")
    comparisons = 0
    for leaf in leaves:
        B = bounds(leaf["box_exact"])
        distance_square = sum(max(a-c, c-b, F(0))**2 for (a,b),c in zip(B[:2],C))
        for fibre in fibres:
            z0,z1 = map(F,fibre["z_exact"])
            # Closure intersection is deliberately conservative at a grid end.
            if z1 < B[2][0] or z0 > B[2][1] or fibre["radius_square_upper_exact"] is None:
                continue
            need(distance_square > F(fibre["radius_square_upper_exact"]), "strict separation from complete compact fixed filling")
            comparisons += 1
    return {"case_id": row["case_id"], "original_tree_check": verified,
            "source_complete_convex_prism_filling_implication": True,
            "fixed_complete_radial_fibre_filling_implication": True,
            "exact_model_intersection_upper_bound": "0",
            "whole_fixed_cap_pcurves_checked": trim_checks,
            "whole_fixed_line_and_vertex_radial_checks": radial_points,
            "fixed_fibre_atoms": len(fibres), "strict_leaf_fibre_comparisons": comparisons,
            "native_boundary_set_identity_proved": False,
            "uniform_compiled_geometry_error_proved": False,
            "full_continuous_G2": False}
