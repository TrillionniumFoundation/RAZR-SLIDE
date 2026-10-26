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
