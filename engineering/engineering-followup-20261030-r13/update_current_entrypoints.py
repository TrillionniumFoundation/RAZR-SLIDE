#!/usr/bin/env python3
"""Update current entrypoints without promoting scoped R13 results."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REL = HERE.relative_to(ROOT).as_posix()


def main():
    path = ROOT / "design/current_product.json"
    current = json.loads(path.read_text())
    prior = "prior_current_summary_before_20261030_r13"
    if prior not in current:
        keys = ("last_update_date", "stage_summary", "verification_summary", "hardware_summary",
                "active_followup", "current_execution_summary", "publication_record", "publication_record_scope",
                "work_packages", "current_verified_functional_source")
        current[prior] = {k: copy.deepcopy(current[k]) for k in keys if k in current}
    current["last_update_date"] = "2026-10-30"
    current["updated_utc"] = datetime.now(timezone.utc).isoformat()
    current["current_execution_summary"] = REL + "/R13_COMPLETED_WORK_LEDGER.json"
    current["stage_summary"] = (
        "R13 completes six declared K1/K3 modification windows in BREP and STEP with 24 zero directed material differences, "
        "complete local section/moment partitions and nominal feature connections. The exact-real shared-slide q subsystem "
        "has 17 feasible and eight infeasible merged branch pairs; complete float64 and physical domains remain unproved. "
        "A new explicit B0 AND T trim model gives a per-side conditional bound near 3.1510793974117154e-15 mm3, "
        "while the weaker B0-only 0.9600000000000029 mm3 bound remains unchanged. Actual native model membership, "
        "global realization and compiled error remain open, so continuous G2 is false. R12 original panel/frame numerical "
        "probes and saved H/restore retain their completed scope, with no new R13 solve. Official OEM source leads add "
        "zero complete PDFs, actual specimen originals or qualified bindings. Current structural FE, OEM electrical/stackup "
        "and real G3-G5 remain open. R12 is publicly verified with exact source-tree equivalence. All release flags are false. "
        "The controlling ledger is " + current["current_execution_summary"] + ".")
    current["verification_summary"] = (
        "Historical S4 dd7def6e6a4de9f47dc91ca2ab336fb1a8828560 retains the 36-suite/1654-test full-unit run. "
        "R12 changed qualification-contract source and completed 133 targeted tests, seven prior independent controls "
        "and twelve donor configurations; R13 preserves those source identities without new functional contract changes "
        "or a new full-tree pass. R13 native window/readback diagnostics, complete exact-real local partitions, "
        "q-subsystem branches and conditional trim certificates have separate independent arithmetic checks and actual "
        "negative controls. Same-kernel BREP/STEP agreement is not a native material-set identity proof. "
        "Original numerical products were last executed in R12 and are not recounted as new R13 work. "
        "Original collisions, native prism/Common failures, the old B0-only bound, seed mismatch and physical unknowns remain.")
    suffix = (
        " R13 on 2026-10-30 locates the manufacturer-linked UK repair-document distribution and three indexed EU/family "
        "L2/L3/BOM URLs, retaining distinct service assembly PNs and unproved XT2551-3 applicability. An actual EU BOM "
        "response is HTTP 405 human-verification HTML, not a PDF. New complete OEM PDFs, same-specimen originals, "
        "measurements and selected PN/revision bindings are all zero. Current delta: " + REL + "/real-inputs/CURRENT_INPUT_DELTA.json.")
    if "R13 on 2026-10-30" not in current["hardware_summary"]:
        current["hardware_summary"] += suffix
    current["publication_record"] = REL + "/publication/R12/R12_PUBLICATION_READBACK.json"
    current["publication_record_scope"] = (
        "After fresh explicit user authorization, R12 was published to evidence/full-sprint-20261030-r12 at "
        "ab9ef3270a9a0d0d28f605f7188038db133dbcd8. Both source trees match the original local R12 commits exactly; "
        "API-created commit metadata differs. Actual Git fetch and empty content diffs are recorded. Original local "
        "commit bytes and the historical approval rejection are retained. R13 publication will receive its own actual "
        "post-commit readback; the science seal does not pre-claim that result.")
    updates = {
        "WP0": ("Historical S4 retains its actual 36-suite/1654-test full run. R12 separately changed qualification-contract source and passed 133 targeted tests. R13 extends evidence/analysis without changing those contract sources.",
                "engineering/engineering-followup-20261030-r12/qualification/SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json",
                "Preserve historical full-run and current targeted-source scope. No full-tree or physical pass is inferred for the containing R13 evidence commit."),
        "WP1": ("R13 adds a manufacturer-linked document route, three indexed EU/family service documents and distinct display-service PN leads. Complete PDFs, specimen originals, measurements and new qualified bindings remain zero.",
                REL + "/real-inputs/README.md", "Bind same-specimen 10/7/12 originals and the actually selected PN/revision; source access or family-level service literature does not establish those facts."),
        "WP4": ("R9 full-factory finite witnesses and R12 original native failures remain immutable. R13 proves a tighter per-side 3.1510793974117154e-15 mm3 bound under explicit B0 AND T, accounts for all 169 original positive boxes and retains 157 positive contributions. The B0-only 0.9600000000000029 mm3 bound is unchanged.",
                REL + "/envelope/README_R13_ENVELOPE.md", "Prove actual native B0/T membership, complete global realization and uniform compiled errors, then qualify the actual full coupled motion domain. A tighter conditional model is not native continuous G2."),
        "WP5": ("R13 completes six changed windows in both formats, 24 zero directed differences, 12 exact coordinate models, 404 positive cells, 364 axial strata and 2348 transverse chord strata. Local moments/connections and the exact-real q subsystem give 17 feasible/eight infeasible branch pairs; eight complete STOP/SPRING bodies have 16 format readbacks.",
                REL + "/geometry/README.md", "Establish global minimum walls/weakest sections, all inherited parent CSG, sourced materials/loads/preload/friction/tolerances and current FE. The q subsystem projection does not prove complete float64 or physical allowable domains."),
        "WP7": ("The unchanged R12 original K/b/C readback retains all five panel and five frame residuals below 1e-7, 7770 RHS/saved-H identity checks and five original restore actions. R13 performs no new solve or original probe products.",
                "engineering/engineering-followup-20261030-r12/numerics/evidence/NUMERICAL_SCOPE.json", "Retain the original finite scope and saved full-field/correction identities. Arbitrary RHS, all 7770 fresh K products, legacy whole-seed bitwise replay and full QP resume remain unqualified."),
        "WP8": ("R13 adds nominal geometric section and load-route inputs, with no actual physical tests or new sourced limits. The current declared contract retains 54 gate records and 67 unassigned numerical limits.",
                REL + "/R13_COMPLETED_WORK_LEDGER.json", "Freeze the actual candidate/specimen/as-built, OEM stack, sourced limits, sampling/calibration and version-bound plan; require real G3 pass/review before G4, then G5."),
        "WP9": ("R12 is publicly published at ab9ef3270a9a0d0d28f605f7188038db133dbcd8, with both source trees verified equal to the original local commits by Git fetch. R13 preserves complete native originals, conditional proof ledgers, negative controls and independent reviews.",
                REL + "/publication/R12/R12_PUBLICATION_READBACK.json", "Keep source-tree equivalence distinct from API commit metadata. Record R13 actual publication after its science commit; publishing evidence never advances engineering release."),
        "WP10": ("R12 qualification-chain source and 133 targeted test results remain byte-bound: failure/maintenance retention, same original donor/as-built, assembly and design binding, ordered G3-G4-G5 acquisition/review, and contradiction rejection. R13 does not change or rerun these sources.",
                 "engineering/engineering-followup-20261030-r12/qualification/README.md", "Synthetic software cases do not supply physical passes. Actual assembly, sourced current contracts and the original as-built evidence remain required."),
    }
    for item in current["work_packages"]:
        if item["id"] in updates:
            item["result"], item["path"], item["remaining"] = updates[item["id"]]
    current["active_followup"] = {
        "scope": "R13 complete named modification windows, exact-real q subsystem, explicit conditional trim bound and OEM-source followup",
        "state": "R13_scoped_results_completed_native_and_physical_release_open",
        "branch": "evidence/full-sprint-20261030-r13", "pull_request": None,
        "execution_summary": current["current_execution_summary"],
        "base_public_commit": "ab9ef3270a9a0d0d28f605f7188038db133dbcd8",
        "historical_tested_functional_source_commit": "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560",
        "R12_targeted_tests_retained": 133, "new_R13_qualification_contract_source_change": False,
        "new_full_unit_execution": False, "new_full_factory_execution": False,
        "new_native_modified_window_crops": 12, "new_directed_material_differences": 24,
        "new_complete_STOP_SPRING_format_readbacks": 16,
        "new_conditional_B0_AND_T_bound_qualified_under_stated_model": True,
        "old_B0_only_bound_replaced": False,
        "exact_real_q_subsystem_projection_proved": True,
        "full_float64_or_15D_acceptance_equivalence_proved": False,
        "original_numerical_R12_qualification_retained": True,
        "new_R13_original_numerical_products_executed": False, "new_solver_executed": False,
        "all_7770_K_products_executed": False, "legacy_whole_seed_bitwise_pass": False,
        "native_material_set_identity_proved": False, "native_T_membership_proved": False,
        "complete_global_native_realization_existence_proved": False,
        "uniform_compiled_geometry_error_proved": False,
        "whole_part_minimum_wall_qualified": False, "physical_allowed_domain_proved": False,
        "full_motion_qualified": False, "complete_G2_qualification": False,
        "current_K1_K3_FE_qualified": False, "complete_OEM_electrical_stack_qualified": False,
        "new_complete_OEM_PDFs": 0, "new_physical_observations": 0, "new_actual_specimen_originals": 0,
        "physical_G3_G4_G5_executed_this_run": False, "physical_platform_frozen": False,
        "actual_fabrication_executed": False, "physical_prototype_built": False,
        "physical_phone_verified": False, "powered_phone_verified": False,
        "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
        "all_blockers_closed": False, "R12_publication_verified": True, "new_branch_pushed": False,
        "current_user_publication_authorization": True, "historical_automatic_rejection_retained": True,
        "containing_commit_scope": "Science seal precedes publication; a later actual readback records exact published identity without self-hashing."}
    current["current_entrypoint_sync_r13"] = {
        "controlling_ledger": current["current_execution_summary"], "historical_records_retained": True,
        "new_R13_contract_source_change": False, "new_full_unit_execution": False,
        "new_solver_execution": False, "new_full_factory_execution": False,
        "new_window_and_STOP_SPRING_native_readbacks": True, "new_conditional_trim_arithmetic": True,
        "new_physical_observations": 0, "new_release_qualification": False,
        "validation_record": REL + "/status/R13_CURRENT_ENTRYPOINT_SYNC_RESULT.json"}
    assert all(current[k] is False for k in ("candidate_go", "fixture_fabrication_go", "manufacturing_go", "physical_phone_verified"))
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n")
    runs = []
    for args in (["python3", "-B", "tools/sync_current_design.py"], ["python3", "-B", "tools/sync_current_design.py", "--check"]):
        start = time.monotonic()
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
        runs.append({"argv": args, "returncode": result.returncode, "stdout": result.stdout,
                     "stderr": result.stderr, "elapsed_seconds": time.monotonic() - start})
        assert result.returncode == 0, runs[-1]
    identities = {}
    for name in ("design/current_product.json", "CURRENT_DESIGN.md", "docs/RESEARCH_OVERVIEW.md", "status.json"):
        raw = (ROOT / name).read_bytes()
        identities[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    receipt = {"schema": "razr-r13-current-entrypoint-sync-v1", "runs": runs, "source_and_outputs": identities,
               "science_results_changed_by_metadata_sync": False, "new_unit_tests_claimed": False,
               "publication_scope_at_this_sync": "R12 actual publication verified; R13 science seal not yet published."}
    target = HERE / "status/R13_CURRENT_ENTRYPOINT_SYNC_RESULT.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"entrypoints": len(identities), "sync_check_passed": True, "publication": "R12_verified_R13_pending_at_science_seal"}))


if __name__ == "__main__":
    main()
