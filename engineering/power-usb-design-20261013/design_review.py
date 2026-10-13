"""Node-level conductive paths and sizing; never a hardware or SPICE certificate."""
from __future__ import annotations

from collections import deque
from pathlib import Path
import json
import math
import platform
import socket

ROOT = Path(__file__).resolve().parent


def path(edges, start, end):
    """Return an auditable node/part path, not a voltage/energy estimate."""
    seen = {start}
    q = deque([(start, [])])
    while q:
        node, route = q.popleft()
        if node == end:
            return route
        for src, dst, ref in edges:
            if src == node and dst not in seen:
                seen.add(dst)
                q.append((dst, route + [{"from": src, "to": dst, "via": ref}]))
    return None


def graph(netlist, on=(), welded=(), faults=()):
    edges = []

    def add(a, b, ref, bilateral=False):
        edges.append((a, b, ref))
        if bilateral:
            edges.append((b, a, ref))

    for cabin in ("A", "B"):
        add(cabin + "_CELL_P", cabin + "_PACK_P", cabin + "_pack_fuse_unspecified", True)
        if cabin + "_PACK_PROTECT" in on:
            add(cabin + "_CELL_N", cabin + "_PACK_N", cabin + "_pack_low_side_protection", True)
    for part in netlist["components"]:
        ref = part["ref"]
        if part.get("part_candidate") == "TPS259470LRPW" and (ref in on or ref in welded):
            add(part["pins"]["5"]["net"], part["pins"]["6"]["net"], ref,
                ref in welded)
    add("A_TX_P", "A_RX_P", "H_POWER_A.forward", True)
    if "open_H_POWER_A_return" not in faults:
        add("A_PACK_N", "B_PACK_N", "H_POWER_A.dedicated_return", True)
    add("A_CHARGE_TX", "A_CHARGE_RX", "H_CHARGE_A.forward", True)
    add("USB_GND", "A_PACK_N", "H_CHARGE_A.dedicated_return", True)
    # Actual bond matrix is still unknown. This is the proposal, not observed wiring.
    add("USB_GND", "B_PACK_N", "proposed_system_side_USB_reference_bond", True)
    # Charger internals are unselected. Enabled VIN->local SYS is only a route screen.
    for cabin, charger in netlist["chargers"].items():
        if "CHARGER_" + cabin in on:
            add(charger["VIN"], charger["SYS"], "unselected_" + cabin + "_charger_converter")
    fault_edges = {
        "raw_A_to_harness": ("A_CELL_P", "A_TX_P"),
        "raw_B_to_harness": ("B_CELL_P", "A_RX_P"),
        "system_bus_to_harness": ("SYS_B_P", "A_RX_P"),
        "raw_A_negative_to_USB_ground": ("A_CELL_N", "USB_GND"),
        "unsafe_B_charger_SYS_to_system": ("B_CHARGER_SYS_LOCAL", "SYS_B_P"),
        "unsafe_precharge_bypasses_two_cuts": ("A_PACK_P", "A_TX_P"),
        "power_to_USB_data_abrasion": ("A_TX_P", "USB_DATA_HOST"),
        "unpowered_host_clamp_bypass": ("USB_DATA_HOST", "HOST_VDD"),
    }
    for fault in faults:
        if fault == "open_H_POWER_A_return":
            continue
        if fault not in fault_edges:
            raise ValueError("Unknown fault " + fault)
        add(*fault_edges[fault], "INJECTED:" + fault, True)
    return edges


def cell_load_loop(netlist, on=(), welded=(), faults=(), cabin="A", positive="SYS_B_P"):
    edges = graph(netlist, on, welded, faults)
    forward = path(edges, cabin + "_CELL_P", positive)
    ret = path(edges, "B_PACK_N", cabin + "_CELL_N")
    return {"forward_path": forward, "return_path": ret,
            "conductive_loop_exists": forward is not None and ret is not None,
            "actual_voltage_current_energy": None}


