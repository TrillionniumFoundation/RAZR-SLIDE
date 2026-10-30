"""Cross-runtime readback of the finite original H and saved-action contract.

No H column is solved here. All 7770 original column records and retained H
projections are checked; missing basis full fields are not reconstructed.
The actual unchanged ExactResponseCache.restore runs with only the original
five ordered SHA-bound full-field responses. Unknown RHS are rejected.
"""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time
import traceback

import numpy as np
import scipy
from scipy.sparse import load_npz, vstack

from read_saved_fields import EXPECTED, array_sha, equal_bits, need, read_array, sha

M = 3885
H_READER_REPORT = "292b23cf138d0861e9aca3cb35ecc651c28737fa5ee13c9ad49aed97e49a094e"
CACHE_SOURCES = {
    "contact_exchange.py": "db1f426d89dfba88bb7d7ed6955e8b92a620c0babc9d4036ee3c0ba1d5be6064",
    "contact_patch_audit.py": "6e6ee08ecf2eac3539edab1f9c18be8cfed8e6dc03f80a3010dc48bc7c612100",
}


def raw_statistics(H):
    scale = 1e-300
    difference = 0.
    for lo in range(0, M, 128):
        hi = min(lo + 128, M)
        block = H[lo:hi]
        need(np.isfinite(block).all(), "nonfinite H")
        scale = max(scale, float(np.max(np.abs(block))))
        difference = max(difference, float(np.max(np.abs(block - H[:, lo:hi].T))))
    diagonal = float(np.min(np.diag(H)))
    need(difference <= 2e-8 * scale and diagonal >= -2e-8 * scale,
         "original raw reciprocity or diagonal self-energy criterion failed")
    return {"absolute_scale": scale, "max_raw_asymmetry": difference,
            "relative_raw_asymmetry": difference / scale, "minimum_diagonal": diagonal,
            "original_reciprocity_and_self_energy_passed": True}


def symmetric_in_place(H):
    # Preserve the original operation and blocking order.
    for lo in range(0, M, 128):
        hi = min(lo + 128, M)
        for col in range(lo, M, 128):
            end = min(col + 128, M)
            average = (H[lo:hi, col:end] + H[col:end, lo:hi].T) * .5
            H[lo:hi, col:end] = average
            H[col:end, lo:hi] = average.T


