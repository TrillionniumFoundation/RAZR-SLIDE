"""Freeze the observed absence of required inputs without inventing measurements."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"


def main(args):
    source_hashes = {}
    def read(rel):
        b = subprocess.check_output(["git", "-C", str(args.repository), "show", S4 + ":" + rel])
        source_hashes[rel] = hashlib.sha256(b).hexdigest()
        return json.loads(b)
    interfaces = read("design/product_interfaces.json")
    structural = read("engineering/engineering-integration-20261025/structural/CURRENT_EP5_INPUT_CONTRACT.json")
    for rel, expected in structural["geometric_source_sha256"].items():
        b = subprocess.check_output(["git", "-C", str(args.repository), "show", S4 + ":" + rel])
        assert hashlib.sha256(b).hexdigest() == expected
        source_hashes[rel] = expected
    missing = [k for k, v in interfaces["donor"].items() if v is None]
    ids = [r["id"] for r in interfaces["interfaces"]]
    materials = structural["all_nominal_material_assignments"]
    loads = structural["loadcases"]
    assert len(missing) == 10 and len(ids) == 12
    assert len(materials) == structural["nominal_body_count"] == 154
    assert all(all(v is None for v in row.values()) for row in materials.values())
    assert len(loads) == 13 and all(all(v is None for v in row.values()) for row in loads.values())
    access = json.loads(args.access.read_text())
    assert access["candidate_reference"] == S4
    assert access["physical_execution_occurred"] is False and access["new_physical_observations"] == 0
    assert access["known_prior_endpoint_only"] is True and access["connect_ex"] == 111
    result = {
        "schema": "razr-current-physical-input-and-contract-state-v1",
        "functional_source_commit": S4, "checked_source_sha256": source_hashes,
        "current_access_rechecked_utc": access["observed_utc"],
        "adb_executable_available": access["adb_executable_available"],
        "previously_designated_endpoint_connection_refused": True,
        "new_physical_observations": 0, "physical_execution_occurred": False,
        "same_specimen_identity_fields_still_unknown": missing,
        "physical_part_roles_still_requiring_originals": ["mainboard", "display", "touch", "COF", "pack_A", "pack_B", "USB_port_board"],
        "interfaces_still_requiring_same_specimen_terminal_and_function_evidence": ids,
        "materials_with_no_selected_physical_grade_or_parameters": len(materials),
        "loadcases_with_no_sourced_physical_values": list(loads),
        "placeholder_bodies_requiring_same_specimen_replacement": structural["placeholder_bodies_requiring_same_specimen_replacement"],
        "contact_requirements": structural["contact_requirements"],
        "tolerance_contract": structural["tolerance_contract"],
        "verification_requirements": structural["verification_requirements"],
        "current_FE_can_be_physically_qualified": False,
        "threshold_values_invented_or_relaxed": False,
        "G3_actual_pass": False, "G4_actual_pass": False, "G5_actual_pass": False,
        "gate_state": {"G3": "unknown_missing_real_inputs_and_execution", "G4": "blocked_by_missing_real_G3_and_OEM_inputs", "G5": "blocked_by_missing_real_G3_G4_and_life_inputs"},
        "same_candidate_and_same_specimen_required_across_actual_gates": True,
        "field_handoff": "PHYSICAL_HANDOFF.md",
        "messages_sent_to_people": False,
        "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
        "scope": "Current access and immutable source-input review only. This does not establish global absence of the user's device or documents."
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "PHYSICAL_INPUT_STATE.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"source_files_bound": len(source_hashes), "unknown_identity_fields": len(missing), "unmapped_interfaces": len(ids), "unselected_materials": len(materials), "unsourced_loadcases": len(loads), "physical_observations": 0}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--access", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
