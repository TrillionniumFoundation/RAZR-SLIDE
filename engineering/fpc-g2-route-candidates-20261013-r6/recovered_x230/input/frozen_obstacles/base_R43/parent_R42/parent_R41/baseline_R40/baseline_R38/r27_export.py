"""R27 twelve research assemblies from R26 complete baseline, with NEW OPEN
captive blade; STEP reimport+SHA256 and separately labelled unsafe GHOST poses.
Interpenetrating GHOST geometry must NEVER be used for fabrication drawings.
"""
from __future__ import annotations
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,P,pawl as stow_pawl,to_global,intersection
from r25_gate import shutter_stow,new_carrier_ear
from r26_open_mechanics import open_pawl,open_carrier_ear
from r27_mechanics import open_gate_captive
from r26_export import SCENES as R26_SCENES
from r24_mechanics import r21,outboard_jaws,solve_jaw_shift_by_A_contact

SCENES=list(R26_SCENES)+[
 ('11_OPEN_CLOSED_PREEXTENDED_0p8_POSITIVE_VETO_GHOST',P.travel,P.z_travel,1.,'OPEN',False,0.,0.,False,0.,.8,True),
 ('12_OPEN_CAPTURED_MANUAL_RELEASE_0p8_UNPOWERED',P.travel,P.z_travel,1.,'OPEN',False,0.,0.,True,.9,.8,False),
]

def export(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R27_A_KEYED_UNCHANGED.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R27_B_CAPTIVE_OPEN_GATE_CUT.brep')).val()
 result=[]
 for name,s,q,leaf,station,st_cap,st_shift,st_ext,op_cap,op_shift,op_ext,ghost in SCENES:
  ref=r21.r17_assembly(P,s,q,leaf)
  parts=dict(A_R27_KEYED_REFERENCE=A,
      B_R27_OPEN_GROOVES=B.translate((0,s,-P.z_travel+q)),
      OLED_R17_UNAPPROVED_HYPOTHESIS=ref['OLED'],
      FPC_R17_UNAPPROVED_HYPOTHESIS=ref['FPC'])
  explicit_contacts=[]
  for side in 'LR':
   parts[f'STOW_{side}_R25_PAWL']=to_global(stow_pawl('STOW',side,st_cap),'STOW',s,q)
   parts[f'STOW_{side}_R25_SHUTTER']=to_global(shutter_stow(side,st_shift),'STOW',s,q)
   parts[f'STOW_{side}_R25_CARRIAGE_EAR']=to_global(new_carrier_ear(side,st_ext),'STOW',s,q)
   parts[f'OPEN_{side}_R26_PAWL_'+('CAPTURED' if op_cap else 'PARKED')]=to_global(open_pawl(side,op_cap),'OPEN',s,q)
   gate=open_gate_captive(side,op_shift)
   ear=open_carrier_ear(side,op_ext)
   parts[f'OPEN_{side}_R27_CLOSURE_BLADE_'+('OPEN' if op_shift else 'CLOSED')]=to_global(gate,'OPEN',s,q)
   parts[f'OPEN_{side}_R27_CARRIER_EAR']=to_global(ear,'OPEN',s,q)
   explicit_contacts.append(dict(side=side,R27_stage2_gate_carrier_overlap_mm3=round(intersection(gate,ear),9)))
   sh=outboard_jaws(dict(L=0.,R=0.))[f'B_R24_OUTBOARD_JAW_{side}']
   cam=solve_jaw_shift_by_A_contact('OPEN',side,s,q) or 0.
   parts[f'OPEN_{side}_R24_EARLY_CAM_JAW']=to_global(sh.translate((0,cam,0)),'OPEN',s,q)
  ass=cq.Assembly(name='R27_'+name)
  for n,shape in parts.items():
   color=(cq.Color(.85,.22,.22) if 'CLOSURE_BLADE' in n else
          cq.Color(.09,.77,.78) if 'OLED' in n else
          cq.Color(.86,.32,.58) if 'FPC' in n else
          cq.Color(.93,.71,.12) if 'PAWL' in n else
          cq.Color(.20,.59,.37) if 'CARRIER' in n else
          cq.Color(.24,.45,.72) if n.startswith('B_') else cq.Color(.62,.65,.67))
   ass.add(shape,name=n+'_RESEARCH_NOT_MANUFACTURING',color=color)
  out=ROOT/'cad'/('R27_'+name+'.step')
  ass.save(str(out),exportType='STEP')
  imported=cq.importers.importStep(str(out)).solids().vals()
  if len(imported)!=len(parts) or not all(sh.isValid() for sh in imported):
   raise AssertionError((name,len(parts),len(imported)))
  row=dict(scene=name,STEP=out.name,parts=len(parts),valid_solids_reimported=len(imported),
    stage2_shift_mm=op_shift,OPEN_carrier_extension_mm=op_ext,
    deliberate_fault_GHOST=ghost,explicit_carrier_blade_contact_witness=explicit_contacts,
    OEM_OLED_not_present=True,real_electrical_hardware_not_present=True,
    real_latch_springs_bearings_not_present=True,size_bytes=out.stat().st_size,
    sha256=hashlib.sha256(out.read_bytes()).hexdigest())
  result.append(row)
  print('R27 STEP',name,len(parts),'ghost',ghost,flush=True)
 out=dict(revision='R27 STEP twelve explicit full nominal and fault assemblies',
   exported_scenes=len(result),scenes=result,manufacturing_go=False)
 if write:(ROOT/'verification'/'R27_STEP_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 export()
