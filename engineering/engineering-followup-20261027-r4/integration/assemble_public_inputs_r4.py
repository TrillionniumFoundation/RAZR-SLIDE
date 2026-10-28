#!/usr/bin/env python3
"""Prepare a scoped public evidence projection without changing science originals."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


def identity(path: Path) -> dict:
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    dest = root / "razr-current/engineering/engineering-followup-20261027-r4"
    dest.mkdir(parents=True, exist_ok=True)
    mappings = []

    def copy(source: Path, relative: str, *, scrub_workspace: bool = False) -> None:
        data = source.read_bytes()
        compressed_json = source.suffix == ".gz"
        text = (gzip.decompress(data) if compressed_json else data).decode("utf-8")
        if compressed_json:
            json.loads(text)
            assert not scrub_workspace, "A frozen gzip projection must be copied byte-identically."
        if scrub_workspace:
            text = text.replace(str(root), "{WORKSPACE}")
        assert not re.search(r"\blibfile_[A-Za-z0-9]{8,}|\bfile_000000[0-9A-Za-z]{8,}", text), source
        assert str(root) not in text, source
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if compressed_json:
            target.write_bytes(data)
        else:
            target.write_text(text)
        mappings.append({"public_path": relative, "original_relative": str(source.relative_to(root)), "original_identity": identity(source), "public_identity": identity(target), "byte_identical_to_original": target.read_bytes() == data, "projection_change": "workspace-prefix token only" if target.read_bytes() != data else None})

    for source in sorted((root / "r4-sources/public").iterdir()):
        if source.is_file():
            copy(source, "real-sources/" + source.name)
    copy(root / "r4-deliverables/R4_RUNTIME_EXECUTED_SUMMARY.json", "runtime/R4_RUNTIME_EXECUTED_SUMMARY.json")
    copy(root / "r4-runtime/independent/README_R4_INDEPENDENT_REVIEW.md", "runtime/README_R4_INDEPENDENT_REVIEW.md")
    copy(root / "r4-runtime/independent/actual-readback/R4_RUNTIME_INDEPENDENT_REVIEW.json", "runtime/R4_RUNTIME_INDEPENDENT_REVIEW_PUBLIC.json", scrub_workspace=True)
    for source in sorted((root / "r4-runtime").glob("*.py")):
        copy(source, "runtime/source/" + source.name)
    copy(root / "r4-runtime/independent/audit_recovered_runtime_r4.py", "runtime/source/audit_recovered_runtime_r4.py")
    copy(Path(__file__).resolve(), "integration/assemble_public_inputs_r4.py")
    for category in ["native", "envelope"]:
        public = root / ("r4-" + category) / ("public-final-v2" if category == "envelope" else "public")
        if public.is_dir():
            for source in sorted(public.rglob("*")):
                if source.is_file():
                    copy(source, category + "/" + str(source.relative_to(public)))

    catalog_path = root / "recovered-science/RAZR-SLIDE_R3_scientific_files_20261027.json"
    catalog = json.loads(catalog_path.read_text())
    recovery = json.loads((root / "r4-recovery/R4_SCIENTIFIC_INPUT_RECOVERY.json").read_text())
    archive_rows = []
    recovered = {p.name for p in (root / "recovered-science").iterdir() if p.is_file()}
    for row in catalog["files"]:
        archive_rows.append({key: row[key] for key in ["file_name", "bytes", "sha256"]} | {"full_archive_restored_and_rehashed_in_R4": row["file_name"] in recovered})
    original_index = {"schema": "razr-r4-original-scientific-archive-identities-v1", "source_directory_identity": identity(catalog_path), "archive_count": len(archive_rows), "actually_restored_in_R4_count": sum(r["full_archive_restored_and_rehashed_in_R4"] for r in archive_rows), "input_restoration_record_identity": identity(root / "r4-recovery/R4_SCIENTIFIC_INPUT_RECOVERY.json"), "restoration_executed": recovery["all_selected_restored"], "old_scientific_jobs_reexecuted_by_restoration": False, "old_git_objects_reconstructed": False, "archives": archive_rows}
    (dest / "ORIGINAL_SCIENTIFIC_ARCHIVE_IDENTITIES.json").write_text(json.dumps(original_index, ensure_ascii=False, indent=2) + "\n")

    git_status = {
        "schema": "razr-r4-available-git-source-and-missing-requested-object-v1",
        "repository": "TrillionniumFoundation/RAZR-SLIDE",
        "requested_original_commit": "a11b00f71231ef3516d2a79c73fa441c375ac755",
        "requested_original_branch": "evidence/full-sprint-20261027-n13-l6",
        "original_publication_authorized": True,
        "current_original_commit_lookup_http_status": 422,
        "current_original_raw_git_object_lookup_http_status": 404,
        "current_original_branch_search_matches": 0,
        "current_local_original_git_object_available": False,
        "original_exact_commit_publication_completed": False,
        "available_verified_public_source_commit": "345af733716a21bf002bf1e16d7ed46594fa83a7",
        "available_verified_public_source_tree": "688bed1e29286260f18b62f4b0e26c50a53a8ed5",
        "available_public_source_commit_raw_SHA1_recomputed": True,
        "available_public_source_tree_entry_count": 28755,
        "new_R4_projection_claimed_as_descendant_of_missing_R3_commits": False,
        "requested_original_commit_substituted_by_new_commit": False,
        "new_projection_branch_intent": "evidence/full-sprint-20261027-r4",
        "required_for_exact_original_publication": "Recover the exact original Git objects/bundle and an authenticated Git transport capable of transferring those objects.",
        "bounded_scientific_archive_recovery_is_not_git_history_recovery": True,
    }
    (dest / "GIT_SOURCE_AND_PUBLICATION_BOUNDARY.json").write_text(json.dumps(git_status, ensure_ascii=False, indent=2) + "\n")
    mapping = {"schema": "razr-r4-public-projection-source-map-v1", "files": mappings, "raw_scientific_archives_replaceable_by_this_projection": False, "third_party_complete_documents_published": False, "private_device_endpoint_or_library_identifiers_published": False}
    (dest / "PUBLIC_PROJECTION_SOURCE_MAP.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"public_directory": str(dest), "mapped_files": len(mappings), "original_archive_identity_count": len(archive_rows), "actual_R4_restored_count": original_index["actually_restored_in_R4_count"]}))


if __name__ == "__main__":
    main()
