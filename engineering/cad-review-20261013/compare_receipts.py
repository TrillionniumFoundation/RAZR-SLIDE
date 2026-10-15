"""Compare numerical/geometric receipts without requiring identical STEP serialization."""
import argparse
import json
import math
from pathlib import Path


def compare(expected, actual, path="", tolerance=1e-5):
    if isinstance(expected, dict):
        excluded = {"environment", "elapsed_s"}
        if path.startswith("/new_STEP_exports/"):
            excluded.add("sha256")
        a = {k: v for k, v in expected.items() if k not in excluded}
        b = {k: v for k, v in actual.items() if k not in excluded}
        if set(a) != set(b):
            raise AssertionError(path + ": different keys")
        for key in a:
            compare(a[key], b[key], path + "/" + key, tolerance)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise AssertionError(path + ": different list length")
        for index, (a, b) in enumerate(zip(expected, actual)):
            compare(a, b, path + "/" + str(index), tolerance)
    elif isinstance(expected, bool):
        if expected is not actual:
            raise AssertionError(path + ": different boolean")
    elif isinstance(expected, (int, float)):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            raise AssertionError(path + ": numerical type mismatch")
        if not math.isfinite(expected) or not math.isfinite(actual):
            raise AssertionError(path + ": nonfinite number")
        if isinstance(expected, int):
            ok = expected == actual
        else:
            ok = math.isclose(expected, actual, rel_tol=1e-8, abs_tol=tolerance)
        if not ok:
            raise AssertionError(f"{path}: {expected!r} != {actual!r}")
    elif expected != actual:
        raise AssertionError(path + ": different value")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    arguments = parser.parse_args()
    a = json.loads(arguments.expected.read_text())
    b = json.loads(arguments.actual.read_text())
    compare(a, b)
    print(json.dumps({"numerical_and_geometric_semantics_match": True,
        "abs_tolerance_mm_or_mm3": 1e-5, "STEP_bytes_not_compared": True,
        "pose_count": b["pose_count"], "manufacturing_go": b["manufacturing_go"]}))
