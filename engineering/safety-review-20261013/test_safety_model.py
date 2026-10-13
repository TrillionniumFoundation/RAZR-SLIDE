"""Adversarial checks of a study model, not a product safety certificate."""
import dataclasses
import unittest

from safety_model import ForceBounds, ReleaseEvidence, build_report, force_window, release_guard


class SafetyStudy(unittest.TestCase):
    def test_unknown_force_data_deny_retraction(self):
        self.assertFalse(force_window(ForceBounds())["model_feasible"])

    def test_no_force_interval_can_retract_without_exceeding_damage_bound(self):
        # Synthetic dimensioned fixture inputs; no product limits are selected.
        decision = force_window(ForceBounds(3.0, 4.0, 2.0, 8.0, 3.5, 3.2))
        self.assertFalse(decision["model_feasible"])

    def test_equal_limit_to_damage_threshold_is_rejected(self):
        self.assertFalse(force_window(ForceBounds(1.0, 2.0, 2.0, 4.0, 2.0, 1.5))["model_feasible"])

    def test_low_actuator_cap_cannot_retract(self):
        self.assertFalse(force_window(ForceBounds(3.0, 2.0, 6.0, 8.0, 4.0, 3.1))["model_feasible"])

    def test_nan_inf_zero_negative_and_boolean_are_not_bounds(self):
        for invalid in (float("nan"), float("inf"), 0, -1, True):
            with self.subTest(invalid=invalid):
                self.assertFalse(force_window(ForceBounds(invalid, 2.0, 3.0, 4.0, 2.0, 1.5))["model_feasible"])

    def test_synthetic_feasible_case_never_grants_manufacturing(self):
        result = force_window(ForceBounds(1.0, 3.0, 4.0, 5.0, 2.0, 1.5))
        self.assertTrue(result["model_feasible"])
        self.assertFalse(result["physical_qualification"])
        self.assertIs(result["manufacturing_go"], False)

    def test_upper_limit_without_guaranteed_available_force_is_not_enough(self):
        self.assertFalse(force_window(ForceBounds(1.0, 3.0, 4.0, 5.0, 2.0))["model_feasible"])
        self.assertFalse(force_window(ForceBounds(1.0, 3.0, 4.0, 5.0, 2.0, 0.5))["model_feasible"])

    def test_every_missing_independent_release_requirement_denies(self):
        complete = ReleaseEvidence(**{field.name: True for field in dataclasses.fields(ReleaseEvidence)})
        self.assertTrue(release_guard(complete)["model_release_allowed"])
        for field in dataclasses.fields(ReleaseEvidence):
            with self.subTest(missing=field.name):
                decision = release_guard(dataclasses.replace(complete, **{field.name: False}))
                self.assertFalse(decision["model_release_allowed"])
                self.assertIn(field.name, decision["missing"])

    def test_isolation_command_never_substitutes_measured_voltage(self):
        complete = ReleaseEvidence(**{field.name: True for field in dataclasses.fields(ReleaseEvidence)})
        for bypass in ("A_direct_pad_short", "B_direct_pad_short", "shared_live_bus_to_pad_short"):
            with self.subTest(bypass=bypass):
                live = dataclasses.replace(complete, voltage_zero_measured_independently=False)
                self.assertFalse(release_guard(live)["model_release_allowed"])

    def test_unknown_default_model_denies_release(self):
        self.assertEqual(len(release_guard(ReleaseEvidence())["missing"]), 8)

    def test_typed_boolean_guard_rejects_truthy_nonproofs(self):
        complete = ReleaseEvidence(**{field.name: True for field in dataclasses.fields(ReleaseEvidence)})
        self.assertFalse(release_guard(dataclasses.replace(complete, residual_energy_bounded=1))["model_release_allowed"])

    def test_exhaustive_logical_states_do_not_grant_manufacturing(self):
        result = build_report()
        self.assertEqual(result["release_logic_states"], 256)
        self.assertEqual(result["release_logic_permitted_state_count"], 1)
        self.assertTrue(all(row["decision"]["manufacturing_go"] is False for row in result["release_logic_rows"]))

    def test_separate_paths_preserve_cross_path_short_counterexamples(self):
        result = build_report()
        self.assertEqual(set(result["candidate_paths"]), {"signal", "USB", "power"})
        self.assertFalse(result["direct_pack_parallel_connection_allowed"])
        self.assertFalse(result["BM28_repeated_mating_during_slide_allowed"])
        self.assertFalse(result["mechanical_force_carried_by_FPC_allowed"])
        self.assertTrue(any(row["affected_paths"] == ["power", "signal"] for row in result["fault_witnesses"]))
        self.assertTrue(any(row["affected_paths"] == ["power", "USB"] for row in result["fault_witnesses"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