def main(args):
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    out = {"schema": "razr-r9-independent-saved-H-restore-readback-v1", "completed": False,
           "source_sha256": sha(__file__), "shared_reader_sha256": sha(Path(__file__).with_name("read_saved_fields.py")),
           "runtime": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__},
           "historical_runtime_reproduced": False, "solver_executed": False,
           "all_7770_K_products_recomputed": False, "all_successful_H_column_full_fields_retained": False,
           "arbitrary_RHS_inverse_qualified": False, "current_geometry_FE_qualified": False,
           "finite_QP_resume_qualified": False, "bodies": {}}
    try:
        need(not sys.flags.optimize, "optimized Python prohibited")
        w = args.work
        n15 = args.n15
        prior_path = n15 / "actual-results/combined-H-independent-readback/report.json"
        need(sha(prior_path) == H_READER_REPORT, "original H reader report identity differs")
        prior = json.loads(prior_path.read_text())
        need(prior["completed"] and prior["original_combined_ExactResponseCache_restore_passed"],
             "original complete H readback missing")
        out["historical_reader_report_sha256"] = H_READER_REPORT
        # Bind this new restoration to this turn's actual full native K products.
        fresh_panel = json.loads(args.panel_readback.read_text())
        fresh_frame = json.loads(args.frame_readback.read_text())
        need(fresh_panel["completed"] and fresh_panel["original_five_qualification_verified"], "panel replay failed")
        need(fresh_frame["completed"] and fresh_frame["all_original_action_gates_passed"], "frame replay failed")
        out["fresh_native_readbacks"] = {"panel": sha(args.panel_readback), "frame": sha(args.frame_readback)}
        frozen = w / "n12/frozen/frozen/frozen/frozen/frozen"
        cfg = {
            "panel": (frozen / "probe-N5/C.npz", frozen / "volume/panel/level-2/loads.npz",
                      w / "n13/native/N13-v3/last-accepted", w / "panel-h/runs"),
            "frame": (w / "n14/inputs/C-frame.npz", w / "frame-volume/frame/level-2/loads.npz",
                      w / "n14/native/frame-numeric/final", w / "frame-h/runs"),
        }
        rng = np.random.default_rng(73021)
        directions = [np.ones(M)] + [rng.choice([-1., 1.], M) for _ in range(4)]
        Cs = {}
        Hs = {}
        fields = {}
        rhs_digests = {}
        for body, (cp, lp, fp, hp) in cfg.items():
            ex = EXPECTED[body]
            need(sha(cp) == ex["C"] and sha(lp) == ex["loads"], "original C/loads differs")
            C = load_npz(cp)
            need(C.format == "csc" and C.shape == (ex["n"], M) and C.dtype == np.float64,
                 "C shape/precision differs")
            with np.load(lp, allow_pickle=False) as z:
                fixed = z["D"]
            free = np.setdiff1d(np.arange(ex["n"]), fixed)
            prior_body = prior["bodies"][body]
            prior_rows = {r["index"]: r for r in prior_body["accepted_column_records"]}
            need(set(prior_rows) == set(range(M)), "historical H coverage differs")
            H = np.empty((M, M), dtype=np.float64)
            covered = set()
            block_records = []
            excluded_failed_history = []
            accepted_report_shas = {r["report_sha256"] for r in prior_rows.values()}
            for report_path in sorted(hp.glob("*/H_BLOCK_REPORT.json")):
                report = json.loads(report_path.read_text())
                digest = sha(report_path)
                if digest not in accepted_report_shas:
                    # The archive deliberately retains the original failed 8:520
                    # attempt. Select only the immutable completed-reader roster.
                    # An unknown extra report cannot silently become an exclusion.
                    need(body == "frame" and digest == "7bb2c07183825515329f0e2aebe5b6d77ae8e29b29c2fa86e84a7935a1662ace"
                         and not report["execution_completed"], "unknown H block outside qualified roster")
                    excluded_failed_history.append({"report_sha256": digest,
                                                    "record": report_path.parent.name,
                                                    "execution_completed": False,
                                                    "promoted_to_complete_H": False})
                    continue
                need(report["body"] == body and report["execution_completed"]
                     and report["all_columns_original_gate_passed"] and not report["preservation_failures"],
                     "failed H block cannot qualify")
                need(report["original_threshold"] == 1e-7 and not report["failed_columns"]
                     and not report["diagnostic_files"], "unexpected changed correction history")
                need(report["original_Kff"] == prior_body["original_Kff"], "different Kff in H block")
                fresh_buffers = (fresh_panel["original_Kff_buffer_hashes"] if body == "panel"
                                 else fresh_frame["Kff_buffer_hashes"])
                need(all(report["original_Kff"][k]["sha256"] == fresh_buffers[k] for k in fresh_buffers),
                     "H Kff differs from freshly read operator")
                for key in ["K", "loads", "C"]:
                    need(report["original_input_sha256"][key + ".npz"] == ex[key], "H input identity differs")
                indices = report["indices"]
                need(indices == sorted(set(indices)) and not covered.intersection(indices), "duplicated H basis")
                need([r["index"] for r in report["columns"]] == indices, "H column ordering differs")
                block_path = report_path.parent / report["block"]["file"]
                need(block_path.resolve().is_relative_to(report_path.parent.resolve()), "escaped H file")
                need(sha(block_path) == report["block"]["sha256"]
                     and block_path.stat().st_size == report["block"]["bytes"], "H block bytes differ")
                block = read_array(block_path, (M, len(indices)))
                for pos, row in enumerate(report["columns"]):
                    index = row["index"]
                    old = prior_rows[index]
                    need(old["report_sha256"] == digest, "H block not bound by original completed reader")
                    need(row["passes"] and row["threshold"] == 1e-7 and row["ratio"] <= 1e-7
                         and row["ratio"] == old["ratio"] and row["correction_count"] == 0,
                         "original H basis gate record differs")
                    direction = np.zeros(M)
                    direction[index] = 1.
                    rhs = np.asarray(C @ direction).ravel()
                    need(array_sha(rhs) == row["rhs_full_array_sha256"]
                         and array_sha(rhs[free]) == row["rhs_free_array_sha256"], "original H basis RHS differs")
                    need(max(float(np.max(np.abs(rhs[free]))), 1.) == row["normalization_denominator"],
                         "H denominator differs")
                    need(array_sha(block[:, pos]) == row["projection_array_sha256"]
                         == old["projection_array_sha256"], "H projection differs")
                    need(float(block[index, pos]) == row["self_energy"], "recorded self energy differs")
                    for key in ["field_full_array_sha256", "residual_free_array_sha256"]:
                        need(row[key] == old[key], "basis field/residual digest differs")
                    H[:, index] = block[:, pos]
                covered.update(indices)
                block_records.append({"report_sha256": digest, "columns": len(indices),
                                      "H_block_sha256": report["block"]["sha256"]})
            need(covered == set(range(M)), "H full basis not covered")
            need(array_sha(H) == prior_body["raw_H_array_sha256"], "assembled raw H differs")
            raw = raw_statistics(H)
            need(all(raw[k] == prior_body["raw_global_checks"][k] for k in raw), "raw H checks differ")
            out["bodies"][body] = {"columns": len(covered), "blocks": block_records,
                                    "excluded_failed_history": excluded_failed_history,
                                    "raw_H_array_sha256": array_sha(H), "raw_global_checks": raw,
                                    "all_basis_RHS_and_projection_digests_recomputed": True,
                                    "basis_K_products_recomputed": False}
            Cs[body] = C
            Hs[body] = H
            fields[body] = [read_array(fp / f"probe-{i}-field.npy", (ex["n"],)) for i in range(5)]
            for i, field in enumerate(fields[body]):
                old = prior_body["five_original_field_actions"][i]
                need(sha(fp / f"probe-{i}-field.npy") == old["full_field_file_sha256"], "saved action field differs")
                need(np.count_nonzero(field[fixed]) == 0, "nonzero fixed displacement")
            rhs_digests[body] = [array_sha(np.asarray(C @ d).ravel()) for d in directions]
            need(rhs_digests[body] == [a["full_RHS_array_sha256"] for a in prior_body["five_original_field_actions"]],
                 "five original RHS differ")
            del block, rhs
        combined_raw = Hs["panel"] + Hs["frame"]
        raw_prior = prior["combined_unsymmetrized_raw_H_checks"]
        need(array_sha(combined_raw) == raw_prior["row_major_float64_array_sha256"], "raw combined H differs")
        out["combined_raw_checks"] = raw_statistics(combined_raw)
        out["combined_raw_array_sha256"] = array_sha(combined_raw)
        del combined_raw
        for body in ["panel", "frame"]:
            symmetric_in_place(Hs[body])
            need(array_sha(Hs[body]) == prior["bodies"][body]["derived_symmetric_H_array_sha256"],
                 "original block symmetrization differs")
        H = Hs.pop("panel")
        H += Hs.pop("frame")
        C = vstack((Cs["panel"], Cs["frame"]), format="csc")
        seed_path = w / "seed/original-linear-response-seed/response.npz"
        need(sha(seed_path) == "26966337fafd2719476f865bff23e20a6160cb385af4f84ffe812a097d760aed",
             "original seed bytes differ")
        with np.load(seed_path, allow_pickle=False) as seed:
            need(equal_bits(H, seed["H"]), "reconstructed H differs from saved exact seed")
        out["derived_H_equals_original_seed_bitwise"] = True
        integration = w / "n12/source/S4/integration"
        for name, digest in CACHE_SOURCES.items():
            need(sha(integration / name) == digest, "original cache source differs")
        sys.path.insert(0, str(integration))
        spec = importlib.util.spec_from_file_location("r9_original_contact_exchange", integration / "contact_exchange.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        identity = prior["reconstructed_combined_identity_for_original_cache_method"]
        count = 0

        def original_five(rhs):
            nonlocal count
            need(count < 5 and rhs.shape == (818829,), "response outside saved five-action contract")
            need(array_sha(rhs[:344103]) == rhs_digests["panel"][count]
                 and array_sha(rhs[344103:]) == rhs_digests["frame"][count], "unknown or reordered RHS")
            value = np.concatenate((fields["panel"][count], fields["frame"][count]))
            count += 1
            return value

        cache = module.ExactResponseCache(818829, original_five, identity)
        check = cache.restore(C, H, identity, probes=5, relative_tolerance=2e-7)
        need(count == 5 and check.response_calls == 5 and check.probes == 5
             and check.largest_relative_error <= 2e-7 and equal_bits(H, cache.H), "saved-action restore failed")
        out["original_ExactResponseCache_restore"] = vars(check)
        out["original_cache_source_sha256"] = CACHE_SOURCES
        out["callback_scope"] = "Exactly five original ordered SHA-bound saved full-field actions; unknown RHS rejected."
        out["restored_H_array_sha256"] = array_sha(cache.H)
        out["completed"] = True
    except BaseException as exc:
        out["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        traceback.print_exc()
    out["seconds"] = time.monotonic() - started
    out["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with args.output.open("x") as stream:
        json.dump(out, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: out.get(k) for k in ["completed", "failure", "seconds", "peak_rss_kib"]}))
    return 0 if out["completed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["work", "n15", "panel-readback", "frame-readback", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
