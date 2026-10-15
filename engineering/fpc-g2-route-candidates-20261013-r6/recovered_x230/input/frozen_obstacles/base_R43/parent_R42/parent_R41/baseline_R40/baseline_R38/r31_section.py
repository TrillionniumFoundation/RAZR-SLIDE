"""Named sample material cells only; not a min-wall / FEA assertion."""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,blk,intersection
from r31_integration import A_OUT,B_OUT

CELLS={
 'new_slide_roof_near_toe':(34.45,34.50,.65,.73,7.09,7.20),
 'new_slide_outboard_cell':(34.56,34.68,.20,.50,6.50,6.75),
 'original_R30_guide_boss_roof':(34.48,34.525,3.0,4.0,2.68,2.85),
 'original_R30_inboard_guide_wall':(34.32,34.42,3.0,4.0,2.40,2.50),
}

def run(write=True):
 B=cq.importers.importBrep(str(B_OUT)).val()
 old=cq.importers.importBrep(str(ROOT/'cad'/'R30_B_LONGITUDINAL_REBASE.brep')).val()
 sections=[]
 for label,bounds in CELLS.items():
  cub=blk(*bounds)
  sections.append({'label':label,'probe_box_mm3':round(cub.Volume(),9),
     'old_R30_material_fraction':round(intersection(old,cub)/cub.Volume(),7),
     'new_R31_material_fraction':round(intersection(B,cub)/cub.Volume(),7)})
 out={'revision':'R31 selected true CAD material occupancy, no min-wall or load-bearing proof',
  'samples':sections,'sampled_actual_B_material_not_a_continuous_wall_scan':True,
  'old_R29_hypothetical_front_lip_mm':.03,
  'old_R29_lip_not_replaced_with_qualified_load_path':True,
  'A_male_key_new_lip_FEA_not_available':True,
  'B_prismatic_guide_pocket_has_no_spring_or_tether_mount':True,
  'no_material_modulus_yield_tolerances_or_300k_cycles':True,
  'manufacturing_go':False}
 if write:(ROOT/'verification'/'R31_section.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out
if __name__=='__main__':
 r=run();print('R31 SECTION',r['samples'],flush=True)
