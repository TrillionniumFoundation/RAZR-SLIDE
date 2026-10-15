"""R31 sampled full-shell and OLED/FPC collision map, plus continuous-ish
final 0.9 mm approach sample. All OLED geometry is a reference assumption.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection,to_global
from r22_mechanics import to_blocal
from r25_dynamic import POSES
from r24_mechanics import r21
from r31_presence import (interposer,a_occupied_shelf,follower_down,
                           pawl_position,pawl_transit_block)
from r30_mechanics import gate,carrier,extension_at

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R31_A_POSITIVE_OPEN_SHELVES.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R31_B_PRESENCE_POCKETS.brep')).val()
 rows=[];bad=[];near=[]
 for name,s,q in POSES:
  ref=r21.r17_assembly(P,s,q,1. if name=='OPEN_SEATED' else 0.)
  bg=B.translate((0,s,-P.z_travel+q))
  pairs={'A_B':intersection(A,bg),'A_OLED':intersection(A,ref['OLED']),
         'A_FPC':intersection(A,ref['FPC']),
         'B_OLED':intersection(bg,ref['OLED']), 'B_FPC':intersection(bg,ref['FPC'])}
  row={'pose':name,'checks_mm3':{k:round(v,9) for k,v in pairs.items()}}
  rows.append(row)
  if any(v>1e-7 for v in pairs.values()):bad.append(row)
  print('R31 chassis',name,'bad',len(bad),flush=True)
 # Dense terminal motion scan, fixed s=P.travel. At all q the A-key drives
 # displacement via direct contact geometry; nothing is based on an electronic
 # seating sensor, but spring return and mechanics remain unmodeled.
 for q_i in range(73,83):
  q=q_i/10
  if q>P.z_travel+1e-6:continue
  for side in 'LR':
   down=follower_down(q)
   p=interposer(side,down)
   wk=to_global(p,'OPEN',P.travel,q)
   vals={'A_against_ideal_interposer':intersection(A,wk),
         'B_against_ideal_interposer':intersection(B,to_blocal(p,'OPEN')),
         'interposer_against_closed_R30_gate':intersection(p,gate(side,0.))}
   # Probe shroud/key against B at near dock where it may pierce B top.
   b_world=B.translate((0,P.travel,-P.z_travel+q))
   vals['new_A_shelf_against_B']=intersection(a_occupied_shelf(side),b_world)
   row={'side':side,'q_mm':q,'stroke_mm':round(down,6),
        'checks_mm3':{k:round(v,9) for k,v in vals.items()}}
   near.append(row)
   if any(v>1e-7 for v in vals.values()):bad.append(row)
 out={'revision':'R31 new physical late A-key shelf + nominal B pockets, 10 reference poses and 20 near-dock side cases',
       'reference_poses':len(rows),'reference_rows':rows,'near_seat_cases':len(near),
       'near_seat_rows':near,'unexpected_clashes':len(bad),'collision_failures':bad,
       'full_OEM_OLED_edge_envelope_not_available':True,
       'not_a_true_continuous_mechanism_or_force_test':True,
       'manufacturing_go':False}
 if write:(ROOT/'verification'/'R31_dynamic.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out
if __name__=='__main__':
 out=run();print('R31 DYNAMIC SUMMARY',out['unexpected_clashes'],flush=True)
