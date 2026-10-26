"""Independently bind the completed E3 native ECAD result to exact S4 sources.

This reader verifies existing native outputs. It does not execute KiCad again.
Only engineering records and original generated artwork are exported.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
E3 = "133bad5c5dddbf14fe466a23080b6e2e72ea3cb6"
ZIP_SHA = "6007caf5f838c9c6b0eb8b2669bfa8f72bdaebe4731abef96ea12f27def22236"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(args):
    raw = args.archive.read_bytes()
    assert len(raw) == 27484 and sha(raw) == ZIP_SHA
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as z:
        assert z.testzip() is None
        prefix = "razr-ep5-ecad/"
        report_bytes = z.read(prefix + "report.json")
        report = json.loads(report_bytes)
        drc_bytes = z.read(prefix + "native-drc.json")
        drc = json.loads(drc_bytes)
        reader_bytes = z.read(prefix + "native-readback/readback.json")
        reader = json.loads(reader_bytes)
        assert report["expected_head"] == report["source_head_after"] == E3
        assert report["github_run_id"] == "40269456951"
        assert report["source_bytes_unchanged"] and report["input_board_project_bytes_unchanged"]
        assert report["source_sha256_before"] == report["source_sha256_after"]
        bindings = {}
        for name, expected in report["source_sha256_before"].items():
            data_s4 = subprocess.check_output(["git", "-C", str(args.repository), "show", S4 + ":" + name])
            data_e3 = subprocess.check_output(["git", "-C", str(args.repository), "show", E3 + ":" + name])
            assert data_s4 == data_e3 and sha(data_s4) == expected
            bindings[name] = {"S4_sha256": sha(data_s4), "E3_sha256": sha(data_e3), "runtime_before_after_sha256": expected}
        assert len(bindings) == 5
        for name, expected in report["files_sha256"].items():
            assert sha(z.read(prefix + name)) == expected
        assert report["passed"] and report["native_DRC_executed"]
        assert {c["label"]: c["exit_code"] for c in report["commands"]} == {"kicad-version": 0, "native-readback": 0, "native-drc": 0}
        assert report["kicad_release"] == drc["kicad_version"] == reader["kicad_release"] == "9.0.9"
        assert set(drc["included_severities"]) == {"error", "warning", "exclusion"}
        assert all(drc[k] == [] for k in ("violations", "unconnected_items", "schematic_parity"))
        assert reader["project_loaded"] and reader["input_bytes_unchanged"]
        assert reader["tracks"] == 130 and reader["footprints"] == 2
        assert reader["native_pad_objects"] == reader["unique_connected_terminals"] == 52
        assert reader["electrical_nets"] == [f"C{i:02}" for i in range(1, 27)]
        assert all(r["count"] == 0 for r in reader["drc_sections"])
        pads = {(p["reference"], p["pad"]): p for p in reader["native_pad_readback"]}
        assert len(pads) == len(reader["native_pad_readback"]) == 52
        for reference, y in (("JA", 3.0), ("JB", 185.0)):
            for n in range(1, 27):
                pad = pads[(reference, str(n))]
                assert pad["net"] == f"C{n:02}" and pad["size_mm"] == [0.25, 4.0]
                assert pad["drill_mm"] == [0.0, 0.0]
                assert abs(pad["position_mm"][0] - (-5 + (n - 1) * .4)) < 1e-12
                assert pad["position_mm"][1] == y
        for name, expected in reader["inputs_sha256"].items():
            assert sha(z.read(prefix + "artwork/" + name)) == expected
        false_keys = ["schematic_ERC_executed", "schematic_parity_requested", "OEM_assignment_qualified", "signal_integrity_or_power_qualified", "dynamic_FPC_qualified", "supplier_stackup_selected", "candidate_go", "fixture_fabrication_go", "manufacturing_go"]
        assert all(report[k] is False for k in false_keys)
        safe_report = {k: v for k, v in report.items() if k != "commands"}
        safe_report["commands"] = [{k: c[k] for k in ("label", "exit_code", "seconds", "log_sha256")} for c in report["commands"]]
        safe_report["projection_policy"] = "Original engineering values retained; command argv omitted. Original report identified by SHA-256."
        safe_report["original_report_sha256"] = sha(report_bytes)
        (args.output / "report.engineering.json").write_text(json.dumps(safe_report, indent=2) + "\n")
        (args.output / "native-drc.json").write_bytes(drc_bytes)
        (args.output / "native-readback.json").write_bytes(reader_bytes)
        for name in ("ep5_continuity26.kicad_pcb", "ep5_continuity26.kicad_pro", "conductor-schedule.csv", "flat-material-outline.json"):
            (args.output / name).write_bytes(z.read(prefix + "artwork/" + name))
        review = {"schema": "razr-E3-native-ECAD-S4-binding-independent-review-v1", "completed": True,
                  "source_execution_commit": E3, "functional_source_commit": S4,
                  "workflow_run_id": 40269456951, "artifact_id": 12628758762,
                  "artifact_bytes": len(raw), "artifact_sha256": ZIP_SHA,
                  "archive_CRC_checked": True, "reported_file_hashes_verified": len(report["files_sha256"]),
                  "five_source_files_exactly_equal_between_S4_E3_and_native_before_after": bindings,
                  "original_report_sha256": sha(report_bytes), "native_readback_sha256": sha(reader_bytes), "native_DRC_sha256": sha(drc_bytes),
                  "native_execution_reported_pass": True, "all_severities_including_exclusions_checked": True,
                  "independently_checked_terminal_identities_and_coordinates": 52, "tracks": 130, "channels": 26,
                  "new_native_execution_by_this_reader": False,
                  "new_physical_observations": 0, "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
                  "scope": "Existing E3 native KiCad 9.0.9 execution, independently bound byte-for-byte to S4 research ECAD sources. No OEM, SI, power, supplier stackup or physical qualification."}
        (args.output / "INDEPENDENT_REVIEW.json").write_text(json.dumps(review, indent=2) + "\n")
        for p in args.output.iterdir():
            b = p.read_bytes()
            assert b"/home/runner/" not in b and b"/workspace/" not in b and b"@" not in b
        print(json.dumps({k: review[k] for k in ("completed", "artifact_sha256", "reported_file_hashes_verified", "independently_checked_terminal_identities_and_coordinates", "tracks", "channels", "new_native_execution_by_this_reader")}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
