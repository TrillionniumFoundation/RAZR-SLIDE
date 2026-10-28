"""Independent lossless provenance/readback audit. No V6 geometry module imports.

The exact arithmetic below only reconstructs boxes/volumes in already-executed
V5 certificate trees to identify source leaves. It does not search channels,
evaluate the V6 primitive enclosure or execute a new qualification worker.
"""
from datetime import datetime, timezone
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "R5_V6_INDEPENDENT_SOURCE_PROJECTION_AUDIT.json"
PLAN = HERE / "R5_V6_SOURCE_ONLY_REVIEW_PLAN.json"
SOURCE = ROOT / "r5-envelope"
ACTUAL = ROOT / "r5-ci-results/run-40645988108"
HEAD = "2ce252f25d340b056bfd350bdde8c743f915c9a4"
RUN = 40645988108
TINY = Q(1e-7) / 100000
ASSERTIONS = 0


def require(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise ValueError(message)


def digest(path):
    path = Path(path)
    with path.open("rb") as stream:
        value = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": value}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def data(path):
    return json.loads(Path(path).read_text())


def byte_record(path, expected):
    actual = digest(path)
    require(actual == {key: expected[key] for key in ("bytes", "sha256")}, "byte identity: " + str(path))
    return actual


def exact_box(encoded):
    require(len(encoded) == 3 and all(len(pair) == 2 for pair in encoded), "three dimensional exact box")
    result = tuple(tuple(Q(value) for value in pair) for pair in encoded)
    require(all(a <= b for a, b in result), "directed box order")
    return result


def volume(box):
    result = Q(1)
    for a, b in box:
        result *= b - a
    return result


def reconstruct_tree(root):
    """Read existing partition topology, not the producer traversal algorithm."""
    nodes = root["tree"]["nodes"]
    require([row["id"] for row in nodes] == list(range(len(nodes))), "original node identity/order")
    boxes = {0: exact_box(root["root_box_exact"])}
    require(volume(boxes[0]) > 0 and volume(boxes[0]) == Q(root["root_directed_volume_exact"]), "positive original root volume")
    remaining = list(range(len(nodes)))
    visited = set()
    leaf_sum = Q(0)
    retained = excluded = Q(0)
    # An iterative topological read tolerates any stored parent/child order.
    while remaining:
        progress = False
        later = []
        for index in remaining:
            if index not in boxes:
                later.append(index)
                continue
            require(index not in visited, "unique reached node")
            visited.add(index)
            node = nodes[index]
            box = boxes[index]
            amount = volume(box)
            require(amount > 0, "positive reached node volume")
            kind = node["kind"]
            if kind == "split":
                axis = node["axis"]
                cut = Q(node["cut_exact"])
                require(type(axis) is int and 0 <= axis < 3 and box[axis][0] < cut < box[axis][1], "original strict interior cut")
                children = node["children"]
                require(len(children) == 2 and children[0] != children[1], "two original distinct children")
                for child, interval in zip(children, ((box[axis][0], cut), (cut, box[axis][1]))):
                    require(type(child) is int and 0 <= child < len(nodes) and child not in boxes, "unique original parentage")
                    next_box = list(box)
                    next_box[axis] = interval
                    boxes[child] = tuple(next_box)
            else:
                require(kind in ("retained", "excluded"), "existing tree leaf classification")
                require(Q(node["positive_directed_volume_exact"]) == amount, "original exact leaf volume")
                leaf_sum += amount
                if kind == "retained":
                    retained += amount
                else:
                    excluded += amount
            progress = True
        require(progress, "all original nodes reachable without cycle")
        remaining = later
    require(len(visited) == len(nodes) and leaf_sum == volume(boxes[0]), "complete existing partition and conservation")
    require(retained == Q(root["tree"]["retained_sum_exact"]) and excluded == Q(root["tree"]["excluded_open_sum_exact"]), "existing tree sums")
    return boxes, retained, excluded


def main():
    require(not OUT.exists(), "new immutable audit report name required")
    plan = data(PLAN)
    limits = plan["budget"]
    require(limits["wall_seconds"] == 90 and limits["address_space_limit_bytes"] == 402653184, "preregistered source-only budget")
    resource.setrlimit(resource.RLIMIT_AS, (402653184, 402653184))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("registered 90 s source-only audit budget")))
    signal.alarm(90)
    start = time.monotonic()
    result = {
        "schema": "razr-r5e-v6-independent-source-only-readback",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "audit_completed": False,
        "preregistered_plan": digest(PLAN),
        "audit_source": digest(__file__),
        "formal_V6_worker_executed": False,
        "producer_helper_or_checker_imported": False,
        "new_native_operations": 0,
        "new_mathematical_qualification": False,
        "new_V6_channel_search_executed": False,
        "old_V5_channel_search_replayed": False,
        "existing_tree_box_readback_only": True,
        "native_resource_gate_admission_claimed": False,
        "original_owned_worker_gates_modified": False,
        "native_primitive_semantics_verified": False,
        "native_trim_class_membership_verified": False,
        "original_raw_gate_reclassified": False,
        "full_continuous_G2": False,
        "all_blockers_closed": False,
    }
    watched = {}
    def bind(path, expected=None):
        path = Path(path).resolve()
        record = byte_record(path, expected) if expected is not None else digest(path)
        watched[path] = record
        return record
    try:
        own_prior = ROOT / "r5-integration/independent-envelope-v5-execution-review/R5_V5_INDEPENDENT_ACTUAL_EXECUTION_READBACK.json"
        result["already_completed_independent_V5_readback"] = bind(own_prior, {
            "bytes": 312550,
            "sha256": "93a1b8098f81d46a4eea5cac5e4dfc01639dde220bb771c71b08e7060c361ee4",
        })
        prior_audit = data(own_prior)
        require(prior_audit["audit_completed"] and prior_audit["actual_run_id"] == RUN and prior_audit["actual_head"] == HEAD, "previous actual V5 audit identity")
        require(prior_audit["actual_conditional_model_passes"] == 8 and prior_audit["original_V3_raw_passes_unchanged"] == 4, "previous real results preserved")
        actual_zip = ROOT / "r5-ci-results/RAZR-R5-trim-model-v5-run-40645988108.zip"
        result["actual_V5_archive"] = bind(actual_zip, {"bytes": 1356621, "sha256": "3128fa481c2e7fe5e5cbf4e09822739349cc1e12b0edf16544c483ca7bdac0d9"})
        names = ("R5E_V6_PRIMITIVE_SOURCE.json.gz", "R5E_V6_REAL_RETAINED_LEAF.json", "R5E_V6_BASE_V5_INPUT_BRIDGE.json")
        fixed = (
            {"bytes": 51349, "sha256": "1dfc953f6ef255ac8fdfe93d147c293049753b38c871ed4f4198bb5d089ba695"},
            {"bytes": 39261, "sha256": "1e52b5f2021674f0e798aa97418ced7ceb0bdedd4fb7a08d1fc20a65ea136d5b"},
            {"bytes": 4997, "sha256": "639dcb2d0d079dfd2e8356b1f096486a8f49c61aaeb2ecfd428988a0ab408335"},
        )
        result["V6_source_artifacts"] = [dict(bind(SOURCE / name, expected), path=name) for name, expected in zip(names, fixed)]
        receipt = data(SOURCE / "R5E_V6_PRIMITIVE_SOURCE_RECEIPT.json")
        result["source_projection_receipt"] = bind(SOURCE / "R5E_V6_PRIMITIVE_SOURCE_RECEIPT.json")
        require(receipt["outputs"] == result["V6_source_artifacts"], "source receipt exact outputs")
        require(receipt["mechanical_source_projection_only"] and receipt["formal_worker_executed"] is False and receipt["new_geometric_pass_claimed"] is False, "projection receipt scope")
        decoded = gzip.decompress((SOURCE / names[0]).read_bytes())
        require(len(decoded) == receipt["decoded_projection_bytes"] == 711235, "exact decoded projection size")
        projection = json.loads(decoded)
        del decoded
        require(projection["schema"] == "razr-r5e-original-primitive-source-projection-v6", "projection schema")
        require(projection["actual_V5_run_id"] == RUN and projection["actual_V5_request_commit"] == HEAD, "projection actual origin")
        require(projection["native_inventory_was_preexisting_actual_evidence"] is True, "original inventory only")
        for key in ("new_mathematical_qualification", "original_pcurve_values_changed", "native_primitive_semantics_verified", "native_trim_class_membership_verified"):
            require(projection[key] is False, "unchanged conditional scope: " + key)
        require(projection["new_native_operations"] == 0, "no new native operations")
        r4_path = ROOT / "r4-envelope/public-final-v2/support-v4/report.json"
        result["original_R4_report"] = bind(r4_path, projection["original_public_R4_report_identity"])
        r4 = data(r4_path)
        native_rel = "native-and-math/producer/worker/report.json"
        require(projection["original_native_inventory_relative_path"] == native_rel, "complete native inventory relative identity")
        native_anchor = next(row for row in r4["input_identities"] if row["path"] == native_rel)
        require(projection["original_native_inventory_identity"] == {k: native_anchor[k] for k in ("bytes", "sha256")} == receipt["source_inventory"], "original inventory triple anchor")
        native_path = ROOT / "recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027" / native_rel
        # One actual native inventory read supplies both its digest and parser.
        native_bytes = native_path.read_bytes()
        native_identity = {"bytes": len(native_bytes), "sha256": hashlib.sha256(native_bytes).hexdigest()}
        require(native_identity == projection["original_native_inventory_identity"], "original inventory exact bytes")
        native = json.loads(native_bytes)
        del native_bytes
        require(native["execution_completed"], "original inventory completed")
        originals = {(row["input"]["case_id"], row["input"]["material_id"]): row for row in native["operands"]}
        require(len(originals) == len(native["operands"]) == 53, "53 unique original operands")
        result["original_native_inventory"] = native_identity
        v5_projection_path = SOURCE / "R5E_V5_PLANAR_TRIM_SOURCE.json.gz"
        result["frozen_V5_projection"] = bind(v5_projection_path, {"bytes": 35630, "sha256": "bc778c13f9efbc280bcb93e59edbc821d2a7b751f0b8730231d1b0bd855e2804"})
        v5_projection = json.loads(gzip.decompress(v5_projection_path.read_bytes()))
        bridge = data(SOURCE / names[2])
        require(bridge["actual_run_id"] == RUN and bridge["actual_request_commit"] == HEAD, "bridge actual origin")
        require(bridge["original_reports_or_certificates_edited"] is False and bridge["path_mapping_only"] is True, "path-only bridge scope")
        require(bridge["public_repository_relative_root"] == "engineering/engineering-followup-20261028-r5/envelope/actions/run-40645988108", "registered public archive root")
        require(len(bridge["files"]) == 25 and len({row["path"] for row in bridge["files"]}) == 25, "25 distinct immutable bridge members")
        result["actual_V5_bridge_members"] = []
        for row in bridge["files"]:
            member = (ACTUAL / row["path"]).resolve()
            require(member.is_relative_to(ACTUAL.resolve()), "bridge member remains in actual root")
            result["actual_V5_bridge_members"].append(dict(bind(member, row), path=row["path"]))
        report_path = ACTUAL / "all-trim-model-frames/report.json"
        report = data(report_path)
        independent = data(ACTUAL / "verify-all/report.json")
        pipeline = data(ACTUAL / "pipeline.json")
        require(report["execution_completed"] and independent["execution_completed"] and pipeline["completed"], "actual V5 reports completed")
        require(report["trim_model_conditional_clearance_passes"] == independent["trim_model_conditional_clearance_passes"] == 8, "actual V5 eight conditional passes preserved")
        require(pipeline["environment"]["github_sha"] == HEAD and str(pipeline["environment"]["github_run_id"]) == str(RUN), "actual V5 runtime run/head")
        require(pipeline["source_lock_identity"]["sha256"] == "d05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211", "actual V5 source lock")
        require(bind(report_path) == projection["actual_V5_report_identity"], "projection actual report identity")
        frame_order = [(case, frame) for case in ("case-001", "case-006", "case-028", "case-037", "case-054", "case-063", "case-072", "case-089") for frame in (1, 2)]
        for rows in (report["frames"], r4["frames"], projection["frame_bindings"], v5_projection["frame_bindings"]):
            require([(row["case_id"], row["frame"]) for row in rows] == frame_order, "complete original 16-frame order")
        targets = {}
        result["frames"] = []
        selected = data(SOURCE / names[1])
        found_selected = False
        total_retained = total_tiny = total_other = total_decoded = total_observations = 0
        observed_members = {
            "pipeline.json", "all-trim-model-frames/report.json", "verify-all/report.json",
            "all-trim-model-frames-supervision/controller.json", "verify-all-supervision/controller.json",
            "all-trim-model-frames-contract.json", "all-trim-model-frames-supervision-contract.json",
            "verify-all-contract.json", "verify-all-supervision-contract.json",
        }
        for row, original_frame, binding, old_binding in zip(report["frames"], r4["frames"], projection["frame_bindings"], v5_projection["frame_bindings"]):
            key = (row["case_id"], row["frame"])
            new_fields = {"actual_V5_certificate", "actual_V5_retained_leaf_locators", "actual_V5_non_tiny_retained_leaf_locators"}
            require({k: v for k, v in binding.items() if k not in new_fields} == old_binding, "original full frame binding copied verbatim")
            require(binding["original_full_D"] == row["original_remaining_displacement_box_exact"] == original_frame["full_remaining_displacement_box_exact"], "all full D components preserved")
            require(binding["original_R4_raw_proof_identity"] == row["original_raw_proof_identity"] == original_frame["proof"], "original R4 proof identity")
            require(row["pair"] == original_frame["pair"], "original frame material pair")
            relative = "all-trim-model-frames/" + row["certificate"]["path"]
            observed_members.add(relative)
            path = ACTUAL / relative
            identity = bind(path, row["certificate"])
            require(binding["actual_V5_certificate"] == dict(identity, path=relative), "new binding exact actual certificate")
            raw = gzip.decompress(path.read_bytes())
            total_decoded += len(raw)
            certificate = json.loads(raw)
            del raw
            require(certificate["frame"] == {k: v for k, v in row.items() if k != "certificate"}, "entire V5 certificate frame header")
            sources = certificate["boundary_refinement"]["sources"]
            require(len(sources) == 2 and [source["material_key"] for source in sources] == binding["moving_and_fixed_material_keys"], "both actual whole material keys")
            locators = []
            non_tiny = []
            retained_sum = excluded_sum = Q(0)
            for original_root in certificate["roots"]:
                boxes, kept, excluded = reconstruct_tree(original_root)
                retained_sum += kept
                excluded_sum += excluded
                for node in original_root["tree"]["nodes"]:
                    if node["kind"] != "retained":
                        continue
                    locator = [original_root["original_cell_index"], node["id"]]
                    locators.append(locator)
                    total_retained += 1
                    amount = volume(boxes[node["id"]])
                    if amount <= TINY:
                        total_tiny += 1
                        continue
                    total_other += 1
                    non_tiny.append(locator)
                    require(row["trim_model_conditional_clearance_gate_passed"] is False and node["reason"] == "no_registered_model_boundary_endpoint_inside_cell", "actual unresolved non-tiny classification")
                    obstruction = node["actual_channel_observation"]["all_registered_channels_blocked"]
                    require(len(obstruction) == 12 and {(item["material_side"], item["axis"], item["end"]) for item in obstruction} == {(side, axis, end) for side in (0, 1) for axis in range(3) for end in (0, 1)}, "all actual 12 channel observations")
                    for item in obstruction:
                        side = item["material_side"]
                        piece = sources[side]["pieces"][item["blocking_piece_index"]]
                        require(piece["kind"] == "face" and piece["replacement"] == "unchanged", "actual blocker is unchanged whole-source face")
                        material_key = tuple(binding["moving_and_fixed_material_keys"][side])
                        targets.setdefault(material_key, set()).add(piece["index"])
                        total_observations += 1
                    if key == ("case-028", 1) and locator == [8, 13]:
                        require(not found_selected, "single selected witness")
                        found_selected = True
                        require(selected["schema"] == "razr-r5e-actual-v5-retained-leaf-selection-v6", "selection schema")
                        require((selected["case_id"], selected["frame"], selected["original_R4_root_index"], selected["actual_V5_leaf_node_index"]) == ("case-028", 1, 8, 13), "fixed actual retained witness")
                        require(selected["actual_V5_leaf_record"] == node and selected["actual_V5_original_root_record"] == original_root, "entire original selected leaf/root records")
                        require(exact_box(selected["leaf_box_exact"]) == boxes[node["id"]], "selected exact box independently reconstructed")
                        require(Q(selected["positive_directed_volume_exact"]) == amount and selected["original_full_D"] == binding["original_full_D"] and selected["pair"] == row["pair"], "selected positive measure, full D and pair")
                        require(selected["actual_V5_certificate"] == dict(identity, path=relative) and selected["actual_V5_report"] == dict(digest(report_path), path="all-trim-model-frames/report.json"), "selected source byte identities")
                        require(selected["actual_V5_run_id"] == RUN and selected["actual_V5_request_commit"] == HEAD and selected["new_geometric_pass_claimed"] is False and selected["original_source_values_changed"] is False, "selected source scope and actual run/head")
                        result["selected_actual_retained_leaf"] = {k: selected[k] for k in ("case_id", "frame", "original_R4_root_index", "actual_V5_leaf_node_index", "leaf_box_exact", "positive_directed_volume_exact", "original_full_D", "pair", "actual_V5_certificate", "actual_V5_report")}
            require(locators == binding["actual_V5_retained_leaf_locators"] and non_tiny == binding["actual_V5_non_tiny_retained_leaf_locators"], "all exact retained leaf locators")
            require(retained_sum == Q(row["retained_leaf_sum_exact"]) and excluded_sum == Q(row["excluded_open_leaf_sum_exact"]), "existing full frame tree sums")
            result["frames"].append({"case_id": key[0], "frame": key[1], "pair": row["pair"], "material_keys": binding["moving_and_fixed_material_keys"], "original_full_D": binding["original_full_D"], "retained_leaf_count": len(locators), "non_tiny_retained_leaf_locators": non_tiny, "retained_leaf_locator_canonical_sha256": canonical(locators), "retained_exact_volume_sum": str(retained_sum), "actual_V5_certificate": dict(identity, path=relative), "all_old_binding_fields_equal": True})
        require(found_selected, "actual selected witness recovered")
        require(observed_members == {row["path"] for row in bridge["files"]}, "exact full 25 required input members")
        require((total_retained, total_tiny, total_other, total_observations) == (1537, 1493, 44, 528), "complete actual retained-source census")
        require((receipt["actual_V5_retained_leaves"], receipt["actual_V5_tiny_retained_leaves"], receipt["actual_V5_non_tiny_retained_leaves"]) == (total_retained, total_tiny, total_other), "receipt actual leaf census")
        require(len(projection["records"]) == len(v5_projection["records"]) == 32, "32 complete projected material rows")
        result["materials"] = []
        seen_materials = set()
        planes = cylinders = 0
        for row, old_row in zip(projection["records"], v5_projection["records"]):
            key = (row["input"]["case_id"], row["input"]["material_id"])
            require(key not in seen_materials, "unique projected whole material")
            seen_materials.add(key)
            original = originals[key]
            boundary = original["boundary"]
            require(row["input"] == original["input"] == old_row["input"], "complete original material input equality")
            require(row["original_complete_boundary_counts"] == boundary["counts"] == old_row["original_complete_boundary_counts"], "full original boundary counts")
            boundary_hash = canonical(boundary)
            require(row["original_complete_boundary_canonical_sha256"] == boundary_hash == old_row["original_complete_boundary_canonical_sha256"], "full original whole-boundary canonical identity")
            require(row["full_original_face_records_unchanged"] is True, "complete face lossless scope")
            face_indices = [candidate["face_index"] for candidate in row["candidate_faces"]]
            require(face_indices == sorted(targets.get(key, set())), "candidate face set equals actual blocked-source set")
            faces = []
            for candidate in row["candidate_faces"]:
                index = candidate["face_index"]
                original_face = boundary["faces"][index]
                require(original_face["index"] == index and candidate["complete_original_face"] == original_face, "entire original face verbatim equality")
                face_hash = canonical(original_face)
                require(candidate["complete_original_face_canonical_sha256"] == face_hash, "entire original face canonical identity")
                kind = original_face["local_surface"]["type"].split(".")[-1]
                require(candidate["source_primitive"] == kind and kind in ("GeomAbs_Plane", "GeomAbs_Cylinder"), "exact primitive source type")
                require(candidate["selection_basis"] == "actual first blocking piece of an original V5 non-tiny retained leaf", "actual recorded selection basis")
                planes += kind == "GeomAbs_Plane"
                cylinders += kind == "GeomAbs_Cylinder"
                faces.append({"index": index, "primitive_type": kind, "complete_original_face_canonical_sha256": face_hash, "complete_original_wire_count": len(original_face["wires"]), "source_face_identical": True})
            result["materials"].append({"input": row["input"], "complete_original_boundary_counts": boundary["counts"], "complete_original_boundary_canonical_sha256": boundary_hash, "candidate_faces": faces})
        require(set(targets).issubset(seen_materials), "no original blocker material omitted")
        require((planes, cylinders) == (48, 16) and receipt["complete_material_records"] == 32 and receipt["complete_plane_records"] == planes and receipt["complete_cylinder_records"] == cylinders, "lossless complete primitive census")
        result["census"] = {"original_operands": 53, "material_records": 32, "complete_plane_faces": planes, "complete_cylinder_faces": cylinders, "actual_V5_retained_leaves": total_retained, "actual_V5_tiny_retained_leaves": total_tiny, "actual_V5_non_tiny_retained_leaves": total_other, "actual_prior_blocked_observation_records": total_observations, "actual_V5_certificate_reads": 16, "actual_V5_certificate_decoded_bytes": total_decoded, "original_native_inventory_reads": 1, "actual_V5_bridge_members": 25}
        result["input_identities"] = [dict(value, path=str(path.relative_to(ROOT))) for path, value in watched.items()]
        require(all(digest(path) == value for path, value in watched.items()), "source and archive inputs unchanged after audit")
        require(digest(__file__) == result["audit_source"] and digest(PLAN) == result["preregistered_plan"], "review source and registered plan unchanged")
        result["all_readback_inputs_unchanged"] = True
        result["audit_completed"] = True
    except BaseException as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        signal.alarm(0)
        result["audit_seconds"] = time.monotonic() - start
        result["audit_peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        result["assertion_count"] = ASSERTIONS
        result["registered_budget_respected"] = result["audit_seconds"] <= 90 and result["audit_peak_RSS_bytes"] <= 402653184
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        encoded = (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode()
        require(len(encoded) <= 4194304, "registered audit output bound")
        OUT.write_bytes(encoded)
        print(json.dumps({k: result.get(k) for k in ("audit_completed", "audit_seconds", "audit_peak_RSS_bytes", "assertion_count", "census", "failure")}, ensure_ascii=False))
    return 0 if result["audit_completed"] and result["registered_budget_respected"] else 2


if __name__ == "__main__":
    sys.exit(main())
