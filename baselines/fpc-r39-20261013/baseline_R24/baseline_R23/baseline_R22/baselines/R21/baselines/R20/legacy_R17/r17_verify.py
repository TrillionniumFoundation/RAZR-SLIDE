"""R17 reproducible analytic scan, parameter screen, selected STEP results.
PASS of tests means rejection mechanisms worked; NOT phone qualification.
"""
import json,math,sys
from dataclasses import asdict,replace
from pathlib import Path
from r17_model import Params,draw_screen,draw_internal_fpc,sweep,ROOT
from r17_cad import a_shell,a_fixed_leaf,a_moving_leaf,b_shell_local,blk,assembly,overlap
sys.path.insert(0,str(ROOT/'legacy_R16'))
from r16_cad import A_frame,B_frame_local
from r16_model import G

def batteries_and_oem_proxies(p):
 # These are clearance research PROXIES, not OEM mechanical drawings or vendor cell models.
 a_bat=blk(-31,31,3,68,.5,4.6)
 b_bat=blk(-33,23,22,58,1.75,5.85)
 b_board=blk(-15,23,61,83,1.65,3.85)
 b_camera=blk(-33,-16,72,89,1.50,7.00)
 return {'A_battery_ASSUMED':a_bat,'B_battery_ASSUMED':b_bat,
         'B_PCB_ASSUMED':b_board,'B_camera_ASSUMED':b_camera}

