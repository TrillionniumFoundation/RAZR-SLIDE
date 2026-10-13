"""R35 OFFLINE rigid sampling. Shows positive geometric retention and negative escape cases.
No physical fastener rating, no electrical continuity, no OEM LCD stack qualification.
"""
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r35_parts import bored_cap,pin,te_signal_envelope

CAP_FEED_DY=(-3.6,-3.0,-2.5,-2.,-1.5,-1.,-.6,-.3,-.15,-.05,0.)
TE_REVERSE_DY=(0.,-.01,-.03,-.05,-.08,-.15,-.3,-.5,-1.,-2.,-3.5)
PIN_WITHDRAW_X=(0.,-.1,-.5,-1.,-1.5,-2.,-2.4)

def parts():
    A=cq.importers.importBrep(str(ROOT/'cad/R35_A_R34_UNCHANGED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep')).val()
    return A,B

def run(write=True):
    A,B=parts(); pose_rows=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        tr=(0,s,q-P.z_travel)
        Bg=B.translate(tr)
        observed={'A_B':intersection(A,Bg),'B_OLED_assumed':intersection(Bg,ref['OLED']),
                  'B_FPC_assumed':intersection(Bg,ref['FPC'])}
        for side in 'LR':
            for typ,sh in [('bridge',bored_cap(side)),('pin',pin(side)),('catalogue_TE',te_signal_envelope(side))]:
                t=sh.translate(tr)
                observed[f'{side}_{typ}_A']=intersection(t,A)
                observed[f'{side}_{typ}_OLED_assumed']=intersection(t,ref['OLED'])
                observed[f'{side}_{typ}_FPC_assumed']=intersection(t,ref['FPC'])
        pose_rows.append(dict(pose=tag,penetrations_mm3={k:round(v,9) for k,v in observed.items() if v>1e-7}))
        print('R35 POSE',tag,len(pose_rows[-1]['penetrations_mm3']),flush=True)
    inserts=[];release=[];pinrow=[]
    for side in 'LR':
        cap=bored_cap(side);gauge=te_signal_envelope(side);pin_obj=pin(side)
        for off in CAP_FEED_DY:
            translated=cap.translate((0,off,0))
            inserts.append(dict(side=side,dy=off,cap_B=round(intersection(translated,B),9),
                                cap_TE=round(intersection(translated,gauge),9)))
        for off in TE_REVERSE_DY:
            translated=gauge.translate((0,off,0))
            release.append(dict(side=side,dy=off,TE_B=round(intersection(translated,B),9),
                                TE_cap_installed=round(intersection(translated,cap),9),
                                TE_cap_removed=0.))
        for off in PIN_WITHDRAW_X:
            dx=off if side=='R' else -off
            p=pin_obj.translate((dx,0,0))
            pinrow.append(dict(side=side,axis_withdraw_mm=abs(off),pin_intersects_B=round(intersection(p,B),9),
                               pin_intersects_cap=round(intersection(p,cap),9)))
    out=dict(revision='R35 independent front capture bridge research, rigid OCC samples',
             reference_poses=len(pose_rows),pose_rows=pose_rows,
             cap_front_feed_samples=inserts,
             catalogue_TE_front_withdrawal_samples=release,
             pin_axial_withdrawal_samples=pinrow,
             no_real_fastener_axial_retention=True,no_A_mating_pads=True,
             no_supplier_3D_model_imported=True,
             no_continuous_swept_volume_proof=True,
             no_solder_thermal_or_force_evidence=True,manufacturing_go=False)
    if write:(ROOT/'verification/R35_dynamic.json').write_text(json.dumps(out,indent=2)+'\n')
    return out
if __name__=='__main__':
    d=run()
    for label,key in [('POSE',d['pose_rows']),('INSERT',d['cap_front_feed_samples']),('REVERSE',d['catalogue_TE_front_withdrawal_samples']),('PIN',d['pin_axial_withdrawal_samples'])]:
        print(label,len(key),'fail/contacts',sum(bool(x.get('penetrations_mm3')) for x in key) if label=='POSE' else key[:2],flush=True)
