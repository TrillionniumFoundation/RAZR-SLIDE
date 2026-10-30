"""Stop this owned v1 worker after its first complete matrix is durable.

Retain the original unfinished four-state run and every later partial output.
The completed first state is separately reusable; no original report is edited.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import time


def record(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--run", type=Path, required=True)
    a = ap.parse_args(); process = Path("/proc") / str(a.pid)
    command = (process / "cmdline").read_bytes().split(b"\0")
    if b"python" not in command[0] or not any(x.endswith(b"/run_independent_states.py") for x in command):
        raise ValueError("refusing to signal a process other than this owned v1 worker")
    birth = (process / "stat").read_text().split()[21]
    first = a.run / "lower_L_contact_R_free" / "report.json"
    start = time.monotonic()
    while time.monotonic() - start < 600:
        try:
            state = json.loads(first.read_text())
            top = json.loads((a.run / "report.json").read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.25); continue
        if state.get("completed") and state.get("pairs", {}).get("count") == 11781 and top.get("states", {}).get("lower_L_contact_R_free", {}).get("completed"):
            if (process / "stat").read_text().split()[21] != birth:
                raise ValueError("owned PID identity changed")
            result = {"schema": "razr-r9-owned-v1-partial-campaign-stop-v1",
                      "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                      "script": record(__file__), "owned_pid": a.pid,
                      "owned_process_start_ticks": birth,
                      "first_state_report": record(first),
                      "campaign_report_before_stop": record(a.run / "report.json"),
                      "first_state_completed": True,
                      "original_four_state_campaign_completed": False,
                      "signal": "SIGTERM",
                      "reason": "First original 11781-pair state complete; stop duplicate remaining v1 work before completing the other three states with separately named v2 frozen-participant predicate.",
                      "original_reports_modified": False,
                      "all_partial_outputs_retained": True}
            os.kill(a.pid, signal.SIGTERM)
            result["signal_sent"] = True
            (a.run / "OWNED_STOP_AFTER_FIRST.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, indent=2), flush=True)
            return
        time.sleep(0.25)
    raise TimeoutError("first complete v1 matrix not observed within supervisor budget")


if __name__ == "__main__":
    main()
