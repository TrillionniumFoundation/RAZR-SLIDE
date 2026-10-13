"""Signed independent XYZ OCC positional offsets: rigid cap vs integral hook.
Do not interpret any pass as production GD&T/force/temperature/lifetime.
"""
import itertools,json
from r25_capture import ROOT,intersection
from r35_parts import bored_cap
from r37_parts import lip
WIDTHS=(.02,.05,.1)

def run(write=True):
    rows=[]
    for width in WIDTHS:
        for side in 'LR':
            hook=lip(side);cap=bored_cap(side)
            for dx,dy,dz in itertools.product((-width,0.,width),repeat=3):
                loc=cap.translate((dx,dy,dz))
                pulling=loc.translate((0,-.05,0))
                rows.append(dict(side=side,hypothetical_error_mm=width,xyz_mm=[dx,dy,dz],
                    installed_lip_jam_mm3=round(intersection(hook,loc),9),
                    forced_forward_0p05_lip_contact_mm3=round(intersection(hook,pulling),9)))
        print('R37 tolerance',width,54,flush=True)
    agg={str(w):dict(configurations=sum(x['hypothetical_error_mm']==w for x in rows),
        installed_clash=sum(x['hypothetical_error_mm']==w and x['installed_lip_jam_mm3']>1e-8 for x in rows),
        no_catch_by_0p05=sum(x['hypothetical_error_mm']==w and x['forced_forward_0p05_lip_contact_mm3']<1e-8 for x in rows))
        for w in WIDTHS}
    out=dict(revision='R37 rigid lip XY/Z hypothetical offsets',
      configuration_count=len(rows),OCC_intersections=len(rows)*2,rows=rows,aggregation=agg,
      tolerance_relaxed_without_supplier_GDT=False,
      cannot_claim_no_jam_and_safe_stop_at_0p05_under_worst_offset=True,
      contact_electrical_pre_touch_distance_unmeasured=True,
      real_material_flexibility_unknown=True,
      manufacturing_go=False)
    if write:(ROOT/'verification/R37_tolerance.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':run()
