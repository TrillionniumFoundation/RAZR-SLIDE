"""Explicitly REJECTED competing TE catalogue envelope bay.

Only a nominal AABB. Enlarging a channel until the box fits does not establish
mount pads, shear path, protective lid, valid circuit, USB SI, durability or
available supplier part. This rejected BRep must not be called production CAD.
"""
from __future__ import annotations
import json
import cadquery as cq
from r25_capture import ROOT,P,blk,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r33_parts import catalogue_TE_box,keeper_pin
from r32_integration import MATERIAL_WITNESSES

TE_REAR_Y_SHIFT=.15
CLEARANCE=.04

def enlarged_box(side):
    te=catalogue_TE_box(side).translate((0,TE_REAR_Y_SHIFT,0))
    bb=te.BoundingBox()
    return blk(bb.xmin-CLEARANCE,bb.xmax+CLEARANCE,
               bb.ymin-CLEARANCE,bb.ymax+CLEARANCE,
               bb.zmin-CLEARANCE,bb.zmax+CLEARANCE)

def run(write=True):
    A=cq.importers.importBrep(str(ROOT/'cad/R33_A_R32_BYTE_IDENTICAL.brep')).val()
    B0=cq.importers.importBrep(str(ROOT/'cad/R33_B_BILATERAL_PIN_PORTS.brep')).val()
    B=B0; cuts=[]
    for side in 'LR':
        old=B.Volume()
        B=B.cut(enlarged_box(side)).clean()
        cuts.append(dict(side=side,removed_mm3=round(old-B.Volume(),9),
             still_single_solid=B.isValid() and len(B.Solids())==1))
    f=[]
    for name,limits in MATERIAL_WITNESSES.items():
        b=blk(*limits)
        f.append(dict(cell=name,R33_rejected_B_final_occupancy=round(intersection(B,b)/b.Volume(),7)))
    collisions=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        trans=(0,s,q-P.z_travel)
        for side in 'LR':
            te=catalogue_TE_box(side).translate((0,TE_REAR_Y_SHIFT,0))
            gl=te.translate(trans)
            collisions.append(dict(pose=tag,side=side,
                A_clash_mm3=round(intersection(gl,A),9),
                OLED_reference_clash_mm3=round(intersection(gl,ref['OLED']),9),
                FPC_reference_clash_mm3=round(intersection(gl,ref['FPC']),9),
                keeper_pin_clash_mm3=round(intersection(te,keeper_pin(side)),9),
                geometry_box_B_clash_after_cut_mm3=round(intersection(te,B),9)))
        print('R33 REJECTED ENLARGED BAY',tag,flush=True)
    d=dict(revision='R33 REJECTED: enlarging nominal B cassette to place TE catalogue AABB',
        source='TE public 2199001-1 signal spring contact nominal envelope, not supplier STEP',
        rearward_shift_y_mm=TE_REAR_Y_SHIFT,
        radial_clearance_proxy_mm=CLEARANCE,
        two_cut_operations=cuts,
        B_after_rejected_bay_valid_single=B.isValid() and len(B.Solids())==1,
        removed_total_B_mm3=round(B0.Volume()-B.Volume(),9),
        witness_fraction_vs_R32_material_cells=f,
        pose_checks=collisions,
        keeper_conflicts=sum(x['keeper_pin_clash_mm3']>1e-8 for x in collisions),
        A_OLED_FPC_collision_count=sum(x[k]>1e-8 for x in collisions for k in ('A_clash_mm3','OLED_reference_clash_mm3','FPC_reference_clash_mm3')),
        electrical_pad_FPC_stackup_and_fasteners_NOT_designed=True,
        supplier_STEP_NOT_retrieved=True,
        enlarged_bay_is_REJECTED_due_to_retainer_and_structural_safety_gaps=True,
        original_R33_B_cassette_bay_retained_as_non_electrical_research_only=True,
        manufacturing_go=False)
    if write:
        cq.exporters.export(B,str(ROOT/'cad/R33_B_TE_LARGER_BAY_REJECTED.brep'))
        (ROOT/'verification/R33_expansion_rejected.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print('R33 REJECTED TE B CUT',d['removed_total_B_mm3'], 'pin clashes',d['keeper_conflicts'],flush=True)
    return d
if __name__=='__main__':run()
