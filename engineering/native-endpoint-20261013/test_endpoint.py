#!/usr/bin/env python3
"""Independent dimensional checks against EDC page-1 dimensions, not snapshots."""
import math
import re
import unittest

from build_endpoint import OFFICIAL, rectangles, orientation_map, kicad_footprint, COUPON


class EndpointChecks(unittest.TestCase):
    def assert_near(self,a,b):
        self.assertTrue(math.isclose(a,b,rel_tol=0,abs_tol=1e-10),(a,b))

    def test_twenty_four_signal_contacts_two_common_power_fittings(self):
        for role in ('DP','DS'):
            p=rectangles(role)
            self.assertEqual(len([x for x in p if x['kind']=='signal']),24)
            self.assertEqual(len(p),28)
            self.assertEqual(len(set(x['site'] for x in p)),26)
            for side in ('L','R'):
                self.assertEqual(len([x for x in p if x['site']=='P_'+side]),2)

    def test_signal_pitch_and_first_to_last_span(self):
        for role in ('DP','DS'):
            for row in ('NEG','POS'):
                p=[x for x in rectangles(role) if x['site'].startswith('S_'+row)]
                self.assert_near(p[-1]['x']-p[0]['x'],3.85)
                for a,b in zip(p,p[1:]):self.assert_near(b['x']-a['x'],.35)
                self.assert_near(min(x['x'] for x in p),-1.925)
                self.assert_near(max(x['x'] for x in p),1.925)

    def test_DP_copper_spans(self):
        # Independent complete spans, not constructor implementation equality.
        signals=[x for x in rectangles('DP') if x['kind']=='signal']
        upper=[x for x in signals if x['y']>0]
        self.assert_near(upper[0]['y']-upper[0]['h']/2,.285)
        self.assert_near(upper[0]['y']+upper[0]['h']/2,.9)
        p=[x for x in rectangles('DP') if x['kind']=='power' and x['y']>0]
        self.assert_near(p[0]['y']-p[0]['h']/2,.125)
        self.assert_near(p[0]['y']+p[0]['h']/2,.525)
        self.assert_near((p[1]['x']-p[1]['w']/2)-(p[0]['x']+p[0]['w']/2),4.51)

    def test_DS_copper_spans(self):
        signals=[x for x in rectangles('DS') if x['kind']=='signal' and x['y']>0]
        self.assert_near(signals[0]['y']-signals[0]['h']/2,.59)
        self.assert_near(signals[0]['y']+signals[0]['h']/2,.9)
        p=[x for x in rectangles('DS') if x['kind']=='power' and x['y']>0]
        self.assert_near(p[0]['y']-p[0]['h']/2,.62)
        self.assert_near(p[0]['y']+p[0]['h']/2,.95)
        self.assert_near(p[1]['x']-p[0]['x'],5.26)

    def test_exact_DP_80_percent_power_stencil(self):
        cu=[x for x in rectangles('DP') if x['kind']=='power']
        paste=[x for x in rectangles('DP',paste=True) if x['kind']=='power']
        for a,b in zip(cu,paste):
            self.assert_near(b['w']*b['h']/(a['w']*a['h']),.8)
            self.assert_near(a['x'],b['x']);self.assert_near(a['y'],b['y'])
        for a,b in zip(rectangles('DS'),rectangles('DS',paste=True)):
            self.assert_near(a['w']*a['h'],b['w']*b['h'])

    def test_adjacent_signal_copper_gap_is_0p17(self):
        for role in ('DP','DS'):
            self.assert_near(OFFICIAL[role]['pitch']-OFFICIAL[role]['signal_width'],.17)

    def test_wrong_orientation_changes_all_signal_and_both_power_identities(self):
        rx=orientation_map('X');ry=orientation_map('Y')
        self.assertEqual(len(rx),26)
        self.assertEqual(len({r['DS_site'] for r in rx}),26)
        self.assertEqual(len({r['DS_site'] for r in ry}),26)
        self.assertEqual(len([1 for a,b in zip(rx,ry) if a['DS_site']!=b['DS_site']]),26)
        self.assertEqual(rx[0]['DS_site'],'S_POS_00')
        self.assertEqual(ry[0]['DS_site'],'S_NEG_11')
        self.assertEqual(rx[-2]['DS_site'],'P_L')
        self.assertEqual(ry[-2]['DS_site'],'P_R')

    def test_footprint_has_exact_copper_and_independent_stencil(self):
        for role in ('DP','DS'):
            text=kicad_footprint(role)
            self.assertEqual(len(re.findall(r'\(pad "',text)),28)
            self.assertEqual(text.count('(layers "F.Cu" "F.Mask")'),28)
            self.assertEqual(text.count('(layer "F.Paste")'),28)
            self.assertNotIn('(pad "1"',text)
            self.assertIn('NO_PIN1_NO_NETS',text)
            self.assertIn('exclude_from_pos_files exclude_from_bom',text)

    def test_complete_sexpression_closes_both_keepout_and_footprint(self):
        for role in ('DP','DS'):
            # The rejected DS lacked the zone closing parenthesis. Ignore all
            # quoted strings so their punctuation cannot influence the grammar.
            text=re.sub(r'"(?:[^"\\]|\\.)*"','""',kicad_footprint(role))
            balance=0
            for ch in text:
                if ch=='(':balance+=1
                elif ch==')':balance-=1
                self.assertGreaterEqual(balance,0)
            self.assertEqual(balance,0)

    def test_DS_under_body_trace_keepout_does_not_cross_lands(self):
        x=2.630-.530/2;y=.59
        for p in rectangles('DS'):
            xhit=min(x,p['x']+p['w']/2)-max(-x,p['x']-p['w']/2)
            yhit=min(y,p['y']+p['h']/2)-max(-y,p['y']-p['h']/2)
            self.assertFalse(xhit>1e-10 and yhit>1e-10,p)
        self.assertIn('(tracks not_allowed)',kicad_footprint('DS'))

    def test_minimum_stiffener_and_separate_compliant_buffer(self):
        self.assertGreaterEqual(COUPON['stiffener_t'],.3)
        self.assertGreater(COUPON['buffer_compressed_t'],0)
        self.assertGreaterEqual(COUPON['fpc_tab_x'],7.)
        self.assertGreaterEqual(COUPON['fpc_tab_y'],1.9)
        self.assertEqual(COUPON['free_neck_length'],8.)


if __name__=='__main__':unittest.main(verbosity=2)
