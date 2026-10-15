#!/usr/bin/env python3
"""Actual OCC first-contact brackets for the isolated translated pawl proxy."""
from __future__ import annotations
import importlib.util
import itertools
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("seat_geometry", HERE / "seat-envelope-scan.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def q_vector(port, q):
    return (0.0, -q, 0.0) if port == "STOW" else (0.0, 0.0, q)


def main():
    sources = base.input_sources()
    sources[str(Path(__file__).relative_to(base.REPO))] = base.sha(Path(__file__))
    rows = []
    for port, side in itertools.product(("STOW", "OPEN"), "LR"):
        key, original_pawl, _ = base.normalized_originals(port, side)
        pawn = original_pawl.translate(q_vector(port, .15))
        for name, initial_q_error, withdrawals in (
            ("nominal_original_key", 0.0, (.175, .180, .185)),
            ("synthetic_key_error_opposite_withdraw_0p05", -.05, (.225, .230, .235)),
        ):
            volumes = []
            for withdraw in withdrawals:
                moved_key = key.translate(q_vector(port, withdraw + initial_q_error))
                actual = base.common(moved_key, pawn)
                volumes.append(actual["checked_volume_mm3"])
                rows.append({"port": port, "side": side, "state": name,
                             "injected_key_q_error_mm": initial_q_error,
                             "key_withdraw_mm": withdraw,
                             "actual_signed_OCC_common": actual})
            if not (volumes[0] <= base.EPS and volumes[1] <= base.EPS and volumes[2] > base.EPS):
                raise ValueError("Actual first-contact bracket differs from the proposed derived spacing")
    source_after = base.input_sources()
    source_after[str(Path(__file__).relative_to(base.REPO))] = base.sha(Path(__file__))
    if source_after != sources:
        raise ValueError("Original contact source or independent witness source changed")
    report = {"source_sha256": sources, "source_bytes_unchanged": True,
              "actual_first_contact_rows": rows,
              "isolated_nominal_pawn_contact_q_boundary_mm": .18,
              "isolated_synthetic_q_error_0p05_pawn_contact_boundary_mm": .23,
              "positive_common_witness_only_after_boundary": True,
              "touch_common_zero_is_not_physical_escape": True,
              "not_a_whole_phone_freeplay_or_FPC_BM28_OLED_qualification": True,
              "native_exit_code": 0, "manufacturing_go": False}
    (HERE / "seat-envelope-derived-freeplay-witness.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"actual_OCC_bracket_common_checks": len(rows), "nominal_q_boundary_mm": .18,
                      "synthetic_q_error_boundary_mm": .23, "native_exit_code": 0,
                      "manufacturing_go": False}))


if __name__ == "__main__":
    main()
