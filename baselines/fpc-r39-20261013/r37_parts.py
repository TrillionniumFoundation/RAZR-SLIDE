"""R37 research-only B-shell INTEGRAL front stop lip.

Two independent locally fused shell lips intercept R35 bridge motion after 0.05mm.
These lips are NOT an assembly-qualified snap-fit: their rigid geometry ALSO
blocks forward bridge assembly. No flexural modulus/fatigue/creep, force,
friction or validated molding process. No electrical connectivity.
All units mm; based on existing R36 B coordinate conventions.
"""
from r25_capture import blk
from r30_mechanics import mirrored

# Two mirrored front-face hooks, each with a real overlap to the existing
# reinforced B shell, located before the R35 bridge entrance (Y=1.43).
# Their nominal contact margin is 1.430-1.419=0.011mm, NOT a GD&T margin.
LIP=(33.25,33.70,1.29,1.419,2.14,2.94)
CAP_MIN_Y=1.43
INTEGRAL_HOOK_NOMINAL_PRECONTACT_MM=CAP_MIN_Y-LIP[3]

# The source R36 keeper has only 0.240mm thickness along screw X.
R36_KEEPER_THICKNESS=0.24
# PEM TA-10-075 from PennEngineering (catalogue only, no licensed native CAD):
PEM='PennEngineering microPEM TA-10-075 (catalogue proxy only)'
PEM_TOP_MIN=0.71
PEM_TOP_MAX=0.79
PEM_BASE_MIN=.89
PEM_BASE_THROUGH_MIN=.50 # actual vendor footnote; process-specific
PEM_TOP_HOLE_D=1.47
PEM_BASE_HOLE_D=1.02
PEM_EDGE_MIN=1.00
PEM_MATERIAL='Aluminum; base sheet hardness HRB<=45 or HB<=84'

def lip(side):
    if side not in 'LR': raise ValueError(side)
    return mirrored(blk(*LIP),side)

def metadata():
    return dict(revision='R37 integral retaining-lip research, NOT a qualified snap-fit',
        lip_proxy_coords_R_mm=LIP,nominal_cap_contact_clearance_mm=round(INTEGRAL_HOOK_NOMINAL_PRECONTACT_MM,6),
        integral_base_instead_of_M08_screw=True,
        lip_cannot_be_elastically_assembled_as_rigid_solids=True,
        no_material_spring_force_or_creep=True,no_qualified_300k_cycle_life=True,
        PEM_candidate=PEM,PEM_top_hole_mm=PEM_TOP_HOLE_D,
        PEM_base_hole_mm=PEM_BASE_HOLE_D,PEM_top_sheet_allowed_mm=[PEM_TOP_MIN,PEM_TOP_MAX],
        PEM_base_min_mm=PEM_BASE_MIN,PEM_material_limits=PEM_MATERIAL,
        source_keeper_thickness_mm=R36_KEEPER_THICKNESS,
        vendor_TE_contact_CAD_available=False,vendor_PEM_native_CAD_imported=False,
        loss_of_one_lip_exposes_one_side=True,manufacturing_go=False)
