import itertools
import json
import math
from pathlib import Path
import sys
import unittest
from fractions import Fraction as F

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'integration'))
from cam_contact_profile import ContactProfile
import slide_domain as d


class SlideDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names=json.loads((HERE.parent/'seating/seating-inventory.json').read_text())['names']
        cls.laws=d.rigid_laws(cls.names,{'L':.02,'R':.03},cls.names)
        # A nondegenerate analytical four-branch profile; this is a mathematical
        # contract test, not a surrogate for actual measured native profiles.
        cls.profiles=[ContactProfile(.1,1.,.1,2.,.12,.2) for _ in range(4)]

    def test_complete_material_classification_preserves_growing_springs(self):
        self.assertEqual(len(self.laws),148)
        self.assertEqual(set(self.laws)|d.SPRINGS|d.FLEX,set(self.names))
        self.assertEqual(len(d.SPRINGS),4)
        self.assertTrue(set(d.STOP_ROLES)<=set(self.laws))

    def test_unknown_or_missing_material_rejected(self):
        for names in (self.names[:-1],self.names[:-1]+['invented_part'],self.names[:-1]+[self.names[0]]):
            with self.assertRaises(ValueError):d.rigid_laws(names,{'L':.02,'R':.03},self.names)

    def test_crosshead_follower_split_piece_follows_x_not_key_y(self):
        self.assertEqual(self.laws['L_KEY_FOLLOWER_LOWER_FLANGE'].q_xyz,(F(-1),F(0),F(0)))
        self.assertEqual(self.laws['L_KEY'].q_xyz,(F(0),F(1),F(0)))
        self.assertEqual(self.laws['B_tail'].q_xyz,(F(0),F(319,48),F(0)))

    def test_complete_independent_joint_polytope_projection(self):
        vertices=d.joint_vertices()
        self.assertEqual(len(vertices),3)
        for left in (self.laws[n] for n in ('L_TELESCOPE_1','L_TELESCOPE_2','L_TELESCOPE_3')):
            for right in (self.laws[n] for n in ('R_TELESCOPE_1','R_TELESCOPE_2','R_PAWL')):
                law=left.relative_to(right); actual=[]
                for jl,jr,fl,fr in itertools.product(vertices,vertices,(-1,1),(-1,1)):
                    vals=tuple(v-d.JOINT_NOMINAL for j in (jl,jr) for v in j[:2])
                    actual.append(sum(c*v for c,v in zip(law.joint_z,vals))+law.flank_z[0]*fl+law.flank_z[1]*fr)
                self.assertEqual(law.z_interval(),(min(actual),max(actual)))

    def test_relative_law_cancels_shared_motion_before_enclosure(self):
        self.assertEqual(self.laws['L_TELESCOPE_1'].relative_to(self.laws['L_CROSSHEAD']).q_xyz,(F(0),)*3)
        self.assertEqual(self.laws['B_SHELL'].relative_to(self.laws['B_tail']),d.ZERO)
        self.assertEqual(self.laws['R_TELESCOPE_3'].z_interval(),(F(0),F(0)))

    def test_stop_height_enclosure_contains_all_four_continuous_branches(self):
        for law in (self.laws['L_STOP_0'],self.laws['L_STOP_0'].relative_to(self.laws['R_CROSSHEAD']),
                    self.laws['L_STOP_1'].relative_to(self.laws['R_STOP_0'])):
            for low,high in d.profile_intervals(self.profiles):
                vectors,intervals=law.enclosure_parameters(self.profiles,low,high)
                minima=[sum(min(v[a]*lo,v[a]*hi) for v,(lo,hi) in zip(vectors,intervals)) for a in range(3)]
                maxima=[sum(max(v[a]*lo,v[a]*hi) for v,(lo,hi) in zip(vectors,intervals)) for a in range(3)]
                for i in range(21):
                    q=low+(high-low)*i/20
                    xyz=law.coordinates(q,d.joint_vertices()[0],d.joint_vertices()[-1],(-1,1),self.profiles)
                    for a,x in enumerate(xyz):self.assertLessEqual(minima[a]-1e-12,x);self.assertLessEqual(x,maxima[a]+1e-12)

    def test_profile_intervals_have_no_gaps_and_keep_actual_breakpoints(self):
        intervals=d.profile_intervals(self.profiles)
        self.assertEqual(intervals[0][0],0.)
        self.assertEqual(intervals[-1][1],12.)
        self.assertEqual([a[1] for a in intervals[:-1]],[b[0] for b in intervals[1:]])
        self.assertEqual(set(q for row in intervals for q in row),{0.,12.,*self.profiles[0].breakpoints})

    def test_invalid_controls_and_outside_contact_travel_rejected(self):
        for low,high in ((-1,1),(0,13),(2,1),(False,1),(0,float('nan'))):
            with self.assertRaises(ValueError):d.q_interval(low,high)
        with self.assertRaises(ValueError):
            d.ZERO.coordinates(0,(.1,.1,.1),d.joint_vertices()[0],(0,0),self.profiles)
        with self.assertRaises(ValueError):
            d.ZERO.coordinates(0,d.joint_vertices()[0],d.joint_vertices()[0],(0,1.01),self.profiles)

    def test_diagnostic_domain_does_not_claim_nonzero_offsets_or_force_qualification(self):
        record=d.domain_record(self.profiles)
        self.assertFalse(record['all_nonzero_KEY_crosshead_clearance_states_included'])
        self.assertFalse(record['complete_G2_or_physical_qualification'])
        self.assertTrue(record['selected_contact_branch_requires_lower_restoring_force'])
        self.assertFalse(any(n=='cadquery' or n=='OCP' or n.startswith('OCP.') for n in sys.modules))


if __name__=='__main__':unittest.main()
