"""Small non-native contract controls for the prospective V4 API."""
from pathlib import Path
from fractions import Fraction
import argparse
from collections import Counter
import hashlib
import json
import sys
import full_slide_api_v4 as api


def rejected(function):
    try:function()
    except ValueError:return True
    raise AssertionError('invalid contract was accepted')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline-repo',type=Path,required=True)
    ap.add_argument('--original-dir',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();checks=[]
    names=json.loads((args.baseline_repo/'engineering/engineering-integration-20261025/geometry/seating/seating-inventory.json').read_text())['names']
    inventory=api.initialize_inventory(names);state=api.inventory_status(inventory,names)
    assert len(inventory)==11781 and not state['all_pairs_evaluated'] and not state['all_pairs_numerically_clear']
    rejected(lambda:api.inventory_status(inventory[:-1],names))
    duplicate=[*inventory[:-1],inventory[-2]];rejected(lambda:api.inventory_status(duplicate,names))
    checks.append('all_11781_slots_retained_missing_or_duplicate_rejected')
    routes=Counter()
    for path in args.original_dir.glob('case-*/result.json'):
        t=json.loads(path.read_text())['target'];routes[api.correlated_family(t['a'],t['b']) or 'V2']+=1
    assert dict(routes)=={'V2':19,'KEY_STOP':36,'SPRING_STOP':34},routes
    checks.append('all_89_original_call_routes_exactly_36_KEY_34_spring_19_other')
    lo='1285835921349979/2000000000000000';hi='64291796067499/100000000000000'
    assert Fraction(hi)-Fraction(lo)==Fraction(1,2000000000000000)
    parts=api.require_closed_partition('0','12',[('0',lo),(lo,hi),(hi,'12')])
    assert parts[1]==[lo,hi]
    rejected(lambda:api.require_closed_partition('0','12',[('0',lo),(hi,'12')]))
    checks.append('nonzero_exact_epsilon_interval_retained_gap_rejected')
    specs=[{'id':0},{'id':1}]
    rows=[{'schema':api.SCHEMA,'source_specification':s,'disposition':'clear','common_upper_bound_mm3':6e-8} for s in specs]
    result=api.aggregate_complete_pair(specs,rows)
    assert result['disposition']=='unresolved_enclosure_overlap' and result['complete_body_common_upper_bound_mm3']==1.2e-7
    rejected(lambda:api.aggregate_complete_pair(specs,rows[:1]))
    rows[0]['common_upper_bound_mm3']=-1e-20;rejected(lambda:api.aggregate_complete_pair(specs,rows))
    checks.append('original_whole_pair_sum_gate_negative_value_and_omission_controls')
    coefficients=[[2.,-3.,.25],[-.5,4.,0.]];domain=[[-1.,2.],[3.,5.]]
    bounds=api.outward_translation_bounds(coefficients,domain)
    for axis in range(3):
        values=[Fraction.from_float(coefficients[0][axis])*Fraction.from_float(a)
              +Fraction.from_float(coefficients[1][axis])*Fraction.from_float(b)
              for a in domain[0] for b in domain[1]]
        assert Fraction.from_float(bounds[2*axis])<=min(values)<=max(values)<=Fraction.from_float(bounds[2*axis+1])
    checks.append('affine_interval_arithmetic_contains_exact_rational_linear_extrema')
    try:api.check_budget(lambda:(_ for _ in ()).throw(RuntimeError('synthetic exhausted capacity')))
    except api.CapacityStop:pass
    else:raise AssertionError('capacity stop not propagated')
    checks.append('capacity_stop_has_separate_failure_type')
    assert not any(n=='cadquery' or n=='OCP' or n.startswith('OCP.') for n in sys.modules)
    output={'schema':'razr-full-slide-api-pure-controls-v1','api_sha256':hashlib.sha256(Path(api.__file__).read_bytes()).hexdigest(),
            'checks_passed':checks,'original_call_route_counts':dict(routes),'native_executed':False,
            'CAD_imported':False,'K1_full_factory_or_continuous_domain_qualified':False}
    args.output.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))


if __name__=='__main__':main()
