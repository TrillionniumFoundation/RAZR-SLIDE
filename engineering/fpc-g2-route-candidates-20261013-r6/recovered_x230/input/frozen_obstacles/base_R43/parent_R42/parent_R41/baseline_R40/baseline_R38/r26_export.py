"""R26 nine assemblies: genuine R26 OCC solids, including explicitly unsafe GHOST
states (interference is deliberately shown, never treated as valid assembly).
STEP export verifies reimport, per-file digest, and status tags.
"""
import cadquery as cq
import hashlib,json
from r25_capture import ROOT,P,pawl as stow_pawl,to_global
from r25_gate import shutter_stow,new_carrier_ear
from r26_open_mechanics import open_pawl,open_gate,open_carrier_ear,OPEN_GATE_STROKE
from r24_mechanics import r21,outboard_jaws
from r22_mechanics import to_blocal

# name, s, q, leaf, active station, STOW captured, STOW gate/open ext,
# OPEN captured, OPEN gate stroke, OPEN ext, deliberate ghost
SCENES=[
 ('01_STOW_SEATED_GATE_CLOSED_SAFE_RETRACTED',0.,0.,0.,'STOW',True,0.,0.,False,0.,0.,False),
 ('02_STOW_SEATED_MANUAL_GATE_OPEN_UNPOWERED',0.,0.,0.,'STOW',True,2.,.8,False,0.,0.,False),
 ('03_STOW_EARLY_1p59_LEGACY_FALSE_OPEN_R25_VETO_GHOST',1.59,0.,0.,'STOW',False,0.,.8,False,0.,0.,True),
 ('04_MID_SLIDE_ALL_PARKED',P.travel/2,0.,0.,None,False,0.,0.,False,0.,0.,False),
 ('05_OPEN_EARLY_6p61_GATE_CLOSED_FORCE_EXT_0p15_GHOST',P.travel,6.61,0.,'OPEN',False,0.,0.,False,0.,.15,True),
 ('06_OPEN_SEATED_CAPTURED_GATE_CLOSED_RETRACTED',P.travel,P.z_travel,1.,'OPEN',False,0.,0.,True,0.,0.,False),
 ('07_OPEN_SEATED_CAPTURED_MANUAL_GATE_OPEN_UNPOWERED',P.travel,P.z_travel,1.,'OPEN',False,0.,0.,True,.9,.8,False),
 ('08_OPEN_EARLY_6p61_FALSE_CAPTURE_BOTH_OPEN_GHOST',P.travel,6.61,0.,'OPEN',False,0.,0.,True,.9,.8,True),
 ('09_OPEN_UNDOCKED_PARKED_PAWL_FORCED_GATE_0p2_GHOST',P.travel,6.61,0.,'OPEN',False,0.,0.,False,.2,0.,True),
 ('10_OPEN_GATE_CLOSED_CARRIER_ALREADY_EXTENDED_GHOST',P.travel,6.61,0.,'OPEN',False,0.,0.,False,0.,.8,True),
]

def export(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R26_A_UNCHANGED.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R26_B_INBOARD_PAWL_OPEN_GATE_CUT.brep')).val()
 rows=[]
 for name,s,q,leaf,station,st_cap,st_shift,st_ext,op_cap,op_shift,op_ext,ghost in SCENES:
  ref=r21.r17_assembly(P,s,q,leaf)
  parts=dict(A_R26_KEYED_REFERENCE=A,
     B_R26_ACTUAL_NEW_OPEN_GROOVES=B.translate((0,s,-P.z_travel+q)),
     OLED_R17_UNAPPROVED_HYPOTHESIS=ref['OLED'],
     FPC_R17_UNAPPROVED_HYPOTHESIS=ref['FPC'])
  for side in 'LR':
   parts[f'STOW_{side}_R25_PAWL_'+('CAPTURED' if st_cap else 'PARKED')]=to_global(stow_pawl('STOW',side,st_cap), 'STOW',s,q)
   parts[f'STOW_{side}_R25_SHUTTER_'+('MANUAL_OPEN' if st_shift else 'CLOSED')]=to_global(shutter_stow(side,st_shift),'STOW',s,q)
   parts[f'STOW_{side}_R25_CARRIAGE_EAR']=to_global(new_carrier_ear(side,st_ext),'STOW',s,q)
   parts[f'OPEN_{side}_R26_PAWL_'+('CAPTURED' if op_cap else 'INBOARD_PARKED')]=to_global(open_pawl(side,op_cap),'OPEN',s,q)
   parts[f'OPEN_{side}_R26_STAGE2_SHUTTER_'+('MANUAL_OPEN' if op_shift else 'CLOSED')]=to_global(open_gate(side,op_shift),'OPEN',s,q)
   parts[f'OPEN_{side}_R26_LOWER_SWEPT_CARRIAGE']=to_global(open_carrier_ear(side,op_ext),'OPEN',s,q)
   j=outboard_jaws(dict(L=0.,R=0.))[f'B_R24_OUTBOARD_JAW_{side}']
   from r24_mechanics import solve_jaw_shift_by_A_contact
   shift=solve_jaw_shift_by_A_contact('OPEN',side,s,q) or 0.
   parts[f'OPEN_{side}_R24_OLD_EARLY_CAM_JAW']=to_global(j.translate((0,shift,0)),'OPEN',s,q)
  ass=cq.Assembly(name='R26_'+name)
  for n,part in parts.items():
   if 'OLED' in n:color=cq.Color(.04,.79,.84)
   elif 'FPC' in n:color=cq.Color(.85,.28,.62)
   elif 'STAGE2_SHUTTER' in n:color=cq.Color(.93,.22,.22)
   elif 'PAWL' in n:color=cq.Color(.94,.70,.15)
   elif 'CARRIAGE' in n:color=cq.Color(.23,.64,.35)
   elif n.startswith('B'):color=cq.Color(.24,.44,.74)
   else:color=cq.Color(.62,.65,.69)
   ass.add(part,name=n+'_R26_RESEARCH_NOT_FOR_MANUFACTURE',color=color)
  out=ROOT/'cad'/(name+'.step')
  ass.save(str(out),exportType='STEP')
  reread=cq.importers.importStep(str(out)).solids().vals()
  if len(reread)!=len(parts) or not all(i.isValid() for i in reread):
   raise AssertionError((name,len(parts),len(reread)))
  digest=hashlib.sha256(out.read_bytes()).hexdigest()
  rows.append(dict(scene=name,STEP=out.name,parts=len(parts),valid_solids_reimported=len(reread),
      s_mm=s,q_mm=q,stage2_STOW_manual_shift=st_shift,stage2_OPEN_manual_shift=op_shift,
      OPEN_active_carrier_extension=op_ext,deliberate_fault_GHOST=ghost,
      OEM_OLED_not_present=True,electrical_power_hardware_not_present=True,
      cassette_bearing_and_springs_NOT_modeled=True,
      size_bytes=out.stat().st_size,sha256=digest))
  print('R26 STEP',name,len(parts),out.stat().st_size,flush=True)
 result=dict(revision='R26 STEP geometric research snapshot, 10 scenes, including deliberate unsafe GHOSTs',
      exported_scenes=len(rows),scenes=rows,manufacturing_go=False)
 if write:(ROOT/'verification'/'R26_STEP_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result
if __name__=='__main__':export()
