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
