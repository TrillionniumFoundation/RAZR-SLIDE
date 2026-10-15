"""R29 OCC subtract from the *actual R28 B-shell*; NO strength certification."""
from __future__ import annotations
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,intersection
from r22_mechanics import to_blocal
from r24_integration import inflated_bbox
from r29_mechanics import (pullback_gate,carrier_with_pin,OPEN_GATE_STROKE,CARRIER_TRAVEL,
                            nominal_planar_webs)
PADDING_MM=.025
BASE=ROOT/'cad'/'R28_B_PULLOUT_CAM_RELIEVED.brep'
A_BASE=ROOT/'cad'/'R28_A_KEYED_UNCHANGED.brep'

def candidate_cuts():
 for side in 'LR':
  for label,shapes in [('FRAME',[pullback_gate(side,t) for t in (0.,OPEN_GATE_STROKE)]),
                       ('PIN',[carrier_with_pin(side,e) for e in (0.,CARRIER_TRAVEL)])]:
   yield side,label,to_blocal(inflated_bbox(shapes,pad=PADDING_MM),'OPEN')

def run(write=True):
 A=cq.importers.importBrep(str(A_BASE)).val()
 baseline=cq.importers.importBrep(str(BASE)).val()
 B=baseline;rows=[]
 for side,label,sh in candidate_cuts():
  removed=intersection(B,sh)
  n=B.cut(sh).clean()
  rows.append(dict(side=side,part=label,swept_envelope_mm3=round(sh.Volume(),8),
     new_cut_from_R28_mm3=round(removed,8),valid=n.isValid(),single=len(n.Solids())==1))
  B=n
  print('R29 SHELL',side,label,round(removed,8),'valid',n.isValid(),'solids',len(n.Solids()),flush=True)
 result=dict(revision='R29 actual BRep relief based on frozen R28 B shell',
  source_R28_B_SHA256=hashlib.sha256(BASE.read_bytes()).hexdigest(),
  source_R28_A_SHA256=hashlib.sha256(A_BASE.read_bytes()).hexdigest(),
  A_unchanged=True,subtractions=rows,B_baseline_volume_mm3=round(baseline.Volume(),8),
  B_R29_volume_mm3=round(B.Volume(),8),additional_B_removed_mm3=round(baseline.Volume()-B.Volume(),8),
  valid_single_A=A.isValid() and len(A.Solids())==1,
  valid_single_B=B.isValid() and len(B.Solids())==1,
  near_front_nominal_web_not_structurally_qualified=True,
  no_added_guide_boss_or_anchored_bearing=True,
  original_R24_0p22mm_rail_web_unqualified=True,
  dimensions_are_research_values=nominal_planar_webs(),manufacturing_go=False)
 if write:
  cq.exporters.export(A,str(ROOT/'cad'/'R29_A_R28_FROZEN_KEYS.brep'))
  cq.exporters.export(B,str(ROOT/'cad'/'R29_B_REVISED_SLOT_POCKET.brep'))
  (ROOT/'verification'/'R29_integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result,(A,B)
if __name__=='__main__':
 r,_=run();print('R29 B cut',r['additional_B_removed_mm3'],flush=True)
