"""R30 independently reassembled STEP archive, not production drawings.

GHOST fault poses intentionally intersect or exceed the equal-size shell;
successful STEP export MUST NOT be misread as manufacturing qualification.
"""
from __future__ import annotations
import json,hashlib
import cadquery as cq
from r25_capture import ROOT,P,pawl,to_global,intersection
from r25_gate import shutter_stow,new_carrier_ear
from r26_open_mechanics import open_pawl
from r30_mechanics import gate as pullback_gate,carrier as carrier_with_pin,extension_at as theoretical_extension
from r28_presence import blocker,SENSE_RISE_MM
from r24_mechanics import r21,outboard_jaws,solve_jaw_shift_by_A_contact

SCENES=[
 dict(name='01_OPEN_SEATED_CLOSED_CARRIER_RETRACTED',s=P.travel,q=P.z_travel,gate=0.,extension=0.,captured=True,ghost=False),
 dict(name='02_OPEN_SEATED_GATE_OPEN_CARRIER_0p8',s=P.travel,q=P.z_travel,gate=.9,extension=.8,captured=True,ghost=False),
 dict(name='03_OPEN_SEATED_COUPLED_CAM_MIDSTROKE',s=P.travel,q=P.z_travel,gate=.63,extension=theoretical_extension(.63),captured=True,ghost=False),
 dict(name='04_OPEN_CARRIER_STUCK_AT_0p8_GATE_FORCE_CLOSED_GHOST',s=P.travel,q=P.z_travel,gate=0.,extension=.8,captured=True,ghost=True),
 dict(name='05_OPEN_NOT_SEATED_FALSE_CAPTURE_UNLOCK_GHOST',s=P.travel,q=6.61,gate=.9,extension=.8,captured=True,ghost=True),
 dict(name='06_OPEN_RAISED_OCCUPANCY_PLUNGER_TOO_TALL_REJECT_GHOST',s=P.travel,q=P.z_travel,gate=0.,extension=0.,captured=True,ghost=True,plunger=True),
]

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R30_A_R29_KEYS_FROZEN.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R30_B_LONGITUDINAL_REBASE.brep')).val()
 result=[]
 for x in SCENES:
  name,s,q=x['name'],x['s'],x['q'];gate=x['gate'];extension=x['extension']
  refs=r21.r17_assembly(P,s,q,1. if (s==P.travel and q==P.z_travel) else 0.)
  parts={
   'A_R30_FOUR_LEGACY_KEYS':A,
   'B_R30_REBASED_GUIDE_AND_SHELL':B.translate((0,s,-P.z_travel+q)),
   'OLED_R17_ASSUMPTION_NOT_OEM':refs['OLED'],
   'FPC_R17_ASSUMPTION_NOT_OEM':refs['FPC'],
  }
  for side in 'LR':
   parts[f'STOW_{side}_PARKED_PAWL']=to_global(pawl('STOW',side,False),'STOW',s,q)
   parts[f'STOW_{side}_SHUTTER_CLOSED']=to_global(shutter_stow(side,0.),'STOW',s,q)
   parts[f'STOW_{side}_CARRIER_EAR_RETRACTED']=to_global(new_carrier_ear(side,0.),'STOW',s,q)
   parts[f'OPEN_{side}_PAWL_'+('CAPTURED' if x['captured'] else 'PARKED')]=to_global(open_pawl(side,x['captured']),'OPEN',s,q)
   g=pullback_gate(side,gate)
   e=carrier_with_pin(side,extension)
   parts[f'OPEN_{side}_R30_GUIDED_TAIL_CAM']=to_global(g,'OPEN',s,q)
   parts[f'OPEN_{side}_R30_FOLLOWER_RELOCATED']=to_global(e,'OPEN',s,q)
   jaw=outboard_jaws({side:0.,('R' if side=='L' else 'L'):0.})[f'B_R24_OUTBOARD_JAW_{side}']
   cam=solve_jaw_shift_by_A_contact('OPEN',side,s,q) or 0.
   parts[f'OPEN_{side}_OLD_CAM_JAW']=to_global(jaw.translate((0,cam,0)),'OPEN',s,q)
   if x.get('plunger'):
    parts[f'OPEN_{side}_PRESENCE_PLUNGER_REJECTED_OVER_B_ENVELOPE']=to_global(blocker(side,SENSE_RISE_MM),'OPEN',s,q)
  assembly=cq.Assembly(name='R30_'+name)
  for label,shape in parts.items():
   color=(cq.Color(.88,.23,.22) if 'SLOTTED_GATE' in label or 'PLUNGER' in label else
          cq.Color(.90,.69,.14) if 'PAWL' in label else
          cq.Color(.2,.62,.37) if 'CARRIER' in label or 'PIN' in label else
          cq.Color(.10,.71,.75) if 'OLED' in label else
          cq.Color(.82,.34,.54) if 'FPC' in label else
          cq.Color(.25,.48,.72) if label.startswith('B_') else cq.Color(.61,.65,.67))
   assembly.add(shape,name=label+'_RESEARCH_NO_FABRICATION',color=color)
  dest=ROOT/'cad'/('R30_'+name+'.step')
  assembly.save(str(dest),exportType='STEP')
  loaded=cq.importers.importStep(str(dest)).solids().vals()
  if len(loaded)!=len(parts) or not all(z.isValid() for z in loaded):
   raise RuntimeError(f'R30 STEP reimport {name}: {len(loaded)}/{len(parts)}')
  witnesses={side:round(intersection(pullback_gate(side,gate),carrier_with_pin(side,extension)),8) for side in 'LR'}
  row=dict(scene=name,filename=dest.name,valid_imported_solids=len(loaded),exported_parts=len(parts),
    ghost_known_failure=x['ghost'],gate_stroke_mm=gate,extension_mm=extension,
    endstate_overlap_mm3=witnesses,unqualified_OLED_FPC=True,no_physical_spring_or_power_qualification=True,
    file_size=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
  result.append(row)
  print('R30 STEP',name,len(loaded),'GHOST',x['ghost'],flush=True)
 report=dict(revision='R30 assembled reference STEP, 6 samples including intentional unsafe GHOST',
  scenes=result,scene_count=len(result),manufacturing_go=False)
 if write:(ROOT/'verification'/'R30_STEP_manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 return report
if __name__=='__main__':run()
