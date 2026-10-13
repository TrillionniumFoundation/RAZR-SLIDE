"""R23 named full-proxy assembly STEP export, with explicit GHOST scenes.

A/B/OLED/FPC still R17/R22 research geometry. TE component is still a
rectangular placeholder; power contacts, A-key/capture and USB aren't modeled.
"""
from __future__ import annotations
import json,hashlib
from pathlib import Path
import cadquery as cq
from r23_gate import (ROOT,P,r21,assembly_local,qualifying_seat,to_global,
         carrier_lugs,independent_guard_jaws,spring_axis_proxies,guard_overlap)
from r23_integration import integrate_b_shell

SCENES=[
 ('01_STOW_PARKED_JAWS_CLOSED',0.,0.,0.,None,False,False),
 ('02_MID_R22_TRIPLE_RELEASE_R23_BLOCK_GHOST',P.travel/2,0.,0.,'STOW',False,True),
 ('03_OPEN_NEAR_0p03_R23_BLOCK_GHOST',P.travel,P.z_travel-.03,0.,'OPEN',False,True),
 ('04_OPEN_SEATED_MANUAL_RELEASE_A_KEY_UNPROVEN',P.travel,P.z_travel,1.,'OPEN',True,False),
 ('05_STOW_SEATED_MANUAL_RELEASE_A_KEY_UNPROVEN',0.,0.,0.,'STOW',True,False),
 ('06_MID_ALL_FIVE_FALSE_RELEASE_ESCAPE_GHOST',P.travel/2,0.,0.,'STOW',True,True)
]

BASE_COLORS={'A':cq.Color(.45,.51,.56),
  'A_fixed_skin':cq.Color(.22,.64,.48),'A_moving_leaf':cq.Color(.95,.73,.23),
  'OLED':cq.Color(.10,.81,.87),'FPC':cq.Color(.82,.32,.66),
  'B_R23':cq.Color(.19,.37,.79)}

def generate(write=True):
    integrated=integrate_b_shell();b=integrated['R23_b']
    CAD=ROOT/'cad';CAD.mkdir(exist_ok=True)
    manifest=[]
    for tag,s,q,leaf,attempt,force_open_new,ghost in SCENES:
        parts={k:v for k,v in r21.r17_assembly(P,s,q,leaf).items() if k!='B'}
        parts['B_R23']=b.translate(cq.Vector(0,s,-P.z_travel+q))
        for port in ('STOW','OPEN'):
            activating=attempt==port
            ext=(.8 if activating else 0.)
            # Force all R22 locks false open ONLY on active port. Otherwise parked.
            old=assembly_local(retracted=not activating,
                side_l_seated=activating,side_r_seated=activating,center_seated=activating,
                old_dog_l_open=activating,old_dog_r_open=activating)
            rg={**carrier_lugs(ext),**independent_guard_jaws(force_open_new and activating,
                 force_open_new and activating),**spring_axis_proxies()}
            for key,shape in {**old,**rg}.items():
                if (key.startswith(('B_CARRIAGE_SAFETY_TAB','B_LOAD_FACE_BOLT',
                           'B_INDEPENDENT_CENTRE_STOP','B_DOG_','B_CARRIER_LUG_',
                           'B_BOTTOM_CARRIER_BACKBONE_PROXY','B_TE_CONTACT_RECT_PROXY_',
                           'B_R23_'))):
                    parts[port+'_'+key]=to_global(shape,port,s,q)
        assem=cq.Assembly(name='R23_'+tag)
        for key,part in parts.items():
            col=BASE_COLORS.get(key)
            if col is None:
                if 'R23_A_KEY_JAW' in key:col=cq.Color(.91,.24,.13)
                elif 'R23_CARRIER_LUG' in key:col=cq.Color(.97,.59,.09)
                elif 'RETURN_SPRING' in key:col=cq.Color(.34,.73,.35)
                elif 'CENTRE_STOP' in key:col=cq.Color(.96,.28,.25)
                elif 'TE_CONTACT' in key:col=cq.Color(.95,.79,.31)
                else:col=cq.Color(.73,.57,.46)
            assem.add(part,name=key+'_NOT_OEM_HARDWARE',color=col)
        fp=CAD/(tag+'.step')
        assem.save(str(fp),exportType='STEP')
        imported=cq.importers.importStep(str(fp)).solids().vals()
        count=len(parts)
        if count!=len(imported) or not all(x.isValid() for x in imported):
            raise AssertionError((tag,count,len(imported)))
        details=dict(scene=tag,STEP=fp.name,parts=count,valid_reimport=len(imported),
            ghost_fault_injection=ghost,
            manually_moved_jaws_no_A_key_mechanism_ever_verified=force_open_new,
            A_keys_not_modelled=True,
            radio_frequency_usb_power_contacts_not_modelled=True,
            size_bytes=fp.stat().st_size,
            sha256=hashlib.sha256(fp.read_bytes()).hexdigest())
        manifest.append(details)
        print('R23_STEP',fp.name,'solids',count,'bytes',details['size_bytes'],flush=True)
    obj=dict(revision='R23 full CAD proxy export, 6 scenes',
        valid_exports=len(manifest),
        OEM_CAD_parts_imported=0,
        **{'NO_MANUFACTURING_RELEASE':True},scenes=manifest)
    (ROOT/'verification'/'R23_STEP_manifest.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    return obj

if __name__=='__main__':generate()
