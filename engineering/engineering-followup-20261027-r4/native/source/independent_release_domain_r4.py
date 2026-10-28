#!/usr/bin/env python3
"""Independent scalar support check; does not import a producer or native kernel."""
from fractions import Fraction as Q
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def ident(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def bits(value):
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    root = a.workspace.resolve()
    report_path = root / "r4-native/release-domain/R4_ORIGINAL_RELEASE_DOMAIN.json"
    j = json.loads(report_path.read_text())
    native_path = Path(j["native_report"]["path"])
    assert ident(native_path) == j["native_report"]["identity"]
    native = json.loads(native_path.read_text())
    requirement_path = Path(j["original_requirement_source"]["path"])
    assert ident(requirement_path) == j["original_requirement_source"]["identity"]
    requirement = requirement_path.read_text()
    assert "if (u==0 and hit<=TOL) or (u==3 and hit>TOL):raise ValueError" in requirement
    rows = []
    for side in ("L", "R"):
        record = j["sides"][side]
        slot = native["slots"][side]
        assert slot == record["native_slot"]
        origin, slope, halfwidth = (Q(slot[k]) for k in ("origin", "slope", "halfwidth"))
        assert origin > 0 and slope > 0 and halfwidth > 0
        key_z = Q(native["whole_inputs"][side + "_KEY"]["native_guard"]["bounds_mm"][5])
        pawl_z = Q(native["whole_inputs"][side + "_PAWL"]["native_guard"]["bounds_mm"][4])
        assert key_z == Q(record["KEY_base_zmax_mm"]["exact"])
        assert pawl_z == Q(record["PAWL_base_zmin_mm"]["exact"])

        def gap(tab):
            # Explicit exact-operation -> binary64 rounding at the three source
            # arithmetic operations. Rational support translation follows the
            # producer's stated mathematical support model, not native transform.
            product = Q(float(slope * Q(tab)))
            translated_origin = Q(float(origin + product))
            translation = Q(float(translated_origin - halfwidth))
            return pawl_z + translation - key_z

        threshold = record["least_binary64_tab_with_strict_source_support_gap"]["float"]
        previous = record["immediate_binary64_predecessor"]["float"]
        assert math.nextafter(threshold, -math.inf) == previous
        assert bits(threshold) == bits(previous) + 1
        assert gap(previous) == 0 and gap(threshold) == Q(1, 2**53)
        for probe in record["checks"]:
            assert gap(probe["tab"]["float"]) == Q(probe["source_support_gap_mm"]["exact"])
        rows.append({"side": side, "threshold_hex": threshold.hex(), "threshold_mm": threshold, "predecessor_hex": previous.hex(), "predecessor_gap_exact_mm": str(gap(previous)), "threshold_gap_exact_mm": str(gap(threshold)), "original_3mm_gap_exact_mm": str(gap(3.0)), "original_3mm_gap_display_mm": float(gap(3.0)), "tab_2p3_gap_exact_mm": str(gap(2.3)), "all_six_declared_checks_equal": True})
    result = {"schema": "razr-r4-independent-original-release-source-support-review-v1", "reviewer": "/root", "producer_or_kernel_imported": False, "source_identity": ident(__file__), "reviewed_report_identity": ident(report_path), "native_input_identity": ident(native_path), "original_requirement_identity": ident(requirement_path), "checks": rows, "monotonicity_argument": "For finite tab in [0,3], positive slope multiplication, adding the positive origin, and subtracting the fixed halfwidth are monotone under round-to-nearest binary64. Positive halfwidth makes flank=-1 minimal. Immediate predecessor gap=0 and candidate gap>0 therefore identify the least strictly positive source-support tab in this binary64 interval. q changes only the declared Y coordinate and does not change this Z support model.", "scope": "Checks the reported scalar sufficient support separation against actual whole-material bounding records and original endpoint retention requirement. It is not the true minimum geometric release tab, a tolerance-qualified release limit, or a universal compiled transform proof.", "original_0_locked_3_released_requirement_confirmed": True, "tab_1_release_requirement_inferred": False, "product_geometry_modified": False, "native_uniform_transform_or_tolerance_verified": False, "physical_domain_qualified": False, "completed": True}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"completed": True, "sides": len(rows), "threshold_mm": rows[0]["threshold_mm"], "original_3mm_gap_mm": rows[0]["original_3mm_gap_display_mm"]}))


if __name__ == "__main__":
    main()
