"""R33 explicit normal vs hazardous STEP scenes.
All electrical parts shown as nominal AABB, NOT official imported geometry.
"""
from __future__ import annotations
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,P
from r24_mechanics import r21
from r33_parts import bored_gauge,keeper_pin,catalogue_TE_box
from r33_expansion import TE_REAR_Y_SHIFT

SCENES=[
 dict(label='01_STOW_KEEPERS_INSTALLED_UNPOWERED',s=0.,q=0.,pin=True),
 dict(label='02_OPEN_FULLY_SEATED_KEEPERS_INSTALLED_UNPOWERED',s=P.travel,q=P.z_travel,pin=True),
 dict(label='03_OPEN_PRIOR_0p05_KEEPERS_INSTALLED_UNPOWERED',s=P.travel,q=8.15,pin=True),
 dict(label='04_PIN_REMOVED_GAUGE_FREE_WITHDRAWAL_GHOST',s=P.travel,q=8.2,pin=False,shift=-2.5,ghost=True),
 dict(label='05_GAUGE_FORCE_WITHDRAWAL_PIN_STILL_INSTALLED_GHOST',s=P.travel,q=8.2,pin=True,shift=-.25,ghost=True),
 dict(label='06_TE_CATALOGUE_BOX_CURRENT_B_COLLISION_GHOST',s=P.travel,q=8.2,pin=True,te=True,ghost=True),
 dict(label='07_REJECTED_ENLARGED_B_TE_CLASHES_KEEPER_GHOST',s=P.travel,q=8.2,pin=True,te=True,rejected=True,ghost=True),
]

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep')).val()
    BREJ=cq.importers.importBrep(str(ROOT/'cad/R33_B_TE_LARGER_BAY_REJECTED.brep')).val()
    rows=[]
    for r in SCENES:
        tag=r['label'];s=r['s'];q=r['q'];tr=(0,s,q-P.z_travel)
        ref=r21.r17_assembly(P,s,q,1 if q==P.z_travel and s==P.travel else 0)
        parts={
            'A_NOMINAL_RESEARCH_SHELL':A,
            'B_R33_PIN_PORTS_RESEARCH' if not r.get('rejected') else 'B_REJECTED_ENLARGEMENT':(BREJ if r.get('rejected') else B).translate(tr),
            'OLED_HYPOTHETICAL_ENVELOPE':ref['OLED'],
            'FPC_HYPOTHETICAL_ENVELOPE':ref['FPC'],
        }
        for side in 'LR':
            parts[f'{side}_UNPOWERED_BORE_GAUGE']=bored_gauge(side,r.get('shift',0.)).translate(tr)
            if r.get('pin'):
                parts[f'{side}_PIN_INSTALLED_BUT_AXIAL_CLIP_MISSING']=keeper_pin(side).translate(tr)
            if r.get('te'):
                parts[f'{side}_TE_2199001_1_CATALOGUE_AABB_PROXY_NOT_OEM_STEP']=catalogue_TE_box(side).translate((0,TE_REAR_Y_SHIFT,0)).translate(tr)
        assembly=cq.Assembly(name='R33_'+tag)
        for label,solid in parts.items():
            col=(cq.Color(.86,.28,.24) if 'TE_' in label or r.get('rejected') else
                 cq.Color(.96,.78,.28) if 'PIN_INSTALLED' in label else
                 cq.Color(.28,.68,.67) if 'OLED' in label else
                 cq.Color(.68,.32,.47) if 'FPC' in label else
                 cq.Color(.26,.45,.78) if label.startswith('B_') else cq.Color(.63,.67,.70))
            assembly.add(solid,name=label,color=col)
        fn=ROOT/'cad'/f'R33_{tag}.step'
        assembly.save(str(fn),exportType='STEP')
        reread=cq.importers.importStep(str(fn)).solids().vals()
        if len(reread)!=len(parts) or not all(sh.isValid() for sh in reread):
            raise RuntimeError(f'{fn.name} bad import {len(reread)} vs {len(parts)}')
        rows.append(dict(scene=tag,file=fn.name,parts=len(parts),valid_solids_imported=len(reread),
                 ghost_unsafe=r.get('ghost',False),
                 manufacturer_TE_STEP_imported=False,
                 bytes=fn.stat().st_size,sha256=hashlib.sha256(fn.read_bytes()).hexdigest()))
        print('R33 STEP',tag,len(reread),'ghost',r.get('ghost',False),flush=True)
    d=dict(revision='R33 7 STEP scenes of unpowered keeper & rejected TE catalogue envelope',
           count=len(rows),scenes=rows,ghost_unsafe_count=sum(x['ghost_unsafe'] for x in rows),
           all_parts_are_valid_no_fabrication_approval=True,manufacturing_go=False)
    if write:(ROOT/'verification/R33_STEP_manifest.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    return d
if __name__=='__main__':run()
