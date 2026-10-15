"""Locate native endpoint interference transitions without relabeling bad requests.

Bisection describes the local signed-volume threshold for specific frozen
participants, not a mathematical certified surface-distance bound, global
reachable-set proof, friction simulation or physical force qualification.
"""
from pathlib import Path
import sys,json,math
R=Path('/home/qian-qi/RAZR-SLIDE-pawl-actuation-20261015');O=Path('/tmp/razr-pawl-actuation-20261015');sys.path.insert(0,str(R/'integration'))
import verify_pawl_actuator as w
meta,p,h=w.load_new(O/'native-v2/manifest.json');prior,old,profiles=w.prior_native(h)
half=(w.GR-w.PR)*math.hypot(1,w.M);rows=[]
for side in 'LR':
 for label,a,b,fixed in [('lower',-half,0.,old[side+'_ROOT_INNER']),('upper',1.1,1.1+half,p[side+'_ROOT_OUTER'])]:
  start=(a,b);va=w.v.common(p[side+'_PAWL'].translate((0,0,a)),fixed);vb=w.v.common(p[side+'_PAWL'].translate((0,0,b)),fixed)
  if label=='lower':assert va>w.TOL and vb<=w.TOL
  else:assert va<=w.TOL and vb>w.TOL
  samples=[{'z':a,'volume':va},{'z':b,'volume':vb}]
  for _ in range(22):
   mid=(a+b)/2.;v=w.v.common(p[side+'_PAWL'].translate((0,0,mid)),fixed);samples.append({'z':mid,'volume':v})
   if (v>w.TOL)==(label=='lower'):a=mid
   else:b=mid
  row={'side':side,'endpoint':label,'initial_slot_only_interval_mm':start,'actual_native_volume_threshold_mm3':w.TOL,'transition_bracket_mm':[a,b],'transition_bracket_width_mm':b-a,'samples':samples,'not_a_certified_surface_or_global_monotonicity_proof':True}
  rows.append(row);print(side,label,row['transition_bracket_mm'],flush=True)
assert all(w.sha(f)==v for f,v in h.items())
(O/'endpoint-contact-brackets.json').write_text(json.dumps({'input_sha256':h,'rows':rows,'scope':__doc__,'does_not_modify_candidate_or_clearance_failures':True},indent=2)+'\n')
