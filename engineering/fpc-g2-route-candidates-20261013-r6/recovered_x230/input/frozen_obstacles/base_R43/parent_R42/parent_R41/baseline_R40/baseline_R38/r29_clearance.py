"""Local key collision and outer-envelope stress probes, not an OEM GDT map."""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection,to_global
from r29_mechanics import pullback_gate,nominal_planar_webs,OPEN_GATE_STROKE

def run(write=True):
 A=cq.importers.importBrep(str(ROOT/'cad'/'R28_A_KEYED_UNCHANGED.brep')).val()
 rows=[]
 for side in 'LR':
  sign=-1 if side=='L' else 1
  for t in (0.,OPEN_GATE_STROKE):
   sh=to_global(pullback_gate(side,t),'OPEN',P.travel,P.z_travel)
   for d in (-.05,-.02,0.,.02,.05):
    rows.append(dict(side=side,gate_stroke_mm=t,outward_delta_mm=d,
      key_shell_clash_mm3=round(intersection(A,sh.translate(cq.Vector(sign*d,0,0))),9)))
 out=dict(revision='R29 A-key actual shell vs ±0.05mm transverse gate offsets',
  samples=len(rows),clashes_at_plus_0p05=sum(x['key_shell_clash_mm3']>1e-8 for x in rows if x['outward_delta_mm']==.05),
  clashes_all_tested=sum(x['key_shell_clash_mm3']>1e-8 for x in rows),
  nominal_dimensions=nominal_planar_webs(),rows=rows,
  no_bearings_or_material_strength_proven=True,manufacturing_go=False)
 if write:(ROOT/'verification'/'R29_clearance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':print('R29 CLEAR',run()['clashes_at_plus_0p05'])
