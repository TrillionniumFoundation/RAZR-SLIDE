"""R29 exact OCC relative XYZ offsets at 3 *prescribed* actuator states.

The offsets are stress cases, not OEM or ISO GPS dimension stacks. Collision
checks alone do NOT prove that a pin is still captured or a gate retracts it.
"""
from __future__ import annotations
import itertools,json
import cadquery as cq
from r25_capture import ROOT,intersection
from r29_mechanics import pullback_gate,carrier_with_pin,theoretical_extension,nominal_planar_webs
STATES=(0.,.45,.9)

def run(write=True):
 rows=[]
 for side in 'LR':
  gates={t:pullback_gate(side,t) for t in STATES}
  ears={t:carrier_with_pin(side,theoretical_extension(t)) for t in STATES}
  for w in (.02,.05):
   for dx,dy,dz in itertools.product((-w,0.,w),repeat=3):
    vec=cq.Vector(dx,dy,dz)
    volumes=[round(intersection(gates[t],ears[t].translate(vec)),9) for t in STATES]
    rows.append(dict(side=side,halfwidth_error_mm=w,xyz_mm=[dx,dy,dz],
       volumes_mm3=volumes,collision_in_prescribed_path=any(v>1e-8 for v in volumes)))
   print('R29 TOL',side,w,flush=True)
 summary=[]
 for w in (.02,.05):
  group=[r for r in rows if r['halfwidth_error_mm']==w]
  summary.append(dict(halfwidth_mm=w,configs=len(group),jam_configs=sum(x['collision_in_prescribed_path'] for x in group),
       warning_noninterference_not_capture_certification=True))
 result=dict(revision='R29 108 configurations, three prescribed cam stages, actual OCC solids',
  samples=len(rows),OCC_checks=len(rows)*len(STATES),summary=summary,rows=rows,
  nominal_webs=nominal_planar_webs(),slot_only_radial_backlash_mm=nominal_planar_webs()['pin_slot_radial_clearance_mm'],
  endpoint_force_or_contact_engagement_unverified=True,actual_GDT_unknown=True,
  no_springs_bearings_force_thermal_wear=True,manufacturing_go=False)
 if write:(ROOT/'verification'/'R29_tolerance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result
if __name__=='__main__':
 r=run();print('R29 TOL RES',r['summary'],flush=True)
