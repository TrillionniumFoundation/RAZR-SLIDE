"""R29 10 complete A/B/OLED/FPC reference poses and coupled OPEN cam proxy.

Full OEM stack and continuous motion not sampled. An OPEN gate actuation is not
permitted at mid-slide; we still check closed and fully open envelope against
fixed A/chassis/OLED/FPC for collision risk.
"""
from __future__ import annotations
import cadquery as cq,json
from r25_capture import ROOT,P,intersection,to_global
from r25_dynamic import POSES
from r24_mechanics import r21,INBOARD_OLED_X_HALF
from r22_mechanics import to_blocal
from r29_mechanics import pullback_gate,carrier_with_pin,theoretical_extension

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R29_A_R28_FROZEN_KEYS.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R29_B_REVISED_SLOT_POCKET.brep')).val()
 rows=[];bad=[]
 for name,s,q in POSES:
  ref=r21.r17_assembly(P,s,q,1. if name=='OPEN_SEATED' else 0.)
  Bworld=B.translate((0,s,-P.z_travel+q))
  vs=dict(A_vs_B=round(intersection(A,Bworld),9),B_vs_OLED=round(intersection(Bworld,ref['OLED']),9),B_vs_FPC=round(intersection(Bworld,ref['FPC']),9))
  if any(v>1e-7 for v in vs.values()):bad.append(dict(pose=name,part='CHASSIS',clashes=vs))
  rows.append(dict(pose=name,part='CHASSIS',clashes=vs))
  for side in 'LR':
   for stage,gate,ear in [('CLOSED',0.,0.),('OPEN',.9,.8)]:
    for part,solid in [(f'OPEN_{side}_CAM_SHUTTER_{stage}',pullback_gate(side,gate)),
                      (f'OPEN_{side}_FOLLOWER_{stage}',carrier_with_pin(side,ear))]:
      world=to_global(solid,'OPEN',s,q)
      vals=dict(A=round(intersection(A,world),9),OLED=round(intersection(ref['OLED'],world),9),
            FPC=round(intersection(ref['FPC'],world),9),
            B=round(intersection(B,to_blocal(solid,'OPEN')),9))
      if any(x>1e-7 for x in vals.values()):bad.append(dict(pose=name,part=part,clashes=vals))
      rows.append(dict(pose=name,part=part,clashes=vals))
  print('R29 POSE',name,'unexpected so far',len(bad),flush=True)
 output=dict(revision='R29 10 stationary ref poses; R29 gate closed/open parts vs A/B/hypothetical OLED-FPC',
      pose_count=len(POSES),tested_rows=len(rows),unexpected_collision_count=len(bad),unexpected_collisions=bad,
      sampled_rows=rows,nominal_old_OLED_gap_x_min_mm=round(33.79-INBOARD_OLED_X_HALF,8),
      true_oled_full_stack_missing=True,no_continuous_key_followers_spring_qualified=True,
      manufacturing_go=False)
 if write:(ROOT/'verification'/'R29_dynamic.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 return output
if __name__=='__main__':
 r=run();print('collisions',r['unexpected_collision_count'])
