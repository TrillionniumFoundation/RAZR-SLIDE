"""Exercise real native boundaries and failure modes of the product study."""
import copy
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import product_interfaces as interfaces
import product_fpc as flex


class ElectricalBoundaryTests(unittest.TestCase):
    def setUp(self):self.config=interfaces.load_config()

    def test_all_native_power_terminals_agree(self):
        result=interfaces.bind_power_chain()
        self.assertEqual(result['native_unique_pins'],168)
        self.assertFalse(result['B_battery_or_charger_implemented'])
        self.assertEqual(result['boards']['B1']['role'],'A_chain_receiver_cut')

    def test_project_routes_complete_without_fabricated_physical_pins(self):
        self.assertEqual({r['id'] for r in self.config['interfaces']},interfaces.INTERFACES)
        for row in self.config['interfaces']:
            self.assertIn(row['cabin_or_route'],('A','B','cross'))
            self.assertTrue(row['proposed_source_location'])
            self.assertTrue(row['proposed_sink_location'])
            self.assertIsNone(row['actual_pinmap'])
            self.assertFalse(row['extension_approved'])

    def test_missing_donor_cannot_be_promoted(self):
        self.config['architecture_decision']['actual_donor_selected']=True
        with self.assertRaises(ValueError):interfaces.validate_config(self.config)
        self.config['donor']={k:'' for k in self.config['donor']}
        with self.assertRaises(ValueError):interfaces.validate_config(self.config)

    def test_unknown_OEM_map_cannot_approve_extension(self):
        self.config['interfaces'][0]['extension_approved']=True
        with self.assertRaises(ValueError):interfaces.validate_config(self.config)
        row=self.config['interfaces'][0];row['extension_approved']=False
        row['actual_pinmap']=[{'net':'DECLARED','source_connector':'J1','source_pin':'1','sink_connector':'J2','sink_pin':'1','evidence':'unverified declaration','identity_kind':'observed_physical_terminal'}]
        result=interfaces.inspect(self.config)
        self.assertEqual(result['declared_terminal_maps'],1)
        self.assertEqual(result['product_interfaces_physically_bound'],0)

    def test_USB_crossing_is_required(self):
        next(r for r in self.config['interfaces'] if r['id']=='USB_DATA_CROSS')['cabin_or_route']='B'
        with self.assertRaises(ValueError):interfaces.validate_config(self.config)

    def test_software_name_is_not_terminal_evidence(self):
        row={'net':'USB_D_P','source_connector':'J1','source_pin':'1','sink_connector':'J2','sink_pin':'1','evidence':'software DTS family','identity_kind':'software_configuration'}
        with self.assertRaises(ValueError):interfaces.validate_pinmap([row])

    def test_energy_and_capacity_use_voltage_and_A_priority(self):
        result=interfaces.cell_budget({'A_mAh':3000,'B_mAh':1700,'A_nominal_V':3.85,'B_nominal_V':3.85})
        self.assertEqual(result['sum_of_cell_label_mAh'],4700)
        self.assertAlmostEqual(result['energy_Wh'],18.095)
        self.assertTrue(result['A_larger_capacity'])
        other=interfaces.cell_budget({'A_mAh':3000,'B_mAh':1700,'A_nominal_V':3.85,'B_nominal_V':3.7})
        self.assertIsNone(other['same_reference_voltage_equivalent_mAh'])
        self.assertIsNone(other['label_sum_target_comparison_at_common_voltage'])
        self.assertFalse(result['actual_system_terminal_capacity_verified'])
        self.assertFalse(other['actual_system_terminal_capacity_verified'])

    def test_mini_boards_retain_native_sites_and_explicit_new_probe_numbering(self):
        old=interfaces.bind_endpoint()
        for side in ('DP','DS'):
            payload,routes,_=flex.mini_endpoint_pcb(side)
            pins,counts=interfaces.pcb_pins(payload.encode())
            self.assertEqual((len(pins),counts['track_segments']),(52,84))
            board=interfaces.sexp(payload)
            setup=interfaces.children(board,'setup')[0]
            stack=interfaces.children(setup,'stackup')[0]
            total=sum(float(interfaces.children(layer,'thickness')[0][1]) for layer in interfaces.children(stack,'layer') if interfaces.children(layer,'thickness'))
            self.assertAlmostEqual(total,.8,places=9)
            for row in old['mapping']:
                self.assertEqual(pins['J1',row[side+'_site']],row['net'])
                self.assertEqual(pins['TP'+row['net'][1:],'1'],row['net'])
            self.assertEqual({r['net'] for r in routes},{f'C{i:02}' for i in range(1,27)})
            for route in routes:
                self.assertEqual(route['polyline_local_mm'][-1],route['target_xy_mm'])
                self.assertTrue(all(abs(p[0])<=4.8 and abs(p[1])<=4.15 for p in route['polyline_local_mm']))

    def test_material_dimension_partition_and_owned_signal_boundary(self):
        rows,facts=flex.coupon_geometry(self.config)
        self.assertEqual(len(rows),26)
        self.assertEqual(facts['length_mm'],facts['free_material_mm']+2*facts['rigid_end_mm'])
        self.config['coupon']['product_signal_or_power_assignment']='assumed USB'
        with self.assertRaises(ValueError):interfaces.validate_config(self.config)


