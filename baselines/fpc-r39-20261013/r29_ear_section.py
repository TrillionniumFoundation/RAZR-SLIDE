"""Material accounting for R29 carrier outer-ear relief; no strength approval."""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,intersection
from r26_open_mechanics import open_carrier_ear
from r29_mechanics import carrier_with_pin

def run(write=True):
 rows=[]
 for side in 'LR':
  for e in (0.,.8):
   original=open_carrier_ear(side,e)
   new=carrier_with_pin(side,e)
   removed=original.Volume()-intersection(original,new)
   rows.append(dict(side=side,extension_mm=e,original_ear_mm3=round(original.Volume(),8),
     removed_original_material_mm3=round(removed,8),R29_with_pin_mm3=round(new.Volume(),8),
     one_connected_valid=new.isValid() and len(new.Solids())==1))
 out=dict(revision='R29 explicit outboard native carrier ear reduction',rows=rows,
  material_removed_not_a_strength_approval=True,minimum_cross_section_FEA_missing=True,
  full_300k_cycle_fatigue_missing=True,manufacturing_go=False)
 if write:(ROOT/'verification'/'R29_ear_section.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 print(run())
