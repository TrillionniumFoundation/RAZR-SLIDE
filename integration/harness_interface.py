"""Read native R5 XML and wire schedule without importing any design generator.

Validates the existing A-only bench chain; not independent B/USB/OLED circuitry.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "engineering/power-chain-pcba-20261013-r5"
STAGES = {
    "A1": ("A_PACK_P", "A_MID_P", "A_PACK_N"),
    "A2": ("A_MID_P", "A_TX_P", "A_PACK_N"),
    "B1": ("A_RX_P", "A_RX_MID_P", "B_SYS_N"),
    "B2": ("A_RX_MID_P", "SYS_B_P", "B_SYS_N"),
}
PAIRS = [
    ("H_A_LOCAL", "A1.J2", "A2.J1"),
    ("H_CROSS", "A2.J2", "B1.J1"),
    ("H_B_LOCAL", "B1.J2", "B2.J1"),
    ("H_INPUT", "ISOLATED_PROTECTED_SUPPLY_BOUNDARY", "A1.J1"),
    ("H_OUTPUT", "B2.J2", "ISOLATED_LOAD_BOUNDARY"),
] + [("CTRL_" + s, "FLOATING_DRIVER_" + s, s + ".J3") for s in STAGES]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_native(payload: bytes, stage: str) -> dict:
    if stage not in STAGES:
        raise ValueError("unknown stage")
    x = ET.fromstring(payload)
    refs = [c.get("ref") for c in x.findall("./components/comp")]
    if len(refs) != 17 or len(set(refs)) != 17:
        raise ValueError("native component count/identity changed")
    pins = {}
    for net in x.findall("./nets/net"):
        name = (net.get("name") or "").removeprefix("/")
        if not name:
            raise ValueError("unnamed native net")
        for node in net.findall("node"):
            key = (node.get("ref"), node.get("pin"))
            if key in pins or key[0] not in refs or not key[1]:
                raise ValueError("duplicate/unknown native pin")
            pins[key] = {"net": name, "function": node.get("pinfunction")}
    if len(pins) != 42:
        raise ValueError("native pin coverage changed")
    vin, vout, ret = STAGES[stage]
    required = {
        ("J1", "1"): vin, ("J2", "1"): vout,
        ("J1", "2"): ret, ("J2", "2"): ret,
        ("U1", "5"): vin, ("U1", "6"): vout, ("U1", "8"): ret,
        ("J3", "1"): stage + "_ISO_LED_P",
        ("J3", "2"): stage + "_ISO_LED_N",
        ("U2", "2"): stage + "_ISO_LED_N", ("U2", "4"): vin,
    }
    for key, expected in required.items():
        if key not in pins or pins[key]["net"] != expected:
            raise ValueError(f"{stage}.{key}: wrong native connection")
    for pin, function in [("5", "IN"), ("6", "OUT"), ("8", "GND")]:
        if pins["U1", pin]["function"] != function:
            raise ValueError("eFuse pin function mismatch")
    return {"component_count": 17, "unique_pins": 42,
            "terminals": {f"{stage}.{ref}.{pin}": pins[ref, pin]["net"]
                          for ref in ("J1", "J2", "J3") for pin in ("1", "2")},
            "role": "A_source_cut" if stage[0] == "A" else "A_chain_receiver_cut",
            "independent_B_battery": False}


def check_harness(rows: list[dict], boards: dict) -> dict:
    if set(boards) != set(STAGES):
        raise ValueError("all four native boards required")
    expected = {(h, f"{a}.{pin}", f"{b}.{pin}") for h, a, b in PAIRS for pin in (1, 2)}
    actual = [(r["harness"], r["from"], r["to"]) for r in rows]
    if len(actual) != 18 or len(set(actual)) != 18 or set(actual) != expected:
        raise ValueError("missing/duplicate/reversed/crossed harness connection")
    if any(str(r.get("motion_qualified")).lower() != "false" for r in rows):
        raise ValueError("static bench schedule cannot claim moving-FPC qualification")
    terminals = {p: net for b in boards.values() for p, net in b["terminals"].items()}
    used = {}; resolved = []
    for r in rows:
        rr = {k: r[k] for k in ("harness", "from", "to")}
        for end in ("from", "to"):
            p = r[end]
            if p.split(".")[0] in STAGES:
                if p not in terminals or p in used:
                    raise ValueError("native terminal missing or multiply terminated")
                used[p] = r["harness"]; rr[end + "_native_net"] = terminals[p]
            else:
                rr[end + "_native_net"] = None
        resolved.append(rr)
    if len(used) != 24:
        raise ValueError("all 24 J1/J2/J3 board terminals must be bound")
    # Native intra-board return links plus scheduled wires, not I-V simulation.
    graph = {}
    def connect(a, b):
        graph.setdefault(a, set()).add(b); graph.setdefault(b, set()).add(a)
    for r in rows:
        connect(r["from"], r["to"])
    for stage in STAGES:
        connect(stage + ".J1.2", stage + ".J2.2")
    a, b = "ISOLATED_PROTECTED_SUPPLY_BOUNDARY.2", "ISOLATED_LOAD_BOUNDARY.2"
    pending = [[a]]; seen = set(); return_path = None
    while pending:
        path = pending.pop(0); point = path[-1]
        if point == b:
            return_path = path; break
        if point in seen:
            continue
        seen.add(point)
        pending += [path + [n] for n in sorted(graph.get(point, [])) if n not in seen]
    if return_path is None:
        raise ValueError("actual main return is discontinuous")
    return {"conductors": 18, "conductor_ends": 36, "native_board_terminals_bound": 24,
            "external_boundary_ends": 12, "resolved_wiring": resolved,
            "common_main_return_path": return_path,
            "A_PACK_N_and_B_SYS_N_are_connected_by_scheduled_harness": True,
            "separate_control_input_pairs": 4, "independent_B_battery_implemented": False,
            "dry_selftest_connected_to_real_return": False,
            "native_ERC_DRC_rerun": False, "moving_FPC_qualified": False,
            "complete_phone_PCB": False, "manufacturing_go": False}


def inspect(source: Path = SOURCE) -> dict:
    paths = [source / "native_pocket_v2/modules" / s / "native.xml" for s in STAGES]
    paths.append(source / "harness_terminal_schedule.csv")
    before = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    boards = {s: parse_native(paths[i].read_bytes(), s) for i, s in enumerate(STAGES)}
    with paths[-1].open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    result = check_harness(rows, boards)
    if before != {str(p.relative_to(ROOT)): sha(p) for p in paths}:
        raise ValueError("frozen native inputs changed")
    return {"schema": "razr-native-harness-bindings-v1", "input_SHA256": before,
            "source_sha256": sha(Path(__file__)), "boards": boards,
            "native_components_read": 68, "native_unique_pins_read": 168,
            "builder_imported": False, "frozen_input_bytes_unchanged": True, **result}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args(); result = inspect()
    with args.output.open("x") as f:
        json.dump(result, f, indent=2); f.write("\n")
    print(json.dumps({k: result[k] for k in ("native_unique_pins_read", "conductors",
          "native_board_terminals_bound", "independent_B_battery_implemented", "manufacturing_go")}))
