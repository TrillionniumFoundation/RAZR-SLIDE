"""R24 8-scene CAD exports with real modelled A keys and B body cuts.

Names GHOST indicate intentional unsafe failure. STEP validation concerns only
geometry and part reimport, never forces, pre-load, or circuit safety.
"""
from __future__ import annotations
import hashlib,json
import cadquery as cq
from r24_mechanics import (ROOT,P,r21,carrier_lugs,independent_guard_jaws,
        to_global,outboard_lugs,outboard_jaws,carrier_arms,solve_jaw_shift_by_A_contact)
from r24_integration import integrate
from r22_mechanics import three_deadbolts
from r20_cad import local_assembly

SCENES=[
 ('01_STOW_SEATED_KEYS_CAMMED_PARKED',0.,0.,0.,'STOW',0.,False,False,False),
 ('02_STOW_EARLY_1p59_INNER_FAULT_RELEASE_GHOST',1.59,0.,0.,'STOW',.8,True,True,True),
 ('03_MID_Y_ALL_CONTACTS_PARKED',P.travel/2,0.,0.,None,0.,False,False,False),
 ('04_OPEN_PREDOCK_CONTACTS_PARKED',P.travel,0.,0.,'OPEN',0.,False,False,False),
 ('05_OPEN_EARLY_Q6p61_INNER_FAULT_RELEASE_GHOST',P.travel,6.61,0.,'OPEN',.8,True,True,True),
 ('06_OPEN_SEATED_KEYS_CAMMED_PARKED',P.travel,P.z_travel,1.,'OPEN',0.,False,False,False),
 ('07_OPEN_SEATED_EXTENDED_NO_POWER_PROOF_GHOST',P.travel,P.z_travel,1.,'OPEN',.8,True,True,True),
 ('08_STOW_SEATED_EXTENDED_NO_POWER_PROOF_GHOST',0.,0.,0.,'STOW',.8,True,True,True),
]

def export(write=True):
 a,b,_=integrate()
 scenes=[]
 for tag,s,q,leaf,active_port,ext,all_old_false,all_r23_false,ghost in SCENES:
  refs=r21.r17_assembly(P,s,q,leaf)
  parts={k:v for k,v in refs.items() if k not in ('A','B')}
  parts['A_R24_FUSED_FOUR_PHYSICAL_KEYS_CONCEPT']=a
  parts['B_R24_RAIL_RELIEVED_CONCEPT']=b.translate(cq.Vector(0,s,-P.z_travel+q))
  for port in ('STOW','OPEN'):
   activating=active_port==port
   ce=(ext if activating else 0.)
   if port=='STOW' and q==0.:
     shifts={t:solve_jaw_shift_by_A_contact(port,t,s,q) for t in 'LR'}
   elif port=='OPEN' and s==P.travel:
     shifts={t:solve_jaw_shift_by_A_contact(port,t,s,q) for t in 'LR'}
   else:shifts={'L':0.,'R':0.}
   if any(x is None for x in shifts.values()):raise ValueError((tag,port,shifts))
   for side in 'LR':
     carrier=carrier_lugs(ce)[f'B_R23_CARRIER_LUG_{side}'].fuse(
        carrier_arms(ce)[f'B_R24_ARM_{side}']).fuse(
        outboard_lugs(ce)[f'B_R24_OUTBOARD_LUG_{side}']).clean()
     assert carrier.isValid() and len(carrier.Solids())==1
     parts[f'{port}_B_R24_MONOLITHIC_CARRIER_LUG_ARM_{side}']=to_global(carrier,port,s,q)
     j=outboard_jaws(shifts)[f'B_R24_OUTBOARD_JAW_{side}']
     parts[f'{port}_B_R24_OUTBOARD_FOLLOWER_JAW_{side}']=to_global(j,port,s,q)
     inner=independent_guard_jaws(all_r23_false and activating,
                 all_r23_false and activating)[f'B_R23_A_KEY_JAW_{side}']
     parts[f'{port}_B_R23_INNER_GUARD_JAW_{side}']=to_global(inner,port,s,q)
   old=three_deadbolts(all_old_false and activating,
        all_old_false and activating,all_old_false and activating)
   for k,sh in old.items():parts[f'{port}_{k}']=to_global(sh,port,s,q)
   contacts=local_assembly(retract=not activating or ext==0.,left_open=False,right_open=False)
   for k,v in contacts.items():
    if k.startswith('B_TE_CONTACT_RECT_PROXY_'):
     parts[f'{port}_{k}']=to_global(v,port,s,q)
  assembly=cq.Assembly(name='R24_'+tag)
  for name,sh in parts.items():
   if 'OLED' in name:col=cq.Color(.06,.78,.87)
   elif 'FPC' in name:col=cq.Color(.91,.30,.62)
   elif name.startswith('A_R24'):col=cq.Color(.55,.52,.49)
   elif name.startswith('B_R24_RAIL'):col=cq.Color(.26,.42,.73)
   elif 'R24_MONOLITHIC' in name:col=cq.Color(.98,.63,.15)
   elif 'R24_OUTBOARD_FOLLOWER' in name:col=cq.Color(.86,.25,.21)
   else:col=cq.Color(.56,.70,.55)
   assembly.add(sh,name=name+'_RESEARCH_NOT_OEM',color=col)
  file=ROOT/'cad'/(tag+'.step')
  assembly.save(str(file),exportType='STEP')
  imp=cq.importers.importStep(str(file)).solids().vals()
  if len(imp)!=len(parts) or not all(x.isValid() for x in imp):
   raise RuntimeError((tag,len(imp),len(parts)))
  result=dict(scene=tag,STEP=file.name,parts=len(parts),reimport_solids=len(imp),
      s_mm=s,q_mm=q,active_port=active_port,nominal_extension_mm=ext,
      ghost_unsafe=ghost,legacy_stop_faults_forced=all_old_false,
      R23_inner_jaws_fault_open=all_r23_false,
      real_A_key_shape_modelled=True,
      physically_captured_postseat_release_built=False,
      used_OEM_parts=False,unqualified_contact_rectangular_proxies_present=True,
      SHA256=hashlib.sha256(file.read_bytes()).hexdigest(),bytes=file.stat().st_size)
  scenes.append(result)
  print('STEP',tag,'parts',len(parts),'bytes',file.stat().st_size,flush=True)
 manifest=dict(revision='R24 8 STEP selected proxy assemblies',exports=len(scenes),
  scenes=scenes,NO_MANUFACTURING_RELEASE=True)
 if write:(ROOT/'verification'/'R24_STEP_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
 return manifest

if __name__=='__main__':
 res=export()
 print('R24 STEP re-import passed',res['exports'])
