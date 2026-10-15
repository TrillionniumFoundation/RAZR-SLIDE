from dataclasses import replace
from pathlib import Path
import hashlib
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import endpoint_joint_pawl as e
import verify_endpoint_joint_pawl as v


class SlotTests(unittest.TestCase):
    def test_rejects_nonfinite_and_boolean_geometry(self):
        for value in (True,float('nan'),float('inf'),'3',None):
            with self.subTest(value=value),self.assertRaises(ValueError):replace(e.SLOT,input_travel_mm=value)

    def test_rejects_zero_clearance_or_travel(self):
        for kwargs in ({'slot_radius_mm':.4},{'slot_radius_mm':.39},{'pin_radius_mm':0.},{'output_span_mm':0.},{'input_travel_mm':-1.}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):replace(e.SLOT,**kwargs)

    def test_manual_input_is_not_clamped(self):
        for u in (True,-.01,3.01,float('nan'),None):
            with self.subTest(u=u),self.assertRaises(ValueError):e.SLOT.interval(u)

    def test_new_centerline_uses_fixed_origin_and_span(self):
        self.assertAlmostEqual(e.SLOT.interval(0.)['center_mm'],.02)
        self.assertAlmostEqual(e.SLOT.interval(3.)['center_mm'],1.08)

    def test_all_ideal_slot_positions_fit_between_existing_axial_stops(self):
        self.assertGreater(e.SLOT.interval(0.)['lower_mm'],-.02)
        self.assertLess(e.SLOT.interval(3.)['upper_mm'],1.12)

    def test_old_range_has_both_failure_extremes(self):
        prior=replace(e.SLOT,output_origin_mm=0.,output_span_mm=1.1)
        self.assertLess(prior.interval(0.)['lower_mm'],-.02)
        self.assertGreater(prior.interval(3.)['upper_mm'],1.12)

    def test_pin_and_radial_clearance_are_not_shrunk(self):
        self.assertEqual(e.SLOT.pin_radius_mm,.4)
        self.assertEqual(e.SLOT.slot_radius_mm,.425)
        self.assertAlmostEqual(e.SLOT.halfwidth,.025*math.hypot(1.,1.06/3.))

    def test_negative_lower_output_not_hidden(self):
        self.assertLess(e.SLOT.interval(0.)['lower_mm'],0.)


class EndpointJointGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.new,cls.detail=e.build();cls.old,_=e.s.build()

    def test_twenty_one_complete_positive_solids(self):
        self.assertEqual(len(self.new),21)
        for body in self.new.values():self.assertEqual(len(e.s.c.n.whole_material(body)[0]),1)

    def test_original_contacts_roots_pins_screws_are_identical(self):
        changed={'A_BACK_PANEL'}|{s+'_'+r for s in 'LR' for r in ('TAB','ROOF','GUIDE_REFERENCE')}
        for name in set(self.new)-changed:self.assertEqual(v.v.w.v.equal(self.new[name],self.old[name]),[0.,0.])

    def test_native_slot_ends_independently_recover_new_datum(self):
        for side in 'LR':
            r=v.native_slot(self.new[side+'_TAB'])
            self.assertAlmostEqual(r['origin'],.02,places=7)
            self.assertAlmostEqual(r['slope'],1.06/3.,places=7)

    def test_slot_changes_confined_to_new_plate(self):
        for side in 'LR':
            box=e.s.c.box((-40,15.5,4.59999),(40,25.5,7.15001))
            a=self.new[side+'_TAB'].cut(self.old[side+'_TAB']);b=self.old[side+'_TAB'].cut(self.new[side+'_TAB'])
            self.assertLessEqual(v.v.vol(a.cut(box)),1e-7)
            self.assertLessEqual(v.v.vol(b.cut(box)),1e-7)

    def test_native_roof_overlap_grows_without_changing_screw(self):
        for side in 'LR':
            for i in (0,1):
                a=v.roof_overlap(self.old,side,i);b=v.roof_overlap(self.new,side,i)
                self.assertAlmostEqual(a['nominal_axial_overlap_mm'],.25)
                self.assertAlmostEqual(b['nominal_axial_overlap_mm'],1.25)
                self.assertAlmostEqual(b['equivalent_pitch_count_not_effective_threads'],5.)

    def test_roof_boss_has_real_pocket_clearance(self):
        for side in 'LR':
            self.assertEqual(v.v.common(self.new[side+'_ROOF'],self.new['A_BACK_PANEL']),0.)
            self.assertGreater(v.v.vol(self.new[side+'_ROOF'].cut(self.old[side+'_ROOF'])),0.)

    def test_closed_release_extreme_shapes_clear_native_roots(self):
        for side in 'LR':
            for u in (0.,3.):
                interval=e.SLOT.interval(u)
                for z in (interval['lower_mm'],interval['upper_mm']):
                    pawl=self.new[side+'_PAWL'].translate((0,0,z))
                    for root in (e.s.c.parent(side+'_ROOT_INNER'),self.new[side+'_ROOT_OUTER']):
                        self.assertLessEqual(v.v.common(pawl,root),1e-7)

    def test_original_failure_geometry_retained(self):
        half=.025*math.hypot(1.,1.1/3.)
        for side in 'LR':
            self.assertGreater(v.v.common(self.old[side+'_PAWL'].translate((0,0,-half)),e.s.c.parent(side+'_ROOT_INNER')),1e-7)
            self.assertGreater(v.v.common(self.old[side+'_PAWL'].translate((0,0,1.1+half)),self.old[side+'_ROOT_OUTER']),1e-7)

    def test_existing_fourteen_body_installations_still_defined(self):
        roles=[name for side in 'LR' for name,_ in v.v.plan(side)]
        self.assertEqual(len(set(roles)),14);self.assertTrue(set(roles)<=set(self.new))

    def test_input_register_not_filled_with_study_assumptions(self):
        self.assertEqual(hashlib.sha256((ROOT/'integration/assembly_inputs.json').read_bytes()).hexdigest(),'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b')

    def test_force_and_thread_qualification_not_inferred(self):
        self.assertTrue(self.detail['threads_preload_torque_pullout_not_qualified'])
        self.assertAlmostEqual(self.detail['radial_boss_pocket_gap_mm'],.05)

    def test_current_parts_stay_inside_original_A_envelope(self):
        outer=e.s.c.parent('A_OUTER')
        for name in ('A_BACK_PANEL','L_ROOF','R_ROOF','L_TAB','R_TAB'):
            self.assertLessEqual(v.v.vol(self.new[name].cut(outer)),1e-7)


    def test_exact_roof_partition_repairs_overbroad_certificate_not_geometry(self):
        for side in 'LR':
            roof=self.new[side+'_ROOF'];base=self.old[side+'_ROOF']
            fixed={'PANEL':self.new['A_BACK_PANEL'],'PAWL':self.new[side+'_PAWL'].translate((0,0,.02)),'PIN':self.new[side+'_SHOULDER_PIN_NOMINAL'].translate((0,0,.02))}
            self.assertTrue(v.v.motion('old_unpartitioned',roof,(0,0,12.),fixed)['failed'])
            r=v.roof_motion_partition('complete',roof,base,(0,0,12.),fixed)
            self.assertFalse(r['failed']);self.assertEqual(r['whole_material_difference_mm3'],[0.,0.]);self.assertEqual(r['partition_components'],3)
            with self.assertRaises(ValueError):v.roof_motion_partition('trimmed',base,roof,(0,0,12.),fixed)
