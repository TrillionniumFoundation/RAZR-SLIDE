import unittest,math,json
from dataclasses import replace
from r17_model import Params,draw_screen,draw_internal_fpc,sbend,sweep,ROOT
from r17_cad import assembly,overlap,b_shell_local,a_shell
from r17_verify import batteries_and_oem_proxies
class TestR17(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=Params();cls.s=sweep(cls.p,ny=2001,nq=401)
 def test_equal_cabins(self):
  self.assertEqual(self.p.H,94.25);self.assertAlmostEqual(self.p.total_h,174)
 def test_radius_R5_2_rejected(self):
  with self.assertRaises(ValueError):draw_screen(replace(self.p,R=5.2),0,0)
 def test_radius_R3_4_pack_nominal_only(self):
  self.assertLessEqual(2*self.p.R,self.p.avail_depth)
 def test_S_curve_tangent_and_length(self):
  p,L,D,LS=sbend(8.2,3.4,79.75,90.25,7.6,64)
  self.assertAlmostEqual(p[-1][1],-.6,places=7)
  self.assertAlmostEqual(p[-1][0],90.25,places=7)
  self.assertGreater(L,10.5)
 def test_screen_invariant_2401(self):self.assertLess(self.s['oled_max_length_drift_mm'],1e-9)
 def test_FPC_invariant_2401(self):self.assertLess(self.s['fpc_max_length_drift_mm'],1e-9)
 def test_tail_never_below_minimum(self):self.assertGreaterEqual(self.s['min_OLED_tail_bottom_margin_mm'],3.2-1e-8)
 def test_tail_moves_again_at_Z_docking(self):
  p=self.p
  self.assertLess(draw_screen(p,p.travel,p.z_travel)['tail_y_local'],draw_screen(p,p.travel,0)['tail_y_local'])
 def test_fpc_hood_clearance(self):self.assertGreater(self.s['min_FPC_to_U_hood_longitudinal_gap_mm'],1)
 def test_R3_4_docking_screen_flat_range(self):
  self.assertGreater(draw_screen(self.p,self.p.travel,self.p.z_travel)['front_length'],self.p.active_h+2)
 def test_static_original_bridge_fails(self):
  a=assembly(self.p,0,0,0,True,True)
  self.assertGreater(overlap(a['OLED'],a['A']),1)
  self.assertGreater(overlap(a['OLED'],a['B']),100)
 def test_modified_stow_no_intersection(self):
  a=assembly(self.p,0,0,0)
  for j in ['A','A_fixed_skin','A_moving_leaf','B','FPC']:
   if j!='FPC':self.assertLess(overlap(a['OLED'],a[j]),1e-6)
  self.assertLess(overlap(a['FPC'],a['B']),1e-6)
 def test_modified_terminal_no_intersection(self):
  a=assembly(self.p,self.p.travel,self.p.z_travel,1)
  for j in ['A','A_fixed_skin','A_moving_leaf','B','FPC']:
   if j!='FPC':self.assertLess(overlap(a['OLED'],a[j]),1e-6)
  self.assertLess(overlap(a['FPC'],a['B']),1e-6)
 def test_bridge_unsafe_early_motion_rejected(self):
  a=assembly(self.p,0,0,1)
  self.assertGreater(overlap(a['OLED'],a['A_moving_leaf']),1)
 def test_front_width_has_narrow_side_margin(self):
  self.assertLess(34.0-self.p.oled_w/2,0.4)
 def test_FPC_and_cells_are_only_proxy(self):
  m=batteries_and_oem_proxies(self.p)
  self.assertGreater(m['A_battery_ASSUMED'].Volume(),m['B_battery_ASSUMED'].Volume())
 def test_supplier_gate_must_remain_false(self):
  data=json.loads((ROOT/'verification'/'R17_independent_results.json').read_text());self.assertFalse(data['gates']['OLED_R3_4_module_supplier_permission'])
  self.assertFalse(data['gates']['cross_cabin_A_B_FPC_YZ_3D_route'])
  self.assertFalse(data['gates']['PRODUCTION_RELEASE'])
if __name__=='__main__':unittest.main()
