#!/usr/bin/env python3
"""R43: necessary-condition centreline and unbuilt mid-carriage screening.

Tests ONLY the R42 half-speed, two independent 180-degree XY-U family
under a common rigid X/Z translation of BOTH FPC sections and their endpoints.
A hit is an explicit fatal interior witness for that layout. Zero sampled hits
is NOT volumetric clearance, manufacturability, or OEM authorization.
"""
import os, json, math, sys, time
from pathlib import Path
import numpy as np
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN, TopAbs_ON
from OCP.gp import gp_Pnt
from r42_double_loop import solve,centerline,SLIDE,DOCK,FPC_WIDTH,FPC_THICK,RADIUS
from r42_occ import A_SHELL,B_SHELL
from r25_capture import P
from r24_mechanics import r21
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
POSES=[('STOW',0.,0.),('MID',SLIDE/2,0.),('PREDOCK',SLIDE,0.),('DOCK_HALF',SLIDE,DOCK/2),('OPEN',SLIDE,DOCK)]

class Core:
 def __init__(self,sh):
  self.cl=BRepClass3d_SolidClassifier(sh.wrapped)
  b=sh.BoundingBox();self.bb=(b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax)
 def inside(self,v):
  b=self.bb;x,y,z=map(float,v)
  if x<b[0] or x>b[1] or y<b[2] or y>b[3] or z<b[4] or z>b[5]:return False
  self.cl.Perform(gp_Pnt(x,y,z),1e-7)
  return self.cl.State() in (TopAbs_IN,TopAbs_ON)

def build_pose():
 contexts=[]
 for name,s,q in POSES:
  ref=r21.r17_assembly(P,s,q,int(name=='OPEN'))
  m=solve(s,q)
  obs={'A_CORE':Core(A_SHELL),'B_CORE':Core(B_SHELL.translate((0,s,q-DOCK))),
       'OLED_PROXY':Core(ref['OLED']),'DISPLAY_FPC_PROXY':Core(ref['FPC'])}
  samples=[]
  for sec in ('section_1','section_2'):
   points,_=centerline(m[sec],leg_samples=7,arc_samples=38)
   lens=np.concatenate(([0.],np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))))
   points=points[(lens>=3.)&(lens<=lens[-1]-3.)]
   samples.append(points)
  contexts.append((name,s,q,m,samples,obs))
 return contexts

def simulate(ctx,dx,dz):
 total={key:0 for key in ('A_CORE','B_CORE','OLED_PROXY','DISPLAY_FPC_PROXY')}
 witness={}; c_in_A=0;all_pts=[]; pose_collisions=[]
 delta=np.array([dx,0.,dz])
 for name,s,q,m,samples,obstacles in ctx:
  hh={key:0 for key in total}
  carriage_center=np.asarray(m['C_MOVING_JUNCTION'])+delta
  if obstacles['A_CORE'].inside(carriage_center):c_in_A+=1
  for ix,p in enumerate(samples):
   pts=p+delta;all_pts.append(pts)
   for j,xyz in enumerate(pts):
    for key,obs in obstacles.items():
     if obs.inside(xyz):
      total[key]+=1;hh[key]+=1
      witness.setdefault(key,{'stage':name,'flex_section':ix+1,'xyz_mm':[round(float(v),5) for v in xyz]})
  pose_collisions.append({'stage':name,'hits':hh})
 arr=np.vstack(all_pts)
 # conservative position only; +/- half ribbon width approximated along X, +/- half thickness Z.
 ovrX=max(0.,-36.995-(arr[:,0].min()-FPC_WIDTH/2),arr[:,0].max()+FPC_WIDTH/2-36.995)
 ovrZ=max(0.,-8.2-(arr[:,2].min()-FPC_THICK/2),arr[:,2].max()+FPC_THICK/2-7.68)
 return {'dx_mm':dx,'dz_mm':dz,'inside_samples':total,'number_poses_carriage_center_in_A':c_in_A,
         'x_violation_mm':round(float(ovrX),6),'z_violation_mm':round(float(ovrZ),6),
         'any_protected_core_hit':(total['A_CORE']+total['B_CORE'])>0,
         'sampled_route_interior_has_hits':sum(total.values())>0,
         'candidate_clearance_proven':False,
         'witness':witness,'pose_collisions':pose_collisions}

def run():
 started=time.monotonic();ctx=build_pose()
 # Grid includes R42 0/0 baseline and prior sideward trials.
 # dx shifts both anchored connectors and moving C; not physically approved relocations.
 dxs=list(range(-36,4,3))
 dzs=[i/2 for i in range(-9,4)]
 rows=[]
 for i,dx in enumerate(dxs):
  for dz in dzs:
   row=simulate(ctx,float(dx),float(dz));rows.append(row)
  print(f'R43 dx={dx:+.1f}mm completed {len(rows)}/{len(dxs)*len(dzs)} in {time.monotonic()-started:.1f}s',flush=True)
  (OUT/'R43_scan_PROGRESS.json').write_text(json.dumps({'complete':False,'rows_done':len(rows),'dx':dx})+'\n')
 zero_cores=[r for r in rows if not r['any_protected_core_hit']]
 zero_all=[r for r in rows if not r['sampled_route_interior_has_hits']]
 in_env=[r for r in rows if r['x_violation_mm']==0 and r['z_violation_mm']==0]
 ranked=sorted(rows,key=lambda r:(r['x_violation_mm']+r['z_violation_mm']>0,
      r['number_poses_carriage_center_in_A'],
      r['inside_samples']['A_CORE']+r['inside_samples']['B_CORE'],
      r['inside_samples']['OLED_PROXY']+r['inside_samples']['DISPLAY_FPC_PROXY']))
 result={'revision':'R43 shifted half-speed two-U layout necessary screen; NOT volumetric clearance',
  'scope':'common dx,dz translation of both R42 two-U FPCs and all endpoint anchors; 5 discrete poses',
  'source_A_B_BRep_unchanged':True,'sample_exclusion_mm':3.,'fpc_width_mm':FPC_WIDTH,'fpc_thickness_mm':FPC_THICK,
  'assumed_min_radius_mm':RADIUS,'tested_dx_mm':dxs,'tested_dz_mm':dzs,
  'layouts_tested':len(rows),'five_pose_sections_per_layout':len(ctx)*2,
  'zero_protected_core_point_hits_layouts':len(zero_cores),
  'zero_all_proxy_point_hits_layouts':len(zero_all),
  'in_envelope_point_layouts':len(in_env),
  'in_envelope_and_zero_all_hits':sum(r in zero_all for r in in_env),
  'carriage_center_outside_A_all_tested_poses':sum(r['number_poses_carriage_center_in_A']==0 for r in rows),
  'best_20':ranked[:20], 'rows':rows,
  'sampled_points_can_only_disprove_a_layout':True,
  'no_global_nonexistence_claim':True,
  'R42_base_geometry_without_contacts_or_mid_carrier_mounts':True,
  'candidate_go':False,'manufacturing_go':False,
  'elapsed_s':round(time.monotonic()-started,3)}
 (OUT/'R43_shifted_2U_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (OUT/'R43_scan_PROGRESS.json').write_text(json.dumps({'complete':True,'rows_done':len(rows)})+'\n')
 print('SUMMARY',json.dumps({k:v for k,v in result.items() if k in ('layouts_tested','zero_protected_core_point_hits_layouts','zero_all_proxy_point_hits_layouts','in_envelope_point_layouts','in_envelope_and_zero_all_hits','carriage_center_outside_A_all_tested_poses','elapsed_s')},ensure_ascii=False),flush=True)
 return result
if __name__=='__main__':run()
