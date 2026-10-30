"""Measure frozen-predicate v2 on the actual saved first v1 factory.

This is an algorithm pilot on an existing full factory, not a new factory or
an independent reader. Preserves all original pair predicates and full rows.
"""
import argparse
import datetime as dt
import importlib.metadata as md
import json
from pathlib import Path
import resource
import sys
import time
import traceback

import run_independent_states_v2 as worker


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--s4-root", required=True, type=Path)
    ap.add_argument("--factory", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    (out / "commons").mkdir()
    started = time.monotonic()
    r = {"schema": "razr-r9-frozen-predicate-pilot-v2", "completed": False,
         "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
         "source": {"factory_report": worker.record(a.factory / "report.json"),
                    "pilot_script": worker.record(__file__),
                    "worker_script": worker.record(worker.__file__),
                    "frozen_predicate": worker.record(Path(__file__).parent / "frozen_predicate_v2.py")},
         "new_factory_executed": False, "independent_reader": False,
         "runtime": {n: md.version(n) for n in ("cadquery", "cadquery-ocp", "numpy", "scipy")}}
    worker.write(out / "report.json", r)
    try:
        sys.path.insert(0, str(a.s4_root.resolve() / "integration"))
        import cadquery as cq
        import product_assembly as p
        old = json.loads((a.factory / "report.json").read_text())
        parts = {}
        checks = {}
        for name, row in old["body_exports"].items():
            entry = row["files"]["brep"]
            path = a.factory / entry["path"]
            if worker.record(path) != {k: entry[k] for k in ("bytes", "sha256")}:
                raise ValueError("v1 saved body changed")
            body = cq.Shape.importBrep(str(path))
            actual = worker.signature(body, p); expected = row["signature"]
            dv = actual["signed_volume_mm3"] - expected["signed_volume_mm3"]
            db = max(abs(x-y) for x, y in zip(actual["bounds_mm"], expected["bounds_mm"]))
            if not actual["valid"] or actual["solid_count"] != expected["solid_count"] or abs(dv) > 1e-7 or db > 1e-7:
                raise ValueError("v1 saved participant failed original signature criteria")
            checks[name] = {"volume_delta_mm3": dv, "bounds_max_delta_mm": db, "passed": True}
            parts[name] = body
        if sorted(parts) != old["participant_names"]:
            raise ValueError("full source participant inventory differs")
        r["body_readbacks"] = checks
        r["pairs"] = worker.pairs(parts, out, p, worker.Budget(1800))
        r["completed"] = bool(r["pairs"]["all_unordered_pairs_present_once"] and r["pairs"]["all_original_BREP_bytes_unchanged"] and not r["pairs"]["failed"])
    except BaseException as exc:
        r["failure"] = type(exc).__name__ + ": " + str(exc)
        r["traceback"] = traceback.format_exc()
    r["seconds"] = time.monotonic() - started
    r["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    worker.write(out / "report.json", r)
    print(json.dumps({"completed": r["completed"], "failure": r.get("failure"), "seconds": r["seconds"]}), flush=True)
    return 0 if r["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
