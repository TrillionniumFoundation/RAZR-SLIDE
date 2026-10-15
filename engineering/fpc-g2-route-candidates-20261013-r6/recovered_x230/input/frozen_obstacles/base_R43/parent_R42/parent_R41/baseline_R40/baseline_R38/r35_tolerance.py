"""Hypothetical rigid XYZ fixture-offset stress grid, NOT real OEM GD&T.
Each candidate position evaluates cap vs B, cap vs TE AABB, and nominal pin vs cap.
A `hit` indicates an interference/jam risk; mechanical capture contact is a different test.
"""
import json,itertools
import cadquery as cq
from r25_capture import ROOT,intersection
from r35_parts import bored_cap,pin,te_signal_envelope
WIDTHS=(.02,.05,.10,.12)

def run(write=True):
    B=cq.importers.importBrep(str(ROOT/'cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep')).val()
    out=[]
    for w in WIDTHS:
        for side in 'LR':
            cap=bored_cap(side);needle=pin(side);te=te_signal_envelope(side)
            for dx,dy,dz in itertools.product((-w,0,w),repeat=3):
                c=cap.translate((dx,dy,dz))
                out.append(dict(side=side,w=w,xyz=[dx,dy,dz],cap_vs_B=round(intersection(c,B),9),
                     cap_vs_TE_catalogue=round(intersection(c,te),9),
                     nominal_pin_vs_misaligned_cap=round(intersection(c,needle),9)))
            print('R35 TOL',w,side,'27 positions',flush=True)
    agg={str(w):dict(configurations=sum(x['w']==w for x in out),
         cap_B_jams=sum(x['w']==w and x['cap_vs_B']>1e-7 for x in out),
         cap_TE_jams=sum(x['w']==w and x['cap_vs_TE_catalogue']>1e-7 for x in out),
         pin_cap_jams=sum(x['w']==w and x['nominal_pin_vs_misaligned_cap']>1e-7 for x in out))
         for w in WIDTHS}
    d=dict(revision='R35 3-axis rigid OFFSET stress not OEM tolerances',records=out,aggregation=agg,
         configurations=len(out),checked_collisions_per_config=3,
         qualified_fastener_manufacturing_GDT_missing=True,
         real_battery_board_and_OLED_package_not_included=True,manufacturing_go=False)
    if write:(ROOT/'verification/R35_tolerance.json').write_text(json.dumps(d,indent=2)+'\n')
    return d
if __name__=='__main__':print('AGGREGATION',run()['aggregation'],flush=True)
