"""Append a read-only resource observation for this geometry campaign."""
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
scripts = {"read_one_completed_state_v2.py", "run_remaining_original_states_v3.py"}
tasks = []
for path in Path("/proc").iterdir():
    if not path.name.isdigit():
        continue
    try:
        args = (path / "cmdline").read_bytes().decode(errors="replace").strip("\x00").split("\x00")
        if not args or Path(args[0]).name not in ("python", "python3"):
            continue
        matches = [x for x in args if Path(x).name in scripts]
        if not matches:
            continue
        status = dict(line.split(":", 1) for line in (path / "status").read_text().splitlines() if ":" in line)
        stat = (path / "stat").read_text()
        fields = stat[stat.rfind(")") + 2:].split()
        tasks.append({"pid": int(path.name), "script": matches[0],
                      "state": args[args.index("--state") + 1] if "--state" in args else None,
                      "output": args[args.index("--output") + 1],
                      "process_start_tick": fields[19], "cpu_ticks": int(fields[11]) + int(fields[12]),
                      "status": {k: status[k].strip() for k in ("Name", "State", "VmRSS", "VmHWM", "VmSize", "Threads")}})
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
cg = Path("/sys/fs/cgroup")
row = {"observed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
       "cgroup": {n: (cg / n).read_text().strip() for n in ("memory.current", "memory.max", "memory.events", "memory.stat", "cpu.max")},
       "owned_geometry_workers_observed": tasks,
       "cgroup_OOM_event_cause_or_victim_identified_by_this_record": False}
with (HERE / "RESOURCE_OBSERVATIONS.jsonl").open("a") as stream:
    stream.write(json.dumps(row) + "\n")
print(json.dumps({"utc": row["observed_utc"], "memory_current": row["cgroup"]["memory.current"],
                  "memory_events": row["cgroup"]["memory.events"],
                  "workers": [{"pid": x["pid"], "script": Path(x["script"]).name,
                               "status": x["status"]["State"], "RSS": x["status"]["VmRSS"]} for x in tasks]}))
