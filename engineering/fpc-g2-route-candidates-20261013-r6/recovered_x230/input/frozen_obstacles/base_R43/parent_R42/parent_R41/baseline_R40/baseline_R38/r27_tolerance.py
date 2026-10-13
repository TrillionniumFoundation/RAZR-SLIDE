"""Hypothetical three-axis interference scan; NOT actual manufacturing GD&T.

216 x 3 witnesses = 648 actual OCC evaluations across two sides,
two hypothetical +/- widths, 27 dx/dy/dz tuples and three ear poses.
Required result: retracted ear clearance and 0.15 / 0.8 ear STOP at close.
Only gate/ear relative offset is scanned, not spring fatigue, key fit etc.
"""
from __future__ import annotations
import itertools,json
import cadquery as cq
from r25_capture import ROOT,intersection
from r27_mechanics import open_gate_captive
from r26_open_mechanics import open_carrier_ear

def run(write=True):
 rows=[]
 for w in (.02,.05):
  for side in 'LR':
   closed=open_gate_captive(side,0.)
   opened=open_gate_captive(side,.9)
   ears={ext:open_carrier_ear(side,ext) for ext in (0.,.15,.8)}
   for dx,dy,dz in itertools.product((-w,0.,w),repeat=3):
    moved={e:sh.translate(cq.Vector(dx,dy,dz)) for e,sh in ears.items()}
    vals={f'closed_vs_extension_{e:g}_mm3':round(intersection(closed,sh),9) for e,sh in moved.items()}
    vals['open_vs_extension_0p8_mm3']=round(intersection(opened,moved[.8]),9)
    rows.append(dict(side=side,width_mm=w,dx_mm=dx,dy_mm=dy,dz_mm=dz,**vals))
 summary=[]
 for w in (.02,.05):
  sub=[v for v in rows if v['width_mm']==w]
  summary.append(dict(hypothetical_each_axis_perturbation_mm=w,cases=len(sub),
   fully_retracted_false_jam_count=sum(v['closed_vs_extension_0_mm3']>1e-9 for v in sub),
   fails_to_intercept_ext_0p15_count=sum(v['closed_vs_extension_0.15_mm3']<=1e-9 for v in sub),
   fails_to_intercept_ext_0p8_count=sum(v['closed_vs_extension_0.8_mm3']<=1e-9 for v in sub),
   fully_open_false_jam_0p8_count=sum(v['open_vs_extension_0p8_mm3']>1e-9 for v in sub)))
 out=dict(revision='R27 nominal blade-closed catch under hypothetical independent XYZ shifts',
     samples=len(rows),groups=summary,rows=rows,
     OEM_geometry_full_tolerance_stackups_absent=True,
     force_wear_material_FEA_missing=True,manufacturing_go=False)
 if write:(ROOT/'verification'/'R27_tolerance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 return out
if __name__=='__main__':
 print(json.dumps(run()['groups'],indent=2))
