"""Evidence-integrity regressions for the new external experiment, no CAD stand-in claim."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import f1_common as f

class Budget:
    def __init__(self,p):self.out=p;self.start=f.time.monotonic()
    def check(self):return {'test_fake_budget':True}

class Assembly:
    def __init__(self,values):self.values=iter(values)
    def strict_common(self,a,b):return {'common_mm3':next(self.values),'method':'test-record-only'}
    def volume(self,x):return x

class Body:
    def __init__(self,value=.25):self.value=value
    def intersect(self,other):return self.value

class EvidenceRecords(unittest.TestCase):
    def run_pairs(self,parts,values,old=None,export_error=False):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);r={};budget=Budget(out)
            with patch.object(f,'export',side_effect=ValueError('simulated export refusal') if export_error else lambda *a,**k: {'test':True}):
                f.evaluate_pairs(parts,out,r,Assembly(values),budget,original=old)
            disk=json.loads((out/'report.json').read_text())
            events=[json.loads(x) for x in (out/'pairs.jsonl').read_text().splitlines()]
            self.assertEqual(disk,r)
            self.assertEqual([x['row'] for x in events if x['event']=='completed'],r['pairs'])
            self.assertEqual(len(events),2*len(r['pairs']))
            return r
    def test_complete_unordered_inventory_and_journal(self):
        r=self.run_pairs({'C':Body(),'A':Body(),'B':Body()},[0,0,0])
        self.assertEqual([(x['a'],x['b']) for x in r['pairs']],[('A','B'),('A','C'),('B','C')])
        self.assertTrue(r['all_unordered_pairs_present_once']);self.assertTrue(r['finite_pose_clear'])
    def test_export_failure_keeps_measured_positive_and_failed_journal_row(self):
        r=self.run_pairs({'A':Body(),'B':Body()},[.25],export_error=True)
        self.assertEqual(r['pairs'][0]['common_mm3'],.25)
        self.assertEqual(r['positive_pairs'][0]['common_mm3'],.25)
        self.assertIn('post_evaluation_failure',r['pairs'][0]);self.assertEqual(len(r['evaluation_failures']),1)
        self.assertFalse(r['finite_pose_clear'])
    def test_invalid_signed_value_is_failure_not_clear(self):
        r=self.run_pairs({'A':Body(),'B':Body()},[-.1])
        self.assertTrue(r['pairs'][0]['evaluation_failed']);self.assertFalse(r['finite_pose_clear'])
    def test_reader_detects_classification_change_even_small_absolute_difference(self):
        old={'pairs':[{'a':'A','b':'B','common_mm3':1.000001e-7,'rejected':True}]}
        r=self.run_pairs({'A':Body(0.999999e-7),'B':Body(0.999999e-7)},[0.999999e-7],old)
        self.assertEqual(len(r['mismatches_to_factory']),1)
        self.assertFalse(r['pairs'][0]['factory_classification_and_volume_consistent'])
    def test_factory_error_cannot_become_successful_readback_match(self):
        old={'pairs':[{'a':'A','b':'B','evaluation_failed':True}]}
        r=self.run_pairs({'A':Body(),'B':Body()},[0],old)
        self.assertEqual(len(r['mismatches_to_factory']),1)
        self.assertIsNone(r['pairs'][0]['factory_difference_mm3'])

if __name__=='__main__':unittest.main()
