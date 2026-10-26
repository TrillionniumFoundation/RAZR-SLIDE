"""Pure rational L5 source/bridge checks; does not import or execute CAD."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import cylindrical_sweep_l5 as l5
from exact_xy_support_l5 import certified_bridge, support_certificate


def execute(root):
    here=Path(__file__).resolve().parent
    binding=json.loads((here/'L5_ORIGINAL_SEVEN_BINDING.json').read_text())
    for name,record in binding['source_files'].items():
        data=(root/name).read_bytes()
        assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
    sections=l5.source_sections(root);rows=[];bridges=[]
    for original in binding['original_cases']:
        target=original['target'];value=l5.plan(target,target['specification'],sections)
        expected=.7+sum([float(F(17,6))]*(2 if target['b'].endswith('TELESCOPE_2') else 3))
        assert value['native_q0_origin_mm'][2]==expected
        assert value['prototype_None_default_joint_branch_used'] is False
        assert F(value['centerline_endpoint_L1_rounding_bound_exact'])>=F(value['original_binary64_coefficient_centerline_L1_endpoint_error_exact'])>0
        assert value['both_continuous_affine_centerlines_covered_by_endpoint_convexity'] is True
        rows.append({'case_id':original['case_id'],'plan':value})
        for i,layer in enumerate(value['layers']):
            points,proof=certified_bridge(value['centerline_endpoints_native'],layer['outer_native_radius'])
            assert proof['continuous_planar_rectangle_inclusion_proved']
            assert support_certificate(value['centerline_endpoints_native'],layer['outer_native_radius'],points)['continuous_rectangle_contained']
            reverse,reverse_proof=certified_bridge(value['centerline_endpoints_native'][::-1],layer['outer_native_radius'])
            assert reverse_proof['continuous_planar_rectangle_inclusion_proved']
            bridges.append({'case_id':original['case_id'],'layer_index':i,'ordinary':proof,'reversed':reverse_proof})
    # Actual rounded coordinates, continuous half-space test, no CAD samples.
    unit_quad=[(0.,1.),(0.,-1.),(2.,-1.),(2.,1.)]
    assert support_certificate([(0.,0.),(2.,0.)],1.,unit_quad)['continuous_rectangle_contained']
    assert not support_certificate([(0.,0.),(2.,0.)],math.nextafter(1.,math.inf),unit_quad)['continuous_rectangle_contained']
    assert not support_certificate([(0.,0.),(2.,0.)],1.,unit_quad[::-1])['continuous_rectangle_contained']
    assert len(rows)==7 and len(bridges)==12
    return {'schema':'razr-L5-pure-source-support-readback-v2','passed':True,
        'source_cases_checked':7,'complete_source_layers_checked':12,
        'source_plans':rows,'exact_continuous_bridge_checks':bridges,
        'negative_controls':{'one_ulp_radius_undercoverage_rejected':True,'negative_winding_rejected':True},
        'explicit_original_SLIDE_q0_reference':'float(Fraction(17,6))',
        'original_q0_joint_mm':float(F(17,6)),
        'prototype_None_branch_not_substituted':True,
        'native_CAD_executed':False,'original_EXTRUSION_branch_executed':False,
        'formal_interval_CAD_certificate':False,'candidate_go':False}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--output',type=Path);a=ap.parse_args();result=execute(a.source_root)
    text=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if a.output:a.output.write_text(text)
    print(json.dumps({k:result[k] for k in ('passed','source_cases_checked','complete_source_layers_checked','native_CAD_executed','original_EXTRUSION_branch_executed')}))

if __name__=='__main__':main()
