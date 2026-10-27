"""Preserve only reviewed, hash-bound engineering ZIPs in an unpublished release.

This performs byte transfers and archive integrity checks, not native CAD/FE or
qualification. It cannot publish a release, delete an asset, overwrite an asset,
change repository settings, or copy unlisted runtime collections.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import http.client
import json
import os
import re
import resource
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = "TrillionniumFoundation/RAZR-SLIDE"
S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
TAG = "evidence/engineering-sprint-20261026"
MARKER = "RAZR-SLIDE-SCIENTIFIC-EVIDENCE-20261026-v1"
TITLE = "2026-10-26 engineering evidence (unpublished; no product release)"
BODY = (MARKER + "\n\nScientific originals for the S4 engineering sprint and PR #39. "
        "Only explicitly reviewed engineering exports are retained. Original arrays, "
        "STEP/BREP materials, histories and engineering projections keep their exact bytes. "
        "Raw runtime collections are excluded. Failed and unresolved results remain failed "
        "or unresolved. candidate_go=false; fixture_fabrication_go=false; manufacturing_go=false. "
        "This draft is evidence preservation, not product publication or qualification.\n")
API = "https://api.github.com/repos/" + REPO
RESERVE = 2 * 1024**3
CHUNK = 1024**2


class ArchiveInvariantError(ValueError):
    """Only fixed, source-controlled gate descriptions can enter the receipt."""
    def __init__(self, gate):
        super().__init__(gate)
        self.gate = gate


def require(value, message):
    if not value:
        raise ArchiveInvariantError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stream_hash(stream):
    h = hashlib.sha256()
    count = 0
    for block in iter(lambda: stream.read(CHUNK), b""):
        count += len(block)
        h.update(block)
    return count, h.hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


class Client:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def headers(self, accept="application/vnd.github+json"):
        return {"Authorization": "Bearer " + self.token, "Accept": accept,
                "X-GitHub-Api-Version": "2026-03-10", "User-Agent": MARKER}

    def json(self, suffix, payload=None):
        require(suffix.startswith("/") and ".." not in suffix, "invalid API suffix")
        data = None if payload is None else json.dumps(payload).encode()
        headers = self.headers()
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(API + suffix, data=data, headers=headers,
                                         method="GET" if payload is None else "POST")
        with self.opener.open(request, timeout=60) as response:
            raw = response.read(8 * 1024**2 + 1)
        require(len(raw) <= 8 * 1024**2, "oversize API response")
        return json.loads(raw)

    def list_all(self, suffix):
        rows = []
        for page in range(1, 11):
            current = self.json(suffix + "?per_page=100&page=" + str(page))
            require(isinstance(current, list), "invalid paged collection")
            rows.extend(current)
            if len(current) < 100:
                return rows
        raise ValueError("collection exceeds declared pagination bound")

    def binary(self, suffix):
        # An authorization header is sent only to api.github.com. Redirected
        # signed transfer URLs are followed without any authorization header.
        if re.fullmatch(r"/actions/artifacts/[0-9]+/zip", suffix):
            accept = "application/vnd.github+json"
        elif re.fullmatch(r"/releases/assets/[0-9]+", suffix):
            accept = "application/octet-stream"
        else:
            raise ArchiveInvariantError("unrecognized binary API route")
        request = urllib.request.Request(API + suffix, headers=self.headers(accept))
        try:
            response = self.opener.open(request, timeout=60)
        except urllib.error.HTTPError as error:
            if error.code not in (301, 302, 303, 307, 308):
                raise
            location = error.headers.get("Location")
            error.close()
            require(isinstance(location, str), "binary redirect lacks location")
            parsed = urllib.parse.urlsplit(location)
            host = parsed.hostname or ""
            require(parsed.scheme == "https" and parsed.username is None and parsed.password is None
                    and (host.endswith(".blob.core.windows.net")
                         or host.endswith(".githubusercontent.com")), "unexpected binary transfer host")
            return self.opener.open(urllib.request.Request(location, headers={"User-Agent": MARKER}), timeout=60)
        require(response.status == 200, "unexpected binary status")
        return response

    def upload(self, release_id, path, content_type):
        require(re.fullmatch(r"[A-Za-z0-9._-]+", path.name), "invalid asset basename")
        suffix = "/repos/" + REPO + "/releases/" + str(release_id) + "/assets?" + urllib.parse.urlencode({"name": path.name})
        connection = http.client.HTTPSConnection("uploads.github.com", timeout=60)
        headers = self.headers()
        headers.update({"Content-Type": content_type, "Content-Length": str(path.stat().st_size)})
        try:
            with path.open("rb") as body:
                connection.request("POST", suffix, body=body, headers=headers)
                response = connection.getresponse()
                raw = response.read(8 * 1024**2 + 1)
            require(response.status == 201 and len(raw) <= 8 * 1024**2, "asset upload did not return bounded success")
            return json.loads(raw)
        finally:
            connection.close()


def verify_v4a_scope(z, entries):
    scope = json.loads(z.read("EXPORT_SCOPE.json"))
    require(scope["schema"] == "razr-V4a-science-export-v1"
            and scope["raw_runtime_exported"] is False
            and scope["private_runtime_durable_preservation_claimed"] is False
            and scope["allowlist_uses_unchanged_producer_exact_label_grammar"] is True
            and scope["unknown_filename_or_link_never_exported"] is True
            and scope["native_producer_and_original_postguards_unchanged"] is True
            and scope["complete_product_qualification"] is False,
            "V4a exact engineering-only and unchanged-postguard scope differs")
    omitted = scope["omitted_unreviewed_JSON"]
    require(isinstance(omitted, list) and len(omitted) == 1
            and set(omitted[0]) == {"file", "sha256", "bytes", "reason"}
            and omitted[0]["file"] == "report.json"
            and omitted[0]["reason"] == "runtime_locator_or_invalid_JSON_not_exported"
            and type(omitted[0]["bytes"]) is int and omitted[0]["bytes"] > 0
            and re.fullmatch(r"[0-9a-f]{64}", omitted[0]["sha256"])
            and "report.json" not in entries,
            "V4a unique original-producer omission or runtime exclusion differs")


def verify_n8_scope(z, manifest, entries):
    """Verify the original N8 storage ledger; numerical qualification is not an archive gate."""
    require(manifest["schema"] == "razr-N8-engineering-allowlist-export-v1"
            and manifest["functional_source_commit"] == S4
            and manifest["raw_runtime_records_exported"] is False
            and manifest["raw_runtime_records_durable"] is False
            and manifest["producer_records_modified"] is False
            and manifest["omitted_runtime_remains_on_ephemeral_runner_only"] is True
            and manifest["original_input_ZIP_included"] is False
            and manifest["original_input_fields_durable_release_asset_id"] is None
            and manifest["original_input_fields_source_artifact_id"] == 12633916809
            and manifest["source_N7_long_term_archive_status_at_registration"] == "pending",
            "N8 exact original-input and excluded-runtime contract differs")
    copied, projections = manifest["copied"], manifest["projections"]
    require(set(entries) == set(copied) | set(projections) | {"EXECUTION_CHECKS.engineering.json"},
            "N8 unaccounted or missing engineering export member")
    require(not set(copied) & set(projections), "N8 original and projection identities overlap")
    require(all(set(item) == {"bytes", "sha256", "original_bytes"} and item["original_bytes"] is True
                and entries.get(name) == {"bytes": item["bytes"], "sha256": item["sha256"]}
                for name, item in copied.items()), "N8 copied original scientific identity differs")
    require(all(set(item) == {"bytes", "sha256", "original_sha256"}
                and entries.get(name) == {"bytes": item["bytes"], "sha256": item["sha256"]}
                and re.fullmatch(r"[0-9a-f]{64}", item["original_sha256"])
                for name, item in projections.items()), "N8 marked projection identity differs")
    require(all(set(item) == {"bytes", "sha256", "exported_original_bytes"}
                and item["exported_original_bytes"] is False
                for item in manifest["original_runtime_record_hashes"]),
            "N8 runtime inventory contains an unlisted or exported field")
    fragments = manifest["scientific_fragments"]
    require(isinstance(fragments, list) and len(fragments) == len(set(fragments))
            and all(name in copied for name in fragments), "N8 scientific fragment inventory differs")
    frozen = json.loads(z.read("source/N8_FROZEN_INPUTS.json"))
    require(frozen["schema"] == "razr-N8-frozen-original-inputs-v1"
            and frozen["functional_source_commit"] == S4
            and frozen["functional_source_tree"] == "cdd9e2c41216201b6cd04dd610d45fde80499045"
            and frozen["source_artifact_id"] == 12633916809
            and frozen["source_ZIP_sha256"] == "2541e06e5c5dcc6a1797e5c85cde410a35056e4e23cae22b2ef9bb7759d85a1c",
            "N8 original source contract identity differs")
    identities = frozen["members"]
    require(len(identities) == 22, "N8 frozen original input inventory differs")
    complete_inputs = ["frozen/" + name for name in identities if "frozen/" + name in copied]
    missing_inputs = ["frozen/" + name for name in identities if "frozen/" + name not in copied]
    require(all(entries[name] == identities[name.removeprefix("frozen/")] for name in complete_inputs),
            "N8 retained frozen original input differs")
    if "frozen/EXPORT_MANIFEST.json" in copied:
        require(entries["frozen/EXPORT_MANIFEST.json"] ==
                {"bytes": frozen["source_manifest_bytes"], "sha256": frozen["source_manifest_sha256"]},
                "N8 original source manifest identity differs")
    p = manifest["scientific_preservation_actual"]
    require(p["selected_complete_inputs_expected"] == 22
            and p["selected_complete_input_identities_verified"] == len(complete_inputs)
            and set(p["missing_selected_complete_inputs"]) == set(missing_inputs)
            and p["all_22_selected_complete_inputs_identity_verified"] ==
                (len(complete_inputs) == 22 and not missing_inputs)
            and p["original_source_manifest_identity_verified"] == ("frozen/EXPORT_MANIFEST.json" in copied)
            and set(p["partial_original_input_files"]) == {name for name in fragments if name.startswith("frozen/")},
            "N8 original input preservation claims differ")
    trial_pattern = re.compile(r"probe-N8/trial-(?:0[1-9]|[1-8][0-9]|9[0-6])/(?:probe-[0-4]-(?:field|residual)|requested-update|actual-update)\.npy(?:\.writing)?$")
    final_pattern = re.compile(r"probe-N8/final/probe-[0-4]-(?:field|residual)\.npy(?:\.writing)?$")
    actual_arrays = {name for name in copied if trial_pattern.fullmatch(name) or final_pattern.fullmatch(name)}
    started = {int(name.split("/")[1].removeprefix("trial-")) for name in actual_arrays
               if name.startswith("probe-N8/trial-")}
    report_name = "probe-N8/N8_REPORT.json"
    producer = json.loads(z.read(report_name)) if report_name in copied else {}
    if producer:
        require(producer["schema"] == "razr-N8-finite-original-five-probe-v1"
                and producer["functional_source_commit"] == S4
                and producer["functional_source_tree"] == "cdd9e2c41216201b6cd04dd610d45fde80499045",
                "N8 original producer identity differs")
    trials = producer.get("trials", [])
    require(isinstance(trials, list) and all(type(t.get("trial_index")) is int and
            1 <= t["trial_index"] <= 96 for t in trials), "N8 producer started candidate index differs")
    require(len({t["trial_index"] for t in trials}) == len(trials), "N8 duplicate producer trial index")
    started.update(t["trial_index"] for t in trials)
    require(p["started_full_candidate_indices"] == sorted(started), "N8 started candidate union differs")
    expected = []
    for index in sorted(started):
        prefix = f"probe-N8/trial-{index:02d}/"
        expected += [prefix + f"probe-0-{kind}.npy" for kind in ("field", "residual")]
        expected += [prefix + "requested-update.npy", prefix + "actual-update.npy"]
    missing = [name for name in expected if name not in copied]
    partial = {name for name in actual_arrays if name.endswith(".writing")}
    trial_by_index = {t["trial_index"]: t for t in trials}
    records, unresolved = [], []
    for index in sorted(started):
        probes = trial_by_index.get(index, {}).get("probes", [])
        for j in range(1, 5):
            rec = probes[j] if len(probes) == 5 and isinstance(probes[j], dict) else {}
            for kind in ("field", "residual"):
                original = f"probe-N7/final/probe-{j}-{kind}.npy"
                relative, identity = "frozen/" + original, identities[original]
                entry = copied.get(relative, {})
                present = rec.get(kind + "_file") == relative and rec.get(kind + "_identity") == identity
                source_checked = all(entry.get(k) == v for k, v in identity.items()) and entry.get("original_bytes") is True
                storage_ok = (rec.get("scientific_storage") == "explicit_frozen_original_field_and_residual_reference"
                              and rec.get("new_native_residual_equals_frozen_original_array_bytes") is True)
                record = {"trial_index": index, "probe_index": j, "kind": kind,
                          "expected_original_file": relative, "expected_original_identity": identity,
                          "explicit_report_reference_matches": present,
                          "referenced_original_bytes_present_and_hash_verified": source_checked,
                          "explicit_actual_native_equality_record_present": storage_ok,
                          "complete_reference": bool(present and source_checked and storage_ok)}
                records.append(record)
                if not record["complete_reference"]:
                    unresolved.append(record)
    finals = [f"probe-N8/final/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
    missing_finals = [name for name in finals if name not in copied]
    duplicates = {name for name in actual_arrays
                  if re.fullmatch(r"probe-N8/trial-[0-9]{2}/probe-[1-4]-(?:field|residual)\.npy(?:\.writing)?", name)}
    require(p["expected_complete_candidate_array_count"] == len(expected)
            and p["complete_candidate_arrays_present"] == len(expected) - len(missing)
            and set(p["missing_complete_candidate_arrays"]) == set(missing)
            and set(p["partial_scientific_candidate_or_final_array_files"]) == partial
            and p["all_started_full_candidate_new_arrays_complete"] ==
                bool(started and not missing and not any(n.startswith("probe-N8/trial-") for n in partial))
            and p["expected_per_candidate_frozen_reference_count"] == len(records)
            and p["complete_per_candidate_frozen_reference_count"] == len(records) - len(unresolved)
            and p["per_candidate_frozen_references"] == records
            and p["missing_or_incomplete_candidate_frozen_references"] == unresolved
            and p["all_started_full_candidates_all5_fields_and_residuals_recoverable"] ==
                bool(started and not missing and not unresolved and not any(n.startswith("probe-N8/trial-") for n in partial))
            and set(p["unexpected_retained_duplicate_candidate_arrays"]) == duplicates
            and p["final_complete_array_count"] == 10 - len(missing_finals)
            and set(p["missing_final_arrays"]) == set(missing_finals)
            and p["all_ten_final_arrays_present"] == (not missing_finals),
            "N8 new arrays, frozen references or truthful partial claims differ")
    existing = p["actual_existing_allowlisted_array_files"]
    require(isinstance(existing, list) and len(existing) == len(set(existing))
            and all(trial_pattern.fullmatch(n) or final_pattern.fullmatch(n) for n in existing)
            and set(p["actual_allowlisted_array_files_copied"]) == actual_arrays
            and p["all_actual_allowlisted_array_bytes_copied_and_hash_verified"] == (set(existing) == actual_arrays),
            "N8 enumerated original array-byte claim differs")
    return {"started_candidates": len(started), "complete_new_arrays": len(expected) - len(missing),
            "complete_frozen_references": len(records) - len(unresolved),
            "unresolved_frozen_references": len(unresolved), "complete_frozen_inputs": len(complete_inputs),
            "complete_final_arrays": 10 - len(missing_finals), "qualification_required": False}


def verify_n7_scope(z, manifest, entries):
    require(manifest["schema"] == "razr-N7-engineering-allowlist-export-v1"
            and manifest["functional_source_commit"] == S4
            and manifest["raw_runtime_records_exported"] is False
            and manifest["raw_runtime_records_durable"] is False
            and manifest["producer_records_modified"] is False
            and manifest["omitted_runtime_remains_on_ephemeral_runner_only"] is True
            and manifest["original_input_ZIP_included"] is False
            and manifest["original_input_fields_durable_release_asset_id"] == 677184053,
            "N7 exact original-input and excluded-runtime contract differs")
    copied = manifest["copied"]
    require(all(item.get("original_bytes") is True and entries.get(name) ==
                {"bytes": item["bytes"], "sha256": item["sha256"]} for name, item in copied.items()),
            "N7 copied scientific identity differs")
    require(all(set(item) == {"bytes", "sha256", "exported_original_bytes"}
                and item["exported_original_bytes"] is False
                for item in manifest["original_runtime_record_hashes"]),
            "N7 runtime inventory contains unlisted or exported fields")
    require(all(entries.get(name) == {"bytes": item["bytes"], "sha256": item["sha256"]}
                and re.fullmatch(r"[0-9a-f]{64}", item["original_sha256"])
                for name, item in manifest["projections"].items()),
            "N7 marked projection identity differs")
    fragments = manifest["scientific_fragments"]
    require(isinstance(fragments, list) and len(fragments) == len(set(fragments))
            and all(name in copied for name in fragments), "N7 scientific fragment identity differs")
    frozen = json.loads(z.read("source/N7_FROZEN_INPUTS.json"))["members"]
    require(len(frozen) == 22, "N7 frozen original input inventory differs")
    complete_inputs = ["frozen/" + name for name in frozen if "frozen/" + name in copied]
    missing_inputs = ["frozen/" + name for name in frozen if "frozen/" + name not in copied]
    require(all(entries[name] == frozen[name.removeprefix("frozen/")] for name in complete_inputs),
            "N7 copied selected original input differs from its frozen identity")
    p = manifest["scientific_preservation_actual"]
    require(isinstance(p, dict) and p["selected_complete_inputs_expected"] == 22
            and p["selected_complete_input_identities_verified"] == len(complete_inputs)
            and set(p["missing_selected_complete_inputs"]) == set(missing_inputs)
            and p["all_22_selected_complete_inputs_identity_verified"] == (len(complete_inputs) == 22 and not missing_inputs)
            and p["original_source_manifest_identity_verified"] == ("frozen/EXPORT_MANIFEST.json" in copied)
            and set(p["partial_original_input_files"]) == {name for name in fragments if name.startswith("frozen/")},
            "N7 complete or missing original-input preservation claims differ")
    started = p["started_full_candidate_indices"]
    require(isinstance(started, list) and all(type(i) is int and 1 <= i <= 32 for i in started)
            and sorted(set(started)) == started, "N7 started-candidate preservation inventory differs")
    trial = re.compile(r"probe-N7/trial-(?:0[1-9]|[12][0-9]|3[0-2])/(?:probe-[0-4]-(?:field|residual)|requested-update|actual-update)\.npy(?:\.writing)?$")
    final = re.compile(r"probe-N7/final/probe-[0-4]-(?:field|residual)\.npy(?:\.writing)?$")
    actual_arrays = {name for name in copied if trial.fullmatch(name) or final.fullmatch(name)}
    require(all(int(name.split("/")[1].removeprefix("trial-")) in started
                for name in actual_arrays if name.startswith("probe-N7/trial-")),
            "N7 existing candidate array omitted from started inventory")
    expected = []
    for i in started:
        prefix = f"probe-N7/trial-{i:02d}/"
        expected += [prefix + f"probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
        expected += [prefix + "requested-update.npy", prefix + "actual-update.npy"]
    missing = [name for name in expected if name not in copied]
    partial_arrays = {name for name in actual_arrays if name.endswith(".writing")}
    finals = [f"probe-N7/final/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
    missing_finals = [name for name in finals if name not in copied]
    require(p["expected_complete_candidate_array_count"] == len(expected)
            and p["complete_candidate_arrays_present"] == len(expected) - len(missing)
            and set(p["missing_complete_candidate_arrays"]) == set(missing)
            and set(p["partial_scientific_candidate_or_final_array_files"]) == partial_arrays
            and p["all_started_full_candidate_arrays_complete"] == bool(started and not missing
                and not any(name.startswith("probe-N7/trial-") for name in partial_arrays))
            and p["final_complete_array_count"] == 10 - len(missing_finals)
            and set(p["missing_final_arrays"]) == set(missing_finals)
            and p["all_ten_final_arrays_present"] == (not missing_finals)
            and set(p["actual_allowlisted_array_files_copied"]) == actual_arrays
            and p["all_actual_allowlisted_array_bytes_copied_and_hash_verified"] ==
                (set(p["actual_existing_allowlisted_array_files"]) == actual_arrays),
            "N7 complete, missing or partial array preservation claims differ")
    # Numerical success is deliberately not an archival gate. Failed complete
    # candidates and truthfully incomplete scientific originals remain valid
    # evidence, with their actual preservation inventory unchanged in the ZIP.


def verify_zip(path, binding):
    with path.open("rb") as stream:
        size, digest = stream_hash(stream)
    require(size == binding["zip_bytes"] and digest == binding["zip_sha256"], "original ZIP byte identity differs")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)), "duplicate ZIP entry")
        for info in infos:
            name = PurePosixPath(info.filename)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in info.filename
                    and not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16), "invalid scientific ZIP member")
        manifest_bytes = z.read(binding["manifest_name"])
        require(sha(manifest_bytes) == binding["manifest_sha256"], "reviewed scientific manifest differs")
        manifest = json.loads(manifest_bytes)
        material_family = {"F1_members": "F1", "K1_members": "K1", "K2_members": "K2", "K3_members": "K3", "K3FULL_members": "K3FULL"}.get(binding["manifest_layout"])
        if binding["manifest_layout"] in ("flat", "V4a_flat"):
            entries = manifest
        elif material_family is not None:
            require(manifest["schema"] == "razr-" + material_family + "-engineering-export-manifest-v1",
                    "frozen geometry engineering manifest schema differs")
            entries = manifest["members"]
        elif binding["manifest_layout"] == "EC1_files":
            entries = manifest["files"]
        else:
            entries = manifest["exported_files"]
        require(isinstance(entries, dict) and len(entries) == binding["manifest_entries"], "manifest entry count differs")
        require(set(names) == set(entries) | {binding["manifest_name"]}, "ZIP contains unlisted or missing material")
        if binding["manifest_layout"] == "exported_files":
            require(manifest["complete_original_runtime_collection_exported"] is False
                    and manifest["raw_runtime_records_durable"] is False
                    and manifest["producer_originals_modified"] is False
                    and manifest["numerical_arrays_and_mathematical_histories_are_original_bytes"] is True,
                    "numeric original-byte or runtime exclusion contract differs")
        if binding["manifest_layout"] == "N6_exported_files":
            require(manifest["schema"] == "razr-N6-engineering-allowlist-export-v1"
                    and manifest["functional_source_commit"] == S4
                    and manifest["raw_runtime_records_exported"] is False
                    and manifest["raw_runtime_records_durable"] is False
                    and manifest["producer_records_modified"] is False
                    and manifest["omitted_runtime_remains_on_ephemeral_runner_only"] is True
                    and manifest["original_input_ZIP_or_field_arrays_duplicated_in_this_export"] is False
                    and manifest["original_input_fields_durable_release_asset_id"] == 677184053,
                    "N6 exact original-input and excluded-runtime contract differs")
            require(all(item.get("original_bytes") is True and entries.get(name) ==
                        {"bytes": item["bytes"], "sha256": item["sha256"]}
                        for name, item in manifest["copied"].items()),
                    "N6 copied scientific identity differs")
            require(all(set(item) == {"bytes", "sha256", "exported_original_bytes"}
                        for item in manifest["original_runtime_record_hashes"]),
                    "N6 runtime inventory contains unlisted fields")
        if binding["manifest_layout"] == "N7_exported_files":
            verify_n7_scope(z, manifest, entries)
        if binding["manifest_layout"] == "N8_exported_files":
            verify_n8_scope(z, manifest, entries)
        if binding["manifest_layout"] == "V4a_flat":
            verify_v4a_scope(z, entries)
        if binding["manifest_layout"] == "EC1_files":
            require(manifest["schema"] == "razr-EC1-engineering-export-v1"
                    and manifest["source_commit"] == S4
                    and manifest["raw_runtime_exported"] is False
                    and manifest["raw_runtime_durable"] is False
                    and manifest["original_producer_records_modified"] is False,
                    "EC1 engineering-only original-byte contract differs")
        if material_family is not None:
            scope = json.loads(z.read("EXPORT_SCOPE.json"))
            require(scope["schema"] == "razr-" + material_family + "-engineering-export-scope-v1"
                    and scope["functional_source_commit"] == S4
                    and scope["raw_producer_reader_reports_modified"] is False
                    and scope["all_copied_original_bytes_verified"] is True
                    and scope["raw_runtime_durable_preservation_claimed"] is False
                    and scope["raw_runtime_location"] == "ephemeral runner only",
                    "frozen geometry original-byte or runtime exclusion contract differs")
            require(all(entries.get(name) == identity for name, identity in scope["copied_originals"].items()),
                    "frozen geometry copied scientific identity differs")
            require(all(set(item) == {"bytes", "category", "sha256"} for item in scope["omitted_runtime_file_hashes"]),
                    "frozen geometry omitted-runtime inventory exposes unlisted fields")
        uncompressed_bytes = 0
        for name, expected in entries.items():
            with z.open(name) as stream:
                count, member_sha = stream_hash(stream)
            require(count == expected["bytes"] and member_sha == expected["sha256"], "scientific member identity differs")
            uncompressed_bytes += count
    return {"original_ZIP_sha256": digest, "original_ZIP_bytes": size,
            "reviewed_manifest_sha256": sha(manifest_bytes), "all_scientific_members_and_CRC_verified": True,
            "verified_manifest_entries": len(entries), "verified_uncompressed_member_bytes": uncompressed_bytes}


def validate_binding(binding):
    require(set(binding) == {"label", "run_id", "head_sha", "artifact_id", "artifact_name", "zip_bytes", "zip_sha256",
                             "manifest_name", "manifest_sha256", "manifest_layout", "manifest_entries", "asset_name"},
            "binding fields differ from archive allowlist")
    require(re.fullmatch(r"[A-Za-z0-9._-]+", binding["asset_name"]) and binding["asset_name"].endswith(".zip"), "invalid scientific asset name")
    require(all(type(binding[k]) is int and binding[k] > 0 for k in ("run_id", "artifact_id", "manifest_entries")), "invalid source identifiers or count")
    require(re.fullmatch(r"[A-Za-z0-9._-]+", binding["manifest_name"]), "invalid manifest basename")
    require(binding["manifest_layout"] in ("flat", "exported_files", "F1_members", "K1_members", "K2_members", "K3_members", "K3FULL_members", "N6_exported_files", "N7_exported_files", "N8_exported_files", "EC1_files", "V4a_flat"), "unsupported reviewed manifest layout")
    require(re.fullmatch(r"[0-9a-f]{40}", binding["head_sha"]), "invalid immutable source identity")
    require(all(re.fullmatch(r"[0-9a-f]{64}", binding[k]) for k in ("zip_sha256", "manifest_sha256")), "invalid SHA binding")
    require(type(binding["zip_bytes"]) is int and 0 < binding["zip_bytes"] <= 768 * 1024**2, "artifact exceeds transfer budget")


def verify_asset(client, asset, size, digest):
    require(asset["state"] == "uploaded" and asset["size"] == size
            and asset["digest"] == "sha256:" + digest, "release asset metadata differs")
    with client.binary("/releases/assets/" + str(asset["id"])) as stream:
        count, readback_digest = stream_hash(stream)
    require(count == size and readback_digest == digest, "complete release asset byte readback differs")
    return {"asset_id": asset["id"], "name": asset["name"], "bytes": size, "sha256": digest,
            "complete_uploaded_asset_bytes_read_back_and_verified": True,
            "browser_download_url": asset["browser_download_url"]}


def require_owned_draft(client, release_id):
    release = client.json("/releases/" + str(release_id))
    require(release["draft"] is True and release["tag_name"] == TAG
            and release["name"] == TITLE and release["body"] == BODY
            and release["target_commitish"] == S4, "owned unpublished draft identity changed")
    return release


def main(args):
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    result = {"schema": "razr-reviewed-scientific-draft-archive-receipt-v1", "completed": False,
              "source_manifest_sha256": sha(args.manifest.read_bytes()), "archive_script_sha256": sha(Path(__file__).read_bytes()),
              "archive_execution_commit": os.environ["GITHUB_SHA"], "archive_workflow_run_id": os.environ["GITHUB_RUN_ID"],
              "native_CAD_or_numeric_execution": False, "raw_runtime_collections_included": False,
              "published_release_created": False, "existing_assets_overwritten_or_deleted": False,
              "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
              "assets": [], "phase": "validating_inputs"}
    def checkpoint():
        result["elapsed_seconds"] = time.monotonic() - started
        (args.output / "ARCHIVE_RECEIPT.json").write_text(json.dumps(result, indent=2) + "\n")
    try:
        require(os.environ.get("GITHUB_REPOSITORY") == REPO, "fixed repository required")
        require(os.environ.get("GITHUB_REF") == "refs/heads/diagnostic/scientific-archive-20261026", "fixed archival branch required")
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        bindings = json.loads(args.manifest.read_text())["artifacts"]
        require(1 <= len(bindings) <= 20, "bounded nonempty scientific selection required")
        for binding in bindings:
            validate_binding(binding)
        require(len({b["artifact_id"] for b in bindings}) == len(bindings)
                and len({b["asset_name"] for b in bindings}) == len(bindings), "duplicate selected artifact")
        require(sum(b["zip_bytes"] for b in bindings) <= 2 * 1024**3, "batch exceeds registered 2GiB transfer payload")
        fs = os.statvfs(args.output)
        require(fs.f_bavail * fs.f_frsize >= RESERVE + sum(b["zip_bytes"] for b in bindings), "ordinary disk reserve unavailable")
        client = Client(os.environ["GITHUB_TOKEN"])
        verified = []
        for binding in bindings:
            result["phase"] = "checking_reviewed_source_" + binding["label"]
            checkpoint()
            meta = client.json("/actions/artifacts/" + str(binding["artifact_id"]))
            require(meta["expired"] is False and meta["name"] == binding["artifact_name"]
                    and meta["size_in_bytes"] == binding["zip_bytes"]
                    and meta["digest"] == "sha256:" + binding["zip_sha256"]
                    and meta["workflow_run"]["id"] == binding["run_id"]
                    and meta["workflow_run"]["head_sha"] == binding["head_sha"], "source artifact metadata differs")
            result["phase"] = "downloading_reviewed_source_" + binding["label"]
            checkpoint()
            path = args.output / binding["asset_name"]
            total = 0
            with client.binary("/actions/artifacts/" + str(binding["artifact_id"]) + "/zip") as source, path.open("xb") as target:
                for block in iter(lambda: source.read(CHUNK), b""):
                    total += len(block)
                    require(total <= binding["zip_bytes"], "source archive exceeded frozen size")
                    fs = os.statvfs(args.output)
                    require(fs.f_bavail * fs.f_frsize >= RESERVE + len(block), "ordinary disk floor reached during transfer")
                    target.write(block)
            result["phase"] = "verifying_original_members_" + binding["label"]
            checkpoint()
            verified.append((binding, path, verify_zip(path, binding)))
        result["phase"] = "all_selected_originals_verified_before_external_archive_write"
        checkpoint()
        releases = [r for r in client.list_all("/releases") if r["tag_name"] == TAG]
        require(len(releases) <= 1, "ambiguous archive release")
        if releases:
            release = releases[0]
            require(release["draft"] is True and release["name"] == TITLE and release["body"] == BODY
                    and release["target_commitish"] == S4, "existing release is not this owned draft archive")
        else:
            release = client.json("/releases", {"tag_name": TAG, "target_commitish": S4, "name": TITLE,
                "body": BODY, "draft": True, "prerelease": True, "make_latest": "false", "generate_release_notes": False})
        require(release["draft"] is True, "archive must remain unpublished")
        result["release"] = {k: release[k] for k in ("id", "html_url", "tag_name", "draft", "target_commitish")}
        assets = client.list_all("/releases/" + str(release["id"]) + "/assets")
        by_name = {a["name"]: a for a in assets}
        require(len(by_name) == len(assets), "duplicate existing release asset name")
        for binding, path, verification in verified:
            result["phase"] = "archiving_" + binding["label"]
            checkpoint()
            require_owned_draft(client, release["id"])
            asset = by_name.get(path.name)
            reused = asset is not None
            if asset is None:
                asset = client.upload(release["id"], path, "application/zip")
            require(asset["name"] == path.name, "uploaded asset basename differs")
            receipt = verify_asset(client, asset, binding["zip_bytes"], binding["zip_sha256"])
            result["assets"].append({"source_artifact": binding, "source_verification": verification,
                                     "release_asset": receipt, "existing_identical_asset_reused": reused})
            checkpoint()
        require_owned_draft(client, release["id"])
        result["completed"] = True
        result["phase"] = "complete_all_scientific_assets_and_full_byte_readbacks"
        checkpoint()
        index = args.output / ("ARCHIVE_INDEX-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"] + ".json")
        index.write_bytes((args.output / "ARCHIVE_RECEIPT.json").read_bytes())
        require_owned_draft(client, release["id"])
        meta = client.upload(release["id"], index, "application/json")
        result["archive_index_asset"] = verify_asset(client, meta, index.stat().st_size, sha(index.read_bytes()))
        require_owned_draft(client, release["id"])
        checkpoint()
        print(json.dumps({"completed": True, "draft_release_id": release["id"], "archive_count": len(result["assets"]),
                          "all_asset_bytes_retrieved_and_verified": True, "published": False}))
        return 0
    except BaseException as error:
        result["completed"] = False
        result["error_type"] = type(error).__name__
        if isinstance(error, ArchiveInvariantError):
            result["failed_source_controlled_gate"] = error.gate
        if isinstance(error, urllib.error.HTTPError):
            result["HTTP_status"] = error.code
        # No raw exception text, request headers, API bodies or signed URLs.
        checkpoint()
        print(json.dumps({"completed": False, "phase": result["phase"], "error_type": result["error_type"],
                          "HTTP_status": result.get("HTTP_status"), "archived_before_failure": len(result["assets"])}))
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
