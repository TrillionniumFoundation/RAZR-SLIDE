"""Pure controls for domain preservation and unfinished inventory; no CAD."""
from fractions import Fraction as F
from pathlib import Path
import json
import os
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import full_slide_api_v4 as api
import capacity_stage_v4 as stage


class Contract:
    def specifications(self,a,b,lo,hi,frame):
        return [{'moving': {}, 'fixed': {}, 'interval': [str(lo),str(hi)]}]
    def child_intervals(self,lo,hi,split):
        if split=='all_actual_profile_breakpoints':
            return ((F(0),F('5e-16')),(F('5e-16'),F(3)),(F(3),F(6)),(F(6),F(9)),(F(9),F(12)))
        mid=(lo+hi)/2
        return ((lo,mid),(mid,hi))


class Bodies:
    def material(self,*unused): return object()


def evaluate(value):
    def run(a,b,spec,target):
        return {'schema':api.SCHEMA,'source_specification':spec,'disposition':value,
                'common_upper_bound_mm3':0.}
    return run


class Checks(unittest.TestCase):
    def test_all_original_recursive_calls_and_epsilon(self):
        calls=[]
        def run(a,b,spec,target):
            calls.append(target['q_interval_exact'])
            return evaluate('unresolved_enclosure_overlap')(a,b,spec,target)
        result=stage.evaluate_interval('A','B',0,12,contract=Contract(),bodies=Bodies(),api=api,
            evaluate_specification=run,budget_check=lambda:None,checkpoint=lambda r:None)
        self.assertEqual(len(calls),36)
        self.assertEqual(result['disposition'],'unresolved_enclosure_overlap')
        self.assertEqual(result['closed_partition_exact'][0],['0','1/2000000000000000'])

    def test_real_error_not_partitioned_away(self):
        result=stage.evaluate_interval('A','B',0,12,contract=Contract(),bodies=Bodies(),api=api,
            evaluate_specification=evaluate('unresolved_evaluation'),budget_check=lambda:None,checkpoint=lambda r:None)
        self.assertEqual(result['disposition'],'unresolved_evaluation')
        self.assertNotIn('children',result)

    def test_budget_retains_partial(self):
        def stop(): raise RuntimeError('capacity guard')
        with self.assertRaises(api.CapacityStop) as c:
            stage.evaluate_interval('A','B',0,12,contract=Contract(),bodies=Bodies(),api=api,
                evaluate_specification=evaluate('clear'),budget_check=stop,checkpoint=lambda r:None)
        self.assertEqual(c.exception.partial['disposition'],'unresolved_budget')
        self.assertEqual(c.exception.partial['q_interval_exact'],['0','12'])

    def test_full_inventory_is_never_faked_complete(self):
        source=Path(os.environ['GITHUB_WORKSPACE'])/'engineering/engineering-integration-20261025/geometry/seating/seating-inventory.json'
        names=json.loads(source.read_text())['names']
        contract=Contract();contract.names=names
        self.assertEqual(len(stage.priority_pairs(names)),17)
        result=stage.run_capacity_pairs(contract=contract,bodies=Bodies(),api=api,
            evaluate_specification=evaluate('clear'),budget_check=lambda:None,checkpoint=lambda r:None,
            construction_receipt={'five_factory_probes_complete':True})
        self.assertTrue(result['execution_completed'])
        self.assertEqual(result['full_inventory_status']['counts'],{'clear':17,'not_evaluated':11764})
        self.assertFalse(result['full_inventory_status']['all_pairs_evaluated'])
        self.assertFalse(result['all_11781_native_pairs_executed'])


if __name__=='__main__':unittest.main()
