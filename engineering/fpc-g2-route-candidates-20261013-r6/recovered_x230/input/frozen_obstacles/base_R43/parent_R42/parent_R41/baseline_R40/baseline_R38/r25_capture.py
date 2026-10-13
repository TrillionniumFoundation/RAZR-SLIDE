"""R25 separate two-port positive-retention pawl proxy (mm).

A-side male features are REAL R24 fused A keys.  These OCC bodies model a B
spring-driven lateral pawl near the male key; they are NOT a complete working
spring or compliant insertion latch.  Both pawls must be mechanically captured
BEFORE independent contact-carrier shutter may be released.  No position oracle
is used to assess whether an engaged pawl actually resists withdrawal.
"""
from __future__ import annotations
import json,sys,itertools,math
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent
R24=ROOT/'baseline_R24'
if str(R24) not in sys.path:sys.path.insert(0,str(R24))
from r24_mechanics import (P,blk,a_key,a_keys,to_global,intersection,
        a_keyed_shell,outboard_lugs,carrier_arms,solve_jaw_shift_by_A_contact)

# These are hypothetical parts and dimensions, not OEM/FEA/GD&T values.
CAPTURE_GAP_MM=.03
CAPTURE_PROBE_DEPART_MM=.05
PAWL_W=.32
X_CENTERS={'L':-34.75,'R':34.75}
PORT_DATA={
 'STOW':dict(y=(-5.38,-5.33),z=(-2.80,-2.30),park_out=1.10,
             dock=(0.,0.),depart=(.05,0.)),
 'OPEN':dict(y=(-4.50,-4.20),z=(.43,.65),park_out=1.80,
             dock=(P.travel,P.z_travel),depart=(P.travel,P.z_travel-.05)),
}

def pawl(port,side,engaged):
 d=PORT_DATA[port]; sign=-1 if side=='L' else 1
 x=X_CENTERS[side]+(0. if engaged else sign*d['park_out'])
 return blk(x-PAWL_W/2,x+PAWL_W/2,*d['y'],*d['z'])

def capture_witness(port,side):
 d=PORT_DATA[port];key=a_key(port,side)
 seat=to_global(pawl(port,side,True),port,*d['dock'])
 depart=to_global(pawl(port,side,True),port,*d['depart'])
 # Positive witness: clearance in the fully engaged scene, but geometric
 # clash when attempting to withdraw without retracting pawl.
 dock_overlap=intersection(key,seat)
 departing_overlap=intersection(key,depart)
 # Traversal from dock to .05 mm: first collision in OCC, 0.03mm assumed gap.
 path=[]
 for delta in [0.,.01,.02,.03,.04,.05]:
  s,q=(delta,0.) if port=='STOW' else (P.travel,P.z_travel-delta)
  path.append(dict(withdraw_mm=delta,contact_mm3=round(intersection(key,to_global(pawl(port,side,True),port,s,q)),8)))
 # Normal docking: pawl MUST be laterally parked until key has passed it.
 arrive=[]
 for dist in ([0.,.05,.2,1.,2.,8.,16.] if port=='STOW' else [0.,.05,.2,1.,1.59,2.,4.,8.2]):
  s,q=(dist,0.) if port=='STOW' else (P.travel,P.z_travel-dist)
  arrive.append(dict(undocked_mm=dist,
    pawl_parked_clash_mm3=round(intersection(key,to_global(pawl(port,side,False),port,s,q)),8),
    pawl_falsely_engaged_clash_mm3=round(intersection(key,to_global(pawl(port,side,True),port,s,q)),8)))
 # At no A feature (far outside dock) a falsely engaged pawl can still be
 # inserted unless another, as-yet-unbuilt, catch prevents it.
 dangerous_free_engagement_at_far_away=any(
  x['undocked_mm']>=4 and x['pawl_falsely_engaged_clash_mm3']<1e-8 for x in arrive)
 return dict(port=port,side=side,
   dock_key_pawl_interference_mm3=round(dock_overlap,8),
   forced_reverse_0p05_interference_mm3=round(departing_overlap,8),
   positive_capture_under_ideal_rigid_pawl=dock_overlap<1e-8 and departing_overlap>1e-7,
   reverse_contact_path=path,arrival_compare=arrive,
   free_pawl_actuation_far_from_A_is_unblocked=dangerous_free_engagement_at_far_away)

def run(write=True):
 witness=[capture_witness(p,s) for p in ('STOW','OPEN') for s in 'LR']
 result=dict(revision='R25 separate A-key/B-lateral-pawl OCC retention witnesses; NOT a working snap latch',
  witness=witness,retention_witness_count=sum(x['positive_capture_under_ideal_rigid_pawl'] for x in witness),
  docking_with_parked_pawl_all_nominal_zero_clash=all(all(v['pawl_parked_clash_mm3']<1e-8 for v in x['arrival_compare']) for x in witness),
  too_early_false_engagement_causes_arrival_collision=any(any(v['pawl_falsely_engaged_clash_mm3']>0 for v in x['arrival_compare']) for x in witness),
  pawl_can_be_activated_without_A_present=any(x['free_pawl_actuation_far_from_A_is_unblocked'] for x in witness),
  seat_capture_shear_strength_measured=False,
  spring_and_bearing_measured=False,wear_and_foreign_object_not_tested=True,
  tactile_manual_latch_release_not_implemented=True,
  electrically_permitted=False,manufacturing_go=False)
 if write:
  (ROOT/'verification'/'R25_capture.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result

if __name__=='__main__':
 r=run();print(json.dumps({k:v for k,v in r.items() if k!='witness'},ensure_ascii=False,indent=2))
