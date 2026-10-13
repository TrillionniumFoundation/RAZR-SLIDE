"""R32 open-port *non-energized* cassette-ENVELOPE study, millimetres.

This does NOT contain a working electrical connector, spring, latch, removable
fastener or proof of a safe contact sequence.  The cassette is a solid gauge.
Unlike the R29 thin leading lip, the proposed fixed B support is positioned
behind the contact station and is fused to an existing R30 rear guide boss.
No loading may be assigned to it without a real A-side load transfer path.
"""
from __future__ import annotations
from r25_capture import blk
from r30_mechanics import mirrored

# B native coords. Positive X is right side; left is mirror about YZ.
FRAME=(34.54,35.34,1.50,4.00,2.00,3.30)
# Mouth opens at Y<0; the rear wall is at Y=3.70..4.00.
CHANNEL=(34.75,35.10,-.05,3.70,2.35,2.95)
# Structural envelope gauge only; there is NO conductive material on this.
CASSETTE=(34.82,35.03,1.48,3.58,2.42,2.88)
# Tests are of the ideal rigid profile and the assumed alignment below.
CASSETTE_Y_INSERT_START=-2.5
SAMPLED_INSERT_OFFSETS=(-2.50,-1.75,-1.00,-.50,0.)


def frame(side):return mirrored(blk(*FRAME),side)
def channel(side):return mirrored(blk(*CHANNEL),side)
def gauge(side,insert_offset=0.):
    return mirrored(blk(*CASSETTE),side).translate((0,insert_offset,0))

def nominal_frame_wall_budget():
    return {
        'local_x_inboard_mm':round(CHANNEL[0]-FRAME[0],6),
        'local_x_outboard_mm':round(FRAME[1]-CHANNEL[1],6),
        'local_z_bottom_mm':round(CHANNEL[4]-FRAME[4],6),
        'local_z_roof_mm':round(FRAME[5]-CHANNEL[5],6),
        'local_y_rear_stop_mm':round(FRAME[3]-CHANNEL[3],6),
        'cassette_x_nominal_gap_each_side_mm':round(CASSETTE[0]-CHANNEL[0],6),
        'cassette_z_nominal_gap_each_side_mm':round(CASSETTE[4]-CHANNEL[4],6),
        'cassette_y_end_stop_gap_mm':round(CHANNEL[3]-CASSETTE[3],6),
        'frame_is_open_at_y_front':True,
        'these_are_design_differences_not_actual_minimum_remaining_machined_wall':True,
    }
