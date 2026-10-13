#!/usr/bin/env python3
"""Original dimensional envelopes, not vendor-native CAD or installation proof.
Positive envelope overlaps are clearance-reservation witnesses only. A vendor
solid may contain voids; the final PCB/FPC/stiffener/fixture is still missing.
Run from any cwd: python3 inspect_catalog_envelope.py
"""
import sys,hashlib,json,datetime,platform,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]/'baselines/fpc-r39-20261013'
sys.path.insert(0,str(BASE))
import cadquery as cq
from r25_capture import P,blk,intersection
from r24_mechanics import r21
from r25_dynamic import POSES
from r38_parts import A_FIXED_XYZ,B_LOCAL_XYZ

FILES={
 'A_unchanged':BASE/'cad/R37_A_R36_IDENTICAL.brep',
 'B_original':BASE/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep',
 'B_R38_provisional_cut':BASE/'cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep'}

def envelope(center,length,width,height):
 x,y,z=center
 return blk(x-width/2,x+width/2,y-length/2,y+length/2,z,z+height)

def run():
 t=time.monotonic()
 before={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in FILES.items()}
 ref={k:cq.importers.importBrep(str(p)).val() for k,p in FILES.items()}
 cases={'R38_header_only':[6.12,1.5,0.6],
        'receptacle_body_reservation':[6.8,1.7,0.6],
        'header_guideline_local_keepout_reservation':[7.0,1.9,0.6]}
 rows=[]
 for case,(length,width,height) in cases.items():
  a=envelope(A_FIXED_XYZ,length,width,height)
  b=envelope(B_LOCAL_XYZ,length,width,height)
  for pose,s,q in POSES:
   shift=(0,s,q-P.z_travel)
   screen=r21.r17_assembly(P,s,q,int(pose=='OPEN_SEATED'))
   objects={'A_unchanged':ref['A_unchanged'],
            'B_original':ref['B_original'].translate(shift),
            'B_R38_provisional_cut':ref['B_R38_provisional_cut'].translate(shift),
            'OLED_proxy':screen['OLED'],'display_FPC_proxy':screen['FPC']}
   shapes={'A_reservation':a,'B_reservation':b.translate(shift)}
   hits={anchor:{obj:round(float(intersection(sh,body)),9) for obj,body in objects.items()}
         for anchor,sh in shapes.items()}
   rows.append({'case':case,'pose':pose,'s_mm':s,'q_mm':q,'reservation_dims_long_short_height_mm':[length,width,height],
                'overlap_mm3':hits,'valid_reservations':all(sh.isValid() for sh in shapes.values())})
   if case=='receptacle_body_reservation' and pose in ['STOW_FULLY_INSERTED','OPEN_SEATED']:
    path=ROOT/'step'/('BM28_RESEARCH_DIMENSION_ENVELOPE_NOT_VENDOR_'+pose+'.step')
    path.parent.mkdir(exist_ok=True)
    ass=cq.Assembly(name='research_dimensional_clearance_reservations_NOT_vendor_CAD')
    for key,sh in {**objects,**shapes}.items():ass.add(sh,name=key)
    ass.save(str(path),exportType='STEP')
    imported=cq.importers.importStep(str(path)).solids().vals()
    assert len(imported)>=len(objects)+len(shapes) and all(sh.isValid() for sh in imported)
    rows[-1]['research_envelope_step']={'filename':'step/'+path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reimport_valid_solids':len(imported)}
   print(case,pose,'B vs cut',hits['B_reservation']['B_R38_provisional_cut'],'A vs A',hits['A_reservation']['A_unchanged'],flush=True)
 after={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in FILES.items()}
 assert before==after
 rec={'revision':'20261013 corrected dimension reservation screen; not vendor assembly',
      'machine':platform.node(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'case_count':len(cases),'pose_count':len(POSES),'rows':rows,'baseline_hashes_before':before,'baseline_hashes_after':after,
      'same_original_anchor_coordinate_hypotheses_used':True,
      'long_side_along_Y_is_unqualified_placement_hypothesis':True,
      'old_B_cut_untouched':True,'vendor_native_solids_used_in_this_screen':False,
      'positive_envelope_intersection_does_not_prove_native_solid_interference':True,
      'entire_footprint_FPC_stiffener_buffer_installed_stack_missing':True,
      'keepout_height_0p6_mm_is_only_lower_reservation_NOT_full_stack':True,
      'OEM_core_cut_authorization_received':False,'manufacturing_go':False,'elapsed_s':round(time.monotonic()-t,3)}
 (ROOT/'catalog_envelope_screen.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
 return rec
if __name__=='__main__':run()
