"""Exact slot-law domain without treating ContactProfile limits as hard stops.

This is a derived source-geometry calculation, not a physical allowable-domain
or native CAD result. The source-bound positive-q analysis supplies a and b.
"""
from __future__ import annotations
import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-analysis',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();basis=json.loads(args.source_analysis.read_text())
    assert basis['functional_source_commit']=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
    a=basis['nominal_source_halfwidths_mm']['crosshead']
    b=basis['nominal_source_halfwidths_mm']['dx_minus_dq'];K=12/79.75
    vertices=[]
    for s,dxL,eL,dxR,eR in itertools.product((F(0),F('79.75')),(-F(a),F(a)),(-F(b),F(b)),(-F(a),F(a)),(-F(b),F(b))):
        x=(s,dxL,dxL-eL,dxR,dxR-eR);qL=F(K)*s+x[2];qR=F(K)*s+x[4]
        vertices.append({'coordinates_exact':list(map(str,x)),'coordinates_binary64':list(map(float,x)),
            'qL_exact':str(qL),'qR_exact':str(qR),
            'outside_declared_ContactProfile_q':[qL<0 or qL>12,qR<0 or qR>12]})
    assert len(vertices)==32
    result={'schema':'razr-S4-unclipped-slot-source-domain-v1',
        'functional_source_commit':basis['functional_source_commit'],
        'basis_positive_q_analysis_sha256':hashlib.sha256(args.source_analysis.read_bytes()).hexdigest(),
        'source_identities':basis['source_identities'],
        'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'coordinate_order':['slide','crosshead_L','KEY_L','crosshead_R','KEY_R'],
        'constraints':'0<=s<=79.75; |dx_i|<=a; |dx_i-dq_i|<=b; no ContactProfile q clipping',
        'source_binary64_constants':{'K':K,'a_mm':a,'b_mm':b},
        'exact_slot_only_vertices':vertices,'vertex_count':len(vertices),
        'vertices_with_at_least_one_side_outside_profile_domain':sum(any(x['outside_declared_ContactProfile_q']) for x in vertices),
        'source_nominal_offset_projection_halfwidth_mm':a+b,
        'exact_real_q_projection_mm':[str(-F(a)-F(b)),str(F(K)*F('79.75')+F(a)+F(b))],
        'approximate_q_projection_mm':[-a-b,12+a+b],
        'exact_real_K_times_decimal_STROKE_minus_12':str(F(K)*F('79.75')-12),
        'source_slot_comparison_TOL_shell_included':False,
        'floating_point_acceptance_set_proved_equal_to_real_polytope':False,
        'profile_outside_current_domain_evaluable':False,
        'physical_allowed_domain_or_hard_stops_proved':False,'new_CAD_executed':False,
        'excluded_states_claimed_impossible':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('vertex_count','vertices_with_at_least_one_side_outside_profile_domain','exact_real_q_projection_mm')}))


if __name__=='__main__':main()
