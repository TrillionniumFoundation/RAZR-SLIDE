"""Actual R50 AABB witnesses: mixed or aliased topology must never be discarded."""
from pathlib import Path
import sys
import unittest
import cadquery as cq

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from r50_full_span_finite_ribbon import solid_intersection
from occ_signed_volume import InconsistentGeometry


class R50TopologyParticipants(unittest.TestCase):
    def setUp(self):
        self.near=cq.Workplane('XY').box(1,1,1).val()
        self.far=cq.Workplane('XY').box(1,2,3).val().translate((10,0,0))
        self.loose=cq.Workplane('XY').rect(1,1).val().translate((12,0,0))

    def test_far_body_solid_plus_loose_wire_rejected_before_AABB(self):
        mixed=cq.Compound.makeCompound([self.far,self.loose])
        self.assertTrue(mixed.isValid());self.assertEqual(len(mixed.Solids()),1)
        self.assertGreater(mixed.Volume(),0)
        self.assertGreater(mixed.BoundingBox().xmin,self.near.BoundingBox().xmax)
        with self.assertRaises(InconsistentGeometry):solid_intersection([self.near],mixed)

    def test_far_cell_solid_plus_loose_wire_rejected_before_AABB(self):
        mixed=cq.Compound.makeCompound([self.far,self.loose])
        with self.assertRaises(InconsistentGeometry):solid_intersection([mixed],self.near)

    def test_far_body_repeated_existing_wire_rejected_despite_identical_counts(self):
        aliased=cq.Compound.makeCompound([self.far,self.far.Wires()[0]])
        self.assertTrue(aliased.isValid())
        for method in ('Vertices','Edges','Wires','Faces','Shells','Solids'):
            self.assertEqual(len(getattr(aliased,method)()),len(getattr(self.far,method)()))
        self.assertEqual(aliased.Volume(),self.far.Volume())
        with self.assertRaises(InconsistentGeometry):solid_intersection([self.near],aliased)

    def test_far_cell_repeated_existing_wire_rejected_before_AABB(self):
        aliased=cq.Compound.makeCompound([self.far,self.far.Wires()[0]])
        with self.assertRaises(InconsistentGeometry):solid_intersection([aliased],self.near)

    def test_pure_nested_single_child_wrappers_preserve_disjoint_and_overlap(self):
        wrapped=cq.Compound.makeCompound([cq.Compound.makeCompound([self.near])])
        self.assertEqual(wrapped.ShapeType(),'Compound')
        self.assertEqual(len(list(wrapped)),1)
        self.assertEqual(len(list(list(wrapped)[0])),1)
        self.assertEqual(solid_intersection([self.far],wrapped)['mm3'],0)
        result=solid_intersection([wrapped],self.near)
        self.assertAlmostEqual(result['mm3'],1)
        self.assertTrue(result['per_cell_signed_volumes_checked'])


if __name__=='__main__':unittest.main(verbosity=2)
