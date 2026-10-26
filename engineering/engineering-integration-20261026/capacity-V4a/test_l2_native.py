"""Native countercontrols for the new carriers; separate from the 89 L1 calls."""
import math
import cadquery as cq
import envelope_v2 as v2
from straight_envelope import whole_material
from translation_regions import subtract_regions, sum_common_upper_bound


def execute():
    rows=[]
    box=cq.Solid.makeBox(1.,1.,1.)
    for name,move in [('ordinary',(2.,.25,0.)),('tiny',(0.,4.440892098500626e-16,0.)),
                      ('negative',(-2.,-.25,0.)),('zero',(0.,0.,0.))]:
        pieces,meta=v2.regions(box,move)
        validations=[whole_material(p)[1] for p in pieces]
        values=[]
        for t in (0.,.25,.5,.75,1.):
            sample=box.translate(tuple(t*x for x in move))
            outside=whole_material(subtract_regions(sample,pieces),empty=True)[1]
            if outside>1e-7:raise ValueError('carrier loses native whole material: '+name)
            values.append(outside)
        rows.append({'name':name,'region_count':len(pieces),'signed_region_volumes_mm3':validations,
                     'finite_containment_crosschecks_mm3':values,
                     'finite_crosschecks_are_not_the_continuous_coverage_argument':True})
    try:v2.regions(box,(math.nan,0.,0.))
    except ValueError:rows.append({'name':'nonfinite_rejected','passed':True})
    else:raise ValueError('nonfinite displacement accepted')
    negative=cq.Shape.cast(box.wrapped.Reversed())
    try:v2.regions(negative,(1.,0.,0.))
    except ValueError:rows.append({'name':'negative_signed_material_rejected','passed':True})
    else:raise ValueError('negative material accepted')
    upper=sum_common_upper_bound([.6e-7,.6e-7])
    if upper<=1e-7:raise ValueError('original aggregate upper-sum guard weakened')
    rows.append({'name':'subtolerance_region_sums_still_rejected','upper_mm3':upper})
    return {'native_controls_completed':True,'controls':rows,'original_89_calls_included_in_this_count':False}
