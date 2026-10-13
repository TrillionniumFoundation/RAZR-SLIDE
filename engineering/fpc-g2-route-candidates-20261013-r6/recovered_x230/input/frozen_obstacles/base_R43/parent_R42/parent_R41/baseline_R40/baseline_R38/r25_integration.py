"""R25 OCC B-shell carving for physically placed stow sidecar and dual capture pawls.

UNRELEASED: B envelope, mouldability, retention strength, button/spring and
assembly extraction not certified.  No OPEN stage2 shutter: naive copy rejected.
"""
import json,sys
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT,R24,P,blk,to_global,pawl,PORT_DATA,X_CENTERS,intersection
from r25_gate import shutter_stow,new_carrier_ear
from r24_integration import integrate as integrate_r24,inflated_bbox
from r22_mechanics import to_blocal

POCKET_PAD=.06

def new_pockets():
 rows=[]
 for port in ('STOW','OPEN'):
  for side in 'LR':
   swept=inflated_bbox([pawl(port,side,True),pawl(port,side,False)],pad=POCKET_PAD)
   rows.append((f'{port}_{side}_CAPTURE_PAWL_X_SWEEP',to_blocal(swept,port)))
 for side in 'LR':
  for name,shapes in (
   ('SECOND_GATE_SWEEP',[shutter_stow(side,0),shutter_stow(side,2)]),
   ('CARRIER_EAR_SWEEP',[new_carrier_ear(side,0),new_carrier_ear(side,.8)])):
   rows.append((f'STOW_{side}_{name}',to_blocal(inflated_bbox(shapes,pad=POCKET_PAD),'STOW')))
 return rows

def run(write=True):
 a,b24,_=integrate_r24()
 b=b24;detail=[]
 for name,pocket in new_pockets():
  t=intersection(b,pocket)
  b=b.cut(pocket).clean()
  detail.append(dict(pocket=name,estimated_cut_envelope_mm3=round(pocket.Volume(),6),
     new_B_material_removed_mm3=round(t,6),valid_so_far=b.isValid(),solids_so_far=len(b.Solids())))
  print('R25 CUT',name,'removed',round(t,6),'solids',len(b.Solids()),flush=True)
 out=dict(revision='R25 A shell unchanged from R24; B STOW physically carved sidecar + two port pawl sliding envelopes',
     new_pockets=len(detail),per_pocket=detail,
     A_shell_R24_still_valid=a.isValid() and len(a.Solids())==1,
     B_shell_R25_valid=b.isValid(),B_shell_R25_solids=len(b.Solids()),
     B_cut_vs_R24_mm3=round(b24.Volume()-b.Volume(),6),
     open_port_second_stage_not_in_CAD=True,
     newly_added_solid_fasteners_springs_and_slider_guides_not_modeled=True,
     available_total_B_rail_strength_not_calculated=True,
     candidate_pocket_is_conservative_box_oversize=True,
     manufacturing_go=False)
 if write:
  (ROOT/'verification'/'R25_integration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
  # cache BREP for later STEP generation to avoid multiple R24 OCC rebuilds
  cq.exporters.export(a,str(ROOT/'cad'/'R25_A_R24_KEYS.brep'))
  cq.exporters.export(b,str(ROOT/'cad'/'R25_B_REWORKED.brep'))
 return out,(a,b)

if __name__=='__main__':
 r,_=run()
 print(json.dumps({k:v for k,v in r.items() if k!='per_pocket'},ensure_ascii=False,indent=2))
