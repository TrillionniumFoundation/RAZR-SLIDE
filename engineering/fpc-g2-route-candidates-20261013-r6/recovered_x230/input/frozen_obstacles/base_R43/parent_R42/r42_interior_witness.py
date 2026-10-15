"""Extra R42 witness: show core/OLED paths away from 3mm terminal regions.
Uses OCC solid classifiers on curve sample points ONLY; volumetric OCC collisions
remain the authority for each discrete pose. Research geometry, no OEM clearance.
"""
from pathlib import Path
import json,sys
import numpy as np
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN, TopAbs_ON
from OCP.gp import gp_Pnt
ROOT=Path(__file__).resolve().parent
PR=ROOT/'parent_R41/baseline_R40'
sys.path[:0]=[str(PR),str(PR/'baseline_R38'),str(PR/'baseline_R38/baseline_R24'),str(PR/'baseline_R38/baseline_R24/baseline_R23'),str(PR/'baseline_R38/baseline_R24/baseline_R23/baseline_R22')]
from r25_capture import P
from r24_mechanics import r21
from r42_double_loop import solve,centerline,SLIDE,DOCK
from r42_occ import POSES,A_SHELL,B_SHELL

class Check:
 def __init__(self,shape):
  self.cl=BRepClass3d_SolidClassifier(shape.wrapped);bb=shape.BoundingBox()
  self.bb=(bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax)
 def hit(self,pt):
  b=self.bb
  if not (b[0]<=pt[0]<=b[1] and b[2]<=pt[1]<=b[3] and b[4]<=pt[2]<=b[5]):return False
  self.cl.Perform(gp_Pnt(*(float(x) for x in pt)),1e-6)
  return self.cl.State() in (TopAbs_IN,TopAbs_ON)

def run():
 result={'revision':'R42 interior-only centerline presence witnesses, ancillary to volumetric OCC',
         'terminal_exclusion_each_end_mm':3.,'sampling_is_not_clearance_proof':True,'rows':[],'manufacturing_go':False}
 for stage,s,q in POSES:
  r=r21.r17_assembly(P,s,q,int(stage=='OPEN_SEATED'))
  obs={'A':Check(A_SHELL),'B':Check(B_SHELL.translate((0,s,q-DOCK))),
       'OLED':Check(r['OLED']),'display_FPC':Check(r['FPC'])}
  pose=solve(s,q)
  for sec in ('section_1','section_2'):
   p,_=centerline(pose[sec],leg_samples=16,arc_samples=100)
   length=np.r_[0.,np.cumsum(np.linalg.norm(p[1:]-p[:-1],axis=1))]
   mask=(length>=3.)&(length<=length[-1]-3.)
   vals={};first={}
   for key,cl in obs.items():
    ix=[int(i) for i in np.where(mask)[0] if cl.hit(p[i])]
    vals[key]=len(ix)
    if ix:first[key]=[round(float(x),5) for x in p[ix[0]]]
   result['rows'].append({'stage':stage,'section':sec,
      'points_checked_after_terminal_exclusion':int(mask.sum()),
      'interior_point_hits':vals,'first_interior_witness_xyz':first})
  print(stage,[(r['section'],r['interior_point_hits']) for r in result['rows'][-2:]],flush=True)
 (ROOT/'verification/R42_interior_points.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result
if __name__=='__main__':run()
