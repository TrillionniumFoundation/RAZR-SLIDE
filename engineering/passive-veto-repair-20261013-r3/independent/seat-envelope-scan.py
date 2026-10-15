#!/usr/bin/env python3
"""Actual original-key/pawl seat and release geometry under injected errors.

No r2/r3 builder is executed, and no original CAD/source is edited. Rigid CAD
zero and deliberately injected displacements are not manufacturing tolerances.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import platform
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
import cadquery as cq

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "engineering/mechanical-closure-20261013"))
sys.path.insert(0, str(REPO / "engineering/cad-review-20261013"))
from mechanical_closure import normalized_originals
from occ_signed_volume import common, validated_solid_volume

EPS = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CheckedBody:
    """Immutable geometric input, validated before any separation shortcut."""
    def __init__(self, shape):
        self.shape = shape
        self.volume = validated_solid_volume(shape)
        b = shape.BoundingBox()
        self.bounds = {a: (float(getattr(b, a + "min")), float(getattr(b, a + "max")))
                       for a in "xyz"}


class Checker:
    def __init__(self):
        self.actual_occ_common_count = 0
        self.validated_body_AABB_proven_zero_count = 0

    def volume(self, first, second):
        # Both CheckedBody constructors have already rejected invalid,
        # disconnected, nonfinite or nonpositive signed-volume inputs.
        if any(min(first.bounds[a][1], second.bounds[a][1]) <=
               max(first.bounds[a][0], second.bounds[a][0]) for a in "xyz"):
            self.validated_body_AABB_proven_zero_count += 1
            return 0.0
        self.actual_occ_common_count += 1
        return common(first.shape, second.shape)["checked_volume_mm3"]


def bands(values):
    values = sorted(values)
    groups = []
    for q in values:
        if not groups or q - groups[-1][-1] > 5:
            groups.append([q])
        else:
            groups[-1].append(q)
    return [{"q_min_mm": g[0] / 1000.0, "q_max_mm": g[-1] / 1000.0,
             "sampled_span_mm": (g[-1] - g[0]) / 1000.0, "grid_point_count": len(g),
             "lower_scan_boundary_truncated": g[0] == -100,
             "upper_scan_boundary_truncated": g[-1] == 100} for g in groups]


def input_sources():
    roots = (REPO / "baselines/fpc-r39-20261013", REPO / "engineering/mechanical-closure-20261013",
             REPO / "engineering/cad-review-20261013")
    paths = {Path(__file__).resolve()}
    for module in list(sys.modules.values()):
        value = getattr(module, "__file__", None)
        if value:
            p = Path(value).resolve()
            if p.is_file() and any(p.is_relative_to(root) for root in roots):
                paths.add(p)
    return {str(p.relative_to(REPO)): sha(p) for p in sorted(paths)}


def main():
    started = time.time()
    sources = input_sources()
    offsets = sorted({xyz for width in (10, 20, 50)
                      for xyz in itertools.product((-width, 0, width), repeat=3)})
    qs = list(range(-100, 101, 5))
    all_rows, summaries = [], []
    counts = Checker()
    for port, side in itertools.product(("STOW", "OPEN"), "LR"):
        key_shape, engaged_shape, parked_shape = normalized_originals(port, side)
        original_key = CheckedBody(key_shape)
        engaged, parked = CheckedBody(engaged_shape), CheckedBody(parked_shape)
        dx = parked_shape.Center().x - engaged_shape.Center().x
        pawls = [CheckedBody(engaged_shape.translate((dx * i / 22.0, 0.0, 0.0)))
                 for i in range(23)]
        key_cache, profile_cache, profiles = {}, {}, []

        def checked_key(translation_um):
            if translation_um not in key_cache:
                delta = tuple(v / 1000.0 for v in translation_um)
                key_cache[translation_um] = CheckedBody(key_shape.translate(delta))
            return key_cache[translation_um]

        def geometry_profile(translation_um):
            if translation_um in profile_cache:
                return profile_cache[translation_um]
            key = checked_key(translation_um)
            reverse = list(translation_um)
            reverse[1 if port == "STOW" else 2] += -50 if port == "STOW" else 50
            reverse_key = checked_key(tuple(reverse))
            path_common = [counts.volume(key, pawl) for pawl in pawls]
            reverse_common = counts.volume(reverse_key, engaged)
            profile = {"actual_key_translation_um": list(translation_um),
                       "actual_engaged_common_mm3": path_common[0],
                       "actual_parked_common_mm3": path_common[-1],
                       "actual_reverse_key_0p05_common_mm3": reverse_common,
                       "actual_retreat_path_common_mm3": path_common,
                       "clear_engaged_and_retreat_positive_reverse_0p05": (
                           max(path_common) <= EPS and reverse_common > EPS)}
            index = len(profiles)
            profiles.append(profile)
            profile_cache[translation_um] = index
            return index

        samples, lookup = [], {}
        for q_um, offset_index in itertools.product(qs, range(len(offsets))):
            xyz = list(offsets[offset_index])
            xyz[1 if port == "STOW" else 2] += -q_um if port == "STOW" else q_um
            index = geometry_profile(tuple(xyz))
            samples.append([q_um, offset_index, index])
            lookup[(q_um, offsets[offset_index])] = profiles[index]
        nominal_clear = [q for q in qs if lookup[(q, (0, 0, 0))]["actual_engaged_common_mm3"] <= EPS]
        nominal_capture = [q for q in qs if lookup[(q, (0, 0, 0))]["clear_engaged_and_retreat_positive_reverse_0p05"]]
        robust = []
        for width in (10, 20, 50):
            selected = list(itertools.product((-width, 0, width), repeat=3))
            allowed = [q for q in qs if all(lookup[(q, xyz)]["clear_engaged_and_retreat_positive_reverse_0p05"]
                                          for xyz in selected)]
            clear = [q for q in qs if all(lookup[(q, xyz)]["actual_engaged_common_mm3"] <= EPS
                                        for xyz in selected)]
            robust.append({"injected_axis_cube_half_width_mm": width / 1000.0,
                           "synthetic_offset_count": len(selected),
                           "all_27_engaged_clear_sampled_bands": bands(clear),
                           "all_27_clear_release_and_reverse_capture_sampled_bands": bands(allowed)})
        summary = {"port": port, "side": side,
                   "actual_original_release_stroke_mm": abs(dx),
                   "nominal_engaged_clear_sampled_bands": bands(nominal_clear),
                   "nominal_clear_release_and_reverse_capture_sampled_bands": bands(nominal_capture),
                   "robust_synthetic_offset_bands": robust,
                   "unique_actual_geometry_profiles": len(profiles),
                   "synthetic_state_count": len(samples)}
        summaries.append(summary)
        all_rows.append({"port": port, "side": side,
                         "actual_original_body_signed_volumes_mm3": {
                             "key": original_key.volume, "engaged_pawl": engaged.volume, "parked_pawl": parked.volume},
                         "injected_error_offsets_xyz_um": [list(x) for x in offsets],
                         "retreat_fractions": [i / 22.0 for i in range(23)],
                         "sample_columns": ["nominal_q_um", "injected_error_offset_index", "actual_geometry_profile_index"],
                         "synthetic_states": samples, "actual_geometry_profiles": profiles})
        print(json.dumps(summary), flush=True)
    if sources != input_sources():
        raise ValueError("Original imported geometry source or verifier changed during actual scan")
    report = {"environment": {"host": platform.node(), "python": platform.python_version(), "cadquery": cq.__version__},
              "source_sha256": sources, "imported_source_bytes_unchanged": True,
              "q_scan_mm": {"min": -.1, "max": .1, "step": .005},
              "engaged_is_acceptable_only_if_retreat_clear_and_reverse_0p05_has_positive_common": True,
              "actual_rigid_research_scan_rows": all_rows, "actual_summary_rows": summaries,
              "numeric_positive_common_threshold_mm3": EPS,
              "actual_Occ_signed_common_evaluations": counts.actual_occ_common_count,
              "validated_actual_body_AABB_proven_zero_evaluations": counts.validated_body_AABB_proven_zero_count,
              "AABB_touch_means_zero_material_volume_not_positive_clearance": True,
              "synthetic_state_count": sum(s["synthetic_state_count"] for s in summaries),
              "unique_actual_geometry_profile_count": sum(s["unique_actual_geometry_profiles"] for s in summaries),
              "elapsed_seconds": time.time() - started, "native_exit_code": 0,
              "controlled_supplier_GDT": False, "physical_material_or_force_qualification": False,
              "CAD_zero_is_not_manufacturing_tolerance": True, "manufacturing_go": False}
    path = HERE / "seat-envelope-full-scan.json"
    path.write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
    summary = {k: v for k, v in report.items() if k != "actual_rigid_research_scan_rows"}
    summary["full_scan_sha256"] = sha(path)
    summary["full_scan_bytes"] = path.stat().st_size
    (HERE / "seat-envelope-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"synthetic_state_count": report["synthetic_state_count"],
                      "unique_actual_geometry_profile_count": report["unique_actual_geometry_profile_count"],
                      "actual_Occ_signed_common_evaluations": counts.actual_occ_common_count,
                      "validated_actual_body_AABB_proven_zero_evaluations": counts.validated_body_AABB_proven_zero_count,
                      "native_exit_code": 0, "manufacturing_go": False}), flush=True)


if __name__ == "__main__":
    main()