def positive_real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def size(inputs):
    """Parametric engineering equations. Missing/invalid input never gets a default."""
    out = {"product_qualified": False, "manufacturing_go": False,
           "computed": {}, "incomplete": [], "invalid": []}

    def calc(name, keys, fn):
        absent = [k for k in keys if inputs.get(k) is None]
        invalid = [k for k in keys if inputs.get(k) is not None and not positive_real(inputs[k])]
        if absent:
            out["incomplete"].append({"calculation": name, "missing": absent})
        if invalid:
            out["invalid"].append({"calculation": name, "invalid": invalid})
        if absent or invalid:
            out["computed"][name] = None
        else:
            out["computed"][name] = fn(*(inputs[k] for k in keys))

    calc("slew_V_per_ms", ["target_inrush_A", "output_capacitance_F"], lambda i, c: i / c / 1000)
    calc("DVDT_C_pF_screen", ["target_inrush_A", "output_capacitance_F"], lambda i, c: 2e6*c/i)
    calc("ILM_R_ohm_screen", ["current_limit_A"], lambda i: 3334/i)
    calc("capacitor_energy_J", ["output_capacitance_F", "A_pack_max_V"], lambda c, v: 0.5*c*v*v)
    calc("single_eFuse_I2R_W_screen", ["load_continuous_A"], lambda i: i*i*0.045)
    calc("harness_conduction_W", ["load_continuous_A", "harness_resistance_ohm"], lambda i, r: i*i*r)
    calc("bleed_equilibrium_V", ["leakage_max_A", "bleed_R_ohm"], lambda i, r: i*r)
    bleed_keys = ["output_capacitance_F", "A_pack_max_V", "residual_voltage_limit_V", "leakage_max_A", "bleed_R_ohm"]
    if all(positive_real(inputs.get(k)) for k in bleed_keys):
        c, vi, vf, il, r = (inputs[k] for k in bleed_keys)
        equilibrium = il*r
        # Roundoff at the boundary cannot demonstrate a reachable lower voltage.
        if vf <= equilibrium or math.isclose(vf, equilibrium, rel_tol=1e-12, abs_tol=0):
            out["computed"]["bleed_time_s"] = None
            out["invalid"].append({"calculation": "bleed_time_s", "reason": "leakage equilibrium at or above permitted voltage; cannot discharge to limit"})
        elif vi <= vf:
            out["computed"]["bleed_time_s"] = 0
        else:
            out["computed"]["bleed_time_s"] = r*c*math.log((vi-equilibrium)/(vf-equilibrium))
    else:
        out["computed"]["bleed_time_s"] = None
        out["incomplete"].append({"calculation": "bleed_time_s", "missing_or_invalid": [k for k in bleed_keys if not positive_real(inputs.get(k))]})
    out["limits"] = {
        "TPS_input_range_check": None if inputs.get("A_pack_min_V") is None or inputs.get("A_pack_max_V") is None else 2.7 <= inputs["A_pack_min_V"] <= inputs["A_pack_max_V"] <= 23,
        "TPS_continuous_current_check": None if inputs.get("load_continuous_A") is None else positive_real(inputs["load_continuous_A"]) and inputs["load_continuous_A"] <= 5.5,
        "TPS_resistance_test_current_A": 3,
        "ILM_resistor_range_check": None if out["computed"]["ILM_R_ohm_screen"] is None else 549 <= out["computed"]["ILM_R_ohm_screen"] <= 6650,
        "actual_fault_energy_fuse_SOA_thermal_qualification": False,
    }
    return out


