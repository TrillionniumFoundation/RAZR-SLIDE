"""R41 two-axis full-discrete-path mathematical and transverse U-cassette feasibility.
All dimensions remain research geometry, not supplier-certified FPC/finished housing.
A simple planar transverse U must span its 2R diameter inside a narrow side strip.
This does NOT rule out general helical, multi-fold, layered or rerouted topologies.
"""
from pathlib import Path
import math,csv,json,sys
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'baseline_R40'))
from r40_motion import solve,poses
SIDE_OLED_HALF_WIDTH=33.66
HALF_CHASSIS_WIDTH=36.995
SIDE_STRIP=HALF_CHASSIS_WIDTH-SIDE_OLED_HALF_WIDTH
XZ_ZMIN=-8.2
XZ_ZMAX=7.68
THICKNESS_ENVELOPE=XZ_ZMAX-XZ_ZMIN
R_HYP=15.

def run():
 rows=[]
 variants=[('R40_original',0.,0.),('internal_reposition',-21.,1.),('external_clearance_tradeoff',-21.,3.)]
 for name,dx,dz in variants:
  for scene in poses():
   m=solve(scene['s'],scene['q'],16.5,119.)
   box=m['box']
   p={ 'layout':name,'dx_mm':dx,'dz_mm':dz,'stage':scene['stage'],
       's_mm':scene['s'],'q_mm':scene['q'],
       'solved_length_mm':round(m['verified_math_length_mm'],9),
       'length_error_mm':round(m['verified_math_length_mm']-119.,9),
       'min_centerline_radius_mm':round(m['min_bend_R_mm'],9),
       'leg_A_mm':m['leg_A_mm'],'leg_B_mm':m['leg_B_mm'],
       'transverse_xz_bbox_excess_centerline_mm':round(max(0.,-HALF_CHASSIS_WIDTH-(box['xmin']+dx),
          (box['xmax']+dx)-HALF_CHASSIS_WIDTH,XZ_ZMIN-(box['zmin']+dz),
          (box['zmax']+dz)-XZ_ZMAX),6)}
   rows.append(p)
 limit_d=math.hypot(SIDE_STRIP,THICKNESS_ENVELOPE)
 z_extra=max(0,math.sqrt(max(0,(2*R_HYP)**2-SIDE_STRIP**2))-THICKNESS_ENVELOPE)
 x_extra=max(0,math.sqrt(max(0,(2*R_HYP)**2-THICKNESS_ENVELOPE**2))-SIDE_STRIP)
 budget={
  'limitation':'only a single planar 180-degree U whose diameter must fit within this side-strip XZ cross section; NOT a general impossibility theorem',
  'chassis_half_x_mm':HALF_CHASSIS_WIDTH,'screen_research_half_width_mm':SIDE_OLED_HALF_WIDTH,
  'side_strip_width_mm':SIDE_STRIP,'research_Z_window_mm':[XZ_ZMIN,XZ_ZMAX],
  'research_Z_height_mm':THICKNESS_ENVELOPE,'side_strip_cross_section_diagonal_mm':limit_d,
  'required_U_diameter_mm_at_hypothetical_R15':2*R_HYP,
  'planar_transverse_U_R15_fits':limit_d>=2*R_HYP,
  'minimum_additional_Z_height_with_X_fixed_mm':z_extra,
  'minimum_additional_X_width_with_Z_fixed_mm':x_extra,
  'real_OLED_vendor_and_FPC_stack_missing':True,'physical_sidecassette_not_implemented':True}
 summary={ 'revision':'R41 121-position two-stage length/radius audit plus sidewall transverse U dimensional lower bound',
  'motion_positions_per_layout':len(poses()),'layouts':len(variants),'math_cases':len(rows),
  'max_abs_length_error_mm':max(abs(x['length_error_mm']) for x in rows),
  'min_radius_mm':min(x['min_centerline_radius_mm'] for x in rows),
  'nonnegative_legs':all(x['leg_A_mm']>=0 and x['leg_B_mm']>=0 for x in rows),
  'envelope_excess_by_layout_mm':{v:max(x['transverse_xz_bbox_excess_centerline_mm'] for x in rows if x['layout']==v) for v,_,_ in variants},
  'sidewall_transverse_planar_u_budget':budget,
  'math_only_not_continuous_Occ_sweep':True,
  'manufacturing_go':False}
 (R/'verification').mkdir(exist_ok=True)
 (R/'verification/R41_motion_budget.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 with (R/'verification/R41_motion_363_positions.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps(summary,ensure_ascii=False,indent=2));return summary
if __name__=='__main__':run()
