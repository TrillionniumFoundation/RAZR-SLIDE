#!/usr/bin/env python3
"""Derived rigid contact pilot: wider backlash with a new 0.25-mm witness.

The original key is preserved; original pawl bodies are translated by +0.15 mm
in the key-withdraw direction. This does not qualify OEM geometry, spring,
strength, force limits or the larger resulting inter-cabin withdrawal slack.
"""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import platform
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("seat_contact_geometry", HERE / "seat-envelope-scan.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def own_sources():
    result = base.input_sources()
    result[str(Path(__file__).resolve().relative_to(base.REPO))] = base.sha(Path(__file__))
    return result


def q_vector(port, q):
    return (0.0, -q, 0.0) if port == "STOW" else (0.0, 0.0, q)


def main():
    started = time.time()
    sources = own_sources()
    counts = base.Checker()
    offsets = list(itertools.product((-50, 0, 50), repeat=3))
    qs = list(range(0, 101, 10))
    cases, summaries = [], []
    for port, side in itertools.product(("STOW", "OPEN"), "LR"):
        key_shape, original_engaged, original_parked = base.normalized_originals(port, side)
        base.CheckedBody(key_shape)
        engaged_shape = original_engaged.translate(q_vector(port, .15))
        parked_shape = original_parked.translate(q_vector(port, .15))
        engaged, parked = base.CheckedBody(engaged_shape), base.CheckedBody(parked_shape)
        dx = parked_shape.Center().x - engaged_shape.Center().x
        pawls = [base.CheckedBody(engaged_shape.translate((dx * i / 22.0, 0.0, 0.0))) for i in range(23)]
        key_cache, profile_cache, profiles, states = {}, {}, [], []

        def key_at(translation_um):
            if translation_um not in key_cache:
                key_cache[translation_um] = base.CheckedBody(key_shape.translate(tuple(x / 1000.0 for x in translation_um)))
            return key_cache[translation_um]

        def profile(translation_um):
            if translation_um in profile_cache:
                return profile_cache[translation_um]
            key = key_at(translation_um)
            path = [counts.volume(key, p) for p in pawls]
            probes = {}
            for probe_um in (50, 250):
                moved = list(translation_um)
                moved[1 if port == "STOW" else 2] += -probe_um if port == "STOW" else probe_um
                probes[str(probe_um)] = counts.volume(key_at(tuple(moved)), engaged)
            row = {"actual_key_translation_um": list(translation_um),
                   "actual_engaged_common_mm3": path[0],
                   "actual_parked_common_mm3": path[-1],
                   "actual_retreat_path_common_mm3": path,
                   "actual_original_reverse_0p05_common_mm3": probes["50"],
                   "actual_new_research_reverse_0p25_common_mm3": probes["250"],
                   "new_probe_clear_release_and_positive_reverse_witness": max(path) <= base.EPS and probes["250"] > base.EPS,
                   "original_probe_clear_release_and_positive_reverse_witness": max(path) <= base.EPS and probes["50"] > base.EPS}
            index = len(profiles)
            profiles.append(row)
            profile_cache[translation_um] = index
            return index

        lookup = {}
        for q_um, offset_index in itertools.product(qs, range(len(offsets))):
            translation = list(offsets[offset_index])
            translation[1 if port == "STOW" else 2] += -q_um if port == "STOW" else q_um
            index = profile(tuple(translation))
            states.append([q_um, offset_index, index])
            lookup[(q_um, offsets[offset_index])] = profiles[index]
        all_new = [q for q in qs if all(lookup[(q, xyz)]["new_probe_clear_release_and_positive_reverse_witness"] for xyz in offsets)]
        all_old = [q for q in qs if all(lookup[(q, xyz)]["original_probe_clear_release_and_positive_reverse_witness"] for xyz in offsets)]
        summary = {"port": port, "side": side,
                   "q_ge_0_range_mm": [0.0, .1], "q_step_mm": .01,
                   "original_key_unchanged": True, "original_pawn_translation_along_keywithdraw_mm": .15,
                   "injected_axis_cube_half_width_mm": .05, "synthetic_offset_count": 27,
                   "all_27_new_0p25_probe_passing_q_samples_mm": [q / 1000.0 for q in all_new],
                   "all_27_original_0p05_probe_passing_q_samples_mm": [q / 1000.0 for q in all_old],
                   "new_probe_passing_logical_states": sum(profiles[i]["new_probe_clear_release_and_positive_reverse_witness"] for q, o, i in states),
                   "original_probe_passing_logical_states": sum(profiles[i]["original_probe_clear_release_and_positive_reverse_witness"] for q, o, i in states),
                   "max_actual_seated_and_retreat_common_mm3": max(max(p["actual_retreat_path_common_mm3"]) for p in profiles),
                   "min_actual_new_0p25_reverse_common_mm3": min(p["actual_new_research_reverse_0p25_common_mm3"] for p in profiles),
                   "synthetic_state_count": len(states), "unique_actual_geometry_profiles": len(profiles),
                   "manufacturing_go": False}
        summaries.append(summary)
        cases.append({"port": port, "side": side, "injected_error_offsets_xyz_um": [list(x) for x in offsets],
                      "retreat_fractions": [i / 22.0 for i in range(23)],
                      "synthetic_state_columns": ["nominal_q_um", "injected_error_offset_index", "actual_geometry_profile_index"],
                      "synthetic_states": states, "actual_geometry_profiles": profiles})
        print(json.dumps(summary), flush=True)
    if sources != own_sources():
        raise ValueError("Independent pilot or original imported contact source changed")
    report = {"environment": {"host": platform.node(), "python": platform.python_version(), "cadquery": base.cq.__version__},
              "source_sha256": sources, "source_bytes_unchanged": True,
              "actual_summary_rows": summaries, "actual_contact_profiles": cases,
              "actual_Occ_signed_common_evaluations": counts.actual_occ_common_count,
              "validated_actual_body_AABB_proven_zero_evaluations": counts.validated_body_AABB_proven_zero_count,
              "new_reverse_probe_mm": .25, "original_reverse_probe_mm": .05,
              "new_probe_must_not_be_reported_as_original_probe_pass": True,
              "nominal_new_free_withdrawal_to_first_contact_mm": .18,
              "synthetic_0p05_error_worst_new_free_withdrawal_mm": .23,
              "geometric_freeplay_numbers_are_not_FPC_USB_BM28_damage_or_strain_qualification": True,
              "controlled_supplier_GDT": False, "physical_qualification": False,
              "elapsed_seconds": time.time() - started, "native_exit_code": 0,
              "manufacturing_go": False}
    path = HERE / "seat-envelope-derived-contact-full.json"
    path.write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
    summary = {k: v for k, v in report.items() if k != "actual_contact_profiles"}
    summary["full_report_sha256"] = base.sha(path)
    summary["full_report_bytes"] = path.stat().st_size
    (HERE / "seat-envelope-derived-contact-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
