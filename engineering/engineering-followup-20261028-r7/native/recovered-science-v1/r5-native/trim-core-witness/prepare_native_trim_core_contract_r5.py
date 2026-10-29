"""Freeze bounded native producer/readback contracts before their execution."""
from pathlib import Path
import argparse
import ast
import datetime as dt
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def ident(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def bind(path):
    return {"path": str(Path(path).resolve()), "identity": ident(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("producer", "reader"))
    args = parser.parse_args()
    old_execution = json.loads((ROOT / "r4-native/R4_NATIVE_PRODUCER_EXECUTION_CONTRACT.json").read_text())
    supervisor = ROOT / "r4-native/recovered/native/source/supervise_native_r3.py"
    assert ident(supervisor)["sha256"] == old_execution["supervisor_sha256"]
    runtime = ROOT / "r4-runtime/R4_PROJECTION_CONTRACT_V3.json"
    qualification = ROOT / "r4-runtime/validation-worker-attempt3/R3_PROJECTION_VALIDATION_EXECUTED.json"
    launcher = ROOT / "r4-runtime/run_qualified_script_r4.py"
    plan = json.loads((ROOT / "r4-runtime/R4_ACTIVATION_PLAN_V3.json").read_text())
    scope = {"original_L1_R3E_V5_panel_inputs": True,
             "current_K3_only_after_registered_material_and_pose_gates": True,
             "whole_current_geometry_modified": False,
             "surface_area_and_topology_not_zero_3D_volume": True,
             "native_tolerances_unchanged": True,
             "rounding_of_original_rational_cores_declared_outwards": True,
             "native_current_boundary_model_membership_claimed": False,
             "compiled_kernel_formal_error_bound_verified": False,
             "full_continuous_G2": False, "physical_qualification": False}
    capacity = {"algorithm": "Four original panels; 40 source-bound faces, 80 complete UV core rectangles. Eight whole-face controls. Four captured-translation material mappings with eight full directed differences. Two current/base differences. Up to 80 added-material/full-core intersections only after their finite native material and pose gates pass. Separate reader imports no producer module and reconstructs all 80 patches and every eligible intersection.",
                "producer_direct_Boolean_operation_count_upper": 178,
                "reader_direct_Boolean_operation_count_upper": 178,
                "complete_original_BREP_inputs": 6, "complete_original_BREP_input_bytes": 1225201,
                "expected_producer_and_reader_seconds_each": [60, 240],
                "expected_peak_RSS_bytes_each": [450000000, 838860800],
                "basis": "Actual R4 whole KEY/PAWL producer: 62 pairs plus full inventories in 51.318485142999634 s at 444329984 B. Actual contact-prism producer: 8.20567792499969 s at 439750656 B. The new bounded job has simpler coplanar face operations plus eight whole-panel differences and the unchanged runtime hash closeouts. These are estimates, not guarantees.",
                "maximum_new_campaign_bytes": 67108864,
                "maximum_producer_worker_bytes": 20971520, "maximum_reader_worker_bytes": 20971520,
                "reserved_runtime_receipts_bytes": 16777216,
                "reserved_selection_sources_contracts_controllers_and_logs_bytes": 8388608,
                "current_projection_payloads_existing_bytes": 1226421880,
                "full_original_source_archives_resident_and_not_copied_into_new_campaign": True,
                "new_full_factory_execution": False,
                "all_original_six_native_resource_limits_unchanged": True}
    selection = OUT / "R5_NATIVE_TRIM_CORE_SELECTION.json"
    mapping = OUT / "R5_NATIVE_CURRENT_PANEL_MAPPING.json"
    projection = ROOT / "r5-envelope/R5E_V5_PLANAR_TRIM_SOURCE.json.gz"
    original = ROOT / "recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027/source-and-inputs/source-original"
    if args.phase == "producer":
        path = OUT / "R5_NATIVE_TRIM_CORE_PRODUCER_CONTRACT.json"
        assert not path.exists()
        selected = json.loads(selection.read_text())
        mapped = json.loads(mapping.read_text())
        record_paths = {selection, mapping, projection, runtime, qualification,
                        OUT / "R5_ORIGINAL_V5_TO_CURRENT_K3_MATERIAL_BOUNDARY.json"}
        for m in selected["materials"]:
            record_paths.add(ROOT / m["input_path"])
        for key in ("K3_original_panel", "K3_current_panel"):
            record_paths.add(ROOT / mapped[key]["input_path"])
        for source in mapped["original_case_records"] + selected["actual_V5_certificates"]:
            record_paths.add(ROOT / source["path"])
        source_paths = {OUT / "native_trim_core_witness_r5.py", OUT / "read_native_trim_core_witness_r5.py",
                        OUT / "prepare_native_trim_core_contract_r5.py", launcher,
                        original / "boundary_inventory_l8.py", original / "product_assembly.py", original / "straight_envelope.py"}
        source_paths.update(ROOT / source["path"] for source in mapped["source_function_bindings"])
        for file in source_paths:
            ast.parse(file.read_text())
        data = {"schema": "r5-finite-native-trim-core-producer-contract-v1", "registered_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "workspace_root": str(ROOT), "worker_identity": ident(OUT / "native_trim_core_witness_r5.py"),
                "independent_reader_source_identity": ident(OUT / "read_native_trim_core_witness_r5.py"),
                "selection": bind(selection), "mapping": bind(mapping), "projection": bind(projection),
                "inventory_source": str(original / "boundary_inventory_l8.py"),
                "bound_records": [bind(p) for p in sorted(record_paths)],
                "bound_sources": [bind(p) for p in sorted(source_paths)],
                "expected_43_package_versions": plan["original_43_version_map"],
                "maximum_report_bytes": 4194304, "maximum_worker_output_bytes": 20971520,
                "maximum_new_campaign_bytes": 67108864,
                "scope": scope, "capacity": capacity,
                "original_3D_material_tolerance_mm3": 1e-7,
                "new_physical_area_threshold": None,
                "native_core_boundary_gray_states_retained": ["edge_or_vertex_only_boundary", "positive_face_area", "null_shape_unresolved", "invalid_topology_unresolved", "zero_area_face_unresolved", "Boolean exception"]}
        worker = OUT / "native_trim_core_witness_r5.py"
        output = OUT / "producer-owned/worker"
    else:
        path = OUT / "R5_NATIVE_TRIM_CORE_READER_CONTRACT.json"
        assert not path.exists()
        producer_contract = OUT / "R5_NATIVE_TRIM_CORE_PRODUCER_CONTRACT.json"
        report = OUT / "producer-owned/worker/R5_NATIVE_TRIM_CORE_WITNESS.json"
        controller = OUT / "producer-owned/controller.json"
        runtime_receipt = OUT / "producer-runtime-observation.json"
        assert json.loads(controller.read_text())["completed"]
        assert json.loads(runtime_receipt.read_text())["completed"]
        assert json.loads(report.read_text())["completed"]
        data = {"schema": "r5-finite-native-trim-core-independent-readback-contract-v1",
                "registered_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "reader_identity": ident(OUT / "read_native_trim_core_witness_r5.py"),
                "producer_report": bind(report), "producer_contract": bind(producer_contract),
                "producer_owned_controller": bind(controller), "producer_runtime_closeout": bind(runtime_receipt),
                "scope": scope, "capacity": capacity}
        worker = OUT / "read_native_trim_core_witness_r5.py"
        output = OUT / "reader-owned/worker"
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    runtime_output = OUT / (args.phase + "-runtime-observation.json")
    command = ["python3", "-I", "-S", "-B", str(launcher), "--runtime-contract", str(runtime),
               "--qualification", str(qualification), "--runtime-receipt", str(runtime_output),
               "--script", str(worker), "--", "--contract", str(path), "--out", str(output)]
    execution = {"schema": "r5-original-gated-native-trim-core-execution-contract-v1",
                 "registered_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                 "supervisor_sha256": ident(supervisor)["sha256"],
                 "resource_limits": old_execution["resource_limits"],
                 "worker_contract": bind(path), "worker": bind(worker),
                 "qualified_runtime_contract": bind(runtime), "qualified_runtime_receipt": bind(qualification),
                 "launcher": bind(launcher), "command": command, "capacity": capacity,
                 "full_factory_and_physical_release_claimed": False}
    execution_path = OUT / ("R5_NATIVE_TRIM_CORE_" + args.phase.upper() + "_EXECUTION_CONTRACT.json")
    assert not execution_path.exists()
    execution_path.write_text(json.dumps(execution, indent=2) + "\n")
    supervisor_command = ["python3", "-B", str(supervisor), "--contract", str(execution_path), "--out", str(output.parent), *command]
    observation = {"schema": "r5-native-trim-core-registered-execution-command-v1",
                   "phase": args.phase, "worker_contract": bind(path), "execution_contract": bind(execution_path),
                   "command": supervisor_command, "native_execution_started": False}
    observation_path = OUT / ("R5_NATIVE_TRIM_CORE_" + args.phase.upper() + "_COMMAND.json")
    assert not observation_path.exists()
    observation_path.write_text(json.dumps(observation, indent=2) + "\n")
    print(json.dumps({"phase": args.phase, "contract": bind(path), "command_record": bind(observation_path), "source_AST_parsing_only": True, "new_native_operations": 0}))


if __name__ == "__main__":
    main()
