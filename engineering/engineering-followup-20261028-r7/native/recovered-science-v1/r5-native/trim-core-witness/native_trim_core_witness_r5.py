"""Finite native intersection of original V5 face cores and current additions.

This experiment preserves 2D topology and area. Zero volume is never a face
emptiness test. All original material, actual failures and gray boundaries stay
visible; no exact native set model or continuous factory qualification follows.
"""
from pathlib import Path
import argparse
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import resource
import sys
import time


def ident(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    c = json.loads(a.contract.read_text())
    need(ident(__file__) == c["worker_identity"], "Producer source changed")
    need(not sys.flags.optimize and sys.flags.dont_write_bytecode, "Original Python execution flags required")
    for row in c["bound_records"] + c["bound_sources"]:
        need(ident(row["path"]) == row["identity"], "Frozen input differs: " + row["path"])
    selection = json.loads(Path(c["selection"]["path"]).read_text())
    mapping = json.loads(Path(c["mapping"]["path"]).read_text())
    projection = json.loads(gzip.decompress(Path(c["projection"]["path"]).read_bytes()))
    source_faces = {(z["input"]["case_id"], z["input"]["material_id"], f["complete_original_face"]["index"]): f["complete_original_face"]
                    for z in projection["records"] for f in z["candidate_faces"]}
    a.out.mkdir(exist_ok=False)
    geometry = a.out / "geometry"
    geometry.mkdir()
    start = time.monotonic()
    r = {"schema": "r5-finite-native-trim-core-witness-v1", "worker_identity": ident(__file__),
         "contract_identity": ident(a.contract), "selection_identity": ident(c["selection"]["path"]),
         "mapping_identity": ident(c["mapping"]["path"]), "completed": False,
         "scope": c["scope"], "whole_inputs": [], "native_face_bindings": [], "original_core_intersections": [],
         "native_controls": [], "material_mapping": [], "current_added_core_intersections": [], "issues": [],
         "current_K3_native_identity_gate_passed": False, "current_K3_candidate_geometry_changed": False,
         "original_V5_raw_result_reclassified": False, "native_exact_membership_verified": False,
         "full_continuous_G2": False, "physical_qualification": False,
         "runtime": {n: importlib.metadata.version(n) for n in c["expected_43_package_versions"]}}

    def persist():
        r["seconds"] = time.monotonic() - start
        r["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        blob = (json.dumps(r, indent=2, allow_nan=False) + "\n").encode()
        need(len(blob) <= c["maximum_report_bytes"], "Registered report cap exceeded")
        (a.out / "R5_NATIVE_TRIM_CORE_WITNESS.json").write_bytes(blob)
        total = sum(p.stat().st_size for p in a.out.rglob("*") if p.is_file())
        need(total <= c["maximum_worker_output_bytes"], "Registered worker output cap exceeded")

    try:
        need(r["runtime"] == c["expected_43_package_versions"], "Original package versions differ")
        sys.path.insert(0, str(Path(c["inventory_source"]).parent))
        native = load(c["inventory_source"], "r5_original_native_inventory")
        cq, guard = native.cq, native.p.whole_material
        from OCP.BinTools import BinTools
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.TopoDS import TopoDS_Shape

        def shape_summary(shape):
            is_null = shape.isNull()
            counts = {name: 0 if is_null else len(getattr(shape, name.capitalize())())
                      for name in ("solids", "shells", "faces", "wires", "edges", "vertices")}
            valid = False if is_null else shape.isValid()
            area = 0.0 if is_null else float(shape.Area())
            need(math.isfinite(area) and area >= 0, "Nonfinite or negative native area")
            if is_null:
                category = "null_shape_unresolved"
            elif not valid:
                category = "invalid_topology_unresolved"
            elif counts["solids"] or counts["shells"]:
                category = "higher_dimension_unresolved"
            elif counts["faces"]:
                category = "positive_face_area" if area > 0 else "zero_area_face_unresolved"
            elif counts["edges"] or counts["vertices"]:
                category = "edge_or_vertex_only_boundary"
            elif all(n == 0 for n in counts.values()):
                category = "topologically_empty"
            else:
                category = "other_topology_unresolved"
            return {"is_null": is_null, "valid": valid, "shape_type": None if is_null else shape.ShapeType(),
                    "counts": counts, "native_area_mm2": area, "native_area_binary64_hex": area.hex(),
                    "classification": category, "zero_3D_volume_used_as_face_emptiness": False}

        def export(shape, name, whole=False):
            path = geometry / (name + ".brep")
            need(not path.exists(), "New exact operand/result path required")
            status = BinTools.Write_s(shape.wrapped, str(path))
            need(status is not False and path.is_file(), "Native BREP export failed")
            summary = shape_summary(shape)
            if whole:
                solids, volume = guard(shape, empty=True)
                summary["original_whole_material_guard"] = {"passed": True, "signed_volume_mm3": volume,
                                                            "solid_signed_volumes_mm3": [s.Volume() for s in solids]}
                if solids:
                    summary["classification"] = "complete_positive_3D_material"
            return {"path": str(path.relative_to(a.out)), **ident(path), "native": summary}

        def read(path):
            native_shape = TopoDS_Shape()
            need(BinTools.Read_s(native_shape, str(path)), "Native BREP read failed")
            return cq.Shape.cast(native_shape)

        parents, faces = {}, {}
        selected_faces = {}
        for row in selection["hole_witnesses"]:
            selected_faces.setdefault(tuple(row["material_key"]), {})[row["face_index"]] = row
        for item in selection["materials"]:
            key = tuple(item["material_key"])
            input_path = Path(c["workspace_root"]) / item["input_path"]
            body = read(input_path)
            solids, volume = guard(body)
            need(len(solids) == 1, "One original complete panel solid required")
            inventory = native.inspect(body)
            need(inventory["counts"] == item["original_complete_boundary_counts"], "Whole original topology counts changed")
            parents[key] = body
            faces[key] = body.Faces()
            copy_path = geometry / (key[0] + "-m" + str(key[1]) + "-original-input.brep")
            copy_path.write_bytes(input_path.read_bytes())
            r["whole_inputs"].append({"material_key": list(key), "exact_input_copy": {"path": str(copy_path.relative_to(a.out)), **ident(copy_path)},
                                      "native_signed_volume_mm3": volume, "counts": inventory["counts"],
                                      "current_K3_identity_claimed": False})
            for index, spec in selected_faces[key].items():
                fresh = inventory["faces"][index]
                expected = source_faces[(*key, index)]
                # Area is an observed numerical integral, kept separately from
                # the complete boundary parameters and topological identity.
                geometry_equal = {k: v for k, v in fresh.items() if k != "native_area"} == {k: v for k, v in expected.items() if k != "native_area"}
                need(geometry_equal and fresh["native_valid"], "Selected native face no longer matches the original source")
                face_export = export(faces[key][index], key[0] + "-m" + str(key[1]) + "-face" + str(index))
                r["native_face_bindings"].append({"material_key": list(key), "face_index": index,
                                                 "source_face_canonical_sha256": canonical(expected),
                                                 "fresh_face_canonical_sha256": canonical(fresh),
                                                 "boundary_parameters_and_topology_equal": geometry_equal,
                                                 "native_area_binary64_equal": fresh["native_area"] == expected["native_area"],
                                                 "original_native_area": expected["native_area"], "fresh_native_area": fresh["native_area"],
                                                 "export": face_export})
            persist()
        patches = {}
        for spec in selection["hole_witnesses"]:
            row = {"witness_id": spec["witness_id"], "material_key": spec["material_key"],
                   "face_index": spec["face_index"], "wire_index": spec["wire_index"], "failure": None}
            r["original_core_intersections"].append(row)
            try:
                key = tuple(spec["material_key"])
                face = faces[key][spec["face_index"]]
                uv = [v["float"] for axis in spec["native_UV_outward_box"] for v in axis]
                tolerance = spec["face_tolerance"]["float"]
                need(float(BRep_Tool.Tolerance_s(face.wrapped)) == tolerance, "Original face tolerance differs")
                patch = face.trim(*uv, tol=tolerance)
                need(patch.isValid() and len(patch.Faces()) == 1 and patch.Area() > 0, "Constructed whole UV patch is invalid")
                patches[spec["witness_id"]] = patch
                row["patch"] = export(patch, spec["witness_id"] + "-core-patch")
                row["actual_common"] = export(face.intersect(patch), spec["witness_id"] + "-original-face-common")
                row["absence_of_positive_face_area_observed"] = row["actual_common"]["native"]["counts"]["faces"] == 0
                row["topological_empty_observed"] = row["actual_common"]["native"]["classification"] == "topologically_empty"
            except Exception as exc:
                row["failure"] = {"type": type(exc).__name__, "message": str(exc)}
            persist()
        for key in sorted(parents):
            index = min(selected_faces[key])
            face = faces[key][index]
            for kind, other in (("positive_self", face), ("outside_1000mm", face.translate((1000.0, 0.0, 0.0)))):
                name = key[0] + "-m" + str(key[1]) + "-control-" + kind
                row = {"material_key": list(key), "face_index": index, "kind": kind,
                       "operand": export(other, name + "-operand"), "common": export(face.intersect(other), name + "-common")}
                summary = row["common"]["native"]
                row["expected_class_observed"] = (summary["classification"] == "positive_face_area") if kind == "positive_self" else (summary["classification"] == "topologically_empty")
                r["native_controls"].append(row)
                persist()
        old_path, current_path = [Path(c["workspace_root"]) / mapping[k]["input_path"] for k in ("K3_original_panel", "K3_current_panel")]
        old, current = read(old_path), read(current_path)
        guard(old); guard(current)
        for name, path in (("K3-original-panel", old_path), ("K3-current-panel", current_path)):
            target = geometry / (name + "-exact-input.brep")
            target.write_bytes(path.read_bytes())
            r["whole_inputs"].append({"current_candidate_role": name, "exact_input_copy": {"path": str(target.relative_to(a.out)), **ident(target)}})
        mapping_ok = {}
        for spec in mapping["original_material_mappings"]:
            key = tuple(spec["material_key"])
            shift = spec["native_inverse_translation_binary64_mm"]
            transformed = parents[key].translate(tuple(shift)) if any(shift) else parents[key]
            left = export(transformed.cut(old), key[0] + "-m" + str(key[1]) + "-mapped-minus-K3-original", whole=True)
            right = export(old.cut(transformed), key[0] + "-m" + str(key[1]) + "-K3-original-minus-mapped", whole=True)
            passed = left["native"]["classification"] == right["native"]["classification"] == "topologically_empty"
            mapping_ok[key] = passed
            r["material_mapping"].append({"material_key": list(key), "inverse_translation_mm": shift,
                                          "mapped_whole_operand": export(transformed, key[0] + "-m" + str(key[1]) + "-mapped-whole", whole=True),
                                          "mapped_minus_K3_original": left, "K3_original_minus_mapped": right,
                                          "finite_native_material_and_pose_gate_passed": passed})
            persist()
        removed, added = old.cut(current), current.cut(old)
        r["current_added_material_account"] = {"original_minus_current": export(removed, "K3-original-minus-current", whole=True),
                                                "current_minus_original": export(added, "K3-current-minus-original", whole=True),
                                                "original_saved_account": mapping["original_saved_added_material_account"]}
        account = r["current_added_material_account"]
        added_volume = account["current_minus_original"]["native"]["original_whole_material_guard"]["signed_volume_mm3"]
        account_ok = account["original_minus_current"]["native"]["classification"] == "topologically_empty" and abs(added_volume - mapping["original_saved_added_material_account"]["added_mm3"]) <= native.p.TOL
        account["original_native_material_account_gate_passed"] = account_ok
        r["current_K3_native_identity_gate_passed"] = account_ok and all(mapping_ok.values())
        inverse = {tuple(x["material_key"]): x["native_inverse_translation_binary64_mm"] for x in mapping["original_material_mappings"]}
        for spec in selection["hole_witnesses"]:
            key = tuple(spec["material_key"])
            row = {"witness_id": spec["witness_id"], "material_key": spec["material_key"], "executed": False, "failure": None}
            r["current_added_core_intersections"].append(row)
            if not (account_ok and mapping_ok.get(key) and spec["witness_id"] in patches):
                row["not_executed_reason"] = "Required original-material/pose or current added-material native gate did not pass"
                continue
            try:
                patch = patches[spec["witness_id"]].translate(tuple(inverse[key])) if any(inverse[key]) else patches[spec["witness_id"]]
                row["mapped_patch"] = export(patch, spec["witness_id"] + "-global-core-patch")
                row["actual_added_material_common"] = export(added.intersect(patch), spec["witness_id"] + "-K3-added-common")
                row["executed"] = True
                row["added_material_topologically_absent_on_native_patch"] = row["actual_added_material_common"]["native"]["classification"] == "topologically_empty"
                row["whole_current_native_trim_model_membership_proved"] = False
            except Exception as exc:
                row["failure"] = {"type": type(exc).__name__, "message": str(exc)}
            persist()
        r["sources_and_records_unchanged"] = all(ident(x["path"]) == x["identity"] for x in c["bound_records"] + c["bound_sources"])
        r["runtime_versions_unchanged"] = {n: importlib.metadata.version(n) for n in c["expected_43_package_versions"]} == r["runtime"]
        r["all_original_80_intersections_executed"] = len(r["original_core_intersections"]) == 80 and all(x["failure"] is None for x in r["original_core_intersections"])
        r["completed"] = r["sources_and_records_unchanged"] and r["runtime_versions_unchanged"] and r["all_original_80_intersections_executed"] and len(r["native_controls"]) == 8 and all(x["expected_class_observed"] for x in r["native_controls"]) and all(x["failure"] is None for x in r["current_added_core_intersections"])
    except Exception as exc:
        r["issues"].append({"type": type(exc).__name__, "message": str(exc)})
    persist()
    print(json.dumps({k: r[k] for k in ("completed", "seconds", "peak_RSS_bytes", "issues", "current_K3_native_identity_gate_passed")}), flush=True)
    return 0 if r["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
