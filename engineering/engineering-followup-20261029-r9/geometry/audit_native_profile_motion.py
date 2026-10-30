"""Bind retained q=0 geometry and actual R9 STOP/SPRING signatures to profiles.

Reads the recorded native signatures and their SHA-bound source files. Performs
no new CAD construction and makes no force, preload, or physical-domain claim.
"""
import argparse
import hashlib
import json
from pathlib import Path


def rec(path):
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-domain", required=True, type=Path)
    ap.add_argument("--reference-q0", required=True, type=Path)
    ap.add_argument("--k3-binding", required=True, type=Path)
    ap.add_argument("--state-reports", nargs="+", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    source = json.loads(a.source_domain.read_text())
    binding = json.loads(a.k3_binding.read_text())
    if rec(a.reference_q0)["sha256"] != binding["poses"]["stow_tabs_3"]["projection_sha256"]["factory"]:
        raise ValueError("retained q0 whole-factory report identity differs")
    old = json.loads(a.reference_q0.read_text())["engineering_record"]
    out = {"schema": "razr-r9-native-STOP-SPRING-profile-motion-readback-v1",
           "script": rec(__file__), "source_domain": rec(a.source_domain),
           "reference_q0": rec(a.reference_q0), "binding": rec(a.k3_binding),
           "states": {}, "all_source_native_bounds_mappings_pass": True,
           "signature_bound_tolerance_mm": 1e-7,
           "new_CAD_execution_by_this_reader": False,
           "real_spring_free_length_stiffness_preload_or_force_proved": False,
           "physical_allowed_domain_proved": False}
    for path in a.state_reports:
        actual = json.loads(path.read_text()); name = actual["state"]
        predictions = source["states"][name]
        row = {"actual_full_factory_report": rec(path), "bodies": {},
               "all_source_native_bounds_mappings_pass": True}
        for side in "LR":
            if actual["actual_q_by_side_mm"][side] != predictions["cam_STOP_i_and_SPRING"][side][0]["q_mm"]:
                raise ValueError("actual source q does not match explicit profile prediction")
            for pred in predictions["cam_STOP_i_and_SPRING"][side]:
                i = pred["contact_index"]
                for kind in ("STOP", "SPRING"):
                    body_name = f"{side}_STOP_{i}" if kind == "STOP" else f"{side}_SPRING_{i}_OD_TOL_ENVELOPE"
                    new_entry = actual["body_exports"][body_name]
                    old_entry = old["body_exports"][body_name]
                    previous = old_entry["signature_before"]["bounds_mm"]
                    observed = new_entry["signature"]["bounds_mm"]
                    delta = [0.0] * 6
                    if kind == "STOP":
                        delta[0] = delta[1] = pred["STOP_X_translation_mm"]
                    else:
                        delta[0] = pred["SPRING_X_lower_endpoint_delta_mm"]
                        delta[1] = pred["SPRING_X_upper_endpoint_delta_mm"]
                    predicted = [x+d for x, d in zip(previous, delta)]
                    errors = [v-u for u, v in zip(predicted, observed)]
                    passed = max(map(abs, errors)) <= 1e-7
                    row["bodies"][body_name] = {"original_q0_files": old_entry["files"],
                        "actual_current_files": new_entry["files"],
                        "source_q_mm": pred["q_mm"], "source_branch": pred["selected_source_branch"],
                        "original_q0_bounds_mm": previous, "predicted_bounds_mm": predicted,
                        "actual_native_bounds_mm": observed, "actual_minus_predicted_mm": errors,
                        "maximum_abs_bound_difference_mm": max(map(abs, errors)), "passed": passed}
                    row["all_source_native_bounds_mappings_pass"] &= passed
        out["states"][name] = row
        out["all_source_native_bounds_mappings_pass"] &= row["all_source_native_bounds_mappings_pass"]
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"states": len(out["states"]), "all_source_native_bounds_mappings_pass": out["all_source_native_bounds_mappings_pass"]}))
    return 0 if out["all_source_native_bounds_mappings_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
