"""Count actual unbound current K3 inputs without supplying assumed values."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def identity(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def limits(value, path=""):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            location = path + "/" + key
            if key in ("value", "minimum", "maximum"):
                found.append({"path": location, "value": item})
            else:
                found.extend(limits(item, location))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(limits(item, path + "/" + str(index)))
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("new audit output required")
    sources = [args.source / name for name in (
        "CURRENT_K3_STRUCTURAL_INPUT_CONTRACT.json", "CURRENT_K3_PHYSICAL_AND_GATE_INPUT_CONTRACT.json")]
    s, p = [json.loads(path.read_text()) for path in sources]
    if s["current_K3_binding"] != p["current_K3_binding"]:
        raise ValueError("structural and physical candidate identities differ")
    materials = s["all_current_roles_material_inputs"]
    material_values = [value for role in materials.values() for value in role["physical_material_inputs"].values()]
    loads = [value for role in s["original_13_loadcases_retained"].values() for value in role.values()]
    stop_loads = [value for role in s["K3_additional_stop_load_and_tolerance_cases"].values() for value in role.values()]
    gates = {}
    for name, gate in p["physical_gate_contracts"].items():
        slots = limits(gate)
        gates[name] = {"records": sum(len(gate.get(key, {})) for key in ("requirements", "criteria", "exposure")),
            "numeric_limit_slots": len(slots), "unassigned_numeric_limits": sum(row["value"] is None for row in slots),
            "source_status": gate["status"], "source_actual_execution": gate["actual_execution"],
            "new_physical_measurements": 0, "real_pass_obtained": False, "limits": slots}
    report = {"schema": "razr-r12-current-input-readback-v1", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": identity(Path(__file__)), "input_identities": list(map(identity, sources)),
        "current_candidate_bindings_equal": True,
        "material_roles": len(materials), "material_slots": len(material_values),
        "unassigned_material_slots": sum(v is None for v in material_values),
        "original_loadcases": len(s["original_13_loadcases_retained"]), "load_slots": len(loads),
        "unassigned_load_slots": sum(v is None for v in loads),
        "additional_stop_loadcases": len(s["K3_additional_stop_load_and_tolerance_cases"]),
        "additional_stop_load_slots": len(stop_loads), "unassigned_stop_load_slots": sum(v is None for v in stop_loads),
        "same_specimen_identity_fields": len(p["ten_identity_fields"]),
        "part_roles": len(p["seven_part_originals"]), "interfaces": len(p["twelve_interfaces"]),
        "physical_gates": gates, "gate_records": sum(g["records"] for g in gates.values()),
        "unassigned_gate_limit_slots": sum(g["unassigned_numeric_limits"] for g in gates.values()),
        "new_actual_specimen_originals": 0, "complete_OEM_PDF_bytes_acquired": False,
        "current_absolute_FE_qualified": False, "OEM_electrical_qualified": False,
        "complete_current_physical_contract_frozen": False,
        "G3_pass": False, "G4_pass": False, "G5_pass": False,
        "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("source", "input_identities", "physical_gates")}))


if __name__ == "__main__":
    main()
