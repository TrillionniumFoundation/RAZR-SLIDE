"""R28 explicit missing stack-up witnesses for thin cam slot web and A key."""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection,to_global
from r28_retraction import (pullback_gate,PLATE_X,PLATE_Y,PLATE_Z,
                              PIN_Y,PIN_Z_CLOSED,CARRIER_TRAVEL,
                              OPEN_GATE_STROKE,SLOT_HALF_WIDTH)

# Based on simple planar envelopes ONLY, NOT minimal OCC thickness maps.
minimum_plate_slot_edge_web_z=min(PLATE_Z[1]-(PIN_Z_CLOSED+CARRIER_TRAVEL+SLOT_HALF_WIDTH),
                                  (PIN_Z_CLOSED-SLOT_HALF_WIDTH)-PLATE_Z[0])

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R28_A_KEYED_UNCHANGED.brep')).val()
 rows=[]
 for side in 'LR':
  outward=(-1. if side=='L' else 1.)
  for gate_t in (0.,OPEN_GATE_STROKE):
   nominal=to_global(pullback_gate(side,gate_t),'OPEN',P.travel,P.z_travel)
   for delta in (-.05,-.02,0.,.02,.05):
    moved=nominal.translate(cq.Vector(outward*delta,0,0))
    rows.append(dict(side=side,gate_stroke_mm=gate_t,outward_axis_shift_mm=delta,
      A_vs_cam_intersection_mm3=round(intersection(A,moved),9)))
 result=dict(revision='R28 A-side male keyed shell vs slotted gate shifted in X by hypothetical errors',
   scan_cases=len(rows),rows=rows,
   original_outboard_plate_X_thickness_mm=round(PLATE_X[1]-PLATE_X[0],6),
   planar_slot_min_residual_Z_web_mm=round(minimum_plate_slot_edge_web_z,6),
   before_pocket_front_B_relief_margin_mm=round(PLATE_Y[0]+5.,6),
   after_nominal_pocket_front_B_relief_margin_mm=round(PLATE_Y[0]+5.-.025,6),
   outward_0p02_nominal_A_collision_cases=sum(r['A_vs_cam_intersection_mm3']>1e-9 for r in rows if r['outward_axis_shift_mm']==.02),
   outward_0p05_nominal_A_collision_cases=sum(r['A_vs_cam_intersection_mm3']>1e-9 for r in rows if r['outward_axis_shift_mm']==.05),
   NOTE_offset_not_actual_GDT=True,
   actual_key_x_position_and_full_OLED_encapsulation_unapproved=True,
   manufacturing_go=False)
 if write:(ROOT/'verification'/'R28_clearance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result
if __name__=='__main__':
 x=run();print('R28 clearance count',x['scan_cases'],'key hits @ +0.05',x['outward_0p05_nominal_A_collision_cases'],'slot min web',x['planar_slot_min_residual_Z_web_mm'])
