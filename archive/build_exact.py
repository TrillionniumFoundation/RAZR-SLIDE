#!/usr/bin/env python3
"""Preserve exact originals with ZIP-aware SHA-256 segment reuse.

Library originals remain local. Files containing restricted vendor CAD are
listed in the exclusion ledger and never contribute bytes to the Git archive.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import struct
import zipfile

CHUNK_SIZE = 1024 * 1024
RESTRICTED = {
    "787382f59954cdb58375d04f67807c54edede419020abaf790023df4714f49d6": "Hirose BM28-24DP.stp; vendor redistribution permission absent",
    "4dc2955e5c0e4b4cce461b1d5ffc036542f0f69ebd753af03207186020587bd2": "Hirose BM28-24DS.stp; vendor redistribution permission absent",
    "387c2ebca29849a6ef3703fcb1db49cba7703fb3536f9ac0841ccb7509b9e3bf": "Hirose Readme.pdf; original notice retained locally only",
    "34bec3a555e535094585da3d4ba89ac8b2a1cfbbb44430ecf68db3596aa26f8e": "Hirose OEM header STEP source ZIP",
    "e4008c42ad317681277262bc48857a1c9720b984c05d1a57ad926c12ea5f618b": "Hirose OEM receptacle STEP source ZIP",
}
RESTRICTED_NAMES = {"bm28-24dp.stp", "bm28-24ds.stp"}


def digest_path(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for data in iter(lambda: stream.read(CHUNK_SIZE), b""):
            h.update(data)
    return h.hexdigest()


class Window(io.RawIOBase):
    """Independent seekable view of a bounded range in an unchanged file."""
    def __init__(self, path, offset=0, size=None):
        super().__init__()
        self.path = pathlib.Path(path)
        self.offset = offset
        self.size = self.path.stat().st_size - offset if size is None else size
        self.position = 0
        self.stream = open(path, "rb")

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        new = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if new < 0: raise OSError(22, "Invalid negative archive view seek")
        self.position = new
        return new

    def read(self, size=-1):
        remaining = max(0, self.size - self.position)
        size = remaining if size < 0 else min(remaining, size)
        self.stream.seek(self.offset + self.position)
        data = self.stream.read(size)
        self.position += len(data)
        return data

    def close(self):
        if not self.closed:
            self.stream.close()
        super().close()


def payload_offset(path, start, info):
    with open(path, "rb") as stream:
        stream.seek(start + info.header_offset)
        header = stream.read(30)
    if len(header) != 30 or header[:4] != b"PK\x03\x04":
        raise ValueError("Invalid ZIP local header")
    filename_length, extra_length = struct.unpack_from("<HH", header, 26)
    return info.header_offset + 30 + filename_length + extra_length


class Scanner:
    def __init__(self, temp):
        self.cache = {}
        self.temp = temp
        temp.mkdir(parents=True, exist_ok=True)
        self.errors = []
        self.geometry = []

    def scan(self, path, start=0, size=None, sha=None, depth=0):
        size = pathlib.Path(path).stat().st_size - start if size is None else size
        if sha in self.cache:
            return self.cache[sha]
        if sha in RESTRICTED:
            findings = [{"path": ".", "sha256": sha, "reason": RESTRICTED[sha]}]
            self.cache[sha] = findings
            return findings
        if depth > 32:
            return [{"path": ".", "reason": "Nested archive depth exceeded audit bound"}]
        findings = []
        try:
            with Window(path, start, size) as view, zipfile.ZipFile(view) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    h = hashlib.sha256()
                    prefix = b""
                    with z.open(info) as stream:
                        for data in iter(lambda: stream.read(CHUNK_SIZE), b""):
                            if len(prefix) < 4: prefix += data[:4-len(prefix)]
                            h.update(data)
                    member_sha = h.hexdigest()
                    basename = pathlib.PurePosixPath(info.filename).name.lower()
                    if member_sha in RESTRICTED or basename in RESTRICTED_NAMES:
                        findings.append({"path": info.filename, "sha256": member_sha,
                                         "reason": RESTRICTED.get(member_sha, "Restricted Hirose native STEP filename")})
                    if basename.endswith((".step", ".stp", ".brep", ".stl", ".obj")):
                        self.geometry.append({"container_sha256": sha, "path": info.filename,
                                              "sha256": member_sha, "size_bytes": info.file_size})
                    if prefix.startswith((b"PK\x03\x04", b"PK\x05\x06")):
                        if info.compress_type == zipfile.ZIP_STORED:
                            inner_path = path
                            inner_start = start + payload_offset(path, start, info)
                        else:
                            inner_path = self.temp / (member_sha + ".zip")
                            if not inner_path.exists():
                                with z.open(info) as src, open(inner_path, "wb") as dst:
                                    for data in iter(lambda: src.read(CHUNK_SIZE), b""): dst.write(data)
                            inner_start = 0
                        inner = self.scan(inner_path, inner_start, info.file_size, member_sha, depth+1)
                        findings.extend({**item, "path": info.filename + "!" + item["path"]} for item in inner)
        except (zipfile.BadZipFile, RuntimeError, ValueError, OSError) as error:
            findings.append({"path": ".", "reason": "Archive audit error: " + str(error)})
            self.errors.append({"sha256": sha, "error": str(error)})
        if sha: self.cache[sha] = findings
        return findings


class Archiver:
    def __init__(self, target):
        self.target = target
        self.blobs = target / "blobs"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.unique = {}
        self.segments = 0

    def raw(self, path, start, size):
        result = []
        with open(path, "rb") as stream:
            stream.seek(start)
            while size:
                data = stream.read(min(size, CHUNK_SIZE))
                if not data: raise ValueError("Unexpected end of archive input")
                sha = hashlib.sha256(data).hexdigest()
                destination = self.blobs / sha[:2] / sha
                if not destination.exists():
                    destination.parent.mkdir(exist_ok=True)
                    destination.write_bytes(data)
                if destination.stat().st_size != len(data): raise ValueError("Blob size conflict")
                self.unique[sha] = len(data)
                result.append([sha, len(data)])
                self.segments += 1
                size -= len(data)
        return result

    def segment(self, path, start=0, size=None, depth=0):
        size = pathlib.Path(path).stat().st_size - start if size is None else size
        try:
            with Window(path, start, size) as view, zipfile.ZipFile(view) as z:
                infos = sorted(z.infolist(), key=lambda item: item.header_offset)
                cursor = 0
                result = []
                for info in infos:
                    offset = payload_offset(path, start, info)
                    if offset < cursor or offset + info.compress_size > size:
                        raise ValueError("ZIP payload is out of bounds or overlaps")
                    result.extend(self.raw(path, start+cursor, offset-cursor))
                    with open(path, "rb") as stream:
                        stream.seek(start+offset)
                        prefix = stream.read(4)
                    if info.compress_type == zipfile.ZIP_STORED and prefix.startswith((b"PK\x03\x04", b"PK\x05\x06")) and depth < 32:
                        result.extend(self.segment(path, start+offset, info.compress_size, depth+1))
                    else:
                        result.extend(self.raw(path, start+offset, info.compress_size))
                    cursor = offset + info.compress_size
                result.extend(self.raw(path, start+cursor, size-cursor))
                return result
        except zipfile.BadZipFile:
            return self.raw(path, start, size)

    def verify(self, segments, expected_sha, expected_size):
        h = hashlib.sha256()
        total = 0
        for sha, size in segments:
            path = self.blobs / sha[:2] / sha
            data = path.read_bytes()
            if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
                raise ValueError("Invalid archived segment")
            h.update(data)
            total += size
        if h.hexdigest() != expected_sha or total != expected_size:
            raise ValueError("Exact reconstruction hash / size mismatch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=pathlib.Path, required=True)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--target", type=pathlib.Path, required=True)
    parser.add_argument("--work", type=pathlib.Path, required=True)
    parser.add_argument("--scan-only", action="store_true")
    parser.add_argument("--use-scan", type=pathlib.Path,
                        help="Reuse completed original-byte audit; reconstruction still checks every SHA")
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text())
    args.work.mkdir(parents=True, exist_ok=True)
    scanner = Scanner(args.work / "nested-scan-cache")
    reused_scan = json.loads(args.use_scan.read_text()) if args.use_scan else None
    records = reused_scan["files"] if reused_scan else []
    hashes = {}
    if reused_scan:
        expected = [(m["library_file_id"], m["size_bytes"]) for m in inventory["files"]]
        actual = [(m["library_file_id"], m["size_bytes"]) for m in records]
        if expected != actual:
            raise ValueError("Reused byte audit does not match inventory identities / order / sizes")
        for record in records:
            hashes[record["sha256"]] = hashes.get(record["sha256"], 0) + 1
    for index, metadata in ([] if reused_scan else enumerate(inventory["files"])):
        relative = metadata["path"].lstrip("/")
        path = args.source / relative
        if not path.is_file() or path.stat().st_size != metadata["size_bytes"]:
            raise ValueError("Missing original or unexpected length: " + str(path))
        sha = digest_path(path)
        hashes[sha] = hashes.get(sha, 0) + 1
        findings = scanner.scan(path, sha=sha) if path.name.lower().endswith(".zip") else []
        if sha in RESTRICTED:
            findings.append({"path": ".", "sha256": sha, "reason": RESTRICTED[sha]})
        record = {"name":metadata["name"], "original_library_path":metadata["path"],
                  "library_file_id":metadata["library_file_id"], "file_id":metadata["file_id"],
                  "version_id":metadata["version_id"], "size_bytes":metadata["size_bytes"],
                  "sha256":sha, "selection_basis":metadata["selection_basis"],
                  "disposition":"excluded_vendor_restriction_or_unreadable" if findings else "allowed",
                  "exclusion_findings":findings}
        records.append(record)
        if index % 25 == 0: print(json.dumps({"phase":"scan", "completed":index+1,"total":len(inventory["files"])}), flush=True)
    scan = reused_scan if reused_scan else {"format":"razr-slide-library-byte-audit-v1", "files":records,
            "restricted_source_sha256":RESTRICTED, "archive_scan_errors":scanner.errors,
            "geometry_inventory":scanner.geometry,
            "summary":{"original_count":len(records), "distinct_original_hashes":len(hashes),
                       "original_bytes":sum(r["size_bytes"] for r in records),
                       "distinct_original_bytes":sum(next(r["size_bytes"] for r in records if r["sha256"]==sha) for sha in hashes),
                       "excluded_count":sum(r["disposition"]!="allowed" for r in records)}}
    (args.work/"originals-byte-audit.json").write_text(json.dumps(scan,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"phase":"scan_complete", **scan["summary"]}), flush=True)
    if args.scan_only: return
    archiver = Archiver(args.target)
    for index, record in enumerate(records):
        if record["disposition"] == "allowed":
            path = args.source / record["original_library_path"].lstrip("/")
            record["segments"] = archiver.segment(path)
            archiver.verify(record["segments"], record["sha256"], record["size_bytes"])
        if index % 25 == 0: print(json.dumps({"phase":"archive", "completed":index+1,"total":len(records)}), flush=True)
    manifest = {"format":"razr-slide-exact-original-segments-v1", "chunk_size_limit":CHUNK_SIZE,
                "manufacturing_go":False, "files":records,
                "summary":{**scan["summary"], "allowed_original_count":sum(r["disposition"]=="allowed" for r in records),
                           "stored_blob_count":len(archiver.unique), "stored_blob_bytes":sum(archiver.unique.values()),
                           "referenced_segment_count":archiver.segments,
                           "all_allowed_originals_reconstructed_and_sha256_verified":True}}
    (args.target/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    (args.target/"exclusions.json").write_text(json.dumps({"restricted_source_sha256":RESTRICTED,
        "files":[r for r in records if r["disposition"]!="allowed"]},indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"phase":"archive_complete", **manifest["summary"]}), flush=True)


if __name__ == "__main__":
    main()
