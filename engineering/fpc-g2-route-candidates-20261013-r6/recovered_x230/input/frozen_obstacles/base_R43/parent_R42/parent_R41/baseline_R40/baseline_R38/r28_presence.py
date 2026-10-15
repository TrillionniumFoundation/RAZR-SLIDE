"""R28 B-side vertical key-occupancy plunger, preliminary physically linked OCC.

Default (spring presumed) position puts a tooth across the parked OPEN-pawl's
lateral stroke. The A key upper shoulder physically interferes with the
unraised sensing foot during terminal docking; a hypothesized vertical stroke
lifts foot & blocking tooth together. NO actual cam force, spring return,
anti-pick enclosure, bearing, guaranteed seat datum, or retention is proven.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,blk,intersection,to_global
from r24_mechanics import a_key
from r26_open_mechanics import open_pawl
from r22_mechanics import to_blocal

SENSE_RISE_MM=1.00

def reflect(s,side):return s if side=='R' else s.mirror('YZ')

def blocker(side,rise=0.):
 if not 0<=rise<=SENSE_RISE_MM:raise ValueError(rise)
 # Toe on the pawl's swept X interval; default blocks +0.15/+0.3 motion.
 toe=blk(34.40,34.54,-4.49,-4.22,.43,.66)
 # Upper A-key occupancy shoe; the A male nose is at x>34.55 and Z up
 # to 6.65 in world coordinates. The B-local datum offset is +6.25 at seat.
 shoe=blk(34.525,34.65,-4.52,-4.32,-.20,-.05)
 # Rigid link from toe to shoe, no need for an abstract boolean sensor.
 stem=blk(34.50,34.55,-4.46,-4.34,-.075,.60)
 solid=toe.fuse(stem).fuse(shoe).clean()
 return reflect(solid,side).translate((0,0,rise))

def pawl_transit(side,x_mm):
 if not 0<=x_mm<=.55:raise ValueError(x_mm)
 return open_pawl(side,False).translate((x_mm if side=='R' else -x_mm,0.,0.))

def study(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R27_A_KEYED_UNCHANGED.brep')).val()
 rows=[]
 for side in 'LR':
  toe0=blocker(side,0.);toe1=blocker(side,SENSE_RISE_MM)
  v=[]
  for q in (0.,4.,6.,6.6,7.,7.5,7.8,8.0,8.1,8.15,8.2):
   v.append(dict(q_mm=q,
      A_key_vs_default_plunger_mm3=round(intersection(a_key('OPEN',side),to_global(toe0,'OPEN',P.travel,q)),9),
      A_key_vs_raised_plunger_mm3=round(intersection(a_key('OPEN',side),to_global(toe1,'OPEN',P.travel,q)),9),
      complete_A_vs_raised_plunger_mm3=round(intersection(A,to_global(toe1,'OPEN',P.travel,q)),9)))
  for shift in (0.,.15,.3,.45,.55):
   rows.append(dict(side=side,pawl_stroke_mm=shift,
     blocked_if_no_A_spring_down_mm3=round(intersection(toe0,pawl_transit(side,shift)),9),
     released_plunger_allows_pawl_mm3=round(intersection(toe1,pawl_transit(side,shift)),9)))
  rows.append(dict(side=side,station_probe=v,initial_one_connected=toe0.isValid() and len(toe0.Solids())==1,
      released_one_connected=toe1.isValid() and len(toe1.Solids())==1))
 out=dict(revision='R28 isolated A-key occupancy plunger, default normally blocking if spring works',
  A_key_to_plunger_and_pawl_geometry=rows,
  no_A_default_blocks_middle_pawl_translation=True,
  raised_B_local_z_max_mm=round(to_blocal(blocker("R",SENSE_RISE_MM),"OPEN").BoundingBox().zmax,6),
  inherited_B_nominal_thickness_limit_mm=7.2,
  raised_plunger_exceeds_B_nominal_envelope_by_mm=round(max(0.,to_blocal(blocker("R",SENSE_RISE_MM),"OPEN").BoundingBox().zmax-7.2),6),
  default_plunger_interferes_before_final_seat=True,
  candidate_rejected_not_integrated_into_B=True,
  actually_spring_loaded=False,
  early_A_key_can_raise_plunger_without_final_seat=True,
  actual_seat_driven_positive_catch_unproven=True,
  B_mount_and_guide_unbuilt=True,
  nominal_OLED_outer_encapsulation_unknown=True,
  manufacturing_go=False)
 if write:(ROOT/'verification'/'R28_presence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 x=study();print(json.dumps(x['A_key_to_plunger_and_pawl_geometry'][:6],indent=2))
