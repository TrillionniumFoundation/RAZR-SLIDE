"""R37 rigid-body approach, extraction, and ten complete surrogate assembly poses.
There is no compliant snap-through FE analysis; an installed stop lip blocks
both withdrawal and the original front-fed bridge assembly sequence.
"""
import json
import cadquery as cq
from r25_capture import ROOT,intersection
from r35_parts import bored_cap,pin,te_signal_envelope
from r35_dynamic import CAP_FEED_DY
from r37_parts import lip,INTEGRAL_HOOK_NOMINAL_PRECONTACT_MM

# Includes fine near-seated sampling, and full original R35 front insertion route.
INSERT_SAMPLES=tuple(sorted(set((*CAP_FEED_DY,-.10,-.08,-.05,-.04,-.03,-.02,-.015,-.011,-.01,0.))))
PULL_SAMPLES=(0.,.005,.01,.015,.02,.03,.04,.05,.08,.1,.2,.5,1.,3.6)

def run(write=True):
    b=cq.importers.importBrep(str(ROOT/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep')).val()
    rows=[]
    for side in 'LR':
        cap=bored_cap(side)
        hook=lip(side)
        for d in INSERT_SAMPLES:
            body=cap.translate((0,d,0))
            rows.append(dict(side=side,operation='original_R35_front_insertion',dy_mm=d,
               body_vs_integral_B_mm3=round(intersection(body,b),9),
               body_vs_local_lip_mm3=round(intersection(body,hook),9)))
        for d in PULL_SAMPLES:
            body=cap.translate((0,-d,0))
            rows.append(dict(side=side,operation='forced_forward_withdrawal',dy_mm=-d,
                body_vs_integral_B_mm3=round(intersection(body,b),9),
                body_vs_local_lip_mm3=round(intersection(body,hook),9)))
        # A fictitious 0.2 mm rigid shift of entire lip can clear one step but
        # detaches its root from B. This is ONLY a disqualifying motion sketch.
        sign=+1 if side=='L' else -1
        pocket=hook.translate((sign*.2,0,0))
        rows.append(dict(side=side,operation='UNPHYSICAL_whole_lip_rigid_shift_0p2',dy_mm=-.3,
            body_vs_shifted_lip_mm3=round(intersection(cap.translate((0,-.3,0)),pocket),9),
            shift_disconnects_real_fused_root=True))
    insertion=[x for x in rows if x['operation']=='original_R35_front_insertion']
    withdrawal=[x for x in rows if x['operation']=='forced_forward_withdrawal']
    out=dict(revision='R37 solid-integral lip; rigid insertion path REJECTED',rows=rows,
      insertion_sample_count=len(insertion),
      original_front_assembly_interfering_positions=sum(x['body_vs_local_lip_mm3']>1e-8 for x in insertion),
      installed_cap_lip_overlap_at_zero=all(abs(x['body_vs_local_lip_mm3'])<1e-8 for x in withdrawal if x['dy_mm']==0.),
      forward_motion_0p05_blocked_each_side=all(x['body_vs_local_lip_mm3']>1e-5 for x in withdrawal if x['dy_mm']==-.05),
      real_snap_installation_not_shown=True,
      no_valid_spring_deflection_or_overmolding_assembly_sequence=True,
      no_retention_force_fatigue_or_thickness_certificate=True,
      theoretical_precontact_clearance_mm=INTEGRAL_HOOK_NOMINAL_PRECONTACT_MM,
      manufacturing_go=False)
    if write:(ROOT/'verification/R37_dynamic.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R37 dynamic insert clashes',out['original_front_assembly_interfering_positions'],'/',len(insertion),'pull .05 both blocked',out['forward_motion_0p05_blocked_each_side'],flush=True)
    return out
if __name__=='__main__':run()
