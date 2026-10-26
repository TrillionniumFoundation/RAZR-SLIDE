"""Diagnose and improve initial bearing-point coverage without an FE solve.

Inputs are the original declared clipped projection faces and optionally one
retained gap audit paired with its original domain manifest. The old perimeter
seed arithmetic is replayed; near-tied extreme vertices may differ by platform.
Proposed
seeds retain every old point and add a bounded, spatially distributed set of
face centroids or actual negative witnesses.  Distance and touched-face counts
describe point coverage only; they do not certify a newly solved contact field.
No material, gap tolerance, stiffness, body contact or equilibrium row changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np


POINT_DUPLICATE_MM = 1e-10


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def polygon_geometry(value):
    p = np.asarray(value)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or p.dtype.kind not in "fiu" or not np.isfinite(p).all():
        raise ValueError("finite polygon with at least three planar vertices required")
    p = p.astype(float)
    q = p-p[0]
    cross = q[:, 0]*np.roll(q[:, 1], -1)-q[:, 1]*np.roll(q[:, 0], -1)
    signed = float(cross.sum())
    if abs(signed) <= 1e-20:
        raise ValueError("nondegenerate polygon required")
    direction = 1 if signed > 0 else -1
    edge = np.roll(p, -1, axis=0)-p
    rel = p[:, None, :]-p[None, :, :]
    side = direction*(edge[None, :, 0]*rel[:, :, 1]-edge[None, :, 1]*rel[:, :, 0])
    allowance = 1e-11*np.maximum(np.linalg.norm(edge, axis=1), 1e-15)
    if np.any(side < -allowance):
        raise ValueError("convex ordered clipped polygon required")
    centroid = p[0]+((q+np.roll(q, -1, axis=0))*cross[:, None]).sum(axis=0)/(3*signed)
    return p, abs(signed)/2, centroid, direction


def contains(polygon, xy, *, interior=False):
    p, _, _, direction = polygon_geometry(polygon)
    x = np.asarray(xy, dtype=float).reshape(-1, 2)
    edge = np.roll(p, -1, axis=0)-p
    rel = x[:, None, :]-p[None, :, :]
    side = direction*(edge[None, :, 0]*rel[:, :, 1]-edge[None, :, 1]*rel[:, :, 0])
    # This spatial membership allowance is unrelated to the mechanical gap target.
    allowance = 1e-11*np.maximum(np.linalg.norm(edge, axis=1), 1e-15)
    return np.all(side > allowance if interior else side >= -allowance, axis=1)


def projection_bearings(panel_rows, frame_rows):
    faces = []
    centers = {}
    for body, rows, direction in (("panel", panel_rows, [0, 0, -1]),
                                  ("frame", frame_rows, [0, 0, 1])):
        for raw in rows:
            if raw.get("kind") != "C":
                continue
            bolt = raw["index"]
            if type(bolt) is not int or not 0 <= bolt < 4 or raw["axis"] != 2 or raw["direction"] != direction:
                raise ValueError("original normal-bearing identity required")
            center = np.asarray(raw["density_target"], dtype=float)
            if center.shape != (2,) or not np.isfinite(center).all():
                raise ValueError("finite bearing center required")
            if bolt in centers and not np.allclose(center, centers[bolt], rtol=0, atol=1e-12):
                raise ValueError("opposed faces disagree about bolt center")
            centers[bolt] = center
            p, area, centroid, _ = polygon_geometry(raw["polygon"])
            if not contains(p, [centroid], interior=True)[0]:
                raise ValueError("convex positive-area face required")
            faces.append({"face": len(faces), "body": body, "index": bolt,
                          "bearing": bolt+(0 if body == "panel" else 4),
                          "patch": f"bearing_{body}_{bolt}", "polygon": p.tolist(),
                          "center": center.tolist(), "area_mm2": area,
                          "centroid": centroid.tolist()})
    if {f["bearing"] for f in faces} != set(range(8)):
        raise ValueError("all eight declared bearing domains are required")
    return faces


def descriptor(face, xy, origin):
    return {"kind": "bearing", "body": face["body"], "index": face["index"],
            "face": face["face"], "patch": face["patch"],
            "xy": list(map(float, xy)), "gap": 0.0, "seed_origin": origin}


def legacy_perimeter_seeds(faces):
    """PR35's twelve directions, dot product and first-on-exact-tie ordering.

    A near tie may round differently under another NumPy/BLAS platform. Record
    the resulting point count rather than substituting the historical 77.
    """
    seeds = []
    for bearing in range(8):
        group = [f for f in faces if f["bearing"] == bearing]
        vertices = [(f, np.asarray(v)) for f in group for v in f["polygon"]]
        seen = []
        for angle in np.arange(12)*2*np.pi/12:
            direction = np.array([np.cos(angle), np.sin(angle)])
            face, xy = max(vertices, key=lambda item: float(item[1]@direction))
            if not any(np.linalg.norm(xy-old) < POINT_DUPLICATE_MM for old in seen):
                seeds.append(descriptor(face, xy, "legacy_perimeter"))
                seen.append(xy)
    return seeds


def bind_retained_domains(faces, panel_rows, frame_rows, domains):
    """Verify each audit ordinal against every original projection field.

    Length alone cannot identify a gap cell. Hashes must additionally tie this
    complete domain file and gap audit to the same retained-run manifest.
    """
    raw_faces = [r for rows in (panel_rows, frame_rows) for r in rows if r.get("kind") == "C"]
    if len(domains) != len(faces):
        raise ValueError("retained domain length differs")
    for i, (face, raw, domain) in enumerate(zip(faces, raw_faces, domains)):
        if any(domain.get(key) != value for key, value in raw.items()):
            raise ValueError(f"retained domain {i} differs from its exact projection row")
        expected = {"body": face["body"], "bearing": face["bearing"],
                    "label": face["patch"], "origin": face["center"],
                    "normal_sign": -1 if face["body"] == "panel" else 1}
        if any(domain.get(key) != value for key, value in expected.items()):
            raise ValueError(f"retained domain {i} has a different bearing identity")
    return {"face_order_and_every_projection_field_verified": True,
            "bound_faces": len(faces)}


def verify_manifest_file(path, manifest):
    matches = [r for r in manifest["files"] if Path(r["path"]).name == path.name]
    if len(matches) != 1 or matches[0]["sha256"] != sha256(path) or matches[0]["bytes"] != path.stat().st_size:
        raise ValueError("retained run manifest does not bind "+str(path))
    return matches[0]


def gap_witnesses(faces, audit, gap_target):
    values = np.asarray(audit["minimum"], dtype=float)
    xy = np.asarray(audit["minimum_at"], dtype=float)
    if values.shape != (len(faces),) or xy.shape != (len(faces), 2) or not np.isfinite(values).all() or not np.isfinite(xy).all():
        raise ValueError("gap audit does not match every declared face")
    negative = np.flatnonzero(values < -gap_target)
    if list(map(int, audit["negative_cells"])) != negative.tolist():
        raise ValueError("negative-cell identities disagree with frozen target")
    if audit.get("unresolved_cells"):
        raise ValueError("unresolved old audit is not a complete witness source")
    candidates = []
    for i in negative:
        if not contains(faces[i]["polygon"], [xy[i]])[0]:
            raise ValueError("saved witness is outside its bound face")
        candidates.append((faces[i], xy[i], float(values[i])))
    return candidates


def distributed_seeds(faces, original, extra_points, *, witnesses=None):
    """Retain old points; round-robin bearings, then farthest unrepresented point.

    With actual witnesses, the first new point per bearing is its most negative
    witness.  Subsequent points maximize distance to that bearing's existing
    seeds, using severity and face identity only to break ties.  This avoids
    filling one local cluster while other portions of a bearing remain empty.
    No spatial cutoff discards a distinct negative witness from a final audit.
    """
    if type(extra_points) is not int or extra_points < 0:
        raise ValueError("nonnegative explicit additional-point budget required")
    result = [dict(p) for p in original]
    candidates = ([(f, np.asarray(f["centroid"]), 0.0) for f in faces]
                  if witnesses is None else list(witnesses))
    groups = {b: [v for v in candidates if v[0]["bearing"] == b] for b in range(8)}
    additions = {b: 0 for b in range(8)}
    while len(result)-len(original) < extra_points:
        changed = False
        for b in range(8):
            prior = np.asarray([p["xy"] for p in result if p["index"]+(0 if p["body"] == "panel" else 4) == b])
            available = []
            for face, xy, minimum in groups[b]:
                distance = float(np.min(np.linalg.norm(prior-xy, axis=1))) if len(prior) else float("inf")
                if distance >= POINT_DUPLICATE_MM:
                    available.append((face, xy, minimum, distance))
            if not available:
                continue
            if witnesses is not None and additions[b] == 0:
                chosen = min(available, key=lambda v: (v[2], v[0]["face"]))
            else:
                chosen = max(available, key=lambda v: (v[3], -v[2], -v[0]["face"]))
            face, xy, _, _ = chosen
            result.append(descriptor(face, xy, "retained_negative_witness" if witnesses is not None else "face_centroid"))
            groups[b] = [v for v in groups[b] if v[0]["face"] != face["face"]]
            additions[b] += 1
            changed = True
            if len(result)-len(original) == extra_points:
                break
        if not changed:
            break
    return result


def coverage(faces, seeds, *, witnesses=None):
    touched = interior = 0
    rows = []
    for b in range(8):
        group = [f for f in faces if f["bearing"] == b]
        points = np.asarray([p["xy"] for p in seeds if p["index"]+(0 if p["body"] == "panel" else 4) == b])
        if not len(points):
            raise ValueError("every bearing needs an original point set")
        centers = np.asarray([f["centroid"] for f in group])
        distance = np.linalg.norm(centers[:, None, :]-points[None, :, :], axis=2).min(axis=1)
        touch = sum(bool(contains(f["polygon"], points).any()) for f in group)
        inside = sum(bool(contains(f["polygon"], points, interior=True).any()) for f in group)
        touched += touch
        interior += inside
        row = {"bearing": b, "faces": len(group), "points": len(points),
               "faces_touched": touch, "faces_with_interior_point": inside,
               "centroid_nearest_point_max_mm": float(distance.max()),
               "area_weighted_centroid_distance_mm": float(np.average(distance, weights=[f["area_mm2"] for f in group]))}
        if witnesses is not None:
            w = [v for v in witnesses if v[0]["bearing"] == b]
            if w:
                wd = np.linalg.norm(np.asarray([v[1] for v in w])[:, None, :]-points[None, :, :], axis=2).min(axis=1)
                row.update({"negative_witnesses": len(w), "negative_witnesses_exactly_seeded": int(np.sum(wd < POINT_DUPLICATE_MM)),
                            "negative_witness_nearest_point_max_mm": float(wd.max()),
                            "negative_witness_nearest_point_mean_mm": float(wd.mean())})
        rows.append(row)
    return {"points": len(seeds), "faces": len(faces), "faces_touched": touched,
            "faces_with_interior_point": interior, "bearings": rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-faces", type=Path, required=True)
    ap.add_argument("--frame-faces", type=Path, required=True)
    ap.add_argument("--gaps", type=Path)
    ap.add_argument("--bearing-domains", type=Path)
    ap.add_argument("--retained-manifest", type=Path)
    ap.add_argument("--gap-target-mm", type=float, default=1e-7)
    ap.add_argument("--extra-points", type=int, default=128)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if not np.isfinite(args.gap_target_mm) or args.gap_target_mm <= 0:
        ap.error("a positive finite frozen gap target is required")
    if len({bool(args.gaps), bool(args.bearing_domains), bool(args.retained_manifest)}) != 1:
        ap.error("retained gaps require original bearing domains and their shared run manifest")
    inputs = [args.panel_faces, args.frame_faces]+([args.gaps, args.bearing_domains, args.retained_manifest] if args.gaps else [])
    hashes = {str(p.resolve()): sha256(p) for p in inputs}
    panel_rows = json.loads(args.panel_faces.read_text())
    frame_rows = json.loads(args.frame_faces.read_text())
    faces = projection_bearings(panel_rows, frame_rows)
    binding = None
    if args.gaps:
        manifest = json.loads(args.retained_manifest.read_text())
        verify_manifest_file(args.gaps, manifest)
        verify_manifest_file(args.bearing_domains, manifest)
        binding = bind_retained_domains(faces, panel_rows, frame_rows, json.loads(args.bearing_domains.read_text()))
    witnesses = gap_witnesses(faces, json.loads(args.gaps.read_text()), args.gap_target_mm) if args.gaps else None
    legacy = legacy_perimeter_seeds(faces)
    geometric = distributed_seeds(faces, legacy, args.extra_points)
    variants = {"legacy": legacy, "distributed_centroids": geometric}
    if witnesses is not None:
        variants["distributed_failed_witnesses"] = distributed_seeds(faces, legacy, args.extra_points, witnesses=witnesses)
    report = {"scope": "initial_point_coverage_only", "gap_target_mm_unchanged": args.gap_target_mm,
              "additional_point_budget_per_variant": args.extra_points,
              "retained_witness_file_available_and_hash_verified": bool(args.gaps),
              "retained_domain_binding": binding,
              "negative_witnesses": len(witnesses) if witnesses is not None else None,
              "variants": {name: coverage(faces, seeds, witnesses=witnesses) for name, seeds in variants.items()},
              "input_sha256": hashes, "source_sha256": sha256(__file__),
              "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                          "platform": platform.platform()},
              "seed_reference": "PR35 support-direction arithmetic replay in this runtime",
              "historical_seed_positions_verified": False,
              "old_points_preserved": all(seeds[:len(legacy)] == legacy for seeds in variants.values()),
              "new_fe_solve": False, "whole_contact_solution_passed": False,
              "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False}
    args.output.mkdir(parents=True, exist_ok=False)
    for name, seeds in variants.items():
        (args.output/(name+"-seeds.json")).write_text(json.dumps(seeds, indent=2)+"\n")
    for path, expected in hashes.items():
        if sha256(path) != expected:
            raise RuntimeError("input bytes changed during diagnostic")
    (args.output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"legacy_points": len(legacy), "variants": {k: {z: v[z] for z in ("points", "faces_touched", "faces_with_interior_point")} for k, v in report["variants"].items()}, "negative_witnesses": report["negative_witnesses"], "new_fe_solve": False}))


if __name__ == "__main__":
    main()
