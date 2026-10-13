"""R28 hypothetical relative XYZ errors for pin/slot (not OEM GD&T).

Perturb moving carrier+pin against stationary shutter at three coupled CAM
poses.  Geometric intersection under error represents a risk of seizure, not
an engineered elastic fit. This scans ONLY relative motion of carrier and
shutter, excluding B mount and real key/torque/thermal distortion.
"""
from __future__ import annotations
import itertools,json
import cadquery as cq
from r25_capture import ROOT,intersection
from r28_retraction import pullback_gate,carrier_with_pin,theoretical_extension

STATES=(0.,.45,.9)

def run(write=True):
 rows=[]
 for side in 'LR':
  gates={t:pullback_gate(side,t) for t in STATES}
  ears={t:carrier_with_pin(side,theoretical_extension(t)) for t in STATES}
  for w in (.02,.05):
   for dx,dy,dz in itertools.product((-w,0.,w),repeat=3):
    vec=cq.Vector(dx,dy,dz)
    overlaps={f'coupled_{t:g}_OCC_interference_mm3':round(intersection(gates[t],ears[t].translate(vec)),9) for t in STATES}
    fail={f'coupled_{t:g}_jam':(v>1e-8) for t,v in [(t,overlaps[f'coupled_{t:g}_OCC_interference_mm3']) for t in STATES]}
    rows.append(dict(side=side,relative_xyz_width_mm=w,dx=dx,dy=dy,dz=dz,**overlaps,**fail))
   print('R28 TOL',side,w,'cases',len([v for v in rows if v['side']==side and v['relative_xyz_width_mm']==w]),flush=True)
 summary=[]
 for w in (.02,.05):
  subset=[r for r in rows if r['relative_xyz_width_mm']==w]
  summary.append(dict(hypothetical_relative_offset_magnitude_mm=w,cases=len(subset),
    reported_nominal_coupled_motion_jam=sum(any(r[f'coupled_{t:g}_jam'] for t in STATES) for r in subset),
    closed_jam=sum(r['coupled_0_jam'] for r in subset),
    transition_jam=sum(r['coupled_0.45_jam'] for r in subset),
    open_jam=sum(r['coupled_0.9_jam'] for r in subset)))
 result=dict(revision='R28 three prescribed positions x two hypothetical xyz offset magnitudes',
   states=STATES,samples=len(rows),OCC_checks=len(rows)*len(STATES),groups=summary,rows=rows,
   true_pin_slot_clearance_budget_unknown=True,actual_GDT_stackup_missing=True,
   no_spring_force_FEA_wear_or_temperature=True,
   manufacturing_go=False)
 if write:(ROOT/'verification'/'R28_tolerance.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 return result
if __name__=='__main__':
 r=run();print('R28 TOLERANCE',r['OCC_checks'],r['groups'])
