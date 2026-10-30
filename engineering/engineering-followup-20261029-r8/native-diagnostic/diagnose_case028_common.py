#!/usr/bin/env python3
"""Fresh finite Common diagnosis of the saved original L1 case-028 materials.

No K1/K3 factory material is substituted. The source result remains unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt


def file_id(path):
    b = path.read_bytes()
    return {"name": path.name, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def signature(shape):
    solids = shape.Solids()
    return {
        "shape_type": shape.ShapeType(), "is_valid": shape.isValid(),
        "signed_volume_mm3": shape.Volume(), "solid_count": len(solids),
        "solid_signed_volumes_mm3": [s.Volume() for s in solids],
        "top_level_children_types": [c.ShapeType() for c in shape],
        "face_count": len(shape.Faces()), "edge_count": len(shape.Edges()),
        "vertex_count": len(shape.Vertices()),
    }


def states(shape, point):
    return [str(BRepClass3d_SolidClassifier(s.wrapped, gp_Pnt(*point), 1e-9).State()) for s in shape.Solids()]


def run_common(a, b, destination):
    started = time.monotonic()
    operation = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    operation.Build()
    result = {"is_done": operation.IsDone(), "fuzzy_value_mm": operation.FuzzyValue(),
              "run_parallel": operation.RunParallel(), "non_destructive": operation.NonDestructive()}
    if not operation.IsDone():
        return {**result, "seconds": time.monotonic()-started, "evaluation_failed": True}
    common = cq.Shape.cast(operation.Shape())
    result["common"] = signature(common)
    result["min_input_signed_volume_mm3"] = min(a.Volume(), b.Volume())
    volume = result["common"]["signed_volume_mm3"]
    result["signed_volume_within_input_upper_bound"] = 0 <= volume <= result["min_input_signed_volume_mm3"]
    result["strictly_above_original_1e_minus7_volume_gate"] = volume > 1e-7
    result["topologically_empty"] = len(list(common)) == 0 and common.ShapeType() == "Compound"
    result["common_export_status"] = bool(common.exportBrep(str(destination)))
    result["common_artifact"] = file_id(destination)
    result["common_solid_centroid_classification"] = []
    for solid in common.Solids():
        c = solid.Center().toTuple()
        result["common_solid_centroid_classification"].append({
            "point_mm": c, "classifier_tolerance_mm": 1e-9,
            "operand_a_solid_states": states(a, c), "operand_b_solid_states": states(b, c),
            "common_solid_state": states(solid, c),
        })
    result["seconds"] = time.monotonic()-started
    result["evaluation_failed"] = False
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-case", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    original = json.loads((args.source_case/"result.json").read_text())
    expected = {m["id"]: m["exports"]["brep"] for m in original["material_exports"]}
    sources = {}
    mats = {}
    for mid in (1, 2, 3, 4):
        path = args.source_case / f"material-{mid:03d}.brep"
        ident = file_id(path)
        assert ident["bytes"] == expected[mid]["bytes"] and ident["sha256"] == expected[mid]["sha256"]
        sources[str(mid)] = ident
        mats[mid] = cq.Shape.importBrep(str(path))
    report = {
        "schema": "razr-r8-original-l1-case028-finite-native-common-producer-v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(), "executable": sys.executable,
        "versions": {name: importlib.metadata.version(name) for name in ("cadquery", "cadquery-ocp")},
        "source_result_identity": file_id(args.source_case/"result.json"),
        "source_material_identities": sources,
        "original_target": original["target"],
        "source_material_roles": {str(m["id"]): m["references"] for m in original["material_exports"]},
        "original_frame_traces": original["trace"]["native_frame_results"],
        "original_failure_preserved": original["native_raw"],
        "input_signatures": {str(mid): signature(s) for mid,s in mats.items()},
        "scope": "Two original saved exception-local finite reference-frame pairs only, each in both operand orders; no continuous envelope or current K1/K3 factory claim",
        "original_volume_gate_mm3": 1e-7,
        "capacity_basis": {"native_common_calls": 4, "source_BREP_bytes": sum(v["bytes"] for v in sources.values()),
            "algorithm": "Direct BRepAlgoAPI_Common on four original small rigid BREP shapes; no mesh, refinement tree or full factory",
            "caller_wall_timeout_seconds": 60},
        "evaluations": [],
    }
    for frame, a_id, b_id in ((1,3,2),(2,4,1)):
        for reverse in (False, True):
            aa, bb = (b_id, a_id) if reverse else (a_id,b_id)
            label = f"frame-{frame}-{'reverse' if reverse else 'forward'}"
            try:
                record = run_common(mats[aa], mats[bb], args.output / f"{label}-common.brep")
            except Exception as exc:
                record = {"evaluation_failed": True, "error": f"{type(exc).__name__}: {exc}"}
            report["evaluations"].append({"label": label, "frame": frame, "a_material_id": aa, "b_material_id": bb, **record})
    report["source_bytes_unchanged"] = all(file_id(args.source_case/f"material-{int(mid):03d}.brep") == ident for mid,ident in sources.items())
    report["result_bytes_unchanged"] = file_id(args.source_case/"result.json") == report["source_result_identity"]
    report["seconds"] = time.monotonic()-start
    report["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    report["full_continuous_G2"] = False
    report["physical_qualification"] = False
    report["original_result_rewritten"] = False
    report["new_K1_K3_factory_execution"] = False
    (args.output/"PRODUCER_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"evaluations":[{"label":e["label"],"failed":e["evaluation_failed"],"common":e.get("common")} for e in report["evaluations"]],"seconds":report["seconds"]}))


if __name__ == "__main__":
    main()
