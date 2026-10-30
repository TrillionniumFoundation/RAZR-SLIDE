"""Exact closed-fibre completion, with zero-dimensional atoms explicitly retained.

These functions construct candidate certificates. The independent checker does
not import this file. No CAD Common volume is used as a conservative bound.
"""
from fractions import Fraction as F
from itertools import product


def box(items):
    value = tuple(tuple(map(F, iv)) for iv in items)
    if len(value) != 3 or any(len(iv) != 2 or iv[0] > iv[1] for iv in value):
        raise ValueError("complete closed box required")
    return value


def encode(value):
    return [[str(a), str(b)] for a, b in value]


def atoms(points):
    points = sorted(set(points))
    result = []
    for index, point in enumerate(points):
        result.append((point, point))
        if index + 1 < len(points):
            result.append((point, points[index + 1]))
    return result


def fibre_completion(boxes):
    """Closed outer boxes for the X-fibre hull of a finite box union.

    Interval atoms represent their open interiors for incidence selection; their
    closures are emitted as conservative cells. Singleton atoms preserve points
    where several projected boxes meet only at an endpoint.
    """
    data = list(map(box, boxes))
    if not data:
        raise ValueError("nonempty complete boundary cover required")
    Y = atoms(v for B in data for v in B[1])
    Z = atoms(v for B in data for v in B[2])
    cells = []
    for yi, zi in product(range(len(Y)), range(len(Z))):
        y, z = Y[yi], Z[zi]
        active = [i for i, B in enumerate(data)
                  if B[1][0] <= y[0] <= y[1] <= B[1][1]
                  and B[2][0] <= z[0] <= z[1] <= B[2][1]]
        if active:
            X = (min(data[i][0][0] for i in active), max(data[i][0][1] for i in active))
            cells.append({"y_atom": yi, "z_atom": zi, "active_boxes": active,
                          "bounds_exact": encode((X, y, z))})
    return {"axis": 0, "boundary_boxes_exact": [encode(B) for B in data],
            "Y_atoms_exact": encode(Y), "Z_atoms_exact": encode(Z), "cells": cells,
            "singleton_atoms_retained": True}


def volume(B):
    return (B[0][1] - B[0][0]) * (B[1][1] - B[1][0]) * (B[2][1] - B[2][0])


def local_certificate(row):
    profiles = row["fixed_profile"]["faces"]
    Z = atoms(F(v) for p in profiles for v in p["z_exact"])
    fibres = []
    for index, atom in enumerate(Z):
        active = [p for p in profiles if F(p["z_exact"][0]) <= atom[0] <= atom[1] <= F(p["z_exact"][1])]
        fibres.append({"atom": index, "z_exact": list(map(str, atom)),
                       "active_faces": [p["face_index"] for p in active],
                       "radius_square_upper_exact": str(max((F(p["radius_square_upper_exact"]) for p in active), default=F(0))) if active else None})
    return {"case_id": row["case_id"], "source_support_exact": row["source_support"]["support_exact"],
            "source_ratio_exact": row["source_support"]["ratio_exact"],
            "source_kind": "complete_affine_face" if row["source_inventory"]["metrics"]["counts"]["solids"] == 0 else "compact_filling_of_complete_affine_boundary",
            "fixed_center_xy_exact": row["fixed_profile"]["center_xy_exact"],
            "fixed_Z_atoms_exact": encode(Z), "fixed_fibres": fibres,
            "original_nodes": [{k: n[k] for k in ("id", "kind", "y_exact", "box_exact")} for n in row["nodes"] if n["kind"] == "leaf"],
            "compact_filling_implication_only": True,
            "native_boundary_set_identity_proved": False,
            "uniform_compiled_geometry_error_proved": False}


def controls():
    unit = ((F(0), F(1)),) * 3
    shells = []
    for axis in range(3):
        for end in (0, 1):
            B = list(unit)
            B[axis] = (F(0), F(1, 4)) if end == 0 else (F(3, 4), F(1))
            shells.append(encode(B))
    thin = [[list(iv) for iv in B] for B in shells]
    for B in thin:
        B[2] = [str(F(v) / (1 << 80)) for v in B[2]]
    # The two boxes touch only at y=1. Their point-fibre hull has an X bridge
    # absent from either neighbouring open Y atom; singleton handling matters.
    touching = [[["0", "1"], ["0", "1"], ["0", "1"]],
                [["2", "3"], ["1", "2"], ["0", "1"]]]
    return [{"name": "original_hollow_shell", "certificate": fibre_completion(shells),
             "expected_filled_volume_exact": "1", "original_missed_intersection_exact": "1/64"},
            {"name": "positive_thin_shell", "certificate": fibre_completion(thin),
             "expected_filled_volume_exact": str(F(1, 1 << 80))},
            {"name": "touching_projection_singleton", "certificate": fibre_completion(touching),
             "expected_filled_volume_exact": "2"}]
