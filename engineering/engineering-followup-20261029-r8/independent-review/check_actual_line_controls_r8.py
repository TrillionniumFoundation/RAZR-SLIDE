"""Actual Line-claim mutation controls using the original edge189 record."""
import copy
import gzip
import json
from pathlib import Path
import sys
import time

import quadric_checker_r8 as checker
from read_depth24_actual_r8 import identity, need


def main():
    originals, proof_path, output = map(Path, sys.argv[1:])
    output.parent.mkdir(parents=True, exist_ok=True)
    need(not output.exists(), "new_control_output")
    start = time.monotonic()
    claim = None
    with gzip.open(proof_path, "rt") as stream:
        for line in stream:
            row = json.loads(line)
            for observation in row["result"].get("observations", []):
                for candidate in observation["new_claims"]:
                    if candidate["code"] == "line":
                        claim = candidate
                        break
                if claim is not None:
                    break
            if claim is not None:
                break
    need(claim is not None, "actual_line_claim_required")
    source_path = originals / "r7-recovery/r3e/native-and-math/reader/worker/report.json"
    source = json.loads(source_path.read_text())
    material = next(r for r in source["operands"] if [r["input"]["case_id"], r["input"]["material_id"]] == claim["material_key"])
    record = material["boundary"]["edges"][claim["original_index"]]
    certificate_path = originals / "r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames/case-028-frame-1-primitive-support.json.gz"
    with gzip.open(certificate_path, "rt") as stream:
        certificate = json.load(stream)
    side, original_source = next((i, r) for i, r in enumerate(certificate["boundary_refinement"]["sources"]) if r["material_key"] == claim["material_key"])
    piece = original_source["pieces"][claim["piece_index"]]
    D = certificate["frame"]["original_remaining_displacement_box_exact"] if side == 0 else [["0", "0"]] * 3
    result = {"schema": "razr-r8-actual-line-claim-mutation-controls", "actual_claim": claim,
              "original_reader": identity(source_path), "original_certificate": identity(certificate_path),
              "producer_proof": identity(proof_path), "checker_source": identity(checker.__file__),
              "self_source": identity(__file__), "positive_readback": checker.verify_line_claim(claim, record, piece, D), "controls": []}
    operations = [
        ("drop_parameter_axis", lambda c: c["parameter_trace"].pop(), "line_complete_parameter_trace"),
        ("wrong_empty_axis", lambda c: c.update(empty_axis=(c["empty_axis"] + 1) % 3), "line_parameter_infeasibility_reason"),
        ("change_nonzero_to_zero_reason", lambda c: c.update(zero_direction_coordinate_outside=True), "line_parameter_infeasibility_reason"),
        ("omit_original_nonzero_displacement", lambda c: c.update(full_D_exact=[["0", "0"]] * 3), "full_D_identity"),
    ]
    for name, operation, expected in operations:
        mutant = copy.deepcopy(claim)
        operation(mutant)
        rejection = None
        try:
            checker.verify_line_claim(mutant, record, piece, D)
        except ValueError as exc:
            rejection = str(exc)
        need(rejection == expected, "specific_mutation_rejection:" + name)
        result["controls"].append({"name": name, "mutated_claim": mutant, "actual_rejection": rejection, "passed": True})
    result.update(completed=True, seconds=time.monotonic() - start, native_BREP_material_membership_certified=False)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"completed": True, "line_controls": len(result["controls"]), "seconds": result["seconds"]}))


if __name__ == "__main__":
    main()
