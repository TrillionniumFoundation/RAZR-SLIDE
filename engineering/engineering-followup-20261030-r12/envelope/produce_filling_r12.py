"""Generate new filled-carrier certificates from identity-fixed R11 evidence."""
import argparse
import datetime as dt
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time
import traceback


def identity(path):
    p = Path(path)
    return {"path": str(p.resolve()), "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (805306368, 805306368))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("120-second producer budget")))
    signal.alarm(120)
    report = {"schema": "razr-r12-new-filled-carrier-certificates-v1", "completed": False,
              "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "limits": {"seconds": 120, "address_space_bytes": 805306368, "cpus": 1},
              "original_threshold_exact": str(F(1e-7)), "new_native_carriers_constructed": 0,
              "new_refinement_splits": 0, "full_continuous_G2": False,
              "native_boundary_set_identity_proved": False, "uniform_compiled_geometry_error_proved": False}
    try:
        import filling_model_r12 as model
        manifest = json.loads((args.inputs / "manifest.json").read_text())
        assert manifest["completed"]
        for record in manifest["files"].values():
            actual = identity(args.inputs / record["relative"])
            assert all(actual[k] == record[k] for k in ("bytes", "sha256"))
        report["input_manifest"] = identity(args.inputs / "manifest.json")
        report["sources"] = [identity(p) for p in (Path(__file__), Path(model.__file__), Path(__file__).parent / "FILLING_BASIS_R12.md")]
        prior = json.loads((args.inputs / "prior-producer.json").read_text())
        assert prior["completed"] and prior["recorded_budget_passed"]
        payload = {"schema": "razr-r12-filled-carrier-payload-v1",
                   "prior_producer": identity(args.inputs / "prior-producer.json"),
                   "local_cases": [model.local_certificate(row) for row in prior["cases"]],
                   "controls": model.controls(), "original_threshold_exact": str(F(1e-7))}
        path = args.output / "certificates.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")
        report["certificate"] = identity(path)
        report["case_count"] = len(payload["local_cases"])
        report["control_count"] = len(payload["controls"])
        report["completed"] = True
    except Exception as exc:
        report["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        signal.alarm(0)
        report["seconds"] = time.monotonic() - start
        report["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        report["recorded_budget_passed"] = report["completed"] and report["seconds"] <= 120
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report.get(k) for k in ("completed", "case_count", "control_count", "seconds", "peak_RSS_bytes", "failure")}))
    if not report["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
