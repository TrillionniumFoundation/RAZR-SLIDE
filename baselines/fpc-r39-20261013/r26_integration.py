"""R26 OCC B-shell integration of the rejected-R25 OPEN datum correction and lowered OPEN shutter.

Conservative swept bounding-box cavities are actual subtraction from R25 B.
This is deliberately NOT a finite-element model or an injection-moulded bracket.
"""
import cadquery as cq
import json
from r25_capture import ROOT,intersection
from r26_open_mechanics import open_pawl,open_carrier_ear,open_gate,OPEN_GATE_STROKE
from r24_integration import inflated_bbox
from r22_mechanics import to_blocal

R26_PAD=.04

def candidate_pockets():
    for side in 'LR':
        options=[('PARK_PAWL_INBOARD_X',[open_pawl(side,True),open_pawl(side,False)]),
                 ('OPEN_CARRIAGE_LOWER_LOAD_PATH',[open_carrier_ear(side,0.),open_carrier_ear(side,.8)]),
                 ('OPEN_STAGE2_GATE_SLIDE',[open_gate(side,0.),open_gate(side,OPEN_GATE_STROKE)])]
        for tag,parts in options:
            yield f'OPEN_{side}_{tag}',to_blocal(inflated_bbox(parts,pad=R26_PAD),'OPEN')

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad'/'R25_A_R24_KEYS.brep')).val()
    b25=cq.importers.importBrep(str(ROOT/'cad'/'R25_B_REWORKED.brep')).val()
    B=b25; rows=[]
    for name,pocket in candidate_pockets():
        removed=intersection(B,pocket)
        B=B.cut(pocket).clean()
        row=dict(name=name,pocket_volume_mm3=round(pocket.Volume(),8),newly_removed_B_mm3=round(removed,8),B_valid=B.isValid(),B_body_count=len(B.Solids()))
        rows.append(row)
        print('R26_BOOLEAN',name,round(removed,8),B.isValid(),len(B.Solids()),flush=True)
    # B-alone connectedness is insufficient to prove bearing/rail mount.
    valid=A.isValid() and len(A.Solids())==1 and B.isValid() and len(B.Solids())==1
    report=dict(revision='R26 actual OCC OPEN inboard pawl, lower carrier ear, stage2 gate swept cuts',
      A_reused_from_R25=True,base_B_brep_R25_sha256=None,
      new_pockets=len(rows),pockets=rows,all_OCC_shell_integrity_valid=valid,
      R26_B_is_single_solid=B.isValid() and len(B.Solids())==1,
      additional_B_cut_vs_R25_mm3=round(b25.Volume()-B.Volume(),8),
      R26_B_solid_volume_mm3=round(B.Volume(),8),
      original_B_rail_wall_minimum_from_R24_mm=.22,
      true_mounting_guides_retention_spring_screws_unbuilt=True,
      FEA_drop_torque_fatigue_and_corrosion_unverified=True,
      A_B_envelope_and_machining_draft_unapproved=True,
      manufacturing_go=False)
    if write:
        (ROOT/'verification'/'R26_integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        cq.exporters.export(A,str(ROOT/'cad'/'R26_A_UNCHANGED.brep'))
        cq.exporters.export(B,str(ROOT/'cad'/'R26_B_INBOARD_PAWL_OPEN_GATE_CUT.brep'))
    return report,(A,B)
if __name__=='__main__':
  d,_=run();print(json.dumps({k:v for k,v in d.items() if k!='pockets'},ensure_ascii=False,indent=2))
