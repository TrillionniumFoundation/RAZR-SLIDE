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


if __name__ == "__main__":
    unittest.main()
