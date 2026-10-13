"""R32 physical housing + inanimate cassette gauge at ten reference postures.
Zero overlap is not electrical contact, proof of fatigue or continuous motion.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r30_mechanics import gate,carrier
from r22_mechanics import to_blocal
from r32_cartridge import gauge,SAMPLED_INSERT_OFFSETS


def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad'/'R32_A_R31_UNMODIFIED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad'/'R32_B_REAR_CASSETTE_BAYS.brep')).val()
    records=[];fails=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1. if tag=='OPEN_SEATED' else 0.)
        Bb=B.translate((0,s,q-P.z_travel))
        pieces={
          'A_B':intersection(A,Bb),
          'B_reference_OLED':intersection(Bb,ref['OLED']),
          'B_reference_FPC':intersection(Bb,ref['FPC']),
        }
        for side in 'LR':
            cas=gauge(side)
            cs=cas.translate((0,s,q-P.z_travel))
            pieces[f'{side}_gauge_A']=intersection(cs,A)
            pieces[f'{side}_gauge_B']=intersection(cas,B)
            pieces[f'{side}_gauge_OLED']=intersection(cs,ref['OLED'])
            pieces[f'{side}_gauge_FPC']=intersection(cs,ref['FPC'])
        row=dict(pose=tag,s_mm=s,q_mm=q,checks_mm3={k:round(v,9) for k,v in pieces.items()})
        if any(v>1e-7 for v in pieces.values()):fails.append(row)
        records.append(row)
        print('R32 assembly',tag,'clashes',sum(v>1e-7 for v in pieces.values()),flush=True)
    insertion=[]
    for side in 'LR':
        for dy in SAMPLED_INSERT_OFFSETS:
            part=gauge(side,dy)
            vol=intersection(B,part)
            insertion.append(dict(side=side,insert_offset_y_mm=dy,interference_mm3=round(vol,10)))
    legacy_parts=[]
    for side in 'LR':
        for t in (0.,.45,.9):
            for name,sh in (('R30_GATE',gate(side,t)),('R30_CARRIER',carrier(side,0.))):
                legacy_parts.append(dict(side=side,part=name,stroke=t,
                    overlap_new_B_mm3=round(intersection(B,to_blocal(sh,'OPEN')),9)))
    out=dict(revision='R32 B-shell built cassette channels, physical non-energized gauge',
        reference_pose_count=len(records),reference_pose_rows=records,unexpected_reference_collisions=fails,
        insertion_cases=insertion,insertion_clashes=sum(v['interference_mm3']>1e-7 for v in insertion),
        legacy_part_checks=legacy_parts,legacy_part_collisions=sum(v['overlap_new_B_mm3']>1e-7 for v in legacy_parts),
        reference_OLED_FPC_is_not_approved_OEM_envelope=True,
        no_actual_CAD_for_A_mating_blade=True,
        no_continuous_full_motion_closure_or_real_force_verification=True,
        manufacturing_go=False)
    if write:(ROOT/'verification'/'R32_dynamic.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out
if __name__=='__main__':
    d=run();print('R32 DYNAMIC',len(d['unexpected_reference_collisions']),d['insertion_clashes'],d['legacy_part_collisions'],flush=True)
