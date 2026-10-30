"""Separate-process STEP/BREP and all-pair reader for R9 independent states.

Does not import the new producer or either candidate builder. Uses the retained
independent native K3 checks and the original scalar tolerances in the same CAD
kernel. This is a finite material check, not a physical reachability result.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import importlib.metadata as md
import itertools
import io
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import traceback
from types import SimpleNamespace

TOL = 1e-7


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def rec(path):
    return {"bytes": Path(path).stat().st_size, "sha256": sha(path)}


def write(path, obj):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def catalog(root):
    return {str(p.relative_to(root)): rec(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc")}


class Budget:
    def __init__(self):
        self.start = time.monotonic()

    def check(self):
        if time.monotonic() - self.start > 3600:
            raise TimeoutError("independent reader exceeded 3600 seconds")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 2 * 2**30:
            raise MemoryError("independent reader exceeded 2 GiB RSS")


def signature(body, p):
    solids, volume = p.whole_material(body)
    return {"valid": body.isValid(), "solid_count": len(solids),
            "signed_volume_mm3": volume,
            "solid_signed_volumes_mm3": [s.Volume() for s in solids],
            "bounds_mm": p.bounds(body)}


def load_file(root, entry, kind, cq, p):
    path = (root / entry["path"]).resolve()
    if not path.is_relative_to(root.resolve()) or rec(path) != {k: entry[k] for k in ("bytes", "sha256")}:
        raise ValueError("serialized original identity differs")
    if kind == "step":
        roots = cq.importers.importStep(str(path)).vals()
        if len(roots) != 1:
            raise ValueError("one whole STEP root required")
        body = roots[0]
    else:
        body = cq.Shape.importBrep(str(path))
    p.single(body)
    return body


def material_difference(a, b, p):
    ab, ba = p.volume(a.cut(b)), p.volume(b.cut(a))
    if not all(math.isfinite(x) and x >= 0 for x in (ab, ba)):
        raise ValueError("invalid signed material difference")
    return {"a_minus_b_mm3": ab, "b_minus_a_mm3": ba, "passed": max(ab, ba) <= TOL}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--producer", type=Path, required=True)
    ap.add_argument("--state", required=True, help="One completed immutable state while other states may still be running")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--s4-root", type=Path, required=True)
    ap.add_argument("--helpers-root", type=Path, required=True)
    ap.add_argument("--near-engineering", type=Path, required=True)
    a = ap.parse_args()
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    source = a.s4_root.resolve(); helpers = a.helpers_root.resolve()
    producer = a.producer.resolve()
    campaign_input_bytes = (producer / "report.json").read_bytes()
    (out / "producer_campaign_input.original.json").write_bytes(campaign_input_bytes)
    start = time.monotonic(); budget = Budget()
    before = catalog(source)
    helper_before = catalog(helpers)
    r = {"schema": "razr-r9-independent-single-state-native-frozen-reader-v2",
         "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
         "script": rec(__file__), "source": rec(out / "producer_campaign_input.original.json"),
         "source_report_is_immutable_snapshot": True, "selected_state": a.state,
         "concurrent_other_producer_states_not_read_or_qualified": True,
         "same_CAD_kernel_separate_process": True, "producer_module_imported": False,
         "candidate_builders_imported": False, "states": {}, "completed": False,
         "runtime": {"python": sys.version, "packages": {n: md.version(n) for n in ("cadquery", "cadquery-ocp", "numpy", "scipy")}},
         "full_continuous_G2": False, "physical_allowed_domain_proved": False,
         "strength_qualified": False, "manufacturing_go": False}
    write(out / "report.json", r)
    try:
        original = json.loads(campaign_input_bytes)
        if a.state not in original["states"] or not original["states"][a.state].get("completed"):
            raise ValueError("requested state is not completely recorded in the captured producer report")
        selected_report = producer / a.state / "report.json"
        selected_report_before = rec(selected_report)
        if json.loads(selected_report.read_text()) != original["states"][a.state]:
            raise ValueError("selected immutable leaf report differs from captured campaign input")
        r["selected_report_before"] = selected_report_before
        if before != json.loads((producer / "S4_SOURCE_CATALOG.json").read_text()):
            raise ValueError("reader source differs from producer source")
        if helper_before != json.loads((producer / "ORIGINAL_HELPERS_CATALOG.json").read_text()):
            raise ValueError("reader original helpers differ from producer helpers")
        os.environ["GITHUB_WORKSPACE"] = str(source)
        sys.path[:0] = [str(helpers), str(source / "integration")]
        import cadquery as cq
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
        from OCP.BRepBndLib import BRepBndLib
        from OCP.Bnd import Bnd_Box
        import product_assembly as p
        import independent_stop_checks as independent
        contract = json.loads((helpers / "PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json").read_text())
        design = contract["design_contract"]
        keybinding = json.loads((helpers / "K3FULL_K1_BINDING.json").read_text())
        keyroot = a.near_engineering.resolve() / "prerequisite-stow_tabs_3" / "prerequisite-near" / "factory" / "worker"
        keyreport = keyroot / "report.engineering.json"
        if sha(keyreport) != keybinding["poses"]["near"]["actual_factory_projection_sha256"]:
            raise ValueError("retained K1 whole material source differs")
        keyrecord = json.loads(keyreport.read_text())["engineering_record"]
        original_keys = {side: load_file(keyroot, keyrecord["candidate_material_exports"][side + "_KEY"]["candidate_q0"]["files"]["step"], "step", cq, p) for side in "LR"}
        for name, item in ((a.state, original["states"][a.state]),):
            target = out / name; target.mkdir()
            state_start = time.monotonic()
            sr = {"state": name, "completed": False, "body_readbacks": {},
                  "factory_report": rec(producer / name / "report.json")}
            r["states"][name] = sr
            try:
                parts = {}
                for body_name, entry in item["body_exports"].items():
                    budget.check()
                    step = load_file(producer / name, entry["files"]["step"], "step", cq, p)
                    brep = load_file(producer / name, entry["files"]["brep"], "brep", cq, p)
                    actual, expected = signature(step, p), entry["signature"]
                    delta_volume = actual["signed_volume_mm3"] - expected["signed_volume_mm3"]
                    delta_bounds = max(abs(x - y) for x, y in zip(actual["bounds_mm"], expected["bounds_mm"]))
                    equal = material_difference(step, brep, p)
                    passed = (actual["valid"] and actual["solid_count"] == expected["solid_count"] == 1
                              and abs(delta_volume) <= TOL and delta_bounds <= TOL and equal["passed"])
                    sr["body_readbacks"][body_name] = {"signature": actual, "volume_delta_mm3": delta_volume,
                        "max_bound_delta_mm": delta_bounds, "STEP_BREP_complete_material_difference": equal, "passed": passed}
                    if not passed:
                        raise ValueError("whole-body original signature or BREP/STEP criterion failed: " + body_name)
                    parts[body_name] = step
                if sorted(parts) != item["participant_names"]:
                    raise ValueError("full participant inventory differs")
                q = item["actual_q_by_side_mm"]
                keys = SimpleNamespace(candidate_q0=original_keys)
                sr["whole_KEY_mapping"] = {side: material_difference(parts[side + "_KEY"].translate((0, -q[side], 0)), original_keys[side], p) for side in "LR"}
                if not all(x["passed"] for x in sr["whole_KEY_mapping"].values()):
                    raise ValueError("whole current KEY differs from retained K1 q0 material")
                oldpanel = load_file(producer / name, item["material_exports"]["original_panel"]["files"]["step"], "step", cq, p)
                checks, _ = independent.all_checks(parts, oldpanel, keys, design, q, p, cq, budget, lambda rows: None)
                sr["independent_native_early_gates"] = checks
                sr["independent_native_early_gates_passed"] = all(x.get("evaluated") and x.get("passed") for x in checks.values())
                sr["panel_KEY_direct_Common_mm3"] = {side: p.volume(parts["A_BACK_PANEL"].intersect(parts[side + "_KEY"])) for side in "LR"}
                previous = [json.loads(line) for line in (producer / name / "pairs.jsonl").read_text().splitlines()]
                expected_pairs = list(itertools.combinations(sorted(parts), 2))
                if [(x["a"], x["b"]) for x in previous] != expected_pairs:
                    raise ValueError("producer canonical full-pair inventory incomplete")
                sr["producer_pair_roster_equals_complete_combinations"] = True
                summary = {"count": 0, "method_counts": {}, "evaluation_failures": [], "rejected_pairs": [], "mismatches": [], "maximum_volume_difference_mm3": 0.0}
                # Independent implementation: original complete-material validation,
                # native AddOptimal bounds, explicit deep geometry copies for Common.
                def body_hash(body):
                    stream = io.BytesIO()
                    if body.exportBrep(stream) is not True:
                        raise ValueError("independent frozen BREP serialization failed")
                    data = stream.getvalue()
                    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                frozen = {}
                for body_name, body in parts.items():
                    p.single(body)
                    box = Bnd_Box()
                    BRepBndLib.AddOptimal_s(body.wrapped, box, False, False)
                    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
                    bounds = [xmin, xmax, ymin, ymax, zmin, zmax]
                    if not all(math.isfinite(x) for x in bounds):
                        raise ValueError("nonfinite independent frozen bounds")
                    frozen[body_name] = {"bounds_mm": bounds, "BREP": body_hash(body),
                                         "signed_volume_mm3": p.volume(body),
                                         "original_single_predicate_passed": True}
                write(target / "frozen_participants.json", frozen)
                counts = Counter()
                with (target / "pairs.jsonl").open("x") as f:
                    for index, ((left, right), prior) in enumerate(zip(expected_pairs, previous)):
                        budget.check()
                        try:
                            aa = frozen[left]["bounds_mm"]
                            bb = frozen[right]["bounds_mm"]
                            gap = max(max(aa[2*i] - bb[2*i+1], bb[2*i] - aa[2*i+1]) for i in range(3))
                            if gap > 0:
                                value = {"common_mm3": 0.0, "method": "positive_axis_gap", "axis_gap_lower_mm": gap}
                            else:
                                left_copy = cq.Shape.cast(BRepBuilderAPI_Copy(parts[left].wrapped, True, False).Shape())
                                right_copy = cq.Shape.cast(BRepBuilderAPI_Copy(parts[right].wrapped, True, False).Shape())
                                value = p.strict_common(left_copy, right_copy)
                            v = value["common_mm3"]
                            if not math.isfinite(v) or v < 0:
                                raise ValueError("invalid directed Common volume")
                            row = {"a": left, "b": right, **value, "rejected": v > TOL}
                            counts[value["method"]] += 1
                            delta = None if prior.get("evaluation_failed") else v - prior["common_mm3"]
                            agrees = delta is not None and abs(delta) <= TOL and row["rejected"] == prior["rejected"]
                            row.update(factory_volume_difference_mm3=delta, factory_classification_and_volume_agree=agrees)
                            if delta is not None:
                                summary["maximum_volume_difference_mm3"] = max(summary["maximum_volume_difference_mm3"], abs(delta))
                            if not agrees:
                                summary["mismatches"].append(row)
                            if row["rejected"]:
                                summary["rejected_pairs"].append(row)
                        except Exception as exc:
                            row = {"a": left, "b": right, "evaluation_failed": True, "error": type(exc).__name__ + ": " + str(exc)}
                            summary["evaluation_failures"].append(row)
                        f.write(json.dumps(row, allow_nan=False) + "\n")
                        summary["count"] += 1
                        if (index + 1) % 512 == 0:
                            f.flush(); print(json.dumps({"reader_state": name, "pairs": index + 1}), flush=True)
                final_hashes = {n: body_hash(body) for n, body in parts.items()}
                summary["all_original_BREP_bytes_unchanged"] = all(final_hashes[n] == frozen[n]["BREP"] for n in parts)
                write(target / "frozen_participants_after.json", final_hashes)
                summary["positive_axis_gaps_use_prevalidated_frozen_participants"] = True
                summary["native_Common_uses_original_strict_common_on_explicit_deep_geometry_copies"] = True
                summary["method_counts"] = dict(counts)
                summary["file"] = rec(target / "pairs.jsonl")
                actual_pairs = [(x["a"], x["b"]) for x in
                                (json.loads(line) for line in (target / "pairs.jsonl").read_text().splitlines())]
                summary["reader_pair_roster_equals_complete_combinations"] = actual_pairs == expected_pairs
                sr["pairs"] = summary
                sr["completed"] = summary["reader_pair_roster_equals_complete_combinations"] and not summary["evaluation_failures"] and summary["all_original_BREP_bytes_unchanged"]
                sr["finite_pose_clear"] = bool(sr["completed"] and not summary["mismatches"] and not summary["rejected_pairs"] and sr["independent_native_early_gates_passed"])
            except BaseException as exc:
                sr["failure"] = type(exc).__name__ + ": " + str(exc)
                sr["traceback"] = traceback.format_exc()
            sr["seconds"] = time.monotonic() - state_start
            write(target / "report.json", sr); write(out / "report.json", r)
            print(json.dumps({"reader_state": name, "completed": sr["completed"], "clear": sr.get("finite_pose_clear"), "failure": sr.get("failure")}), flush=True)
        r["selected_report_after"] = rec(selected_report)
        r["selected_report_unchanged"] = r["selected_report_after"] == selected_report_before
        r["completed"] = all(x["completed"] for x in r["states"].values()) and r["selected_report_unchanged"]
    except BaseException as exc:
        r["failure"] = type(exc).__name__ + ": " + str(exc)
        r["traceback"] = traceback.format_exc()
    r["producer_module_imported"] = "run_independent_states" in sys.modules
    r["candidate_builders_imported"] = any(n in sys.modules for n in ("panel_key_travel_stops_v1", "key_forward_loop_v1"))
    r["source_bytes_unchanged"] = before == catalog(source)
    r["helper_bytes_unchanged"] = helper_before == catalog(helpers)
    r["seconds"] = time.monotonic() - start
    r["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    write(out / "report.json", r)
    return 0 if r["completed"] and r["source_bytes_unchanged"] and r["helper_bytes_unchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
