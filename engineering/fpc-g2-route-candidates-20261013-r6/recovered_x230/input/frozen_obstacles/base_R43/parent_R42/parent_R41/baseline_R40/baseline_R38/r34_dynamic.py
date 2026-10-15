"""R34 complete-NAMED-part rigid pose and insertion checks for unpowered AABB.
Nothing here models native OEM geometry, compliant contact, electrical mating,
post-fabrication stress, FPC width or continuous dynamics between samples.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r34_parts import te_signal_envelope

INSERT_OFFSETS_Z=(0.,.05,.10,.2,.5,.8,1.1,1.4,1.7,2.0,2.3)
FRONT_INSERT_OFFSETS_Y=(0.,-.05,-.1,-.15,-.2,-.3,-.5,-.8,-1.,-1.5,-2.,-2.5,-3.,-3.5)

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad/R34_A_R33_UNCHANGED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R34_B_OPEN_SIGNAL_ENVELOPE_CRADLES.brep')).val()
    rows=[];fail=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        tr=(0,s,q-P.z_travel)
        Bglobal=B.translate(tr)
        volumes={'A_vs_B':intersection(A,Bglobal),
                 'B_vs_OLED_assumed':intersection(Bglobal,ref['OLED']),
                 'B_vs_FPC_assumed':intersection(Bglobal,ref['FPC'])}
        for side in 'LR':
            proxy=te_signal_envelope(side)
            boxworld=proxy.translate(tr)
            volumes.update({f'{side}_A_vs_TE_nominal_proxy':intersection(A,boxworld),
                            f'{side}_B_vs_TE_nominal_proxy':intersection(B,proxy),
                            f'{side}_OLED_vs_TE_nominal_proxy':intersection(boxworld,ref['OLED']),
                            f'{side}_FPC_vs_TE_nominal_proxy':intersection(boxworld,ref['FPC'])})
        row=dict(pose=tag,volumes_mm3={k:round(v,9) for k,v in volumes.items()},
                 unexpected=[k for k,v in volumes.items() if v>1e-7])
        rows.append(row)
        if row['unexpected']:fail.append(row)
        print('R34 FULL BODY',tag,'unexpected',len(row['unexpected']),flush=True)
    # Insertion happens at B-module subassembly stage before A mating. Nominal
    # vertical tool access, no complete tool geometry or solder operations.
    top,front=[],[]
    for side in 'LR':
        for rise in INSERT_OFFSETS_Z:
            part=te_signal_envelope(side,extra_z=rise)
            top.append(dict(side=side,extra_z_mm=rise,
                    intersects_B_mm3=round(intersection(part,B),9)))
        for dy in FRONT_INSERT_OFFSETS_Y:
            part=te_signal_envelope(side).translate((0,dy,0))
            front.append(dict(side=side,feed_y_offset_mm=dy,
                    intersects_B_mm3=round(intersection(part,B),9)))
        print('R34 FRONT INSERTION',side,'samples',len(FRONT_INSERT_OFFSETS_Y),flush=True)
    out=dict(revision='R34 native catalogue-size TE SIGNAL AABB at relocated top-front-open bays',
             reference_poses=len(POSES),reference_checks=rows,
             unexpected_named_pose_collisions=fail,
             rejected_top_feed_cases=len(top),rejected_top_feed_records=top,
             top_feed_interference_cases=sum(r['intersects_B_mm3']>1e-7 for r in top),
             front_feed_cases=len(front),front_feed_records=front,
             front_feed_interference_cases=sum(r['intersects_B_mm3']>1e-7 for r in front),
             top_withdrawal_has_no_retaining_lid=True,
             open_front_y_without_front_retainer=True,
             does_not_claim_native_TE_STEP_or_valid_electrical_contact=True,
             OLED_FPC_are_unqualified_R21_reference_solids=True,
             not_entire_dynamic_continuous_motion=True,
             manufacturing_go=False)
    if write:(ROOT/'verification/R34_dynamic.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':run()
