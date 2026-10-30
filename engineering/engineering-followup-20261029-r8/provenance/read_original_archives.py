"""Read immutable saved originals; this does not run CAD or a numerical solver."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tarfile
import time
import zipfile


ARCHIVES = {
    "RAZR-R7-method-diagnostics-and-supervision-complete-originals-20261028.zip":
        (53293490, "709500f8d11e3c4a98114de5777ab3a7605d0a324169fb74054cd6b5e1a77b9d", "libfile_2caa15dac6808191b426fda57b336694"),
    "RAZR-R7-native80-runtime-and-original-evidence-20261028.zip":
        (130335275, "99eca1ecc39c8f2a9334734535b5fb46da92204d13f577ffe733081801997ef7", "libfile_0565f7df7c1c8191a5406441e7dcf317"),
    "RAZR-R7-near-full-factory-and-independent-originals-20261028.zip":
        (126771580, "711db7175ea364735f337ecc575b7d7ee479df9287d78c7cec08a147120533ae", "libfile_03369f15bb2c819189c055031babf4ad"),
    "RAZR-SLIDE_N15_H_restore_four_load_science_20261027.zip":
        (40413347, "c3cc04b9c577b8cc1d4c884e9e4334a9533148757473d32334db65a886e3f4be", "libfile_913f997577a08191906bfe7f3ffb0ac5"),
    "RAZR-L6-original-envelope-complete-evidence-20261027.tar.gz":
        (2653823, "7b79b6362cc97b42af3a9312217fac909762f88743c03e288e64dc7230c93f55", "libfile_159f707246e0819185597ae68f77dc77"),
    "RAZR-L8-common-drift-and-outward-failure-complete-evidence-20261027.tar.gz":
        (384907, "6d4d295114b16b1bfb7ebfb79d57fb1dc9841e370b2727f35bfb3a33be3f27b3", "libfile_7275a60bd5648191b4afa459f7120855"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(stream):
    return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive-root", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    require(not args.output.exists(), "output must be new")
    start = time.monotonic()
    records = []
    for name, (size, sha, library_id) in ARCHIVES.items():
        path = args.archive_root / name
        with path.open("rb") as stream:
            actual_sha = digest(stream)
        require(path.stat().st_size == size and actual_sha == sha, "archive identity differs: " + name)
        members = []
        if name.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    with archive.open(member) as stream:
                        member_sha = digest(stream)  # Full read also checks CRC.
                    members.append((member.filename, member.file_size, member_sha))
        else:
            with tarfile.open(path, "r:gz") as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    with archive.extractfile(member) as stream:
                        member_sha = digest(stream)
                    members.append((member.name, member.size, member_sha))
        require(len({m[0] for m in members}) == len(members), "duplicate member paths: " + name)
        records.append({"file_name": name, "bytes": size, "sha256": sha,
                        "saved_original_library_file_id": library_id,
                        "regular_member_count": len(members),
                        "all_regular_member_bytes_read": True,
                        "member_digest_index_sha256": hashlib.sha256(json.dumps(members, separators=(",", ":")).encode()).hexdigest()})
    numeric_name = "RAZR-SLIDE_N15_H_restore_four_load_science_20261027.zip"
    with zipfile.ZipFile(args.archive_root / numeric_name) as archive:
        def read(name):
            raw = archive.read(name)
            return json.loads(raw), {"archive": numeric_name, "member": name,
                                     "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        panel, panel_id = read("original-probe-qualification/panel/N13-v3-independent-readback.json")
        frame, frame_id = read("original-probe-qualification/frame/FRAME_INDEPENDENT_READBACK.json")
        h, h_id = read("independent-audit/H_EXECUTED_READBACK_SUMMARY.json")
        full_h, full_h_id = read("actual-results/combined-H-independent-readback/report.json")
    require(h["original_report"]["sha256"] == full_h_id["sha256"], "complete saved H report identity differs")
    for body, report in (("panel", panel), ("frame", frame)):
        values = report["original_five_ratios"]
        require(report["original_five_qualification_verified"] and len(values) == 5, body + " five-probe report differs")
        require(all(0 <= x <= 1e-7 for x in values), body + " original threshold differs")
        require(values == [x["saved_native_residual_ratio"] for x in h["bodies"][body]["five_original_field_actions"]], body + " H report residuals disagree")
    result = {
        "schema": "razr-r8-immutable-original-archive-readback-v1",
        "repository_base_commit": "e51de63915a1abeed29e2f95be3044a5d5965045",
        "functional_S4_commit": "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560",
        "archives": records,
        "numeric_original_report_identities": [panel_id, frame_id, h_id, full_h_id],
        "original_panel_residuals": panel["original_five_ratios"],
        "original_frame_residuals": frame["original_five_ratios"],
        "original_threshold": 1e-7,
        "saved_H_and_restore_report_accepted": h["both_body_complete_H_accepted"] and h["original_combined_ExactResponseCache_restore_passed"],
        "saved_restore_maximum_relative_error": h["original_ExactResponseCache_restore"]["largest_relative_error"],
        "new_CAD_or_solver_execution": False,
        "full_probe_fields_or_K_recomputed_this_run": False,
        "current_candidate_FE_qualified": False,
        "physical_qualification": False,
        "all_blockers_closed": False,
        "scope": "Exact whole archive and every regular member read; saved original reports compared. Original numerical full-field/K/C/response dependencies retain their separate existing archives and are not recomputed here.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "elapsed_seconds": time.monotonic() - start,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"archives": len(records), "members": sum(r["regular_member_count"] for r in records),
                      "original_reports_agree": True, "seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
