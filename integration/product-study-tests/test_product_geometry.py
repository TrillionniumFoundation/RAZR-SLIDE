"""Targeted product risks: material conservation, provenance, real motion."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

import product_assembly as p
import product_motion as motion
import oled_storage as oled


class ProductGeometryTests(unittest.TestCase):
    def changed_config(self,change):
        cfg=copy.deepcopy(p.load_config());change(cfg)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'config.json';path.write_text(json.dumps(cfg));return p.load_config(path)

    def test_native_dimensions_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ValueError,'native baseline'):
            self.changed_config(lambda c:c['dimensions'].update({'thickness_mm':7.}))

    def test_measurement_claim_needs_actual_record(self):
        with self.assertRaisesRegex(ValueError,'measurement record'):
            self.changed_config(lambda c:c['components'][0].update({'source_kind':'measured_component'}))

    def test_unselected_battery_space_cannot_acquire_capacity(self):
        with self.assertRaisesRegex(ValueError,'unselected space'):
            self.changed_config(lambda c:c['components'][0].update({'capacity_mAh':3000}))

    def test_single_flexible_display_and_flat_B_constraints(self):
        c=p.load_config()['constraints'];self.assertTrue(c['one_flexible_display']);self.assertFalse(c['independent_rear_display']);self.assertEqual(c['planar_storage_cabin'],'B')

    def test_B_transform_rejects_unphysical_combined_motion(self):
        for s,d in ((40,1),(79.751,0),(0,-.01),(float('nan'),0)):
            with self.assertRaises(ValueError):p.b_transform(s,d)
        self.assertEqual(p.b_transform(79.75,8.2),(0.,79.75,0.))

    def test_motion_requires_both_independent_PAWL_controls(self):
        with self.assertRaisesRegex(ValueError,'both independent'):
            motion.transition(motion.Pose(left_tab=3),motion.Pose(slide=1,left_tab=3))

    def test_OPEN_accessories_cannot_be_hidden_during_travel(self):
        for args in ({'slide':40,'hold_screws':1},{'slide':79.75,'descent':4,'support_insert':True}):
            with self.assertRaisesRegex(ValueError,'OPEN accessories'):motion.Pose(**args)

    def test_complete_manual_roundtrip_preserves_physical_limitations(self):
        r=motion.manual_program();self.assertEqual(len(r['actions']),14);self.assertEqual(r['poses'][0],r['poses'][-1])
        self.assertFalse(r['physical_cycle_completed_on_hardware']);self.assertFalse(r['onboard_accessory_storage'])
        self.assertTrue(any(a['requires_temporary_front_strip_forming_support'] for a in r['actions']))

    def test_same_material_station_not_reset_between_poses(self):
        spec=oled.specification();start=[];ends=[]
        for s,d in ((0,0),(40,0),(79.75,0),(79.75,4.1),(79.75,8.2)):
            start.append(oled.material_station(0,s,d)['point_mm']);ends.append(oled.material_station(spec['total_material_length_mm'],s,d)['point_mm'])
            q=oled.state(s,d)
            for u in (q['front_length_mm'],q['front_length_mm']+q['arc_length_mm']):
                a=oled.material_station(u-1e-5,s,d);b=oled.material_station(u+1e-5,s,d)
                self.assertLess(math.dist(a['point_mm'],b['point_mm']),2.00001e-5)
                self.assertLess(math.dist(a['unit_tangent'],b['unit_tangent']),1e-5)
        self.assertTrue(all(x==start[0] for x in start));self.assertNotEqual(ends[0],ends[-1])

    def test_finite_one_piece_OLED_material_volume_constant(self):
        for s,d in ((0,0),(79.75,0),(79.75,8.2)):
            body,r=oled.geometry(s,d);self.assertEqual(len(body.Solids()),1);self.assertAlmostEqual(p.volume(body),2517.86,places=7)

    def test_current_full_depth_cavity_has_no_material_length_solution(self):
        r=oled.budget();self.assertFalse(r['original_full_depth_cavity_family_feasible']);self.assertAlmostEqual(r['minimum_extra_planar_storage_into_original_solid_lap_mm'],9.35,places=8)
        self.assertTrue(r['trial_inside_geometric_length_interval'])
        spec=oled.specification();spec['total_material_length_mm']=r['analytic_whole_two_stage_length_interval_mm'][0]-.01
        with self.assertRaisesRegex(ValueError,'material length'):oled.geometry(79.75,0,spec)

    def test_supplier_FPC_is_not_more_OLED_and_partial_stack_stays_unknown(self):
        rows=oled.source_comparison()['rows'];self.assertEqual(len(rows),2)
        for row in rows:
            self.assertGreater(row['panel_length_deficit_for_this_family_mm'],20.)
            self.assertIsNone(row['thickness_scope']['finished_maximum_mm']);self.assertFalse(row['selected_for_product'])

    def test_equal_finished_rigid_envelopes_are_native_bounds(self):
        r=motion.finished_envelopes();self.assertTrue(r['equal_fixed_cabin_bounds'])
        baseline,native_meta=p.native_scene()
        self.assertEqual(len(baseline),83)
        self.assertEqual(native_meta['expected_scene_participants'],83)
        self.assertFalse(native_meta['material_geometry_changed'])
        for scene,meta in (p.product_scene(),p.product_scene(79.75,8.2,3,3,open_hold=True,open_support=True)):
            self.assertEqual(meta['expected_scene_participants'],len(scene))
            self.assertIn(len(scene),(94,101))
            self.assertTrue(meta['material_geometry_changed'])
            self.assertEqual(meta['native_baseline_expected_scene_participants'],83)
            self.assertFalse(meta['native_baseline_material_geometry_changed'])
        for kind in ('A_fixed_parts','B_fixed_body'):
            for a,b in zip(r[kind]['size_mm'],(73.99,94.25,9.15)):self.assertAlmostEqual(a,b,places=7)
        panel=p.product_templates()[0]['A_BACK_PANEL'];before=p.bounds(panel)
        with tempfile.TemporaryDirectory() as td:
            p.cq.exporters.export(panel,str(Path(td)/'panel.stl'),tolerance=.03,angularTolerance=.1)
        for a,b in zip(before,p.bounds(panel)):
            self.assertAlmostEqual(a,b,places=10,msg='STL mesh cache changed native geometric bounds')

    def test_wide_B_battery_midpath_collision_is_preserved(self):
        negative=p.load_config(p.ROOT/'engineering/product-integration-20261018/mechanical/geometry-wide-B-negative-control.json')
        scene,_=p.product_scene(40,0,3,3);previous=p.registered_components(negative,40,0)['B_BATTERY_ALLOCATION'];current=p.registered_components(slide_mm=40)['B_BATTERY_ALLOCATION']
        tracks=[body for name,body in scene.items() if 'TELESCOPE_' in name]
        self.assertTrue(any(p.strict_common(previous,b)['common_mm3']>1e-7 for b in tracks))
        self.assertTrue(all(p.strict_common(current,b)['common_mm3']<=1e-7 for b in tracks))


if __name__=='__main__':unittest.main()
