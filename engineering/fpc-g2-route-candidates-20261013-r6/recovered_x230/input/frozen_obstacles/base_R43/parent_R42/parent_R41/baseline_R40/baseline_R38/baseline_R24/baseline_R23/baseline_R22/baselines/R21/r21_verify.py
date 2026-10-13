"""R21 repeatable calculated proxy verification; NOT actual hardware qualification."""
from pathlib import Path
import json,csv,sys,hashlib,math
from dataclasses import replace
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
import cadquery as cq
from r21_geom import (ROOT,P,STOW_Y,STOW_PAD_Z,OPEN_Y,OPEN_PAD_Z,
  CUT_CLEAR,FLOOR_SCREEN,HEAD_CAVITY_X_HALF,run_dock_integration,
  stow_pocketed_shell,open_contact_cradle,local_assembly,r17_assembly,intersection,
  blk,Params)
from r20_cad import collision_metrics as old_cad_cm
from r17_model import sweep
V=ROOT/'verification';V.mkdir(exist_ok=True)

def nearest(a,b):
 d=BRepExtrema_DistShapeShape(a.wrapped,b.wrapped);d.Perform()
 if not d.IsDone():raise RuntimeError('distance failed')
 return float(d.Value())

def port_movers_at_B(retract:bool,left_open:bool,right_open:bool,which='STOW'):
 """R20 component proxies placed at each of two R21 cabin-local stations.
 Each moving body translates rigidly with B; no actual actuation linkage modeled.
 """
 parts=local_assembly(retract,left_open,right_open)
 if which=='STOW': localy,z=STOW_Y,STOW_PAD_Z+P.z_travel
 elif which=='OPEN':localy,z=5.,OPEN_PAD_Z
 else:raise ValueError(which)
 return {name:shape.translate(cq.Vector(0,localy,z)) for name,shape in parts.items()
         if name.startswith(('B_DOG','B_CARRIER_LUG','B_BOTTOM_CARRIER','B_TE_CONTACT'))}

def baseline_battery_boxes():
 # Do not import actual OEM battery geometry: these boxes are R17 research proxies.
 return dict(B_battery=blk(-33.,23.,22.,58.,1.75,5.85),
             B_PCB=blk(-15.,23.,61.,83.,1.65,3.85),
             B_camera=blk(-33.,-16.,72.,89.,1.50,7.00))

def old_contact_port_battery_hit(old_y=30):
 # reconstruct R21 machining at old R19 Y30, independent of OLED shell.
 import r21_geom as rg
 saved=rg.STOW_Y
 try:
  rg.STOW_Y=old_y
  old=rg.stow_pocketed_shell()
  removed=old['baseline'].cut(old['cut_core'])
  return removed.intersect(baseline_battery_boxes()['B_battery']).Volume()
 finally:rg.STOW_Y=saved

