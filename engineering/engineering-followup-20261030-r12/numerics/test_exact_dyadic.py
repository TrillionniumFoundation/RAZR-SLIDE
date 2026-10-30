"""Independent exact-reference edge cases and original-data artifact mutations."""
from fractions import Fraction as Q
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import struct
import sys

import numpy as np
from exact_dyadic import exact_dot64
from read_portable_load_map import validate_terms_and_map


def bits(x):return struct.pack('>d',float(x))


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--r9-reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
    tiny=math.ldexp(1.,-1074);big=float.fromhex('0x1.fffffffffffffp1023')
    cases=[([],[]),([1.,1.],[1.,math.ldexp(1.,-53)]),([1.,1.,1.],[1.,math.ldexp(1.,-52),math.ldexp(1.,-53)]),
        ([tiny],[.5]),([tiny,tiny],[1.,.5]),([-tiny],[.5]),([big,big],[2.,-2.]),([big],[2.]),
        ([1e16,1.,-1e16],[1.,1.,1.]),([math.ldexp(1.,-1022),tiny],[1.,-0.5]),([-0.,0.],[1.,1.])]
    rng=random.Random(73021)
    for _ in range(160):
        def draw():return math.ldexp(rng.uniform(1.,2.)*rng.choice((-1.,1.)),rng.choice([-1074,-1023,-1022,-1000,-53,-1,0,1,500,1023]))
        n=rng.randrange(1,13);cases.append(([draw() for _ in range(n)],[draw() for _ in range(n)]))
    records=[]
    for i,(left,right) in enumerate(cases):
        exact=sum((Q(x)*Q(y) for x,y in zip(left,right)),Q())
        try:expected=float(exact);overflow=False
        except OverflowError:overflow=True
        try:
            result=exact_dot64(left,right)
            if overflow:raise AssertionError('expected overflow rejection')
            assert bits(result.value)==bits(expected) and Q(result.integer)*Q(2)**result.exponent==exact
            records.append(dict(case=i,passed=True,result_hex=result.value.hex(),overflow_rejected=False))
        except OverflowError:
            assert overflow;records.append(dict(case=i,passed=True,overflow_rejected=True))
    invalid=[]
    for name,left,right in [('nan',[float('nan')],[1.]),('infinity',[1.],[float('inf')]),('length',[1.],[])]:
        try:exact_dot64(left,right)
        except ValueError:invalid.append(name)
        else:raise AssertionError('invalid input accepted: '+name)
    ref=json.loads(a.r9_reference.read_text())['loadG_exact_reference']
    with np.load(a.run/'original_nonzero_terms.npz',allow_pickle=False) as z:terms={k:z[k] for k in z.files}
    mapped=np.load(a.run/'portable_loadG.npy',allow_pickle=False)
    permutation_checks=0
    for i,row in enumerate(ref):
        lo,hi=map(int,terms['offsets'][i:i+2]);order=list(range(lo,hi))
        for _ in range(5):
            rng.shuffle(order);value=exact_dot64(terms['left'][order],terms['right'][order]).value
            assert bits(value)==bits(mapped[row['row'],row['column']]);permutation_checks+=1
    controls=[]
    def rejection(name,t,m):
        tp=a.output/(name+'-terms.npz');mp=a.output/(name+'-map.npy')
        np.savez(tp,**t);np.save(mp,m,allow_pickle=False)
        try:validate_terms_and_map(tp,mp,ref)
        except ValueError as exc:controls.append(dict(name=name,rejected=True,reason=str(exc)))
        else:raise AssertionError('tampered artifact accepted: '+name)
    changed={k:v.copy() for k,v in terms.items()};changed['left'][0]=math.nextafter(float(changed['left'][0]),math.inf)
    rejection('changed-original-term',changed,mapped)
    altered=mapped.copy();altered[0,0]=math.nextafter(float(altered[0,0]),math.inf)
    rejection('changed-rounded-entry',terms,altered)
    rejection('transposed-map',terms,mapped.T)
    bad={k:v.copy() for k,v in terms.items()};bad['offsets'][1]+=1
    rejection('changed-term-support',bad,mapped)
    result=dict(schema='r12.exact_dyadic_differential_and_negative_controls.v1',completed=True,
        independent_fraction_edge_and_random_cases=records,invalid_input_rejections=invalid,
        original24_order_permutations_passed=permutation_checks,actual_retained_mutation_controls=controls,
        algorithm_is_versioned=True,old_seed_or_original_gate_modified=False)
    (a.output/'TEST_REPORT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(completed=True,differential_cases=len(records),invalid_rejections=len(invalid),permutations=permutation_checks,actual_mutation_rejections=len(controls))))


if __name__=='__main__':main()
