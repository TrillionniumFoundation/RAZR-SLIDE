"""R41 geometry point-sampling ONLY, not volumetric/OCC swept collision clearance.
Tests x/z relocations of the R40 two-stage rolling-U. Does not authorize
changing OEM BRep, connector locations or finished-phone envelope.
"""
from pathlib import Path
import sys,math,json,csv
import numpy as np
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN,TopAbs_ON
R=Path(__file__).resolve().parent
PR=R/'baseline_R40'
sys.path[:0]=[str(PR),str(PR/'baseline_R38'),str(PR/'baseline_R38/baseline_R24'),str(PR/'baseline_R38/baseline_R24/baseline_R23'),str(PR/'baseline_R38/baseline_R24/baseline_R23/baseline_R22')]
from r40_motion import solve,points,DOCK,SLIDE
from r25_capture import P
from r24_mechanics import r21
STATIONS=[('STOW',0.,0.),('MID',SLIDE/2.,0.),('PREDOCK',SLIDE,0.),('OPEN',SLIDE,DOCK)]
A=cq.importers.importBrep(str(PR/'baseline_R38/cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
B=cq.importers.importBrep(str(PR/'baseline_R38/cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()
class Check:
 def __init__(self,part):
  self.cl=BRepClass3d_SolidClassifier(part.wrapped);bb=part.BoundingBox()
  self.bb=np.array([bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax])
 def is_in(self,p):
  b=self.bb
  if not(b[0]-1e-6<=p[0]<=b[1]+1e-6 and b[2]-1e-6<=p[1]<=b[3]+1e-6 and b[4]-1e-6<=p[2]<=b[5]+1e-6):return False
  self.cl.Perform(gp_Pnt(*(float(a) for a in p)),1e-5)
  return self.cl.State() in (TopAbs_IN,TopAbs_ON)

def collect(write=True):
 scenes=[]
 for scene,s,q in STATIONS:
  ref=r21.r17_assembly(P,s,q,1 if scene=='OPEN' else 0)
  obs={ 'A':Check(A),'B':Check(B.translate((0,s,q-DOCK))),
        'OLED':Check(ref['OLED']),'display_FPC':Check(ref['FPC'])}
  scenes.append((scene,s,q,obs))
 dxs=[-33.,-27.,-21.,-15.,-9.,-3.,0.,3.]
 dzs=[-12.,-9.,-6.,-3.,0.,3.,6.,9.,12.]
 rows=[]
 for dx in dxs:
  for dz in dzs:
   counts={k:0 for k in ('A','B','OLED','display_FPC')};interior={k:0 for k in counts}
   env=0.; stations=[]
   for scene,s,q,obs in scenes:
    sol=solve(s,q,16.5,119.)
    pp=points(sol,each_leg=10,around=30)+np.array([dx,0.,dz]);n=len(pp)
    cc={k:0 for k in counts};ir={k:0 for k in counts}
    for i,p in enumerate(pp):
     for name,cls in obs.items():
      hit=cls.is_in(p)
      if hit:
       cc[name]+=1;counts[name]+=1
       if 2<=i<n-2:ir[name]+=1;interior[name]+=1
     # Research physical external X,Z envelope; y end-motion allowance handled independently.
     env=max(env,max(0.,abs(p[0])-36.995,-8.2-p[2],p[2]-7.68))
    stations.append({'pose':scene,'hits':cc,'interior_hits':ir})
   row={'dx_mm':dx,'dz_mm':dz,'total_core_centerline_hits':counts['A']+counts['B'],
        'total_OLED_centerline_hits':counts['OLED'],'total_display_FPC_hits':counts['display_FPC'],
        'interior_core_hits':interior['A']+interior['B'],
        'external_XZ_envelope_excess_mm':round(float(env),5),'pose_hits':stations}
   rows.append(row)
  print('dx done',dx,flush=True)
 rows.sort(key=lambda x:(x['interior_core_hits']+x['total_OLED_centerline_hits'],x['external_XZ_envelope_excess_mm']))
 out={'method':'OCC SolidClassifier points on centreline only; NOT ribbon sweep or continuous collision proof',
      'sampled_stations':[x[0] for x in scenes],'samples_per_station':len(points(solve(0,0),each_leg=10,around=30)),
      'origin_R40_R_mm':16.5,'origin_R40_L_mm':119.,'scan_positions':len(rows),
      'stated_original_cable_anchors_are_relocated_NOT_INSTALLED':True,
      'user_authorized_OEM_volume_removal':False,'manufacturing_go':False,'cases':rows}
 if write:
  p=R/'verification';p.mkdir(exist_ok=True)
  (p/'R41_corridor_scan.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
  with (p/'R41_corridor_rank.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['dx_mm','dz_mm','total_core_centerline_hits','interior_core_hits','total_OLED_centerline_hits','total_display_FPC_hits','external_XZ_envelope_excess_mm']);w.writeheader();w.writerows({k:row[k] for k in w.fieldnames} for row in rows)
 print('BEST',json.dumps(rows[:16],ensure_ascii=False)[:7000]);return out
if __name__=='__main__':collect()
