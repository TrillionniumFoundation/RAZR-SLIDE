"""OCC shell-level R31 adaptation: real A male ledges and moving B plunger
cavities. No assertion of actual spring/rod bearing attachment or strength.
"""
from __future__ import annotations
import json,hashlib
import cadquery as cq
from r25_capture import ROOT,P,blk,intersection
from r22_mechanics import to_blocal
from r30_integration import A_BASE as _R30_IGNORED
from r31_presence import a_occupied_shelf,interposer,mirror,MAX_STROKE
from r24_integration import inflated_bbox

A_PATH=ROOT/'cad'/'R30_A_R29_KEYS_FROZEN.brep'
B_PATH=ROOT/'cad'/'R30_B_LONGITUDINAL_REBASE.brep'
A_OUT=ROOT/'cad'/'R31_A_POSITIVE_OPEN_SHELVES.brep'
B_OUT=ROOT/'cad'/'R31_B_PRESENCE_POCKETS.brep'
POCKET_PAD=.02

def plunger_cut(side):
    # Exact local OCC envelope bounding rest to fully-pushed, not a software flag.
    return to_blocal(inflated_bbox([interposer(side,0.),interposer(side,MAX_STROKE)],pad=POCKET_PAD),'OPEN')

def shelf_sweep_cut(side):
    # A fixed shelf in world, B moves upward from q=7.3 to q=8.2.
    # Before q=7.3, shelf is ABOVE B's upper nominal 7.2 mm bound.
    a=a_occupied_shelf(side)
    return inflated_bbox([a.translate((0,-P.travel,P.z_travel-q)) for q in (7.3,P.z_travel)],pad=POCKET_PAD)

def run(write=True):
    A0=cq.importers.importBrep(str(A_PATH)).val()
    B0=cq.importers.importBrep(str(B_PATH)).val()
    A=A0; B=B0; rows=[]
    for side in 'LR':
        sh=a_occupied_shelf(side)
        before=A.Volume()
        A=A.fuse(sh).clean()
        rows.append(dict(side=side,operation='FUSE_A_LATE_SHELF', added_mm3=round(A.Volume()-before,9),
                         previous_A_overlap_mm3=round(intersection(A0,sh),9),
                         connected=A.isValid() and len(A.Solids())==1))
    for side in 'LR':
        for label,cutter in (('B_PLUNGER_SWEEP_CUT',plunger_cut(side)),('B_A_SHELF_SWEEP_CUT',shelf_sweep_cut(side))):
            before=B.Volume()
            B=B.cut(cutter).clean()
            rows.append(dict(side=side,operation=label,removed_mm3=round(before-B.Volume(),9),
                 connected=B.isValid() and len(B.Solids())==1,
                 nominal_cutter_volume_mm3=round(cutter.Volume(),7)))
            print('R31',side,label,'removed',rows[-1]['removed_mm3'], 'single',rows[-1]['connected'],flush=True)
    result=dict(revision='R31 initial OPEN late-key-driven plunger CAD feasibility',
        A_base_sha256=hashlib.sha256(A_PATH.read_bytes()).hexdigest(),
        B_base_sha256=hashlib.sha256(B_PATH.read_bytes()).hexdigest(),
        A_valid_single=A.isValid() and len(A.Solids())==1,
        B_valid_single=B.isValid() and len(B.Solids())==1,
        A_old_volume_mm3=round(A0.Volume(),9),A_new_volume_mm3=round(A.Volume(),9),
        B_old_volume_mm3=round(B0.Volume(),9),B_new_volume_mm3=round(B.Volume(),9),
        operations=rows,
        no_real_prismatic_bearing_spring_fastener_or_force_test=True,
        existing_R29_0p03mm_web_not_structurally_repaired=True,
        no_OEM_mating_contact_or_electrical_proof=True,manufacturing_go=False)
    if write:
        cq.exporters.export(A,str(A_OUT));cq.exporters.export(B,str(B_OUT))
        (ROOT/'verification'/'R31_integration.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result,(A,B)

if __name__=='__main__':
    r,_=run();print('R31 VOLUME',r['B_old_volume_mm3'],r['B_new_volume_mm3'],'A',r['A_new_volume_mm3'],flush=True)
