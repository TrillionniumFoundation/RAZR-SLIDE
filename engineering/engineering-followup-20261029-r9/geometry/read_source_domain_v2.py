"""Read exact retained positive-q profiles and independent input domains.

Source semantics only. K3 panel Y travel stops and cam STOP_i X-moving
participants are kept separate. Neither selected branch nor source admissibility
establishes physical restoring force, contact maintenance, or reachability.
"""
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys


def record(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--s4-root", required=True, type=Path)
    ap.add_argument("--helpers-root", required=True, type=Path)
    ap.add_argument("--profiles-root", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    sys.path[:0] = [str(a.s4_root.resolve() / "integration"), str(a.helpers_root.resolve())]
    import cam_contact_profile as profile_module
    import full_stop_states as states
    fields = {f.name for f in dataclasses.fields(profile_module.ContactProfile)}
    profiles = {}
    for side in "LR":
        profiles[side] = []
        for i in range(2):
            path = a.profiles_root / f"{side}_contact{i}.profile.original.json"
            raw = json.loads(path.read_text())
            p = profile_module.ContactProfile(**{k: raw[k] for k in fields})
            if list(p.breakpoints) != raw["breakpoints_q_mm"]:
                raise ValueError("exact original breakpoint values differ")
            profiles[side].append((p, raw, path))
    result = {"schema": "razr-r9-source-positive-q-and-independent-domain-all-ten-v2",
              "script": record(__file__), "profile_source": record(profile_module.__file__),
              "original_state_source": record(states.__file__), "profiles": {}, "states": {},
              "source_model_only": True, "new_CAD_execution_by_this_reader": False,
              "physical_allowed_domain_proved": False, "restoring_force_or_preload_proved": False,
              "cam_STOP_i_and_panel_travel_stops_are_distinct": True,
              "source_defined_independent_input_domain": {
                  "slide_mm": [0.0, 79.75], "descent_mm": [0.0, 8.2],
                  "positive_descent_requires_full_slide": True,
                  "independent_manual_tab_mm_per_side": [0.0, 3.0],
                  "independent_flank_per_side": [-1.0, 1.0],
                  "q_per_side": "q=K*slide+dq, K=12/79.75; each original profile requires 0<=q<=12 without clamping",
                  "crosshead_KEY_constraints": "abs(dx)<=(.425-.4)*hypot(1,K)+1e-7; abs(dx-dq)<=(.425-.4)*sqrt(2)+1e-7 independently per side",
                  "telescope_per_side": "Three independent side-specific joints, .1-1e-7<=j<=2.9+1e-7; abs(sum(j)-8.5+descent)<=1e-7",
                  "equal_telescope_allocation_is_physical_constraint": False,
                  "OPEN_accessory_condition": "hold/support flags require slide=79.75 and descent=8.2",
                  "these_binary64_source_constraints_prove_real_allowed_domain": False}}
    for side, items in profiles.items():
        result["profiles"][side] = []
        for i, (p, raw, path) in enumerate(items):
            aa, bb, cc = p.breakpoints
            result["profiles"][side].append({"contact_index": i, "original_file": record(path),
                "complete_original_values": raw,
                "positive_q_branches": [
                    {"branch": "plateau", "interval": "(0,a]", "a_mm": aa},
                    {"branch": "rounded_corner", "interval": "(a,b)", "a_mm": aa, "b_mm": bb},
                    {"branch": "ramp", "interval": "[b,c)", "b_mm": bb, "c_mm": cc},
                    {"branch": "lower_stop", "interval": "[c,12]", "c_mm": cc}],
                "q_zero_branch": p.evaluate(0.0)[2]})
    result["original_state_roster"] = list(states.STATES)
    result["domain_source_files"] = {n: record(a.s4_root / "integration" / n) for n in ("product_nominal_motion.py", "product_assembly.py", "verify_cam_coupling.py", "product_split_assembly.py")}
    for name in states.STATES:
        q_values = states.STATES[name]["actual_binary64_q_from_declared_factory_inputs"]
        result["states"][name] = {"source_state_inputs": states.STATES[name],
            "K3_panel_Y_travel_stop_contacts": states.EXPECTED_CONTACT_ENDS[name],
            "cam_STOP_i_and_SPRING": {}}
        for side, q in zip("LR", q_values):
            sign = -1 if side == "L" else 1
            rows = []
            for i, (p, _, _) in enumerate(profiles[side]):
                h, slope, branch = p.evaluate(q); h0 = p.evaluate(0.0)[0]
                delta = h - h0; move = sign * delta
                rows.append({"contact_index": i, "q_mm": q, "q_binary64_hex": float(q).hex(),
                             "selected_source_branch": branch, "height_mm": h,
                             "height_slope": slope, "reference_height_mm": h0,
                             "STOP_X_translation_mm": move,
                             "SPRING_X_lower_endpoint_delta_mm": min(0.0, move),
                             "SPRING_X_upper_endpoint_delta_mm": max(0.0, move),
                             "SPRING_is_OD_tolerance_envelope": True,
                             "physical_contact_or_force_implied": False})
            result["states"][name]["cam_STOP_i_and_SPRING"][side] = rows
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"profile_count": 4, "state_count": len(result["states"]), "physical_allowed_domain_proved": False}))


if __name__ == "__main__":
    main()
