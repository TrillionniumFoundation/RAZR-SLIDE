"""R35 research ONLY: robust inboard rail, front retaining bridge and removable cross-pin.
All 3D solids are parametric surrogate parts, NOT approved hardware. Geometry mm.
TE envelope remains manufacturer CATALOGUE AABB, not a real native STEP.
"""
import cadquery as cq
from r25_capture import blk
from r30_mechanics import mirrored
from r34_parts import te_signal_envelope

# Inboard (+/-X) frame rail, built onto B, avoids fragile 0.25mm outer lip.
INBOARD_RAIL=(32.80,34.08,1.35,5.45,1.80,3.42)
ARM_GUIDE=(33.47,34.23,-0.35,5.27,2.04,3.04)
# Removable bridge is inserted AFTER unpowered signal-size gauge, from front Y.
CROSS_BRIDGE=(34.16,35.29,1.49,1.64,2.06,3.20)
BRIDGE_ARM=(33.55,34.12,1.43,5.14,2.14,2.94)
BRIDGE_NECK=(34.08,34.20,1.44,1.62,2.37,2.70)
PIN_Y=4.92
PIN_Z=2.535
PIN_BORE_RADIUS=0.20
PIN_SHAFT_RADIUS=0.11
PIN_X0=32.62
PIN_X1=34.70
# Head at x<32.8, no qualified counter-retention on positive end.
HEAD_X0=32.48
HEAD_X1=32.62
HEAD_RADIUS=0.30

def inboard_rail(side):return mirrored(blk(*INBOARD_RAIL),side)
def arm_guide(side):return mirrored(blk(*ARM_GUIDE),side)
def cap_bridge(side):
    sh=blk(*CROSS_BRIDGE).fuse(blk(*BRIDGE_ARM)).fuse(blk(*BRIDGE_NECK)).clean()
    return mirrored(sh,side)
def fastener_bore(side):
    return mirrored(cq.Solid.makeCylinder(PIN_BORE_RADIUS,PIN_X1-PIN_X0+0.2,
                           cq.Vector(PIN_X0-0.1,PIN_Y,PIN_Z),cq.Vector(1,0,0)),side)
def bored_cap(side):return cap_bridge(side).cut(fastener_bore(side)).clean()
def pin(side):
    stem=cq.Solid.makeCylinder(PIN_SHAFT_RADIUS,PIN_X1-PIN_X0,
         cq.Vector(PIN_X0,PIN_Y,PIN_Z),cq.Vector(1,0,0))
    head=cq.Solid.makeCylinder(HEAD_RADIUS,HEAD_X1-HEAD_X0,
         cq.Vector(HEAD_X0,PIN_Y,PIN_Z),cq.Vector(1,0,0))
    return mirrored(stem.fuse(head).clean(),side)

def part_metadata():
    return dict(rail_mm=INBOARD_RAIL,guide_mm=ARM_GUIDE,bridge_mm=CROSS_BRIDGE,arm_mm=BRIDGE_ARM,neck_mm=BRIDGE_NECK,
                pin_bore_diameter_mm=2*PIN_BORE_RADIUS,pin_stem_diameter_mm=2*PIN_SHAFT_RADIUS,
                pin_head_diameter_mm=2*HEAD_RADIUS,
                axial_circlip_or_thread_or_ferrule_missing=True,
                cap_not_electrical_connector=True,
                still_only_TE_catalogue_AABB_not_vendor_STEP=True,
                B_inboard_volume_competes_with_real_electronics=True,
                spring_breakaway_force_and_material_unqualified=True)
