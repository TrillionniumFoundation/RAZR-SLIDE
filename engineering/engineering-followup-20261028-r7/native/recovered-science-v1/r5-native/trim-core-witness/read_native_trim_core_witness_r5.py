"""Separate-process native readback, without importing the R5 producer.

Every saved BREP is read; original patches are reconstructed through the OCP
surface constructor directly. Full-area observations never use zero 3D volume
as an emptiness shortcut. Native area bit equality is reported separately.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import resource
import sys
import time


def ident(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    contract = json.loads(args.contract.read_text())
    require(ident(__file__) == contract["reader_identity"], "Reader identity differs")
    for item in (contract["producer_report"], contract["producer_contract"]):
        require(ident(item["path"]) == item["identity"], "Producer report/contract changed")
    producer_path = Path(contract["producer_report"]["path"])
    previous = json.loads(producer_path.read_text())
    pc = json.loads(Path(contract["producer_contract"]["path"]).read_text())
    require(previous["completed"], "Producer did not complete its registered finite experiment")
    require(previous["contract_identity"] == contract["producer_contract"]["identity"], "Producer contract binding differs")
    require(not sys.flags.optimize and sys.flags.dont_write_bytecode, "Original interpreter flags required")
    for item in pc["bound_records"] + pc["bound_sources"]:
        require(ident(item["path"]) == item["identity"], "Original source or record changed")
    selection = json.loads(Path(pc["selection"]["path"]).read_text())
    mapping = json.loads(Path(pc["mapping"]["path"]).read_text())
    args.out.mkdir(exist_ok=False)
    (args.out / "geometry").mkdir()
    start = time.monotonic()
    result = {"schema": "r5-independent-native-trim-core-readback-v1", "reader_identity": ident(__file__),
              "contract_identity": ident(args.contract), "producer_report_identity": ident(producer_path),
              "completed": False, "producer_module_imported": False, "separate_native_process": True,
              "independent_CAD_kernel": False, "saved_BREP_readbacks": [], "original_core_readbacks": [],
              "control_readbacks": [], "material_mapping_readbacks": [], "current_added_core_readbacks": [],
              "issues": [], "scope": pc["scope"], "native_exact_membership_verified": False,
              "full_continuous_G2": False, "physical_qualification": False,
              "runtime": {name: importlib.metadata.version(name) for name in pc["expected_43_package_versions"]}}

    def persist():
        result["seconds"] = time.monotonic() - start
        result["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        data = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
        require(len(data) <= pc["maximum_report_bytes"], "Reader report budget exceeded")
        (args.out / "R5_NATIVE_TRIM_CORE_READBACK.json").write_bytes(data)
        require(sum(p.stat().st_size for p in args.out.rglob("*") if p.is_file()) <= pc["maximum_worker_output_bytes"], "Reader output budget exceeded")

    try:
        require(result["runtime"] == pc["expected_43_package_versions"], "Original 43 package versions differ")
        sys.path.insert(0, str(Path(pc["inventory_source"]).parent))
        spec = importlib.util.spec_from_file_location("r5_original_reader_inventory", pc["inventory_source"])
        inventory = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inventory)
        cq = inventory.cq
        from OCP.BinTools import BinTools
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.TopoDS import TopoDS_Shape

        def read(path):
            raw = TopoDS_Shape()
            require(BinTools.Read_s(raw, str(path)), "Independent BREP read failed")
            return cq.Shape.cast(raw)

        def describe(shape, whole=False):
            null = shape.isNull()
            counts = {name: (0 if null else len(getattr(shape, name.capitalize())()))
                      for name in ("solids", "shells", "faces", "wires", "edges", "vertices")}
            valid = False if null else bool(shape.isValid())
            area = 0.0 if null else float(shape.Area())
            require(math.isfinite(area) and area >= 0, "Nonfinite independent area")
            if null:
                category = "null_shape_unresolved"
            elif not valid:
                category = "invalid_topology_unresolved"
            elif counts["solids"] or counts["shells"]:
                category = "higher_dimension_unresolved"
            elif counts["faces"]:
                category = "positive_face_area" if area > 0 else "zero_area_face_unresolved"
            elif counts["edges"] or counts["vertices"]:
                category = "edge_or_vertex_only_boundary"
            elif not any(counts.values()):
                category = "topologically_empty"
            else:
                category = "other_topology_unresolved"
            record = {"is_null": null, "valid": valid, "shape_type": None if null else shape.ShapeType(),
                      "counts": counts, "classification": category,
                      "native_area_mm2": area, "native_area_binary64_hex": area.hex(),
                      "zero_3D_volume_used_as_face_emptiness": False}
            if whole:
                solids, volume = inventory.p.whole_material(shape, empty=True)
                record["original_whole_material_guard"] = {"passed": True, "signed_volume_mm3": volume,
                                                           "solid_signed_volumes_mm3": [s.Volume() for s in solids]}
                if solids:
                    record["classification"] = "complete_positive_3D_material"
            return record

        def compare(actual, expected):
            topology = all(actual[k] == expected[k] for k in ("is_null", "valid", "shape_type", "counts", "classification"))
            return {"topology_and_classification_equal": topology,
                    "area_binary64_equal": actual["native_area_binary64_hex"] == expected["native_area_binary64_hex"],
                    "area_difference_mm2": actual["native_area_mm2"] - expected["native_area_mm2"]}

        def write(shape, label, expected=None, whole=False):
            file = args.out / "geometry" / (label + ".brep")
            status = BinTools.Write_s(shape.wrapped, str(file))
            require(status is not False and file.is_file(), "Independent native output failed")
            rec = {"path": str(file.relative_to(args.out)), **ident(file), "native": describe(shape, whole)}
            if expected is not None:
                rec["comparison"] = compare(rec["native"], expected["native"])
                require(rec["comparison"]["topology_and_classification_equal"], "Independent native topology/classification differs")
            return rec

        seen = set()
        def visit(value):
            if isinstance(value, dict):
                path = value.get("path")
                if isinstance(path, str) and path.startswith("geometry/") and {"bytes", "sha256"} <= value.keys() and path not in seen:
                    seen.add(path)
                    full = producer_path.parent / path
                    require(ident(full) == {key: value[key] for key in ("bytes", "sha256")}, "Saved operand/result bytes differ")
                    shape = read(full)
                    whole = "original_whole_material_guard" in value.get("native", {})
                    desc = describe(shape, whole)
                    entry = {"path": path, "identity": ident(full), "native": desc}
                    if "native" in value:
                        entry["comparison"] = compare(desc, value["native"])
                        require(entry["comparison"]["topology_and_classification_equal"], "Saved BREP readback differs")
                    result["saved_BREP_readbacks"].append(entry)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(previous)
        persist()
        parents, face_lists = {}, {}
        for item in selection["materials"]:
            key = tuple(item["material_key"])
            shape = read(Path(pc["workspace_root"]) / item["input_path"])
            solids, volume = inventory.p.whole_material(shape)
            require(len(solids) == 1, "Complete original panel required")
            parents[key] = shape
            face_lists[key] = shape.Faces()
        by_original = {x["witness_id"]: x for x in previous["original_core_intersections"]}
        patches = {}
        for witness in selection["hole_witnesses"]:
            key = tuple(witness["material_key"])
            face = face_lists[key][witness["face_index"]]
            require(inventory.surface_record(BRepAdaptor_Surface(face.wrapped, True)) == witness["face_surface"], "Independent original plane parameters differ")
            uv = [point["float"] for axis in witness["native_UV_outward_box"] for point in axis]
            tolerance = float(BRep_Tool.Tolerance_s(face.wrapped))
            require(tolerance == witness["face_tolerance"]["float"], "Independent face tolerance differs")
            constructor = BRepBuilderAPI_MakeFace(BRep_Tool.Surface_s(face.wrapped), *uv, tolerance)
            require(constructor.IsDone(), "Independent UV patch construction failed")
            patch = cq.Face(constructor.Face())
            require(patch.isValid() and patch.Area() > 0, "Invalid independent patch")
            patches[witness["witness_id"]] = patch
            old = by_original[witness["witness_id"]]
            row = {"witness_id": witness["witness_id"],
                   "patch": write(patch, witness["witness_id"] + "-independent-patch", old["patch"]),
                   "common": write(face.intersect(patch), witness["witness_id"] + "-independent-face-common", old["actual_common"])}
            result["original_core_readbacks"].append(row)
            persist()
        for old in previous["native_controls"]:
            key = tuple(old["material_key"])
            face = face_lists[key][old["face_index"]]
            other = face if old["kind"] == "positive_self" else face.translate((1000.0, 0.0, 0.0))
            result["control_readbacks"].append({"material_key": old["material_key"], "kind": old["kind"],
                                                "common": write(face.intersect(other), key[0] + "-m" + str(key[1]) + "-independent-" + old["kind"], old["common"])})
            persist()
        old_panel = read(Path(pc["workspace_root"]) / mapping["K3_original_panel"]["input_path"])
        current = read(Path(pc["workspace_root"]) / mapping["K3_current_panel"]["input_path"])
        native_gates = {}
        recorded_mapping = {tuple(x["material_key"]): x for x in previous["material_mapping"]}
        shifts = {}
        for item in mapping["original_material_mappings"]:
            key = tuple(item["material_key"])
            shift = item["native_inverse_translation_binary64_mm"]
            shifts[key] = shift
            body = parents[key].translate(tuple(shift)) if any(shift) else parents[key]
            prior = recorded_mapping[key]
            first = write(body.cut(old_panel), key[0] + "-m" + str(key[1]) + "-independent-map-forward", prior["mapped_minus_K3_original"], True)
            second = write(old_panel.cut(body), key[0] + "-m" + str(key[1]) + "-independent-map-reverse", prior["K3_original_minus_mapped"], True)
            passed = first["native"]["classification"] == second["native"]["classification"] == "topologically_empty"
            require(passed == prior["finite_native_material_and_pose_gate_passed"], "Native mapping gate changed")
            native_gates[key] = passed
            result["material_mapping_readbacks"].append({"material_key": list(key), "first_difference": first,
                                                        "second_difference": second, "finite_gate_passed": passed})
            persist()
        added, removed = current.cut(old_panel), old_panel.cut(current)
        result["current_added_material_account"] = {
            "added": write(added, "independent-K3-added", previous["current_added_material_account"]["current_minus_original"], True),
            "removed": write(removed, "independent-K3-removed", previous["current_added_material_account"]["original_minus_current"], True)}
        added_volume = result["current_added_material_account"]["added"]["native"]["original_whole_material_guard"]["signed_volume_mm3"]
        account_ok = result["current_added_material_account"]["removed"]["native"]["classification"] == "topologically_empty" and abs(added_volume - mapping["original_saved_added_material_account"]["added_mm3"]) <= inventory.p.TOL
        require(account_ok == previous["current_added_material_account"]["original_native_material_account_gate_passed"], "Current added-material gate changed")
        old_current = {x["witness_id"]: x for x in previous["current_added_core_intersections"]}
        for witness in selection["hole_witnesses"]:
            old = old_current[witness["witness_id"]]
            key = tuple(witness["material_key"])
            eligible = account_ok and native_gates.get(key) and witness["witness_id"] in patches
            require(bool(eligible) == old["executed"], "Current witness eligibility changed")
            if not eligible:
                result["current_added_core_readbacks"].append({"witness_id": witness["witness_id"], "executed": False, "not_executed_reason": old["not_executed_reason"]})
                continue
            shift = shifts[key]
            patch = patches[witness["witness_id"]].translate(tuple(shift)) if any(shift) else patches[witness["witness_id"]]
            result["current_added_core_readbacks"].append({"witness_id": witness["witness_id"], "executed": True,
                "mapped_patch": write(patch, witness["witness_id"] + "-independent-global-patch", old["mapped_patch"]),
                "added_common": write(added.intersect(patch), witness["witness_id"] + "-independent-added-common", old["actual_added_material_common"])})
            persist()
        checks = []
        def collect(value):
            if isinstance(value, dict):
                if "area_binary64_equal" in value:
                    checks.append(value)
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        collect(result)
        result["native_area_comparisons"] = {"count": len(checks), "all_binary64_equal": all(x["area_binary64_equal"] for x in checks),
                                             "maximum_absolute_difference_mm2": max((abs(x["area_difference_mm2"]) for x in checks), default=0.0),
                                             "new_physical_area_threshold_introduced": False}
        result["sources_and_original_inputs_unchanged"] = all(ident(x["path"]) == x["identity"] for x in pc["bound_records"] + pc["bound_sources"])
        result["producer_report_and_contract_unchanged"] = all(ident(x["path"]) == x["identity"] for x in (contract["producer_report"], contract["producer_contract"]))
        result["runtime_versions_unchanged"] = {n: importlib.metadata.version(n) for n in pc["expected_43_package_versions"]} == result["runtime"]
        result["completed"] = len(result["original_core_readbacks"]) == 80 and len(result["control_readbacks"]) == 8 and len(result["material_mapping_readbacks"]) == 4 and len(result["current_added_core_readbacks"]) == 80 and result["sources_and_original_inputs_unchanged"] and result["producer_report_and_contract_unchanged"] and result["runtime_versions_unchanged"]
    except Exception as exc:
        result["issues"].append({"type": type(exc).__name__, "message": str(exc)})
    persist()
    print(json.dumps({key: result[key] for key in ("completed", "seconds", "peak_RSS_bytes", "issues")}), flush=True)
    return 0 if result["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
