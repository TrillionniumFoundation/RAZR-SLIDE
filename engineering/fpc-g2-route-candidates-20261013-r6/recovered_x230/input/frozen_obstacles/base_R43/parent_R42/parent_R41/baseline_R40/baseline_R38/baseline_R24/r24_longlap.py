"""Adversarial optimization attempt: lengthen jaw overlap to defer early release.
Proves its collision against existing R16/R17 lateral lock-pin envelope.
This is a rejected variant, not an authorized replacement for R24 CAD.
"""
import json
from r24_mechanics import (ROOT,P,blk,to_global,intersection,
  solve_jaw_shift_by_A_contact)
from r16_model import G
from r16_cad import locking_pin
JAW_X={'R':(34.08,34.95),'L':(-34.95,-34.08)}
LUG_X={'R':(34.13,34.39),'L':(-34.39,-34.13)}

def long_jaw(side,shift):return blk(*JAW_X[side],-4.89+shift,-2.81+shift,-3.1,-2.25)
def long_lug(side):return blk(*LUG_X[side],-3.16,-2.89,-3.64+.8,-3.24+.8)
def measure():
 poses=[('STOW',s,0.) for s in (2.,1.6,1.,.2,.02,0.)]
 poses += [('OPEN',P.travel,q) for q in (6.2,6.6,7.,8.,8.15,8.18,8.2)]
 rows=[]
 for port,s,q in poses:
  shift=solve_jaw_shift_by_A_contact(port,'R',s,q)
  vol=intersection(long_jaw('R',shift),long_lug('R'))
  rows.append(dict(port=port,s=s,q=q,cam_stroke=shift,blocking_overlap_mm3=round(vol,9),
       already_cleared_under_strict_tolerance=vol<1e-8,
       fully_seated=(port=='STOW' and s==0.) or (port=='OPEN' and q==P.z_travel)))
 # Legacy R16 pin at fully docked physically locates in A, x=34.15..36.75,
 # y=79.75+4=83.75, z=3.6; envelope must NOT share volume with jaw.
 pin=locking_pin(G(),1,4.,extended=True)
 jaw=to_global(long_jaw('R',2.0),'OPEN',P.travel,P.z_travel)
 pin_clash=intersection(jaw,pin)
 result=dict(revision='R24 long-lap alternative, rejected due to inherited end-lock pin envelope collision',
       cases=rows,
       premature_cam_clear_before_seat=any(x['already_cleared_under_strict_tolerance'] and not x['fully_seated'] for x in rows),
       seated_ideal_cam_has_zero_tolerance_headroom=True,
       OPEN_seated_residual_jaw_lug_overlap_mm3=next(x['blocking_overlap_mm3'] for x in rows if x['port']=='OPEN' and x['q']==8.2),
       OPEN_seated_strict_positive_unlock_not_proven=True,
       clash_with_R16_A_side_lock_pin_at_OPEN_mm3=round(pin_clash,7),
       assumed_existing_pin_is_still_required_as_per_R16=False,
       immediate_recommendation='Do not substitute a longer outboard jaw without redesigning inherited A/B side-pin lock and OEM side-rail load path',
       OEM_tolerances_and_force_validation=False,manufacturing_go=False)
 (ROOT/'verification'/'R24_longlap_rejected.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 return result
if __name__=='__main__':
 x=measure();print(json.dumps({k:v for k,v in x.items() if k!='cases'},indent=2))
