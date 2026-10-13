import unittest
from r20_model import p,tolerance_budget,working_height_window,compatible_double_end_ports,allowed_contact_carriage,screen_oled_limit
from r20_cad import local_assembly,collision_metrics,run
class TestR20(unittest.TestCase):
    def test_vendor_dims(self):self.assertEqual((p.free_height,p.hmin,p.hmax), (1.2,.7,1.0))
    def test_vendor_signal_not_battery(self):self.assertEqual(p.te_signal_current_A,1.5)
    def test_old_global_tolerance_fails(self):self.assertFalse(tolerance_budget()['old']['passes'])
    def test_new_nominal_stack_mathematically_passes(self):self.assertTrue(tolerance_budget()['preliminary_room_temp']['passes'])
    def test_thermal_and_wear_fails(self):self.assertFalse(tolerance_budget()['thermal_wear']['passes'])
    def test_numerical_guard(self):self.assertAlmostEqual(tolerance_budget()['preliminary_room_temp']['min_vendor_margin_mm'],.04)
    def test_retracted_gap(self):self.assertAlmostEqual(tolerance_budget()['retracted_free_tip_clearance_nominal_mm'],.45)
    def test_slide_global_gap(self):self.assertAlmostEqual(tolerance_budget()['retracted_free_tip_clearance_if_global_error_025_mm'],.20)
    def test_stow_end(self):self.assertTrue(compatible_double_end_ports(0,0)['stowed'])
    def test_open_end(self):self.assertTrue(compatible_double_end_ports(79.75,8.2)['deployed'])
    def test_y_middle(self):self.assertTrue(compatible_double_end_ports(40,0)['intermediate'])
    def test_z_middle(self):self.assertTrue(compatible_double_end_ports(79.75,4.1)['intermediate'])
    def test_one_pin_fail(self):self.assertFalse(allowed_contact_carriage(True,False,True,spring_retract_verified=True))
    def test_two_pins_no_real_stop_fail(self):self.assertFalse(allowed_contact_carriage(True,True,False,spring_retract_verified=True))
    def test_two_pins_without_verified_spring_fail(self):self.assertFalse(allowed_contact_carriage(True,True,True,spring_retract_verified=False))
    def test_ideal_all_true(self):self.assertTrue(allowed_contact_carriage(True,True,True,spring_retract_verified=True))
    def test_screen_nominal_passes_only_clearance(self):self.assertTrue(screen_oled_limit()['screen_geometric_pass'])
    def test_screen_nominal_margin(self):self.assertAlmostEqual(screen_oled_limit()['ideal_spare_mm'],.34)
    def test_screen_variation_fails(self):self.assertFalse(screen_oled_limit(avail=7.1)['screen_geometric_pass'])
    def test_left_dog_force_blocks(self):
        m=collision_metrics(local_assembly(False,False,True));self.assertGreater(m['L_block_mm3'],0);self.assertAlmostEqual(m['R_block_mm3'],0)
    def test_right_dog_force_blocks(self):
        m=collision_metrics(local_assembly(False,True,False));self.assertGreater(m['R_block_mm3'],0);self.assertAlmostEqual(m['L_block_mm3'],0)
    def test_both_dogs_force_blocks(self):
        m=collision_metrics(local_assembly(False,False,False));self.assertGreater(m['L_block_mm3'],0);self.assertGreater(m['R_block_mm3'],0)
    def test_open_dogs_no_obstruction(self):
        m=collision_metrics(local_assembly(False,True,True));self.assertAlmostEqual(m['L_block_mm3']+m['R_block_mm3'],0)
    def test_retracted_no_obstruction(self):
        m=collision_metrics(local_assembly(True,False,False));self.assertAlmostEqual(m['L_block_mm3']+m['R_block_mm3'],0)
    def test_pad_no_interference(self):
        for retract in (False,True):
          self.assertAlmostEqual(collision_metrics(local_assembly(retract,True,True))['pad_contact_overlap_mm3'],0)
    def test_local_gates_dont_prove_hard_stop(self):
        m=collision_metrics(local_assembly(False,True,True))
        self.assertAlmostEqual(m['L_block_mm3']+m['R_block_mm3'],0)
        self.assertFalse(allowed_contact_carriage(True,True,False,spring_retract_verified=True))
    def test_no_real_step(self):self.assertFalse(run(False)['vendor_REAL_STEP_imported'])
    def test_all_states_expected(self):self.assertEqual(len(run(False)['rows']),9)
if __name__=='__main__': unittest.main(verbosity=1)
