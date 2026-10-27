"""Small integrity and credential-boundary controls; no network or mutation."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import urllib.error
import zipfile

SPEC = importlib.util.spec_from_file_location("archive_impl", Path(__file__).with_name("archive_scientific_evidence.py"))
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class IntegrityControls(unittest.TestCase):
    def make_f1(self, directory, runtime_claim=False, extra_runtime_field=False, family="F1"):
        content = b"original STEP engineering material\n"
        identity = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        omitted = {"bytes": 2, "category": "runtime_receipt", "sha256": "0" * 64}
        if extra_runtime_field:
            omitted["path"] = "unlisted-runtime-locator"
        scope = {"schema": "razr-" + family + "-engineering-export-scope-v1", "functional_source_commit": MOD.S4,
                 "raw_producer_reader_reports_modified": False, "all_copied_original_bytes_verified": True,
                 "raw_runtime_durable_preservation_claimed": runtime_claim, "raw_runtime_location": "ephemeral runner only",
                 "copied_originals": {"material.step": identity}, "omitted_runtime_file_hashes": [omitted]}
        scope_bytes = json.dumps(scope).encode()
        manifest = json.dumps({"schema": "razr-" + family + "-engineering-export-manifest-v1", "members": {
            "material.step": identity, "EXPORT_SCOPE.json": {"bytes": len(scope_bytes),
            "sha256": hashlib.sha256(scope_bytes).hexdigest()}}}).encode()
        path = Path(directory) / "F1.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("material.step", content)
            z.writestr("EXPORT_SCOPE.json", scope_bytes)
            z.writestr("ENGINEERING_MANIFEST.json", manifest)
        return path, {"zip_bytes": path.stat().st_size, "zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "manifest_name": "ENGINEERING_MANIFEST.json", "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
                      "manifest_layout": family + "_members", "manifest_entries": 2}

    def test_k1_exact_original_scientific_schema(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make_f1(d, family="K1")
            self.assertTrue(MOD.verify_zip(p, b)["all_scientific_members_and_CRC_verified"])

    def test_k1_not_relabelled_as_f1(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make_f1(d, family="K1")
            b["manifest_layout"] = "F1_members"
            with self.assertRaises(MOD.ArchiveInvariantError):
                MOD.verify_zip(p, b)

    def test_f1_original_science_and_exclusion_contract(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make_f1(d)
            self.assertTrue(MOD.verify_zip(p, b)["all_scientific_members_and_CRC_verified"])

    def test_f1_untrue_runtime_durability_claim_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make_f1(d, runtime_claim=True)
            with self.assertRaises(MOD.ArchiveInvariantError):
                MOD.verify_zip(p, b)

    def test_f1_unlisted_runtime_inventory_field_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make_f1(d, extra_runtime_field=True)
            with self.assertRaises(MOD.ArchiveInvariantError):
                MOD.verify_zip(p, b)

    def test_k2_k3_exact_family_and_cross_family_rejection(self):
        for family in ("K2", "K3"):
            with self.subTest(family=family), tempfile.TemporaryDirectory() as d:
                p, b = self.make_f1(d, family=family)
                self.assertTrue(MOD.verify_zip(p, b)["all_scientific_members_and_CRC_verified"])
                b["manifest_layout"] = "K1_members"
                with self.assertRaises(MOD.ArchiveInvariantError):
                    MOD.verify_zip(p, b)

    def test_k3full_exact_family_and_cross_family_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            p, binding = self.make_f1(d, family="K3FULL")
            self.assertTrue(MOD.verify_zip(p, binding)["all_scientific_members_and_CRC_verified"])
            binding["manifest_layout"] = "K3_members"
            with self.assertRaises(MOD.ArchiveInvariantError):
                MOD.verify_zip(p, binding)
        with tempfile.TemporaryDirectory() as d:
            p, binding = self.make_f1(d, family="K3")
            binding["manifest_layout"] = "K3FULL_members"
            with self.assertRaises(MOD.ArchiveInvariantError):
                MOD.verify_zip(p, binding)

    def test_k3full_existing_runtime_exclusion_gates_remain(self):
        for claim, extra_field in ((True, False), (False, True)):
            with self.subTest(claim=claim, extra_field=extra_field), tempfile.TemporaryDirectory() as d:
                p, binding = self.make_f1(d, family="K3FULL", runtime_claim=claim,
                                          extra_runtime_field=extra_field)
                with self.assertRaises(MOD.ArchiveInvariantError):
                    MOD.verify_zip(p, binding)

    def pack_typed_science(self, directory, contents, manifest, layout):
        name = "MANIFEST.json" if layout == "V4a_flat" else "EXPORT_MANIFEST.json"
        raw = json.dumps(manifest).encode()
        path = Path(directory) / "new-typed.zip"
        with zipfile.ZipFile(path, "w") as z:
            for member, data in contents.items():
                z.writestr(member, data)
            z.writestr(name, raw)
        entries = manifest if layout == "V4a_flat" else manifest["exported_files"]
        return path, {"zip_bytes": path.stat().st_size, "zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "manifest_name": name, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "manifest_layout": layout, "manifest_entries": len(entries)}

    def make_v4a(self, directory, mutation=None):
        scope = {"schema": "razr-V4a-science-export-v1", "raw_runtime_exported": False,
            "private_runtime_durable_preservation_claimed": False,
            "omitted_unreviewed_JSON": [{"file": "report.json", "sha256": "1" * 64, "bytes": 123,
                "reason": "runtime_locator_or_invalid_JSON_not_exported"}],
            "allowlist_uses_unchanged_producer_exact_label_grammar": True,
            "unknown_filename_or_link_never_exported": True,
            "native_producer_and_original_postguards_unchanged": True,
            "complete_product_qualification": False}
        if mutation:
            mutation(scope)
        contents = {"call-000001-material.brep": b"retained synthetic geometry\n",
                    "EXPORT_SCOPE.json": json.dumps(scope).encode()}
        manifest = {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    for name, data in contents.items()}
        return self.pack_typed_science(directory, contents, manifest, "V4a_flat")

    def test_v4a_exact_scope_and_original_producer_omission(self):
        with tempfile.TemporaryDirectory() as d:
            p, binding = self.make_v4a(d)
            self.assertTrue(MOD.verify_zip(p, binding)["all_scientific_members_and_CRC_verified"])

    def test_v4a_unknown_schema_runtime_fields_and_changed_postguard_rejected(self):
        mutations = [lambda s: s.update(schema="unreviewed-schema"),
                     lambda s: s.update(raw_runtime_exported=True),
                     lambda s: s.update(native_producer_and_original_postguards_unchanged=False),
                     lambda s: s["omitted_unreviewed_JSON"][0].update(path="private-runtime-locator")]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as d:
                p, binding = self.make_v4a(d, mutation)
                with self.assertRaises(MOD.ArchiveInvariantError):
                    MOD.verify_zip(p, binding)

    def make_n7(self, directory, partial=False, mutation=None):
        contents = {}
        def identity(data):
            return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        frozen = {f"input-{i:02d}.npy": identity(f"synthetic original {i}".encode()) for i in range(22)}
        contents["source/N7_FROZEN_INPUTS.json"] = json.dumps({"members": frozen}).encode()
        fragments = []
        for i, name in enumerate(frozen):
            suffix = ".writing" if partial and i == 0 else ""
            full = "frozen/" + name + suffix
            contents[full] = f"synthetic original {i}".encode()
            if suffix:
                fragments.append(full)
        candidates = [f"probe-N7/trial-01/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
        candidates += ["probe-N7/trial-01/requested-update.npy", "probe-N7/trial-01/actual-update.npy"]
        finals = [f"probe-N7/final/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
        for i, name in enumerate(candidates + finals):
            suffix = ".writing" if partial and name in (candidates[0], finals[0]) else ""
            contents[name + suffix] = f"synthetic array {i}".encode()
            if suffix:
                fragments.append(name + suffix)
        # A true numerical rejection is valid evidence, including when every
        # field is complete. This is not made a successful-solve archive gate.
        contents["probe-N7/N7_REPORT.json"] = b'{"original_five_passed":false}'
        copied = {name: {**identity(data), "original_bytes": True} for name, data in contents.items()}
        arrays = sorted(name for name in contents if name.endswith((".npy", ".npy.writing")) and name.startswith("probe-N7/"))
        missing_inputs = ["frozen/input-00.npy"] if partial else []
        missing_candidates = [candidates[0]] if partial else []
        missing_finals = [finals[0]] if partial else []
        preservation = {"selected_complete_inputs_expected": 22,
            "selected_complete_input_identities_verified": 22 - int(partial),
            "missing_selected_complete_inputs": missing_inputs,
            "partial_original_input_files": [name for name in fragments if name.startswith("frozen/")],
            "all_22_selected_complete_inputs_identity_verified": not partial,
            "original_source_manifest_identity_verified": False, "started_full_candidate_indices": [1],
            "expected_complete_candidate_array_count": 12, "complete_candidate_arrays_present": 12 - int(partial),
            "missing_complete_candidate_arrays": missing_candidates,
            "partial_scientific_candidate_or_final_array_files": [name for name in arrays if name.endswith(".writing")],
            "all_started_full_candidate_arrays_complete": not partial, "final_complete_array_count": 10 - int(partial),
            "missing_final_arrays": missing_finals, "all_ten_final_arrays_present": not partial,
            "all_actual_allowlisted_array_bytes_copied_and_hash_verified": True,
            "actual_existing_allowlisted_array_files": arrays, "actual_allowlisted_array_files_copied": arrays}
        manifest = {"schema": "razr-N7-engineering-allowlist-export-v1", "functional_source_commit": MOD.S4,
            "raw_runtime_records_exported": False, "raw_runtime_records_durable": False,
            "producer_records_modified": False, "omitted_runtime_remains_on_ephemeral_runner_only": True,
            "original_input_ZIP_included": False, "original_input_fields_durable_release_asset_id": 677184053,
            "copied": copied, "projections": {}, "scientific_fragments": fragments,
            "original_runtime_record_hashes": [{"bytes": 1, "sha256": "0" * 64, "exported_original_bytes": False}],
            "scientific_preservation_actual": preservation,
            "exported_files": {name: identity(data) for name, data in contents.items()}}
        if mutation:
            mutation(manifest)
        return self.pack_typed_science(directory, contents, manifest, "N7_exported_files")

    def test_n7_complete_failed_solve_and_truthful_partial_arrays_preserved(self):
        for partial in (False, True):
            with self.subTest(partial=partial), tempfile.TemporaryDirectory() as d:
                p, binding = self.make_n7(d, partial)
                self.assertTrue(MOD.verify_zip(p, binding)["all_scientific_members_and_CRC_verified"])

    def test_n7_runtime_producer_modification_and_false_complete_claim_rejected(self):
        mutations = [lambda m: m.update(raw_runtime_records_exported=True),
                     lambda m: m.update(producer_records_modified=True),
                     lambda m: m.update(original_input_ZIP_included=True),
                     lambda m: m["scientific_preservation_actual"].update(all_ten_final_arrays_present=True)]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as d:
                p, binding = self.make_n7(d, True, mutation)
                with self.assertRaises(MOD.ArchiveInvariantError):
                    MOD.verify_zip(p, binding)

    def make_typed_report(self, directory, family, unsafe=False, modified=False):
        content = b'{"scientific_diagnostic":true}\n'
        identity = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        if family == "N6":
            manifest = {"schema": "razr-N6-engineering-allowlist-export-v1", "functional_source_commit": MOD.S4,
                "raw_runtime_records_exported": unsafe, "raw_runtime_records_durable": False,
                "producer_records_modified": modified, "omitted_runtime_remains_on_ephemeral_runner_only": True,
                "original_input_ZIP_or_field_arrays_duplicated_in_this_export": False,
                "original_input_fields_durable_release_asset_id": 677184053,
                "copied": {"scientific.json": {**identity, "original_bytes": True}},
                "original_runtime_record_hashes": [], "exported_files": {"scientific.json": identity}}
            layout = "N6_exported_files"
        else:
            manifest = {"schema": "razr-EC1-engineering-export-v1", "source_commit": MOD.S4,
                "raw_runtime_exported": unsafe, "raw_runtime_durable": False,
                "original_producer_records_modified": modified, "files": {"scientific.json": identity}}
            layout = "EC1_files"
        raw = json.dumps(manifest).encode()
        path = Path(directory) / "typed.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("scientific.json", content)
            z.writestr("MANIFEST.json", raw)
        return path, {"zip_bytes": path.stat().st_size, "zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "manifest_name": "MANIFEST.json", "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "manifest_layout": layout, "manifest_entries": 1}

    def test_exact_N6_and_EC1_contracts(self):
        for family in ("N6", "EC1"):
            with self.subTest(family=family), tempfile.TemporaryDirectory() as d:
                p, b = self.make_typed_report(d, family)
                self.assertTrue(MOD.verify_zip(p, b)["all_scientific_members_and_CRC_verified"])

    def test_N6_and_EC1_raw_runtime_or_modified_producer_rejected(self):
        for family in ("N6", "EC1"):
            for unsafe, modified in ((True, False), (False, True)):
                with self.subTest(family=family,unsafe=unsafe,modified=modified), tempfile.TemporaryDirectory() as d:
                    p, b = self.make_typed_report(d, family, unsafe, modified)
                    with self.assertRaises(MOD.ArchiveInvariantError):
                        MOD.verify_zip(p, b)

    def make(self, directory, extra=False, symlink=False):
        content = b"retained engineering bytes\n"
        manifest = json.dumps({"material.brep": {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}}).encode()
        path = Path(directory) / "scientific.zip"
        with zipfile.ZipFile(path, "w") as z:
            info = zipfile.ZipInfo("material.brep")
            if symlink:
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, content)
            z.writestr("MANIFEST.json", manifest)
            if extra:
                z.writestr("unlisted-runtime.log", "not allowed")
        return path, {"zip_bytes": path.stat().st_size, "zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "manifest_name": "MANIFEST.json", "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
                      "manifest_layout": "flat", "manifest_entries": 1}

    def test_exact_manifest_and_all_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make(d)
            self.assertTrue(MOD.verify_zip(p, b)["all_scientific_members_and_CRC_verified"])

    def test_wrong_original_zip_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make(d)
            b["zip_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                MOD.verify_zip(p, b)

    def test_extra_runtime_member_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make(d, extra=True)
            with self.assertRaises(ValueError):
                MOD.verify_zip(p, b)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p, b = self.make(d, symlink=True)
            with self.assertRaises(ValueError):
                MOD.verify_zip(p, b)

    def test_redirect_drops_authorization(self):
        client = MOD.Client("synthetic-test-token")
        seen = []
        class Opener:
            def open(self, request, timeout):
                seen.append(request)
                if len(seen) == 1:
                    raise urllib.error.HTTPError(request.full_url, 302, "redirect",
                        {"Location": "https://example.blob.core.windows.net/scientific"}, None)
                return io.BytesIO(b"artifact")
        client.opener = Opener()
        with client.binary("/actions/artifacts/1/zip") as stream:
            self.assertEqual(stream.read(), b"artifact")
        self.assertIsNotNone(seen[0].get_header("Authorization"))
        self.assertEqual(seen[0].get_header("Accept"), "application/vnd.github+json")
        self.assertIsNone(seen[1].get_header("Authorization"))

    def test_release_asset_binary_media_type(self):
        client = MOD.Client("synthetic-test-token")
        seen = []
        class Opener:
            def open(self, request, timeout):
                seen.append(request)
                response = io.BytesIO(b"asset")
                response.status = 200
                return response
        client.opener = Opener()
        with client.binary("/releases/assets/1") as stream:
            self.assertEqual(stream.read(), b"asset")
        self.assertEqual(seen[0].get_header("Accept"), "application/octet-stream")

    def test_unrecognized_binary_route_rejected(self):
        with self.assertRaises(MOD.ArchiveInvariantError):
            MOD.Client("synthetic-test-token").binary("/unlisted/route")

    def test_unrecognized_redirect_host_rejected(self):
        client = MOD.Client("synthetic-test-token")
        class Opener:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": "https://example.net/"}, None)
        client.opener = Opener()
        with self.assertRaises(ValueError):
            client.binary("/actions/artifacts/1/zip")

    def test_owned_draft_identity_rechecked(self):
        class Client:
            def json(self, suffix):
                return {"draft": True, "tag_name": MOD.TAG, "name": MOD.TITLE,
                        "body": MOD.BODY, "target_commitish": MOD.S4}
        self.assertTrue(MOD.require_owned_draft(Client(), 1)["draft"])

    def test_published_state_rejected_before_further_asset_write(self):
        class Client:
            def json(self, suffix):
                return {"draft": False, "tag_name": MOD.TAG, "name": MOD.TITLE,
                        "body": MOD.BODY, "target_commitish": MOD.S4}
        with self.assertRaises(MOD.ArchiveInvariantError):
            MOD.require_owned_draft(Client(), 1)



class N8TypedControls(unittest.TestCase):
    """Small synthetic storage records; no native arithmetic or network."""

    def make_n8(self):
        def ident(data):
            return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        payload = {}
        members = {}
        for j in range(1, 5):
            for kind in ("field", "residual"):
                name = f"probe-N7/final/probe-{j}-{kind}.npy"
                data = ("synthetic-original-" + name).encode()
                payload["frozen/" + name] = data
                members[name] = ident(data)
        for j in range(14):
            name = f"input-{j}.npy"
            data = ("synthetic-input-" + str(j)).encode()
            payload["frozen/" + name] = data
            members[name] = ident(data)
        payload["frozen/EXPORT_MANIFEST.json"] = b'{"synthetic_source_manifest":true}'
        original_manifest = ident(payload["frozen/EXPORT_MANIFEST.json"])
        frozen = {"schema": "razr-N8-frozen-original-inputs-v1", "functional_source_commit": MOD.S4,
                  "functional_source_tree": "cdd9e2c41216201b6cd04dd610d45fde80499045",
                  "source_artifact_id": 12633916809,
                  "source_ZIP_sha256": "2541e06e5c5dcc6a1797e5c85cde410a35056e4e23cae22b2ef9bb7759d85a1c",
                  "source_manifest_bytes": original_manifest["bytes"],
                  "source_manifest_sha256": original_manifest["sha256"], "members": members}
        payload["source/N8_FROZEN_INPUTS.json"] = json.dumps(frozen).encode()
        probes = [{}]
        references = []
        for j in range(1, 5):
            rec = {"scientific_storage": "explicit_frozen_original_field_and_residual_reference",
                   "new_native_residual_equals_frozen_original_array_bytes": True}
            for kind in ("field", "residual"):
                source = f"probe-N7/final/probe-{j}-{kind}.npy"
                relative = "frozen/" + source
                rec[kind + "_file"] = relative
                rec[kind + "_identity"] = dict(members[source])
                references.append({"trial_index": 1, "probe_index": j, "kind": kind,
                                   "expected_original_file": relative,
                                   "expected_original_identity": dict(members[source]),
                                   "explicit_report_reference_matches": True,
                                   "referenced_original_bytes_present_and_hash_verified": True,
                                   "explicit_actual_native_equality_record_present": True,
                                   "complete_reference": True})
            probes.append(rec)
        producer = {"schema": "razr-N8-finite-original-five-probe-v1", "functional_source_commit": MOD.S4,
                    "functional_source_tree": "cdd9e2c41216201b6cd04dd610d45fde80499045",
                    "trials": [{"trial_index": 1, "probes": probes}], "original_five_passed": False}
        payload["probe-N8/N8_REPORT.json"] = json.dumps(producer).encode()
        candidate = ["probe-N8/trial-01/" + name for name in
                     ("probe-0-field.npy", "probe-0-residual.npy", "requested-update.npy", "actual-update.npy")]
        final = [f"probe-N8/final/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
        for name in candidate + final:
            payload[name] = ("synthetic-scientific-" + name).encode()
        copied = {name: {**ident(data), "original_bytes": True} for name, data in payload.items()}
        payload["EXECUTION_CHECKS.engineering.json"] = b"{}"
        entries = {name: ident(data) for name, data in payload.items()}
        arrays = sorted(candidate + final)
        p = {"selected_complete_inputs_expected": 22, "selected_complete_input_identities_verified": 22,
             "missing_selected_complete_inputs": [], "partial_original_input_files": [],
             "all_22_selected_complete_inputs_identity_verified": True, "original_source_manifest_identity_verified": True,
             "started_full_candidate_indices": [1], "expected_complete_candidate_array_count": 4,
             "complete_candidate_arrays_present": 4, "missing_complete_candidate_arrays": [],
             "partial_scientific_candidate_or_final_array_files": [], "all_started_full_candidate_new_arrays_complete": True,
             "expected_per_candidate_frozen_reference_count": 8, "complete_per_candidate_frozen_reference_count": 8,
             "per_candidate_frozen_references": references, "missing_or_incomplete_candidate_frozen_references": [],
             "all_started_full_candidates_all5_fields_and_residuals_recoverable": True,
             "unexpected_retained_duplicate_candidate_arrays": [], "final_complete_array_count": 10,
             "missing_final_arrays": [], "all_ten_final_arrays_present": True,
             "all_actual_allowlisted_array_bytes_copied_and_hash_verified": True,
             "actual_existing_allowlisted_array_files": arrays[:], "actual_allowlisted_array_files_copied": arrays[:]}
        manifest = {"schema": "razr-N8-engineering-allowlist-export-v1", "functional_source_commit": MOD.S4,
                    "raw_runtime_records_exported": False, "raw_runtime_records_durable": False,
                    "producer_records_modified": False, "omitted_runtime_remains_on_ephemeral_runner_only": True,
                    "original_input_ZIP_included": False, "original_input_fields_durable_release_asset_id": None,
                    "original_input_fields_source_artifact_id": 12633916809,
                    "source_N7_long_term_archive_status_at_registration": "pending", "copied": copied,
                    "projections": {}, "original_runtime_record_hashes": [], "scientific_fragments": [],
                    "scientific_preservation_actual": p, "exported_files": entries}
        return payload, manifest, entries

    def check(self, payload, manifest, entries):
        class Reader:
            def read(self, name):
                return payload[name]
        return MOD.verify_n8_scope(Reader(), manifest, entries)

    def test_n8_failed_numeric_originals_are_archivable(self):
        payload, m, e = self.make_n8()
        result = self.check(payload, m, e)
        self.assertEqual(result["complete_new_arrays"], 4)
        self.assertEqual(result["complete_frozen_references"], 8)
        self.assertFalse(result["qualification_required"])

    def test_n8_unknown_schema_rejected(self):
        payload, m, e = self.make_n8()
        m["schema"] = "unknown-new-format"
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n8_runtime_claim_and_private_inventory_rejected(self):
        for extra in (False, True):
            with self.subTest(extra=extra):
                payload, m, e = self.make_n8()
                if extra:
                    m["original_runtime_record_hashes"] = [{"bytes": 1, "sha256": "0" * 64,
                                                            "exported_original_bytes": False, "path": "unlisted"}]
                else:
                    m["raw_runtime_records_exported"] = True
                with self.assertRaises(MOD.ArchiveInvariantError):
                    self.check(payload, m, e)

    def test_n8_frozen_reference_identity_tamper_rejected(self):
        payload, m, e = self.make_n8()
        name = "probe-N8/N8_REPORT.json"
        report = json.loads(payload[name])
        report["trials"][0]["probes"][1]["field_identity"]["sha256"] = "0" * 64
        payload[name] = json.dumps(report).encode()
        e[name] = {"bytes": len(payload[name]), "sha256": hashlib.sha256(payload[name]).hexdigest()}
        m["copied"][name] = {**e[name], "original_bytes": True}
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n8_missing_frozen_bytes_cannot_claim_complete(self):
        payload, m, e = self.make_n8()
        name = "frozen/probe-N7/final/probe-1-field.npy"
        del payload[name], m["copied"][name], e[name]
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n8_four_new_arrays_cannot_be_reported_as_twelve(self):
        payload, m, e = self.make_n8()
        m["scientific_preservation_actual"]["expected_complete_candidate_array_count"] = 12
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n8_truthful_partial_new_array_is_preserved(self):
        payload, m, e = self.make_n8()
        name = "probe-N8/trial-01/probe-0-field.npy"
        partial = name + ".writing"
        payload[partial] = payload.pop(name)
        m["copied"][partial] = m["copied"].pop(name)
        e[partial] = e.pop(name)
        m["scientific_fragments"] = [partial]
        p = m["scientific_preservation_actual"]
        p["complete_candidate_arrays_present"] = 3
        p["missing_complete_candidate_arrays"] = [name]
        p["partial_scientific_candidate_or_final_array_files"] = [partial]
        p["all_started_full_candidate_new_arrays_complete"] = False
        p["all_started_full_candidates_all5_fields_and_residuals_recoverable"] = False
        for key in ("actual_existing_allowlisted_array_files", "actual_allowlisted_array_files_copied"):
            p[key] = sorted(partial if v == name else v for v in p[key])
        self.assertEqual(self.check(payload, m, e)["complete_new_arrays"], 3)

    def test_n8_truthful_unresolved_report_references_are_preserved(self):
        payload, m, e = self.make_n8()
        name = "probe-N8/N8_REPORT.json"
        del payload[name], m["copied"][name], e[name]
        p = m["scientific_preservation_actual"]
        for row in p["per_candidate_frozen_references"]:
            row["explicit_report_reference_matches"] = False
            row["explicit_actual_native_equality_record_present"] = False
            row["complete_reference"] = False
        p["complete_per_candidate_frozen_reference_count"] = 0
        p["missing_or_incomplete_candidate_frozen_references"] = p["per_candidate_frozen_references"][:]
        p["all_started_full_candidates_all5_fields_and_residuals_recoverable"] = False
        self.assertEqual(self.check(payload, m, e)["unresolved_frozen_references"], 8)


class N9TypedControls(unittest.TestCase):
    """Small synthetic storage records; no native arithmetic or network."""

    def make_n9(self):
        def ident(data):
            return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        payload = {}
        members = {}
        for j in range(1, 5):
            for kind in ("field", "residual"):
                name = f"probe-N8/final/probe-{j}-{kind}.npy"
                data = ("synthetic-original-" + name).encode()
                payload["frozen/" + name] = data
                members[name] = ident(data)
        for j in range(14):
            name = f"input-{j}.npy"
            data = ("synthetic-input-" + str(j)).encode()
            payload["frozen/" + name] = data
            members[name] = ident(data)
        payload["frozen/EXPORT_MANIFEST.json"] = b'{"synthetic_source_manifest":true}'
        original_manifest = ident(payload["frozen/EXPORT_MANIFEST.json"])
        frozen = {"schema": "razr-N9-frozen-original-inputs-v1", "functional_source_commit": MOD.S4,
                  "functional_source_tree": "cdd9e2c41216201b6cd04dd610d45fde80499045",
                  "source_artifact_id": 12634369890,
                  "source_ZIP_sha256": "ac747737b52960596c6a35be47ba3d924f6276227d22a98be8fd3b1fde0d9d0e",
                  "source_manifest_bytes": original_manifest["bytes"],
                  "source_manifest_sha256": original_manifest["sha256"], "members": members}
        payload["source/N9_FROZEN_INPUTS.json"] = json.dumps(frozen).encode()
        probes = [{}]
        references = []
        for j in range(1, 5):
            rec = {"scientific_storage": "explicit_frozen_original_field_and_residual_reference",
                   "new_native_residual_equals_frozen_original_array_bytes": True}
            for kind in ("field", "residual"):
                source = f"probe-N8/final/probe-{j}-{kind}.npy"
                relative = "frozen/" + source
                rec[kind + "_file"] = relative
                rec[kind + "_identity"] = dict(members[source])
                references.append({"trial_index": 1, "probe_index": j, "kind": kind,
                                   "expected_original_file": relative,
                                   "expected_original_identity": dict(members[source]),
                                   "explicit_report_reference_matches": True,
                                   "referenced_original_bytes_present_and_hash_verified": True,
                                   "explicit_actual_native_equality_record_present": True,
                                   "complete_reference": True})
            probes.append(rec)
        producer = {"schema": "razr-N9-finite-original-five-probe-v1", "functional_source_commit": MOD.S4,
                    "functional_source_tree": "cdd9e2c41216201b6cd04dd610d45fde80499045",
                    "trials": [{"trial_index": 1, "probes": probes}], "original_five_passed": False}
        payload["probe-N9/N9_REPORT.json"] = json.dumps(producer).encode()
        candidate = ["probe-N9/trial-01/" + name for name in
                     ("probe-0-field.npy", "probe-0-residual.npy", "requested-update.npy", "actual-update.npy")]
        final = [f"probe-N9/final/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
        for name in candidate + final:
            payload[name] = ("synthetic-scientific-" + name).encode()
        copied = {name: {**ident(data), "original_bytes": True} for name, data in payload.items()}
        payload["EXECUTION_CHECKS.engineering.json"] = b"{}"
        entries = {name: ident(data) for name, data in payload.items()}
        arrays = sorted(candidate + final)
        p = {"selected_complete_inputs_expected": 22, "selected_complete_input_identities_verified": 22,
             "missing_selected_complete_inputs": [], "partial_original_input_files": [],
             "all_22_selected_complete_inputs_identity_verified": True, "original_source_manifest_identity_verified": True,
             "started_full_candidate_indices": [1], "expected_complete_candidate_array_count": 4,
             "complete_candidate_arrays_present": 4, "missing_complete_candidate_arrays": [],
             "partial_scientific_candidate_or_final_array_files": [], "all_started_full_candidate_new_arrays_complete": True,
             "expected_per_candidate_frozen_reference_count": 8, "complete_per_candidate_frozen_reference_count": 8,
             "per_candidate_frozen_references": references, "missing_or_incomplete_candidate_frozen_references": [],
             "all_started_full_candidates_all5_fields_and_residuals_recoverable": True,
             "unexpected_retained_duplicate_candidate_arrays": [], "final_complete_array_count": 10,
             "missing_final_arrays": [], "all_ten_final_arrays_present": True,
             "all_actual_allowlisted_array_bytes_copied_and_hash_verified": True,
             "actual_existing_allowlisted_array_files": arrays[:], "actual_allowlisted_array_files_copied": arrays[:]}
        manifest = {"schema": "razr-N9-engineering-allowlist-export-v1", "functional_source_commit": MOD.S4,
                    "raw_runtime_records_exported": False, "raw_runtime_records_durable": False,
                    "producer_records_modified": False, "omitted_runtime_remains_on_ephemeral_runner_only": True,
                    "original_input_ZIP_included": False, "original_input_fields_durable_release_asset_id": None,
                    "original_input_fields_source_artifact_id": 12634369890,
                    "source_N8_long_term_archive_status_at_registration": "pending", "copied": copied,
                    "projections": {}, "original_runtime_record_hashes": [], "scientific_fragments": [],
                    "scientific_preservation_actual": p, "exported_files": entries}
        return payload, manifest, entries

    def check(self, payload, manifest, entries):
        class Reader:
            def read(self, name):
                return payload[name]
        return MOD.verify_n9_scope(Reader(), manifest, entries)

    def test_n9_failed_numeric_originals_are_archivable(self):
        payload, m, e = self.make_n9()
        result = self.check(payload, m, e)
        self.assertEqual(result["complete_new_arrays"], 4)
        self.assertEqual(result["complete_frozen_references"], 8)
        self.assertFalse(result["qualification_required"])

    def test_n9_unknown_schema_rejected(self):
        payload, m, e = self.make_n9()
        m["schema"] = "unknown-new-format"
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n9_runtime_claim_and_private_inventory_rejected(self):
        for extra in (False, True):
            with self.subTest(extra=extra):
                payload, m, e = self.make_n9()
                if extra:
                    m["original_runtime_record_hashes"] = [{"bytes": 1, "sha256": "0" * 64,
                                                            "exported_original_bytes": False, "path": "unlisted"}]
                else:
                    m["raw_runtime_records_exported"] = True
                with self.assertRaises(MOD.ArchiveInvariantError):
                    self.check(payload, m, e)

    def test_n9_frozen_reference_identity_tamper_rejected(self):
        payload, m, e = self.make_n9()
        name = "probe-N9/N9_REPORT.json"
        report = json.loads(payload[name])
        report["trials"][0]["probes"][1]["field_identity"]["sha256"] = "0" * 64
        payload[name] = json.dumps(report).encode()
        e[name] = {"bytes": len(payload[name]), "sha256": hashlib.sha256(payload[name]).hexdigest()}
        m["copied"][name] = {**e[name], "original_bytes": True}
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n9_missing_frozen_bytes_cannot_claim_complete(self):
        payload, m, e = self.make_n9()
        name = "frozen/probe-N8/final/probe-1-field.npy"
        del payload[name], m["copied"][name], e[name]
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n9_four_new_arrays_cannot_be_reported_as_twelve(self):
        payload, m, e = self.make_n9()
        m["scientific_preservation_actual"]["expected_complete_candidate_array_count"] = 12
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n9_truthful_partial_new_array_is_preserved(self):
        payload, m, e = self.make_n9()
        name = "probe-N9/trial-01/probe-0-field.npy"
        partial = name + ".writing"
        payload[partial] = payload.pop(name)
        m["copied"][partial] = m["copied"].pop(name)
        e[partial] = e.pop(name)
        m["scientific_fragments"] = [partial]
        p = m["scientific_preservation_actual"]
        p["complete_candidate_arrays_present"] = 3
        p["missing_complete_candidate_arrays"] = [name]
        p["partial_scientific_candidate_or_final_array_files"] = [partial]
        p["all_started_full_candidate_new_arrays_complete"] = False
        p["all_started_full_candidates_all5_fields_and_residuals_recoverable"] = False
        for key in ("actual_existing_allowlisted_array_files", "actual_allowlisted_array_files_copied"):
            p[key] = sorted(partial if v == name else v for v in p[key])
        self.assertEqual(self.check(payload, m, e)["complete_new_arrays"], 3)

    def test_n9_truthful_unresolved_report_references_are_preserved(self):
        payload, m, e = self.make_n9()
        name = "probe-N9/N9_REPORT.json"
        del payload[name], m["copied"][name], e[name]
        p = m["scientific_preservation_actual"]
        for row in p["per_candidate_frozen_references"]:
            row["explicit_report_reference_matches"] = False
            row["explicit_actual_native_equality_record_present"] = False
            row["complete_reference"] = False
        p["complete_per_candidate_frozen_reference_count"] = 0
        p["missing_or_incomplete_candidate_frozen_references"] = p["per_candidate_frozen_references"][:]
        p["all_started_full_candidates_all5_fields_and_residuals_recoverable"] = False
        self.assertEqual(self.check(payload, m, e)["unresolved_frozen_references"], 8)

class L5FailedControlTypedControls(unittest.TestCase):
    def fixture(self):
        payload = {"source-"+name: ("synthetic-frozen-"+name).encode() for name in MOD.L5_CONTROL_SOURCE_NAMES}
        identity = {name: {"bytes":len(payload["source-"+name]), "sha256":hashlib.sha256(payload["source-"+name]).hexdigest()}
                    for name in MOD.L5_CONTROL_SOURCE_NAMES}
        scope = {"schema":"razr-L5-science-export-v1", "raw_runtime_exported":False,
                 "private_runtime_durable_preservation_claimed":False,"rejected_items":[],
                 "derived_producer_projections":[], "complete_product_qualification":False,
                 "unknown_filename_or_link_never_exported":True}
        payload["EXPORT_SCOPE.json"] = json.dumps(scope).encode()
        payload["L5_SOURCE_IDENTITY.json"] = json.dumps(identity).encode()
        payload["report.json"] = b'{"completed":false,"exception_type":"ValueError"}'
        entries={name:{"bytes":len(value), "sha256":hashlib.sha256(value).hexdigest()} for name,value in payload.items()}
        return payload,entries

    def check(self,payload,entries):
        class Reader:
            def read(self,name): return payload[name]
        return MOD.verify_l5_failed_control_scope(Reader(),entries)

    def test_l5_failed_original_control_is_archivable(self):
        p,e=self.fixture()
        self.assertEqual(self.check(p,e),{"frozen_source_files":19,"qualification_required":False})

    def test_l5_runtime_claim_or_cross_family_rejected(self):
        for key,value in [("raw_runtime_exported",True),("schema","razr-V4a-science-export-v1"),
                          ("complete_product_qualification",True)]:
            p,e=self.fixture();scope=json.loads(p["EXPORT_SCOPE.json"]);scope[key]=value
            p["EXPORT_SCOPE.json"]=json.dumps(scope).encode()
            with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e)

    def test_l5_missing_source_or_source_identity_tamper_rejected(self):
        for mutate in [lambda e:e.pop("source-run_l5.py"),
                       lambda e:e["source-run_l5.py"].update(sha256="0"*64)]:
            p,e=self.fixture();mutate(e)
            with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e)

    def test_l5_unreviewed_runtime_filename_rejected(self):
        p,e=self.fixture();e["unreviewed-runtime.json"]={"bytes":2,"sha256":hashlib.sha256(b"{}").hexdigest()}
        with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e)


if __name__ == "__main__":
    unittest.main()
