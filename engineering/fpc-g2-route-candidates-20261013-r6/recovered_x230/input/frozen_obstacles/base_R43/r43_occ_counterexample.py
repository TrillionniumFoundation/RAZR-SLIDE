#!/usr/bin/env python3
"""Volumetric OCC counterexamples for only two previously screened shift layouts.
No modifications to protected A/B/OLED/FPC, and no functional wiring.
"""
from pathlib import Path
import hashlib,json,time,sys
import cadquery as cq
import numpy as np
from r42_double_loop import solve,SLIDE,DOCK
from r42_occ import A_SHELL,B_SHELL,make_ribbon,carriage
from r40_occ import intersectvol
from r25_capture import P
from r24_mechanics import r21
ROOT=Path(__file__).resolve().parent
LAYOUTS={'LOWEST_SAMPLED_COLLISION':(-3.,1.),'OLED_CENTERLINE_ESCAPE':(-36.,-3.5)}
POSES={'STOW':(0.,0.),'PREDOCK':(SLIDE,0.),'OPEN_SEATED':(SLIDE,DOCK)}

def run():
 started=time.monotonic()
 results={'revision':'R43 OCC volumetric reject: two R42-style translated XY double-U research paths',
 'protected_BRep_unchanged':True,'endpoints_translated_without_OEM_approval':True,
 'evidence_poses':[],'candidate_go':False,'manufacturing_go':False,
 'not_continuous_motion_clearance':True,'ghost_not_a_functional_assembly':True}
 (ROOT/'cad').mkdir(exist_ok=True)
 for lname,(dx,dz) in LAYOUTS.items():
  for stage,(s,q) in POSES.items():
   m=solve(s,q)
   delta=(dx,0.,dz)
   ref=r21.r17_assembly(P,s,q,int(stage=='OPEN_SEATED'))
   protected={'A_R38_CORE':A_SHELL,'B_R38_CORE':B_SHELL.translate((0,s,q-DOCK)),
             'OLED_RESEARCH_PROXY':ref['OLED'],'DISPLAY_FPC_PROXY':ref['FPC']}
   shapes={}
   for sec in ('section_1','section_2'):
    raw,_=make_ribbon(m[sec]);shapes[sec]=raw.translate(delta)
   shapes['FLOATING_C_NO_ACTUATOR']=carriage(m['C_MOVING_JUNCTION']).translate(delta)
   overlaps={k:{obs:round(float(intersectvol(sh,other)),9) for obs,other in protected.items()} for k,sh in shapes.items()}
   inter=intersectvol(shapes['section_1'],shapes['section_2'])
   assert all(sh.isValid() and len(sh.Solids())==1 for sh in shapes.values())
   assert any(v>1e-6 for section in ('section_1','section_2') for key,v in overlaps[section].items() if key in ('A_R38_CORE','B_R38_CORE'))
   row={'layout':lname,'translation_mm':[dx,0.,dz],'pose':stage,'s_mm':s,'q_mm':q,
        'penetration_volume_mm3':overlaps,'flex_to_flex_overlap_mm3':round(float(inter),9),
        'rejected_for_core_penetration':True,'oem_modification_permission':False}
   if stage in ('STOW','OPEN_SEATED'):
    path=ROOT/'cad'/f'R43_GHOST_{lname}_{stage}.step'
    assembly=cq.Assembly(name=f'R43_INVALID_{lname}_{stage}')
    for n,sh in {**protected,**shapes}.items():assembly.add(sh,name=n)
    assembly.save(str(path),exportType='STEP')
    solids=cq.importers.importStep(str(path)).solids().vals()
    assert len(solids)>=7 and all(x.isValid() for x in solids)
    row['GHOST_STEP']={'name':path.name,'valid_solids':len(solids),
      'sha256':hashlib.file_digest(open(path,'rb'),'sha256').hexdigest()}
   results['evidence_poses'].append(row)
   print(lname,stage,'A/B totals',*[round(sum(overlaps[sec][name] for sec in ('section_1','section_2')),4) for name in ('A_R38_CORE','B_R38_CORE')],
         'interflex',round(inter,4),flush=True)
 results['poses_with_core_penetration']=sum(r['rejected_for_core_penetration'] for r in results['evidence_poses'])
 results['STEP_count']=sum('GHOST_STEP' in r for r in results['evidence_poses'])
 results['elapsed_s']=round(time.monotonic()-started,3)
 out=ROOT/'verification/R43_OCC_2layout_counterexamples.json';out.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 return results
if __name__=='__main__':run()
