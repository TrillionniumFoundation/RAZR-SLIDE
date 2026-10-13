"""Bounded architecture/control study, with no physical qualification claims.

Numerical limits must come from measured parts/fixtures. Unknown data deny
release; hypothetical test values never enter the product configuration.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import itertools
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class ForceBounds:
    # Every force below is a worst-case bound, not a nominal force.
    retract_resistance_max_N: float | None = None
    actuator_limit_max_N: float | None = None
    damage_threshold_min_N: float | None = None
    capture_strength_min_N: float | None = None
    calibrated_limit_max_N: float | None = None
    available_retraction_force_min_N: float | None = None


def force_window(bounds: ForceBounds) -> dict:
    values = asdict(bounds)
    if any(value is None for value in values.values()):
        return {"model_feasible": False, "reason": "missing measured worst-case bounds",
                "physical_qualification": False, "manufacturing_go": False}
    if any(not isinstance(value, (int, float)) or isinstance(value, bool)
           or not math.isfinite(value) or value <= 0 for value in values.values()):
        return {"model_feasible": False, "reason": "non-finite or nonpositive bound",
                "physical_qualification": False, "manufacturing_go": False}
    required = bounds.retract_resistance_max_N
    applied = min(bounds.actuator_limit_max_N, bounds.calibrated_limit_max_N)
    safe_upper = min(bounds.damage_threshold_min_N, bounds.capture_strength_min_N)
    # A maximum force cap does not guarantee enough force to overcome a jam.
    # Require a separately measured lower bound on force available in the
    # accepted operating envelope, and a strict upper bound below damage.
    available = bounds.available_retraction_force_min_N
    feasible = required <= available <= applied < safe_upper
    return {"model_feasible": feasible,
            "reason": "hypothetical force window exists" if feasible else "no bounded force window",
            "required_force_max_N": required, "limited_force_max_N": applied,
            "available_retraction_force_min_N": available,
            "safe_force_upper_min_N": safe_upper, "physical_qualification": False,
            "manufacturing_go": False}


@dataclass(frozen=True)
class ReleaseEvidence:
    intentional_release: bool = False
    both_endpoint_retention_verified: bool = False
    both_sources_isolation_commanded: bool = False
    voltage_zero_measured_independently: bool = False
    residual_energy_bounded: bool = False
    harness_retraction_position_verified: bool = False
    finite_force_window_available: bool = False
    passive_fail_closed_retention_verified: bool = False


def release_guard(evidence: ReleaseEvidence) -> dict:
    # This determines a study's sequencing decision only. A boolean entry is
    # no substitute for supplier data, physical geometry, or synchronized tests.
    missing = [name for name, value in asdict(evidence).items() if value is not True]
    return {"model_release_allowed": not missing, "missing": missing,
            "physical_qualification": False, "manufacturing_go": False}


def independent_path_faults() -> list[dict]:
    """Review cross-path faults instead of an electrical-hazard umbrella bit.

    Signal, USB, and controlled power are separately routed/terminated candidate
    paths. Separate naming does not prove physical/electrical independence.
    """
    return [
        {"fault": "signal_fpc_open", "affected_paths": ["signal"],
         "hazard": "loss of sensing/control; mechanical retention must persist without software",
         "required_evidence": "independent passive latch and force-limited safe-stop test"},
        {"fault": "usb_fpc_open_or_pair_short", "affected_paths": ["USB"],
         "hazard": "link loss, ESD/ground-current injection, possible backfeed",
         "required_evidence": "frozen USB topology, protection/layout review, SI and fault tests"},
        {"fault": "power_harness_open", "affected_paths": ["power"],
         "hazard": "undervoltage, loss of actuator supply, local residual energy",
         "required_evidence": "local BMS, safe actuator power-loss position, discharge waveform"},
        {"fault": "power_harness_short_to_signal", "affected_paths": ["power", "signal"],
         "hazard": "control upset and battery-fed short despite separate net names",
         "required_evidence": "physical separation, abrasion/insulation tests, fault current limiting"},
        {"fault": "power_harness_short_to_usb_shield_or_ground", "affected_paths": ["power", "USB"],
         "hazard": "shield/ground becomes unintended battery return",
         "required_evidence": "all return paths and chassis contacts in schematic/PCB/harness FMEA"},
        {"fault": "A_direct_pad_short", "affected_paths": ["power"],
         "hazard": "source A bypasses commanded isolation",
         "required_evidence": "physical PCB bypass injection and independently measured zero voltage"},
        {"fault": "B_direct_pad_short", "affected_paths": ["power"],
         "hazard": "source B bypasses commanded isolation",
         "required_evidence": "physical PCB bypass injection and independently measured zero voltage"},
        {"fault": "shared_live_bus_to_pad_short", "affected_paths": ["power"],
         "hazard": "shared bus bypasses commanded isolation",
         "required_evidence": "shared rail elimination or tested independent interruption path"},
        {"fault": "stale_zero_voltage_measurement", "affected_paths": ["power", "signal"],
         "hazard": "controller can release against energized metal if sensor falsely reports zero",
         "required_evidence": "separate measurement/inhibit fault injection; software guard alone is insufficient"},
        {"fault": "both_release_channels_common_cause", "affected_paths": ["mechanical"],
         "hazard": "two side latches sharing an actuator/load path can both release",
         "required_evidence": "real kinematics, separate load paths, common-cause physical fault test"},
        {"fault": "fpc_anchor_slip", "affected_paths": ["signal", "USB", "power"],
         "hazard": "connector sees peel/axial force or moving loom becomes structural restraint",
         "required_evidence": "actual anchor/strain-relief CAD, measured force/strain at endpoints and every pose"},
    ]


def build_report() -> dict:
    fields = list(ReleaseEvidence.__dataclass_fields__)
    rows = []
    for bits in itertools.product((False, True), repeat=len(fields)):
        evidence = ReleaseEvidence(**dict(zip(fields, bits)))
        rows.append({"input": asdict(evidence), "decision": release_guard(evidence)})
    return {
        "scope": "new conceptual release policy and path-specific FMEA; no implemented hardware",
        "research_config": {"two_equal_compartments": True, "single_approx_7inch_flexible_OLED": True,
                            "B_upward_travel_mm": 79.75, "terminal_normal_seating_mm": 8.2,
                            "A_larger_battery_priority": True},
        "candidate_paths": {
            "signal": "static BM28 endpoint, independently strain-relieved signal FPC; pinout pending",
            "USB": "separate static termination and controlled-impedance moving path; speed/pinout pending",
            "power": "local pack/BMS in each compartment; separately protected controlled exchange path pending",
        },
        "direct_pack_parallel_connection_allowed": False,
        "BM28_repeated_mating_during_slide_allowed": False,
        "mechanical_force_carried_by_FPC_allowed": False,
        "real_pinout_schematic_PCB_harness_frozen": False,
        "default_force_bounds": asdict(ForceBounds()),
        "default_force_decision": force_window(ForceBounds()),
        "default_release_decision": release_guard(ReleaseEvidence()),
        "release_logic_states": len(rows),
        "release_logic_permitted_state_count": sum(row["decision"]["model_release_allowed"] for row in rows),
        "release_logic_rows": rows,
        "fault_witnesses": independent_path_faults(),
        "sequencing_requirement": ["stop motion and keep both captures",
                                  "isolate all energy sources and measure voltage/residual energy",
                                  "verify retraction at bounded force; jam means stay captured",
                                  "permit intentional latch release only after prior requirements"],
        "important_scope_limit": "logical release_permission does not physically interrupt shorts, retract a jam, or create a latch",
        "physical_qualification": False, "manufacturing_go": False,
    }


if __name__ == "__main__":
    report = build_report()
    path = Path(__file__).resolve().parent / "architecture-and-release-study.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "release_logic_rows"}, indent=2))
