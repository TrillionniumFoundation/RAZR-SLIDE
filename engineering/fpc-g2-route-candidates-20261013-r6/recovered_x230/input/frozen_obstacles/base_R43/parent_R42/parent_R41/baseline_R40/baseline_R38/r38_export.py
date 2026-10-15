"""Research STEP scenes with STATIC connector-size proxies and NO linking FPC.
Four sample poses + one knowingly clashing GHOST. STEP import validation
proves BRep serialization only, not electrical or dynamic-mechanical fitness.
"""
import json,hashlib
import cadquery as cq
from r25_capture import ROOT,P
from r24_mechanics import r21
from r38_parts import A_proxy,B_proxy,old_outboard_placement_proxy
from r25_dynamic import POSES

SCENES=[
 ('01_STOW_DISCONNECTED_STATIC_TERMINATORS',POSES[0],False),
 ('02_MID_DISCONNECTED_STATIC_TERMINATORS',POSES[5],False),
 ('03_OPEN_PRESEAT_DISCONNECTED_TERMINATORS',POSES[-2],False),
 ('04_OPEN_SEATED_DISCONNECTED_TERMINATORS',POSES[-1],False),
 ('05_GHOST_OLD_OUTBOARD_BM28_AT_OPEN_COLLISION',POSES[-1],True),
]

def run(write=True):
    a=cq.importers.importBrep(str(ROOT/'cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
    b=cq.importers.importBrep(str(ROOT/'cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()
    out=[]
    for name,(tag,s,q),ghost in SCENES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        tr=(0,s,q-P.z_travel)
        shapes={
            'A_R37_CHASSIS_STUDY':a,
            'B_R38_PROVISIONAL_CUT_FROM_UNVERIFIED_CORE':b.translate(tr),
            'OLED_NOT_VENDOR_APPROVED':ref['OLED'],
            'OLD_DISPLAY_FPC_NOT_CROSS_CHAMBER_CABLE':ref['FPC'],
            'A_BM28_STATIC_HEADER_CATALOGUE_ENVELOPE_ONLY':A_proxy(),
            'B_BM28_STATIC_HEADER_CATALOGUE_ENVELOPE_ONLY':B_proxy().translate(tr),
        }
        if ghost: shapes['GHOST_BM28_OLD_R37_OUTBOARD_LOCATION_CLASHES_A']=old_outboard_placement_proxy().translate(tr)
        ass=cq.Assembly(name='R38_'+name)
        for label,sh in shapes.items():
            col=cq.Color(.92,.15,.14) if label.startswith('GHOST') else cq.Color(.22,.56,.78) if label.startswith('B_R38') else cq.Color(.70,.73,.77)
            ass.add(sh,name=label,color=col)
        p=ROOT/'cad'/f'R38_{name}.step'
        if write:ass.save(str(p),exportType='STEP')
        imported=cq.importers.importStep(str(p)).solids().vals()
        assert len(imported)==len(shapes) and all(q.isValid() for q in imported),(name,len(imported))
        out.append(dict(scene=name,pose=tag,ghost=ghost,file=p.name,
          actual_FPC_cross_compartment_installed=False,real_connector_step_imported=False,
          parts=len(shapes),reimported_valid_solids=len(imported),
          file_size_bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        print('R38 STEP',name,'OK',len(imported),flush=True)
    result=dict(revision='R38 research static connector catalogue envelopes; UNCONNECTED and NOT LIVE',scenes=out,
        step_count=len(out),intentional_ghost_count=sum(q['ghost'] for q in out),
        no_real_vendor_FPC_service_loop=True,manufacturing_go=False)
    if write:(ROOT/'verification/R38_STEP_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
if __name__=='__main__':run()
