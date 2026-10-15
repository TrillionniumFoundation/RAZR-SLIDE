"""Reject the tempting reduced-stroke R28 occupancy plunger.

Reducing B envelope overhang from +0.71 to 0 does NOT clear the A-side key;
no claim of seat-qualified engagement or spring force is possible.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,to_global,intersection
from r28_presence import blocker,pawl_transit
from r22_mechanics import to_blocal

SHORT_STROKE=.28

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R29_A_R28_FROZEN_KEYS.brep')).val()
 rows=[]
 for side in 'LR':
  sh=blocker(side,SHORT_STROKE)
  for q in (6.6,7.8,8.,8.1,8.2):
   rows.append(dict(side=side,q_mm=q,
    raised_blocker_vs_entire_A_mm3=round(intersection(A,to_global(sh,'OPEN',P.travel,q)),9)))
  for shift in (.15,.30,.45):
   rows.append(dict(side=side,pawl_shift_mm=shift,
     raised_blocker_vs_pawl_mm3=round(intersection(sh,pawl_transit(side,shift)),9)))
 max_z=to_blocal(blocker('R',SHORT_STROKE),'OPEN').BoundingBox().zmax
 out=dict(revision='R29 rejected reduced-stroke B plunger',
  hypothetical_rise_mm=SHORT_STROKE,B_local_Z_max_mm=round(max_z,6),
  B_nominal_max_mm=7.2,outside_B_envelope=bool(max_z>7.2),rows=rows,
  raised_plunger_interferes_with_A_at_final_seat=any(x.get('q_mm')==8.2 and x.get('raised_blocker_vs_entire_A_mm3',0)>1e-8 for x in rows),
  short_rise_still_physically_stops_pawl=any(x.get('raised_blocker_vs_pawl_mm3',0)>1e-8 for x in rows),
  cannot_claim_no_A_false_capture_resolved=True,
  candidate_rejected_not_integrated=True,manufacturing_go=False)
 if write:(ROOT/'verification'/'R29_presence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 r=run();print('R29 PRESENCE REJECT',r['raised_plunger_interferes_with_A_at_final_seat'])
