"""R33 enclosure OCC checks for 10 reference poses and unpowered keeper system."""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r33_parts import bored_gauge,keeper_pin

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep')).val()
    rows=[];fatal=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        trans=(0,s,q-P.z_travel)
        Bw=B.translate(trans)
        volumes={'A_B':intersection(A,Bw),
                 'B_OLED_reference':intersection(Bw,ref['OLED']),
                 'B_FPC_reference':intersection(Bw,ref['FPC'])}
        for side in 'LR':
            pin=keeper_pin(side);part=bored_gauge(side)
            volumes.update({f'{side}_pin_B':intersection(pin,B),
                            f'{side}_pin_gauge':intersection(pin,part),
                            f'{side}_gauge_B':intersection(part,B),
                            f'{side}_pin_A':intersection(pin.translate(trans),A),
                            f'{side}_gauge_A':intersection(part.translate(trans),A),
                            f'{side}_pin_OLED':intersection(pin.translate(trans),ref['OLED']),
                            f'{side}_pin_FPC':intersection(pin.translate(trans),ref['FPC']),
                            f'{side}_gauge_OLED':intersection(part.translate(trans),ref['OLED']),
                            f'{side}_gauge_FPC':intersection(part.translate(trans),ref['FPC'])})
        abnormal={k:round(v,9) for k,v in volumes.items() if v>1e-7}
        row=dict(label=tag,s_mm=s,q_mm=q,abnormal=abnormal)
        rows.append(row)
        if abnormal:fatal.append(row)
        print('R33 DYNAMIC',tag,'unexpected',len(abnormal),flush=True)
    d=dict(revision='R33 both bored non-conductive gauge and installed keeper 10-posture OCC study',
           reference_pose_count=len(rows),pose_records=rows,unexpected_collisions=fatal,
           no_actual_true_OLED_package_or_cof_fpc_geometry=True,
           catalogue_contact_not_imported_in_this_assembly=True,
           no_continuous_deformation_lifetime_or_force_verification=True,
           manufacturing_go=False)
    if write:(ROOT/'verification/R33_dynamic.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d
if __name__=='__main__':run()
