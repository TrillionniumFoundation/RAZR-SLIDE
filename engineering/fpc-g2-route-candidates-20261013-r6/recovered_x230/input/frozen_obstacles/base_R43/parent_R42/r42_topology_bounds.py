"""R42 geometric impossibility *for a narrowly specified alternative*:
A single downward (-Y) 180deg R16.5 U for C->B that must store in Y>=0 at stow,
with both endpoints at local Y=15 and at maximum stroke separated by 39.875.
Other multiloop/zigzag/multi-axis packaging designs are NOT excluded.
"""
import json,math
from pathlib import Path
from r42_double_loop import solve,anchors,arc_calcs,RADIUS,SLIDE,DOCK,B_Y_LOCAL
ROOT=Path(__file__).resolve().parent

def run(write=True):
    c0,b0=anchors(0,0)[1:]
    c1,b1=anchors(SLIDE,DOCK)[1:]
    arc_stow,_=arc_calcs(RADIUS,float(b0[2]-c0[2]))
    arc_seated,_=arc_calcs(RADIUS,float(b1[2]-c1[2]))
    dy=abs(float(b1[1]-c1[1]))
    # To extend toward -Y, each straight leg must be nonnegative at seat:
    # L>=arc + abs(deltaY). To remain inside chassis Y>=0 at stow:
    # Ymin=Y_C - (L-arc_stow)/2 - R >= 0 => L<=arc_stow+2*(Y_C-R)
    min_total_length=arc_seated+dy
    max_stow_length=arc_stow+2*(float(c0[1])-RADIUS)
    y_min_for_minimum_length=float(c0[1]-(min_total_length-arc_stow)/2-RADIUS)
    d={'revision':'R42 conditional necessary bound for a single negative-Y 180deg C->B return loop',
       'geometry_scope':'unfolded mid-junction C to B, same research anchors, half-rate junction, radius 16.5; Y>=0 at stow',
       'all_other_topologies_not_disproved':True,
       'R_mm':RADIUS,'Ymin_allowed_mm':0.,'anchor_Y_stow_mm':float(c0[1]),
       'endpoint_delta_Y_seated_mm':dy,
       'U_arc_3d_stow_mm':arc_stow,'U_arc_3d_seated_mm':arc_seated,
       'minimum_FPC_length_for_final_separation_mm':min_total_length,
       'maximum_FPC_length_that_fits_stow_Y_min_mm':max_stow_length,
       'Y_lower_bound_at_stow_with_minimum_length_mm':y_min_for_minimum_length,
       'required_outside_Y_at_stow_mm':max(0.,-y_min_for_minimum_length),
       'feasible_single_negative_Y_U_under_conditions':min_total_length<=max_stow_length,
       'manufacturing_go':False}
    if write:
        (ROOT/'verification/R42_reverse_U_bound.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    return d
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
