#!/usr/bin/env python3
"""Bind actual R4 source reads to the unchanged per-fact intake contract."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--prior-current-state", type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent
    out = root / "public"
    original = read(args.contract)
    prior = read(args.prior_current_state)
    require(len(original["requirements"]) == 228, "Original contract requirement count changed")
    scope_counts = dict(Counter(r["scope"] for r in original["requirements"]))
    category_counts = dict(Counter(r["category"] for r in original["requirements"]))
    require(scope_counts == {"same_specimen": 207, "selected_part_revision": 21}, "Unexpected original scopes")
    require(category_counts == {"identity": 10, "part": 77, "interface": 120, "supplier": 21}, "Unexpected original categories")
    require(prior["actual_new_physical_measurements"] == 0, "Prior state is not the recorded R3 state")

    main_capture = read(root / "R4_OFFICIAL_MODEL_PAGE_ACTUAL_CAPTURE.json")
    alternate_guide = read(root / "R4_OFFICIAL_MODEL_GUIDE_LINK_CAPTURE.json")
    exact_guide = read(root / "R4_OFFICIAL_LITERAL_GUIDE_ANCHOR_CAPTURE.json")
    captures = main_capture["records"] + [alternate_guide["record"], exact_guide["record"]]
    pages = {}
    for record in captures:
        require(record["complete_html_captured"] and record["http_status"] == 200, "A declared HTML input was not read")
        name = record["id"]
        html = root / "private-inputs" / "official-html" / (name + ".html")
        visible = root / "private-inputs" / "official-html" / (name + ".visible.json")
        require(identity(html) == {"bytes": record["received_bytes"], "sha256": record["received_sha256"]}, "HTML identity differs: " + name)
        require(identity(visible) == record["visible_extraction_identity"], "Visible extraction identity differs: " + name)
        pages[name] = read(visible)

    def has_link(source, target):
        return any(r["href"] == target for r in pages[source]["links"])

    product = pages["product_1047"]
    require("XT2551-3" in product["visible_text_segments"], "Exact product model token absent")
    require("Motorola" in product["visible_text_segments"], "Manufacturer product category absent")
    require(has_link("product_1047", pages["downloads_1047"]["effective_url"]), "Product to download directory link missing")
    for name in ["quick_guide_1762", "user_guides_1766"]:
        require(has_link("downloads_1047", pages[name]["effective_url"]), "Download to detail link missing")
        require("XT2551-3" in " ".join(pages[name]["visible_text_segments"]), "Detail does not explicitly name model")
    require(has_link("product_1047", pages["guides_1047_exact_anchor"]["effective_url"]), "Literal product to guide link missing")
    require(has_link("guides_1047_exact_anchor", pages["usb_baseline_82351"]["effective_url"]), "Guide to USB article link missing")
    require(identity(root / "private-inputs/official-html/guides_1047.html") == identity(root / "private-inputs/official-html/guides_1047_exact_anchor.html"), "Actual guide query-order payload equality failed")

    public_inputs = []
    for record in captures:
        public_inputs.append({k: record[k] for k in ["id", "requested_url", "effective_url", "started_utc", "http_status", "content_type", "received_bytes", "received_sha256", "visible_extraction_identity", "exact_model_token_present", "outcome"]})
    write(out / "R4_OFFICIAL_MODEL_SOURCE_IDENTITIES.json", {
        "schema": "razr-r4-official-model-source-identities-v1",
        "derived_projection_not_raw_HTTP_response": True,
        "actual_capture_count": len(captures),
        "unique_HTML_payloads": len({r["received_sha256"] for r in captures}),
        "sources": public_inputs,
        "full_third_party_HTML_or_PDF_in_public_projection": False,
        "actual_input_bytes_rechecked": True,
        "literal_link_chain_rechecked": True,
        "differently_ordered_guide_query_responses_actually_same_bytes": True,
        "same_specimen_qualification_granted": False,
    })

    directory = " ".join(pages["downloads_1047"]["visible_text_segments"])
    declarations = []
    for name, file_id, listing_date, detail_date, file_format, size_text in [
        ("quick_guide_1762", "1762", "2025.07.23", "2025-04-25", "pdf", "2.13 MB"),
        ("user_guides_1766", "1766", "2025.08.22", "2025-05-08", "rar", "11.28 MB"),
    ]:
        text = " ".join(pages[name]["visible_text_segments"])
        require(listing_date in directory and detail_date in text and size_text in text, "Declared document metadata differs")
        download_url = "https://m.lenovocare.com.cn/Handler/Download.ashx?fileid=" + file_id
        require(has_link(name, download_url), "Actual public download anchor missing")
        declarations.append({"source_id": name, "explicit_model": "XT2551-3",
                             "declared_format": file_format, "declared_size_text": size_text,
                             "listing_date_text": listing_date, "detail_date_text": detail_date,
                             "dates_disagree": True, "revision_selected_from_larger_date": False,
                             "actual_internal_document_revision": None,
                             "public_download_url": download_url,
                             "complete_document_acquired": False,
                             "actual_full_document_bytes": None, "actual_full_document_sha256": None})

    manual_reads = read(root / "R4_PUBLIC_MANUAL_ACTUAL_READS.json")["results"]
    cn_reads = read(root / "R4_LENOVO_CN_DOCUMENT_ACTUAL_READS.json")["results"]
    cn_retry = read(root / "R4_LENOVO_CN_HTTPS_RETRY.json")["results"]
    require(len(manual_reads + cn_reads + cn_retry) == 6, "Unexpected recorded document-read count")
    require(all(not r.get("complete_pdf_acquired", False) and not r.get("complete_expected_document_acquired", False) for r in manual_reads + cn_reads + cn_retry), "Document acquisition state changed")
    require(all(r.get("http_status") == 503 for r in cn_reads + cn_retry), "Official body read result changed")
    write(out / "R4_DOCUMENT_BODY_READ_OBSERVATIONS.json", {
        "schema": "razr-r4-document-body-observation-public-v1",
        "derived_projection_not_raw_HTTP_response": True,
        "attempts": [{k: r[k] for k in ["name", "requested_url", "http_status", "effective_url", "outcome", "received_bytes", "received_sha256", "seconds"] if k in r}
                     for r in manual_reads + cn_reads + cn_retry],
        "complete_PDFs_or_RARs_acquired": 0,
        "full_PDF_page_inspection_executed": False,
        "document_body_absence_at_origin_inferred": False,
        "same_specimen_qualification_inferred": False,
    })

    usb_text = " ".join(pages["usb_baseline_82351"]["visible_text_segments"])
    require(all(s in usb_text for s in ["USB", "文件传输", "内部共享存储空间"]), "USB procedure source text incomplete")
    usb = {
        "schema": "razr-r4-G4-usb-source-candidate-v1",
        "state": "MODEL_LINKED_PROCEDURE_SOURCE_CANDIDATE_ONLY",
        "source_url": pages["usb_baseline_82351"]["effective_url"],
        "source_identity": next(r for r in public_inputs if r["id"] == "usb_baseline_82351"),
        "source_chain": [product["effective_url"], pages["guides_1047_exact_anchor"]["effective_url"], pages["usb_baseline_82351"]["effective_url"]],
        "article_itself_explicitly_names_XT2551_3": False,
        "article_linked_from_exact_model_service_index": True,
        "paraphrased_source_procedure": ["Connect the unmodified phone to a computer with a USB cable.", "Select the phone USB file-transfer mode.", "Check that the computer exposes the phone shared storage for ordinary file access."],
        "candidate_contract_location": "G4-plan.function_protocols.usb.source",
        "candidate_contract_frozen_or_approved": False,
        "OEM_protocol_certifies_modified_slider": False,
        "USB_version_or_rate_from_this_source": None,
        "physical_terminal_or_pin_map_from_this_source": None,
        "original_device_function_baseline_actually_measured": False,
        "actual_file_transfer_performed": False,
        "new_G4_pass": False,
        "remaining_prerequisites": ["same-specimen identity and assembly revision", "real G3 prerequisite", "selected OEM interconnect and pin map", "sourced numerical limits, sampling, calibration and uncertainty", "candidate-bound approved protocol", "raw original-battery and original-charging observations in all required phases"],
    }
    write(out / "R4_G4_USB_PROTOCOL_SOURCE_CANDIDATE.json", usb)

    requirements = []
    for row in original["requirements"]:
        requirements.append({**row, "state": "UNBOUND", "qualifying_new_originals": [],
                             "new_model_pages_used_as_qualifying_originals": False,
                             "remaining": ("Same-specimen original observations, traceable operator/metrology and applicable part identity are still absent." if row["scope"] == "same_specimen" else "No selected-part PN/revision-bound supplier drawing, stack, process and rating evidence was obtained.")})
    coverage = {"schema": "razr-r4-actual-source-to-original-requirement-coverage-v1",
                "is_new_empty_intake_template": False,
                "unchanged_original_contract_identity": identity(args.contract),
                "requirements_count": len(requirements), "original_scope_counts": scope_counts,
                "original_category_counts": category_counts,
                "new_same_specimen_identity_fields_bound": 0, "new_actual_part_roles_bound": 0,
                "new_actual_OEM_interfaces_bound": 0, "new_selected_part_revision_requirements_bound": 0,
                "requirements": requirements,
                "source_admission_policy": "An exact model-family page or consumer method source cannot supply same-specimen or selected-part-revision observations.",
                "new_physical_measurements": 0,
                "original_R3_contract_or_V2_validator_modified": False}
    write(out / "R4_ORIGINAL_228_REQUIREMENT_COVERAGE.json", coverage)

    device = read(root / "DEVICE_CONNECTIVITY_R4.json")
    require(device["attempt_count"] == 1 and device["transport_application_bytes_sent"] == 0 and device["device_commands_executed"] == 0 and device["new_physical_measurements"] == 0, "Device observation scope changed")
    require(not device["connection_opened"] and device["errno"] == 111, "Recorded service outcome changed")
    write(out / "DEVICE_CONNECTIVITY_R4.json", device)
    library = read(root / "R4_LIBRARY_UPLOADED_LOOKUP_ACTUAL_RESULTS.json")
    require(library["matched_originals"] == 0 and len(library["actual_results"]) == 2, "Bounded source lookup changed")
    write(out / "R4_BOUNDED_UPLOADED_SOURCE_LOOKUP.json", {
        "schema": "razr-r4-bounded-uploaded-source-lookup-public-v1",
        "actual_record_identity": identity(root / "R4_LIBRARY_UPLOADED_LOOKUP_ACTUAL_RESULTS.json"),
        "queries": library["queries"], "filters": library["filters"],
        "top_k_per_call": library["top_k_per_call"], "actual_calls": 2,
        "matching_originals": 0, "proof_of_global_absence": False,
        "same_specimen_qualification_granted": False})

    summary = {
        "schema": "razr-r4-real-source-executed-summary-v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "generator_identity": identity(Path(__file__)),
        "prior_R3_current_state_identity": identity(args.prior_current_state),
        "original_contract_identity": identity(args.contract),
        "new_exact_manufacturer_model_page_binding": {"model": "XT2551-3", "market_name": "moto razr 60 Ultra", "manufacturer_category": "Motorola", "source_id": "product_1047", "model_page_identity_and_literal_navigation_verified": True, "same_specimen_region_inferred": False},
        "new_exact_model_consumer_document_declarations": declarations,
        "same_variant_controlled_service_manual_or_schematic_obtained": False,
        "prior_NA_XT2551_1_2_engineering_document_applicability_to_XT2551_3_established": False,
        "official_HTML_capture_entries": len(captures),
        "distinct_official_HTML_payloads": len({r["received_sha256"] for r in captures}),
        "complete_new_PDFs_or_RARs_acquired": 0,
        "actual_document_read_attempts": 6,
        "actual_device_service_readonly_observations": 1,
        "current_device_connection_opened": False,
        "current_adb_executable_available": device["adb_executable_available"],
        "new_actual_device_commands": 0,
        "new_actual_physical_measurements": 0,
        "original_required_identity_part_interface_counts": original["counts"],
        "original_per_fact_requirements": len(requirements),
        "new_qualified_requirements": 0,
        "new_G4_USB_source_candidate": "R4_G4_USB_PROTOCOL_SOURCE_CANDIDATE.json",
        "original_V2_37_controls_rerun": False,
        "original_contract_or_validator_changed": False,
        "same_specimen_10_7_12_complete": False,
        "current_FE_qualified": False,
        "OEM_electrical_and_finished_stack_qualified": False,
        "G3_pass": False, "G4_pass": False, "G5_pass": False,
        "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
        "all_blockers_closed": False,
        "no_forms_messages_purchase_login_or_device_command": True,
        "full_third_party_documents_in_public_projection": False,
    }
    write(out / "R4_SOURCE_EXECUTED_SUMMARY.json", summary)
    print(json.dumps({"public_summary_identity": identity(out / "R4_SOURCE_EXECUTED_SUMMARY.json"), "official_HTML_captures": len(captures), "source_requirement_rows": len(requirements), "qualified_original_requirements": 0, "all_blockers_closed": False}))


if __name__ == "__main__":
    main()
