"""R34 isolated, unpowered CATALOGUE-ENVELOPE signal bay study (mm).

All solids called TE_* are *plain bounding-box test gauges*, never TE native STEP,
working spring geometry, weldable pads, contact sequence or qualified retention.
A 1.05 x 2.4 x 1.2 mm body cannot be squeezed into R32's 0.35 x 0.60 channel.
Instead a symmetric side bay is moved inboard and rearward in native B coords.
"""
from __future__ import annotations
from r25_capture import blk
from r30_mechanics import mirrored
from r33_parts import catalogue_TE_box, TE_CATALOGUE_MM

# B-local reference (right side). Note: front mouth/top is OPEN; no real lid.
FRAME=(33.85,35.60,1.60,4.65,1.65,4.05)
POCKET=(34.10,35.35,1.58,4.32,1.95,4.12)
# Front-fed throat, cut through original R32 stub. This supersedes top loading.
THROAT=(34.10,35.35,-.30,1.58,1.95,3.35)
Y_SHIFT=.37
X_SHIFT_INWARD=.20
# Exact TE nominal box as provided by R33, mirror-aware translation.

def rail_frame(side):
    return mirrored(blk(*FRAME),side)

def top_front_open_pocket(side):
    return mirrored(blk(*POCKET),side)

def front_insert_throat(side):
    return mirrored(blk(*THROAT),side)

def te_signal_envelope(side,extra_z=0.):
    dx=X_SHIFT_INWARD if side=='L' else -X_SHIFT_INWARD
    return catalogue_TE_box(side).translate((dx,Y_SHIFT,extra_z))

def frame_dimensions():
    f,p=FRAME,POCKET
    budget={
        'nominal_left_x_wall_mm':round(p[0]-f[0],6),
        'nominal_right_x_wall_mm':round(f[1]-p[1],6),
        'nominal_rear_y_wall_mm':round(f[3]-p[3],6),
        'nominal_bottom_z_wall_mm':round(p[4]-f[4],6),
        'top_open':p[5]>f[5],
        'front_open':p[2]<f[2],
        'machined_front_feed_throat_present':True,
        'nominal_front_wall_mm':0.,
        'nominal_roof_wall_mm':0.,
        'not_finished_wall_thickness_or_structural_fea':True,
    }
    # Nominal clearance of actual catalogue AABB under this orientation, NOT real CAD.
    te=te_signal_envelope('R').BoundingBox()
    budget.update(
        nominal_TE_1p05_2p4_1p2_catalogue_box=True,
        open_pocket_bbox_mm=list(p),
        TE_bbox_R_mm=[round(x,6) for x in (te.xmin,te.xmax,te.ymin,te.ymax,te.zmin,te.zmax)],
        TE_to_pocket_clearances_mm=[round(te.xmin-p[0],6),round(p[1]-te.xmax,6),
                                     round(te.ymin-p[2],6),round(p[3]-te.ymax,6),
                                     round(te.zmin-p[4],6)],
        TE_native_STEP_not_available=True,
    )
    return budget
