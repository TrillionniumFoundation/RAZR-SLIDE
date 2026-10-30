"""Persist a small independent I/O fault control for the new recovery helper.

This exercises the helper and commit labels. It does not execute either all16
driver or retrospectively recover/qualify an earlier production attempt.
"""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time
import traceback

R9 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R9 / "envelope"))
import atomic_refinement_r9 as atomic
import recovery_serialization_r9 as recovery


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    report = {"schema": "razr-r9-independent-persisted-recovery-control-v1",
              "control_completed": False, "source": recovery.identity(__file__),
              "recovery_source": recovery.identity(recovery.__file__),
              "atomic_source": recovery.identity(atomic.__file__),
              "reviewed_driver_v1": recovery.identity(R9 / "envelope/cylinder_slab_all16_r9.py"),
              "reviewed_driver_v2": recovery.identity(R9 / "envelope/cylinder_slab_all16_r9_v2.py"),
              "scope": {"synthetic_IO_control_only": True, "full_driver_executed": False,
                        "production_v1_restored_by_this_control": False,
                        "production_v1_retroactively_qualified": False,
                        "geometry_or_native_qualification": False}}
    try:
        payloads = [("frame-1.json.gz", {"frame": 1, "synthetic_roots": [1, 2]}),
                    ("frame-2.json.gz", {"frame": 2, "synthetic_roots": [3, 4]})]
        original = args.output / "interrupted-original-write"
        original.mkdir()
        try:
            for index, (name, payload) in enumerate(payloads):
                with gzip.open(original / name, "wt") as f:
                    if index == 1:
                        f.write('{"frame":2,"synthetic_roots":[')
                        raise TimeoutError("independent injected deadline during second gzip payload")
                    json.dump(payload, f)
        except TimeoutError as exc:
            report["original_write_failure"] = {"type": type(exc).__name__, "message": str(exc),
                                                "traceback": traceback.format_exc()}
        require("original_write_failure" in report, "injection must actually execute")
        partial = original / "frame-2.json.gz"
        before = recovery.identity(partial)
        parse_error = None
        try:
            with gzip.open(partial, "rt") as f:
                json.load(f)
        except json.JSONDecodeError as exc:
            parse_error = {"type": type(exc).__name__, "message": str(exc)}
        require(parse_error is not None, "original partial JSON must remain incomplete")

        old = {"nodes": [{"id": 0, "depth": 0, "kind": "leaf"}]}
        trace = {}
        new = atomic.prepare_split(old, 0, 0, "1/2", (None, None),
                                   lambda B, i, d: {"id": i, "depth": d, "kind": "leaf"}, trace)
        before_label = recovery.pending_commit_state(trace, old)
        after_label = recovery.pending_commit_state(trace, new)
        require(before_label == "uncommitted", "before-commit label")
        require(after_label == "committed_before_interruption", "after-commit label")
        pending = dict(trace, commit_state=after_label, synthetic_control_only=True)
        recovered = recovery.recover(payloads, args.output / "disqualified-recovery", pending)
        require(recovered["completed"] and recovered["payload_count"] == 2, "two complete recovered payloads")
        require(recovered["qualified_execution"] is False, "recovery cannot create qualification")
        require(recovery.identity(partial) == before, "original truncated bytes preserved")
        rebound = []
        for name, payload in payloads:
            path = args.output / "disqualified-recovery" / name
            with gzip.open(path, "rt") as f:
                actual = json.load(f)
            require(actual == payload, "independent recovered payload equality")
            rebound.append(recovery.identity(path))
        pending_path = args.output / "disqualified-recovery/pending-attempt-evidence.json.gz"
        with gzip.open(pending_path, "rt") as f:
            actual_pending = json.load(f)
        require(actual_pending == pending, "independent pending evidence equality")
        report.update(control_completed=True, original_partial=before,
                      original_partial_parse_failure=parse_error,
                      original_partial_unchanged=True, independently_reopened_payload_count=len(rebound),
                      independently_reopened_payloads=rebound,
                      independently_reopened_pending=recovery.identity(pending_path),
                      recovery_manifest=recovery.identity(args.output / "disqualified-recovery/recovery-manifest.json"),
                      pending_labels={"before_commit": before_label, "after_commit": after_label},
                      qualified_execution_after_failure=False)
    except Exception as exc:
        report["control_failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    report["seconds"] = time.monotonic() - start
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report.get(k) for k in ("control_completed", "seconds", "control_failure")}))
    if not report["control_completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
