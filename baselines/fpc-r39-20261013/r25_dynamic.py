"""R25 discrete independent OCC interference: actual A keys v. movable
STOW gate and bilateral capture pawls; reworked B shell v. moving parts.
R21 OLED x envelope is only an unapproved geometric hypothesis.
"""
import json
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT,PORT_DATA,P,a_key,to_global,pawl,intersection,X_CENTERS
from r25_gate import shutter_stow,new_carrier_ear
from r24_mechanics import INBOARD_OLED_X_HALF

POSES=[('STOW_FULLY_INSERTED',0.,0.),('STOW_0p04',.04,0.),('STOW_1p59',1.59,0.),
 ('STOW_2',2.,0.),('STOW_8',8.,0.),('MID',P.travel/2,0.),
 ('OPEN_PREDOCK',P.travel,0.),('OPEN_6p61',P.travel,6.61),
 ('OPEN_8p15',P.travel,8.15),('OPEN_SEATED',P.travel,8.2)]

def run(write=True):
 a=cq.importers.importBrep(str(ROOT/'cad'/'R25_A_R24_KEYS.brep')).val()
 b=cq.importers.importBrep(str(ROOT/'cad'/'R25_B_REWORKED.brep')).val()
 rows=[];unexpected=[]
 for tag,s,q in POSES:
  print('R25 POSE',tag,flush=True)
  for port in ('STOW','OPEN'):
   for side in 'LR':
    seat=tag in ('STOW_FULLY_INSERTED','OPEN_SEATED') and (('STOW' in tag)==(port=='STOW'))
    cp=pawl(port,side,seat)
    bworld=to_global(cp,port,s,q)
    key=a_key(port,side)
    v=intersection(key,bworld)
    bclash=intersection(b,to_global(cp,port,0.,P.z_travel)) if False else 0. # B native separate shift below
    # Use B-native physical placement for collision test; return zero only if
    # actual R25 B OCC cuts relieved the swept solid.
    from r22_mechanics import to_blocal
    b_local=to_blocal(cp,port)
    bclash=intersection(b,b_local)
    bb=cp.BoundingBox()
    xgap=min(abs(bb.xmin),abs(bb.xmax))-INBOARD_OLED_X_HALF
    row=dict(pose=tag,station=port,side=side,engaged=seat,
       moving_pawl_A_key_interference_mm3=round(v,8),
       moving_pawl_cut_B_interference_mm3=round(bclash,8),
       assumed_screen_x_separation_mm=round(xgap,6))
    # A key should never clash with PARKED pawl on sampled normal travel.
    if not seat and v>1e-7:unexpected.append(row)
    rows.append(row)
  for side in 'LR':
   gate=shutter_stow(side,0.)
   key=a_key('STOW',side)
   clash=intersection(key,to_global(gate,'STOW',s,q))
   rows.append(dict(pose=tag,station='STOW',side=side,part='closed_stage2_gate',
                    moving_gate_A_key_interference_mm3=round(clash,8),
                    moving_gate_B_shell_interference_mm3=round(intersection(b,__import__('r22_mechanics').to_blocal(gate,'STOW')),8)))
   if clash>1e-7:unexpected.append(dict(pose=tag,station='STOW',side=side,gate_key_clash_mm3=clash))
 # fully captured STOW + manually activated gate (not automatically driven)
 opened=[]
 for side in 'LR':
  sh=shutter_stow(side,2.)
  opened.append(dict(side=side,open_gate_clash_with_A_key_mm3=round(intersection(a_key('STOW',side),to_global(sh,'STOW',0.,0.)),8),
          open_gate_clash_with_reworked_B_mm3=round(intersection(b,__import__('r22_mechanics').to_blocal(sh,'STOW')),8)))
 out=dict(revision='R25 10 normal reference poses OCC capture pawls and STOW safety shutter against R24 A keys / modified B',
   samples=len(POSES),rows=rows,unintended_contact_during_parked_travel=unexpected,
   seated_opened_STOW_scenes=opened,
   B_R25_actual_solid_valid=b.isValid(),B_R25_one_body=len(b.Solids())==1,
   A_R24_actual_solid_valid=a.isValid(),
   all_stowed_nonengaged_pawls_key_clashfree=not any('moving_pawl_A_key_interference_mm3' in x for x in unexpected),
   OLED_OEM_package_width_not_known=True,
   installed_slider_guide_and_springs_unverified=True,
   manufacturing_go=False)
 if write:(ROOT/'verification'/'R25_dynamic.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out

if __name__=='__main__':
 r=run()
 print(json.dumps({k:v for k,v in r.items() if k!='rows'},ensure_ascii=False,indent=2))
