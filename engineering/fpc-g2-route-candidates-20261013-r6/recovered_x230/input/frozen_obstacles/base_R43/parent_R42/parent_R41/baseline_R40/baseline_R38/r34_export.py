"""R34 exact-source assemblies and intentionally hazardous GHOST witnesses.
No vendor native CAD, no working electrical connection, no locking safety claims.
"""
from __future__ import annotations
import hashlib,json
import cadquery as cq
from r25_capture import ROOT,P
from r24_mechanics import r21
from r34_parts import te_signal_envelope
from r25_dynamic import POSES
from r33_parts import catalogue_TE_box

SCENES=[
 ('01_STOW_BOTH_SIGNAL_BOX_GAUGES_UNPOWERED',0.,0.,'normal'),
 ('02_OPEN_SEATED_BOTH_SIGNAL_BOX_GAUGES_UNPOWERED',P.travel,P.z_travel,'normal'),
 ('03_OPEN_PRIOR_0p05_UNPOWERED',P.travel,8.15,'normal'),
 ('04_FRONT_WITHDRAWAL_UNOPPOSED_GHOST',P.travel,P.z_travel,'front_exit'),
 ('05_REJECTED_TOP_INSERTION_INTERFERENCE_GHOST',P.travel,P.z_travel,'top_clash'),
 ('06_REJECTED_R33_MINI_BAY_VENDOR_SIZE_CLASH_GHOST',P.travel,P.z_travel,'old_bay'),
]

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad/R34_A_R33_UNCHANGED.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R34_B_OPEN_SIGNAL_ENVELOPE_CRADLES.brep')).val()
    BOLD=cq.importers.importBrep(str(ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep')).val()
    out=[]
    for name,s,q,mode in SCENES:
        ref=r21.r17_assembly(P,s,q,1 if s==P.travel and q==P.z_travel else 0)
        tr=(0,s,q-P.z_travel)
        old=mode=='old_bay'
        parts={
            'A_UNCHANGED_RESEARCH_BREP':A,
            'B_R33_REJECTED_OLD_SMALL_BAY' if old else 'B_R34_RELOCATED_MECHANICAL_ENVELOPE':(BOLD if old else B).translate(tr),
            'OLED_UNQUALIFIED_REFERENCE_ENVELOPE':ref['OLED'],
            'FPC_UNQUALIFIED_REFERENCE_ENVELOPE':ref['FPC'],
        }
        for side in 'LR':
            box=catalogue_TE_box(side) if old else te_signal_envelope(side)
            if mode=='front_exit':box=box.translate((0,-3.5,0))
            if mode=='top_clash':box=box.translate((0,0,1.4))
            parts[f'{side}_TE_CATALOGUE_AABB_PROXY_NOT_ACTUAL_STEP']=box.translate(tr)
        a=cq.Assembly(name='R34_'+name)
        for label,shape in parts.items():
            col=(cq.Color(.93,.31,.22) if mode not in ('normal',) and label.startswith(('L_TE','R_TE')) else
                 cq.Color(.18,.53,.71) if label.startswith('B_') else
                 cq.Color(.29,.73,.66) if 'OLED' in label else
                 cq.Color(.66,.35,.48) if 'FPC' in label else cq.Color(.72,.75,.77))
            a.add(shape,name=label,color=col)
        path=ROOT/'cad'/f'R34_{name}.step'
        a.save(str(path),exportType='STEP')
        imported=cq.importers.importStep(str(path)).solids().vals()
        assert len(imported)==len(parts) and all(x.isValid() for x in imported),(name,len(parts),len(imported))
        out.append(dict(scene=name,file=path.name,parts=len(parts),valid_imported=len(imported),
                    ghost=mode!='normal',bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        print('R34 STEP',name,'parts',len(parts),'ghost',mode!='normal',flush=True)
    result=dict(revision='R34 catalogue-size SIGNAL AABB in front-feed research cradle',
                scenes=out,count=len(out),ghost_count=sum(x['ghost'] for x in out),
                vendor_supplier_STEP_imported=False,manufacturing_go=False)
    if write:(ROOT/'verification/R34_STEP_manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result
if __name__=='__main__':run()
