#!/usr/bin/env python3
"""List, verify, or reconstruct archived exact Library originals."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def reconstruct(root, record, destination=None):
    total = 0
    whole = hashlib.sha256()
    output = None
    if destination is not None:
        relative = PurePosixPath(record["original_library_path"].lstrip("/"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Unsafe original path")
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        output = target.open("wb")
    try:
        for digest, size in record["segments"]:
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Invalid segment SHA-256")
            data = (root / "blobs" / digest[:2] / digest).read_bytes()
            if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("Corrupt or missing segment: " + digest)
            whole.update(data)
            total += size
            if output is not None: output.write(data)
    finally:
        if output is not None: output.close()
    if total != record["size_bytes"] or whole.hexdigest() != record["sha256"]:
        raise ValueError("Original reconstruction mismatch: " + record["name"])
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--restore", metavar="NAME_OR_LIBRARY_ID")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_text())
    records = manifest["files"]
    if args.list:
        for record in records:
            print(record["sha256"], record["size_bytes"], record["disposition"], record["name"])
        return
    if args.restore:
        if args.destination is None: parser.error("--restore requires --destination")
        records = [record for record in records
                   if args.restore in (record["name"], record["library_file_id"])]
        if len(records) != 1: parser.error("Select one exact original filename or Library ID")
        if records[0]["disposition"] != "allowed":
            parser.error("Original bytes excluded; inspect exclusions.json")
    else:
        records = [record for record in records if record["disposition"] == "allowed"]
    total = sum(reconstruct(root, record, args.destination if args.restore else None)
                for record in records)
    print(json.dumps({"verified_originals": len(records), "verified_bytes": total,
                      "manufacturing_go": False}))


if __name__ == "__main__":
    main()
