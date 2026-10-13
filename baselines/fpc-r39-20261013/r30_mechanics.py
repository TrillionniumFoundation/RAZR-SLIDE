"""R30 feasible rigid research candidate after REJECTING outboard-plate
relocation: keep R29 original A-safe cam/pin and add a rearward SLIDING TAIL
on the same one-piece shutter to mate with a real B-shell guide sleeve.

This is a geometrical support-path candidate, not fail-safe protection, no
fabricated pins/bearings/preload, and the R29 thin forward edge STILL exists.
"""
from __future__ import annotations
from r25_capture import blk
from r29_mechanics import (pullback_gate as original_gate,
 carrier_with_pin as original_carrier,theoretical_extension,
 mirrored,nominal_planar_webs,PLATE_X,PLATE_Y,PLATE_Z,
 PIN_Y,PIN_Z_CLOSED,PIN_RADIUS,SLOT_HALF_WIDTH,
 CARRIER_TRAVEL,OPEN_GATE_STROKE)

# B-fixture OPEN Y: add +5.0 to obtain B-local Y.  All mm.
TAIL=(34.47,34.525,-3.55,-.75,-3.90,-3.65)
TAIL_GUIDE_SWEEP_PAD=.06

def sliding_tail(side,gate_stroke=0.):
 if not 0<=gate_stroke<=OPEN_GATE_STROKE:raise ValueError(gate_stroke)
 return mirrored(blk(*TAIL),side).translate((0,gate_stroke,0))

def gate(side,stroke=0.):
 body=original_gate(side,stroke).fuse(sliding_tail(side,stroke)).clean()
 return body

def carrier(side,extension=0.):
 return original_carrier(side,extension)

def extension_at(stroke):return theoretical_extension(stroke)

def web_budget():
 return {'R29_original_hypothetical_front_wall_mm':nominal_planar_webs()['front_Y_wall_after_0p025mm_cut_mm'],
   'R29_original_pin_slot_radial_backlash_mm':nominal_planar_webs()['pin_slot_radial_clearance_mm'],
   'new_tail_length_mm':TAIL[3]-TAIL[2],
   'tail_width_x_mm':TAIL[1]-TAIL[0],
   'rear_guide_kinematic_channel_added':True,
   'thin_front_edge_not_structurally_fixed':True,
   'no_actual_bearing_fastener_spring_or_FE_A':True}

if __name__=='__main__':
 from r25_capture import intersection
 print(web_budget())
 for s in 'LR':
  for t in (0.,.45,.9):
   g=gate(s,t);c=carrier(s,extension_at(t))
   print(s,t,g.isValid(),len(g.Solids()),c.isValid(),len(c.Solids()),round(intersection(g,c),9),flush=True)