def run():
 p=Params();m=sweep(p);print('analytic sweep',m)
 qparams=[]
 for R in [2.5,2.8,3.0,3.2,3.4,3.5,3.65,3.75,4.0,4.4,4.8,5.2,5.6,6.0]:
  pp=replace(p,R=R)
  physical_U_plane_gap=(2*R<=pp.avail_depth+1e-9)
  try:
   a=draw_screen(pp,0,0,9)
   b=draw_screen(pp,pp.travel,0,9)
   c=draw_screen(pp,pp.travel,pp.z_travel,9)
   can_bridge_stow=True;tail_min=min(a['tail_y_local'],b['tail_y_local'],c['tail_y_local'])
   path_total=a['total_len']; minrun=a['transition_run_min']; available=pp.O-pp.u
  except ValueError:
   can_bridge_stow=False;tail_min=None;path_total=None;minrun=None;available=pp.O-pp.u
  qparams.append(dict(R=R,required_U_sep=2*R,available_sep=pp.avail_depth,
                      U_inside_B_plane=physical_U_plane_gap,stowed_transition_available=available,
                      stowed_transition_min_run=minrun,stowed_transition_geom_possible=can_bridge_stow,
                      bottom_tail_min=tail_min,OLED_length_nominal=path_total,
                      status='GEOMETRIC_RADIUS_CANDIDATE; NOT SUPPLIER QUALIFIED' if (can_bridge_stow and physical_U_plane_gap) else 'REJECT_GEOMETRY'))
 # stage physical volume change using precise OCC solids (proxy cores)
 oldA=A_frame(G());oldB=B_frame_local(G());newA=a_shell(p);newB=b_shell_local(p)
 oldA_vol=oldA.Volume()/1000;oldB_vol=oldB.Volume()/1000
 newA_vol=newA.Volume()/1000;newB_vol=newB.Volume()/1000
 leaf_vol=a_fixed_leaf(p).Volume()/1000
 # independent test of battery and board/camera boxes INSIDE candidate permitted proxy material
 equipment=batteries_and_oem_proxies(p)
 equipment_rec={}
 for nm,solid in equipment.items():
  sh=newA if nm.startswith('A_') else newB
  inside=solid.intersect(sh).Volume()
  equipment_rec[nm]={'volume_cm3':solid.Volume()/1000,'proxy_core_overlap_fraction':inside/solid.Volume()}
  assert inside/solid.Volume()>0.999999,(nm,inside,solid.Volume())
 for k1,x in list(equipment.items()):
  for k2,y in list(equipment.items()):
   if k1>=k2:continue
   if k1.startswith('A_')!=k2.startswith('A_'):continue
   assert overlap(x,y)<1e-8,(k1,k2,overlap(x,y))
 batt_energy_Wh=4.7*3.85
 capv=equipment['A_battery_ASSUMED'].Volume()/1000+equipment['B_battery_ASSUMED'].Volume()/1000
 req_den=batt_energy_Wh/(capv/1000)
 # Real OEM frame data & dynamic flex data are not available
 clearance={'body_width_mm':p.W,'minimum_stowed_Z_envelope_including_OLED_proxy_mm':p.z_travel+p.Z_A+p.oled_t/2,
   'display_active_width_mm':p.oled_w,
   'display_active_height_mm':p.active_h,'screen_active_edge_to_R16_B_inner_rail_mm':34.0-p.oled_w/2,
   'nominal_outer_rail_ear_thickness_mm':p.W/2-35.60,
   'display_route_flat_front_after_seating_mm':draw_screen(p,p.travel,p.z_travel)['front_length'],
   'display_h_minus_active_h_mm':draw_screen(p,p.travel,p.z_travel)['front_length']-p.active_h,
   'FPC_to_screen_U_min_Y_clear_mm':m['min_FPC_to_U_hood_longitudinal_gap_mm'],
   'B_rear_screen_to_FPC_z_separation_mm':1.95-(p.Z_A-2*p.R),
   'B_front_screen_to_FPC_z_separation_mm':p.Z_A-(1.95+2*p.FPC_loop_R),
   'B_module_side_lane_reserved_for_FPC_mm':p.FPC_w,
   'screen_compatibility_with_OEM_and_nonactive_border':False}
 pocket={
   'original_A_core_proxy_cm3':oldA_vol,'R17_A_relieved_core_only_cm3':newA_vol,
   'R17_A_fixed_leaf_cm3':leaf_vol,'R17_A_mobile_leaf_cm3':leaf_vol,
   'original_B_core_proxy_cm3':oldB_vol,'R17_B_relieved_core_proxy_cm3':newB_vol,
   'R17_B_core_cut_cm3':oldB_vol-newB_vol,
   'A_assembled_static_geometry_vol_diff_vs_R16_cm3':oldA_vol-(newA_vol+2*leaf_vol),
   'assumed_battery_A_cm3':equipment['A_battery_ASSUMED'].Volume()/1000,
   'assumed_battery_B_cm3':equipment['B_battery_ASSUMED'].Volume()/1000,
   'battery_total_assumed_proxy_cm3':capv,
   'battery_min_cell_density_Wh_L_if_full_assumed_boxes':req_den,
   'battery_min_cell_density_Wh_L_if_85pct_use':req_den/.85,
   'note':'This is discarded/protected core proxy volume, NOT displacement of actual OEM cells; cell performance unverified.'}
 # Need a physical interlock to disallow early bridge deployment (strong negative control)
 bad=assembly(p,0,0,1.)
 early_bridge_collision=overlap(bad['A_moving_leaf'],bad['OLED'])
 assert early_bridge_collision>1
 cad_path=ROOT/'verification'/'R17_CAD_selected_poses.json'
 cad=json.loads(cad_path.read_text())
 for rec in cad['states']:
  d=rec['intersections_mm3']
  assert all(abs(v)<1e-6 for v in d.values()),(rec['state'],d)
 orig=cad['original_R16_clashes'];assert orig['screen_in_R16_original_A_bridge_mm3']>1
 assert m['oled_max_length_drift_mm']<=1e-8 and m['fpc_max_length_drift_mm']<=1e-8
 assert m['min_OLED_tail_bottom_margin_mm']>=3.2-1e-9
 assert m['min_FPC_to_U_hood_longitudinal_gap_mm']>=1.3
 assert clearance['display_h_minus_active_h_mm']>=2
 # Key explicitly rejected gates. Only nominal geometry of 6 proxy solids qualifies.
 gates={'OLED_R3_4_module_supplier_permission':False,
        'OLED_R5_2_in_one_cabin_package':False,
        'OLED_R3_4_nominal_single_U_package_with_modified_B_proxy':True,
        'OLED_full_Y_then_Z_neutral_length_conservation_analytic':True,
        'OLED_full_Y_then_Z_no_collision_at_8_reimported_CAD_poses':True,
        'B_local_FPC_loop_length_conservation_analytic':True,
        'B_local_FPC_loop_no_collision_at_8_reimported_CAD_poses':True,
        'bridge_early_deployment_must_be_physically_interlocked':False,
        'bridge_FEA_load_and_backfill_support':False,
        'actual_board_and_camera_geometry_integrated':False,
        'cross_cabin_A_B_FPC_YZ_3D_route':False,
        'real_4700mAh_battery_cells_and_safety_space':False,
        'OLED_full_physical_width_and_edge_border':False,
        'tolerance_envelope_verified_for_real_mechanism':False,
        'wear_creep_and_drop_tests':False,
        'PRODUCTION_RELEASE':False}
 out={'revision':'R17 RAZR Ultra dual equal-cabin, B-top U and two-stage Z docking; no manufacturing release',
      'design_params':asdict(p),'screen_and_display_tail_FPC_sweep':m,'radius_scan':qparams,
      'electronics_envelopes_only':equipment_rec,'geometry_constraints':clearance,
      'core_volume_and_energy_tradeoff':pocket,'early_bridge_wrong_sequence_collision_mm3':early_bridge_collision,
      'CAD_eight_pose_reimport':cad['states'],'original_R16_screen_collision':orig,'gates':gates,
      'sources':{
        'motorola_razer60ultra':'https://en-us.support.motorola.com/app/answers/detail/a_id/187134',
        'OPPO_X2021_6p8mm_axis_diameter':'https://www.oppo.com/en/smartphones/oppo-x-2021/',
        'JSID2024_specific_4mm_R_AMOLED':'https://sid.onlinelibrary.wiley.com/doi/10.1002/jsid.1305',
        'IEC_flattening_force':'https://webstore.iec.ch/en/publication/78233',
        'Hirose_2026_FPC_construction':'https://www.hirose.com/en/product/document?clcode=CL0580-1613-4-50&documentid=D49359_en&documenttype=Catalog&lang=en&productname=FH36-29S-0.3SHW%2850%29&series=FH36'}}
 (ROOT/'verification'/'R17_independent_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print('R17 selected checks passed; EARLY BRIDGE CLASH',early_bridge_collision,'B CUT',pocket['R17_B_core_cut_cm3'])
 print('R3.4 valid screen?',[a for a in qparams if a['R']==3.4][0])
 return out
if __name__=='__main__':run()
