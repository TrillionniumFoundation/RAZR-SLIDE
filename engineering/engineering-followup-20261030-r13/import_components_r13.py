#!/usr/bin/env python3
"""Import byte-sealed R13 components; retain original paths as provenance.

This is an import/readback procedure, not a replay of CAD or numerical work.
The default source directories are the original execution workspaces.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WORK = ROOT.parent


def digest(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def copy_verified(source, target, expected=None):
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"not a regular source file: {source}")
    before = digest(source)
    if expected is not None:
        assert all(before[k] == expected[k] for k in ("bytes", "sha256")), source
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert digest(target) == before, target
    else:
        shutil.copy2(source, target)
    assert digest(target) == before and digest(source) == before
    return {"source": str(source), "repository_path": target.relative_to(ROOT).as_posix(), **before}


def import_manifest(source, target, name, extras=()):
    manifest = json.loads((source / name).read_text())
    raw = manifest["files"]
    members = [{"path": k, **v} for k, v in raw.items()] if isinstance(raw, dict) else raw
    rows = []
    for item in members:
        rel = Path(item["path"])
        assert not rel.is_absolute() and ".." not in rel.parts
        rows.append(copy_verified(source / rel, target / rel, item))
    for rel in (name, *extras):
        rows.append(copy_verified(source / rel, target / rel))
    return {"manifest": name, "manifest_members": len(members), "imported_files": len(rows),
            "imported_bytes": sum(r["bytes"] for r in rows), "files": rows,
            "all_source_and_destination_bytes_equal": True}


def main():
    components = {}
    components["geometry"] = import_manifest(WORK / "r13_geometry_work", HERE / "geometry",
        "DELIVERY_MANIFEST.json", ("ARCHIVE_READBACK.json",))
    components["envelope"] = import_manifest(WORK / "r13_envelope_work", HERE / "envelope",
        "R13_ENVELOPE_DELIVERY_MANIFEST.json")
    components["real_inputs"] = import_manifest(WORK / "r13_inputs_work/public", HERE / "real-inputs",
        "MANIFEST.json")
    row = copy_verified(WORK / "r13_inputs_work/INDEPENDENT_READBACK.json",
                        HERE / "real-inputs/INDEPENDENT_READBACK.json")
    components["real_inputs"]["files"].append(row)
    components["real_inputs"]["imported_files"] += 1
    components["real_inputs"]["imported_bytes"] += row["bytes"]
    pub = WORK / "r13_publication_work"
    public_names = ["R12_PUBLICATION_READBACK.json", "R12_PUBLICATION_PLAN.json",
                    "CHECKPOINT_TREE_PLAN.json", "CHECKPOINT_EXTRA_BLOB_RECEIPT.json"]
    public_names += sorted(p.relative_to(pub).as_posix() for p in (pub / "receipts").glob("*.json"))
    public_names += sorted(p.relative_to(pub).as_posix() for p in (pub / "original-local-commit-objects").glob("*.commit"))
    rows = [copy_verified(pub / name, HERE / "publication/R12" / name) for name in public_names]
    components["R12_publication"] = {"imported_files": len(rows),
        "imported_bytes": sum(r["bytes"] for r in rows), "files": rows,
        "transport_job_payloads_imported": False, "all_source_and_destination_bytes_equal": True}
    receipt = {"schema": "razr-r13-root-component-import-readback-v1",
        "verified_utc": datetime.now(timezone.utc).isoformat(), "components": components,
        "file_count": sum(c["imported_files"] for c in components.values()),
        "total_bytes": sum(c["imported_bytes"] for c in components.values()),
        "private_OEM_response_bodies_imported": False, "R12_scientific_files_modified": False,
        "scientific_scope_promoted_by_copy": False}
    target = HERE / "independent-review/COMPONENT_IMPORT_READBACK.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"verified_files": receipt["file_count"], "bytes": receipt["total_bytes"],
                      "components": {k: v["imported_files"] for k, v in components.items()}}))


if __name__ == "__main__":
    main()
