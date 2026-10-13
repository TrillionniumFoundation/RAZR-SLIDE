#!/usr/bin/env python3
"""121-step swept-ribbon OCC discrete study for the near-rear floating XY-U section.
No connector, rear cassette, tension, twist/fatigue, or OEM authorization. Not a continuous swept-volume proof.
"""
import json,time,gc,sys
from pathlib import Path
from r44_rear_bypass import ROOT,ribbon_at,protected,intersectvol,FPC_W,FPC_T,R,L
from r42_double_loop import stages

def run():
 start=time.monotonic();rows=[];E=ROOT/'evidence';E.mkdir(exist_ok=True)
 all_stages=stages();assert len(all_stages)==121
 for i,stage in enumerate(all_stages):
  s,q=float(stage['s']),float(stage['q']);sh,sec,wl=ribbon_at(s,q,-7.95,True)
  collisions={k:round(float(intersectvol(sh,body)),8) for k,body in protected(s,q).items()}
  bb=sh.BoundingBox()
  row={'idx':i,'stage':stage['stage'],'s_mm':s,'q_mm':q,
       'length_mm':L,'swept_wire_length_mm':round(wl,7),
       'min_centerline_curvature_radius_mm':round(float(sec['minimum_calculated_centerline_radius_mm']),6),
       'min_A_straight_leg_mm':round(float(sec['leg_A_mm']),6),
       'volumetric_intersection_mm3':collisions,
       'xz_envelope_violation_mm':round(max(0.,-36.995-bb.xmin,bb.xmax-36.995,-8.2-bb.zmin,bb.zmax-7.68),6),
       'y_nominal_envelope_violation_mm':round(max(0.,bb.ymax-(94.25+s)),6)}
  rows.append(row)
  if (i+1)%20==0 or i==len(all_stages)-1:
   print('progress',i+1,'/',len(all_stages),'elapsed_s',round(time.monotonic()-start,1),flush=True)
   (E/'R44_dense_progress.json').write_text(json.dumps({'complete':False,'rows':len(rows),'elapsed_s':round(time.monotonic()-start,1)})+'\n')
   gc.collect()
 bad=[r for r in rows if any(v>1e-6 for v in r['volumetric_intersection_mm3'].values())]
 data={'revision':'R44 near-rear floating single-XY-U ribbon 121-POSITION discrete OCC screen',
       'radius_assumed_mm':R,'FPC_width_mm':FPC_W,'FPC_thick_mm':FPC_T,
       'length_assumed_mm':L,'nominal_base_z_mm':-7.95,
       'pose_count':len(rows),'slide_poses':101,'dock_poses':20,
       'core_or_display_Occ_intersection_pose_count':len(bad),
       'max_swept_wire_length_abs_error_mm':max(abs(row['swept_wire_length_mm']-L) for row in rows),
       'smallest_centerline_curvature_radius_mm':min(row['min_centerline_curvature_radius_mm'] for row in rows),
       'max_envelope_XZ_violation_mm':max(row['xz_envelope_violation_mm'] for row in rows),
       'max_envelope_Y_violation_mm':max(row['y_nominal_envelope_violation_mm'] for row in rows),
       'all_pose_details':rows,
       'discrete_Occ_only_no_full_continuous_swept_clearance':True,
       'no_terminal_or_FPC_OEM_layerstack_or_rear_cassette':True,
       'other_missing_critical_rails_not_modelled':True,
       'not_manufacturable':True,'candidate_go':False,'manufacturing_go':False,
       'elapsed_s':round(time.monotonic()-start,3)}
 (E/'R44_dense_121_OCC.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 (E/'R44_dense_progress.json').write_text(json.dumps({'complete':True,'rows':len(rows)})+'\n')
 print('R44 DENSE SUMMARY',json.dumps({k:v for k,v in data.items() if k in ('pose_count','core_or_display_Occ_intersection_pose_count','smallest_centerline_curvature_radius_mm','max_envelope_XZ_violation_mm','max_envelope_Y_violation_mm','elapsed_s')}),flush=True)
 return data
if __name__=='__main__':run()