def run(write=True):
 obj=run_dock_integration()
 raw_b=obj['built_b_core']
 ba=baseline_battery_boxes()
 cut_old=old_contact_port_battery_hit(30)
 removed=obj['stow']['baseline'].cut(obj['stow']['cut_core'])
 new_battery_cut=intersection(removed,ba['B_battery'])
 pose_cad=[]
 for pos in obj['poses']:
  s,q,leaf=pos['s'],pos['q'],pos['leaf']
  a=r17_assembly(P,s,q,leaf)
  b=raw_b.translate(cq.Vector(0,s,-P.z_travel+q))
  dist=nearest(b,a['OLED'])
  # OLED and moving components must be compared throughout in selected poses.
  interactions=[]
  for dock in ('STOW','OPEN'):
   for retract in (True,False):
    for go in (False,True):
     parts=port_movers_at_B(retract,go,go,dock)
     for name,local in parts.items():
      part=local.translate(cq.Vector(0,s,-P.z_travel+q))
      bad=intersection(part,b)
      if bad>1e-6:interactions.append((dock,retract,go,name,round(bad,6)))
  pose_cad.append(dict(stage=pos['state'],slide_mm=s,dock_mm=q,
      b_model_one_connected_solid=len(raw_b.Solids())==1,
      b_vs_active_oled_min_mm=round(dist,6),
      cad_intersections=pos['intersections'],carriage_vs_B_illegal_intersections=interactions))
  assert not interactions,(pos['state'],interactions[:4])
  assert all(v<1e-6 for v in pos['intersections'].values())
 # Vary effective OLED strip width; actual OEM module is wider than active display.
 sensitivity=[]
 for extra in (0,.05,.10,.15,.20,.30):
  pp=replace(P,oled_w=P.oled_w+2*extra)
  r=r17_assembly(pp,0,0,0)
  b=raw_b.translate(cq.Vector(0,0,-P.z_travel))
  d=nearest(b,r['OLED'])
  sensitivity.append(dict(assumed_encapsulation_extension_each_edge_mm=extra,
    min_clearance_mm=round(d,6),study_target_mm=.30,passes_screening=d>=.30))
 # Explicitly test false both-gates-open flow in original R20: collision geometry lets it move.
 r20_false_open=old_cad_cm(local_assembly(False,True,True))
 boolean_r20_already_unsafe=(r20_false_open['L_block_mm3']+r20_false_open['R_block_mm3'])<1e-6
 floor=obj['island']['bottom_floor_nominal_mm']
 ref=list(obj['stow']['original_rib_overlap_mm3'])
 out=dict(revision='R21 geometry-only; no new OEM parts or validation claims',
   common_design=dict(A_static=True,B_moves_up_then_front=True,
     each_cabin_H_mm=P.H,each_cabin_W_mm=P.W,Y_travel_mm=P.travel,Z_dock_mm=P.z_travel,
     oled_only_main=True,no_rear_external_screen=True,battery_total_4700mAh_NOT_VALIDATED=True),
   altered_compared_to_R20=dict(stow_contact_position_old_y_mm=30.,new_local_y_mm=STOW_Y,
     machined_B_stow_actuator_clearance_assumption_mm=CUT_CLEAR,
     abandoned_old_guides_original_intended_core_attachment_overlap_mm3=round(sum(ref),6),
     original_R20_guides_hit_oled_at_upper_endpoint_mm3=4.992,
     battery_proxy_old_recess_intersection_mm3=round(cut_old,6),
     battery_proxy_new_recess_intersection_mm3=round(new_battery_cut,6),
     screen_rear_and_top_bay_new_halfwidth_mm=HEAD_CAVITY_X_HALF,
     side_rail_ear_remaining_nominal_mm=round(P.W/2-HEAD_CAVITY_X_HALF,6),
     stow_machine_cut_away_mm3=round(obj['stow']['cut_volume_mm3'],6),
     open_carriage_guide_volume_added_mm3=round(obj['cradle']['added_bracket_volume_mm3'],6),
     B_one_connected_proxy_solid=len(raw_b.Solids())==1,
     open_island_min_floor_stated_0_7mm_before_tolerance=floor,
     open_island_floor_after_hypothetical_minus0_15mm=round(floor-.15,6)),
   oled_screening_mm=sensitivity,poses=pose_cad,
   original_R17_analytic_path=sweep(P,ny=1001,nq=401),
   hazards=dict(R20_both_dogs_false_open_yet_carriage_free=boolean_r20_already_unsafe,
      actual_hard_stop_release_mechanism=False,
      real_flex_OLED_nonactive_border_width_known=False,
      OEM_OLED_R3_4_dynamic_permission=False,
      B_battery_box_is_research_proxy=True,
      moving_contact_guide_manufacturing_and_strength_checked=False,
      vendor_TE_STEP_present=False,
      contact_thermal_wear_robust=False,
      cross_cabin_battery_current_path_qualified=False,
      touch_support_lifetime_qualified=False,
      complete_manufacturing_release=False),
   scope='5 representative STEP bodies and named proxy solids, not full tolerance/contact continuous motion analysis')
 if write:
  (V/'R21_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
  with (V/'R21_screen_edge_sensitivity.csv').open('w',newline='') as file:
   writer=csv.DictWriter(file,fieldnames=list(sensitivity[0]));writer.writeheader();writer.writerows(sensitivity)
 return out
if __name__=='__main__':
 x=run()
 print('R21',json.dumps({'poses':len(x['poses']), 'B_continuous':x['altered_compared_to_R20']['B_one_connected_proxy_solid'],
  'old_battery_cut_mm3':x['altered_compared_to_R20']['battery_proxy_old_recess_intersection_mm3'],
  'new_battery_cut_mm3':x['altered_compared_to_R20']['battery_proxy_new_recess_intersection_mm3'],
  'new_screen_sensitivity':x['oled_screening_mm'],'manufacturing':False},ensure_ascii=False,indent=2))
