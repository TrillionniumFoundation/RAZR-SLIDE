"""Execute the four remaining original K3 states against the full S4 factory.

Original source and input bytes are read-only. This is a new-runtime finite
experiment, not a replay claim for the original locked runtime or a physical
domain qualification. Every unordered full-factory pair is evaluated freshly. Frozen-body v2
reuses only validated immutable participant bounds for strict positive gaps.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import importlib.metadata as md
import itertools
import json
import math
from pathlib import Path
import resource
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
TOL = 1e-7
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
STATES = ("stow_tabs_0", "stow_tabs_3", "predock", "open_installed")


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def record(path):
    path = Path(path)
    return {"bytes": path.stat().st_size, "sha256": sha(path)}


def write(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def source_catalog(root):
    return {str(p.relative_to(root)): record(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc")}


class Budget:
    def __init__(self, seconds=3600):
        self.start = time.monotonic()
        self.limit = seconds

    def check(self):
        if time.monotonic() - self.start > self.limit:
            raise TimeoutError("finite-state experiment wall budget exhausted")
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 2 * 2**30:
            raise MemoryError("finite-state worker exceeds 2 GiB RSS")


def signature(body, p):
    solids, volume = p.whole_material(body)
    return {"valid": body.isValid(), "solid_count": len(solids),
            "signed_volume_mm3": volume,
            "solid_signed_volumes_mm3": [x.Volume() for x in solids],
            "bounds_mm": p.bounds(body)}


def export(body, stem, p):
    before = signature(body, p)
    files = {}
    for ext, method in (("brep", body.exportBrep), ("step", body.exportStep)):
        path = stem.with_suffix("." + ext)
        if path.exists():
            raise FileExistsError(path)
        status = method(str(path))
        if ext == "brep" and status is not True:
            raise ValueError("BREP serialization failed")
        if ext == "step" and status != type(status).IFSelect_RetDone:
            raise ValueError("STEP serialization failed")
        files[ext] = {"path": str(path.relative_to(stem.parent.parent)), **record(path)}
    after = signature(body, p)
    if before != after:
        raise ValueError("serialization changed in-memory material")
    return {"signature": before, "files": files, "serialization_preserved_signature": True}


def pairs(parts, out, p, budget):
    from frozen_predicate_v2 import FrozenBodies
    frozen = FrozenBodies(parts, p)
    write(out / "frozen_participants.json", {"records": frozen.records, "deep_copy_implementation": frozen.copy_source})
    rows = []
    counts = Counter()
    start = time.monotonic()
    with (out / "pairs.jsonl").open("x") as f:
        for index, (a, b) in enumerate(itertools.combinations(sorted(parts), 2)):
            budget.check()
            try:
                result = frozen.pair(a, b)
                v = result["common_mm3"]
                if not math.isfinite(v) or v < 0:
                    raise ValueError("invalid directed Common volume")
                row = {"a": a, "b": b, **result, "rejected": v > TOL}
                counts[result["method"]] += 1
                if v > 0:
                    body = parts[a].copy(mesh=False).intersect(parts[b].copy(mesh=False))
                    direct = p.volume(body)
                    if direct < 0 or abs(direct - v) > TOL:
                        raise ValueError("direct Common does not match pair predicate")
                    row["direct_Common_mm3"] = direct
                    row["positive_Common"] = export(body, out / "commons" / f"pair-{index:05d}", p)
            except Exception as exc:
                row = {"a": a, "b": b, "evaluation_failed": True,
                       "error": type(exc).__name__ + ": " + str(exc)}
            rows.append(row)
            f.write(json.dumps(row, allow_nan=False) + "\n")
            if (index + 1) % 512 == 0:
                f.flush()
                print(json.dumps({"state": out.name, "pairs": index + 1,
                                  "seconds": time.monotonic() - start}), flush=True)
    expected_roster = list(itertools.combinations(sorted(parts), 2))
    actual_roster = [(r["a"], r["b"]) for r in rows]
    frozen_after = frozen.check_unchanged()
    write(out / "frozen_participants_after.json", frozen_after)
    return {"count": len(rows), "method_counts": dict(counts),
            "all_original_BREP_bytes_unchanged": frozen_after["all_original_BREP_bytes_unchanged"],
            "positive_gap_uses_prevalidated_frozen_participants": True,
            "native_Common_uses_original_strict_common_on_deep_geometry_copies": True,
            "failed": [x for x in rows if x.get("evaluation_failed")],
            "rejected": [x for x in rows if x.get("rejected")],
            "positive": [x for x in rows if x.get("common_mm3", 0) > 0],
            "all_unordered_pairs_present_once": actual_roster == expected_roster,
            "actual_pair_roster_equals_complete_combinations": actual_roster == expected_roster,
            "freshly_evaluated_all_pairs": True, "certificate_reuse": False,
            "seconds": time.monotonic() - start, "file": record(out / "pairs.jsonl")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--s4-root", type=Path, required=True)
    ap.add_argument("--near-engineering", type=Path, required=True)
    ap.add_argument("--helpers-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--capacity-basis", type=Path, required=True)
    ap.add_argument("--states", nargs="+", choices=STATES, default=list(STATES))
    args = ap.parse_args()
    capacity = json.loads(args.capacity_basis.read_text())
    if not capacity.get("prior_four_asymmetric_producers_completed_and_at_least_three_readers_completed"):
        raise ValueError("four complete producer states and at least three complete reader measurements required")
    if capacity.get("requested_states") != list(STATES):
        raise ValueError("capacity receipt does not bind these four original states")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = args.s4_root.resolve()
    retained = args.near_engineering.resolve()
    originals = args.helpers_root.resolve()
    source_before = source_catalog(source)
    write(out / "S4_SOURCE_CATALOG.json", source_before)
    original_before = source_catalog(originals)
    write(out / "ORIGINAL_HELPERS_CATALOG.json", original_before)
    started = time.monotonic()
    result = {"schema": "razr-r9-remaining-original-full-factory-frozen-v3",
              "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "functional_source_identity": S4,
              "source_identity_kind": "archived_source_bytes; no Git worktree claim",
              "script": record(__file__), "frozen_predicate_script": record(HERE / "frozen_predicate_v2.py"), "states": {}, "completed": False,
              "original_Common_tolerance_mm3": TOL,
              "requested_states": list(args.states),
              "capacity_basis": {"path": str(args.capacity_basis.resolve()), **record(args.capacity_basis)},
              "capacity_budget_seconds": 3600,
              "source_inputs_reused_without_change": True,
              "runtime": {"python": sys.version, "executable": sys.executable,
                          "packages": {n: md.version(n) for n in ("cadquery", "cadquery-ocp", "numpy", "scipy")}},
              "original_locked_runtime_replayed": False,
              "full_continuous_G2": False, "physical_allowed_domain_proved": False,
              "physical_qualification": False, "manufacturing_go": False}
    write(out / "report.json", result)
    try:
        sys.path[:0] = [str(originals), str(source / "integration")]
        import cadquery as cq
        import product_nominal_motion as nominal
        import verify_cam_coupling as cam
        import frozen_key_factory_adapter as adapter
        import actual_stop_prerequisite as prerequisite
        import panel_key_travel_stops_v1 as candidate
        import full_stop_states as states
        p = nominal.p
        budget = Budget(3600)
        binding = json.loads((originals / "K3FULL_K3_BINDING.json").read_text())
        key_binding = json.loads((originals / "K3FULL_K1_BINDING.json").read_text())
        verified = prerequisite.load({name: retained / ("prerequisite-" + name)
                                      for name in ("stow_tabs_3", "predock")},
                                     binding, key_binding, p, cq, budget)
        result["prerequisite_receipt"] = verified.receipt
        write(out / "report.json", result)
        for name in args.states:
            target = out / name
            target.mkdir()
            (target / "bodies").mkdir()
            (target / "commons").mkdir()
            (target / "materials").mkdir()
            state_start = time.monotonic()
            r = {"state": name, "completed": False}
            result["states"][name] = r
            try:
                r["original_state_record"] = json.loads(json.dumps(states.STATES[name]))
                r["original_expected_contact_ends"] = states.EXPECTED_CONTACT_ENDS[name]
                spec = dict(states.STATES[name])
                expected_bodies = spec.pop("expected_bodies")
                expected_q = spec.pop("actual_binary64_q_from_declared_factory_inputs")
                r["input"] = spec
                r["expected_full_factory_bodies"] = expected_bodies
                r["expected_complete_pair_count"] = expected_bodies * (expected_bodies - 1) // 2
                baseline, meta = adapter.full_scene(verified.keys, nominal, cam, p, **spec)
                if len(baseline) != expected_bodies:
                    raise ValueError("original full-factory inventory differs")
                q = {s: cam.K * spec["slide"] + dq for s, dq in zip("LR", spec["key_offsets"])}
                if [q[s] for s in "LR"] != expected_q:
                    raise ValueError("original binary64 state q differs")
                parts, materials, receipt = candidate.apply(baseline, meta, p, originals / "KEY_FORWARD_LOOP_V1_CONTRACT.json")
                r.update(actual_q_by_side_mm=q, native_scene_metadata=meta,
                         candidate_application=receipt, participant_names=sorted(parts),
                         original_panel_mapping=adapter.compare(baseline["A_BACK_PANEL"], verified.original_panel, p),
                         candidate_panel_mapping=adapter.compare(parts["A_BACK_PANEL"], verified.candidate_panel, p))
                # Retain the full factory before checking potentially failing contacts.
                r["body_exports"] = {n: export(body, target / "bodies" / n, p) for n, body in sorted(parts.items())}
                r["material_exports"] = {n: export(body, target / "materials" / n, p)
                                         for n, body in materials.items() if body.Solids()}
                write(target / "report.json", r)
                checks, controls = candidate.endpoint_and_overtravel_checks(parts, verified.keys, p,
                                      originals / "KEY_FORWARD_LOOP_V1_CONTRACT.json", q)
                r["endpoint_and_overtravel_checks"] = checks
                for side in "LR":
                    expected = states.EXPECTED_CONTACT_ENDS[name][side]
                    if set(checks[side]["endpoint_contacts"]) != ({expected} if expected else set()):
                        raise ValueError("unexpected actual endpoint contact")
                r["material_exports"].update({n: export(body, target / "materials" / n, p)
                                              for n, body in controls.items() if body.Solids()})
                r["panel_KEY_direct_Common_mm3"] = {s: p.volume(parts["A_BACK_PANEL"].intersect(parts[s + "_KEY"])) for s in "LR"}
                write(target / "report.json", r)
                r["pairs"] = pairs(parts, target, p, budget)
                r["completed"] = r["pairs"]["all_unordered_pairs_present_once"] and not r["pairs"]["failed"] and r["pairs"]["all_original_BREP_bytes_unchanged"]
                r["finite_pose_clear"] = r["completed"] and not r["pairs"]["rejected"]
            except BaseException as exc:
                r["failure"] = type(exc).__name__ + ": " + str(exc)
                r["traceback"] = traceback.format_exc()
            r["seconds"] = time.monotonic() - state_start
            write(target / "report.json", r)
            write(out / "report.json", result)
            print(json.dumps({"state": name, "completed": r["completed"],
                              "finite_pose_clear": r.get("finite_pose_clear"),
                              "failure": r.get("failure"), "seconds": r["seconds"]}), flush=True)
        result["completed"] = list(result["states"]) == list(args.states) and all(r["completed"] for r in result["states"].values())
        result["all_selected_finite_poses_clear"] = result["completed"] and all(r.get("finite_pose_clear") for r in result["states"].values())
    except BaseException as exc:
        result["failure"] = type(exc).__name__ + ": " + str(exc)
        result["traceback"] = traceback.format_exc()
    result["source_bytes_unchanged"] = source_catalog(source) == source_before
    result["original_helpers_unchanged"] = source_catalog(originals) == original_before
    result["seconds"] = time.monotonic() - started
    result["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    write(out / "report.json", result)
    return 0 if result["completed"] and result["source_bytes_unchanged"] and result["original_helpers_unchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
