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


class N10TypedControls(unittest.TestCase):
    """Small synthetic storage records; no native arithmetic or network."""

    def make_n10(self):
        def ident(data):
            return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        payload = {}
        members = {}
        for j in range(1, 5):
            for kind in ("field", "residual"):
                name = f"probe-N9/final/probe-{j}-{kind}.npy"
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
        frozen = {"schema": "razr-N10-frozen-original-inputs-v1", "functional_source_commit": MOD.S4,
                  "functional_source_tree": "cdd9e2c41216201b6cd04dd610d45fde80499045",
                  "source_artifact_id": 12715569236,
                  "source_ZIP_sha256": "13fcea5602f25efc827ebb717b1b38c76541c95d78addd78374f69dc359a6e27",
                  "source_manifest_bytes": original_manifest["bytes"],
                  "source_manifest_sha256": original_manifest["sha256"], "members": members}
        payload["source/N10_FROZEN_INPUTS.json"] = json.dumps(frozen).encode()
        probes = [{}]
        references = []
        for j in range(1, 5):
            rec = {"scientific_storage": "explicit_frozen_original_field_and_residual_reference",
                   "new_native_residual_equals_frozen_original_array_bytes": True}
            for kind in ("field", "residual"):
                source = f"probe-N9/final/probe-{j}-{kind}.npy"
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
        producer = {"schema": "razr-N10-finite-original-five-probe-v1", "functional_source_commit": MOD.S4,
                    "functional_source_tree": "cdd9e2c41216201b6cd04dd610d45fde80499045",
                    "trials": [{"trial_index": 1, "probes": probes}], "original_five_passed": False}
        payload["probe-N10/N10_REPORT.json"] = json.dumps(producer).encode()
        candidate = ["probe-N10/trial-01/" + name for name in
                     ("probe-0-field.npy", "probe-0-residual.npy", "requested-update.npy", "actual-update.npy")]
        final = [f"probe-N10/final/probe-{j}-{kind}.npy" for j in range(5) for kind in ("field", "residual")]
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
        manifest = {"schema": "razr-N10-engineering-allowlist-export-v1", "functional_source_commit": MOD.S4,
                    "raw_runtime_records_exported": False, "raw_runtime_records_durable": False,
                    "producer_records_modified": False, "omitted_runtime_remains_on_ephemeral_runner_only": True,
                    "original_input_ZIP_included": False, "original_input_fields_durable_release_asset_id": 680813106,
                    "original_input_fields_source_artifact_id": 12715569236,
                    "source_N9_long_term_archive_status_at_registration": "actual_all_members_and_uploaded_whole_bytes_verified",
                    "source_N9_archive_run_id":40467375503,
                    "source_N9_archive_receipt_sha256":"f3e81121c6021604f9b46190a3184e2ae985a27dc98144ff4388ed324f93b8f5", "copied": copied,
                    "projections": {}, "original_runtime_record_hashes": [], "scientific_fragments": [],
                    "scientific_preservation_actual": p, "exported_files": entries}
        manifest["virtual_record_preservation_actual"]=[
            {"file":"probe-N10/"+n,"present_and_original_bytes_copied":False,
             "complete_JSON_records":0,"last_record_is_partial":False,
             "native_full_qualification_from_these_virtual_records":False}
            for n in ("N10_SCALAR_SCREENS.jsonl","N10_SCREEN_ATTEMPTS.jsonl")]
        return payload, manifest, entries

    def check(self, payload, manifest, entries):
        class Reader:
            def read(self, name):
                return payload[name]
        return MOD.verify_n10_scope(Reader(), manifest, entries)

    def test_n10_failed_numeric_originals_are_archivable(self):
        payload, m, e = self.make_n10()
        result = self.check(payload, m, e)
        self.assertEqual(result["complete_new_arrays"], 4)
        self.assertEqual(result["complete_frozen_references"], 8)
        self.assertFalse(result["qualification_required"])

    def test_n10_unknown_schema_rejected(self):
        payload, m, e = self.make_n10()
        m["schema"] = "unknown-new-format"
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n10_runtime_claim_and_private_inventory_rejected(self):
        for extra in (False, True):
            with self.subTest(extra=extra):
                payload, m, e = self.make_n10()
                if extra:
                    m["original_runtime_record_hashes"] = [{"bytes": 1, "sha256": "0" * 64,
                                                            "exported_original_bytes": False, "path": "unlisted"}]
                else:
                    m["raw_runtime_records_exported"] = True
                with self.assertRaises(MOD.ArchiveInvariantError):
                    self.check(payload, m, e)

    def test_n10_frozen_reference_identity_tamper_rejected(self):
        payload, m, e = self.make_n10()
        name = "probe-N10/N10_REPORT.json"
        report = json.loads(payload[name])
        report["trials"][0]["probes"][1]["field_identity"]["sha256"] = "0" * 64
        payload[name] = json.dumps(report).encode()
        e[name] = {"bytes": len(payload[name]), "sha256": hashlib.sha256(payload[name]).hexdigest()}
        m["copied"][name] = {**e[name], "original_bytes": True}
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n10_missing_frozen_bytes_cannot_claim_complete(self):
        payload, m, e = self.make_n10()
        name = "frozen/probe-N9/final/probe-1-field.npy"
        del payload[name], m["copied"][name], e[name]
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n10_four_new_arrays_cannot_be_reported_as_twelve(self):
        payload, m, e = self.make_n10()
        m["scientific_preservation_actual"]["expected_complete_candidate_array_count"] = 12
        with self.assertRaises(MOD.ArchiveInvariantError):
            self.check(payload, m, e)

    def test_n10_truthful_partial_new_array_is_preserved(self):
        payload, m, e = self.make_n10()
        name = "probe-N10/trial-01/probe-0-field.npy"
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

    def test_n10_truthful_unresolved_report_references_are_preserved(self):
        payload, m, e = self.make_n10()
        name = "probe-N10/N10_REPORT.json"
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

    def test_n10_durable_predecessor_status_cannot_be_backdated(self):
        p,m,e=self.make_n10()
        m["original_input_fields_durable_release_asset_id"]=None
        with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,m,e)

    def test_n10_truthful_terminal_virtual_fragment_preserved(self):
        p,m,e=self.make_n10()
        name="probe-N10/N10_SCREEN_ATTEMPTS.jsonl"
        data=b'{"schema":"razr-N10-virtual-attempt-v1","screen_index":1}\n{"screen_index":'
        p[name]=data;e[name]={"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
        m["copied"][name]={**e[name],"original_bytes":True}
        m["scientific_fragments"]=[name]
        m["virtual_record_preservation_actual"][1].update(present_and_original_bytes_copied=True,
                                                      complete_JSON_records=1,last_record_is_partial=True)
        self.assertFalse(self.check(p,m,e)["qualification_required"])
        m["virtual_record_preservation_actual"][1]["last_record_is_partial"]=False
        with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,m,e)

    def test_n10_virtual_log_not_a_native_qualification(self):
        p,m,e=self.make_n10()
        m["virtual_record_preservation_actual"][0]["native_full_qualification_from_these_virtual_records"]=True
        with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,m,e)


