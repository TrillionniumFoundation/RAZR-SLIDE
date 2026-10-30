"""Freeze four producer and completed-reader costs before four original states.

The fourth asynchronous reader may still be running. It is explicitly recorded
as pending and supplies no passing result or completed runtime estimate.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent


def rec(path):
    data = Path(path).read_bytes()
    return {"path": str(Path(path).relative_to(HERE)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def main():
    destination = HERE / "CAPACITY_BASIS_V3.json"
    if destination.exists():
        raise FileExistsError(destination)
    snapshot_root = HERE / "capacity-v3-inputs"
    snapshot_root.mkdir(exist_ok=False)
    sources = {
        "lower_L_contact_R_free": ("producer-attempt1", "reader-first-v2-attempt1"),
        "lower_R_contact_L_free": ("producer-v2-attempt1", "reader-lower-R-v2-attempt1"),
        "upper_L_contact_R_free": ("producer-v2-attempt1", "reader-upper-L-v2-attempt1"),
        "upper_R_contact_L_free": ("producer-v2-attempt1", "reader-upper-R-v2-attempt1"),
    }
    observations = {}
    for name, (producer, reader) in sources.items():
        pp = HERE / producer / name / "report.json"
        rr = HERE / reader / "report.json"
        p = json.loads(pp.read_text())
        reader_bytes = rr.read_bytes()
        snapshot = snapshot_root / (name + ".reader.original.json")
        snapshot.write_bytes(reader_bytes)
        reader_result = json.loads(reader_bytes)
        r = reader_result["states"].get(name, {})
        if not p["completed"]:
            raise ValueError("prior producer state incomplete: " + name)
        reader_complete = reader_result["completed"] and r.get("completed", False)
        observations[name] = {
            "producer_leaf": rec(pp), "reader_campaign_snapshot": rec(snapshot),
            "reader_observed_path": str(rr.relative_to(HERE)),
            "reader_completed_when_capacity_recorded": reader_complete,
            "producer_seconds": p["seconds"], "producer_matrix_seconds": p["pairs"]["seconds"],
            "reader_seconds": r.get("seconds") if reader_complete else None,
            "reader_peak_RSS_bytes": reader_result.get("peak_RSS_bytes") if reader_complete else None,
            "producer_pair_count": p["pairs"]["count"],
            "reader_pair_count": r.get("pairs", {}).get("count") if reader_complete else None,
            "producer_clear": p["finite_pose_clear"], "reader_clear": r.get("finite_pose_clear") if reader_complete else None,
            "applicable_original_early_gates": len(r.get("independent_native_early_gates", {})) if reader_complete else None,
            "method": "original_v1" if name == "lower_L_contact_R_free" else "frozen_v2",
        }
    producer_v2_file = HERE / "producer-v2-attempt1/report.json"
    p2 = json.loads(producer_v2_file.read_text())
    if not p2["completed"]:
        raise ValueError("v2 three-state campaign not complete")
    v2_costs = [x["producer_seconds"] for x in observations.values() if x["method"] == "frozen_v2"]
    reader_costs = [x["reader_seconds"] for x in observations.values() if x["reader_completed_when_capacity_recorded"]]
    if len(reader_costs) < 3:
        raise ValueError("at least three completed independent reader measurements required")
    extra_open_pairs_ratio = 12880 / 11781
    planning_producer_seconds = max(v2_costs) * (3 + extra_open_pairs_ratio) * 1.5 + 180
    planning_reader_seconds = max(reader_costs) * (3 + extra_open_pairs_ratio) * 1.5
    cgroup = Path("/sys/fs/cgroup")
    resource_snapshot = {n: (cgroup / n).read_text().strip()
                         for n in ("memory.current", "memory.max", "memory.events", "memory.stat", "cpu.max")}
    out = {
        "schema": "razr-r9-remaining-original-four-states-measured-capacity-v3",
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "script": rec(__file__),
        "prior_four_asymmetric_producers_completed_and_at_least_three_readers_completed": True,
        "prior_four_asymmetric_states_completed_and_read_back": len(reader_costs) == 4,
        "completed_independent_reader_count": len(reader_costs),
        "pending_independent_readers": [n for n, x in observations.items() if not x["reader_completed_when_capacity_recorded"]],
        "capacity_scope": "All four actual full factories and at least three complete independent reader runs supply the estimate. A pending fourth reader is not treated as a result; one remaining-states producer may pipeline with it under the existing one-producer/one-reader cap.",
        "prior_states": observations, "prior_v2_campaign": rec(producer_v2_file),
        "prior_v2_campaign_seconds": p2["seconds"],
        "prior_v2_peak_RSS_bytes": p2["peak_RSS_bytes"],
        "requested_states": ["stow_tabs_0", "stow_tabs_3", "predock", "open_installed"],
        "source_state_inputs_changed": False,
        "expected_complete_unordered_pairs": {"stow_tabs_0": 11781, "stow_tabs_3": 11781,
                                             "predock": 11781, "open_installed": 12880},
        "expected_pair_total_per_producer_or_reader": 48223,
        "planning_method": "Maximum actual frozen-v2 state cost, scaled by all four original matrix sizes, 1.5 resource-contention factor; producer additionally 180 seconds prerequisite allowance. This is a capacity estimate, not an execution result.",
        "planning_producer_seconds": planning_producer_seconds,
        "planning_reader_seconds_serial_sum": planning_reader_seconds,
        "producer_wall_budget_seconds": 3600,
        "reader_wall_budget_seconds_per_selected_state": 3600,
        "worker_RSS_guard_bytes": 2 * 2**30,
        "concurrency_cap": {"producer": 1, "reader": 1},
        "shared_cgroup_resource_snapshot": resource_snapshot,
        "disk_free_bytes": shutil.disk_usage(HERE).free,
        "resource_reservation_guaranteed": False,
        "resource_competition_policy": "One producer and at most one independent reader; no three-state fanout. Preserve timeout, exception, partial export and failed pair records rather than declare completion.",
        "predicate": "Original whole-material/signed-volume topology checks and 1e-7 mm3 Common gate; frozen AddOptimal positive gaps only for immutable participants; potential overlap uses original strict_common on deep geometry copies.",
        "OPEN_inventory": "161 original full-factory participants, requiring all 12880 unordered pairs",
        "full_continuous_G2": False,
        "physical_allowed_domain_proved": False,
    }
    if planning_producer_seconds > out["producer_wall_budget_seconds"]:
        raise ValueError("measured planning estimate exceeds proposed producer budget")
    destination.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"capacity_basis": str(destination), "planning_producer_seconds": planning_producer_seconds,
                      "planning_reader_seconds_serial_sum": planning_reader_seconds}))


if __name__ == "__main__":
    main()
