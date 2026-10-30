"""Losslessly archive every R9 geometry file, including failed/partial attempts.

Run after all native workers and scope writers have finished. The original
directories remain untouched. The tar is read back without extraction; every
payload member is compared to the complete source-file SHA256 manifest.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time

HERE = Path(__file__).resolve().parent
EXCLUDED = {"R9_GEOMETRY_ORIGINALS.tar.gz", "RAW_EVIDENCE_MANIFEST.json", "ARCHIVE_READBACK.json"}


def fingerprint(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest}


def files():
    return {str(p.relative_to(HERE)): p for p in sorted(HERE.rglob("*"))
            if p.is_file() and p.name not in EXCLUDED and "__pycache__" not in p.parts
            and not p.name.endswith((".pyc", ".tmp"))}


def main():
    started = time.monotonic()
    archive = HERE / "R9_GEOMETRY_ORIGINALS.tar.gz"
    manifest_path = HERE / "RAW_EVIDENCE_MANIFEST.json"
    receipt_path = HERE / "ARCHIVE_READBACK.json"
    if any(p.exists() for p in (archive, manifest_path, receipt_path)):
        raise FileExistsError("archive or preservation receipt already exists")
    source_files = files()
    manifest = {"schema": "razr-r9-geometry-complete-original-file-manifest-v1",
                "files": {name: fingerprint(path) for name, path in source_files.items()},
                "includes_original_v1_partial_second_state": True,
                "includes_initial_ESRCH_and_successful_owned_stop_records": True,
                "external_historical_source_archives_referenced_not_duplicated": True}
    manifest_bytes = (json.dumps(manifest, indent=2, allow_nan=False) + "\n").encode()
    manifest_path.write_bytes(manifest_bytes)
    with archive.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as tar:
                info = tarfile.TarInfo("MANIFEST.json")
                info.size = len(manifest_bytes)
                info.mtime = 0
                tar.addfile(info, io.BytesIO(manifest_bytes))
                for name, path in source_files.items():
                    tar.add(path, arcname="payload/" + name, recursive=False)
    expected = {"payload/" + name: identity for name, identity in manifest["files"].items()}
    expected["MANIFEST.json"] = {"bytes": len(manifest_bytes), "sha256": hashlib.sha256(manifest_bytes).hexdigest()}
    observed = {}
    with tarfile.open(archive, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile() or member.name in observed:
                raise ValueError("unexpected or duplicate archive member")
            stream = tar.extractfile(member)
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            observed[member.name] = {"bytes": member.size, "sha256": digest}
    if observed != expected:
        raise ValueError("complete archive payload differs from original manifest")
    after_files = files()
    unchanged = (list(source_files) == list(after_files)
                 and {n: fingerprint(p) for n, p in after_files.items()} == manifest["files"])
    if not unchanged:
        raise ValueError("original file set or bytes changed during archival")
    receipt = {
        "schema": "razr-r9-geometry-complete-original-archive-readback-v1",
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "archive": {"path": archive.name, **fingerprint(archive)},
        "manifest": {"path": manifest_path.name, **fingerprint(manifest_path)},
        "source_file_count": len(source_files),
        "source_bytes": sum(x["bytes"] for x in manifest["files"].values()),
        "archive_member_count": len(observed),
        "complete_member_names_sizes_and_SHA256_match": True,
        "all_source_files_before_after_unchanged": unchanged,
        "source_files_removed": False,
        "scientific_evidence_reclassified": False,
        "full_continuous_G2": False,
        "seconds": time.monotonic() - started,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
