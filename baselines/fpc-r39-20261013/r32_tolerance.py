"""R32 cassette insertion pressure scan. XYZ offsets are ASSUMED, not GD&T.

The cassette is a *solid gauge* with no leads, fasteners or insulating ribs.
Failures are recorded as evidence, not silently excluded from PASS verdicts.
"""
from __future__ import annotations
import json,itertools
import cadquery as cq
from r25_capture import ROOT,intersection
from r32_cartridge import gauge

WIDTHS=(.02,.05,.10)

def run(write=True):
    B=cq.importers.importBrep(str(ROOT/'cad'/'R32_B_REAR_CASSETTE_BAYS.brep')).val()
    rows=[]
    for side in 'LR':
        for w in WIDTHS:
            for dx,dy,dz in itertools.product((-w,0.,w),repeat=3):
                part=gauge(side).translate(cq.Vector(dx,dy,dz))
                v=intersection(B,part)
                rows.append(dict(side=side,width_mm=w,xyz_mm=(dx,dy,dz),
                        CAD_interference_mm3=round(v,10),jam=v>1e-8))
            print('R32 TOL',side,w,'cases',len(rows),flush=True)
    hard=[]
    for side in 'LR':
        for name,xyz in (
            ('overshoot_y_0p20',(0.,.20,0.)),
            ('withdraw_y_minus_2p50',(0.,-2.50,0.)),
            ('outboard_x_0p14',(.14 if side=='R' else -.14,0.,0.)),
            ('inboard_x_0p14',(-.14 if side=='R' else .14,0.,0.)),
            ('z_up_0p14',(0.,0.,.14)),('z_down_0p14',(0.,0.,-.14))):
            hard.append(dict(side=side,test=name,offset_mm=xyz,
                interference_mm3=round(intersection(B,gauge(side).translate(cq.Vector(*xyz))),10)))
    per=[]
    for w in WIDTHS:
        rr=[x for x in rows if x['width_mm']==w]
        per.append(dict(width_mm=w,count=len(rr),jam_count=sum(x['jam'] for x in rr)))
    d=dict(revision='R32 assumed XYZ pressure on non-energized gauge, rigid OCC collision only',
        configurations=len(rows),results_by_width=per,rows=rows,hard_stop_and_withdrawal_probes=hard,
        cassette_retainer_absent_withdrawal_unopposed=True,
        no_supplier_real_GDT_or_material_spring_tolerance=True,
        body_clearance_not_a_contact_path_or_load_qualification=True,
        manufacturing_go=False)
    if write:(ROOT/'verification'/'R32_tolerance.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d
if __name__=='__main__':
    d=run();print('R32 tol conclusion',d['results_by_width'],d['hard_stop_and_withdrawal_probes'],flush=True)
