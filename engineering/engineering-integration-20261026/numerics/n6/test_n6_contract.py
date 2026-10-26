"""Small correctness/privacy contracts; never load the large numerical problem."""
from array import array
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import audit_n6_row as producer
import readback_n6_row as reader
from n6_evidence_io import AuditGateError, ND, ORIGINAL_FIXED_ORDER, read_npy, validate_original_domain
from export_n6_engineering import export


def npy(descr, shape, payload, fortran=False):
    h = repr({"descr": descr, "fortran_order": fortran, "shape": shape})
    h = (h + " " * ((-len(h) - 11) % 64) + "\n").encode("latin1")
    return b"\x93NUMPY\x01\x00" + struct.pack("<H", len(h)) + h + payload


class Contracts(unittest.TestCase):
    def test_real_original_unsorted_fixed_order_counterexample(self):
        proof = json.loads((Path(__file__).resolve().parent / "N6B_FIXED_DOMAIN_ORDER_EVIDENCE.json").read_text())
        raw = bytes.fromhex(proof["actual_original_NPY_hex"])
        self.assertEqual(len(raw), 176)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "c5253eefb07da8a1e680eb31d3c6bb5d1d181a44ed1161f50aa6370c84709205")
        fixed, unused = read_npy(io.BytesIO(raw))
        self.assertEqual(tuple(fixed), ORIGINAL_FIXED_ORDER)
        self.assertNotEqual(list(fixed), sorted(fixed))
        free = array("q", (i for i in range(ND) if i not in set(fixed)))
        validate_original_domain(free, fixed)
        with self.assertRaisesRegex(AuditGateError, "original_fixed_order_preserved"):
            validate_original_domain(free, sorted(fixed))
        with self.assertRaisesRegex(AuditGateError, "original_fixed_unique_and_in_range"):
            validate_original_domain(free, [0, 1, 2, 13, 14, 14])
        free[0], free[1] = free[1], free[0]
        with self.assertRaisesRegex(AuditGateError, "original_free_exact_sorted_complement"):
            validate_original_domain(free, fixed)

    def test_exact_cancellation_and_independent_replay(self):
        a, u = [1.0, 1.0, 1.0], [1e16, 1.0, -1e16]
        r = producer.dot_audit(a, u, 0.0, trace=True)
        computed, exact = reader.independently_check_arithmetic(r, a, u, 0.0)
        self.assertEqual((computed, exact), (0.0, Fraction(1)))
        self.assertEqual(r["accumulation_rounding_error_exact"]["numerator"], "-1")
        r["accumulation_rounding_error_exact"]["numerator"] = "0"
        with self.assertRaises(AuditGateError):
            reader.independently_check_arithmetic(r, a, u, 0.0)

    def test_product_and_subtraction_errors_are_exact_dyadics(self):
        a, u, b = [1.1, -7.3, 2.2], [1.3, 0.1, 0.7], 0.8
        r = producer.dot_audit(a, u, b, trace=True)
        computed, exact = reader.independently_check_arithmetic(r, a, u, b)
        reference = sum((Fraction.from_float(x) * Fraction.from_float(y) for x, y in zip(a, u)), Fraction()) - Fraction.from_float(b)
        self.assertEqual(exact, reference)
        self.assertNotEqual(r["product_rounding_error_exact"]["numerator"], "0")
        self.assertEqual(r["sequential_float64_residual"]["float64"], computed)

    def test_npy_dtype_shape_and_payload_binding(self):
        blob = npy("<f8", (3,), struct.pack("<ddd", 1.0, -0.0, 2.5))
        a, m = read_npy(io.BytesIO(blob))
        self.assertEqual(a.tobytes(), struct.pack("<ddd", 1.0, -0.0, 2.5))
        self.assertEqual(m["sha256"], hashlib.sha256(blob).hexdigest())
        self.assertEqual(m["bytes"], len(blob))
        value, unused = read_npy(io.BytesIO(npy("|S3", (), b"csc")))
        self.assertEqual(value, b"csc")
        for bad in (blob + b"x", npy("<f8", (3,), b""), npy("|O", (1,), b""), npy("<f8", (1,), b"\0" * 8, True)):
            with self.assertRaises(AuditGateError):
                read_npy(io.BytesIO(bad))

    def test_original_submatrix_order_and_linear_reader_row_agree(self):
        # Fixed DOF 1 removes one original row and column; literal expected CSC
        # buffers independently specify the surviving original column order.
        matrix = {"indptr": array("i", [0, 2, 3, 6, 8]),
                  "indices": array("i", [0, 2, 1, 0, 1, 2, 2, 3]),
                  "data": array("d", [4., 1., 9., 2., 7., 6., 3., 5.])}
        expected = {"data": hashlib.sha256(array("d", [4., 1., 2., 6., 3., 5.]).tobytes()).hexdigest(),
                    "indices": hashlib.sha256(array("i", [0, 1, 0, 1, 1, 2]).tobytes()).hexdigest(),
                    "indptr": hashlib.sha256(array("i", [0, 2, 4, 6]).tobytes()).hexdigest()}
        with patch.object(producer, "ND", 4), patch.object(producer, "ROW", 2), patch.object(producer, "KFF_COMPONENTS", expected), patch.object(producer, "ORIGINAL_KFF_NNZ", 6):
            entries, hashes = producer.frozen_Kff_hashes_and_row(matrix, [0, 2, 3], [1])
            self.assertEqual(hashes, expected)
            self.assertEqual([(x['original_column_DOF'],x['original_CSC_data_position'],x['coefficient']['float64']) for x in entries], [(0,1,1.),(2,5,6.),(3,6,3.)])
            matrix['data'][5] = 6.01
            with self.assertRaisesRegex(AuditGateError, "actual_original_Kff_buffer_order_exact"):
                producer.frozen_Kff_hashes_and_row(matrix, [0, 2, 3], [1])

    def test_export_omits_unlisted_runtime_and_rejects_private_or_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, output = Path(tmp) / "case", Path(tmp) / "export"
            root.mkdir()
            (root / "unlisted-runtime.json").write_text(json.dumps({"private": "/workspace/unused", "author": "hidden@example.test"}))
            record = {"schema": "razr-N6-original-row-capacity-audit-v1", "completed": False, "failure_type": "AuditGateError"}
            (root / "row-N6").mkdir()
            (root / "row-N6/N6_ROW_AUDIT.json").write_text(json.dumps(record))
            export(root, output)
            self.assertFalse((output / "unlisted-runtime.json").exists())
            manifest = json.loads((output / "EXPORT_MANIFEST.json").read_text())
            self.assertNotIn("/workspace/", json.dumps(manifest))
            self.assertNotIn("@", json.dumps(manifest))
            record["failure_gate"] = "private@example.test"
            (root / "row-N6/N6_ROW_AUDIT.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "private runtime string"):
                export(root, Path(tmp) / "private-rejected")
            record.pop("failure_gate")
            record["unexpected_api_author"] = "name"
            (root / "row-N6/N6_ROW_AUDIT.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "unexpected diagnostic schema"):
                export(root, Path(tmp) / "schema-rejected")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Contracts)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if os.environ.get("CASE_DIR"):
        receipt = {"schema": "razr-N6-small-contract-results-v1", "tests_run": result.testsRun,
                   "failure_count": len(result.failures), "error_count": len(result.errors),
                   "passed": result.wasSuccessful(), "historical_S4_test_count_modified": False,
                   "real_original_unsorted_fixed_member_counterexample_included": True,
                   "test_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (Path(os.environ["CASE_DIR"]) / "N6-small-contracts.json").write_text(json.dumps(receipt, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 2)
