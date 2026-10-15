"""R31 OPEN-terminal two-sided A-key-occupied interposer, research-only OCC.

Both A-side shelves are continuous solids with the inherited A shell.  A shelf's
UNDERSIDE rises relative to the mating B plunger only during final 0.40 mm of
normal docking: an axis-constrained, spring-return B plunger is ASSUMED to move
DOWN to avoid intersecting that real shelf. With A absent, default-position
blocker lies in the B-side lateral capture pawl's sweep. This is an independent
face-contact-derived ideal prismatic kinematic model, NOT a finished spring,
axial guide, load-rated latch or manufacturing-certified fail-close design.

Every contact or release conclusion is explicitly limited to defined geometry.
An inverted/noisy/sideways insertion, broken shelf, fouled slide, or missing
spring is NOT made safe by the software calculating a nominal displacement.
"""
from __future__ import annotations
import cadquery as cq
from r25_capture import P,blk,intersection,to_global
from r26_open_mechanics import open_pawl

# mm. B local OPEN fixture has x=nominal, y+5, z+6.25, B world z shift=q-8.2.
SHELF_WORLD=(34.43,34.64,79.81,79.96,6.30,6.42)
HEAD_MAX_Z=.45
OPEN_FIXTURE_Z=6.25
SHELF_UNDERSIDE_WORLD_Z=SHELF_WORLD[4]
MAX_STROKE=.40
PAWL_LATERAL_STROKE=.55

def mirror(s,side):
    if side not in ('L','R'):raise ValueError(side)
    return s if side=='R' else s.mirror('YZ')

def a_occupied_shelf(side):
    # It overlaps old A-key nose (part of the already-fused R30 A shell).
    return mirror(blk(*SHELF_WORLD),side)

def interposer(side,down=0.):
    """Connected ideal B slide: high rest toe blocks pawl; low release clears it.
    No third party, physical return spring, cylinder guide or captive retention
    is implied just because CAD pieces are one connected solid.
    """
    if not 0<=down<=MAX_STROKE:raise ValueError(down)
    tooth=blk(34.41,34.535,-4.51,-4.20,.44,.82)
    stem=blk(34.47,34.505,-4.91,-4.29,.40,.45)
    head=blk(34.43,34.535,-4.92,-4.77,.35,.45)
    return mirror(tooth.fuse(stem).fuse(head).clean(),side).translate((0,0,-down))

def follower_down(q,has_A=True):
    """IDEAL push-contact displacement, not an A-present sensor or guarantee.

    At target q=8.2 the unshifted head upper face lies at 6.70 world Z;
    fixed A-shelf underside lies at 6.30.  At q=7.8 these just touch.
    Lost spring, wrong stroke, interference and 3D contact forces are excluded.
    """
    if q<0 or q>P.z_travel:raise ValueError(q)
    if not has_A:return 0.
    unshifted_head_top_world=HEAD_MAX_Z+OPEN_FIXTURE_Z+(q-P.z_travel)
    return max(0.,min(MAX_STROKE,unshifted_head_top_world-SHELF_UNDERSIDE_WORLD_Z))

def pawl_position(side,lateral):
    if not 0<=lateral<=PAWL_LATERAL_STROKE:raise ValueError(lateral)
    return open_pawl(side,False).translate((lateral if side=='R' else -lateral,0,0))

def pawl_transit_block(side,down,strokes=(.10,.15,.25,.30,.45)):
    x=interposer(side,down)
    return [round(intersection(x,pawl_position(side,t)),10) for t in strokes]

def no_A_false_engagement_blocked(side):
    vals=pawl_transit_block(side,0.)
    return all(x>1e-8 for x in vals)
