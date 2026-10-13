"""R30 complete reference poses, including newly ADDED fixed B-guide bosses.
Checks 10 discrete poses, two ends of the shutter; not continuous load proof.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection,to_global
from r25_dynamic import POSES
from r24_mechanics import r21,INBOARD_OLED_X_HALF
from r22_mechanics import to_blocal
from r30_mechanics import gate,carrier,extension_at

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R30_A_R29_KEYS_FROZEN.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R30_B_LONGITUDINAL_REBASE.brep')).val()
 rows=[];bad=[]
 for name,s,q in POSES:
  ref=r21.r17_assembly(P,s,q,1. if name=='OPEN_SEATED' else 0.)
  b_global=B.translate((0,s,-P.z_travel+q))
  vals={'A_vs_B':round(intersection(A,b_global),9),
      'B_vs_OLED':round(intersection(b_global,ref['OLED']),9),
      'B_vs_FPC':round(intersection(b_global,ref['FPC']),9)}
  rows.append({'pose':name,'part':'CHASSIS_AND_NEW_BOSSES','intersections':vals})
  if any(v>1e-7 for v in vals.values()):bad.append(rows[-1])
  for side in 'LR':
   for t in (0.,.9):
    for kind,part in (('GATE',gate(side,t)),('CARRIER',carrier(side,extension_at(t)))):
     world=to_global(part,'OPEN',s,q)
     checks={'A':round(intersection(A,world),9),
             'OLED':round(intersection(ref['OLED'],world),9),
             'FPC':round(intersection(ref['FPC'],world),9),
             'B_SHELL':round(intersection(B,to_blocal(part,'OPEN')),9)}
     row={'pose':name,'side':side,'gate_stroke':t,'part':kind,'intersections':checks}
     rows.append(row)
     if any(v>1e-7 for v in checks.values()):bad.append(row)
  print('R30 COMPLETE POSE',name,'bad',len(bad),flush=True)
 out={'revision':'R30 actual rebased B shell + new anchored bosses vs full modeled A/B/OLED/FPC',
   'pose_count':len(POSES),'tested_rows':len(rows),'unexpected_collision_count':len(bad),
   'failures':bad,'parametric_OLED_only_not_OEM_full_packaging':True,
   'no_real_thermal_mechanical_electrical_validation':True,
   'manufacturing_go':False}
 if write:(ROOT/'verification'/'R30_dynamic.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':print('R30 full pose failures',run()['unexpected_collision_count'])