class FlexMotionTests(unittest.TestCase):
    def test_whole_stroke_and_reverse_keep_same_material(self):
        c=interfaces.load_config();cache={};poses=flex.motion_poses()
        self.assertEqual(len(poses),49)
        for phase,slide,descent in poses:
            state=flex.travel_manual_state(slide,descent)
            self.assertEqual((state['left_tab'],state['right_tab']),(3.,3.))
            self.assertEqual((state['hold_screws'],state['support_insert']),(0,False))
            sections,result=flex.route_pose(c,slide,descent)
            self.assertAlmostEqual(result['length_analytic_mm'],140.,places=11)
            self.assertGreater(result['analytic_minimum_material_jacobian'],0)
            np.testing.assert_allclose(sections['width_axis'],np.tile([1,0,0],(len(sections['s']),1)),atol=1e-12)
            np.testing.assert_allclose(sections['center'][0],c['route_study']['A_anchor_local_mm'],atol=1e-9)
            base=np.linspace(0,140,65)
            self.assertTrue(all(np.min(abs(sections['s']-v))<1e-10 for v in base))
            key=(slide,descent)
            if key in cache:np.testing.assert_array_equal(sections['corners'],cache[key])
            cache[key]=sections['corners']
        self.assertEqual(len(cache),25)

    def test_finite_OPEN_turn_does_not_disappear_between_coarse_material_samples(self):
        c=interfaces.load_config();sections,r=flex.route_pose(c,79.75,8.2)
        shape,report=flex.finite_material_solid(sections['corners'])
        self.assertTrue(shape.isValid());self.assertEqual(len(shape.Solids()),1)
        self.assertGreater(shape.Volume(),0)
        self.assertGreater(len(sections['s']),65)
        self.assertAlmostEqual(shape.BoundingBox().xlen,12.,places=7)
        self.assertLess(r['analytic_minimum_centerline_radius_mm'],.22)

    def test_clamp_rigid_transform_does_not_put_width_along_Z(self):
        c=interfaces.load_config();sections,_=flex.route_pose(c,0,0)
        for end,expected in [('A',20),('B',12)]:
            parts=flex.place_endpoint(flex.local_endpoint_parts(c,end),sections,end)
            jaw=parts[end+'_upper_jaw'].BoundingBox()
            self.assertAlmostEqual(jaw.xlen,expected,places=7)
            self.assertAlmostEqual(jaw.zlen,.8,places=7)

    def test_degenerate_lanes_and_too_short_material_are_rejected(self):
        with self.assertRaises(ValueError):flex.material_return_sections([0,0,1],[0,1,1],140,65,12,.1)
        with self.assertRaises(ValueError):flex.material_return_sections([0,0,1],[0,100,2],20,65,12,.1)


if __name__=='__main__':unittest.main()
