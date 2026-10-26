"""Material-identity and connectivity counterexamples for new EP5 artwork."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'integration'))
import product_ep5_ecad as e


class EP5ArtworkTests(unittest.TestCase):
    def setUp(self):
        self.config = e.route_input()
        self.board = e.pcb(self.config)

    def reject(self, text):
        with self.assertRaises(ValueError):
            e.verify_artwork(text,self.config)

    def test_complete_new_material_and_copper(self):
        report = e.verify_artwork(self.board,self.config)
        self.assertEqual(report['pads'],52)
        self.assertEqual(report['tracks'],130)
        self.assertGreaterEqual(report['minimum_copper_edge_clearance_mm'],.5)
        self.assertGreaterEqual(report['track_clearance_mm'],.1)
        self.assertFalse(report['native_KiCad_DRC_executed'])

    def test_legacy_164_total_material_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            config = copy.deepcopy(self.config)
            config['route']['total_material_length_mm'] = 164
            p = Path(t)/'route.json'; p.write_text(json.dumps(config))
            with self.assertRaises(ValueError): e.route_input(p)

    def test_wrong_free_length_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            config = copy.deepcopy(self.config); config['route']['free_length_mm'] = 140
            p = Path(t)/'route.json'; p.write_text(json.dumps(config))
            with self.assertRaises(ValueError): e.route_input(p)

    def test_missing_copper_segment_is_rejected(self):
        lines = self.board.splitlines()
        index = next(i for i,x in enumerate(lines) if x.startswith('(segment'))
        self.reject('\n'.join(lines[:index]+lines[index+1:]))

    def test_endpoint_net_swap_is_rejected(self):
        self.reject(self.board.replace('(net 1 "C01"))','(net 2 "C02"))',1))

    def test_missing_pad_is_rejected(self):
        lines = self.board.splitlines()
        index = next(i for i,x in enumerate(lines) if x.startswith('(pad'))
        self.reject('\n'.join(lines[:index]+lines[index+1:]))

    def test_old_rectangular_outline_is_rejected(self):
        lines = self.board.splitlines()
        index = next(i for i,x in enumerate(lines) if x.startswith('(gr_line'))
        lines[index] = '(gr_line (start 6 0) (end 6 188) (layer "Edge.Cuts") (width .05))'
        self.reject('\n'.join(lines))

    def test_foreign_copper_is_rejected(self):
        self.reject(self.board[:-2]+'(via (at 0 50) (size 1) (drill .3) (layers "F.Cu" "B.Cu") (net 1))\n)\n')

    def test_wrong_copper_layer_is_rejected(self):
        self.reject(self.board.replace('(layers "F.Cu" "F.Mask")','(layers "B.Cu" "F.Mask")',1))

    def test_wrong_stack_sum_is_rejected(self):
        self.reject(self.board.replace('(thickness .062)','(thickness .063)',1))

    def test_duplicate_segment_is_rejected(self):
        line = next(x for x in self.board.splitlines() if x.startswith('(segment'))
        self.reject(self.board[:-2]+line+'\n)\n')

    def test_quintic_width_and_stiffened_regions_match_EP5(self):
        c = self.config
        for y in (0,3,12,176,185,188): self.assertEqual(e.width(y,c),12)
        for y in (16,50,100,172): self.assertAlmostEqual(e.width(y,c),10.8)
        self.assertAlmostEqual(e.width(14,c),11.4)
        self.assertAlmostEqual(e.width(174,c),11.4)

    def test_export_preserves_unknowns_and_existing_output(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)/'new'; report = e.export(out)
            self.assertTrue(report['research_26_conductors_routed_in_flat_artwork'])
            self.assertIsNone(report['OEM_pinmap'])
            self.assertIsNone(report['power_current_rating_A'])
            for key in ('candidate_go','fixture_fabrication_go','manufacturing_go','supplier_dynamic_qualified'):
                self.assertFalse(report[key])
            with self.assertRaises(ValueError): e.export(out)


if __name__ == '__main__': unittest.main()
