#!/usr/bin/env python3
"""Bind the final R4 checklist to completed records and saved scientific bytes."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
from pathlib import Path


def identity(path):
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("--workspace", required=True, type=Path)
    a = p.parse_args()
    root = a.workspace.resolve()
    public = root / "razr-current/engineering/engineering-followup-20261027-r4"
    read = lambda rel: json.loads((root / rel).read_text())
    v2 = read("r4-envelope/support-v2/report.json")
    v4 = read("r4-envelope/support-v4/report.json")
    verifier = read("r4-envelope/independent-support-v4/report.json")
    native = read("r4-native/public/R4_NATIVE_PUBLIC_EVIDENCE.json")
    runtime = read("r4-deliverables/R4_RUNTIME_EXECUTED_SUMMARY.json")
    sources = read("r4-sources/public/R4_SOURCE_EXECUTED_SUMMARY.json")
    git_objects = read("r4-recovery/R4_LOCAL_GIT_OBJECT_AVAILABILITY.json")
    assert v4["execution_completed"] and verifier["execution_completed"]
    assert runtime["current_runtime_snapshot_qualified"] and runtime["independent_full_byte_and_provenance_readback_qualified"]
    assert native["finite_result_summary"]["all62_direct_strict_and_independent_classifications_agree"]
    assert not sources["same_specimen_10_7_12_complete"] and not sources["all_blockers_closed"]
    assert not git_objects["requested_a11_object_present"]

    def gates(report):
        frames = report["frames"]
        return {"frames": len(frames), "min_volume_plus_TOL_passes": sum(x["original_min_volume_plus_TOL_gate_passed"] for x in frames), "clearance_1e_7_passes": sum(x["original_clearance_gate_passed"] for x in frames), "L2_diagnostic_clearance_passes": sum(x["declared_tolerance_diagnostic_gate_passed"] for x in frames)}

    assert gates(v4) == {"frames": 16, "min_volume_plus_TOL_passes": 16, "clearance_1e_7_passes": 4, "L2_diagnostic_clearance_passes": 0}
    state = {
        "schema": "razr-r4-current-checklist-state-v1",
        "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_source_anchor": "345af733716a21bf002bf1e16d7ed46594fa83a7",
        "scope": "Current user checklist and new executed R4 evidence; not a reconstructed old Git history or a declaration that every project task has been enumerated.",
        "all_blockers_closed": False,
        "original_exact_a11_publication_completed": False,
        "candidate_go": False,
        "fixture_fabrication_go": False,
        "manufacturing_go": False,
        "full_G2": False,
        "current_FE": False,
        "OEM_electrical_and_finished_stack_qualified": False,
        "G3": False,
        "G4": False,
        "G5": False,
        "new_product_material_modified": False,
        "runtime_snapshot_and_independent_readback_qualified": True,
        "whole_KEY_PAWL_62_comparisons_complete_and_independently_read_back": True,
        "whole_current_factory_all_pairs_reexecuted_in_R4": False,
        "source_release_support_threshold_recomputed_independently": True,
        "physical_release_hold_or_relock_qualified": False,
        "envelope_V2_original_two_gate_results": gates(v2),
        "envelope_V4_original_two_gate_results": gates(v4),
        "envelope_aggregate_legacy_field_note": "conditional_upper_bound_gate_failures=12 counts clearance failures, not min(volume)+TOL failures; the two original gates above are computed from individual frames.",
        "native_material_boundary_semantics_verified": False,
        "compiled_curve_or_transform_rounding_verified": False,
        "new_qualified_same_specimen_or_selected_part_facts": sources["new_qualified_requirements"],
        "original_fact_requirements": sources["original_per_fact_requirements"],
        "new_physical_measurements": sources["new_actual_physical_measurements"],
        "new_physical_G3_G4_G5_passes": 0,
        "original_numeric_contract_changed": False,
        "original_numeric_probes_or_H_restore_rerun_in_R4": False,
        "checklist": [
            {"item": "1. Original intermediate whole-factory witnesses", "state": "prior_evidence_retained", "closed_by_R4": False, "evidence": "The R2 original candidate-specific direct Common and whole-pair records remain preserved. R4 restores relevant inputs; it does not rerun or replace those whole factories."},
            {"item": "2. Current structure and admissible domain", "state": "partially_resolved", "closed_by_R4": False, "evidence": "Six whole originals,62 pair checks,conditional exclusion subdomain and original u=3 sufficient source release support are complete. No geometry trim was required by the u=1 observation.", "remaining": "Full correlated current-factory domain,other material pairs,current walls with sourced criteria,actual spring/hold/relock mechanics and FE."},
            {"item": "3. Continuous envelope method", "state": "conditional_bound_subtask_resolved_clearance_and_native_scope_open", "closed_by_R4": False, "evidence": "All16 original frames have conservative conditional complete-material bounds passing min(volume)+TOL;4 pass clearance. V4 independent enumeration and separate source/cell audit completed.", "remaining": "12 coarse spatial bounds,trimmed-face occupancy correlations,native boundary semantics and compiled transform/evaluation error guarantee."},
            {"item": "Parallel original numerical qualification", "state": "prior_qualified_scope_retained_new_runtime_qualified", "closed_by_R4": False, "evidence": "No original K,b,C or residual gate changes. Existing N13/N14/H/restore archives are indexed. Current runtime8112/43 with independent readback is qualified.", "remaining": "This runtime result does not qualify the current changed geometry FE or revalidate every historical solve."},
            {"item": "Parallel real device and OEM evidence", "state": "requires_real_inputs", "closed_by_R4": False, "evidence": "Exact-model official HTML binding and USB procedure source candidate found;0 of228 original fact requirements newly qualified.", "remaining": "Same-specimen10/7/12 originals,PN/revision,dimensions and uncertainty,orientation,terminals,function and manufacturer part/process documentation."},
            {"item": "Current structural/electrical/test contract", "state": "not_ready_to_freeze", "closed_by_R4": False, "remaining": "Current geometry FE and worst cases,OEM interconnect,finished stack,sourced G3-G5 thresholds,sampling,calibration and plan/version bindings."},
            {"item": "Sequential physical G3 -> G4 -> G5", "state": "not_executed", "closed_by_R4": False, "remaining": "The same candidate and specimen must obtain actual passes in order,retaining missing tests,failures,repairs and replacements separately."},
            {"item": "Requested exact original Git publication", "state": "original_objects_missing", "closed_by_R4": False, "remaining": "Original a11 Git objects/bundle and authenticated object-transfer transport. A new R4 commit is not a substitute."},
        ],
        "bound_record_identities": {rel: identity(root / rel) for rel in ["r4-envelope/support-v4/report.json", "r4-envelope/independent-support-v4/report.json", "r4-native/public/R4_NATIVE_PUBLIC_EVIDENCE.json", "r4-deliverables/R4_RUNTIME_EXECUTED_SUMMARY.json", "r4-sources/public/R4_SOURCE_EXECUTED_SUMMARY.json", "r4-integration/independent-native-release/R4_INDEPENDENT_RELEASE_DOMAIN_REVIEW.json"]},
    }
    (public / "R4_CHECKLIST_STATE.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    saved = []
    for batch in [1, 2]:
        receipt = read(f"r4-deliverables/R4_PRESERVATION_BATCH{batch}_FULL_READBACK.json")
        assert receipt["all_matched"]
        for row in receipt["files"]:
            assert row["full_byte_readback"] and row["zip_CRC_readback"] and row["local_identity_applied"]
            saved.append(row)
    assert len(saved) == 4 and len({r["file_name"] for r in saved}) == 4
    archive_public = {"schema": "razr-r4-new-scientific-archive-identities-v1", "files": [{key: row[key] for key in ["file_name", "bytes", "sha256", "full_byte_readback", "zip_CRC_readback"]} for row in saved], "all_four_saved_and_full_byte_read_back": True, "Git_repository_or_bundle_stored_in_these_archives": False, "public_summaries_do_not_replace_raw_scientific_records": True}
    (public / "R4_NEW_SCIENTIFIC_ARCHIVE_IDENTITIES.json").write_text(json.dumps(archive_public, ensure_ascii=False, indent=2) + "\n")
    original_path = root / "recovered-science/RAZR-SLIDE_R3_scientific_files_20261027.json"
    original = json.loads(original_path.read_text())
    files = list(original["files"])
    for row in saved:
        files.append({key: row[key] for key in ["file_name", "bytes", "sha256", "library_file_id", "file_id"]} | {"url": "https://chatgpt.com/library?file_id=" + row["library_file_id"] + "&account_id=personal", "R4_actual_preservation_and_full_byte_readback": True})
    catalog = {"schema": "razr-r4-preserved-scientific-files-directory-v1", "prior_directory_identity": identity(original_path), "prior_file_count": len(original["files"]), "new_file_count": len(saved), "file_count": len(files), "files": files, "prior_entries_inherited_without_new_execution_claim": True, "new_entries_all_have_actual_saved_full_byte_readback": True, "repository_sources_or_Git_bundle_stored_in_this_scientific_directory": False, "no_raw_science_replaced_by_public_projection": True, "all_blockers_closed": False}
    (root / "r4-deliverables/RAZR-SLIDE_R4_scientific_files_20261028.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    (public / "integration/finalize_followup_state_r4.py").write_bytes(Path(__file__).read_bytes())
    (public / "R4_LOCAL_GIT_OBJECT_AVAILABILITY.json").write_bytes((root / "r4-recovery/R4_LOCAL_GIT_OBJECT_AVAILABILITY.json").read_bytes())
    print(json.dumps({"checklist_written": True, "new_saved_archives": len(saved), "cumulative_science_files": len(files), "all_blockers_closed": False, "V4_original_gates": gates(v4)}))


if __name__ == "__main__":
    main()
