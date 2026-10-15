"""R25 STEP evidence: 7 traceable R24/R25 merged research scenes.
Not material/force/production-qualified.  GHOST denotes deliberate unsafe pose.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT,P,PORT_DATA,pawl,to_global,intersection
from r24_mechanics import r21
from r25_gate import shutter_stow,new_carrier_ear
from r24_mechanics import outboard_jaws,solve_jaw_shift_by_A_contact,outboard_lugs
from r22_mechanics import three_deadbolts

SCENES=[
 ('01_STOW_SEATED_CAPTURED_CONTACT_RETRACTED',0.,0.,0.,'STOW',True,0.,0.,False),
 ('02_STOW_CAPTURED_SECONDARY_MANUAL_OPEN_CONTACT_EXTENDED_UNPOWERED',0.,0.,0.,'STOW',True,2.,.8,True),
 ('03_STOW_EARLY_1p59_OLD_FALSE_OPEN_R25_STOP_HARD_GHOST',1.59,0.,0.,'STOW',False,0.,.8,True),
 ('04_MID_SLIDE_ALL_RETRACTED',P.travel/2,0.,0.,None,False,0.,0.,False),
 ('05_OPEN_EARLY_6p61_STILL_UNSAFE_GHOST',P.travel,6.61,0.,'OPEN',False,0.,.8,True),
 ('06_OPEN_SEATED_PAWL_CAPTURED_CARRIAGE_RETRACTED',P.travel,8.2,1.,'OPEN',True,0.,0.,False),
 ('07_OPEN_CAPTURED_FORCE_EXTEND_OPEN_SECOND_STAGE_MISSING_GHOST',P.travel,8.2,1.,'OPEN',True,0.,.8,True),
]

def export(write=True):
 a=cq.importers.importBrep(str(ROOT/'cad'/'R25_A_R24_KEYS.brep')).val()
 b=cq.importers.importBrep(str(ROOT/'cad'/'R25_B_REWORKED.brep')).val()
 scenes=[]
 for name,s,q,leaf,active,captured,gate_shift,ext,ghost in SCENES:
  refs=r21.r17_assembly(P,s,q,leaf)
  parts={'A_R24_KEYS_RETAINED':a,
       'B_R25_CUT_RESEARCH':b.translate(cq.Vector(0,s,-P.z_travel+q)),
       'OLED_R17_HYPOTHESIS':refs['OLED'],'FPC_R17_HYPOTHESIS':refs['FPC']}
  for port in ('STOW','OPEN'):
   for side in 'LR':
    engaged=captured and port==active
    parts[f'{port}_{side}_B_R25_LATERAL_CAPTURE_PAWL_'+('ENGAGED' if engaged else 'PARKED')]=to_global(pawl(port,side,engaged),port,s,q)
    if port=='STOW':
     # R25 STOW native contacts still parked if inactive or ghost extension=0.
     active_ext=ext if active==port else 0.
     parts[f'{port}_{side}_B_R25_CARRIAGE_EAR']=to_global(new_carrier_ear(side,active_ext),port,s,q)
     parts[f'{port}_{side}_B_R25_SECOND_GATE_'+('OPEN' if gate_shift else 'CLOSED')]=to_global(shutter_stow(side,gate_shift if active==port else 0.),port,s,q)
    elif active==port:
     parts[f'{port}_{side}_B_R24_CARRIAGE_WITH_NO_R25_SECOND_GATE']=to_global(outboard_lugs(ext)[f'B_R24_OUTBOARD_LUG_{side}'],port,s,q)
  ass=cq.Assembly(name='R25_'+name)
  for key,sh in parts.items():
   if 'OLED' in key:color=cq.Color(.04,.79,.84)
   elif 'FPC' in key:color=cq.Color(.85,.28,.62)
   elif 'R25_SECOND_GATE' in key:color=cq.Color(.90,.24,.23)
   elif 'R25_LATERAL_CAPTURE_PAWL' in key:color=cq.Color(.94,.70,.15)
   elif 'B_R25_CUT' in key:color=cq.Color(.24,.44,.74)
   else:color=cq.Color(.6,.63,.67)
   ass.add(sh,name=key+'_NOT_FOR_MANUFACTURE',color=color)
  p=ROOT/'cad'/(name+'.step')
  ass.save(str(p),exportType='STEP')
  got=cq.importers.importStep(str(p)).solids().vals()
  valid= len(got)==len(parts) and all(q.isValid() for q in got)
  if not valid:raise RuntimeError((p,len(got),len(parts)))
  item=dict(scene=name,STEP=p.name,parts=len(parts),reimport_valid_solids=len(got),
    s_mm=s,q_mm=q,selected_station=active,legacy_fault_ghost=ghost,
    actual_R25_OPEN_second_stage_hardware_present=False,
    manual_R25_STOW_release_independent_trigger_unbuilt=True,
    research_OLED_is_not_vendor_part=True,
    no_power_interconnect_or_materials_qualified=True,
    sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size_bytes=p.stat().st_size)
  scenes.append(item);print('R25 STEP',name,len(got),p.stat().st_size,flush=True)
 report=dict(revision='R25 7 parametric OCC/STEP assembly snapshots including deliberately bad states',
   exports=len(scenes),scenes=scenes,manufacturing_go=False)
 if write:(ROOT/'verification'/'R25_STEP_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 return report

if __name__=='__main__':
 export()
