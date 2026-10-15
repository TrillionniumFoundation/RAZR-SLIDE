"""R41 OCC swept-ribbon layout counterexamples: measured envelope, full body collisions.
No OEM modification; all endpoints catalogue-only. Not a real FPC or CAD authorization.
"""
import json,sys,time,hashlib
from pathlib import Path
import cadquery as cq
R=Path(__file__).resolve().parent
PAR=R/'baseline_R40'
sys.path[:0]=[str(PAR),str(PAR/'baseline_R38'),str(PAR/'baseline_R38/baseline_R24'),str(PAR/'baseline_R38/baseline_R24/baseline_R23'),str(PAR/'baseline_R38/baseline_R24/baseline_R23/baseline_R22')]
from r40_occ import ribbon,intersectvol,POSES
from r40_motion import DOCK,SLIDE,A
from r25_capture import P
from r24_mechanics import r21
from r38_parts import size_proxy
A_shell=cq.importers.importBrep(str(PAR/'baseline_R38/cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
B_shell=cq.importers.importBrep(str(PAR/'baseline_R38/cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()
LAYOUTS=[('R40_original',(0.,0.,0.)),('internal_reposition',(-21.,0.,1.)),('external_clearance_tradeoff',(-21.,0.,3.))]

def run():
 out=[]; R.joinpath('verification').mkdir(exist_ok=True);R.joinpath('cad').mkdir(exist_ok=True)
 for name,s,q in POSES:
  original,shape=ribbon(s,q)
  b_world=B_shell.translate((0.,s,q-DOCK))
  ref=r21.r17_assembly(P,s,q,int(name=='OPEN_SEATED'))
  obs={'A_protected_core':A_shell,'B_protected_core':b_world,
       'OLED_research_proxy':ref['OLED'],'original_display_FPC':ref['FPC']}
  for layout,(dx,dy,dz) in LAYOUTS:
   started=time.monotonic()
   fpc=shape.translate((dx,dy,dz))
   bb=fpc.BoundingBox()
   cross={k:round(intersectvol(fpc,v),8) for k,v in obs.items()}
   # Current research upper/lower XZ envelope, NOT genuine complete OEM casing.
   xz_over=max(0.,-36.995-bb.xmin,bb.xmax-36.995,-8.2-bb.zmin,bb.zmax-7.68)
   Bheader=size_proxy((original['B_RELOCATED_LOCAL_x_mm']+dx,15.,4.5+dz))
   Aheader=size_proxy((float(A[0])+dx,70.,5.75+dz))
   a_bounding=A_shell.BoundingBox();b_bounding=B_shell.BoundingBox()
   floating_a=max(0.,Aheader.BoundingBox().zmin-a_bounding.zmax)
   floating_b=max(0.,Bheader.BoundingBox().zmin-b_bounding.zmax)
   row={'scene':name,'s_mm':s,'q_mm':q,'variant':layout,'dx_mm':dx,'dz_mm':dz,
        'centerline_nominal_length_mm':original['verified_math_length_mm'],
        'R_min_math_mm':original['min_bend_R_mm'],
        'ribbon_single_valid_solid':fpc.isValid() and len(fpc.Solids())==1,
        'ribbon_volume_mm3':round(fpc.Volume(),8),
        'ribbon_bounds_mm':{k:round(getattr(bb,k),7) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')},
        'collision_mm3':cross,'named_collision':any(v>1e-6 for v in cross.values()),
        'research_XZ_envelope_excess_mm':round(xz_over,7),
        'A_header_catalogue_overlap_A_mm3':round(intersectvol(Aheader,A_shell),8),
        'B_header_catalogue_overlap_B_mm3':round(intersectvol(Bheader,B_shell),8),
        'A_header_box_min_above_A_shell_max_mm':round(floating_a,7),
        'B_header_box_min_above_B_shell_max_mm':round(floating_b,7),
        'catalogue_only_NO_native_step':True,'header_PCB_mounted':False,
        'elapsed_s':round(time.monotonic()-started,3)}
   if layout!='R40_original' and name in ('STOW','OPEN_SEATED'):
    ass=cq.Assembly(name='R41_GHOST_'+layout+'_'+name)
    for k,v in {'A_protected_R38':A_shell,'B_protected_R38':b_world,'OLED_NOT_VENDOR':ref['OLED'],
                'R41_GHOST_SPATIAL_FPC':fpc,'A_HEADER_NOT_INSTALLED':Aheader,
                'B_HEADER_NOT_INSTALLED':Bheader.translate((0.,s,q-DOCK))}.items():ass.add(v,name=k)
    target=R/'cad'/('R41_GHOST_'+layout+'_'+name+'.step')
    ass.save(str(target),exportType='STEP')
    imported=cq.importers.importStep(str(target)).solids().vals()
    assert len(imported)>=6 and all(k.isValid() for k in imported)
    row['ghost_STEP']={'name':target.name,'valid_imported_solids':len(imported),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
   out.append(row)
   print(name,layout,'collisions',cross,'ext',xz_over,'seconds',row['elapsed_s'],flush=True)
  (R/'verification/R41_OccSweeps_PARTIAL.json').write_text(json.dumps({'complete':False,'rows':out},indent=2)+'\n')
 result={'revision':'R41 spatial X/Z relocation comparison; geometric negatives and packaging tradeoff',
         'complete':True,'variants':len(LAYOUTS),'pose_count':len(POSES),
         'total_OCC_ribbon_poses':len(out),'rows':out,
         'all_named_collision_free_and_within_research_XZ_envelope_variants':[],
         'R15_screen_NOT_vendor_life_qualification':True,
         'internal_R38_protected_core_not_authorized_for_cut':True,
         'real_FPC_BM28_PCB_mounted':False,'manufacturing_go':False}
 for v,_ in LAYOUTS:
  rows=[x for x in out if x['variant']==v]
  if all(not x['named_collision'] and x['research_XZ_envelope_excess_mm']<=1e-5 for x in rows):
   result['all_named_collision_free_and_within_research_XZ_envelope_variants'].append(v)
 (R/'verification/R41_OCC_layouts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result
if __name__=='__main__':run()
