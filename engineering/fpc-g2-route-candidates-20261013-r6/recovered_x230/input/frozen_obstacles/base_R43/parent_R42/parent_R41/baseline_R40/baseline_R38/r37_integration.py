"""Real OCC fusion into R36 B shell; no assembly qualification."""
import cadquery as cq,hashlib,shutil,json
from r25_capture import ROOT,P,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r35_parts import bored_cap,pin,te_signal_envelope
from r36_parts import keeper,catalog_m08x2_screw
from r37_parts import lip,metadata

A_IN=ROOT/'cad/R36_A_R35_UNCHANGED.brep'
B_IN=ROOT/'cad/R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep'
A_OUT=ROOT/'cad/R37_A_R36_IDENTICAL.brep'
B_OUT=ROOT/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep'

def run(write=True):
    a=cq.importers.importBrep(str(A_IN)).val()
    old=cq.importers.importBrep(str(B_IN)).val()
    b=old
    row=[]
    for side in 'LR':
        hook=lip(side); cap=bored_cap(side)
        before=b.Volume()
        root_overlap=intersection(b,hook)
        b=b.fuse(hook).clean()
        row.append(dict(side=side,lip_volume_mm3=round(hook.Volume(),9),
            root_shell_overlap_mm3=round(root_overlap,9),
            new_material_mm3=round(b.Volume()-before,9),
            cap_installed_overlap_mm3=round(intersection(hook,cap),9),
            cap_forced_pull_0p05_overlap_mm3=round(intersection(hook,cap.translate((0,-.05,0))),9),
            original_pin_overlap_mm3=round(intersection(hook,pin(side)),9),
            te_gauge_overlap_mm3=round(intersection(hook,te_signal_envelope(side)),9),
            keeper_overlap_mm3=round(intersection(hook,keeper(side)),9),
            R36_M08_screw_overlap_mm3=round(intersection(hook,catalog_m08x2_screw(side)),9)))
    poses=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        shift=(0,s,q-P.z_travel)
        B=b.translate(shift)
        seen={'A_vs_B':intersection(a,B),'B_vs_OLED_proxy':intersection(B,ref['OLED']),
            'B_vs_FPC_proxy':intersection(B,ref['FPC'])}
        for side in 'LR':
            for name,part in (('cap',bored_cap(side)),('TE_catalogue_gauge',te_signal_envelope(side))):
                part=part.translate(shift)
                seen[side+'_'+name+'_A']=intersection(part,a)
                seen[side+'_'+name+'_OLED_proxy']=intersection(part,ref['OLED'])
                seen[side+'_'+name+'_FPC_proxy']=intersection(part,ref['FPC'])
        poses.append(dict(pose=tag,unexpected_occupied_intersections_mm3={k:round(v,9) for k,v in seen.items() if v>1e-7}))
        print('POSE',tag,'unexpected',len(poses[-1]['unexpected_occupied_intersections_mm3']),flush=True)
    result=dict(revision='R37 integral stop lips OCC study; NO-GO',
        source_R36_B_sha256=hashlib.sha256(B_IN.read_bytes()).hexdigest(),
        source_R36_A_sha256=hashlib.sha256(A_IN.read_bytes()).hexdigest(),
        source_R36_B_volume_mm3=round(old.Volume(),9),
        R37_B_volume_mm3=round(b.Volume(),9),
        added_B_volume_mm3=round(b.Volume()-old.Volume(),9),
        A_byte_identical=True,B_valid=b.isValid(),B_solids=len(b.Solids()),
        lips=row,reference_poses=poses,reference_pose_count=len(poses),
        no_real_flexing_assembly_analysis=True,not_a_real_qualified_connector=True,
        OEM_electronics_battery_bodies_missing=True,metadata=metadata(),manufacturing_go=False)
    if write:
        shutil.copyfile(A_IN,A_OUT)
        cq.exporters.export(b,str(B_OUT))
        for side in 'LR': cq.exporters.export(lip(side),str(ROOT/f'cad/R37_{side}_INTEGRAL_LIP_RESEARCH.brep'))
        (ROOT/'verification/R37_integration.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print('R37 integrated shell',b.isValid(),len(b.Solids()),'delta',result['added_B_volume_mm3'],flush=True)
    return result
if __name__=='__main__':run()
