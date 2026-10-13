"""R35 standalone STEP scenes. GHOST = deliberately unsafe, NOT validated assembly."""
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,P
from r24_mechanics import r21
from r35_parts import bored_cap,pin,te_signal_envelope

SCENES=[
 ('01_STOW_UNPOWERED_BRIDGES_PINNED',0.,0.,'normal'),
 ('02_OPEN_FULLY_SEATED_UNPOWERED_BRIDGES_PINNED',P.travel,P.z_travel,'normal'),
 ('03_OPEN_PRIOR_0p05_UNPOWERED_BRIDGES_PINNED',P.travel,8.15,'normal'),
 ('04_PIN_WITHDRAWN_UNOPPOSED_GHOST',P.travel,P.z_travel,'pin_withdrawn'),
 ('05_CAP_WITHDRAWN_AFTER_PIN_LOSS_GHOST',P.travel,P.z_travel,'cap_withdrawn'),
 ('06_FORCED_GAUGE_THROUGH_CLOSED_CAP_GHOST',P.travel,P.z_travel,'gauge_forced'),
 ('07_ASSUMED_0p10_CAP_OUT_OF_TOL_GHOST',P.travel,P.z_travel,'tolerance'),
]

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad/R35_A_R34_UNCHANGED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R35_B_INBOARD_RAILS_AND_GUIDES.brep')).val()
    reports=[]
    for name,s,q,mode in SCENES:
        ref=r21.r17_assembly(P,s,q,1 if mode=='normal' and s==P.travel and q==P.z_travel else 0)
        tr=(0,s,q-P.z_travel)
        parts={'A_UNCHANGED_RESEARCH_SHELL':A,'B_R35_INBOARD_RAILS':B.translate(tr),
               'OLED_UNQUALIFIED_ASSUMED_ENVELOPE':ref['OLED'],
               'FPC_UNQUALIFIED_ASSUMED_ENVELOPE':ref['FPC']}
        for side in 'LR':
            cap=bored_cap(side);needle=pin(side);gauge=te_signal_envelope(side)
            if mode=='pin_withdrawn':
                needle=needle.translate((2.4 if side=='L' else -2.4,0,0))
            if mode=='cap_withdrawn':
                cap=cap.translate((0,-1.0,0))
                needle=None
            if mode=='gauge_forced':gauge=gauge.translate((0,-.15,0))
            if mode=='tolerance':cap=cap.translate((-.1 if side=='R' else +.1,-.1,-.1))
            parts[f'{side}_TE_CATALOGUE_AABB_UNPOWERED_NOT_VENDOR_STEP']=gauge.translate(tr)
            parts[f'{side}_RESEARCH_DETACHABLE_BRIDGE_UNQUALIFIED']=cap.translate(tr)
            if needle is not None:
                parts[f'{side}_PIN_WITHOUT_APPROVED_AXIAL_KEEPER']=needle.translate(tr)
        assembly=cq.Assembly(name='R35_'+name)
        for label,solid in parts.items():
            color=(cq.Color(.92,.32,.18) if mode!='normal' and (label.startswith(('L_','R_'))) else
                   cq.Color(.22,.62,.81) if label.startswith('B_') else
                   cq.Color(.63,.67,.72))
            assembly.add(solid,name=label,color=color)
        path=ROOT/'cad'/f'R35_{name}.step'
        assembly.save(str(path),exportType='STEP')
        imported=cq.importers.importStep(str(path)).solids().vals()
        assert len(imported)==len(parts) and all(s.isValid() for s in imported),(name,len(parts),len(imported))
        reports.append(dict(name=name,file=path.name,ghost=mode!='normal',parts=len(parts),valid_imported=len(imported),
                            bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        print('R35 STEP',name,len(parts),'ghost',mode!='normal',flush=True)
    out=dict(revision='R35 seven unpowered surrogate-assembly STEP scenes',scenes=reports,count=len(reports),
             ghosts=sum(r['ghost'] for r in reports),vendor_native_STEP_imported=False,manufacturing_go=False)
    if write:(ROOT/'verification/R35_STEP_manifest.json').write_text(json.dumps(out,indent=2)+'\n')
    return out
if __name__=='__main__':run()
