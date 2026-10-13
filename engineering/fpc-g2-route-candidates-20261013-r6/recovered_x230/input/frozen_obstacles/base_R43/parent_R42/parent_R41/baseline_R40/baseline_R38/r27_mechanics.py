"""R27 exploratory positive-geometry *continuous* OPEN contact-carrier shutter.

This repairs a specific R26 endpoint escape: an OPEN gate already CLOSED had
zero OCC overlap with the carrier preextended by 0.8 mm.  R27 adds a connected
high-Z interception blade.  This does NOT retract a trapped carrier, make
mechanical capture fail-safe, validate shroud force, qualify spring return or
prevent both gates being broken. All dimensions hypothetical in mm.
"""
from __future__ import annotations
from r25_capture import blk,intersection
from r26_open_mechanics import open_gate,open_carrier_ear,open_pawl,OPEN_GATE_STROKE

BLADE_BOTTOM_Z=-3.17
BLADE_TOP_Z=-2.30
SPINE_MIN_WEB_X_MM=.08  # local prototype, not a strength-approved web
SPINE_MIN_WEB_Y_MM=.05

def open_gate_captive(side:str,stroke:float=0.):
    if side not in ('L','R') or not 0.<=stroke<=OPEN_GATE_STROKE:
        raise ValueError((side,stroke))
    def xmir(lo,hi):return (lo,hi) if side=='R' else (-hi,-lo)
    # A continuous independent OCC solid: new vertical spine attaches to
    # existing R26 top rail; lateral blade catches the raised carrier even
    # when the carrier had ALREADY risen before the gate tried to close.
    # All geometry in *OPEN-port B fixture-local coordinates*.
    spine=blk(*xmir(34.14,34.22),-4.67,-4.62,BLADE_BOTTOM_Z,.77)
    blade=blk(*xmir(34.14,34.31),-4.67,-4.36,BLADE_BOTTOM_Z,BLADE_TOP_Z)
    result=open_gate(side,0.).fuse(spine).fuse(blade).clean().translate((0,stroke,0))
    return result

def open_contact_carrier(side:str,extension:float):
    return open_carrier_ear(side,extension)

def nominal_witness(side:str, extension:float, stroke:float):
    return intersection(open_gate_captive(side,stroke),open_contact_carrier(side,extension))

def swept_first_contact(side:str, step:float=.002):
    """Discrete scan, not a continuous analytic proof; report sampling step."""
    n=round(.8/step)
    for i in range(n+1):
        x=.8*i/n
        if nominal_witness(side,x,0.)>1e-9:
            return round(x,6)
    return None

if __name__=='__main__':
    for side in 'LR':
        print(side,'first witness',swept_first_contact(side),
            'full 0.8 closed',nominal_witness(side,.8,0),
            'full 0.8 opened',nominal_witness(side,.8,.9))
