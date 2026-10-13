"""R26 OPEN-port side-inboard PARK + lowered-path secondary shutter OCC prototype.

Exploratory rigid geometry, NOT production-ready. Existing R25 OPEN parked pawl
actually intersects complete A shell at seated configuration; this intentionally
moves it inward instead of outboard. OPEN contact-motion veto is *swept-path*,
not an endpoint collision. No forces, torsion, spring, fasteners, OLED lamination
or exposure shielding have been qualified.
"""
from __future__ import annotations
import cadquery as cq
from r25_capture import ROOT,P,blk,intersection,to_global,pawl as old_pawl,a_key
from r24_mechanics import outboard_lugs,outboard_jaws,INBOARD_OLED_X_HALF

OPEN_INWARD_PARK_MM=.55
OPEN_GATE_STROKE=.90
OPEN_LUG_CENTERS={'L':-34.26,'R':34.26}

def open_pawl(side,engaged):
    orig=old_pawl('OPEN',side,True)
    if engaged:return orig
    # Unlike R25 outward parked position, inside A/B external shell at full dock.
    sign=1 if side=='L' else -1
    return orig.translate((sign*OPEN_INWARD_PARK_MM,0.,0.))

def open_carrier_ear(side,extension):
    if not 0 <= extension <= .8:raise ValueError(extension)
    l=OPEN_LUG_CENTERS[side]
    base=outboard_lugs(extension)[f'B_R24_OUTBOARD_LUG_{side}']
    components=[
       blk(l-.07,l+.07,-4.65,-4.30,-4.38+extension,-3.35+extension),
       blk(l-.07,l+.07,-4.40,-4.02,-4.31+extension,-4.14+extension),
       blk(l-.13,l+.13,-4.19,-3.91,-4.42+extension,-4.105+extension),
    ]
    shape=base
    for comp in components:shape=shape.fuse(comp)
    return shape.clean()

def open_gate(side,stroke=0.):
    if not 0 <= stroke <= OPEN_GATE_STROKE:raise ValueError(stroke)
    sign=1 if side=='R' else -1
    l=OPEN_LUG_CENTERS[side]
    def mir(x0,x1):
        return (x0,x1) if side=='R' else (-x1,-x0)
    # Separate Z plane from original R24 jaw sweep; inboard spine outside jaw X.
    components=[
      blk(*mir(34.13,34.39),-4.20,-3.88,-4.01,-3.85),
      blk(*mir(33.82,34.39),-4.18,-4.05,-4.03,-3.87),
      blk(*mir(33.79,33.91),-4.16,-4.05,-4.03,.84),
      blk(*mir(33.80,34.32),-4.16,-4.05,.74,.84),
      blk(*mir(34.12,34.24),-4.68,-4.05,.72,.79),
      blk(*mir(34.04,34.36),-4.68,-4.62,.42,.75),
    ]
    sh=components[0]
    for part in components[1:]:sh=sh.fuse(part)
    return sh.clean().translate((0,stroke,0))

def quick_probe():
    from pathlib import Path
    A=cq.importers.importBrep(str(ROOT/'cad'/'R25_A_R24_KEYS.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad'/'R25_B_REWORKED.brep')).val()
    from r22_mechanics import to_blocal
    for side in 'LR':
      print('SIDE',side,flush=True)
      for label,shape in [('ear_retract',open_carrier_ear(side,0.)),('ear_ext',open_carrier_ear(side,.8)),('gate_closed',open_gate(side,0.)),('gate_open',open_gate(side,.9)),('pawl_parked',open_pawl(side,False))]:
        bb=to_blocal(shape,'OPEN').BoundingBox()
        print(label,'valid',shape.isValid(),'solids',len(shape.Solids()),'bounds',tuple(round(x,3) for x in [bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax]),'A',round(intersection(A,to_global(shape,'OPEN',P.travel,P.z_travel)),6),'B',round(intersection(B,to_blocal(shape,'OPEN')),6),flush=True)
      for ext in [0,.03,.06,.1,.15,.2,.3,.4,.5,.6,.7,.8]:
        print('ear ext',ext,'closed',round(intersection(open_carrier_ear(side,ext),open_gate(side,0)),8),'open',round(intersection(open_carrier_ear(side,ext),open_gate(side,.9)),8))
      for captured in (False,True):
       print('PARKED' if not captured else 'CAPTURED',[(t,round(intersection(open_pawl(side,captured),open_gate(side,t)),8)) for t in [0,.02,.04,.06,.1,.2,.3,.5,.9]])
      for jawshift in [0,.4,1.,2.]:
       jaw=outboard_jaws(dict(L=jawshift,R=jawshift))[f'B_R24_OUTBOARD_JAW_{side}']
       print('jawshift',jawshift,'gate',[(t,round(intersection(jaw,open_gate(side,t)),8)) for t in [0,.3,.9]])
if __name__=='__main__':quick_probe()
