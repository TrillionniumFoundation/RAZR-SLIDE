from pathlib import Path
import hashlib
import math
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
import cam_coupling as c
from verify_mounted_mechanism import common


class CouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=c.templates();cls.h,cls.detail=c.housing_study()

    def test_valid_two_phase_endpoints(self):
        self.assertEqual(c.pose(0)['nominal_KEY_Y_mm'],0.)
        self.assertEqual(c.pose(79.75)['nominal_KEY_Y_mm'],12.)
        self.assertEqual(c.pose(79.75,8.2)['B_Z_mm'],0.)

    def test_nonfinite_and_boolean_inputs_rejected(self):
        for v in (True,None,'1',float('nan'),float('inf')):
            with self.assertRaises(ValueError):c.pose(v)

    def test_domain_errors_rejected(self):
        for s,d in ((-1,0),(79.76,0),(79.75,-1),(79.75,8.21)):
            with self.assertRaises(ValueError):c.pose(s,d)

    def test_seating_cannot_precede_full_slide(self):
        with self.assertRaises(ValueError):c.pose(40,1.)

    def test_ratio_is_not_a_rigid_one_to_one_link(self):
        self.assertAlmostEqual(c.RATIO*79.75,12.)
        self.assertLess(c.RATIO,1.)

    def test_centerline_reverse_is_not_unique_driving(self):
        values=[c.pose(s)['nominal_KEY_Y_mm'] for s in (0,20,40,79.75)]
        self.assertEqual(list(reversed(values)),[c.pose(s)['nominal_KEY_Y_mm'] for s in (79.75,40,20,0)])
        self.assertFalse(c.output_band(0)['unique_output_without_preload'])

    def test_finite_backlash_is_not_clamped_at_endpoints(self):
        a,b=c.output_band(0),c.output_band(79.75)
        self.assertLess(a['lower_mm'],0.)
        self.assertGreater(b['upper_mm'],12.)
        self.assertAlmostEqual(a['reversal_lost_motion_mm'],.12127354213309306)

    def test_invalid_band_query_rejected(self):
        for s in (-1,80,True,float('nan')):
            with self.assertRaises(ValueError):c.output_band(s)

    def test_telescope_total_capacity_exceeds_normal_seating(self):
        self.assertAlmostEqual(3*(c.STAGE_MAX-c.STAGE_MIN),8.4)
        self.assertGreater(3*(c.STAGE_MAX-c.STAGE_MIN),8.2)

    def test_unequal_extension_allocations_are_explicitly_allowed(self):
        self.assertEqual(c.stage_allocation(0,[2.9,2.9,2.7]),[2.9,2.9,2.7])
        self.assertEqual(c.stage_allocation(4.1,[.1,1.4,2.9]),[.1,1.4,2.9])
        self.assertTrue(c.pose(79.75)['equal_extension_allocation_is_not_mechanically_enforced'])

    def test_joint_overtravel_and_wrong_total_rejected(self):
        for j in ([0,2.9,2.9],[3.,2.8,2.7],[.1,.1],[True,2.9,2.9],[2.,2.,2.]):
            with self.assertRaises(ValueError):c.stage_allocation(0,j)

    def test_all_nineteen_export_bodies_are_single_positive_solids(self):
        shapes=[*self.t.values(),*self.h.values()]
        self.assertEqual(len(shapes),19)
        for body in shapes:self.assertEqual(len(c.n.whole_material(body)[0]),1)

    def test_original_KEY_material_and_scale_preserved(self):
        for side in 'LR':
            old=c.parent(side+'_KEY');new=self.t[side+'_KEY_YOKE']
            self.assertEqual(c.vol(old.cut(new)),0.)
            self.assertGreater(c.vol(new.cut(old)),0.)
            self.assertEqual(c.vol(old.cut(self.t[side+'_ORIGINAL_KEY'])),0.)

    def test_guide_and_cam_supports_have_positive_shell_connections(self):
        self.assertEqual(len(self.detail['joints']),8)
        self.assertTrue(all(x['overlap_mm3']>1e-7 for x in self.detail['joints']))

    def test_shell_material_cost_is_accounted_not_called_free_space(self):
        for name,row in self.detail['material'].items():
            self.assertAlmostEqual(row['old_volume_mm3']-row['removed_mm3']+row['added_mm3'],row['new_volume_mm3'],places=7)
        self.assertGreater(self.detail['material']['A_FRAME']['removed_mm3'],0)
        self.assertGreater(self.detail['material']['B_SHELL']['removed_mm3'],0)

    def test_modified_shells_stay_inside_declared_study_outer(self):
        for name,outer in [('A_FRAME','A_OUTER'),('A_BACK_PANEL','A_OUTER'),('B_SHELL','B_OUTER')]:
            self.assertEqual(c.vol(self.h[name].cut(c.parent(outer))),0.)

    def test_original_B_floor_rejects_tube_new_passage_clears(self):
        parts,_=c.state(0,0)
        for side in 'LR':
            tube=parts[side+'_TELESCOPE_2']
            self.assertGreater(common(tube,c.parent('B_SHELL').translate((0,0,8.2)))[0],1e-7)
            self.assertEqual(common(tube,self.h['B_SHELL'].translate((0,0,8.2)))[0],0.)

    def test_new_output_arm_does_not_cut_old_roots_to_pass(self):
        for s in (0,40,79.75):
            q=c.pose(s)['nominal_KEY_Y_mm']
            for side in 'LR':
                new=self.t[side+'_KEY_YOKE'].cut(self.t[side+'_ORIGINAL_KEY']).translate((0,q,0))
                for root in ('ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'):
                    self.assertEqual(common(new,c.parent(side+'_'+root))[0],0.)

    def test_state_calls_do_not_rebuild_or_trim_templates(self):
        before={k:c.vol(v) for k,v in self.t.items()}
        c.state(79.75,8.2);c.state(0,0)
        self.assertEqual(before,{k:c.vol(v) for k,v in c.templates().items()})

    def test_actual_phone_input_register_is_unchanged(self):
        data=(ROOT/'integration/assembly_inputs.json').read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b')


    def test_added_arm_clears_full_PAWL_return_and_old_arm_fails(self):
        for side in 'LR':
            pawl=c.parent(side+'_PAWL');b=pawl.BoundingBox()
            full=c.box((b.xmin,b.ymin,b.zmin),(b.xmax,b.ymax,b.zmax+1.1))
            added=self.t[side+'_KEY_YOKE'].cut(self.t[side+'_ORIGINAL_KEY'])
            for q in (0.,c.output_band(0)['upper_mm'],12.):
                self.assertEqual(common(added.translate((0,q,0)),full)[0],0.)
            old_rod=c.handed(c.box((14.2,15.8,4.05),(14.8,39.6,4.35)),side)
            self.assertGreater(common(old_rod,pawl)[0],1e-7)
