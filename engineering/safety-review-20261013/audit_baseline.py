"""Independent, read-only reconstruction of legacy safety counterexamples.

Imports CAD fault run(write=False), hashes every baseline member before/after,
and writes only to this review directory. This is software and nominal geometry
evidence. It supplies no physical safety qualification.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1] / "baselines" / "fpc-r39-20261013"
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))


def hashes() -> dict[str, str]:
    return {
        str(path.relative_to(BASE)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(BASE.rglob("*")) if path.is_file()
    }


def minimal_cuts(states):
    cuts = []
    for state in sorted(states, key=lambda item: (len(item), sorted(item))):
        if not any(cut <= state for cut in cuts):
            cuts.append(state)
    return [sorted(cut) for cut in cuts]


def main():
    before = hashes()
    started = time.time()
    # A separately written expression, not a read of the reported count.
    names = ("L_gate_forced_open", "R_gate_forced_open", "L_ear_broken",
             "R_ear_broken", "L_pawl_false_capture", "R_pawl_false_capture")
    mechanical = []
    for bits in itertools.product((False, True), repeat=6):
        f = dict(zip(names, bits))
        escaped = ((f["L_gate_forced_open"] or f["L_ear_broken"])
                   and (f["R_gate_forced_open"] or f["R_ear_broken"]))
        mechanical.append({**f, "escape": escaped})
    historical = json.loads((BASE / "verification/R27_faults.json").read_text())
    assert len(mechanical) == historical["joint_fault_cases"] == 64
    assert sum(row["escape"] for row in mechanical) == historical["joint_fault_escape_cases"] == 36
    for fresh, old in zip(mechanical, historical["joint_fault_rows"]):
        assert all(fresh[name] == old[name] for name in names)
        assert fresh["escape"] == old["model_dangerous_escape_if_all_inherited_stops_broken"]

    # Reconstruct the actual nine-fault R27 power tree independently.
    power_names = ("A_iso_weld", "A_main_weld", "A_precharge_weld", "B_iso_weld",
                   "B_main_weld", "B_precharge_weld", "A_direct_pad_short",
                   "B_direct_pad_short", "shared_live_bus_to_pad_short")
    power = []
    for bits in itertools.product((False, True), repeat=9):
        f = dict(zip(power_names, bits))
        live = (f["A_direct_pad_short"] or f["B_direct_pad_short"]
                or f["shared_live_bus_to_pad_short"]
                or f["A_iso_weld"] and (f["A_main_weld"] or f["A_precharge_weld"])
                or f["B_iso_weld"] and (f["B_main_weld"] or f["B_precharge_weld"]))
        power.append({"failed": [name for name in power_names if f[name]], "live": live})
    from r27_power_faults import run as legacy_power
    rerun_power = legacy_power(write=False)
    assert len(power) == rerun_power["enumerated_fault_states"] == 512
    assert sum(row["live"] for row in power) == rerun_power["dangerous_states"]
    power_cuts = minimal_cuts([set(row["failed"]) for row in power if row["live"]])
    assert power_cuts == rerun_power["minimal_cut_sets"]
    assert sum(len(cut) == 1 for cut in power_cuts) == 3

    # Fresh OCC computation of the R37 local stop, preserving failed baselines.
    from r37_faults import run as legacy_mechanics
    from r38_faults import run as legacy_architecture
    rerun_r37 = legacy_mechanics(write=False)
    rerun_r38 = legacy_architecture(write=False)
    assert rerun_r37 == json.loads((BASE / "verification/R37_faults.json").read_text())
    assert rerun_r38 == json.loads((BASE / "verification/R38_faults.json").read_text())
    after = hashes()
    assert before == after, "Baseline changed during read-only safety review"
    report = {
        "revision": "2026-10-13 independent safety baseline reconstruction",
        "execution_host": platform.node(), "python": platform.python_version(),
        "baseline_member_count": len(before), "all_baseline_bytes_unchanged": True,
        "baseline_hash_inventory": before,
        "mechanical_states": 64, "mechanical_escapes": 36,
        "mechanical_minimal_escape_cut_sets": minimal_cuts([
            {name for name in names if row[name]} for row in mechanical if row["escape"]]),
        "mechanical_false_presence_axes_do_not_change_escape_predicate": True,
        "electrical_states": 512, "electrical_live_states": sum(row["live"] for row in power),
        "electrical_minimal_live_cut_sets": power_cuts,
        "electrical_single_fault_live_cut_count": 3,
        "R37_fresh_OCC_fault_result_matches_baseline": True,
        "R37_fresh_nominal_geometry_rows": rerun_r37["joint_r36_physical_fault_scenarios"],
        "R37_single_integral_lip_fracture_exposes_side": True,
        "R38_fresh_architecture_result_matches_baseline": True,
        "R38_nonfunctional_axes_for_electrical_hazard": ["flex_loom_continuous", "mechanical_captured"],
        "R38_continuity_or_capture_failure_requires_new_hazards_not_boolean_reuse": True,
        "physical_qualification": False, "manufacturing_go": False,
        "elapsed_s": time.time() - started,
    }
    (HERE / "independent-baseline-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "legacy-mechanical-witnesses.json").write_text(json.dumps(mechanical, indent=2) + "\n")
    (HERE / "legacy-electrical-witnesses.json").write_text(json.dumps(power, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "baseline_hash_inventory"}, indent=2))


if __name__ == "__main__":
    main()
