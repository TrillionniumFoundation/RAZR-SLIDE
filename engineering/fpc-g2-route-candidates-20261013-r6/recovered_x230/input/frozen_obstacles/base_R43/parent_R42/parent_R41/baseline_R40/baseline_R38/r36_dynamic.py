"""R36 finite OCC motion probes; not continuous dynamic sweep, not powered testing."""
import json
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r25_dynamic import POSES
from r24_mechanics import r21
from r35_parts import pin,bored_cap,te_signal_envelope
from r36_parts import keeper,catalog_m08x2_screw,rejected_square_nut,pin_head_shear_surrogate

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad/R36_A_R35_UNCHANGED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep')).val()
    poses=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        tr=(0,s,q-P.z_travel)
        ib=B.translate(tr)
        check={'A_B':intersection(A,ib), 'B_assumed_OLED':intersection(ib,ref['OLED']),
            'B_assumed_FPC':intersection(ib,ref['FPC'])}
        for side in 'LR':
            for name,obj in (('keeper',keeper(side)),('M08_screw_AABB',catalog_m08x2_screw(side)),
                             ('R35_bridge',bored_cap(side)),('R35_pin',pin(side)),('TE_AABB',te_signal_envelope(side))):
                obj=obj.translate(tr)
                check[f'{side}_{name}_A']=intersection(obj,A)
                check[f'{side}_{name}_OLED']=intersection(obj,ref['OLED'])
                check[f'{side}_{name}_FPC']=intersection(obj,ref['FPC'])
        poses.append(dict(name=tag,unexpected_penetrations_mm3={k:round(v,9) for k,v in check.items() if v>1e-7}))
        print('R36 POSE',tag,len(poses[-1]['unexpected_penetrations_mm3']),flush=True)
    stages=[]
    for side in 'LR':
        k=keeper(side);screw=catalog_m08x2_screw(side);p=pin(side)
        sign=(-1 if side=='R' else 1)
        for d in (0,.01,.02,.03,.04,.05,.07,.10,.2,.5):
            stages.append(dict(side=side,action='R35_pin_axial_pull',offset_mm=d,
                 pin_hits_keeper=round(intersection(k,p.translate((sign*d,0,0))),9)))
        for d in (0,.02,.05,.1,.3,.5,1.,2.4):
            sign2=(-1 if side=='R' else 1)
            stages.append(dict(side=side,action='R36_M08_unthreaded_screw_axial_pull',offset_mm=d,
                screw_hits_B=round(intersection(screw.translate((sign2*d,0,0)),B),9),
                screw_hits_keeper=round(intersection(screw.translate((sign2*d,0,0)),k),9)))
        for d in (0,.02,.05,.1,.2,.5,1.):
            stages.append(dict(side=side,action='keeper_backout_with_screw_installed',offset_mm=d,
                 keeper_hits_screw=round(intersection(k.translate((sign2*d,0,0)),screw),9),
                 keeper_hits_B=round(intersection(k.translate((sign2*d,0,0)),B),9)))
        for d in (0,.05,.1,.2,.5,1.):
            stages.append(dict(side=side,action='keeper_backout_after_screw_lost',offset_mm=d,
                keeper_hits_B=round(intersection(k.translate((sign2*d,0,0)),B),9)))
    out=dict(revision='R36 pin-head keeper; finite rigid surrogate motion',
             poses=poses,pose_count=len(poses),stages=stages,
             DIN6799_0p8_model_not_fitted_due_to_shaft_mismatch=True,
             M08_fastener_has_no_thread_engagement_or_torque_witness=True,
             NO_OEM_screw_STEP=True,NO_OEM_TE_STEP=True,
             no_physical_force_test=True,no_real_electrical_isolation=True,
             no_continuous_swept_volume_proof=True,manufacturing_go=False)
    if write:(ROOT/'verification/R36_dynamic.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out
if __name__=='__main__':
 d=run();print('R36 DYNAMIC',len(d['stages']),flush=True)
