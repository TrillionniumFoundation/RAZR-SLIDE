"""Independent exact filling checks and new native readback/Common execution."""
import argparse
import copy
import datetime as dt
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def identity(path):
    p = Path(path)
    return {"path": str(p.resolve()), "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (805306368, 805306368))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("120-second reader budget")))
    signal.alarm(120)
    report = {"schema": "razr-r12-independent-filled-carrier-and-native-readback-v1", "completed": False,
              "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "limits": {"seconds": 120, "address_space_bytes": 805306368, "cpus": 1},
              "cases": [], "controls": [], "negative_controls": [],
              "producer_construction_not_imported": True,
              "full_continuous_G2": False, "complete_region_union_proved": False,
              "native_boundary_set_identity_proved": False, "uniform_compiled_geometry_error_proved": False,
              "original_initial_q_sweep_for_016_to_019_proved": False,
              "G3_pass": False, "G4_pass": False, "G5_pass": False, "release_go": False}
    events = Path("/sys/fs/cgroup/memory.events")
    report["shared_memory_events_before"] = events.read_text() if events.exists() else None
    try:
        import check_filling_r12 as check
        need = check.need
        sys.path.insert(0, str(args.inputs / "dependencies"))
        sys.path.insert(0, str(args.inputs / "dependencies/l1-local-rebuild"))
        import native_local_inventory_r11 as inv
        import check_local_cover_r11 as original_check
        import check_hybrid_axis_mask_r11 as box_check
        import audit_native_uv_orientation_r11 as orientation
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
        from OCP.TopTools import TopTools_ListOfShape
        import OCP
        raw = inv.raw
        manifest = json.loads((args.inputs / "manifest.json").read_text())
        need(manifest["completed"], "complete exact original inputs")
        for record in manifest["files"].values():
            actual = identity(args.inputs / record["relative"])
            need(all(actual[k] == record[k] for k in ("bytes", "sha256")), "every copied original unchanged")
        def mapped(item):
            record = manifest["files"][item["path"]]
            need(all(record[k] == item[k] for k in ("bytes", "sha256")), "original-reference binding")
            return args.inputs / record["relative"]
        producer = json.loads((args.producer / "report.json").read_text())
        need(producer["completed"] and producer["recorded_budget_passed"], "completed original-budget producer")
        report["producer_report"] = identity(args.producer / "report.json")
        report["input_manifest"] = identity(args.inputs / "manifest.json")
        need(all(producer["input_manifest"][k] == report["input_manifest"][k] for k in ("bytes", "sha256")), "same input manifest")
        payload_path = args.producer / "certificates.json"
        need(all(identity(payload_path)[k] == producer["certificate"][k] for k in ("bytes", "sha256")), "actual produced certificate unchanged")
        payload = json.loads(payload_path.read_text())
        need(F(payload["original_threshold_exact"]) == F(producer["original_threshold_exact"]) == F(1e-7), "unaltered original float64 threshold")
        prior = json.loads((args.inputs / "prior-producer.json").read_text())
        need(prior["completed"] and prior["recorded_budget_passed"] and F(prior["original_gate_exact"]) == F(1e-7), "same complete R11 gate")
        report["original_R11_producer_reference"] = manifest["original_producer"]
        report["sources"] = [identity(module.__file__) for module in (check, inv, original_check, box_check, orientation, raw)] + [identity(__file__)]
        report["OCP_version"] = getattr(OCP, "__version__", None)
        report["actual_loaded_native_extensions"] = [identity(module.__file__) for name,module in list(sys.modules.items())
                                                      if name.startswith("OCP") and str(getattr(module,"__file__","")).endswith(".so")]
        need(report["actual_loaded_native_extensions"], "actual imported CAD binary identity")

        def reject(name, mutated, callable_check):
            path = args.output / (name + ".json")
            path.write_text(json.dumps(mutated, indent=2) + "\n")
            try:
                callable_check(mutated)
            except (ValueError, KeyError, IndexError) as exc:
                report["negative_controls"].append({"name": name, "rejected": True,
                                                     "reason": str(exc), "input": identity(path)})
            else:
                raise ValueError("invalid certificate accepted: " + name)

        for control in payload["controls"]:
            proof = control["certificate"]
            checked = check.check_completion(proof)
            expected = {"original_hollow_shell": F(1), "positive_thin_shell": F(1,1<<80),
                        "touching_projection_singleton": F(2)}[control["name"]]
            need(F(checked["filled_carrier_volume_exact"]) == F(control["expected_filled_volume_exact"]) == expected, "known exact fill-control volume")
            row = {"name": control["name"], "check": checked}
            if control["name"] == "original_hollow_shell":
                boundary_volume = check.all_box_union_volume(proof["boundary_boxes_exact"])
                fixed = [["3/8","5/8"]]*3
                recovered = check.carrier_intersection_volume(proof,fixed)
                need(boundary_volume == F(7,8) and recovered == F(1,64), "original hollow-boundary failure repaired by actual fill")
                row.update(original_boundary_union_volume_exact=str(boundary_volume), omitted_material_volume_exact="1/8",
                           recovered_intersection_exact=str(recovered), old_boundary_only_proof_still_invalid=True)
                changed = copy.deepcopy(proof)
                changed["cells"].pop(len(changed["cells"])//2)
                reject("delete_filled_fibre_cell",changed,check.check_completion)
            if control["name"] == "positive_thin_shell":
                need(expected > 0, "positive tiny thickness retained")
                changed = copy.deepcopy(proof)
                nonzero = next(c for c in changed["cells"] if check.dimensions_volume(check.bounds(c["bounds_exact"])) > 0)
                nonzero["bounds_exact"][0][1] = nonzero["bounds_exact"][0][0]
                reject("drop_positive_tiny_fibre_volume",changed,check.check_completion)
            if control["name"] == "touching_projection_singleton":
                candidates = [c for c in proof["cells"] if c["bounds_exact"][1] == ["1","1"] and c["bounds_exact"][0] == ["0","3"]]
                need(candidates, "touch-only projected endpoints have their complete X bridge")
                changed = copy.deepcopy(proof)
                changed["cells"] = [c for c in changed["cells"] if c["bounds_exact"][1] != ["1","1"]]
                reject("delete_touch_only_singleton_fibres",changed,check.check_completion)
            report["controls"].append(row)
        need([r["case_id"] for r in prior["cases"]] == [c["case_id"] for c in payload["local_cases"]] == [f"case-{i:03}" for i in range(11,20)], "all nine original local cases")
        totals = {"original_cases": 0, "original_BREPs_reread": 0, "original_carriers_reread": 0,
                  "new_independent_Common_calls": 0, "complete_directed_box_face_loops": 0,
                  "fixed_fibre_atoms": 0, "strict_leaf_fibre_comparisons": 0,
                  "whole_fixed_cap_pcurves_checked": 0, "whole_fixed_line_and_vertex_radial_checks": 0}
        for row,certificate in zip(prior["cases"],payload["local_cases"]):
            result = json.loads(mapped(row["input_references"]["copied_result"]).read_text())
            native_shapes = {}
            for item in row["input_references"]["materials"]:
                native = inv.read_original(mapped(item["copied"]))
                native_shapes[item["role"]] = native
                if item["role"] == "old_failure":
                    need(raw.metrics(native) == row["old_failure_metrics_new_actual_read"], "original failed object unchanged")
                else:
                    need(inv.inventory(native) == row[item["role"]+"_inventory"], "entire native original geometry and trim reread")
                totals["original_BREPs_reread"] += 1
            proof = check.local_filling(row,result,certificate,original_check)
            output = args.output / row["case_id"]
            output.mkdir()
            native_checks = []
            for leaf in row["native_leaves"]:
                native = raw.read_binary(mapped(leaf["carrier"]))
                inventory = raw.inventory(native)
                need(inventory == leaf["carrier_inventory"], "same original carrier entire inventory")
                node = row["nodes"][leaf["node_id"]]
                checked = box_check.native_box(inventory,node["box_exact"])
                directed = orientation.audit({"label": row["case_id"]+":"+str(leaf["node_id"]),
                                              "inventory": inventory, "bounds_exact": node["box_exact"],
                                              "native_file": identity(mapped(leaf["carrier"]))})
                need(checked["directed_volume_exact"] == directed["exact_native_world_boundary_flux_volume"] == leaf["carrier_positive_directed_volume_exact"], "entire positive carrier volume and orientation")
                old_common = raw.read_binary(mapped(leaf["Common"]))
                need(raw.metrics(old_common) == leaf["Common_metrics"], "actual original Common bytes and observation retained")
                left,right = TopTools_ListOfShape(),TopTools_ListOfShape()
                left.Append(native);right.Append(native_shapes["fixed"])
                op = BRepAlgoAPI_Common();op.SetArguments(left);op.SetTools(right);op.SetRunParallel(False);op.Build()
                need(op.IsDone(), "new independent Common completed")
                common = op.Shape();metrics = raw.metrics(common)
                target = output / f"node-{leaf['node_id']:04}-new-independent-Common.brep"
                saved = raw.write_binary(common,target)
                need(metrics["native_valid"] and metrics["signed_volume_float"] == 0 and all(v == 0 for v in metrics["counts"].values()), "new actual empty Common agrees with strict complete-filling separation")
                need(metrics == leaf["Common_metrics"], "new observation agrees with prior independent execution")
                native_checks.append({"node_id":leaf["node_id"],"carrier":identity(mapped(leaf["carrier"])),
                                      "new_Common":saved,"metrics":metrics,"directed_volume_exact":checked["directed_volume_exact"]})
                totals["original_carriers_reread"] += 1
                totals["new_independent_Common_calls"] += 1
                totals["complete_directed_box_face_loops"] += 6
            report["cases"].append({"case_id":row["case_id"],"exact_model_filling_check":proof,"native_checks":native_checks,
                                    "actual_original_failure_preserved":True,"original_local_threshold_pass_under_stated_model":True})
            totals["original_cases"] += 1
            for key in ("fixed_fibre_atoms","strict_leaf_fibre_comparisons","whole_fixed_cap_pcurves_checked","whole_fixed_line_and_vertex_radial_checks"):
                totals[key] += proof[key]
            if totals["original_cases"] == 1:
                changed = copy.deepcopy(certificate)
                next(f for f in changed["fixed_fibres"] if f["active_faces"])["active_faces"].pop()
                reject("omit_actual_active_fixed_face",changed,lambda c:check.local_filling(row,result,c,original_check))
                changed = copy.deepcopy(certificate)
                next(f for f in changed["fixed_fibres"] if f["active_faces"])["radius_square_upper_exact"] = "0"
                reject("zero_positive_fixed_radius",changed,lambda c:check.local_filling(row,result,c,original_check))
                changed = copy.deepcopy(certificate);changed["native_boundary_set_identity_proved"] = True
                reject("promote_unproved_native_identity",changed,lambda c:check.local_filling(row,result,c,original_check))
                changed = copy.deepcopy(row);changed["source_support"]["remaining_vectors_exact"][-1] = ["0","0","0"]
                reject("remove_original_nonzero_displacement",changed,lambda r:check.local_filling(r,result,certificate,original_check))
        report["totals"] = totals
        report["exact_model_boundary_to_compact_filling_implication_verified"] = True
        report["original_hollow_shell_failure_preserved_and_fibre_completion_verified"] = True
        need("filling_model_r12" not in sys.modules and "produce_filling_r12" not in sys.modules, "independent reader does not import certificate producer")
        report["completed"] = True
    except Exception as exc:
        report["failure"] = {"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        signal.alarm(0)
        report["seconds"] = time.monotonic()-start
        report["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        report["recorded_budget_passed"] = report["completed"] and report["seconds"] <= 120
        report["shared_memory_events_after"] = events.read_text() if events.exists() else None
        (args.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report.get(k) for k in ("completed","totals","seconds","peak_RSS_bytes","failure")}))
    if not report["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
