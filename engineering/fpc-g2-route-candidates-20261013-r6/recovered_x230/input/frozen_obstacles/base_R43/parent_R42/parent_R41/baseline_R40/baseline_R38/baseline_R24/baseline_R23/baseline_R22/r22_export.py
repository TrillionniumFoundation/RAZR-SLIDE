"""R22 inspectable STEP engineering *proxies*; actual mating hardware unproven.

Selected solids in '_FORCE_GHOST_DIAGNOSTIC' scenes intentionally collide;
they are impossible attempted-contact envelopes, not physical assembled positions.
"""
from __future__ import annotations
import cadquery as cq
from pathlib import Path
import hashlib,json
from r22_mechanics import (ROOT,P,r21,integrated_b_shell,assembly_local,to_global,
        qualifying_seat)
from r22_verify import check_geometry

CAD=ROOT/'cad';CAD.mkdir(exist_ok=True)
POSES=[
 ('01_STOW_PARKED_RETRACTED',0.,0.,0.,None,False),
 ('02_MID_SLIDE_DUAL_DOG_FALSE_OPEN_FORCE_GHOST_DIAGNOSTIC',P.travel/2,0.,0.,'STOW',True),
 ('03_OPEN_NEAR_0p20_UNSEATED_FORCE_GHOST_DIAGNOSTIC',P.travel,P.z_travel-.2,0.,'OPEN',True),
 ('04_OPEN_SEATED_CONTACT_EXTENDED_FACE_KEY_UNPROVEN',P.travel,P.z_travel,1.,'OPEN',False),
 ('05_STOW_SEATED_CONTACT_EXTENDED_FACE_KEY_UNPROVEN',0.,0.,0.,'STOW',False),
]
PART_NAMES=('B_CARRIAGE_SAFETY_TAB','B_LOAD_FACE_BOLT_L','B_LOAD_FACE_BOLT_R',
      'B_INDEPENDENT_CENTRE_STOP','B_DOG_L','B_DOG_R',
      'B_CARRIER_LUG_L','B_CARRIER_LUG_R','B_BOTTOM_CARRIER_BACKBONE_PROXY')
COLOR={'A':cq.Color(.54,.56,.60), 'A_fixed_skin':cq.Color(.25,.61,.48),
       'A_moving_leaf':cq.Color(.98,.67,.20),'OLED':cq.Color(.05,.76,.91),
       'FPC':cq.Color(.88,.28,.62),'B_R22':cq.Color(.25,.42,.83)}

def run():
 model=integrated_b_shell(); b=model['R22_b'];manifest=[]
 for tag,s,q,leaf,attempt_port,ghost in POSES:
  parts={k:v for k,v in r21.r17_assembly(P,s,q,leaf).items() if k!='B'}
  parts['B_R22']=b.translate(cq.Vector(0,s,-P.z_travel+q))
  for port in ('STOW','OPEN'):
   if attempt_port==port: retracted=False
   else:retracted=True
   seat=qualifying_seat(port,s,q)
   hardware=assembly_local(retracted=retracted,
       side_l_seated=seat['left_face_proxied_seated'],
       side_r_seated=seat['right_face_proxied_seated'],
       center_seated=seat['captive_A_center_key_proxied_seated'],
       old_dog_l_open=(attempt_port==port),old_dog_r_open=(attempt_port==port))
   for k,v in hardware.items():
    if k in PART_NAMES or k.startswith('B_TE_CONTACT_RECT_PROXY_'):
     parts[port+'_'+k]=to_global(v,port,s,q)
  ass=cq.Assembly(name='R22_'+tag)
  for label,sh in parts.items():
   if label in COLOR: col=COLOR[label]
   elif 'INDEPENDENT_CENTRE_STOP' in label:col=cq.Color(.96,.23,.18)
   elif 'LOAD_FACE_BOLT' in label:col=cq.Color(.89,.39,.18)
   elif 'SAFETY_TAB' in label:col=cq.Color(.99,.76,.18,.55 if ghost else 1.)
   elif 'TE_CONTACT' in label:col=cq.Color(.99,.85,.26)
   elif 'DOG' in label:col=cq.Color(.77,.48,.85)
   else:col=cq.Color(.70,.59,.39)
   ass.add(sh,name=label+'_NON_OEM_PROXY',color=col)
  path=CAD/(tag+'.step')
  ass.save(str(path),exportType='STEP')
  imported=cq.importers.importStep(str(path)).solids().vals()
  expected=len(parts)
  if len(imported)!=expected or any(not x.isValid() for x in imported):
   raise AssertionError((tag,expected,len(imported)))
  item=dict(name=tag,pose_s_mm=s,pose_q_mm=q,ghost_collision=ghost,
    port_attempted_or_engaged=attempt_port,imported_valid_solids=len(imported),
    expected_solids=expected,file=path.name,bytes=path.stat().st_size,
    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    all_OEM_parts_and_spring_force_unverified=True)
  manifest.append(item);print('STEP',tag,expected,path.stat().st_size,flush=True)
 out=dict(revision='R22 PROXY ONLY',manufacturer_production_release=False,
    failures_are_intentionally_overlapping_contact_attempt_ghosts=True,
    STEP_records=manifest,source_B_R22_cut_single_solid=model['one_connected_body'])
 (ROOT/'verification'/'R22_STEP_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 return out

if __name__=='__main__':run()
