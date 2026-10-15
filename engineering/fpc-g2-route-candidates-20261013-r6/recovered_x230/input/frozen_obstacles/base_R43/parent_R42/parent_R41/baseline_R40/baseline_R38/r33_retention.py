"""Actual OCC continuous sampled escape-axis penetration, installed/absent keeper.

A final withdrawn gauge has NO contact with the keeper after unrealistically
passing THROUGH it. Only a path sweep can establish the intervening barrier.
No force, pin shear, clip, seat-datum or qualified pin installation is modeled.
"""
from __future__ import annotations
import itertools,json
import cadquery as cq
from r25_capture import ROOT,intersection
from r33_parts import keeper_pin,bored_gauge,bore,PIN_R,BORE_R

WIDTHS=(0.0,0.02,0.05)
STEPS=(0.,-.02,-.04,-.06,-.08,-.10,-.15,-.25,-.50,-1.,-2.5)

def run(write=True):
    rows=[]
    for side in 'LR':
        pin=keeper_pin(side)
        for dy in STEPS:
            v=intersection(pin,bored_gauge(side,dy))
            rows.append(dict(side=side,gauge_y_shift_mm=dy,contact_mm3=round(v,10)))
        print('R33 KEEPER SWEEP',side,'done',flush=True)
    seated=[x for x in rows if x['gauge_y_shift_mm']==0]
    barrier=[x for x in rows if -0.5<=x['gauge_y_shift_mm']<0 and x['contact_mm3']>1e-8]
    fully_withdrawn=[x for x in rows if x['gauge_y_shift_mm']==-2.5]
    # The pin head lacks external locking, so the entire pin can be withdrawn in x.
    import cadquery as cq
    B=cq.importers.importBrep(str(ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep')).val()
    pin_axial=[]
    for side in 'LR':
        direction=1 if side=='R' else -1
        for dx in (0,.05,.25,.50,.75,1.0):
            move=keeper_pin(side).translate((direction*dx,0,0))
            v=intersection(move,bored_gauge(side))
            pin_axial.append(dict(side=side,withdraw_pin_x_mm=dx,
                         still_hits_gauge_mm3=round(v,9),
                         keeper_pin_B_interference_mm3=round(intersection(move,B),9)))
    # Off-axis datum error: with installed pin, assembly may JAM from hole shift.
    mismatch=[]
    for side in 'LR':
        p=keeper_pin(side)
        for w in (.02,.05):
            for yy,zz in itertools.product((-w,0,w),repeat=2):
                v=intersection(p,bored_gauge(side).translate((0,yy,zz)))
                mismatch.append(dict(side=side,magnitude_mm=w,delta_y_mm=yy,
                    delta_z_mm=zz,interference_mm3=round(v,10)))
    d=dict(revision='R33 bored gauge keeper pin positive local escape-path witness (NOT fail-safe device)',
           sweep_cases=len(rows),sweep=rows,
           seated_assembly_zero_interference=all(v['contact_mm3']<1e-8 for v in seated),
           withdrawal_barrier_paths=len(set(x['side'] for x in barrier)),
           fully_withdrawn_endpoint_misses_intermediate_barrier=all(v['contact_mm3']<1e-8 for v in fully_withdrawn),
           pin_missing_full_gauge_exit_not_resisted=True,
           pin_axial_escape_cases=pin_axial,
           pin_axial_no_B_stop_all_offsets=all(v['keeper_pin_B_interference_mm3']<1e-8 for v in pin_axial),
           pin_has_no_axial_capture_or_retaining_clip=True,
           misalignment_cases=mismatch,
           misalignment_jam_count=sum(x['interference_mm3']>1e-8 for x in mismatch),
           catalogue_pin_selected=False,
           no_shear_or_force_test=True,no_dirt_corrosion_wear_or_fatigue_data=True,
           legacy_mechanical_escape_counterexamples=36,
           mechanical_dock_release_is_NOT_improved_by_keeper=True,
           manufacturing_go=False)
    if write:(ROOT/'verification/R33_retention.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print('R33 RETENTION',d['withdrawal_barrier_paths'],'both?',d['misalignment_jam_count'],'/',len(mismatch),'mismatch jamming',flush=True)
    return d
if __name__=='__main__':run()
