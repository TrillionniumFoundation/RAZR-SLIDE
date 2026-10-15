import io
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from prepare_inputs import safe_extract

ROOT = Path(__file__).resolve().parent


class CadReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / "R45_CAD_motion_audit.json").read_text())

    def test_full_new_discrete_motion_not_frozen_json(self):
        self.assertEqual(self.report["pose_count"], 121)
        self.assertEqual(len(self.report["new_full_motion_rows"]), 121)
        self.assertTrue(self.report["complete"])

    def test_obstacle_coverage_includes_uncut_B_and_bilateral_rails(self):
        rows = self.report["new_full_motion_rows"]
        self.assertEqual(self.report["obstacles_per_pose"], 23)
        for row in rows:
            self.assertIn("B_R37_BEFORE_UNAPPROVED_HEADER_CUT", row["intersections_mm3"])
            for side in "LR":
                self.assertIn(f"B_INBOARD_RAIL_{side}_RESEARCH_PROXY", row["intersections_mm3"])

    def test_single_ribbon_volume_and_length_consistency(self):
        for row in self.report["new_full_motion_rows"]:
            self.assertTrue(row["valid_single_solid"])
            self.assertGreater(row["ribbon_volume_mm3"], 0.)
            self.assertLess(abs(row["ribbon_volume_mm3"] - 120*1.2*.15), .001)
            self.assertLess(abs(row["wire_length_mm"] - 120.), 1e-5)

    def test_join_tangent_artifact_removed_in_research_curve(self):
        for row in self.report["actual_STEP_curve_and_terminal_frame_comparisons"]:
            self.assertGreater(row["legacy_R44_curve"]["start_join_tangent_error_deg"], .001)
            self.assertLess(row["tangent_constrained_curve"]["start_join_tangent_error_deg"], 1e-6)
            self.assertLess(row["tangent_constrained_curve"]["end_join_tangent_error_deg"], 1e-6)

    def test_geometric_frame_no_longer_assumes_28degree_B_clamp_rotation(self):
        seated = self.report["actual_STEP_curve_and_terminal_frame_comparisons"][-1]
        self.assertGreater(seated["legacy_B_end_material_frame"]["width_axis_tilt_from_XY_deg"], 27.)
        self.assertLess(seated["tangent_constrained_B_end_material_frame"]["width_axis_tilt_from_XY_deg"], .1)
        self.assertTrue(self.report["Frenet_director_is_geometric_hypothesis_not_material_or_clamp_qualification"])

    def test_easy_axis_counterexample_is_not_silently_discarded(self):
        negative = self.report["easy_axis_negative_counterexamples"]
        self.assertGreater(negative[0]["intersections_mm3"]["OLED_PROXY"], 2.)
        self.assertTrue(all(row["lower_Z_envelope_excess_mm"] >= .35 for row in negative))

    def test_manufacturing_release_not_created_by_zero_intersection(self):
        self.assertFalse(self.report["candidate_go"])
        self.assertFalse(self.report["manufacturing_go"])
        self.assertFalse(self.report["continuous_motion_qualification"])
        self.assertTrue(self.report["no_protected_BRep_or_OLED_was_cut_or_modified"])

    def test_GHOST_STEP_hash_and_reimport_receipt(self):
        self.assertEqual(len(self.report["new_STEP_exports"]), 6)
        for row in self.report["new_STEP_exports"]:
            self.assertTrue(row["GHOST_only"])
            self.assertEqual(row["valid_reimported_solids"], 23)
            self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"])

    def test_archive_path_traversal_is_rejected_before_writing(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("../escape.py", "untrusted")
        data = stream.getvalue()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                safe_extract(data, Path(temp)/"root", hashlib.sha256(data).hexdigest(), 1)
            self.assertFalse((Path(temp)/"escape.py").exists())


if __name__ == "__main__":
    unittest.main()
