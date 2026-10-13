"""Actual BRep local material witnesses and volume accounting; the calculated
leading-edge front margin is not necessarily remaining shell material.
"""
from __future__ import annotations
import json,hashlib
import cadquery as cq
from r25_capture import ROOT,blk,intersection
from r30_mechanics import web_budget

CELLS={
 'outboard_guide_sidewall':(34.59,34.84,3.0,4.0,2.4,2.5),
 'inboard_guide_sidewall':(34.32,34.42,3.0,4.0,2.4,2.5),
 'guide_roof':(34.48,34.525,3.0,4.0,2.68,2.85),
 'guide_floor':(34.48,34.525,3.0,4.0,2.05,2.30),
}

def run(write=True):
 names=['R27_B_CAPTIVE_OPEN_GATE_CUT.brep','R28_B_PULLOUT_CAM_RELIEVED.brep',
        'R29_B_REVISED_SLOT_POCKET.brep','R30_B_LONGITUDINAL_REBASE.brep']
 solids={n:cq.importers.importBrep(str(ROOT/'cad'/n)).val() for n in names}
 ratios={}
 for label,params in CELLS.items():
  witness=blk(*params)
  ratios[label]={'box_volume_mm3':round(witness.Volume(),10)}
  for n,v in solids.items():
   ratios[label][n[:3]+'_material_occupation_fraction']=round(intersection(v,witness)/witness.Volume(),8)
 details=[{'model':n,'valid':s.isValid(),'connected':len(s.Solids())==1,
    'solid_volume_mm3':round(s.Volume(),8),'sha256':hashlib.sha256((ROOT/'cad'/n).read_bytes()).hexdigest()}
     for n,s in solids.items()]
 result={'revision':'R30 B shell actual local material specimens and revision volumes',
   'model':details,'sampled_cross_sections':ratios,'nominal_geometrical_budget':web_budget(),
   'actual_bearing_boss_rearward_of_A_nose_not_a_stress_analysis':True,
   'no_actual_nominal_minimum_wall_thickness_calculated':True,
   'not_full_solid_distance_mesh_tolerance_or_structural_FEA':True,
   'joint_and_pullout_strength_not_measured':True,
   'manufacturing_go':False}
 if write:(ROOT/'verification'/'R30_section.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 return result
if __name__=='__main__':
 r=run(); print('R30 SECTIONS',len(r['sampled_cross_sections']),flush=True)
