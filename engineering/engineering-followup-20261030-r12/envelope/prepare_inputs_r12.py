"""Copy exact, already executed R11 inputs into a relocatable R12 evidence set."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def identity(path):
    p = Path(path)
    return {"path": str(p.resolve()), "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--r11-envelope", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    old = args.r11_envelope.resolve()
    records = {}

    def copy(source, relative, expected=None):
        source = Path(source)
        actual = identity(source)
        if expected:
            assert all(actual[k] == expected[k] for k in ("bytes", "sha256")), str(source)
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert all(identity(target)[k] == actual[k] for k in ("bytes", "sha256"))
        records[str(source.resolve())] = {"relative": relative, "bytes": actual["bytes"],
                                         "sha256": actual["sha256"]}
        return target

    producer = old / "l1-local-rebuild/producer-attempt1/report.json"
    reader = old / "l1-local-rebuild/independent-attempt1/report.json"
    prior = json.loads(producer.read_text())
    assert prior["completed"] and prior["recorded_budget_passed"]
    assert json.loads(reader.read_text())["completed"]
    copy(producer, "prior-producer.json")
    copy(reader, "prior-reader.json")
    deps = ["native_axis_inventory_r11.py", "check_hybrid_axis_mask_r11.py",
            "audit_native_uv_orientation_r11.py", "l1-local-rebuild/native_local_inventory_r11.py",
            "l1-local-rebuild/check_local_cover_r11.py"]
    for relative in deps:
        copy(old / relative, "dependencies/" + relative)
    for row in prior["cases"]:
        cid = row["case_id"]
        inputs = row["input_references"]
        item = inputs["copied_result"]
        copy(item["path"], f"originals/{cid}/result.json", item)
        for entry in inputs["materials"]:
            item = entry["copied"]
            copy(item["path"], f"originals/{cid}/{entry['role']}.brep", item)
        for leaf in row["native_leaves"]:
            for key in ("carrier", "Common"):
                item = leaf[key]
                copy(item["path"], f"r11-native/{cid}/node-{leaf['node_id']:04}-{key}.brep", item)
    negative = old.parent / "geometry-proof/BOUNDED_FILLING_EXACT_NEGATIVE_CONTROL_V1.json"
    copy(negative, "prior-hollow-shell-negative-control.json")
    manifest = {"schema": "razr-r12-exact-local-input-copy-v1", "completed": True,
                "preparation_source": identity(__file__), "files": records,
                "original_producer": identity(producer), "original_reader": identity(reader),
                "case_ids": [r["case_id"] for r in prior["cases"]],
                "old_files_modified": False, "file_count": len(records),
                "content_bytes": sum(r["bytes"] for r in records.values())}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in ("completed", "file_count", "content_bytes")}))


if __name__ == "__main__":
    main()
