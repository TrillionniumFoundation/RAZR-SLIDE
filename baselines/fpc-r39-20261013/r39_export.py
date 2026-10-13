"""R39 research ribbon cross-section lofts / STEP negative evidence.
The sweep is a geometric proxy, not FPC layer, conductor, strain relief,
electrical circuit, vendor STEP, validated force equilibrium or usable harness.
"""
import hashlib,json
import cadquery as cq
import numpy as np
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from r25_capture import ROOT,P
from r24_mechanics import r21
from r39_screen import CANDIDATES, frames
from r39_path import curve,anchors,FPC_WIDTH_MM,FPC_THICKNESS_MM

SCENES=[('STOW',0.,0.),('MID',39.875,0.),('OPEN',79.75,8.2)]
CHOSEN=[('INBOARD_SERPENTINE_125','STOW'),('INBOARD_SERPENTINE_125','OPEN'),
        ('OUTBOARD_SINGLE_BOW_125','STOW'),('OUTBOARD_SINGLE_BOW_125','MID'),('OUTBOARD_SINGLE_BOW_125','OPEN'),
        ('GENTLE_INBOARD_SINGLE_BOW_150','OPEN')]

def loft_ribbon(path):
    loft=BRepOffsetAPI_ThruSections(True,False,1.e-3)
    loft.SetMaxDegree(3)
    pts=path['points']; sections=frames(path['tangent'])
    for k in range(0,len(pts),2):
        p=pts[k];w,v=sections[k]
        corners=[p + ws*(FPC_WIDTH_MM/2)*w+vs*(FPC_THICKNESS_MM/2)*v for ws,vs in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        wire=cq.Wire.makePolygon([cq.Vector(*x) for x in corners],close=True)
        loft.AddWire(wire.wrapped)
    loft.Build()
    sh=cq.Shape.cast(loft.Shape())
    if not sh.isValid() or len(sh.Solids())!=1: raise RuntimeError('loft failed validity/solid count; must not fake STEP pass')
    return sh

def run():
    A=cq.importers.importBrep(str(ROOT/'cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
    B=cq.importers.importBrep(str(ROOT/'cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()
    from r38_parts import A_proxy,B_proxy
    rows=[]
    for k,(which,tag) in enumerate(CHOSEN,1):
        _,c,L=next(x for x in CANDIDATES if x[0]==which)
        _,s,q=next(x for x in SCENES if x[0]==tag)
        path=curve(c,s,q,n=81,target=L)
        rib=loft_ribbon(path)
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN' else 0)
        parts={
          'A_UNAPPROVED_CHASSIS':A,
          'B_UNAPPROVED_CHASSIS':B.translate((0,s,q-P.z_travel)),
          'OLED_NOT_VENDOR_APPROVED':ref['OLED'],
          'OLD_DISPLAY_FPC_NOT_NEW_CROSS_CHAMBER':ref['FPC'],
          'A_BM28_CATALOGUE_PROXY':A_proxy(),
          'B_BM28_CATALOGUE_PROXY':B_proxy().translate((0,s,q-P.z_travel)),
          'R39_GHOST_FLEX_RIBBON_UNQUALIFIED_3D_PROXY':rib,
        }
        asm=cq.Assembly(name=f'R39_{k:02d}_{tag}')
        for nm,shape in parts.items():
            col=cq.Color(.97,.12,.12) if nm.startswith('R39_GHOST') else cq.Color(.2,.52,.77) if nm.startswith('B_UNAPPROVED') else cq.Color(.77,.8,.78)
            asm.add(shape,name=nm,color=col)
        filename=f'R39_{k:02d}_GHOST_{which}_{tag}.step'
        output=ROOT/'cad'/filename
        asm.save(str(output),exportType='STEP')
        imported=cq.importers.importStep(str(output)).solids().vals()
        assert len(imported)==len(parts) and all(p.isValid() for p in imported),(filename,len(imported),len(parts))
        row=dict(scene=k,pose=tag,candidate=which,step=filename,valid_solids=len(imported),
           parts=len(parts),actual_OEM_dynamic_FPC_present=False,
           ribbon_loft_solid_valid=rib.isValid(),ribbon_loft_volume_mm3=round(rib.Volume(),7),
           ribbon_actual_length_mm=round(path['numerical_length'],8),
           minimum_radius_mm=round(path['min_centerline_radius_mm'],6),
           intentional_unsafe_ghost=True,
           step_size_bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())
        rows.append(row)
        print('R39 STEP',k,filename,'OK',len(imported),'Rmin',row['minimum_radius_mm'],flush=True)
    report=dict(revision='R39 physically thickened UNQUALIFIED ribbon negative STEP scenes',
       scenarios=rows,all_intentionally_unsafe_ghost=True,real_supplier_harness_present=False,
       actual_electrical_link_implemented=False,manufacturing_go=False)
    (ROOT/'verification/R39_STEP_manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report
if __name__=='__main__':run()
