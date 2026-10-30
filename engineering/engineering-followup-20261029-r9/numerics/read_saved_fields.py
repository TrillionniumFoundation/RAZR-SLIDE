"""Read original saved fields on the observed runtime, without a numerical solver.

This is a new cross-runtime reader. It does not modify or invoke the historical
version-gated N14 producer/reader, and does not claim the historical runtime.
The original CSC buffers, one-dimensional products and 1e-7 gate are fixed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
import traceback

import numpy as np
import scipy
from scipy.sparse import load_npz

EXPECTED = {
    "frame": {"n": 474726, "fixed": 777,
        "K": "e077f8d0176c041041b984b5dbb016e140219b34223d235ac739978b1dddd95d",
        "loads": "eb2b180696785a77b71412506760df974fbf54c800090e36f027f2aaf70135a3",
        "C": "66b4328416302b37948f8f4258678dd0e24526af3303c2f228a84e3694a1e55e",
        "report": "571226abebdca4f992515db4ff2faa7e32c64c0a7e5aba21f5748bb57d1d5ee3"},
    "panel": {"n": 344103, "fixed": 6,
        "K": "80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb",
        "loads": "811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6",
        "C": "9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f",
        "report": "3387d687c553461ae29fd7fdecbe5ee9085875a27aae384d52bb7d9fea32b861"},
}


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def equal_bits(left, right):
    return left.shape == right.shape and left.dtype == right.dtype and left.tobytes() == right.tobytes()


def read_array(path, shape):
    value = np.load(path, allow_pickle=False)
    need(value.shape == shape and value.dtype == np.float64 and np.isfinite(value).all(),
         "saved array shape, precision or finiteness differs")
    return value


def main(args):
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    body = "frame" if args.mode == "frame-five" else "panel"
    ex = EXPECTED[body]
    result = {"schema": "razr-r9-saved-field-independent-native-readback-v1",
              "mode": args.mode, "completed": False, "source_sha256": sha(__file__),
              "runtime": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__},
              "historical_runtime_reproduced": False, "solver_executed": False,
              "arbitrary_RHS_inverse_qualified": False, "current_geometry_FE_qualified": False,
              "original_threshold": 1e-7}
    checked_files = {}

    def identity(path, expected):
        rec = {"bytes": path.stat().st_size, "sha256": sha(path)}
        need(rec["sha256"] == expected, "input identity mismatch: " + path.name)
        checked_files[path] = rec
        return rec

    try:
        need(not sys.flags.optimize, "optimized Python prohibited")
        result["source_report_identity"] = identity(args.report, ex["report"])
        report = json.loads(args.report.read_text())
        need(report["execution_completed"] and not report["preservation_failures"], "incomplete producer")
        need(report["original_threshold"] == 1e-7, "changed original gate")
        result["original_inputs"] = {
            "K": identity(args.volume / "K.npz", ex["K"]),
            "loads": identity(args.volume / "loads.npz", ex["loads"]),
            "C": identity(args.C, ex["C"]),
        }
        for name, rec in report["files"].items():
            path = args.fields / name
            need(path.resolve().is_relative_to(args.fields.resolve()), "escaped evidence reference")
            actual = identity(path, rec["sha256"])
            need(actual["bytes"] == rec["bytes"], "evidence length differs")
        result["full_array_file_identities_verified"] = len(report["files"])
        with np.load(args.volume / "loads.npz", allow_pickle=False) as loads:
            fixed = loads["D"]
            F = loads["F"] if body == "panel" else None
        need(fixed.ndim == 1 and len(fixed) == ex["fixed"] and len(np.unique(fixed)) == len(fixed),
             "fixed DOF set differs")
        free = np.setdiff1d(np.arange(ex["n"]), fixed)
        C = load_npz(args.C)
        K = load_npz(args.volume / "K.npz")
        need(K.format == "csc" and K.shape == (ex["n"], ex["n"]) and K.dtype == np.float64,
             "original native CSC operator required")
        A = K[free][:, free].tocsc()
        del K
        result["Kff_buffer_hashes"] = {key: array_sha(getattr(A, key)) for key in ["data", "indices", "indptr"]}
        for key, digest in result["Kff_buffer_hashes"].items():
            need(digest == report["original_Kff"][key]["sha256"], "native CSC buffer changed")
        rng = np.random.default_rng(73021)
        directions = [np.ones(3885)] + [rng.choice([-1., 1.], 3885) for _ in range(4)]
        rows = report["probes"] if body == "frame" else report["loads"]
        need(len(rows) == (5 if body == "frame" else 4), "incomplete original action set")
        scalar_rows = []
        fields = []
        for index, row in enumerate(rows):
            if body == "frame":
                need(row["probe_index"] == index and report["original_probe_seed"] == 73021,
                     "probe identity differs")
                direction = read_array(args.fields / f"probe-{index}/direction.npy", (3885,))
                need(equal_bits(direction, directions[index]), "original direction changed")
                rhs = np.asarray(C @ direction).ravel()
                rhs_path = args.fields / f"probe-{index}/rhs-full.npy"
            else:
                need(row["index"] == index and F.shape == (ex["n"], 4), "four load identity differs")
                rhs = F[:, index].copy()
                rhs_path = args.fields / row["rhs_full_file"]
            need(equal_bits(rhs, read_array(rhs_path, (ex["n"],))), "original full RHS bytes differ")
            # These recorded runs accepted their first field. A new correction history
            # must not be silently interpreted by this finite replay contract.
            need(len(row["steps"]) == 1 and row["steps"][0]["step"] == 0,
                 "unexpected correction history in immutable recorded run")
            step = row["steps"][0]
            need(step == row["final"], "final field is not actual last step")
            field = read_array(args.fields / step["field"], (ex["n"],))
            need(equal_bits(field[fixed], np.zeros(len(fixed))), "fixed values differ")
            b = rhs[free]
            residual = A @ field[free] - b
            need(equal_bits(residual, read_array(args.fields / step["residual"], (len(free),))),
                 "original scalar native residual bytes differ")
            numerator = float(np.max(np.abs(residual)))
            denominator = max(float(np.max(np.abs(b))), 1.)
            ratio = numerator / denominator
            need(numerator == step["residual_numerator"] and denominator == step["normalization_denominator"]
                 and ratio == step["free_dof_residual_infinity_ratio"] and ratio <= 1e-7,
                 "original scalar residual gate differs")
            prefix = "probe" if body == "frame" else "load"
            for kind, saved_name in [("field", step["field"]), ("residual", step["residual"])]:
                need(sha(args.fields / f"final/{prefix}-{index}-{kind}.npy") == sha(args.fields / saved_name),
                     "final alias differs from actual field")
            scalar_rows.append({"index": index, "ratio": ratio, "threshold": 1e-7,
                                "residual_bytes_equal": True, "residual_array_sha256": array_sha(residual),
                                "rhs_array_sha256": array_sha(rhs), "corrections": 0})
            fields.append(field)
        result["scalar_actions"] = scalar_rows
        if body == "panel":
            U = np.column_stack(fields)
            block_residual = A @ U[free] - F[free]
            need(equal_bits(block_residual, read_array(args.fields / "block/native-residual.npy", (len(free), 4))),
                 "original two-dimensional native residual differs")
            block_ratio = float(np.max(np.abs(block_residual))) / max(float(np.max(np.abs(F))), 1.)
            need(block_ratio == report["external_block_native_gate"]["ratio"]
                 and block_ratio <= 1e-7, "original two-dimensional gate differs")
            result["original_2D_block_gate"] = {"ratio": block_ratio, "threshold": 1e-7,
                                                 "native_residual_bytes_equal": True,
                                                 "residual_array_sha256": array_sha(block_residual)}
        for path, rec in checked_files.items():
            need(path.stat().st_size == rec["bytes"] and sha(path) == rec["sha256"], "input changed during readback")
        result["completed"] = True
        result["all_original_action_gates_passed"] = True
    except BaseException as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        traceback.print_exc()
    result["seconds"] = time.monotonic() - started
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: result.get(k) for k in ["mode", "completed", "failure", "seconds", "peak_rss_kib"]}))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["frame-five", "panel-four-loads"], required=True)
    for name in ["volume", "C", "report", "fields", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