L5_DIAGNOSTIC_FIXTURES = {'L5c': {'EXPORT_SCOPE.json': {'schema': 'razr-L5c-narrow-scientific-export-v1', 'raw_runtime_exported': False, 'raw_private_runtime_preservation_claimed': False, 'rejected_items': [], 'failed_original_operations_not_reclassified': True, 'original_seven_reexecuted': False, 'complete_product_qualification': False}, 'L5_SOURCE_IDENTITY.json': {'run_l5.py': {'sha256': 'c17c812f90a19ca98e37e99056c78607b57872adcb13aa52b4904d3086e62e12', 'bytes': 17573}, 'supervise_l5.py': {'sha256': '5cdb452e4cb14313e65767d292e0434908da830bbc4a4dadf50ec1b6d94762f4', 'bytes': 8452}, 'cylindrical_sweep_l5.py': {'sha256': '433b9f89f34ffca28123d767f02ae81572e68d282e95f020a600b1b31aa1d949', 'bytes': 23268}, 'exact_xy_support_l5.py': {'sha256': 'd1e113d1e61051d7fcee9d0d65c591da1f4a83c811ee3dc2e34226c6cc7d4369', 'bytes': 7117}, 'test_l5_native.py': {'sha256': 'c3b09e50c3083142678dce5add1a3f93837692818e8b6dbfe9f7dc1420b0d723', 'bytes': 5236}, 'check_l5_plan.py': {'sha256': 'e82a6d91fc0658ebc8cc708bff5a9474a3a5b00af5b974181231041d75d3efc9', 'bytes': 3728}, 'l5_science_contract.py': {'sha256': 'd69f87ad8c894018a03c27451d38cefb569a4a31fddd579165a285e701b79967', 'bytes': 8220}, 'read_l5_native.py': {'sha256': '29790e254aea6ebdf90400121531824aebce8fe108dab302dc3af4a57c7cf548', 'bytes': 14765}, 'read_l5_records.py': {'sha256': '00fe744fc9cb8751b11806b33ba1deacd58709c28092ec315844daa900aab40a', 'bytes': 7891}, 'export_l5.py': {'sha256': '75d21a7e1b014877b6bae822ba8adec264a10ce220f1a1f6aefe50f9eb0bf7d7', 'bytes': 7190}, 'test_export_l5.py': {'sha256': '81c6ae57954c3d05a487ff3512f68f78cd792fc3c9f7247f476fbb71618ddc74', 'bytes': 5453}, 'capacity_stage_v4.py': {'sha256': '7aa792c027ca824440c7fa61bb9c39e678a45380ca69485e5335eb0aac3c8e14', 'bytes': 15054}, 'full_slide_api_v4.py': {'sha256': '698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64', 'bytes': 13596}, 'envelope_v2.py': {'sha256': '807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc', 'bytes': 11001}, 'correlated_v3.py': {'sha256': '2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2', 'bytes': 14583}, 'test_l2_native.py': {'sha256': '39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318', 'bytes': 1910}, 'frozen_key_factory_adapter.py': {'sha256': 'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6', 'bytes': 8189}, 'K1_BINDING.json': {'sha256': 'cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be', 'bytes': 3914}, 'L5_ORIGINAL_SEVEN_BINDING.json': {'sha256': '7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2', 'bytes': 39348}, 'README.md': {'sha256': '02176d24c635cb806ece05daa61b01a97589c9f82b223ccd3406c0b62eaf5fee', 'bytes': 4132}, 'L5_METHOD_AND_CAPACITY_PLAN.md': {'sha256': '6464057058016f123b5789033a7f2ae27f453908412499110e79e1987d72be57', 'bytes': 12034}}, 'L5C_SOURCE_IDENTITY.json': {'schema': 'razr-L5c-frozen-diagnostic-source-byte-check-v1', 'sources': {'run_l5c.py': {'bytes': 22038, 'sha256': '6754946bb1e41df130841834e21c6a1ea7c1c30ce197c6224a657d7eb8c35f01'}, 'supervise_l5c.py': {'bytes': 8421, 'sha256': 'e2bc7998cc46ab751804c6b5c2f42d8a88b3c0273c12cf4e40a8341dd9e66910'}, 'export_l5c.py': {'bytes': 4470, 'sha256': 'ece630d25ff54bf50031b38210c0db7ee1abd124140ef72fe56c5ef1ed621b25'}, 'L5C_INPUT_BINDING.json': {'bytes': 20527, 'sha256': 'a06aed5fc76b5a7bc5c538eb1920802b14594fa63cb36b171b3fcebbac12d173'}, 'L5C_CAPACITY_PREREGISTRATION.json': {'bytes': 2201, 'sha256': '5f6d44f507cb925907e71c194719f7e376240a2544b01354d02fca83776d08ba'}}, 'old_L5b_workflow_commit': '690b1ed0df100fe175f5d6752b716105c0521a25', 'unchanged_original_19_scientific_sources': True, 'new_native_execution': False}, 'source-L5C_INPUT_BINDING.json': {'schema': 'razr-L5c-frozen-L5b-scientific-input-v1', 'source_workflow_commit': '690b1ed0df100fe175f5d6752b716105c0521a25', 'source_run_id': 40465353232, 'source_run_attempt': 1, 'source_artifact_id': 12715683051, 'source_artifact_name': 'S4-L5-original-40465353232-1', 'source_zip_bytes': 143535, 'source_zip_sha256': '39bd7f2f28bb81cf8e8a80357ce4c74e0ceb0d7433190e30c67515558a0310aa', 'source_manifest_bytes': 10031, 'source_manifest_sha256': 'a2193e4bbb94b92a42072b2942085756df37f60540e01e0db796bd8c0f298591', 'source_manifest_entries': 68, 'source_regular_file_count': 69, 'source_manifest': {'EXPORT_SCOPE.json': {'sha256': '4fd1ea5acc011fc88dce7005f603ce72900937a08b09cb7d225c804f30ceeb42', 'bytes': 290}, 'INDEPENDENT_RECORD_CHECK.json': {'sha256': 'd5c91c8af75cda009380f721f6cccee3396bfeeafbde14967424a6809f2e516c', 'bytes': 785}, 'L5_INPUT_VERIFIED.json': {'sha256': 'a631ba8e9af684d48f4924741d6566898567b54dd98dd7bc3478e3bbf5a763b1', 'bytes': 293}, 'L5_SOURCE_IDENTITY.json': {'sha256': '211f04f27a2ccadc69ced687ce105ee7d8c19929e3a93deeea17727ab15df2f1', 'bytes': 2773}, 'L5_SOURCE_PLAN_RECHECK.json': {'sha256': '5bdd6039f6c44ead328e9920a61fd840f9f4271f7068eebaf87367148cc98cc8', 'bytes': 187511}, 'NATIVE_READBACK.json': {'sha256': '3a2f267cbacc60b56d7389e43db6d2a80c17c261e2398aba6ba3853c1e11770d', 'bytes': 3296}, 'control-ordinary-capsule-assembled-union.brep': {'sha256': '35da2908c525a504a2666ccdbfe4830f10211a9e8a33897834714aa7dd15afd2', 'bytes': 5550}, 'control-ordinary-capsule-bridge-difference.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 'control-ordinary-capsule-bridge.brep': {'sha256': '70da41ff7e5fbfbc351881caa6ec429eedc13f5407576683fc99b2faa97205b2', 'bytes': 4290}, 'control-ordinary-capsule-endpoint-0-difference.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 'control-ordinary-capsule-endpoint-0.brep': {'sha256': '46c0f5d0e649c46166be55151950991c0694d28685ce7a64a356129d8213c8bb', 'bytes': 1108}, 'control-ordinary-capsule-endpoint-1-difference.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 'control-ordinary-capsule-endpoint-1.brep': {'sha256': 'ec8f3d870f052891b0171779029909113f3ffb428f449c041613a6d4a00550e7', 'bytes': 1085}, 'control-ordinary-source-disk.brep': {'sha256': '46c0f5d0e649c46166be55151950991c0694d28685ce7a64a356129d8213c8bb', 'bytes': 1108}, 'control-ordinary-whole-carrier.brep': {'sha256': '728af19c7004cfd2c4d42912daf5b8fb982efad175567ca38f223c5d46f6f36b', 'bytes': 6522}, 'control-original-extrusion-original-face.brep': {'sha256': 'ad4c3a9dce88d8f4fc37f507461907edbc0e97468639f1ce973f0ec9f738e36e', 'bytes': 2086}, 'control-original-extrusion-original-face.step': {'sha256': '2757f836bf065837e34062563d12c1b8bb84e2ed57453536373c95b7c022eb4a', 'bytes': 5089}, 'control-original-extrusion-original-shape.brep': {'sha256': 'f48d4f4a188fc7b85e0d5a89082134de47bfa83b5e4169c75de639ee1eb0d5a8', 'bytes': 9378}, 'control-original-extrusion-original-shape.step': {'sha256': 'b2315f536a5146ec6ad14d9ee296c6d8a28f3d0da21d0d6af147d956efcbc1ce', 'bytes': 31982}, 'control-original-extrusion-v2-region-0.brep': {'sha256': '8c5ccf1475719375dbce201d0f5ef809db4fb3dc8a9d74ff62f91c336e2fabad', 'bytes': 9378}, 'control-original-extrusion-v2-region-1.brep': {'sha256': 'aed40e139549231ebdb923eabd8a0f3c509c4158dda552a2d954f6bf961caf45', 'bytes': 8252}, 'control-original-extrusion-v2-region-10.brep': {'sha256': 'ad78ef2681f0c628833a419807b9dba10f93df67bca57531b21d6c92ef890176', 'bytes': 4817}, 'control-original-extrusion-v2-region-11.brep': {'sha256': '2d3b5737046c85392c4c5db88f3d8e958d725c02344a54d9b6d04f544a563c86', 'bytes': 4805}, 'control-original-extrusion-v2-region-2.brep': {'sha256': '3139cf6ee76f11a873e9483aaf37539e2525bd9d14b7653b8d386a77bdcc3cc7', 'bytes': 4512}, 'control-original-extrusion-v2-region-3.brep': {'sha256': 'f6297753f611850138d36f7f2b721e4806cc03093af1e4016801753eb649e6a2', 'bytes': 4832}, 'control-original-extrusion-v2-region-4.brep': {'sha256': '7576946f6ec42eef503580183799263d8913f3b1ba77627c69ef1daa73509ffd', 'bytes': 4499}, 'control-original-extrusion-v2-region-5.brep': {'sha256': 'fec9264564d033a7523eba749e7f1464521511f9b51b56131a09e3e859e128b3', 'bytes': 4556}, 'control-original-extrusion-v2-region-6.brep': {'sha256': 'a8d89327f005ab898cca343651c120acfd7c5bab2304b8d0b9a9df1ee5d488ff', 'bytes': 4508}, 'control-original-extrusion-v2-region-7.brep': {'sha256': '20983b339b49661ae1493c167529bf479d535872448cc2e799815e035987239f', 'bytes': 4895}, 'control-original-extrusion-v2-region-8.brep': {'sha256': '7509720b56bc1c3b28a1f8ab107ef2cf96a25a3af8d75229a372052a933f5275', 'bytes': 4521}, 'control-original-extrusion-v2-region-9.brep': {'sha256': '58b1b5db3808318a704f66aba7a66dba49349fc174fcae1b98a9511b3483b8b0', 'bytes': 4636}, 'control-reversed-capsule-assembled-union.brep': {'sha256': 'd788571efcfac9a477991f96d67957d096e26af5f223faed6be848612e84c5bf', 'bytes': 5550}, 'control-reversed-capsule-bridge-difference.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 'control-reversed-capsule-bridge.brep': {'sha256': 'f07535fbe43b82d4fd1bc51424debaae981c2a80074c6a145bc9239e4c889797', 'bytes': 4290}, 'control-reversed-capsule-endpoint-0-difference.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 'control-reversed-capsule-endpoint-0.brep': {'sha256': 'ec8f3d870f052891b0171779029909113f3ffb428f449c041613a6d4a00550e7', 'bytes': 1085}, 'control-reversed-capsule-endpoint-1-difference.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 'control-reversed-capsule-endpoint-1.brep': {'sha256': '46c0f5d0e649c46166be55151950991c0694d28685ce7a64a356129d8213c8bb', 'bytes': 1108}, 'control-reversed-source-disk.brep': {'sha256': 'ec8f3d870f052891b0171779029909113f3ffb428f449c041613a6d4a00550e7', 'bytes': 1085}, 'control-reversed-whole-carrier.brep': {'sha256': 'd189c628bf2f1a7c71cf72dc1e730fb4e937ffca6b59ed9ac89c254b3068c0ca', 'bytes': 6522}, 'control-tiny-capsule-short-disk.brep': {'sha256': '7cff77f0680571d63f01cf1fc120f5a15be684fddc32eea64a0e9f6a019ef1aa', 'bytes': 1204}, 'control-tiny-source-disk.brep': {'sha256': '46c0f5d0e649c46166be55151950991c0694d28685ce7a64a356129d8213c8bb', 'bytes': 1108}, 'control-tiny-whole-carrier.brep': {'sha256': '7cff77f0680571d63f01cf1fc120f5a15be684fddc32eea64a0e9f6a019ef1aa', 'bytes': 1204}, 'control-zero-capsule-short-disk.brep': {'sha256': '46c0f5d0e649c46166be55151950991c0694d28685ce7a64a356129d8213c8bb', 'bytes': 1108}, 'control-zero-source-disk.brep': {'sha256': '46c0f5d0e649c46166be55151950991c0694d28685ce7a64a356129d8213c8bb', 'bytes': 1108}, 'control-zero-whole-carrier.brep': {'sha256': '46c0f5d0e649c46166be55151950991c0694d28685ce7a64a356129d8213c8bb', 'bytes': 1108}, 'l5-CONTROLLER_OUTCOME.json': {'sha256': '7a371d85af506af07483955e8b4f9024cedf017945e4cff93e021481d8f5e408', 'bytes': 911}, 'native-reader-CONTROLLER_OUTCOME.json': {'sha256': '06042f8a9ffcf475b52f0e944cf23e57a57a2fe973d41bc877b7082d713bad72', 'bytes': 910}, 'report.json': {'sha256': '737be50b0ee34502bc16f02ae050a0eccc1beada36aa879f004327b8331b269e', 'bytes': 141771}, 'source-K1_BINDING.json': {'sha256': 'cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be', 'bytes': 3914}, 'source-L5_ORIGINAL_SEVEN_BINDING.json': {'sha256': '7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2', 'bytes': 39348}, 'source-capacity_stage_v4.py': {'sha256': '7aa792c027ca824440c7fa61bb9c39e678a45380ca69485e5335eb0aac3c8e14', 'bytes': 15054}, 'source-check_l5_plan.py': {'sha256': 'e82a6d91fc0658ebc8cc708bff5a9474a3a5b00af5b974181231041d75d3efc9', 'bytes': 3728}, 'source-correlated_v3.py': {'sha256': '2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2', 'bytes': 14583}, 'source-cylindrical_sweep_l5.py': {'sha256': '433b9f89f34ffca28123d767f02ae81572e68d282e95f020a600b1b31aa1d949', 'bytes': 23268}, 'source-envelope_v2.py': {'sha256': '807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc', 'bytes': 11001}, 'source-exact_xy_support_l5.py': {'sha256': 'd1e113d1e61051d7fcee9d0d65c591da1f4a83c811ee3dc2e34226c6cc7d4369', 'bytes': 7117}, 'source-export_l5.py': {'sha256': '75d21a7e1b014877b6bae822ba8adec264a10ce220f1a1f6aefe50f9eb0bf7d7', 'bytes': 7190}, 'source-frozen_key_factory_adapter.py': {'sha256': 'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6', 'bytes': 8189}, 'source-full_slide_api_v4.py': {'sha256': '698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64', 'bytes': 13596}, 'source-l5_science_contract.py': {'sha256': 'd69f87ad8c894018a03c27451d38cefb569a4a31fddd579165a285e701b79967', 'bytes': 8220}, 'source-read_l5_native.py': {'sha256': '29790e254aea6ebdf90400121531824aebce8fe108dab302dc3af4a57c7cf548', 'bytes': 14765}, 'source-read_l5_records.py': {'sha256': '00fe744fc9cb8751b11806b33ba1deacd58709c28092ec315844daa900aab40a', 'bytes': 7891}, 'source-run_l5.py': {'sha256': 'c17c812f90a19ca98e37e99056c78607b57872adcb13aa52b4904d3086e62e12', 'bytes': 17573}, 'source-supervise_l5.py': {'sha256': '5cdb452e4cb14313e65767d292e0434908da830bbc4a4dadf50ec1b6d94762f4', 'bytes': 8452}, 'source-test_export_l5.py': {'sha256': '81c6ae57954c3d05a487ff3512f68f78cd792fc3c9f7247f476fbb71618ddc74', 'bytes': 5453}, 'source-test_l2_native.py': {'sha256': '39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318', 'bytes': 1910}, 'source-test_l5_native.py': {'sha256': 'c3b09e50c3083142678dce5add1a3f93837692818e8b6dbfe9f7dc1420b0d723', 'bytes': 5236}}, 'source_producer_sha256': '737be50b0ee34502bc16f02ae050a0eccc1beada36aa879f004327b8331b269e', 'source_native_reader_sha256': '3a2f267cbacc60b56d7389e43db6d2a80c17c261e2398aba6ba3853c1e11770d', 'operands': {'original-whole-brep': {'path': 'control-original-extrusion-original-shape.brep', 'bytes': 9378, 'sha256': 'f48d4f4a188fc7b85e0d5a89082134de47bfa83b5e4169c75de639ee1eb0d5a8'}, 'original-whole-step': {'path': 'control-original-extrusion-original-shape.step', 'bytes': 31982, 'sha256': 'b2315f536a5146ec6ad14d9ee296c6d8a28f3d0da21d0d6af147d956efcbc1ce'}, 'original-face-brep': {'path': 'control-original-extrusion-original-face.brep', 'bytes': 2086, 'sha256': 'ad4c3a9dce88d8f4fc37f507461907edbc0e97468639f1ce973f0ec9f738e36e'}, 'original-face-step': {'path': 'control-original-extrusion-original-face.step', 'bytes': 5089, 'sha256': '2757f836bf065837e34062563d12c1b8bb84e2ed57453536373c95b7c022eb4a'}}, 'saved_V2_regions': [{'path': 'control-original-extrusion-v2-region-0.brep', 'bytes': 9378, 'sha256': '8c5ccf1475719375dbce201d0f5ef809db4fb3dc8a9d74ff62f91c336e2fabad', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 4.453452962600495e-10, 'solid_signed_volumes_mm3': [4.453452962600495e-10], 'positive_whole_material_passed': True, 'bounds_mm': [-4.195366740711009, 20.030338588443, 1.1004367534338555, 162.1004367534357, 8.066666666666666, 12.566666666666666]}}, {'path': 'control-original-extrusion-v2-region-1.brep', 'bytes': 8252, 'sha256': 'aed40e139549231ebdb923eabd8a0f3c509c4158dda552a2d954f6bf961caf45', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 4.4532222655781633e-10, 'solid_signed_volumes_mm3': [4.4532222655781633e-10], 'positive_whole_material_passed': True, 'bounds_mm': [-4.195366740711009, 20.030338588443, 1.1004367534338555, 162.1004367534357, 8.266666666666666, 12.766666666666666]}}, {'path': 'control-original-extrusion-v2-region-2.brep', 'bytes': 4512, 'sha256': '3139cf6ee76f11a873e9483aaf37539e2525bd9d14b7653b8d386a77bdcc3cc7', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 262.27066097970607, 'solid_signed_volumes_mm3': [262.27066097970607], 'positive_whole_material_passed': True, 'bounds_mm': [5.983999222501991, 20.030348688443006, 1.1004266534338552, 94.45001010000023, 12.166656566666665, 12.366676766666666]}}, {'path': 'control-original-extrusion-v2-region-3.brep', 'bytes': 4832, 'sha256': 'f6297753f611850138d36f7f2b721e4806cc03093af1e4016801753eb649e6a2', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 0.0009774841019270786, 'solid_signed_volumes_mm3': [0.0009774841019270786], 'positive_whole_material_passed': True, 'bounds_mm': [8.03032709804441, 20.030350078841582, 1.1004252630354046, 80.85044824383264, 12.166656566666665, 12.766676766666667]}}, {'path': 'control-original-extrusion-v2-region-4.brep', 'bytes': 4499, 'sha256': '7576946f6ec42eef503580183799263d8913f3b1ba77627c69ef1daa73509ffd', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 265.93579448462305, 'solid_signed_volumes_mm3': [265.93579448462305], 'positive_whole_material_passed': True, 'bounds_mm': [5.886193579868989, 20.030348688443006, 1.1004266534339997, 95.10001010000029, 12.566656566666666, 12.766676766666667]}}, {'path': 'control-original-extrusion-v2-region-5.brep', 'bytes': 4556, 'sha256': 'fec9264564d033a7523eba749e7f1464521511f9b51b56131a09e3e859e128b3', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 0.0065978284686727335, 'solid_signed_volumes_mm3': [0.0065978284686727335], 'positive_whole_material_passed': True, 'bounds_mm': [5.8861921894704095, 17.88621517026758, 15.349988509601403, 95.10001149039864, 8.716656566666666, 12.766676766666668]}}, {'path': 'control-original-extrusion-v2-region-6.brep', 'bytes': 4508, 'sha256': 'a8d89327f005ab898cca343651c120acfd7c5bab2304b8d0b9a9df1ee5d488ff', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 648.1621605327534, 'solid_signed_volumes_mm3': [648.1621605327534], 'positive_whole_material_passed': True, 'bounds_mm': [-4.19537684071101, 17.886213779869276, 15.349989899999999, 162.10044685343567, 8.716656566666666, 8.916676766666667]}}, {'path': 'control-original-extrusion-v2-region-7.brep', 'bytes': 4895, 'sha256': '20983b339b49661ae1493c167529bf479d535872448cc2e799815e035987239f', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 0.0013847554329265693, 'solid_signed_volumes_mm3': [0.0013847554329265693], 'positive_whole_material_passed': True, 'bounds_mm': [-4.195378231109592, 7.804644749687583, 82.35042526303539, 162.10044824383263, 8.066656566666666, 8.916676766666667]}}, {'path': 'control-original-extrusion-v2-region-8.brep', 'bytes': 4521, 'sha256': '7509720b56bc1c3b28a1f8ab107ef2cf96a25a3af8d75229a372052a933f5275', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 653.9166677433104, 'solid_signed_volumes_mm3': [653.9166677433104], 'positive_whole_material_passed': True, 'bounds_mm': [-4.19537684071101, 17.98401942250238, 14.699989899999998, 162.10044685343573, 8.066656566666666, 8.266676766666667]}}, {'path': 'control-original-extrusion-v2-region-9.brep', 'bytes': 4636, 'sha256': '58b1b5db3808318a704f66aba7a66dba49349fc174fcae1b98a9511b3483b8b0', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 0.0070050997995890155, 'solid_signed_volumes_mm3': [0.0070050997995890155], 'positive_whole_material_passed': True, 'bounds_mm': [5.98399783210341, 17.98402081290058, 14.699988509601397, 94.45001149039864, 8.066656566666666, 12.366676766666666]}}, {'path': 'control-original-extrusion-v2-region-10.brep', 'bytes': 4817, 'sha256': 'ad78ef2681f0c628833a419807b9dba10f93df67bca57531b21d6c92ef890176', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 0.007800752669214943, 'solid_signed_volumes_mm3': [0.007800752669214943], 'positive_whole_material_passed': True, 'bounds_mm': [7.804621768890414, 20.030350078841586, 1.1004252630334932, 82.35044824383455, 8.066656566666666, 12.766676766666667]}}, {'path': 'control-original-extrusion-v2-region-11.brep', 'bytes': 4805, 'sha256': '2d3b5737046c85392c4c5db88f3d8e958d725c02344a54d9b6d04f544a563c86', 'producer_signature': {'shape_type': 'Solid', 'is_valid': True, 'signed_volume_mm3': 0.007800752666552732, 'solid_signed_volumes_mm3': [0.007800752666552732], 'positive_whole_material_passed': True, 'bounds_mm': [-4.195378231109583, 8.030350078841582, 80.85042526303349, 162.10044824383453, 8.066656566666666, 12.766676766666667]}}], 'original_vector_xyz': [0.0, 0.0, 0.2], 'direct_parameters': [0.0, 0.25], 'traced_parameter': 0.25, 'original_region_cap': 4096, 'observed_retained_region_count': 12, 'original_L5b_pair_calls': 0, 'original_failure_type': 'ValueError', 'original_failure_report_or_source_modified': False}}, 'L5d': {'EXPORT_SCOPE.json': {'schema': 'razr-L5d-narrow-scientific-export-v1', 'raw_runtime_exported': False, 'raw_private_runtime_preservation_claimed': False, 'rejected_items': [], 'failed_original_operations_not_reclassified': True, 'original_seven_reexecuted': False, 'old_failed_STEP_originals_not_replaced': True, 'null_result_not_replaced_by_empty': True, 'complete_product_qualification': False}, 'L5_SOURCE_IDENTITY.json': {'run_l5.py': {'sha256': 'c17c812f90a19ca98e37e99056c78607b57872adcb13aa52b4904d3086e62e12', 'bytes': 17573}, 'supervise_l5.py': {'sha256': '5cdb452e4cb14313e65767d292e0434908da830bbc4a4dadf50ec1b6d94762f4', 'bytes': 8452}, 'cylindrical_sweep_l5.py': {'sha256': '433b9f89f34ffca28123d767f02ae81572e68d282e95f020a600b1b31aa1d949', 'bytes': 23268}, 'exact_xy_support_l5.py': {'sha256': 'd1e113d1e61051d7fcee9d0d65c591da1f4a83c811ee3dc2e34226c6cc7d4369', 'bytes': 7117}, 'test_l5_native.py': {'sha256': 'c3b09e50c3083142678dce5add1a3f93837692818e8b6dbfe9f7dc1420b0d723', 'bytes': 5236}, 'check_l5_plan.py': {'sha256': 'e82a6d91fc0658ebc8cc708bff5a9474a3a5b00af5b974181231041d75d3efc9', 'bytes': 3728}, 'l5_science_contract.py': {'sha256': 'd69f87ad8c894018a03c27451d38cefb569a4a31fddd579165a285e701b79967', 'bytes': 8220}, 'read_l5_native.py': {'sha256': '29790e254aea6ebdf90400121531824aebce8fe108dab302dc3af4a57c7cf548', 'bytes': 14765}, 'read_l5_records.py': {'sha256': '00fe744fc9cb8751b11806b33ba1deacd58709c28092ec315844daa900aab40a', 'bytes': 7891}, 'export_l5.py': {'sha256': '75d21a7e1b014877b6bae822ba8adec264a10ce220f1a1f6aefe50f9eb0bf7d7', 'bytes': 7190}, 'test_export_l5.py': {'sha256': '81c6ae57954c3d05a487ff3512f68f78cd792fc3c9f7247f476fbb71618ddc74', 'bytes': 5453}, 'capacity_stage_v4.py': {'sha256': '7aa792c027ca824440c7fa61bb9c39e678a45380ca69485e5335eb0aac3c8e14', 'bytes': 15054}, 'full_slide_api_v4.py': {'sha256': '698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64', 'bytes': 13596}, 'envelope_v2.py': {'sha256': '807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc', 'bytes': 11001}, 'correlated_v3.py': {'sha256': '2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2', 'bytes': 14583}, 'test_l2_native.py': {'sha256': '39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318', 'bytes': 1910}, 'frozen_key_factory_adapter.py': {'sha256': 'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6', 'bytes': 8189}, 'K1_BINDING.json': {'sha256': 'cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be', 'bytes': 3914}, 'L5_ORIGINAL_SEVEN_BINDING.json': {'sha256': '7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2', 'bytes': 39348}, 'README.md': {'sha256': '02176d24c635cb806ece05daa61b01a97589c9f82b223ccd3406c0b62eaf5fee', 'bytes': 4132}, 'L5_METHOD_AND_CAPACITY_PLAN.md': {'sha256': '6464057058016f123b5789033a7f2ae27f453908412499110e79e1987d72be57', 'bytes': 12034}}, 'L5D_SOURCE_IDENTITY.json': {'schema': 'razr-L5d-frozen-diagnostic-source-byte-check-v1', 'sources': {'run_l5d.py': {'bytes': 26207, 'sha256': 'b205ed726ead19c194ea5971374a9936e7ea327c57ab7959b30a0e474bf90928'}, 'supervise_l5d.py': {'bytes': 8421, 'sha256': 'c490bc92ed16a877c7deec371beb0f16dd266463d297ae8940f14738fe1e37ba'}, 'export_l5d.py': {'bytes': 5214, 'sha256': '123f47d7365d30064f718790a6c3d8ac9a603eb55441ec2804f9e2b4bd698bd4'}, 'L5D_INPUT_BINDING.json': {'bytes': 11587, 'sha256': '3c5053b480482b2c47a90128e7e7a9737bd45c8ae7dce19ddbbab14263046f96'}, 'L5D_CAPACITY_PREREGISTRATION.json': {'bytes': 1924, 'sha256': '820ab8a220450247797463deeb8421d8ed293f77b111b071dc2c86618450e7c3'}}, 'parent_L5c_workflow_commit': 'f544f33c563ef4a44e8baa38c3e1225ad6e60b9e', 'unchanged_original_19_scientific_sources': True, 'new_native_execution': False}, 'source-L5D_INPUT_BINDING.json': {'schema': 'razr-L5d-frozen-L5c-null-Boolean-input-v1', 'source_workflow_commit': 'f544f33c563ef4a44e8baa38c3e1225ad6e60b9e', 'source_run_id': 40468054101, 'source_run_attempt': 1, 'source_artifact_id': 12717347119, 'source_artifact_name': 'S4-L5c-diagnostic-40468054101-1', 'source_zip_bytes': 128633, 'source_zip_sha256': '71f96228c6f8f5e3cbcb5ddb1f44d76ecb3cbf635bcd6e71eac7ba4c36aaa49a', 'source_manifest_bytes': 7492, 'source_manifest_sha256': 'd11e04632249bc02fd7d5975c573b1175d8339cb81ccdcc7ca925d782e5f1a07', 'source_manifest_entries': 52, 'source_regular_file_count': 53, 'source_manifest': {'EXPORT_SCOPE.json': {'sha256': 'dc5bb3f5976fcf29f6b164d91e65a0fddd93fcbc55c075711308dbea2573f405', 'bytes': 301}, 'L5C_CONTROLLER_OUTCOME.json': {'sha256': '612e7dc9529b5f36df57ef08bb82276167df5066d9eedff4d1cef71315e67cd9', 'bytes': 925}, 'L5C_INPUT_VERIFIED.json': {'sha256': 'acd3049c42031e0f6ce72a026ee1af2e37a3db0e74fe457656b76d868c772caf', 'bytes': 734}, 'L5C_SOURCE_IDENTITY.json': {'sha256': 'b2edf5a55f1792a3089c02265bd0c977f36016e7897f5426a57484c737edaa74', 'bytes': 944}, 'L5_SOURCE_IDENTITY.json': {'sha256': '211f04f27a2ccadc69ced687ce105ee7d8c19929e3a93deeea17727ab15df2f1', 'bytes': 2773}, 'control-original-extrusion-original-face.brep': {'sha256': 'ad4c3a9dce88d8f4fc37f507461907edbc0e97468639f1ce973f0ec9f738e36e', 'bytes': 2086}, 'control-original-extrusion-original-face.step': {'sha256': '2757f836bf065837e34062563d12c1b8bb84e2ed57453536373c95b7c022eb4a', 'bytes': 5089}, 'control-original-extrusion-original-shape.brep': {'sha256': 'f48d4f4a188fc7b85e0d5a89082134de47bfa83b5e4169c75de639ee1eb0d5a8', 'bytes': 9378}, 'control-original-extrusion-original-shape.step': {'sha256': 'b2315f536a5146ec6ad14d9ee296c6d8a28f3d0da21d0d6af147d956efcbc1ce', 'bytes': 31982}, 'control-original-extrusion-v2-region-0.brep': {'sha256': '8c5ccf1475719375dbce201d0f5ef809db4fb3dc8a9d74ff62f91c336e2fabad', 'bytes': 9378}, 'control-original-extrusion-v2-region-1.brep': {'sha256': 'aed40e139549231ebdb923eabd8a0f3c509c4158dda552a2d954f6bf961caf45', 'bytes': 8252}, 'control-original-extrusion-v2-region-10.brep': {'sha256': 'ad78ef2681f0c628833a419807b9dba10f93df67bca57531b21d6c92ef890176', 'bytes': 4817}, 'control-original-extrusion-v2-region-11.brep': {'sha256': '2d3b5737046c85392c4c5db88f3d8e958d725c02344a54d9b6d04f544a563c86', 'bytes': 4805}, 'control-original-extrusion-v2-region-2.brep': {'sha256': '3139cf6ee76f11a873e9483aaf37539e2525bd9d14b7653b8d386a77bdcc3cc7', 'bytes': 4512}, 'control-original-extrusion-v2-region-3.brep': {'sha256': 'f6297753f611850138d36f7f2b721e4806cc03093af1e4016801753eb649e6a2', 'bytes': 4832}, 'control-original-extrusion-v2-region-4.brep': {'sha256': '7576946f6ec42eef503580183799263d8913f3b1ba77627c69ef1daa73509ffd', 'bytes': 4499}, 'control-original-extrusion-v2-region-5.brep': {'sha256': 'fec9264564d033a7523eba749e7f1464521511f9b51b56131a09e3e859e128b3', 'bytes': 4556}, 'control-original-extrusion-v2-region-6.brep': {'sha256': 'a8d89327f005ab898cca343651c120acfd7c5bab2304b8d0b9a9df1ee5d488ff', 'bytes': 4508}, 'control-original-extrusion-v2-region-7.brep': {'sha256': '20983b339b49661ae1493c167529bf479d535872448cc2e799815e035987239f', 'bytes': 4895}, 'control-original-extrusion-v2-region-8.brep': {'sha256': '7509720b56bc1c3b28a1f8ab107ef2cf96a25a3af8d75229a372052a933f5275', 'bytes': 4521}, 'control-original-extrusion-v2-region-9.brep': {'sha256': '58b1b5db3808318a704f66aba7a66dba49349fc174fcae1b98a9511b3483b8b0', 'bytes': 4636}, 'report.json': {'sha256': '7ed716e0abd918b977fca1cbaa270c0e4873dc88e8d626397203c9c5e40b82fb', 'bytes': 44715}, 'source-K1_BINDING.json': {'sha256': 'cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be', 'bytes': 3914}, 'source-L5C_CAPACITY_PREREGISTRATION.json': {'sha256': '5f6d44f507cb925907e71c194719f7e376240a2544b01354d02fca83776d08ba', 'bytes': 2201}, 'source-L5C_INPUT_BINDING.json': {'sha256': 'a06aed5fc76b5a7bc5c538eb1920802b14594fa63cb36b171b3fcebbac12d173', 'bytes': 20527}, 'source-L5_ORIGINAL_SEVEN_BINDING.json': {'sha256': '7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2', 'bytes': 39348}, 'source-capacity_stage_v4.py': {'sha256': '7aa792c027ca824440c7fa61bb9c39e678a45380ca69485e5335eb0aac3c8e14', 'bytes': 15054}, 'source-check_l5_plan.py': {'sha256': 'e82a6d91fc0658ebc8cc708bff5a9474a3a5b00af5b974181231041d75d3efc9', 'bytes': 3728}, 'source-correlated_v3.py': {'sha256': '2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2', 'bytes': 14583}, 'source-cylindrical_sweep_l5.py': {'sha256': '433b9f89f34ffca28123d767f02ae81572e68d282e95f020a600b1b31aa1d949', 'bytes': 23268}, 'source-envelope_v2.py': {'sha256': '807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc', 'bytes': 11001}, 'source-exact_xy_support_l5.py': {'sha256': 'd1e113d1e61051d7fcee9d0d65c591da1f4a83c811ee3dc2e34226c6cc7d4369', 'bytes': 7117}, 'source-export_l5.py': {'sha256': '75d21a7e1b014877b6bae822ba8adec264a10ce220f1a1f6aefe50f9eb0bf7d7', 'bytes': 7190}, 'source-export_l5c.py': {'sha256': 'ece630d25ff54bf50031b38210c0db7ee1abd124140ef72fe56c5ef1ed621b25', 'bytes': 4470}, 'source-frozen_key_factory_adapter.py': {'sha256': 'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6', 'bytes': 8189}, 'source-full_slide_api_v4.py': {'sha256': '698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64', 'bytes': 13596}, 'source-l5_science_contract.py': {'sha256': 'd69f87ad8c894018a03c27451d38cefb569a4a31fddd579165a285e701b79967', 'bytes': 8220}, 'source-read_l5_native.py': {'sha256': '29790e254aea6ebdf90400121531824aebce8fe108dab302dc3af4a57c7cf548', 'bytes': 14765}, 'source-read_l5_records.py': {'sha256': '00fe744fc9cb8751b11806b33ba1deacd58709c28092ec315844daa900aab40a', 'bytes': 7891}, 'source-run_l5.py': {'sha256': 'c17c812f90a19ca98e37e99056c78607b57872adcb13aa52b4904d3086e62e12', 'bytes': 17573}, 'source-run_l5c.py': {'sha256': '6754946bb1e41df130841834e21c6a1ea7c1c30ce197c6224a657d7eb8c35f01', 'bytes': 22038}, 'source-supervise_l5.py': {'sha256': '5cdb452e4cb14313e65767d292e0434908da830bbc4a4dadf50ec1b6d94762f4', 'bytes': 8452}, 'source-supervise_l5c.py': {'sha256': 'e2bc7998cc46ab751804c6b5c2f42d8a88b3c0273c12cf4e40a8341dd9e66910', 'bytes': 8421}, 'source-test_export_l5.py': {'sha256': '81c6ae57954c3d05a487ff3512f68f78cd792fc3c9f7247f476fbb71618ddc74', 'bytes': 5453}, 'source-test_l2_native.py': {'sha256': '39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318', 'bytes': 1910}, 'source-test_l5_native.py': {'sha256': 'c3b09e50c3083142678dce5add1a3f93837692818e8b6dbfe9f7dc1420b0d723', 'bytes': 5236}, 'step-original-face-step-root-0.brep': {'sha256': 'f61c12634156eb8d5632b80da4058fdaf537bb248995b689d28f64e0669f43f1', 'bytes': 188}, 'step-original-whole-step-root-0.brep': {'sha256': '36d6e48a97bccfd2dae33ee1ab1e31354ca85f4de1548d07cdac00ab22ad90a8', 'bytes': 6556}, 't000-original-subtract-result.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 't000-translated.brep': {'sha256': '1736197846dbfbbe17fad4b5e7bbd7d3b8ace06af2add6f65e3e4a5f78b73125', 'bytes': 8258}, 't025-translated.brep': {'sha256': 'a30ff27ca9731f4553ed11cd4332d5525cf553e7a43d152d77dc40f8319ce094', 'bytes': 8258}, 'trace-t025-translated.brep': {'sha256': 'a30ff27ca9731f4553ed11cd4332d5525cf553e7a43d152d77dc40f8319ce094', 'bytes': 8258}}, 'preserved_originals': [{'input_path': 'control-original-extrusion-original-shape.brep', 'output_path': 'control-original-extrusion-original-shape.brep', 'sha256': 'f48d4f4a188fc7b85e0d5a89082134de47bfa83b5e4169c75de639ee1eb0d5a8', 'bytes': 9378}, {'input_path': 'control-original-extrusion-original-face.brep', 'output_path': 'control-original-extrusion-original-face.brep', 'sha256': 'ad4c3a9dce88d8f4fc37f507461907edbc0e97468639f1ce973f0ec9f738e36e', 'bytes': 2086}, {'input_path': 'control-original-extrusion-original-shape.step', 'output_path': 'control-original-extrusion-original-shape.step', 'sha256': 'b2315f536a5146ec6ad14d9ee296c6d8a28f3d0da21d0d6af147d956efcbc1ce', 'bytes': 31982}, {'input_path': 'control-original-extrusion-original-face.step', 'output_path': 'control-original-extrusion-original-face.step', 'sha256': '2757f836bf065837e34062563d12c1b8bb84e2ed57453536373c95b7c022eb4a', 'bytes': 5089}, {'input_path': 'step-original-whole-step-root-0.brep', 'output_path': 'step-original-whole-step-root-0.brep', 'sha256': '36d6e48a97bccfd2dae33ee1ab1e31354ca85f4de1548d07cdac00ab22ad90a8', 'bytes': 6556}, {'input_path': 'step-original-face-step-root-0.brep', 'output_path': 'step-original-face-step-root-0.brep', 'sha256': 'f61c12634156eb8d5632b80da4058fdaf537bb248995b689d28f64e0669f43f1', 'bytes': 188}, {'input_path': 't025-translated.brep', 'output_path': 't025-translated.brep', 'sha256': 'a30ff27ca9731f4553ed11cd4332d5525cf553e7a43d152d77dc40f8319ce094', 'bytes': 8258}, {'input_path': 'control-original-extrusion-v2-region-0.brep', 'output_path': 'control-original-extrusion-v2-region-0.brep', 'sha256': '8c5ccf1475719375dbce201d0f5ef809db4fb3dc8a9d74ff62f91c336e2fabad', 'bytes': 9378}, {'input_path': 'report.json', 'output_path': 'original-L5c-report.json', 'sha256': '7ed716e0abd918b977fca1cbaa270c0e4873dc88e8d626397203c9c5e40b82fb', 'bytes': 44715}], 'actual_cut_operands': {'a': 't025-translated.brep', 'b': 'control-original-extrusion-v2-region-0.brep'}, 'actual_expected_CadQuery_null_constant': {'public_source_literal': 'Null TopoDS_Shape object', 'utf8_bytes': 24, 'sha256': '6ec2e46348dbe80afad13cbcb89fd614c1d61a7905475c9e817ca619cd0b3d5c', 'locked_shapes_source_sha256': '48331311a0e6de8dc324c3bf76e4ed3c3769f47d007a0243ac25f454cc22bb47', 'official_source_URL': 'https://raw.githubusercontent.com/CadQuery/cadquery/v2.7.0/cadquery/occ_impl/shapes.py'}, 'original_two_STEP_failures_retained_not_reclassified': True, 'original_pair_volume_gate_mm3': 1e-07, 'maximum_boolean_build_calls': 6, 'actual_native_predecessor_seconds': 4.1149082919999955, 'actual_native_predecessor_peak_RSS_bytes': 517107712, 'full_domain_or_pair_qualification': False}}}


class L5DiagnosticTypedControls(unittest.TestCase):
    def fixture(self,family):
        p={n:json.dumps(d).encode() for n,d in L5_DIAGNOSTIC_FIXTURES[family].items()}
        upper=family.upper()
        binding=json.loads(p["source-"+upper+"_INPUT_BINDING.json"])
        identity=json.loads(p[upper+"_SOURCE_IDENTITY.json"])
        e={n:{"bytes":len(d),"sha256":hashlib.sha256(d).hexdigest()} for n,d in p.items()}
        e.update({"source-"+n:binding["source_manifest"]["source-"+n] for n in MOD.L5_CONTROL_SOURCE_NAMES})
        e.update({"source-"+n:d for n,d in identity["sources"].items()})
        p["report.json"]=b'{"completed":false}'
        e["report.json"]={"bytes":len(p["report.json"]),"sha256":hashlib.sha256(p["report.json"]).hexdigest()}
        return p,e

    def check(self,p,e,family):
        class Reader:
            def read(self,n):return p[n]
        return MOD.verify_l5_diagnostic_scope(Reader(),e,family)

    def test_failed_partial_geometric_material_is_preserved(self):
        for family in ("L5c","L5d"):
            p,e=self.fixture(family)
            r=self.check(p,e,family)
            self.assertFalse(r["qualification_required"])
            self.assertGreater(len(r["missing_predecessor_originals"]),0)

    def test_diagnostic_source_identity_tamper_rejected(self):
        for family in ("L5c","L5d"):
            p,e=self.fixture(family);e["source-run_"+family.lower()+".py"]={"bytes":1,"sha256":"0"*64}
            with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e,family)

    def test_diagnostic_runtime_or_null_reclassification_rejected(self):
        for family in ("L5c","L5d"):
            p,e=self.fixture(family);s=json.loads(p["EXPORT_SCOPE.json"]);s["raw_runtime_exported"]=True
            p["EXPORT_SCOPE.json"]=json.dumps(s).encode()
            with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e,family)
        p,e=self.fixture("L5d");s=json.loads(p["EXPORT_SCOPE.json"]);s["null_result_not_replaced_by_empty"]=False
        p["EXPORT_SCOPE.json"]=json.dumps(s).encode()
        with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e,"L5d")

    def test_diagnostic_unlisted_runtime_filename_rejected(self):
        for family in ("L5c","L5d"):
            p,e=self.fixture(family);e["worker-runtime.json"]={"bytes":2,"sha256":"0"*64}
            with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e,family)

    def test_preserved_failed_STEP_cannot_be_replaced(self):
        for family in ("L5c","L5d"):
            p,e=self.fixture(family);e["control-original-extrusion-original-shape.step"]={"bytes":2,"sha256":"0"*64}
            with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e,family)



