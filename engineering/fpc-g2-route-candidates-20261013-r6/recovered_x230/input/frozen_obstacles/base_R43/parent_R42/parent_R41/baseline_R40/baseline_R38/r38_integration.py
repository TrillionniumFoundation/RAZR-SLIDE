"""R38: local catalogue-header research placement in the ORIGINAL R37 reference.

A/B are internal chassis study BReps, not definitive finished housing CAD.
Cutting the B protective solid is a HARD DESIGN BLOCKER until OEM electronics
and enclosure structure are known; this does not create a production cavity.
No functional cross-compartment cable is modeled.
"""
import json,hashlib,shutil
import cadquery as cq
from r25_capture import ROOT,P,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r38_parts import A_proxy,B_proxy,old_outboard_placement_proxy,constant_z_u_loop_budget,SKU,CL_NO,SOURCE

A_BASE=ROOT/'cad/R37_A_R36_IDENTICAL.brep'
B_BASE=ROOT/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep'
A_OUT=ROOT/'cad/R38_A_R37_BYTE_IDENTICAL.brep'
B_OUT=ROOT/'cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep'

def run(write=True):
    A=cq.importers.importBrep(str(A_BASE)).val()
    B0=cq.importers.importBrep(str(B_BASE)).val()
    a,b=A_proxy(),B_proxy()
    old=old_outboard_placement_proxy()
    old_intersect=intersection(old,B0)
    gross_intersect=intersection(B0,b)
    provisional=B0.cut(b).clean()
    assert provisional.isValid() and len(provisional.Solids())==1
    poses=[]; old_poses=[]
    for tag,s,q in POSES:
        ref=r21.r17_assembly(P,s,q,1 if tag=='OPEN_SEATED' else 0)
        tr=(0,s,q-P.z_travel)
        bm=b.translate(tr);B=provisional.translate(tr)
        parts={
          'A_header_vs_A_chassis':intersection(a,A),
          'B_header_vs_provisional_B_chassis':intersection(bm,B),
          'A_header_vs_B_chassis':intersection(a,B),
          'B_header_vs_A_chassis':intersection(bm,A),
          'A_header_vs_OLED_proxy':intersection(a,ref['OLED']),
          'B_header_vs_OLED_proxy':intersection(bm,ref['OLED']),
          'A_header_vs_FPC_proxy':intersection(a,ref['FPC']),
          'B_header_vs_FPC_proxy':intersection(bm,ref['FPC']),
        }
        poses.append(dict(pose=tag,s_mm=s,q_mm=q,
                          intersections_mm3={k:round(v,8) for k,v in parts.items()},
                          specified_named_interference=any(v>1e-7 for v in parts.values())))
        if tag in ['STOW_FULLY_INSERTED','OPEN_SEATED']:
            old_sh=old.translate(tr)
            old_poses.append(dict(pose=tag,
              old_outboard_header_vs_A_mm3=round(intersection(old_sh,A),8),
              old_outboard_header_vs_R37_B_unmodified_mm3=round(old_intersect,8)))
        print('R38 pose',tag,'named candidate clashes',poses[-1]['specified_named_interference'],flush=True)
    result={
      'revision':'R38 CHANGE TO FIXED-MATED HYBRID FPC TERMINATORS (UNQUALIFIED)',
      'vendor':{'sku':SKU,'cl_number':CL_NO,'product_url':SOURCE,'native_VENDOR_STEP_downloaded_and_imported':False,
                'only_catalogue_bounding_proxy':True,'mated_receptacle_or_actual_flex_tail_drawings_imported':False,
                'mating_cycles_max_published':10,'mating_occurs_each_slide_in_proposed_architecture':False},
      'R37_original_A_SHA256':hashlib.sha256(A_BASE.read_bytes()).hexdigest(),
      'R37_original_B_SHA256':hashlib.sha256(B_BASE.read_bytes()).hexdigest(),
      'A_original_bytes_unchanged':True,
      'B_original_volume_mm3':round(B0.Volume(),8),
      'B_provisional_volume_mm3':round(provisional.Volume(),8),
      'B_protected_volume_cut_mm3':round(B0.Volume()-provisional.Volume(),8),
      'B_provisional_valid_single_solid':provisional.isValid() and len(provisional.Solids())==1,
      'B_OEM_BOM_clearance_known':False,'B_material_removed_from_unapproved_protected_core':True,
      'A_header_gross_vs_A_original_mm3':round(intersection(a,A),8),
      'B_header_gross_vs_B_original_mm3':round(gross_intersect,8),
      'reference_poses':poses,'reference_pose_count':len(poses),
      'old_R37_mini_contact_bay_header_direct_substitution':old_poses,
      'simple_U_bend_feasibility':constant_z_u_loop_budget(),
      'stow_and_open_connector_contacts_NOT_electrically_linked_in_CAD':True,
      'true_two_compartment_flex_service_loop_generated':False,
      'no_actual_power_isolation_circuit':True,
      'legacy_mechanical_fault_36_of_64_unresolved':True,
      'legacy_PCB_single_bypass_categories_unresolved':3,
      'OLED_OEM_data_missing':True,'finished_A_B_equal_cover_sizes_unverified':True,
      'manufacturing_go':False,
    }
    if write:
        shutil.copyfile(A_BASE,A_OUT)
        cq.exporters.export(provisional,str(B_OUT))
        for name,shape in [('A',a),('B',b)]:
            cq.exporters.export(shape,str(ROOT/'cad'/f'R38_{name}_BM28_CATALOGUE_BBOX_NOT_VENDOR_STEP.brep'))
        (ROOT/'verification/R38_integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

if __name__=='__main__':run()
