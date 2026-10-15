"""Two-spring axial roof-joint screening, not a thread-strength calculator.

Inputs must come from a selected joint/material/test. No strength is inferred
from a nominal M1 label or the count of pitch-lengths in a CAD cylinder.
Each load is for ONE screw; load sharing among four screws is not assumed.
The linear model ceases to describe the open joint after separation.
"""
from pathlib import Path
import argparse
import json
import math

FIELDS=('preload_min_N','preload_max_N','bolt_stiffness_N_per_mm','member_stiffness_N_per_mm',
        'external_axial_load_per_screw_N','bolt_tensile_allowable_N','female_thread_allowable_N',
        'roof_boss_allowable_N','bearing_allowable_N')


def screen(values):
    if not isinstance(values,dict):raise ValueError('named load inputs required')
    missing=[name for name in FIELDS if values.get(name) is None]
    for name in FIELDS:
        x=values.get(name)
        if x is not None and (type(x) not in (int,float) or not math.isfinite(x) or x<0):
            raise ValueError('finite nonnegative load input required: '+name)
    if missing:
        return {'status':'undetermined','missing_inputs':missing,'candidate_go':False,
                'reason':'nominal CAD geometry supplies no measured preload or material capacity'}
    a,b,kb,km,P,*limits=[values[name] for name in FIELDS]
    if a>b or kb<=0 or km<=0 or min(limits)<=0:raise ValueError('inconsistent preload, stiffness or allowable capacity')
    C=kb/(kb+km)
    if not 0<C<1:raise ValueError('ill-conditioned stiffness ratio')
    allowable=min(limits);clamp=a-(1-C)*P;bolt=b+C*P
    first_limit=min(a/(1-C),(allowable-b)/C)
    return {'status':'passes_this_axial_screen' if clamp>0 and bolt<=allowable else 'rejected_by_axial_screen',
            'bolt_load_fraction':C,'minimum_remaining_compression_N':clamp,
            'maximum_bolt_load_N_while_closed':bolt,'minimum_supplied_allowable_N':allowable,
            'external_axial_load_to_first_limit_N':max(0.,first_limit),
            'linear_result_is_invalid_after_separation':clamp<=0,'candidate_go':False,
            'scope':'one screw, axial quasistatic elastic screen; excludes prying, transverse slip, fatigue, torque scatter, temperature and manufacturing validation'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.inputs.read_text());result=screen(data['per_screw_inputs'])
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))
