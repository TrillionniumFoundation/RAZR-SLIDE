"""108 ideal-BOX offset OCC checks; x/y/z assumed +/- 0.02 or 0.05.

They do not include actual TE tolerances, adhesive stack, mounting pads or load.
"""
from __future__ import annotations
import json,itertools
import cadquery as cq
from r25_capture import ROOT,intersection
from r34_parts import te_signal_envelope

WIDTHS=(.02,.05,.10,.12)

def run(write=True):
    B=cq.importers.importBrep(str(ROOT/'cad/R34_B_OPEN_SIGNAL_ENVELOPE_CRADLES.brep')).val()
    records=[]
    for w in WIDTHS:
        for side in 'LR':
            proxy=te_signal_envelope(side)
            for dx,dy,dz in itertools.product((-w,0,w),repeat=3):
                sh=proxy.translate((dx,dy,dz))
                v=intersection(sh,B)
                records.append(dict(side=side,hypothetical_axis_offset_magnitude_mm=w,
                    xyz_mm=[dx,dy,dz],interference_mm3=round(v,9)))
            print('R34 offset scan',side,w,'done',flush=True)
    by_width={str(w):dict(cases=sum(x['hypothetical_axis_offset_magnitude_mm']==w for x in records),
      hits=sum(x['hypothetical_axis_offset_magnitude_mm']==w and x['interference_mm3']>1e-7 for x in records)) for w in WIDTHS}
    out=dict(revision='R34 3-axis nominal bounding-gauge rigid geometry tolerance sampling',
             cases=len(records),offset_aggregation=by_width,records=records,
             no_GDT_from_real_connector=True,no_thermal_wear_or_transient_load=True,
             breakaway_and_retention_NOT_tested=True,manufacturing_go=False)
    if write:(ROOT/'verification/R34_tolerance.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':run()
