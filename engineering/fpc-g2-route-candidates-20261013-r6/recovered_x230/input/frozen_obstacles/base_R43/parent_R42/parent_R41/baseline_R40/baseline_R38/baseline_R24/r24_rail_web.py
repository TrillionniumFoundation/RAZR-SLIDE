"""R24 candidate A-key groove versus retained R16 side pin bore web.
Uses actual B-local swept OCC envelope and R16 x-axis cylinder shapes.
Distance is nominal, not a tolerance stack/strength qualification.
"""
import json
from r24_mechanics import ROOT
from r24_integration import shell_key_sweep
from r16_cad import cyl_x

def run():
  rows=[]
  for side in 'LR':
    p=shell_key_sweep('STOW',side)
    for yy in (4.,10.):
      bore=cyl_x(33.8,35.3,yy,3.6,.90) if side=='R' else cyl_x(-35.3,-33.8,yy,3.6,.90)
      rows.append(dict(side=side,legacy_B_side_pin_bore_y=yy,
          physical_research_solids_intersect_mm3=round(p.intersect(bore).Volume(),7),
          CAD_nearest_nominal_web_mm=round(p.distance(bore),7)))
  minimum=min(x['CAD_nearest_nominal_web_mm'] for x in rows)
  out=dict(revision='R24 real OCC distance between STOW A-key sweep pocket and R16 side locking-pin bore',
       examined_bores=rows,min_nominal_remaining_sidewall_web_mm=minimum,
       confirmed_OEM_min_wall_thickness=False,
       confirmed_pin_retention_under_impact=False,
       supplier_plate_tolerance_not_loaded=True,
       cannot_use_0p22_nominal_web_as_strength_approval=True,
       manufacturing_go=False)
  (ROOT/'verification'/'R24_side_rail_web.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
  return out
if __name__=='__main__':
 print(json.dumps(run(),ensure_ascii=False,indent=2))