L5_DIAGNOSTIC_FIXTURES["L5d1"] = {'EXPORT_SCOPE.json': {'schema': 'razr-L5d1-narrow-scientific-export-v1', 'raw_runtime_exported': False, 'raw_private_runtime_preservation_claimed': False, 'rejected_items': [], 'failed_original_operations_not_reclassified': True, 'original_seven_reexecuted': False, 'old_failed_STEP_originals_not_replaced': True, 'null_result_not_replaced_by_empty': True, 'complete_product_qualification': False}, 'L5_SOURCE_IDENTITY.json': {'run_l5.py': {'sha256': 'c17c812f90a19ca98e37e99056c78607b57872adcb13aa52b4904d3086e62e12', 'bytes': 17573}, 'supervise_l5.py': {'sha256': '5cdb452e4cb14313e65767d292e0434908da830bbc4a4dadf50ec1b6d94762f4', 'bytes': 8452}, 'cylindrical_sweep_l5.py': {'sha256': '433b9f89f34ffca28123d767f02ae81572e68d282e95f020a600b1b31aa1d949', 'bytes': 23268}, 'exact_xy_support_l5.py': {'sha256': 'd1e113d1e61051d7fcee9d0d65c591da1f4a83c811ee3dc2e34226c6cc7d4369', 'bytes': 7117}, 'test_l5_native.py': {'sha256': 'c3b09e50c3083142678dce5add1a3f93837692818e8b6dbfe9f7dc1420b0d723', 'bytes': 5236}, 'check_l5_plan.py': {'sha256': 'e82a6d91fc0658ebc8cc708bff5a9474a3a5b00af5b974181231041d75d3efc9', 'bytes': 3728}, 'l5_science_contract.py': {'sha256': 'd69f87ad8c894018a03c27451d38cefb569a4a31fddd579165a285e701b79967', 'bytes': 8220}, 'read_l5_native.py': {'sha256': '29790e254aea6ebdf90400121531824aebce8fe108dab302dc3af4a57c7cf548', 'bytes': 14765}, 'read_l5_records.py': {'sha256': '00fe744fc9cb8751b11806b33ba1deacd58709c28092ec315844daa900aab40a', 'bytes': 7891}, 'export_l5.py': {'sha256': '75d21a7e1b014877b6bae822ba8adec264a10ce220f1a1f6aefe50f9eb0bf7d7', 'bytes': 7190}, 'test_export_l5.py': {'sha256': '81c6ae57954c3d05a487ff3512f68f78cd792fc3c9f7247f476fbb71618ddc74', 'bytes': 5453}, 'capacity_stage_v4.py': {'sha256': '7aa792c027ca824440c7fa61bb9c39e678a45380ca69485e5335eb0aac3c8e14', 'bytes': 15054}, 'full_slide_api_v4.py': {'sha256': '698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64', 'bytes': 13596}, 'envelope_v2.py': {'sha256': '807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc', 'bytes': 11001}, 'correlated_v3.py': {'sha256': '2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2', 'bytes': 14583}, 'test_l2_native.py': {'sha256': '39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318', 'bytes': 1910}, 'frozen_key_factory_adapter.py': {'sha256': 'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6', 'bytes': 8189}, 'K1_BINDING.json': {'sha256': 'cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be', 'bytes': 3914}, 'L5_ORIGINAL_SEVEN_BINDING.json': {'sha256': '7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2', 'bytes': 39348}, 'README.md': {'sha256': '02176d24c635cb806ece05daa61b01a97589c9f82b223ccd3406c0b62eaf5fee', 'bytes': 4132}, 'L5_METHOD_AND_CAPACITY_PLAN.md': {'sha256': '6464057058016f123b5789033a7f2ae27f453908412499110e79e1987d72be57', 'bytes': 12034}}, 'L5D1_SOURCE_IDENTITY.json': {'schema': 'razr-L5d1-frozen-diagnostic-source-byte-check-v1', 'sources': {'run_l5d1.py': {'bytes': 30882, 'sha256': '7387a0747e369d5e860a2df9c49ef6d21eb09bd7f3f442e329f6365eaa41b15b'}, 'supervise_l5d1.py': {'bytes': 8425, 'sha256': 'db8acece9a762585a511c5c3c0f09119699346c0252342045906d5a8742ef457'}, 'export_l5d1.py': {'bytes': 5228, 'sha256': 'e3ea8f6ad6a3268f17fd8c35b569f8653ce8efabd51ce48d4a88799a5146a564'}, 'L5D1_INPUT_BINDING.json': {'bytes': 11587, 'sha256': '3c5053b480482b2c47a90128e7e7a9737bd45c8ae7dce19ddbbab14263046f96'}, 'L5D1_CAPACITY_PREREGISTRATION.json': {'bytes': 3164, 'sha256': '609862b9e7e32d3ca6db200e37bf4d12e819b08020de8494411ced946b903627'}}, 'parent_L5d_workflow_commit': '40a4357903b63051578940d14ff8ee6426c04388', 'unchanged_original_19_scientific_sources': True, 'new_native_execution': False}, 'source-L5D1_INPUT_BINDING.json': {'schema': 'razr-L5d-frozen-L5c-null-Boolean-input-v1', 'source_workflow_commit': 'f544f33c563ef4a44e8baa38c3e1225ad6e60b9e', 'source_run_id': 40468054101, 'source_run_attempt': 1, 'source_artifact_id': 12717347119, 'source_artifact_name': 'S4-L5c-diagnostic-40468054101-1', 'source_zip_bytes': 128633, 'source_zip_sha256': '71f96228c6f8f5e3cbcb5ddb1f44d76ecb3cbf635bcd6e71eac7ba4c36aaa49a', 'source_manifest_bytes': 7492, 'source_manifest_sha256': 'd11e04632249bc02fd7d5975c573b1175d8339cb81ccdcc7ca925d782e5f1a07', 'source_manifest_entries': 52, 'source_regular_file_count': 53, 'source_manifest': {'EXPORT_SCOPE.json': {'sha256': 'dc5bb3f5976fcf29f6b164d91e65a0fddd93fcbc55c075711308dbea2573f405', 'bytes': 301}, 'L5C_CONTROLLER_OUTCOME.json': {'sha256': '612e7dc9529b5f36df57ef08bb82276167df5066d9eedff4d1cef71315e67cd9', 'bytes': 925}, 'L5C_INPUT_VERIFIED.json': {'sha256': 'acd3049c42031e0f6ce72a026ee1af2e37a3db0e74fe457656b76d868c772caf', 'bytes': 734}, 'L5C_SOURCE_IDENTITY.json': {'sha256': 'b2edf5a55f1792a3089c02265bd0c977f36016e7897f5426a57484c737edaa74', 'bytes': 944}, 'L5_SOURCE_IDENTITY.json': {'sha256': '211f04f27a2ccadc69ced687ce105ee7d8c19929e3a93deeea17727ab15df2f1', 'bytes': 2773}, 'control-original-extrusion-original-face.brep': {'sha256': 'ad4c3a9dce88d8f4fc37f507461907edbc0e97468639f1ce973f0ec9f738e36e', 'bytes': 2086}, 'control-original-extrusion-original-face.step': {'sha256': '2757f836bf065837e34062563d12c1b8bb84e2ed57453536373c95b7c022eb4a', 'bytes': 5089}, 'control-original-extrusion-original-shape.brep': {'sha256': 'f48d4f4a188fc7b85e0d5a89082134de47bfa83b5e4169c75de639ee1eb0d5a8', 'bytes': 9378}, 'control-original-extrusion-original-shape.step': {'sha256': 'b2315f536a5146ec6ad14d9ee296c6d8a28f3d0da21d0d6af147d956efcbc1ce', 'bytes': 31982}, 'control-original-extrusion-v2-region-0.brep': {'sha256': '8c5ccf1475719375dbce201d0f5ef809db4fb3dc8a9d74ff62f91c336e2fabad', 'bytes': 9378}, 'control-original-extrusion-v2-region-1.brep': {'sha256': 'aed40e139549231ebdb923eabd8a0f3c509c4158dda552a2d954f6bf961caf45', 'bytes': 8252}, 'control-original-extrusion-v2-region-10.brep': {'sha256': 'ad78ef2681f0c628833a419807b9dba10f93df67bca57531b21d6c92ef890176', 'bytes': 4817}, 'control-original-extrusion-v2-region-11.brep': {'sha256': '2d3b5737046c85392c4c5db88f3d8e958d725c02344a54d9b6d04f544a563c86', 'bytes': 4805}, 'control-original-extrusion-v2-region-2.brep': {'sha256': '3139cf6ee76f11a873e9483aaf37539e2525bd9d14b7653b8d386a77bdcc3cc7', 'bytes': 4512}, 'control-original-extrusion-v2-region-3.brep': {'sha256': 'f6297753f611850138d36f7f2b721e4806cc03093af1e4016801753eb649e6a2', 'bytes': 4832}, 'control-original-extrusion-v2-region-4.brep': {'sha256': '7576946f6ec42eef503580183799263d8913f3b1ba77627c69ef1daa73509ffd', 'bytes': 4499}, 'control-original-extrusion-v2-region-5.brep': {'sha256': 'fec9264564d033a7523eba749e7f1464521511f9b51b56131a09e3e859e128b3', 'bytes': 4556}, 'control-original-extrusion-v2-region-6.brep': {'sha256': 'a8d89327f005ab898cca343651c120acfd7c5bab2304b8d0b9a9df1ee5d488ff', 'bytes': 4508}, 'control-original-extrusion-v2-region-7.brep': {'sha256': '20983b339b49661ae1493c167529bf479d535872448cc2e799815e035987239f', 'bytes': 4895}, 'control-original-extrusion-v2-region-8.brep': {'sha256': '7509720b56bc1c3b28a1f8ab107ef2cf96a25a3af8d75229a372052a933f5275', 'bytes': 4521}, 'control-original-extrusion-v2-region-9.brep': {'sha256': '58b1b5db3808318a704f66aba7a66dba49349fc174fcae1b98a9511b3483b8b0', 'bytes': 4636}, 'report.json': {'sha256': '7ed716e0abd918b977fca1cbaa270c0e4873dc88e8d626397203c9c5e40b82fb', 'bytes': 44715}, 'source-K1_BINDING.json': {'sha256': 'cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be', 'bytes': 3914}, 'source-L5C_CAPACITY_PREREGISTRATION.json': {'sha256': '5f6d44f507cb925907e71c194719f7e376240a2544b01354d02fca83776d08ba', 'bytes': 2201}, 'source-L5C_INPUT_BINDING.json': {'sha256': 'a06aed5fc76b5a7bc5c538eb1920802b14594fa63cb36b171b3fcebbac12d173', 'bytes': 20527}, 'source-L5_ORIGINAL_SEVEN_BINDING.json': {'sha256': '7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2', 'bytes': 39348}, 'source-capacity_stage_v4.py': {'sha256': '7aa792c027ca824440c7fa61bb9c39e678a45380ca69485e5335eb0aac3c8e14', 'bytes': 15054}, 'source-check_l5_plan.py': {'sha256': 'e82a6d91fc0658ebc8cc708bff5a9474a3a5b00af5b974181231041d75d3efc9', 'bytes': 3728}, 'source-correlated_v3.py': {'sha256': '2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2', 'bytes': 14583}, 'source-cylindrical_sweep_l5.py': {'sha256': '433b9f89f34ffca28123d767f02ae81572e68d282e95f020a600b1b31aa1d949', 'bytes': 23268}, 'source-envelope_v2.py': {'sha256': '807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc', 'bytes': 11001}, 'source-exact_xy_support_l5.py': {'sha256': 'd1e113d1e61051d7fcee9d0d65c591da1f4a83c811ee3dc2e34226c6cc7d4369', 'bytes': 7117}, 'source-export_l5.py': {'sha256': '75d21a7e1b014877b6bae822ba8adec264a10ce220f1a1f6aefe50f9eb0bf7d7', 'bytes': 7190}, 'source-export_l5c.py': {'sha256': 'ece630d25ff54bf50031b38210c0db7ee1abd124140ef72fe56c5ef1ed621b25', 'bytes': 4470}, 'source-frozen_key_factory_adapter.py': {'sha256': 'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6', 'bytes': 8189}, 'source-full_slide_api_v4.py': {'sha256': '698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64', 'bytes': 13596}, 'source-l5_science_contract.py': {'sha256': 'd69f87ad8c894018a03c27451d38cefb569a4a31fddd579165a285e701b79967', 'bytes': 8220}, 'source-read_l5_native.py': {'sha256': '29790e254aea6ebdf90400121531824aebce8fe108dab302dc3af4a57c7cf548', 'bytes': 14765}, 'source-read_l5_records.py': {'sha256': '00fe744fc9cb8751b11806b33ba1deacd58709c28092ec315844daa900aab40a', 'bytes': 7891}, 'source-run_l5.py': {'sha256': 'c17c812f90a19ca98e37e99056c78607b57872adcb13aa52b4904d3086e62e12', 'bytes': 17573}, 'source-run_l5c.py': {'sha256': '6754946bb1e41df130841834e21c6a1ea7c1c30ce197c6224a657d7eb8c35f01', 'bytes': 22038}, 'source-supervise_l5.py': {'sha256': '5cdb452e4cb14313e65767d292e0434908da830bbc4a4dadf50ec1b6d94762f4', 'bytes': 8452}, 'source-supervise_l5c.py': {'sha256': 'e2bc7998cc46ab751804c6b5c2f42d8a88b3c0273c12cf4e40a8341dd9e66910', 'bytes': 8421}, 'source-test_export_l5.py': {'sha256': '81c6ae57954c3d05a487ff3512f68f78cd792fc3c9f7247f476fbb71618ddc74', 'bytes': 5453}, 'source-test_l2_native.py': {'sha256': '39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318', 'bytes': 1910}, 'source-test_l5_native.py': {'sha256': 'c3b09e50c3083142678dce5add1a3f93837692818e8b6dbfe9f7dc1420b0d723', 'bytes': 5236}, 'step-original-face-step-root-0.brep': {'sha256': 'f61c12634156eb8d5632b80da4058fdaf537bb248995b689d28f64e0669f43f1', 'bytes': 188}, 'step-original-whole-step-root-0.brep': {'sha256': '36d6e48a97bccfd2dae33ee1ab1e31354ca85f4de1548d07cdac00ab22ad90a8', 'bytes': 6556}, 't000-original-subtract-result.brep': {'sha256': 'fdc75bfe05a54932b6580d63f4b6c2252e66e24302a5c754eeeb1b59d04840bc', 'bytes': 188}, 't000-translated.brep': {'sha256': '1736197846dbfbbe17fad4b5e7bbd7d3b8ace06af2add6f65e3e4a5f78b73125', 'bytes': 8258}, 't025-translated.brep': {'sha256': 'a30ff27ca9731f4553ed11cd4332d5525cf553e7a43d152d77dc40f8319ce094', 'bytes': 8258}, 'trace-t025-translated.brep': {'sha256': 'a30ff27ca9731f4553ed11cd4332d5525cf553e7a43d152d77dc40f8319ce094', 'bytes': 8258}}, 'preserved_originals': [{'input_path': 'control-original-extrusion-original-shape.brep', 'output_path': 'control-original-extrusion-original-shape.brep', 'sha256': 'f48d4f4a188fc7b85e0d5a89082134de47bfa83b5e4169c75de639ee1eb0d5a8', 'bytes': 9378}, {'input_path': 'control-original-extrusion-original-face.brep', 'output_path': 'control-original-extrusion-original-face.brep', 'sha256': 'ad4c3a9dce88d8f4fc37f507461907edbc0e97468639f1ce973f0ec9f738e36e', 'bytes': 2086}, {'input_path': 'control-original-extrusion-original-shape.step', 'output_path': 'control-original-extrusion-original-shape.step', 'sha256': 'b2315f536a5146ec6ad14d9ee296c6d8a28f3d0da21d0d6af147d956efcbc1ce', 'bytes': 31982}, {'input_path': 'control-original-extrusion-original-face.step', 'output_path': 'control-original-extrusion-original-face.step', 'sha256': '2757f836bf065837e34062563d12c1b8bb84e2ed57453536373c95b7c022eb4a', 'bytes': 5089}, {'input_path': 'step-original-whole-step-root-0.brep', 'output_path': 'step-original-whole-step-root-0.brep', 'sha256': '36d6e48a97bccfd2dae33ee1ab1e31354ca85f4de1548d07cdac00ab22ad90a8', 'bytes': 6556}, {'input_path': 'step-original-face-step-root-0.brep', 'output_path': 'step-original-face-step-root-0.brep', 'sha256': 'f61c12634156eb8d5632b80da4058fdaf537bb248995b689d28f64e0669f43f1', 'bytes': 188}, {'input_path': 't025-translated.brep', 'output_path': 't025-translated.brep', 'sha256': 'a30ff27ca9731f4553ed11cd4332d5525cf553e7a43d152d77dc40f8319ce094', 'bytes': 8258}, {'input_path': 'control-original-extrusion-v2-region-0.brep', 'output_path': 'control-original-extrusion-v2-region-0.brep', 'sha256': '8c5ccf1475719375dbce201d0f5ef809db4fb3dc8a9d74ff62f91c336e2fabad', 'bytes': 9378}, {'input_path': 'report.json', 'output_path': 'original-L5c-report.json', 'sha256': '7ed716e0abd918b977fca1cbaa270c0e4873dc88e8d626397203c9c5e40b82fb', 'bytes': 44715}], 'actual_cut_operands': {'a': 't025-translated.brep', 'b': 'control-original-extrusion-v2-region-0.brep'}, 'actual_expected_CadQuery_null_constant': {'public_source_literal': 'Null TopoDS_Shape object', 'utf8_bytes': 24, 'sha256': '6ec2e46348dbe80afad13cbcb89fd614c1d61a7905475c9e817ca619cd0b3d5c', 'locked_shapes_source_sha256': '48331311a0e6de8dc324c3bf76e4ed3c3769f47d007a0243ac25f454cc22bb47', 'official_source_URL': 'https://raw.githubusercontent.com/CadQuery/cadquery/v2.7.0/cadquery/occ_impl/shapes.py'}, 'original_two_STEP_failures_retained_not_reclassified': True, 'original_pair_volume_gate_mm3': 1e-07, 'maximum_boolean_build_calls': 6, 'actual_native_predecessor_seconds': 4.1149082919999955, 'actual_native_predecessor_peak_RSS_bytes': 517107712, 'full_domain_or_pair_qualification': False}}

class L5d1PartialNativeArchiveControls(unittest.TestCase):
    fixture=L5DiagnosticTypedControls.fixture
    check=L5DiagnosticTypedControls.check
    def test_l5d1_partial_SIGSEGV_evidence_is_archivable(self):
        p,e=self.fixture("L5d1")
        r=self.check(p,e,"L5d1")
        self.assertFalse(r["qualification_required"])
        self.assertEqual(r["frozen_source_files"],24)

    def test_l5d1_original_source_predecessor_is_distinct_from_input_predecessor(self):
        p,e=self.fixture("L5d1")
        d=json.loads(p["L5D1_SOURCE_IDENTITY.json"])
        d["parent_L5d_workflow_commit"]="f544f33c563ef4a44e8baa38c3e1225ad6e60b9e"
        p["L5D1_SOURCE_IDENTITY.json"]=json.dumps(d).encode()
        with self.assertRaises(MOD.ArchiveInvariantError):self.check(p,e,"L5d1")

if __name__ == "__main__":
    unittest.main()
