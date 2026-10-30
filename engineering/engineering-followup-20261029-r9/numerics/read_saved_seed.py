"""Recompute the original linear seed's auxiliary maps from preserved fields.

This is a readback of the historical linear seed. It does not create a contact
QP state, resume a driver, or transfer historical FE to current geometry.
"""
import argparse
import json
from pathlib import Path
import resource
import sys
import time
import traceback

import numpy as np
import scipy
from scipy.sparse import load_npz, vstack

from read_saved_fields import EXPECTED, need, sha, array_sha, equal_bits, read_array


def main(args):
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    result = {"schema": "razr-r9-original-linear-seed-readback-v1", "completed": False,
              "source_sha256": sha(__file__), "shared_reader_sha256": sha(Path(__file__).with_name("read_saved_fields.py")),
              "runtime": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__},
              "historical_runtime_reproduced": False, "solver_executed": False,
              "trace_driver_executed": False, "finite_QP_resume_qualified": False,
              "current_geometry_FE_qualified": False}
    try:
        need(not sys.flags.optimize, "optimized Python prohibited")
        hcheck = json.loads(args.h_readback.read_text())
        four = json.loads(args.four_readback.read_text())
        need(hcheck["completed"] and hcheck["derived_H_equals_original_seed_bitwise"]
             and four["completed"] and four["all_original_action_gates_passed"], "fresh H or full-field prerequisite failed")
        result["fresh_prerequisites_sha256"] = {"H": sha(args.h_readback), "four_loads": sha(args.four_readback)}
        w = args.work
        frozen = w / "n12/frozen/frozen/frozen/frozen/frozen"
        lp = frozen / "volume/panel/level-2/loads.npz"
        lf = w / "frame-volume/frame/level-2/loads.npz"
        cp = frozen / "probe-N5/C.npz"
        cf = w / "n14/inputs/C-frame.npz"
        need(sha(lp) == EXPECTED["panel"]["loads"] and sha(cp) == EXPECTED["panel"]["C"]
             and sha(lf) == EXPECTED["frame"]["loads"] and sha(cf) == EXPECTED["frame"]["C"], "original input differs")
        with np.load(lp, allow_pickle=False) as z:
            R, F, fixed = z["R"], z["F"], z["D"]
        with np.load(lf, allow_pickle=False) as z:
            need(z["F"].shape == (474726, 0), "original frame external map differs")
        need(R.shape == (344103, 6) and F.shape == (344103, 4), "original maps differ")
        Cp, Cf = load_npz(cp), load_npz(cf)
        fields = args.n15 / "four-load-full-arrays"
        U = np.column_stack([read_array(fields / f"final/load-{i}-field.npy", (344103,)) for i in range(4)])
        need(np.count_nonzero(U[fixed]) == 0, "nonzero fixed displacement")
        seed_root = w / "seed/original-linear-response-seed"
        response_path = seed_root / "response.npz"
        need(sha(response_path) == "26966337fafd2719476f865bff23e20a6160cb385af4f84ffe812a097d760aed", "original seed differs")
        points_path = seed_root / "points.json"
        need(sha(points_path) == "682a157686b06b4d8a1c8f431eab3453b9a43594801df148c03594435c4bf796", "points differ")
        points = json.loads(points_path.read_text())
        need(len(points) == 3885 and points[:4] == [{"kind": "bolt", "index": i} for i in range(4)], "point ordering differs")
        computed = {"G": np.asarray(Cp.T @ R), "loadG": R.T @ F,
                    "qfree": np.asarray(Cp.T @ U),
                    "initialgap": np.asarray([p.get("gap", 0.) for p in points], dtype=np.float64)}
        free = np.setdiff1d(np.arange(344103), fixed)
        need(equal_bits(computed["qfree"], np.asarray(Cp[free].T @ U[free])), "full/free projection differs")
        with np.load(response_path, allow_pickle=False) as seed:
            need(set(seed.files) == {"H", "G", "loadG", "qfree", "initialgap"}, "seed key set differs")
            for name, value in computed.items():
                need(equal_bits(value, seed[name]), "original auxiliary bytes differ: " + name)
        C = vstack((Cp, Cf), format="csc")
        savedC = load_npz(seed_root / "C.npz")
        need(C.shape == savedC.shape == (818829, 3885) and
             all(equal_bits(getattr(C, k), getattr(savedC, k)) for k in ["data", "indices", "indptr"]),
             "original combined force map differs")
        result["auxiliary_arrays"] = {name: {"shape": list(value.shape), "dtype": value.dtype.str,
                                            "sha256": array_sha(value), "bitwise_equal_to_saved_seed": True}
                                      for name, value in computed.items()}
        result["full_and_fixed_zero_free_qfree_projections_bit_equal"] = True
        result["combined_C_native_buffers_bit_equal"] = True
        result["original_seed_sha256"] = sha(response_path)
        result["scope"] = "Historical linear response seed only; no finite QP state or physical qualification."
        result["completed"] = True
    except BaseException as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        traceback.print_exc()
    result["seconds"] = time.monotonic() - started
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: result.get(k) for k in ["completed", "failure", "seconds", "peak_rss_kib"]}))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["work", "n15", "h-readback", "four-readback", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
