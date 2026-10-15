"""R33 INTERIM mechanical retention study, all dimensions in mm.

This is a hypothetical bored single-pin keeper and non-electrical gauge,
not a selected fastener, approved retaining clip, connector or fail-safe lock.
TE 2199001-1 is modeled ONLY as a nominal manufacturer catalogue bounding BOX.
The supplier native STEP was not retrieved; no OEM shape is represented here.
"""
from __future__ import annotations
import cadquery as cq
from r25_capture import blk
from r30_mechanics import mirrored
from r32_cartridge import CASSETTE, CHANNEL

PIN_Y=2.10
PIN_Z=2.65
PIN_R=.085
BORE_R=.14
PIN_X_BEGIN=34.50
PIN_X_END=35.40
HEAD_R=.14
HEAD_BEGIN=35.35
HEAD_END=35.47

def bore(side):
    return mirrored(cq.Solid.makeCylinder(BORE_R,1.10,cq.Vector(34.45,PIN_Y,PIN_Z),cq.Vector(1,0,0)),side)

def keeper_pin(side):
    sh=cq.Solid.makeCylinder(PIN_R,PIN_X_END-PIN_X_BEGIN,cq.Vector(PIN_X_BEGIN,PIN_Y,PIN_Z),cq.Vector(1,0,0))
    head=cq.Solid.makeCylinder(HEAD_R,HEAD_END-HEAD_BEGIN,cq.Vector(HEAD_BEGIN,PIN_Y,PIN_Z),cq.Vector(1,0,0))
    return mirrored(sh.fuse(head).clean(),side)

def bored_gauge(side,y_offset=0):
    box=mirrored(blk(*CASSETTE),side)
    return box.cut(bore(side)).clean().translate((0,y_offset,0))

def catalogue_TE_box(side,permutation=(1.05,2.4,1.2)):
    """Catalogue AABB ONLY: x width, y length, z uncompressed height."""
    x,y,z=permutation
    xc=(CASSETTE[0]+CASSETTE[1])/2
    yc=(CASSETTE[2]+CASSETTE[3])/2
    zc=(CASSETTE[4]+CASSETTE[5])/2
    return mirrored(blk(xc-x/2,xc+x/2,yc-y/2,yc+y/2,zc-z/2,zc+z/2),side)

TE_SOURCE='https://www.te.com/en/product-2199001-1.html'
TE_CATALOGUE_MM=dict(width=1.05,length=2.4,uncompressed_height=1.2,
                     application='Signal',max_current_A=1.5,
                     permitted_working_height_low=.70,permitted_working_height_high=1.0)

def constraints():
    return dict(pin_hole_diameter_mm=2*BORE_R,pin_shaft_diameter_mm=2*PIN_R,
                pin_nominal_radial_play_mm=BORE_R-PIN_R,
                remaining_gauge_top_web_mm=CASSETTE[5]-(PIN_Z+BORE_R),
                remaining_gauge_bottom_web_mm=(PIN_Z-BORE_R)-CASSETTE[4],
                pin_head_axial_capture_missing=True,
                keeper_is_not_electrically_energized=True,
                pin_head_is_not_a_qualified_fastener=True)
