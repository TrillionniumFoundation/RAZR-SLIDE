"""R24 OCC real Boolean candidate A keys & B double-station sweeps.

Deliberate conservative axis-aligned broad swept pockets overcarve the B rail;
actual machinability, rail pull-out, seals, fastener seats and springs unbuilt.
"""
from __future__ import annotations
import json
from pathlib import Path
import cadquery as cq
from r24_mechanics import (ROOT,R23,P,r21,blk,intersection,to_blocal,to_global,
   a_key,a_keys,a_keyed_shell,outboard_lugs,outboard_jaws,carrier_arms,
   solve_jaw_shift_by_A_contact)
from r23_integration import integrate_b_shell

CUT_PAD=.08 # made-up geometry relief, not verified GD&T

def inflated_bbox(shapes,pad=CUT_PAD):
    boxes=[shape.BoundingBox() for shape in shapes]
    return blk(min(b.xmin for b in boxes)-pad,max(b.xmax for b in boxes)+pad,
               min(b.ymin for b in boxes)-pad,max(b.ymax for b in boxes)+pad,
               min(b.zmin for b in boxes)-pad,max(b.zmax for b in boxes)+pad)

def shell_key_sweep(port,side):
    key=a_key(port,side)
    def inv_to_b(s,q):return key.translate(cq.Vector(0,-s,P.z_travel-q))
    if port=='STOW':
        # B must pass the fixed stow key throughout its first 16mm of Y motion.
        variants=[inv_to_b(s,0.) for s in (0.,15.61)]
    else:
        variants=[inv_to_b(P.travel,q) for q in (0.,P.z_travel)]
    return inflated_bbox(variants)

def module_motion_sweeps(port):
    moving=[]
    for side in 'LR':
        base=outboard_lugs(0.)[f'B_R24_OUTBOARD_LUG_{side}']
        ext=outboard_lugs(.8)[f'B_R24_OUTBOARD_LUG_{side}']
        moving.append((f'OUTBOARD_LUG_{side}',inflated_bbox([base,ext])))
        closed=outboard_jaws()[f'B_R24_OUTBOARD_JAW_{side}']
        released=outboard_jaws(dict(L=2.,R=2.))[f'B_R24_OUTBOARD_JAW_{side}']
        moving.append((f'OUTBOARD_JAW_{side}',inflated_bbox([closed,released])))
        arm0=carrier_arms(0.)[f'B_R24_ARM_{side}']
        arm1=carrier_arms(.8)[f'B_R24_ARM_{side}']
        moving.append((f'OUTBOARD_ARM_{side}',inflated_bbox([arm0,arm1])))
    return {name:to_blocal(shape,port) for name,shape in moving}

def integrate(write=True):
    base=integrate_b_shell()['R23_b']
    a0=r21.r17_assembly(P,0.,0.,0.)['A'];a=a_keyed_shell()
    b=base
    cuts=[]
    for port in ('STOW','OPEN'):
        for side in 'LR':
            cut=shell_key_sweep(port,side)
            hit=intersection(b,cut);b=b.cut(cut).clean()
            cuts.append(dict(port=port,name='KEY_SWEPT_'+side,removed_mm3=round(hit,8),
                  envelope_mm3=round(cut.Volume(),6)))
        for name,cut in module_motion_sweeps(port).items():
            hit=intersection(b,cut);b=b.cut(cut).clean()
            cuts.append(dict(port=port,name=name,removed_mm3=round(hit,8),envelope_mm3=round(cut.Volume(),6)))
    valid=dict(reference_A_valid=a0.isValid(),A_with_four_keys_valid=a.isValid(),
         A_with_four_keys_one_body=len(a.Solids())==1,
         R23_B_valid=base.isValid(),R24_cut_B_valid=b.isValid(),
         R24_cut_B_one_body=len(b.Solids())==1,
         A_added_material_mm3=round(a.Volume()-a0.Volume(),6),
         B_removed_R23_mm3=round(base.Volume()-b.Volume(),6),
         removed_per_pocket=cuts)
    return a,b,valid


def full_poses(write=True):
    a,b,global_metrics=integrate()
    rows=[];bad=[]
    poses=[('STOW',0.,0.,0.),('STOW_DEPART_1p0',1.,0.,0.),('STOW_DEPART_8',8.,0.,0.),
           ('STOW_DEPART_16',16.,0.,0.),('Y_HALF',P.travel/2,0.,0.),
           ('OPEN_PREDOCK',P.travel,0.,0.),('OPEN_Z_4p1',P.travel,4.1,0.),
           ('OPEN_Z_6p6',P.travel,6.6,0.),('OPEN_Z_7p9',P.travel,7.9,0.),
           ('OPEN_SEATED',P.travel,P.z_travel,1.)]
    # Important: actuator is a fixed PART of the A shell, not a software pose oracle.
    for name,s,q,leaf in poses:
        refs=r21.r17_assembly(P,s,q,leaf)
        bw=b.translate(cq.Vector(0,s,-P.z_travel+q))
        controlled=dict(A_R24_vs_B=intersection(a,bw),
            B_R24_vs_OLED=intersection(bw,refs['OLED']),
            B_R24_vs_FPC=intersection(bw,refs['FPC']),
            A_R24_vs_OLED=intersection(a,refs['OLED']),
            A_R24_vs_FPC=intersection(a,refs['FPC']))
        # Note A_R24_vs_OLED can include existing A prior geometry, previously clear.
        violations={k:round(v,7) for k,v in controlled.items() if v>1e-6}
        if violations:bad.append(dict(pose=name,unexpected_clashes_mm3=violations))
        rows.append(dict(pose=name,s=s,q=q,leaf=leaf,clashes={k:round(v,8) for k,v in controlled.items()}))
    # Critical: outboard key plus B shell collision no longer magically zero in
    # unmodeled q/s paths. Only 10 sampled desired path states covered.
    out=dict(revision='R24 real Boolean A key and B relief candidate',
       **global_metrics,sampled_poses=len(poses),poses=rows,
       sampled_unexpected_clashes=bad,sampled_unexpected_clash_count=len(bad),
       conditional_on_oversize_key_pocket_overcarve=True,
       true_B_rail_shear_and_bending_not_tested=True,
       A_key_secure_mechanical_latching_not_built=True,
       actual_A_B_OEM_parts_absent=True,real_current_and_300k_unproved=True,
       manufacturing_go=False)
    if write:(ROOT/'verification'/'R24_integration.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    return out,(a,b)

if __name__=='__main__':
    x,_=full_poses()
    print(json.dumps({k:v for k,v in x.items() if k not in ('removed_per_pocket','poses')},ensure_ascii=False,indent=2))
