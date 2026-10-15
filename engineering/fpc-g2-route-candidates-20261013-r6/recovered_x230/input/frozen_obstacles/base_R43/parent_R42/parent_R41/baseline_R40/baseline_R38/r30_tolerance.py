"""Differential cam/follower OCC static pose perturbations.
Exhaustive only for the declared cube grid, NOT full GDT or constrained cam action.
"""
from __future__ import annotations
import cadquery as cq,json,itertools
from r25_capture import ROOT,intersection
from r30_mechanics import gate,carrier,extension_at,web_budget
STROKES=(0.,.45,.9)

def run(write=True):
 rows=[]
 for side in 'LR':
  gates={t:gate(side,t) for t in STROKES}
  ears={t:carrier(side,extension_at(t)) for t in STROKES}
  for w in (.02,.05):
   for xyz in itertools.product((-w,0.,w),repeat=3):
    displaced=cq.Vector(*xyz)
    vs=[round(intersection(gates[t],ears[t].translate(displaced)),10) for t in STROKES]
    rows.append(dict(side=side,w_mm=w,xyz_mm=xyz,volumes_mm3=vs,
                     interference=any(v>1e-8 for v in vs)))
   print('R30 CAM TOL',side,w,flush=True)
 out={'revision':'R30 triple-stroke static tolerance stress only',
    'number_configurations':len(rows),'occ_pair_checks':len(rows)*len(STROKES),
    'summary':[dict(w_mm=w,configs=sum(r['w_mm']==w for r in rows),
           jam_configs=sum(r['w_mm']==w and r['interference'] for r in rows)) for w in (.02,.05)],
    'rows':rows,'web_budget':web_budget(),'not_oem_stack_up':True,
    'relative_sliding_contact_capture_force_and_retraction_unproved':True,
    'manufacturing_go':False}
 if write:(ROOT/'verification'/'R30_tolerance.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 return out
if __name__=='__main__':
 d=run();print('R30 TOL',d['summary'],flush=True)
