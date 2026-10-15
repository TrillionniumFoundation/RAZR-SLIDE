"""R23 B-cabin integration trial with CAD Boolean pockets and candidate fixed frames.

R23 new jaws are ideal axis-aligned swept solids.  Frame supports joined into B
are NOT mechanical fastening, material, fail-closed spring or A-key cams.
"""
from __future__ import annotations
import cadquery as cq
from pathlib import Path
import json
from r23_gate import (ROOT,R22,P,r21,blk,intersection,to_blocal,to_global,
   integrated_b_shell,carrier_lugs,independent_guard_jaws,
   independent_guard_frames,spring_axis_proxies)

POCKET_PAD=.12  # invented clearance, NOT GD&T


def bbox_cover(shapes,pad=POCKET_PAD):
    b=[x.BoundingBox() for x in shapes]
    return blk(min(x.xmin for x in b)-pad,max(x.xmax for x in b)+pad,
               min(x.ymin for x in b)-pad,max(x.ymax for x in b)+pad,
               min(x.zmin for x in b)-pad,max(x.zmax for x in b)+pad)


def moving_sweep_pockets():
    l0=carrier_lugs(0.);l1=carrier_lugs(.8)
    stop0=independent_guard_jaws(False,False)
    stop1=independent_guard_jaws(True,True)
    springs=spring_axis_proxies()
    return {
     **{f'LUG_{side}':bbox_cover([l0[f'B_R23_CARRIER_LUG_{side}'],l1[f'B_R23_CARRIER_LUG_{side}']]) for side in ('L','R')},
     **{f'JAW_{side}':bbox_cover([stop0[f'B_R23_A_KEY_JAW_{side}'],stop1[f'B_R23_A_KEY_JAW_{side}']]) for side in ('L','R')},
     **{f'SPRING_{side}':bbox_cover([springs[f'B_R23_RETURN_SPRING_{side}_ENVELOPE_ONLY']]) for side in ('L','R')}
    }


def integrate_b_shell():
    r22=integrated_b_shell()
    orig=r22['R22_b']
    b=orig
    pockets=moving_sweep_pockets()
    carved=[]
    # Boolean working solids are the whole rebuilt B hull, not just drawings.
    for port in ('STOW','OPEN'):
        for name,pocket in pockets.items():
            at=to_blocal(pocket,port)
            hit=intersection(b,at)
            b=b.cut(at).clean()
            carved.append({'port':port,'pocket':name,'mm3_taken_now':round(hit,7)})
    cutbody=b
    newframes={}
    mounted={}
    for port in ('STOW','OPEN'):
        for name,frame in independent_guard_frames().items():
            target=to_blocal(frame,port)
            mounted[f'{port}_{name}']=round(intersection(b,target),8)
            newframes[f'{port}_{name}']=target
            b=b.fuse(target).clean()
    out=dict(base_R22=orig,post_cut=cutbody,R23_b=b,pocket_removed_R22_mm3=round(orig.Volume()-cutbody.Volume(),6),
             final_body_delta_R22_mm3=round(b.Volume()-orig.Volume(),6),
             carved=carved,fixed_support_mount_overlap_mm3=mounted,
             base_valid=orig.isValid(),post_cut_valid=cutbody.isValid(),final_valid=b.isValid(),
             post_cut_one_solid=len(cutbody.Solids())==1,final_one_solid=len(b.Solids())==1,
             frame_part_count=len(newframes),R23_frames_fused_into_B_shell_candidate_only=True)
    return out


def check_full_assembly(write=True):
    integ=integrate_b_shell();b=integ['R23_b'];base=integ['base_R22']
    poses=[('STOW',0.,0.,0.),('MID_Y',P.travel/2,0.,0.),
           ('OPEN_Y_FINISHED',P.travel,0.,0.),('OPEN_Z_HALF',P.travel,P.z_travel/2,0.),
           ('OPEN_SEATED',P.travel,P.z_travel,1.)]
    rows=[];illegals=[]
    for label,s,q,leaf in poses:
        refs=r21.r17_assembly(P,s,q,leaf)
        body=b.translate(cq.Vector(0,s,-P.z_travel+q))
        against={ref:round(intersection(body,refs[ref]),8) for ref in ('OLED','FPC','A','A_fixed_skin','A_moving_leaf')}
        for ref,val in against.items():
            if val>1e-6:illegals.append((label,'B_FRAME',ref,val))
        local_items={**carrier_lugs(0.),**independent_guard_jaws(),**spring_axis_proxies()}
        for port in ('STOW','OPEN'):
            for name,sh in local_items.items():
                world=to_global(sh,port,s,q)
                with_b=round(intersection(world,body),8)
                if with_b>1e-6:illegals.append((label,name,'B',with_b))
                for ref in ('OLED','FPC','A'):
                    vol=round(intersection(world,refs[ref]),8)
                    if vol>1e-6:illegals.append((label,name,ref,vol))
        rows.append(dict(pose=label,s_mm=s,q_mm=q,nominal_OLED_A_other_overlaps_mm3=against))
    out=dict(revision='R23 B-cabin OCC and selected R21 five-pose nominal validation',
        reference_R22_valid=integ['base_valid'],B_cut_valid=integ['post_cut_valid'],
        final_B_valid=integ['final_valid'],B_post_cut_one_solid=integ['post_cut_one_solid'],
        B_final_one_solid=integ['final_one_solid'],
        model_B_volume_mm3=round(b.Volume(),6),
        B_pockets_removed_from_R22_mm3=integ['pocket_removed_R22_mm3'],
        B_net_volume_change_from_R22_mm3=integ['final_body_delta_R22_mm3'],
        frame_B_mating_intersection_before_fusing_mm3=integ['fixed_support_mount_overlap_mm3'],
        frame_parts=len(integ['fixed_support_mount_overlap_mm3']),
        cavity_operations=integ['carved'],
        selected_pose_clashes=illegals,selected_pose_clash_count=len(illegals),
        five_pose_checks=rows,
        physically_modelled_A_positive_key_wedge=False,
        plausible_spring_retention_fatigue_machinability_fea_proven=False,
        all_OEM_battery_PCB_display_details_available=False,
        mechanical_mating_300k_proven=False,manufacturing_go=False)
    if write:(ROOT/'verification'/'R23_B_integration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out,integ

if __name__=='__main__':
    x,_=check_full_assembly()
    print(json.dumps({k:v for k,v in x.items() if k not in ('five_pose_checks','cavity_operations','frame_B_mating_intersection_before_fusing_mm3')},ensure_ascii=False,indent=2))
