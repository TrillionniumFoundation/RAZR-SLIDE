"""Adversarial synthetic fixtures: no actual archived original is modified."""
from contextlib import contextmanager
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "archive" / "restore.py"
spec = importlib.util.spec_from_file_location("safe_archive_restore", MODULE)
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.store = self.base / "archive"
        self.dest = self.base / "destination"
        self.dest.mkdir()
        self.data = b"original exact bytes\x00\xff\n"
        digest = hashlib.sha256(self.data).hexdigest()
        self.blob = self.store / "blobs" / digest[:2] / digest
        self.blob.parent.mkdir(parents=True)
        self.blob.write_bytes(self.data)
        self.record = dict(original_library_path="/folder/original.bin", size_bytes=len(self.data),
                           sha256=digest, segments=[[digest, len(self.data)]], name="original.bin")
        self.target = self.dest / "folder" / "original.bin"

    def run_restore(self, record=None):
        return restore.reconstruct(self.store, record or self.record, self.dest)

    def assert_no_temps(self):
        self.assertEqual(list(self.dest.rglob(".restore-*.tmp")), [])

    def test_new_destination_is_exact(self):
        self.assertEqual(self.run_restore(), len(self.data))
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assert_no_temps()

    def test_existing_identical_is_idempotent_without_writing(self):
        self.run_restore()
        before = self.target.stat()
        self.run_restore()
        after = self.target.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns, before.st_ctime_ns),
                         (after.st_ino, after.st_mtime_ns, after.st_ctime_ns))

    def test_existing_different_is_preserved(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b"do not modify")
        before = self.target.stat()
        with self.assertRaises(FileExistsError):
            self.run_restore()
        self.assertEqual(self.target.read_bytes(), b"do not modify")
        self.assertEqual(self.target.stat().st_mtime_ns, before.st_mtime_ns)
        self.assert_no_temps()

    def test_bad_whole_hash_does_not_modify_existing(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b"keep old")
        record = {**self.record, "sha256": "0" * 64}
        with self.assertRaises(ValueError):
            self.run_restore(record)
        self.assertEqual(self.target.read_bytes(), b"keep old")
        self.assert_no_temps()

    def test_bad_whole_hash_does_not_publish_new(self):
        with self.assertRaises(ValueError):
            self.run_restore({**self.record, "sha256": "0" * 64})
        self.assertFalse(self.target.exists())
        self.assert_no_temps()

    def test_corrupt_segment_does_not_publish(self):
        self.blob.write_bytes(b"x" * len(self.data))
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assertFalse(self.target.exists())
        self.assert_no_temps()

    def test_missing_segment_preserves_existing(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b"keep")
        self.blob.unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_restore()
        self.assertEqual(self.target.read_bytes(), b"keep")
        self.assert_no_temps()

    def test_symlink_parent_cannot_escape(self):
        outside = self.base / "outside"
        outside.mkdir()
        target = outside / "original.bin"
        target.write_bytes(b"outside")
        (self.dest / "folder").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            self.run_restore()
        self.assertEqual(target.read_bytes(), b"outside")

    def test_symlink_destination_root_rejected(self):
        link = self.base / "root-link"
        link.symlink_to(self.dest, target_is_directory=True)
        with self.assertRaises(OSError):
            restore.reconstruct(self.store, self.record, link)
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_existing_symlink_even_to_identical_bytes_rejected(self):
        self.target.parent.mkdir()
        self.target.symlink_to(self.blob)
        with self.assertRaises(OSError):
            self.run_restore()
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(self.blob.read_bytes(), self.data)
        self.assert_no_temps()

    def test_existing_fifo_rejected_without_blocking(self):
        self.target.parent.mkdir()
        os.mkfifo(self.target)
        with self.assertRaises(FileExistsError):
            self.run_restore()
        self.assert_no_temps()

    def test_source_segment_symlink_rejected(self):
        self.blob.unlink()
        actual = self.base / "outside-source"
        actual.write_bytes(self.data)
        self.blob.symlink_to(actual)
        with self.assertRaises(OSError):
            self.run_restore()
        self.assertFalse(self.target.exists())
        self.assert_no_temps()

    def test_source_fifo_rejected_without_blocking(self):
        self.blob.unlink()
        os.mkfifo(self.blob)
        with self.assertRaises(ValueError):
            self.run_restore()
        self.assert_no_temps()

    def test_unsafe_manifest_paths_rejected(self):
        for value in ("../escape", "/../escape", "/folder/../escape", "//absolute", "C:/escape", "a\\b", "", "/", "a/./b", "a\0b"):
            with self.subTest(path=value), self.assertRaises(ValueError):
                self.run_restore({**self.record, "original_library_path": value})
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_invalid_manifest_lengths_and_digest_rejected(self):
        for value in (-1, True, 2.5, "2"):
            with self.subTest(size=value), self.assertRaises(ValueError):
                self.run_restore({**self.record, "size_bytes": value})
        with self.assertRaises(ValueError):
            self.run_restore({**self.record, "sha256": "not-a-digest"})
        with self.assertRaises(ValueError):
            self.run_restore({**self.record, "segments": [[self.record['sha256'], 2**30]]})
        with self.assertRaises(ValueError):
            self.run_restore({**self.record, "size_bytes": 1})

    def test_verify_only_never_creates_output(self):
        self.assertEqual(restore.reconstruct(self.store, self.record), len(self.data))
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_relative_destination_root_supported(self):
        original = Path.cwd()
        try:
            os.chdir(self.base)
            restore.reconstruct(self.store, self.record, Path("destination"))
        finally:
            os.chdir(original)
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_multi_segment_whole_verification(self):
        record = copy.deepcopy(self.record)
        record["segments"] *= 3
        record["size_bytes"] *= 3
        record["sha256"] = hashlib.sha256(self.data * 3).hexdigest()
        self.run_restore(record)
        self.assertEqual(self.target.read_bytes(), self.data * 3)

    def test_empty_original(self):
        # The archive content store exists even for a zero-segment original.
        record = {**self.record, "segments": [], "size_bytes": 0,
                  "sha256": hashlib.sha256(b"").hexdigest()}
        self.run_restore(record)
        self.assertEqual(self.target.read_bytes(), b"")

    def test_publish_race_preserves_competing_destination(self):
        original_link = os.link
        def competing_link(src, dst, **kwargs):
            self.target.write_bytes(b"concurrent writer")
            return original_link(src, dst, **kwargs)
        with patch.object(restore.os, "link", side_effect=competing_link):
            # Mock functions are not members of os.supports_dir_fd.
            with patch.object(restore, "_require_secure_fs"):
                with self.assertRaises(FileExistsError):
                    self.run_restore()
        self.assertEqual(self.target.read_bytes(), b"concurrent writer")
        self.assert_no_temps()

    def test_interruption_before_publication_cleans_temp(self):
        with patch.object(restore.os, "fsync", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_restore()
        self.assertFalse(self.target.exists())
        self.assert_no_temps()

    def test_partial_stream_write_error_cleans_temp(self):
        def fail(root, segs, size, digest, stream):
            stream.write(b"partial")
            raise OSError("simulated disk error")
        with patch.object(restore, "_reconstruct_to_stream", side_effect=fail):
            with self.assertRaises(OSError):
                self.run_restore()
        self.assertFalse(self.target.exists())
        self.assert_no_temps()


if __name__ == "__main__":
    unittest.main()
