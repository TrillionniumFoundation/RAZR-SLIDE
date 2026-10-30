#!/usr/bin/env python3
"""Advance stale current-entrypoint metadata to the already recorded R7 scope.

This is a metadata synchronization. It does not execute CAD, a numerical solver,
or a physical test, and does not change historical scientific results.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE_COMMIT = "e51de63915a1abeed29e2f95be3044a5d5965045"
S4_COMMIT = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
R7 = "engineering/engineering-followup-20261028-r7"
R5 = "engineering/engineering-followup-20261028-r5"
R8 = "engineering/engineering-followup-20261029-r8/status"
LEDGER = f"{R7}/independent-review/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_V2.json"
NATIVE = f"{R7}/native/R7_ACTUAL_NATIVE80_AND_TWO_FINITE_POSES_SCOPE_V1.json"
NUMERIC = f"{R5}/numerics/R5_ORIGINAL_NUMERIC_QUALIFICATION_SCOPE.json"
HANDOFF = f"{R5}/handoff/R5_EXTERNAL_BLOCKER_HANDOFF_V2.json"
ORIGINAL_BLOBS = {
    "design/current_product.json": "361a4d9d5fcd4b29a862a8e147be081c8498d43b",
    "CURRENT_DESIGN.md": "e3895b5f4b3b1b3a16e2488e2b8ecac5fe3b710d",
    "status.json": "f972cabed2f779e4721546789b92e29e131a865f",
    "docs/RESEARCH_OVERVIEW.md": "4988fc655b5a56773b454828169e5429e70e9bd6",
    "tools/sync_current_design.py": "64616870da1280f5bc23d371dcecc4b8be877aac",
    "tools/test_suites.json": "919d27c8950aa35440f7959bc91f345c8f80b467",
    LEDGER: "d0264d2e4163e9f9d2f9a6b87b64e330e2a155d1",
    NATIVE: "3ff4a18b80153306419c38b553bf746d9387fdea",
    NUMERIC: "31f8ee48a7d4ac543d9c3bbb63197437b1fc3f80",
    HANDOFF: "af1b16c703796404376e0009555e17132336bb85",
}
CHANGED_FIELDS = (
    "stage_summary", "hardware_summary", "verification_summary", "work_packages",
    "open_research_prs", "last_update_date", "updated_utc", "current_execution_summary",
    "active_followup", "publication_record", "publication_record_scope",
)


def identity(path: Path) -> dict:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
    }


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def main() -> None:
    receipt_path = OUT / "R8_CURRENT_ENTRYPOINT_SYNC_RESULT.json"
    if receipt_path.exists():
        raise SystemExit("This recorded migration already ran; use the original generator --check for read-only verification.")
    before_identities = {path: identity(ROOT / path) for path in ORIGINAL_BLOBS}
    for path, expected in ORIGINAL_BLOBS.items():
        if before_identities[path]["git_blob_sha1"] != expected:
            raise SystemExit(f"Original Git identity mismatch: {path}")
    before = load("design/current_product.json")
    current = copy.deepcopy(before)
    ledger, native, numeric, handoff = (load(p) for p in (LEDGER, NATIVE, NUMERIC, HANDOFF))
    if ledger["functional_source_commit"] != S4_COMMIT:
        raise SystemExit("Unexpected functional source identity")
    if ledger["rows"][0]["status"] != "closed_for_two_finite_current_candidate_poses":
        raise SystemExit("Finite-pose scope is not the previously recorded R7 scope")
    if ledger["rows"][3]["status"] != "closed_for_original_historical_numeric_contract":
        raise SystemExit("Original numerical contract is not the previously recorded R7 scope")
    if native["finite_pose_count"] != 2 or native["full_continuous_G2"]:
        raise SystemExit("Unexpected native scope")
    residuals = numeric["panel_original_five_residuals"] + numeric["frame_original_five_residuals"]
    if len(residuals) != 10 or not all(v <= numeric["original_float64_residual_threshold"] for v in residuals):
        raise SystemExit("Original five-probe records do not support the summary")
    if handoff["current_actual_state"]["original_requirement_count"] != 228:
        raise SystemExit("Physical intake contract identity changed")
    for key in ("candidate_go", "fixture_fabrication_go", "manufacturing_go", "physical_phone_verified"):
        if before[key] is not False:
            raise SystemExit(f"Unexpected original release state: {key}")

    now = datetime.now(timezone.utc).isoformat()
    history_key = "prior_current_summary_before_20261029_r8"
    if history_key in current:
        raise SystemExit("R8 historical snapshot already exists")
    current[history_key] = {
        "source_commit": BASE_COMMIT,
        "source_file_git_blob_sha1": ORIGINAL_BLOBS["design/current_product.json"],
        "scope": "Exact prior values of each current-entrypoint field updated by R8; historical scientific records remain unchanged.",
        "fields": {key: copy.deepcopy(before[key]) for key in CHANGED_FIELDS},
    }
    current["last_update_date"] = "2026-10-29"
    current["updated_utc"] = now
    current["current_execution_summary"] = LEDGER
    current["publication_record"] = LEDGER
    current["publication_record_scope"] = (
        f"R8 entrypoint synchronization from the R7 evidence checkpoint {BASE_COMMIT}. "
        f"S4 {S4_COMMIT} remains the tested functional source. Named K1/K3 finite geometry "
        "and restored original numerical qualification retain their own exact scopes. "
        "This metadata change performs no CAD, solver, full-unit, physical or release execution."
    )
    current["stage_summary"] = (
        f"S4 {S4_COMMIT} remains the tested functional source. R7 completed the named "
        "key_forward_loop_v1 / panel_key_travel_stops_v1 full factories at slide "
        "23.142044210239405 and 60.880681403413135 mm: each producer and separate-process "
        "same-kernel reader recorded all 11781 pairs of 154 bodies; both sides' direct "
        "panel/KEY Common volumes are zero, with no positive pair, evaluation failure or "
        "classification mismatch. Original N15 K/b/C evidence qualifies all five panel "
        "and five frame float64 residuals at the unchanged 1e-7 threshold, with the "
        "original H and five SHA-bound saved-action restore scope preserved. This does "
        "not qualify current K1/K3 structure. Positive-q STOP/SPRING source branches are "
        "recorded; true physically supported independent domains remain open. V6 retains "
        "8 conditional passes and 8 non-passes across the original 16 cases. V9's owned "
        "supervision failure and unreached first-u gate remain failures/unexecuted stages; "
        "the later depth-25 Line diagnostic does not satisfy the original depth-24 budget. "
        "The 228 original specimen/selected-revision facts, current FE/tolerances/OEM/stackup "
        "and real G3-G5 remain unqualified. All release flags remain false. "
        f"The controlling scope is {LEDGER}; the R8 entrypoint-only validation is {R8}/R8_CURRENT_ENTRYPOINT_SYNC_RESULT.json."
    )
    current["verification_summary"] = (
        "Historical S4 D6 is the actual 36-suite/1654-test full-unit pass; this evidence "
        "successor is not a new full software execution. R7's two repaired-candidate "
        "finite factories and separate-process readers each completed the original "
        "all-pair/STEP criteria. The original N15 numerical records preserve K/b/C, full "
        "fields, corrections and the five saved-action restore scope; their recovery "
        "does not rerun a solver or transfer FE qualification to K1/K3. Original F1 "
        "interference, N7 rejection, V9 supervision failure and all other historical "
        "failures retain their original identity. R8 verifies exact source blob identities, "
        "the original generator's output agreement and unchanged historical/release "
        "scope. It performs no new CAD, numerical, OEM electrical or physical acquisition. "
        "Full continuous G2, current structural qualification and G3-G5 remain open."
    )
    current["hardware_summary"] = (
        before["hardware_summary"]
        + " The later R5/R7 intake and handoff preserve 228 unique required facts: ten "
        "identity facts, 77 fields for seven part roles, 120 fields for twelve actual "
        "interfaces, and 21 selected-part revision facts. Of these, 207 require the "
        "same specimen and 21 the actually selected PN/revision. No qualified new "
        "specimen/OEM binding or physical G3/G4/G5 pass is recorded. The official "
        "XT2551-3 quick guide is model literature and supplies none of those bindings. "
        f"The existing H00-H12 handoff is {HANDOFF}. R8 changes entrypoint metadata only; "
        "it does not repeat a device-access attempt or create physical observations."
    )
    packages = {item["id"]: item for item in current["work_packages"]}
    packages["WP1"].update({
        "result": "R5/R7 retain 228 unbound original facts: 10 identity, 77 seven-role part, 120 twelve-interface and 21 selected-PN/revision facts. No qualified new physical observation is recorded.",
        "path": HANDOFF,
        "remaining": "Deliver actual same-specimen labels/photos, PN/revision, dimensions and uncertainty, orientation, terminal maps and original-device function; bind selected OLED/COF/FPC, connectors and material/process sources.",
    })
    packages["WP2"]["result"] = "Historical " + before["work_packages"][2]["result"]
    packages["WP4"].update({
        "result": "R7 completes the two named K1/K3 repaired full-factory poses at slide 23.142044210239405 and 60.880681403413135 mm. Each producer/reader has 154 bodies and 11781 pair records; both panel/KEY sides are zero Common and all pair classifications agree. Positive-q branches are source-bound. Original V6 remains 8/16 conditional passes; V9 failed owned supervision before first-u, and the later Line certificate is a depth-25 local conditional result.",
        "path": LEDGER,
        "remaining": "Qualify complete continuous envelopes under the original domain/depth/criteria, native material/error semantics, physically supported independent left/right and telescope domains, flexible self-validity, return and relock. Finite-pose success does not close G2.",
    })
    packages["WP5"].update({
        "result": "K1 KEY and K3 panel material identities and finite native mapping are retained. The current contract still has 154 nominal material assignments and 13 unsourced load cases. Local leg section dimensions do not establish global minimum wall thickness or strength.",
        "path": HANDOFF,
        "remaining": "Obtain actual material/process, contact/friction/preload, loads and correlated tolerances; qualify current K1/K3 geometry with complete-domain worst cases, mesh/load convergence and independent fields. Original-model N15 results do not qualify this geometry.",
    })
    packages["WP6"]["result"] = "Historical " + packages["WP6"]["result"]
    packages["WP7"].update({
        "result": "Recovered original N15 evidence closes the original K/b/C numerical contract: five panel and five frame float64 residuals satisfy 1e-7. Maxima are 9.983337773558199e-8 and 5.659897926075834e-9. Original full fields/corrections, H records and five ordered SHA-bound saved-action restores remain available; restore maximum relative error is 1.1659935073707673e-8.",
        "path": NUMERIC,
        "remaining": "Preserve the original finite numerical scope and rejected history. Arbitrary-RHS inversion and finite-QP checkpoint/resume are not qualified. Current K1/K3 structural FE belongs to WP5 and requires its own physical inputs; no repeat of already qualified original probes is required by this metadata update.",
    })
    packages["WP8"].update({
        "result": "Historical S4 empty templates retain 121 source and 13 native-payload bindings. R5/R7 H00-H12 handoff preserves sourced-limit, as-built, calibration and sampling requirements. No real G3, G4 or G5 pass is recorded.",
        "path": HANDOFF,
        "remaining": "Freeze actual current candidate/specimen/assembly identity, OEM stack and sourced thresholds, then execute real G3 followed by G4 and G5. Missing, failed, repaired and replaced states remain separate; changed assembly revision does not inherit old passes.",
    })
    packages["WP9"].update({
        "result": "R7 preserves complete native80 and near/far factory archives with member identities, full original failures and separate current scope. The method archive and original N15 qualification retain independent original identities. R8 corrects the stale 2026-10-26 current-entrypoint view while preserving its prior values.",
        "path": f"{R7}/NATIVE_FINITE_WITNESSES.md",
        "remaining": "Retain immutable originals and narrow scientific scope. The unavailable exact historical a11b00f7 commit and its requested branch remain a separate publication issue; this successor does not claim to publish that exact commit.",
    })
    for pr in current["open_research_prs"]:
        if pr["number"] == 35:
            pr["action"] = (
                "Keep PR35 as an independent normalized bearing model. The original N15 "
                "K/b/C five-probe panel/frame and five saved-action H/restore evidence now "
                "qualifies its recorded numerical scope; earlier probe0 rejections remain "
                "historical. Arbitrary RHS and finite-QP checkpoint/resume are not qualified. "
                "The retained gap failures and current K1/K3 structural qualification remain separate."
            )
    active = current["active_followup"]
    active.update({
        "scope": "R7 qualified finite factory/original numerical scopes with continuous geometry, current structure and actual physical inputs still open",
        "state": "R7_two_current_finite_factories_and_original_N15_scope_closed_continuous_and_physical_gates_open",
        "branch": "evidence/full-sprint-20261028-r5",
        "execution_summary": LEDGER,
        "latest_evidence_commit": BASE_COMMIT,
        "latest_evidence_commit_scope": "Exact previously published R7 source/evidence checkpoint read by this R8 metadata synchronization",
        "latest_completed_diagnostic_run_scope": "Historical S4 hosted run ID; subsequent local R7 executions are identified by the current R7 evidence ledger",
        "original_numeric_five_probes_qualified": True,
        "original_frame_five_probes_qualified": True,
        "original_H_five_saved_action_restore_qualified": True,
        "two_current_K1_K3_midtravel_full_factory_poses_clear": True,
        "current_K1_K3_FE_qualified": False,
        "full_motion_qualified": False,
        "complete_G2_qualification": False,
        "K3_full_continuous_or_physical_domain_qualified": False,
        "physical_G3_G4_G5_executed_this_run": False,
        "required_original_specimen_and_selected_revision_facts": 228,
        "qualified_new_specimen_OEM_fact_bindings": 0,
        "all_blockers_closed": False,
    })
    current["current_entrypoint_sync_r8"] = {
        "source_evidence_commit": BASE_COMMIT,
        "functional_source_commit": S4_COMMIT,
        "controlling_R7_ledger": LEDGER,
        "original_numeric_scope": NUMERIC,
        "original_physical_handoff": HANDOFF,
        "validation_record": f"{R8}/R8_CURRENT_ENTRYPOINT_SYNC_RESULT.json",
        "minimum_actual_input_handoff": f"{R8}/REQUIRED_ACTUAL_INPUTS.md",
        "new_CAD_solver_or_physical_execution": False,
        "historical_originals_modified": False,
        "new_release_qualification": False,
    }
    unchanged_fields = [key for key in before if key not in CHANGED_FIELDS]
    if not all(current[key] == before[key] for key in unchanged_fields):
        raise SystemExit("An out-of-scope or historical field was changed")
    if current[history_key]["fields"] != {key: before[key] for key in CHANGED_FIELDS}:
        raise SystemExit("Prior values were not preserved")
    (ROOT / "design/current_product.json").write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
    commands = []
    for extra in ([], ["--check"]):
        command = [sys.executable, "-B", str(ROOT / "tools/sync_current_design.py"), "--root", str(ROOT), *extra]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        commands.append({"argv": command, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise SystemExit(f"Original entrypoint generator failed: {commands[-1]}")
    status = load("status.json")
    for key in ("candidate_go", "fixture_fabrication_go", "manufacturing_go"):
        if current[key] is not False or status[key] is not False:
            raise SystemExit(f"A release flag changed: {key}")
    if status["current_execution_summary"] != LEDGER or status["current_work_packages"] != current["work_packages"]:
        raise SystemExit("Generated current state disagrees")
    immutable_inputs = [path for path in ORIGINAL_BLOBS if path not in (
        "design/current_product.json", "CURRENT_DESIGN.md", "status.json", "docs/RESEARCH_OVERVIEW.md")]
    if not all(identity(ROOT / p) == before_identities[p] for p in immutable_inputs):
        raise SystemExit("A source or original evidence file changed")
    changed_paths = ["design/current_product.json", "CURRENT_DESIGN.md", "status.json", "docs/RESEARCH_OVERVIEW.md"]
    report = {
        "schema": "razr-r8-current-entrypoint-r7-scope-sync-v1",
        "recorded_utc": now,
        "source_evidence_commit": BASE_COMMIT,
        "functional_source_commit": S4_COMMIT,
        "scope": "Actual metadata synchronization and original-generator verification; no new science or physical test",
        "input_identities": before_identities,
        "modified_entrypoint_paths": changed_paths,
        "output_identities": {p: identity(ROOT / p) for p in changed_paths},
        "source_script": identity(Path(__file__).resolve()),
        "actual_generator_commands": commands,
        "original_generator_check_passed": True,
        "original_evidence_and_generator_bytes_unchanged": True,
        "unchanged_original_top_level_field_count": len(unchanged_fields),
        "unchanged_original_top_level_fields": unchanged_fields,
        "prior_changed_field_values_preserved_exactly": True,
        "prior_values_pointer": f"design/current_product.json#/{history_key}/fields",
        "original_finite_native_poses": {name: {
            "slide_mm": pose["slide_mm"],
            "pair_count_per_process": pose["factory_and_reader"]["factory"]["pair_count"],
            "finite_state_clear": pose["finite_state_clear"],
            "separate_process_same_kernel": pose["same_kernel_separate_process_reader"],
        } for name, pose in native["finite_poses"].items()},
        "original_panel_five_residuals": numeric["panel_original_five_residuals"],
        "original_frame_five_residuals": numeric["frame_original_five_residuals"],
        "original_numeric_threshold": numeric["original_float64_residual_threshold"],
        "original_restore_scope": numeric["historical_restore_callback_scope"],
        "required_original_physical_facts": 228,
        "new_qualified_physical_fact_count": 0,
        "new_CAD_solver_or_physical_execution": False,
        "current_K1_K3_FE_qualified": False,
        "full_continuous_G2": False,
        "physical_gate_pass": {"G3": False, "G4": False, "G5": False},
        "release_flags": {k: current[k] for k in ("candidate_go", "fixture_fabrication_go", "manufacturing_go")},
        "all_blockers_closed": False,
    }
    receipt_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"metadata_sync_passed": True, "modified_entrypoints": changed_paths, "report": receipt_path.relative_to(ROOT).as_posix(), "scientific_or_physical_execution": False}))


if __name__ == "__main__":
    main()
