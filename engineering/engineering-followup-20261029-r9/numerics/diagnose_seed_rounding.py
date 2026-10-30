"""Locate a cross-runtime seed discrepancy without changing any acceptance gate."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time

import numpy as np
import scipy
from scipy.sparse import load_npz, vstack

from read_saved_fields import EXPECTED, need, sha, array_sha, equal_bits, read_array


def main(args):
    started = time.monotonic()
    w = args.work
    frozen = w / "n12/frozen/frozen/frozen/frozen/frozen"
    loads = frozen / "volume/panel/level-2/loads.npz"
    need(sha(loads) == EXPECTED["panel"]["loads"], "original load identity differs")
    with np.load(loads, allow_pickle=False) as z:
        R, F, fixed = z["R"], z["F"], z["D"]
    Cp = load_npz(frozen / "probe-N5/C.npz")
    Cf = load_npz(w / "n14/inputs/C-frame.npz")
    U = np.column_stack([read_array(args.n15 / f"four-load-full-arrays/final/load-{i}-field.npy", (344103,))
                         for i in range(4)])
    need(np.count_nonzero(U[fixed]) == 0, "fixed field differs")
    seed_root = w / "seed/original-linear-response-seed"
    response = seed_root / "response.npz"
    need(sha(response) == "26966337fafd2719476f865bff23e20a6160cb385af4f84ffe812a097d760aed", "original seed differs")
    points = json.loads((seed_root / "points.json").read_text())
    computed = {"G": np.asarray(Cp.T @ R), "qfree": np.asarray(Cp.T @ U),
                "initialgap": np.asarray([p.get("gap", 0.) for p in points], dtype=np.float64), "loadG": R.T @ F}
    comparisons = {}
    with np.load(response, allow_pickle=False) as z:
        historical = z["loadG"]
        for name, now in computed.items():
            prior = z[name]
            comparisons[name] = {"shape": list(now.shape), "bitwise_equal": equal_bits(now, prior),
                                 "numeric_unequal_entries": int(np.count_nonzero(now != prior)),
                                 "max_abs_difference": float(np.max(np.abs(now - prior))),
                                 "historical_array_sha256": array_sha(prior), "current_array_sha256": array_sha(now)}
    rounded = np.zeros((6, 4), dtype=np.float64)
    rows = []
    for j in range(6):
        for k in range(4):
            indices = np.flatnonzero((R[:, j] != 0) & (F[:, k] != 0))
            exact = sum((Fraction(float(R[i, j])) * Fraction(float(F[i, k])) for i in indices), Fraction())
            rounded[j, k] = float(exact)
            old, new = float(historical[j, k]), float(computed["loadG"][j, k])
            old_error, new_error = Fraction(old) - exact, Fraction(new) - exact
            spacing = math.ulp(float(exact))
            rows.append({"row": j, "column": k, "nonzero_product_count": len(indices),
                         "exact_sum": {"numerator": str(exact.numerator), "denominator": str(exact.denominator)},
                         "nearest_float64_to_exact_sum": float(exact), "historical": old, "current": new,
                         "historical_exact_error": float(old_error), "current_exact_error": float(new_error),
                         "historical_error_in_ulps": float(old_error) / spacing,
                         "current_error_in_ulps": float(new_error) / spacing})
    args.arrays.mkdir(exist_ok=True)
    arrays = {"historical-loadG.npy": historical, "current-loadG.npy": computed["loadG"],
              "nearest-exact-loadG.npy": rounded}
    identities = {}
    for name, value in arrays.items():
        path = args.arrays / name
        need(not path.exists(), "diagnostic output already exists")
        np.save(path, value, allow_pickle=False)
        identities[name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    savedC = load_npz(seed_root / "C.npz")
    C = vstack((Cp, Cf), format="csc")
    result = {"schema": "razr-r9-original-seed-rounding-diagnostic-v1", "completed": True,
              "source_sha256": sha(__file__), "shared_reader_sha256": sha(Path(__file__).with_name("read_saved_fields.py")),
              "runtime": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__},
              "original_inputs_unchanged": True, "original_acceptance_threshold_changed": False,
              "historical_runtime_reproduced": False, "current_seed_bitwise_reproduction_passed": all(r["bitwise_equal"] for r in comparisons.values()),
              "historical_seed_qualification_revoked": False,
              "reason": "A different-runtime auxiliary-map diagnostic does not replace the historical source-bound numerical execution.",
              "comparisons": comparisons, "loadG_exact_reference": rows, "saved_diagnostic_arrays": identities,
              "combined_C_buffers_equal": all(equal_bits(getattr(C, k), getattr(savedC, k)) for k in ["data", "indices", "indptr"]),
              "scope": "Reports the measured discrepancy; no revised tolerance, arbitrary RHS inverse, finite QP state, or current geometry FE qualification.",
              "seconds": time.monotonic() - started, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(comparisons, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["work", "n15", "arrays", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    main(p.parse_args())
