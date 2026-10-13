"""R38 research architecture fork (all dimensions in mm).

Hirose BM28B0.6-24DP/2-0.35V(53) is a SPECIFIC published catalogue header.
These rectangular OCC envelopes are NOT the native STEP, mated receptacle,
PCB/FPC footprint/keep-out, power safety rating, or working electrical circuit.
Placed permanently WITHIN each compartment: NO per-slide mating assumed.
"""
from math import pi
from r25_capture import blk

SKU = 'BM28B0.6-24DP/2-0.35V(53)'
CL_NO = 'CL0673-5024-0-53'
SOURCE = 'https://www.hirose.com/en/product/p/CL0673-5024-0-53'
# Hirose published header length/width/height 6.12 / 1.50 / .465;
# 0.60 mm is the SPECIFIED mated height, not a verified total PCB+strain-relief keepout.
HEADER_LENGTH_MM = 6.12
HEADER_WIDTH_MM = 1.50
HEADER_HEIGHT_MM = .465
MATED_HEIGHT_MM = .60
PUBLISHED_MATING_CYCLES = 10
TARGET_SLIDE_CYCLES_ASSUMED = 300_000
B_LOCAL_XYZ=(32.70,15.00,4.50)
A_FIXED_XYZ=(32.70,70.00,5.75)
R_ASSUMED_MM=2.50     # hypothetical flexible-harness bend radius, NOT OEM-approved
SLIDE_TRAVEL_MM=79.75
DOCK_Z_TRAVEL_MM=8.20

# Long side along Y; orientation is a *placement hypothesis*, not supplier mating alignment.
def size_proxy(center, zheight=MATED_HEIGHT_MM):
    x,y,z=center
    return blk(x-HEADER_WIDTH_MM/2,x+HEADER_WIDTH_MM/2,
               y-HEADER_LENGTH_MM/2,y+HEADER_LENGTH_MM/2,z,z+zheight)

def A_proxy():return size_proxy(A_FIXED_XYZ)
def B_proxy():return size_proxy(B_LOCAL_XYZ)

def old_outboard_placement_proxy():
    return size_proxy((34.70,3.60,2.60))

def constant_z_u_loop_budget():
    """NEGATIVE feasibility screen for simplest planar U only.

    A and B header Z-centres move relative to each other by 8.2 mm. A two-rail
    constant-radius U requires the two straight legs to be spaced 2R in Z.
    More complex torsional, multi-arc, out-of-plane routes are NOT rejected here.
    """
    a=A_FIXED_XYZ[2]+MATED_HEIGHT_MM/2
    b_nom=B_LOCAL_XYZ[2]+MATED_HEIGHT_MM/2
    z_stow=b_nom-DOCK_Z_TRAVEL_MM
    z_open=b_nom
    gap_stow=abs(a-z_stow)
    gap_open=abs(a-z_open)
    required=2*R_ASSUMED_MM
    return {
      'radius_mm_assumed_NOT_vendor':R_ASSUMED_MM,
      'constant_radius_two_parallel_leg_sep_mm':required,
      'header_anchor_Z_gap_stow_mm':round(gap_stow,6),
      'header_anchor_Z_gap_open_mm':round(gap_open,6),
      'simple_constant_plane_U_matches_both_Z_endpoints':abs(gap_stow-required)<1e-6 and abs(gap_open-required)<1e-6,
      'simple_constant_plane_U_matches_open_endpoint':abs(gap_open-required)<1e-6,
      'vertical_dock_stroke_mm':DOCK_Z_TRAVEL_MM,
      'travel_mm':SLIDE_TRAVEL_MM,
      'minimum_idealized_yz_centerline_length_mm':round(max(abs(A_FIXED_XYZ[1]-B_LOCAL_XYZ[1]),abs(A_FIXED_XYZ[1]-(B_LOCAL_XYZ[1]+SLIDE_TRAVEL_MM)))+pi*R_ASSUMED_MM,6),
      'real_multiaxis_flex_loop_validated':False,
      'fpc_lifetime_or_strain_relief_qualified':False,
    }
