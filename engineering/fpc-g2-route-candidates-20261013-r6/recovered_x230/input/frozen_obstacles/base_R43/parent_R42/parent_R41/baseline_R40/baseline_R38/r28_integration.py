"""R28 actual OCC B-shell relief for OPEN positive-pullback plate and pin.

Boolean validity is not strength or retention qualification. Both old R24
thin web and R28 new near-edge lip are manufacturing HOLD conditions.
"""
from __future__ import annotations
import json,hashlib
import cadquery as cq
from r25_capture import ROOT,intersection
from r22_mechanics import to_blocal
from r24_integration import inflated_bbox
from r28_retraction import (pullback_gate,carrier_with_pin,PLATE_Y,
                              PIN_RADIUS,OPEN_GATE_STROKE,CARRIER_TRAVEL)
PAD=.025
BASE_B=ROOT/'cad'/'R27_B_CAPTIVE_OPEN_GATE_CUT.brep'
BASE_A=ROOT/'cad'/'R27_A_KEYED_UNCHANGED.brep'

def candidate_cuts():
 for side in 'LR':
  # A bounding envelope is conservative and overcuts relative to exact swept
  # geometry, so it MUST be audited independently for wall preservation.
  yield f'OPEN_{side}_PULLBACK_GATE_PLATE_SWEEP',to_blocal(
      inflated_bbox([pullback_gate(side,t) for t in (0.,OPEN_GATE_STROKE)],pad=PAD),'OPEN')
  yield f'OPEN_{side}_PIN_WEB_CARRIER_SWEEP',to_blocal(
      inflated_bbox([carrier_with_pin(side,e) for e in (0.,CARRIER_TRAVEL)],pad=PAD),'OPEN')

def run(write=True):
 A=cq.importers.importBrep(str(BASE_A)).val()
 B=cq.importers.importBrep(str(BASE_B)).val()
 original=B; cuts=[]
 for name,cut in candidate_cuts():
  diff=intersection(B,cut)
  nextB=B.cut(cut).clean()
  cuts.append(dict(name=name,nominal_bbox_cut_volume_mm3=round(cut.Volume(),9),
       actual_new_B_material_removed_mm3=round(diff,9),
       new_shell_valid=nextB.isValid(),new_shell_solids=len(nextB.Solids()),
       intersects_existing_shell=diff>1e-10))
  B=nextB
  print('R28 SHELL',name,'removed',round(diff,8),'valid',B.isValid(),'solids',len(B.Solids()),flush=True)
 # Defer costly B-vs-part checks to R28_dynamic.py, which separately
 # verifies A/B/OLED/FPC full assembly. This avoids repeated broad BRep
 # Boolean intersections during the same shell-export step.
 controls=[]
 report=dict(revision='R28 actual OCC B cavity relative to preserved R27 shell',
   source_R27_B_SHA256=hashlib.sha256(BASE_B.read_bytes()).hexdigest(),
   A_unchanged=True,actual_B_relieved_with_OCC=True,cut_count=len(cuts),cuts=cuts,
   A_valid_single_body=A.isValid() and len(A.Solids())==1,
   B_valid_single_body=B.isValid() and len(B.Solids())==1,
   B_R28_volume_mm3=round(B.Volume(),8),additional_B_removed_mm3=round(original.Volume()-B.Volume(),8),
   samples=controls,full_pose_check_deferred_to_R28_dynamic=True,
   nominal_front_B_gate_margin_mm=round(PLATE_Y[0]+5,4),
   presumed_min_front_B_margin_after_relief_mm=round(PLATE_Y[0]+5-PAD,4),
   # These are hold observations; true local wall thickness requires proper
   # solid-distance + pressure FEM & actual process tolerances.
   near_boundary_hypothetical_lip_unqualified=True,
   no_machinable_bearing_anchor_screw_boss_FEA=True,
   inherited_R24_0p22mm_side_rail_unqualified=True,
   power_OLED_material_qualification_missing=True,
   manufacturing_go=False)
 if write:
  cq.exporters.export(A,str(ROOT/'cad'/'R28_A_KEYED_UNCHANGED.brep'))
  cq.exporters.export(B,str(ROOT/'cad'/'R28_B_PULLOUT_CAM_RELIEVED.brep'))
  (ROOT/'verification'/'R28_integration.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 return report,(A,B)

if __name__=='__main__':
 report,_=run()
 print('TOTAL CUT',report['additional_B_removed_mm3'],'connected',report['B_valid_single_body'])
