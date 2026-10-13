#!/usr/bin/env python3
"""Conditional XY 180deg U longitudinal stow envelope algebra, NOT a supplier minimum."""
import math,json
from pathlib import Path
R=16.5;w=1.2;A_Y=70.; B_Y=15.; YCAP=94.25
cymax=YCAP-R-w/2
Lmax=math.pi*R+2*cymax-A_Y-B_Y
minleg_model=10.
ycap_need=A_Y+minleg_model+R+w/2
r={'revision':'R44 conditional single XY semicircle stow Y budget',
    'applies_only_to_one_180deg_XY_U_with_A_Y_70_B_Y_15':True,
    'research_radius_mm':R,'research_ribbon_width_mm':w,'original_stow_Y_budget_mm':YCAP,
    'semicircle_length_mm':math.pi*R,'max_center_Y_to_keep_outer_ribbon_within_stow_mm':cymax,
    'max_A_straight_leg_mm':cymax-A_Y,'max_total_constant_length_mm':Lmax,
    'chosen_route_length_mm':120.,
    'conditional_10mm_A_straight_leg_not_a_vendor_spec':True,
    'hypothetical_10mm_A_leg_required_Ycap_mm':ycap_need,
    'hypothetical_10mm_A_leg_Y_excess_mm':max(0.,ycap_need-YCAP),
    'no_global_topology_impossibility_claim':True,
    'candidate_go':False,'manufacturing_go':False}
(ROOT:=Path(__file__).resolve().parent/'evidence').mkdir(exist_ok=True)
(ROOT/'R44_analytic_bounds.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
