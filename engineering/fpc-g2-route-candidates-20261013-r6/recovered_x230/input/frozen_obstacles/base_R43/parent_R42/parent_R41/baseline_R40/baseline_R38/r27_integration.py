"""Actual OCC shell subtract on top of R26 for the R27 captive blade's sweep.

One per-side swept bounding-box cut is performed in the R26 *real* B shell,
not represented by annotation or a saved fake result.  A connected B after
subtraction says nothing about local wall fatigue or anchor retention.
"""
from __future__ import annotations
import json,hashlib
import cadquery as cq
from r25_capture import ROOT,intersection
from r22_mechanics import to_blocal
from r24_integration import inflated_bbox
from r27_mechanics import open_gate_captive
from r26_open_mechanics import OPEN_GATE_STROKE

PADDING_MM=.04

def candidate_cuts():
    for side in 'LR':
        shapes=[open_gate_captive(side,0.),open_gate_captive(side,OPEN_GATE_STROKE)]
        yield side,to_blocal(inflated_bbox(shapes,pad=PADDING_MM),'OPEN')

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad'/'R26_A_UNCHANGED.brep')).val()
    base=cq.importers.importBrep(str(ROOT/'cad'/'R26_B_INBOARD_PAWL_OPEN_GATE_CUT.brep')).val()
    B=base;rows=[]
    for side,pocket in candidate_cuts():
        removed=intersection(B,pocket)
        new=B.cut(pocket).clean()
        rows.append(dict(side=side,new_material_removed_mm3=round(removed,9),
            swept_pocket_volume_mm3=round(pocket.Volume(),9),
            valid=new.isValid(),body_count=len(new.Solids())))
        B=new
        print('R27 CUT',side,round(removed,9),'connected',len(B.Solids()),flush=True)
    result=dict(revision='R27 actual OCC B shell subtract for pre-extended carrier interception',
        baseline_B_R26_SHA256=hashlib.sha256((ROOT/'cad'/'R26_B_INBOARD_PAWL_OPEN_GATE_CUT.brep').read_bytes()).hexdigest(),
        A_unmodified=True,pocket_count=len(rows),pockets=rows,
        all_shells_one_valid_body=(A.isValid() and B.isValid() and len(A.Solids())==len(B.Solids())==1),
        B_volume_after_mm3=round(B.Volume(),9),additional_cut_over_R26_mm3=round(base.Volume()-B.Volume(),9),
        minimum_support_web_FEA_unqualified=True,local_original_R24_web_only_0p22mm=True,
        no_mounting_boss_screw_preload_or_return_spring=True,manufacturing_go=False)
    if write:
        cq.exporters.export(A,str(ROOT/'cad'/'R27_A_KEYED_UNCHANGED.brep'))
        cq.exporters.export(B,str(ROOT/'cad'/'R27_B_CAPTIVE_OPEN_GATE_CUT.brep'))
        (ROOT/'verification'/'R27_integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result,(A,B)

if __name__=='__main__':
    print(run()[0]['additional_cut_over_R26_mm3'])
