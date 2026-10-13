"""R26 full-shell/OLED/FPC probes using reworked R26 A/B OCC bodies.

Samples only; a true continuous collision/dynamics/force test requires further
CAD and actual OEM envelope. Deliberate unsafe pose witnesses are separately
exported and do not count as clean travel.
"""
import cadquery as cq
import json
from r25_capture import ROOT,P,intersection,to_global,a_key
from r25_dynamic import POSES
from r24_mechanics import r21,INBOARD_OLED_X_HALF,outboard_jaws
from r26_open_mechanics import open_pawl,open_gate,open_carrier_ear,OPEN_GATE_STROKE
from r22_mechanics import to_blocal

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad'/'R26_A_UNCHANGED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad'/'R26_B_INBOARD_PAWL_OPEN_GATE_CUT.brep')).val()
    rows=[];bad=[]
    for tag,s,q in POSES:
      refs=r21.r17_assembly(P,s,q,1. if tag=='OPEN_SEATED' else 0.)
      b_world=B.translate(cq.Vector(0,s,-P.z_travel+q))
      chassis=dict(A_B_intersection_mm3=round(intersection(A,b_world),8),
        B_OLED_mm3=round(intersection(b_world,refs['OLED']),8),
        B_FPC_mm3=round(intersection(b_world,refs['FPC']),8))
      if any(v>1e-7 for v in chassis.values()):bad.append(dict(pose=tag,chassis=chassis))
      for side in 'LR':
       items={'OPEN_PAWL_PARK':open_pawl(side,False),
              'OPEN_GATE_CLOSED':open_gate(side,0.),
              'OPEN_LOWER_CARRIAGE_RETRACTED':open_carrier_ear(side,0.)}
       for part,shape in items.items():
        world=to_global(shape,'OPEN',s,q)
        clash=dict(A=round(intersection(A,world),8),
              OLED=round(intersection(refs['OLED'],world),8),
              FPC=round(intersection(refs['FPC'],world),8),
              B=round(intersection(B,to_blocal(shape,'OPEN')),8))
        if any(v>1e-7 for v in clash.values()):bad.append(dict(pose=tag,side=side,part=part,clash=clash))
        rows.append(dict(pose=tag,side=side,part=part,clashes=clash))
      rows.append(dict(pose=tag,part='CHASSIS',clashes=chassis))
      print('R26_POSE',tag,'chassis',chassis,'accumulated_unspecified_clashes',len(bad),flush=True)
    atseat=[]
    for side in 'LR':
     for active in (False,True):
      pawl=open_pawl(side,active)
      atseat.append(dict(side=side,engaged=active,
        dock_A_full_shell_mm3=round(intersection(A,to_global(pawl,'OPEN',P.travel,P.z_travel)),8),
        B_body_mm3=round(intersection(B,to_blocal(pawl,'OPEN')),8)))
     atseat.append(dict(side=side,gate_manual_open=True,
       manual_gate_A_shell=round(intersection(A,to_global(open_gate(side,OPEN_GATE_STROKE),'OPEN',P.travel,P.z_travel)),8),
       manual_gate_B_body=round(intersection(B,to_blocal(open_gate(side,OPEN_GATE_STROKE),'OPEN')),8)))
    result=dict(revision='R26 actual R25 + OPEN 2nd gate modified shell, 10 nominal discrete poses',
      pose_count=len(POSES),per_part_clashes=rows,
      unexpected_discrete_clashes=bad,unexpected_count=len(bad),
      seated_STOW_and_OPEN_no_corresponding_early_energization_claim=True,
      NEW_OPEN_pawl_park_vs_complete_A_shell_atseat=atseat,
      R25_original_OPEN_pawl_park_vs_A_shell_collision_was_unchecked=True,
      OPEN_gate_min_assumed_OLED_outer_edge_nominal_gap_mm=round(33.79-INBOARD_OLED_X_HALF,6),
      OPEN_gate_native_shell_top_clearance_mm=round(7.2-(6.25+.84),6),
      OEM_OLED_width_material_tolerance_missing=True,
      guide_mount_material_and_spring_missing=True,
      manufacturing_go=False)
    if write:(ROOT/'verification'/'R26_dynamic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
if __name__=='__main__':
 d=run();print('R26_DYNAMIC',len(d['unexpected_discrete_clashes']),flush=True)
