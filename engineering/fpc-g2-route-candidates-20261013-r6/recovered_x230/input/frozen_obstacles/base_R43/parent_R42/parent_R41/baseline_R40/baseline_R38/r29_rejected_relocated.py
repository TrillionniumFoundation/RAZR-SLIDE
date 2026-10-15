"""R29 inboard relocated wide-guide *research* revision. mm.

This model is not a contact force proof. Increasing geometric pin/slot clearance
trades jamming for backlash; following the cam centreline is a prescribed
kinematic path and not a kinematic constraint under real load.
"""
from __future__ import annotations
import cadquery as cq
from shapely.geometry import LineString
from r25_capture import blk, intersection
from r26_open_mechanics import open_carrier_ear, OPEN_GATE_STROKE
from r27_mechanics import open_gate_captive
from r24_mechanics import yz_prism

CARRIER_TRAVEL=0.8
PIN_Y=-3.60
PIN_Z_CLOSED=-4.16
PIN_RADIUS=0.05
SLOT_HALF_WIDTH=0.145
PIN_X_INNER=34.25
PIN_X_OUTER=34.485
PLATE_X=(34.335,34.445)
PLATE_Y=(-4.76,-3.10)
PLATE_Z=(-4.50,-3.03)
CAM_DWELL_MM=0.36
SLOT_END_OPEN=(PIN_Y-OPEN_GATE_STROKE,PIN_Z_CLOSED+CARRIER_TRAVEL)
SLOT_END_CLOSED=(PIN_Y,PIN_Z_CLOSED)

def mirrored(shape, side):
    if side not in 'LR':raise ValueError(side)
    return shape if side=='R' else shape.mirror('YZ')

def guide_slot_cut(side):
    contour=LineString([SLOT_END_OPEN,(PIN_Y-CAM_DWELL_MM,PIN_Z_CLOSED),SLOT_END_CLOSED]).buffer(SLOT_HALF_WIDTH,resolution=10)
    return mirrored(yz_prism(PLATE_X[0]-.015, PLATE_X[1]+.015,list(contour.exterior.coords)),side)

def pullback_gate(side,stroke=0.):
    if not 0<=stroke<=OPEN_GATE_STROKE:raise ValueError(stroke)
    plate=mirrored(blk(*PLATE_X,*PLATE_Y,*PLATE_Z),side).cut(guide_slot_cut(side)).clean()
    sh=open_gate_captive(side,0.)
    # A bridge to the inherited shutter instead of relying on a nearly tangent coincidence.
    bridge=mirrored(blk(34.29,34.41,-4.16,-4.075,-4.02,-3.87),side)
    return sh.fuse(plate).fuse(bridge).clean().translate((0,stroke,0))

def carrier_with_pin(side,extension=0.):
    if not 0<=extension<=CARRIER_TRAVEL:raise ValueError(extension)
    pin=cq.Solid.makeCylinder(PIN_RADIUS,PIN_X_OUTER-PIN_X_INNER,
        cq.Vector(PIN_X_INNER,PIN_Y,PIN_Z_CLOSED+extension),cq.Vector(1,0,0))
    web=mirrored(blk(34.23,34.27,-4.02,-3.58,-4.24+extension,-4.16+extension),side)
    return open_carrier_ear(side,extension).fuse(web).fuse(mirrored(pin,side)).clean()

def theoretical_extension(gate_stroke):
    if not 0<=gate_stroke<=OPEN_GATE_STROKE:raise ValueError(gate_stroke)
    return CARRIER_TRAVEL*max(0.,(gate_stroke-CAM_DWELL_MM)/(OPEN_GATE_STROKE-CAM_DWELL_MM))

def nominal_planar_webs():
    return dict(plate_X_mm=PLATE_X[1]-PLATE_X[0],
        slot_end_Z_web_bottom_mm=PIN_Z_CLOSED-SLOT_HALF_WIDTH-PLATE_Z[0],
        slot_end_Z_web_top_mm=PLATE_Z[1]-(PIN_Z_CLOSED+CARRIER_TRAVEL+SLOT_HALF_WIDTH),
        front_Y_wall_after_0p025mm_cut_mm=PLATE_Y[0]+5-.025,
        pin_slot_radial_clearance_mm=SLOT_HALF_WIDTH-PIN_RADIUS)

if __name__=='__main__':
 for s in 'LR':
  for t in (0.,.45,.9):
   gate=pullback_gate(s,t); ear=carrier_with_pin(s,theoretical_extension(t))
   print(s,t,gate.isValid(),len(gate.Solids()),ear.isValid(),len(ear.Solids()),intersection(gate,ear),flush=True)
 print(nominal_planar_webs())