def run():
    netlist = json.loads((ROOT / "candidate_netlist.json").read_text())
    inputs = json.loads((ROOT / "product_inputs.json").read_text())["measured_or_signed_inputs"]
    rows = []
    scenarios = [
        ("all_energy_cuts_off", ["A_PACK_PROTECT", "B_PACK_PROTECT"], [], [], "A", "A_TX_P"),
        ("one_source_stage_welded", ["A_PACK_PROTECT"], ["U_A1"], [], "A", "A_TX_P"),
        ("both_A_source_stages_welded", ["A_PACK_PROTECT"], ["U_A1", "U_A2"], [], "A", "A_TX_P"),
        ("raw_A_direct_short_bypasses_both_cuts", ["A_PACK_PROTECT"], [], ["raw_A_to_harness"], "A", "A_TX_P"),
        ("raw_B_direct_short_to_other_harness", ["B_PACK_PROTECT"], [], ["raw_B_to_harness"], "B", "A_RX_P"),
        ("B_live_receiver_blocks_reverse", ["B_PACK_PROTECT", "U_B1", "U_B2"], [], [], "B", "A_RX_P"),
        ("B_live_system_PCB_short_bypasses_receiver", ["B_PACK_PROTECT", "U_B1", "U_B2"], [], ["system_bus_to_harness"], "B", "A_RX_P"),
        ("pack_protection_off_return_isolated", ["U_A1", "U_A2", "U_ARX"], [], [], "A", "SYS_B_P"),
        ("pack_protection_off_raw_negative_USB_bypass", ["U_A1", "U_A2", "U_ARX"], [], ["raw_A_negative_to_USB_ground"], "A", "SYS_B_P"),
        ("raw_negative_bypass_does_not_defeat_positive_off_cuts", [], [], ["raw_A_negative_to_USB_ground"], "A", "SYS_B_P"),
        ("unsafe_parallel_precharge_branch", ["A_PACK_PROTECT"], [], ["unsafe_precharge_bypasses_two_cuts"], "A", "A_TX_P"),
        ("power_return_open_reroutes_through_charge_return", ["A_PACK_PROTECT", "U_A1", "U_A2", "U_ARX"], [], ["open_H_POWER_A_return"], "A", "SYS_B_P"),
    ]
    for name, on, welded, faults, cabin, positive in scenarios:
        rows.append({"id": name, "on": on, "welded": welded, "faults": faults,
                     "cabin": cabin, "hazard_node": positive,
                     **cell_load_loop(netlist, on, welded, faults, cabin, positive)})
    external_on = ["U_VBUS", "CHARGER_B"]
    external_faults = ["unsafe_B_charger_SYS_to_system"]
    rows.append({"id": "adapter_live_despite_all_battery_source_cuts_off", "on": external_on,
                 "faults": external_faults,
                 "forward_path": path(graph(netlist, external_on, faults=external_faults), "USB_VBUS_PORT", "SYS_B_P"),
                 "return_path": [{"from":"USB_GND","to":"USB_GND","via":"external adapter return"}],
                 "scope": "unsafe proposed charger SYS tie, not measured charger model; grounded in documented adapter mode"})
    edgegraph = graph(netlist, ["A_PACK_PROTECT", "U_A1", "U_A2"], faults=["power_to_USB_data_abrasion", "unpowered_host_clamp_bypass"])
    rows.append({"id":"unselected_IO_clamp_can_phantom_supply_HOST_VDD", "forward_path":path(edgegraph,"A_CELL_P","HOST_VDD"),
                 "scope":"explicit injected insulation fault and clamp path; actual host clamp parameters unknown"})
    out = {"schema": "razr-slide-node-path-review-v1", "host": socket.gethostname(),
           "system": platform.platform(), "physical_hardware_test": False,
           "manufacturing_go": False, "product_sizing": size(inputs), "path_counterexamples": rows,
           "finite_leakage_and_residual_energy_not_simulated": True,
           "PCB_short_clearance_or_physical_independence_verified": False}
    (ROOT / "execution_receipt.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"node_path_cases": len(rows), "product_computed_outputs": out["product_sizing"]["computed"],
                      "manufacturing_go": False}, indent=2))


if __name__ == "__main__":
    run()
