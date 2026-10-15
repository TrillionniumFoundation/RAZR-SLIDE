#!/usr/bin/env python3
"""One process per legacy module to prevent same-name import cross-contamination."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import unittest


def acceptable(result: unittest.TestResult, minimum: int) -> bool:
    return (type(minimum) is int and minimum > 0 and result.testsRun >= minimum
            and result.wasSuccessful() and not result.skipped and not result.expectedFailures)


class IdentifiedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_ids = []

    def startTest(self, test):
        self.test_ids.append(test.id())
        super().startTest(test)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--extra-path", action="append", default=[])
    parser.add_argument("--minimum", required=True, type=int)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    sys.path[:0] = [str(args.directory.resolve()), *args.extra_path,
                    str(Path(__file__).resolve().parents[1])]
    suite = unittest.defaultTestLoader.discover(str(args.directory), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2, resultclass=IdentifiedResult).run(suite)
    ok = acceptable(result, args.minimum)
    data = {"tests_run": result.testsRun, "minimum_tests": args.minimum,
            "test_ids": result.test_ids, "failures": len(result.failures),
            "errors": len(result.errors), "skipped": len(result.skipped),
            "expected_failures": len(result.expectedFailures),
            "unexpected_successes": len(result.unexpectedSuccesses), "passed": ok,
            "manufacturing_go": False}
    args.report.write_text(json.dumps(data, indent=2) + "\n")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
