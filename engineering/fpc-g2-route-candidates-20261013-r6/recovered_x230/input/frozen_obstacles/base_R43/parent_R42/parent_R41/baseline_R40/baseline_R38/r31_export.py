"""R31 annotated, research-only STEP export with GHOST unsafe examples."""
from __future__ import annotations
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,P,to_global
from r24_mechanics import r21
from r26_open_mechanics import open_pawl
from r30_mechanics import gate,carrier
from r31_presence import interposer,pawl_position,follower_down

SCENES=[
 dict(name='01_STOW_SEATED_OPEN_INTERPOSER_DEFAULT',s=0.,q=0.,has_A=True,lift=0.,pawl=0.,gate=0.,carrier=0.,ghost=False),
 dict(name='02_MID_SLIDE_NO_A_OPEN_INTERPOSER_DEFAULT',s=P.travel/2,q=0.,has_A=True,lift=0.,pawl=0.,gate=0.,carrier=0.,ghost=False),
 dict(name='03_OPEN_8p15_NOT_SEATED_PAWL_PARKED',s=P.travel,q=8.15,has_A=True,lift=.35,pawl=0.,gate=0.,carrier=0.,ghost=False),
 dict(name='04_OPEN_8p20_SEATED_KEY_DRIVEN_RELEASE',s=P.travel,q=8.20,has_A=True,lift=.4,pawl=.55,gate=0.,carrier=0.,ghost=False),
 dict(name='05_OPEN_NO_A_FORCE_FALSE_CAPTURE_GHOST',s=P.travel,q=8.2,has_A=False,lift=0.,pawl=.25,gate=.9,carrier=.8,ghost=True),
 dict(name='06_OPEN_EARLY_8p15_KEY_Z_MINUS_0p05_GHOST',s=P.travel,q=8.15,has_A=True,A_dz=-.05,lift=.4,pawl=.55,gate=.9,carrier=.8,ghost=True),
 dict(name='07_OPEN_SEAT_KEY_Z_PLUS_0p05_LATCH_JAM_GHOST',s=P.travel,q=8.2,has_A=True,A_dz=.05,lift=.35,pawl=.25,gate=0.,carrier=0.,ghost=True),
 dict(name='08_OPEN_PREEXTENDED_CARRIER_FORCE_CLOSED_GHOST',s=P.travel,q=8.2,has_A=True,lift=.4,pawl=.55,gate=0.,carrier=.8,ghost=True),
]

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R31_A_POSITIVE_OPEN_SHELVES.brep')).val()
 B=cq.importers.importBrep(str(ROOT/'cad'/'R31_B_PRESENCE_POCKETS.brep')).val()
 out=[]
 for r in SCENES:
  s,q=r['s'],r['q']
  ref=r21.r17_assembly(P,s,q,1. if (s==P.travel and q==P.z_travel) else 0.)
  parts={
   'B_R31_REWORKED':B.translate((0,s,-P.z_travel+q)),
   'OLED_REFERENCE_NOT_OEM':ref['OLED'],
   'FPC_REFERENCE_NOT_OEM':ref['FPC'],
  }
  if r['has_A']:parts['A_R31_NEW_MALE_SHELVES']=A.translate((0,0,r.get('A_dz',0.)))
  for side in 'LR':
   parts[f'R31_{side}_B_INTERPOSER']=to_global(interposer(side,r['lift']),'OPEN',s,q)
   parts[f'R31_{side}_CAPTURE_PAWL']=to_global(pawl_position(side,r['pawl']),'OPEN',s,q)
   parts[f'R30_{side}_GATE']=to_global(gate(side,r['gate']),'OPEN',s,q)
   parts[f'R30_{side}_CARRIER']=to_global(carrier(side,r['carrier']),'OPEN',s,q)
  a=cq.Assembly(name='R31_'+r['name'])
  for name,solid in parts.items():
   color=(cq.Color(.85,.22,.25) if 'GHOST' in r['name'] and 'INTERPOSER' in name else
      cq.Color(.92,.71,.23) if 'INTERPOSER' in name else
      cq.Color(.75,.50,.15) if 'PAWL' in name else
      cq.Color(.29,.77,.75) if 'OLED' in name else
      cq.Color(.74,.30,.45) if 'FPC' in name else
      cq.Color(.26,.45,.70) if name.startswith('B_') else cq.Color(.61,.65,.69))
   a.add(solid,name=name+'_NOT_RELEASED_FOR_MANUFACTURING',color=color)
  dest=ROOT/'cad'/f'R31_{r["name"]}.step'
  a.save(str(dest),exportType='STEP')
  reread=cq.importers.importStep(str(dest)).solids().vals()
  if len(reread)!=len(parts) or not all(x.isValid() for x in reread):
    raise RuntimeError(f'bad STEP {dest.name} {len(reread)}/{len(parts)}')
  row={'name':r['name'],'filename':dest.name,'parts':len(parts),
       'valid_reimported_solids':len(reread),'ghost_known_unsafe':r['ghost'],
       'A_present':r['has_A'],'q_mm':q,'ideal_plunger_down_mm':r['lift'],
       'size_bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
  out.append(row)
  print('R31 STEP',r['name'],len(parts),'ghost',r['ghost'],flush=True)
 report={'revision':'R31 A-key/B interposer experiment 8 independent STEPs',
   'scenes':out,'scene_count':len(out),'manufacturing_go':False,
   'not_OEM_CAD_or_captive_spring_or_force_proven':True}
 if write:(ROOT/'verification'/'R31_STEP_manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 return report
if __name__=='__main__':run()
