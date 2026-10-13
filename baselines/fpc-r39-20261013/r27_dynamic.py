"""R27 registered A/B/OLED/FPC 10 discrete poses plus stage2 gate states.

Maintains exact declared R26 pose set; no claim about continuous dynamics,
OEM outer display edge or operating clearances under forces and tolerances.
"""
from __future__ import annotations
import cadquery as cq,json
from r25_capture import ROOT,P,intersection,to_global
from r25_dynamic import POSES
from r24_mechanics import r21,INBOARD_OLED_X_HALF
from r26_open_mechanics import open_carrier_ear,open_pawl
from r27_mechanics import open_gate_captive
from r22_mechanics import to_blocal

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R27_A_KEYED_UNCHANGED.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R27_B_CAPTIVE_OPEN_GATE_CUT.brep')).val()
 rows=[];bad=[]
 for tag,s,q in POSES:
  ref=r21.r17_assembly(P,s,q,1. if tag=='OPEN_SEATED' else 0.)
  worldB=B.translate((0,s,-P.z_travel+q))
  ch=dict(A_B=round(intersection(A,worldB),8), B_OLED=round(intersection(worldB,ref['OLED']),8),B_FPC=round(intersection(worldB,ref['FPC']),8))
  if any(v>1e-7 for v in ch.values()):bad.append(dict(pose=tag,part='CHASSIS',clash=ch))
  rows.append(dict(pose=tag,part='CHASSIS',clash=ch))
  for side in 'LR':
   for part,sh in [('NEW_CLOSED_SHUTTER',open_gate_captive(side,0.)),
                   ('NEW_MANUALLY_OPEN_SHUTTER',open_gate_captive(side,.9)),
                   ('PARKED_PAWL',open_pawl(side,False)),
                   ('CARRIER_RETRACTED',open_carrier_ear(side,0.))]:
    world=to_global(sh,'OPEN',s,q)
    vals=dict(A=round(intersection(world,A),8),OLED=round(intersection(world,ref['OLED']),8),
              FPC=round(intersection(world,ref['FPC']),8),B=round(intersection(to_blocal(sh,'OPEN'),B),8))
    if any(x>1e-7 for x in vals.values()):bad.append(dict(pose=tag,side=side,part=part,clash=vals))
    rows.append(dict(pose=tag,side=side,part=part,clash=vals))
  print('R27_POSE',tag,len(bad),flush=True)
 out=dict(revision='R27 ten R26-compatible selected nominal poses, two OPEN gate states',
  pose_count=len(POSES),tested_items=len(rows),unexpected_collision_count=len(bad),
  unexpected_collision_cases=bad,per_part=rows,
  nominal_OLED_edge_gap_worst_from_inherited_OPEN_gate_mm=round(33.79-INBOARD_OLED_X_HALF,8),
  nominal_B_top_clearance_worst_inherited_R26_mm=.11,
  OLED_edge_and_full_encapsulation_not_OEM_qualified=True,
  no_continuous_dynamic_OR_real_mount_qualification=True,manufacturing_go=False)
 if write:(ROOT/'verification'/'R27_dynamic.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 print('unexpected',run()['unexpected_collision_count'])
