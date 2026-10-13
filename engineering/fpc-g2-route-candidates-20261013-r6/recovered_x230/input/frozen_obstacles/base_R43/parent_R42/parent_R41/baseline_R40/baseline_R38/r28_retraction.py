"""R28 *research-only* positive-pullback captive cam/slot proxy.

A roller/pin attached to the contact carrier passes through a THROUGH slot in
an integral OPEN-shutter side plate.  With ideal rigid pin and constrained axes,
closing the gate 0.90mm forces the carrier extension from 0.80mm to zero.

All distances mm. OCC solids merely provide geometry, NOT proof of elastic
force, an intact pin, spring defaults, blocked motion under debris, retention,
manufacturing tolerance or electrical break-before-motion.
"""
from __future__ import annotations
import cadquery as cq
from shapely.geometry import LineString
from r25_capture import blk, intersection
from r26_open_mechanics import open_carrier_ear, OPEN_GATE_STROKE
from r27_mechanics import open_gate_captive
from r24_mechanics import yz_prism

CARRIER_TRAVEL=.8
PIN_Y=-3.84
PIN_Z_CLOSED=-4.16
PIN_RADIUS=.050
SLOT_HALF_WIDTH=.082  # axial pin centreline clearance 0.032 mm, no toleranced part yet
PIN_X_INNER=34.29
PIN_X_OUTER=34.55
PLATE_X=(34.425,34.51)
PLATE_Y=(-4.96,-3.47)
PLATE_Z=(-4.30,-3.22)
CAM_DWELL_MM=.36  # close the stage-2 shutter AFTER the pin has been retracted
SLOT_END_OPEN=(PIN_Y-OPEN_GATE_STROKE,PIN_Z_CLOSED+CARRIER_TRAVEL)
SLOT_END_CLOSED=(PIN_Y,PIN_Z_CLOSED)

def mirrored(shape,side):
    if side not in ('L','R'):raise ValueError(side)
    return shape if side=='R' else shape.mirror('YZ')

def guide_slot_cut(side):
    # Rounded-ended swept cylinder envelope through full plate thickness.
    contour=LineString([SLOT_END_OPEN,(PIN_Y-CAM_DWELL_MM,PIN_Z_CLOSED),SLOT_END_CLOSED]).buffer(SLOT_HALF_WIDTH,resolution=14)
    return mirrored(yz_prism(PLATE_X[0]-.015,PLATE_X[1]+.015,list(contour.exterior.coords)),side)

def pullback_gate(side,stroke=0.):
    if not 0.<=stroke<=OPEN_GATE_STROKE:raise ValueError(stroke)
    plate=mirrored(blk(*PLATE_X,*PLATE_Y,*PLATE_Z),side)
    plate=plate.cut(guide_slot_cut(side)).clean()
    # Body-attached bridge, above the retracted carrier. At the nominal mated
    # state this is connected to R27's lower native rail at x ±34.30..34.39.
    bridge=mirrored(blk(34.32,34.51,-4.17,-4.08,-4.012,-3.88),side)
    body=open_gate_captive(side,0.).fuse(plate).fuse(bridge).clean()
    return body.translate((0,stroke,0))

def carrier_with_pin(side,extension=0.):
    if not 0<=extension<=CARRIER_TRAVEL:raise ValueError(extension)
    pin=cq.Solid.makeCylinder(PIN_RADIUS,PIN_X_OUTER-PIN_X_INNER,
       cq.Vector(PIN_X_INNER,PIN_Y,PIN_Z_CLOSED+extension), cq.Vector(1,0,0))
    # A shallow outboard rib ties the pin into the original ear, not a free
    # floating pin. This web lives below R27's lower shutter rail in dwell.
    web=mirrored(blk(34.30,34.34,-4.05,-3.81,-4.24+extension,-4.16+extension),side)
    body=open_carrier_ear(side,extension).fuse(web).fuse(mirrored(pin,side)).clean()
    return body

def theoretical_extension(gate_stroke):
    if not 0<=gate_stroke<=OPEN_GATE_STROKE:raise ValueError(gate_stroke)
    return CARRIER_TRAVEL*max(0.,(gate_stroke-CAM_DWELL_MM)/(OPEN_GATE_STROKE-CAM_DWELL_MM))

def probe():
    for side in 'LR':
        for t in (0.,.09,.225,.45,.675,.81,.9):
            e=theoretical_extension(t)
            gate=pullback_gate(side,t);ear=carrier_with_pin(side,e)
            clash=intersection(gate,ear)
            print('PROBE',side,t,round(e,3),'gate valid',gate.isValid(),len(gate.Solids()),'ear valid',ear.isValid(),len(ear.Solids()),'overlap mm3',round(clash,8),flush=True)
        gate=pullback_gate(side,0.)
        for e in (0.,.15,.4,.8):
            print('VETO',side,e,intersection(gate,carrier_with_pin(side,e)),flush=True)

if __name__=='__main__':probe()
