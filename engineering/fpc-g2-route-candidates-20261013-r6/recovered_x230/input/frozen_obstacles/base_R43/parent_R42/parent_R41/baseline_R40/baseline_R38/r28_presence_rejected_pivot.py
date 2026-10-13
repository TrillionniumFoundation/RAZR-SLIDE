"""R28 separate research A-key actuated physical *presence interposer*.

A spring-biased (SPRING NOT INSTALLED) pivoted feeler projects into the B pawl
path when A is absent. Existing A side nose may depress the upper lever near
full seating and release that path. Both parts are OCC solid constraints, NOT
qualification of spring return, shear, latch timing or dual-side decoupling.
"""
from __future__ import annotations
import cadquery as cq
from r25_capture import blk,intersection,to_global,P
from r24_mechanics import yz_prism,a_key
from r26_open_mechanics import open_pawl

PIVOT_Y=-4.50
PIVOT_Z=1.30
RELEASE_DEG=30.

def mirror(s,side):return s if side=='R' else s.mirror('YZ')

def lever(side:str,angle_deg=0.):
    if not (0<=angle_deg<=RELEASE_DEG):raise ValueError(angle_deg)
    # A single oblique rib between upper key feeler and lower veto finger.
    rib=yz_prism(34.46,34.56,[(-5.01,1.98),(-4.89,2.17),(-4.22,.73),(-4.34,.47)])
    upper=blk(34.50,34.65,-5.01,-4.89,2.00,2.17)
    lower=blk(34.41,34.53,-4.49,-4.22,.45,.69)
    # Pivot eye reference is part of rotating lever, not a modelled bearing.
    boss=cq.Solid.makeCylinder(.13,.10,cq.Vector(34.46,PIVOT_Y,PIVOT_Z),cq.Vector(1,0,0))
    body=rib.fuse(upper).fuse(lower).fuse(boss).clean()
    body=body.rotate((34.46,PIVOT_Y,PIVOT_Z),(35.46,PIVOT_Y,PIVOT_Z),angle_deg)
    return mirror(body,side)

def pawl_path(side,travel):
    if not 0<=travel<=.55:raise ValueError(travel)
    # R26 OPEN parked pawn travels 0.55mm outboard to captured shoulder.
    s=open_pawl(side,False)
    return s.translate(((travel if side=='R' else -travel),0,0))

def first_probe():
    for side in 'LR':
        for theta in (0.,10.,20.,30.):
            sh=lever(side,theta)
            key=a_key('OPEN',side)
            row=dict(side=side,theta=theta,valid=sh.isValid(),solids=len(sh.Solids()),
                seat_A_key_clash=round(intersection(key,to_global(sh,'OPEN',P.travel,P.z_travel)),9),
                near_A_key_clash_at_q8p0=round(intersection(key,to_global(sh,'OPEN',P.travel,8.0)),9),
                absent_key_pawl_path_clashes=[round(intersection(sh,pawl_path(side,x)),8) for x in (0.,.15,.3,.45,.55)])
            print(row,flush=True)
if __name__=='__main__':first_probe()
