"""Research STEP scenes only. Deliberate GHOSTs visually witness unsafe or impossible poses."""
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,P
from r24_mechanics import r21
from r35_parts import pin,bored_cap,te_signal_envelope
from r36_parts import keeper,catalog_m08x2_screw,rejected_square_nut,pin_head_shear_surrogate

SCENES=[
 ('01_STOW_UNPOWERED_KEEPERS_AND_M08_PROXY',0.,0.,'normal'),
 ('02_OPEN_FULLY_SEATED_UNPOWERED_KEEPERS_AND_M08_PROXY',P.travel,P.z_travel,'normal'),
 ('03_OPEN_PRESEAT_0p05_UNPOWERED',P.travel,8.15,'normal'),
 ('04_FORCED_R35_PIN_WITH_KEEPER_GHOST',P.travel,P.z_travel,'force_pin'),
 ('05_UNTHREADED_M08_SCREW_WITHDRAWN_GHOST',P.travel,P.z_travel,'screw_lost'),
 ('06_KEEPER_AND_SCREW_LOST_PIN_WITHDRAWN_GHOST',P.travel,P.z_travel,'three_stage_loss'),
 ('07_UNFITTED_SQUARE_M08_NUT_COLLISION_GHOST',P.travel,P.z_travel,'nut_collision'),
 ('08_R35_PIN_HEAD_SHEARED_GHOST',P.travel,P.z_travel,'head_shear'),
]

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad/R36_A_R35_UNCHANGED.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val()
 report=[]
 for name,s,q,mode in SCENES:
  ref=r21.r17_assembly(P,s,q,1 if s==P.travel and q==P.z_travel else 0)
  tr=(0,s,q-P.z_travel)
  parts={'A_R35_SOURCE_UNMODIFIED':A,'B_R36_RESEARCH_FRAME':B.translate(tr),
         'OLED_SURROGATE_NOT_VENDOR_3D':ref['OLED'],'FPC_SURROGATE_NOT_VENDOR_3D':ref['FPC']}
  for side in 'LR':
   p=pin(side);c=bored_cap(side);g=te_signal_envelope(side);k=keeper(side);screw=catalog_m08x2_screw(side)
   if mode=='force_pin':p=p.translate((.05 if side=='L' else -.05,0,0))
   if mode=='screw_lost':screw=screw.translate((2.4 if side=='L' else -2.4,0,0))
   if mode=='three_stage_loss':
    screw=None;k=None;p=p.translate((2.4 if side=='L' else -2.4,0,0))
   if mode=='head_shear':p=pin_head_shear_surrogate(side).translate((.20 if side=='L' else -.20,0,0))
   for label,body in [('TE_SIGNAL_CATALOGUE_AABB',g),('RESEARCH_R35_CAP',c),('R35_PIN_OR_HEAD_SHEAR',p),('R36_PIN_KEEPER',k),('M0p8x2_SCREW_CATALOGUE_SURROGATE',screw)]:
    if body is not None: parts[f'{side}_{label}']=body.translate(tr)
   if mode=='nut_collision':parts[f'{side}_2x2x1_SQUARE_NUT_REJECTED']=rejected_square_nut(side).translate(tr)
  ass=cq.Assembly(name='R36_'+name)
  for label,solid in parts.items():
   clr=cq.Color(.90,.28,.23) if mode!='normal' and label.startswith(('R_','L_')) else (cq.Color(.19,.6,.75) if label.startswith('B_') else cq.Color(.7,.72,.73))
   ass.add(solid,name=label,color=clr)
  path=ROOT/'cad'/f'R36_{name}.step'
  ass.save(str(path),exportType='STEP')
  imported=cq.importers.importStep(str(path)).solids().vals()
  assert len(imported)==len(parts) and all(z.isValid() for z in imported),(name,len(imported),len(parts))
  report.append(dict(name=name,file=path.name,ghost=mode!='normal',parts=len(parts),valid_reimport=len(imported),
                    bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  print('R36 STEP',name,len(parts),'GHOST',mode!='normal',flush=True)
 out=dict(revision='R36 unpowered CAD candidates and intentional negative ghosts',scenes=report,
          count=len(report),ghosts=sum(x['ghost'] for x in report),
          vendor_native_TE_STEP_imported=False,vendor_native_M08_STEP_imported=False,
          manufacturer_fit_and_thread_engagement_unproven=True,
          manufacturing_go=False)
 if write:(ROOT/'verification/R36_STEP_manifest.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out
if __name__=='__main__':run()
