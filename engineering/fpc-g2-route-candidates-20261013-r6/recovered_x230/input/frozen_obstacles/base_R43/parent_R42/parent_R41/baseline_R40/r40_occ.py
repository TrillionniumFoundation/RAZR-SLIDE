"""R40 real OpenCascade swept width x thickness envelope tests against R38 shells/OLED.
NOTE: research CAD ribbon is not actual supplier dynamic FPC. OCC-valid GHOST
STEPS are negative geometry witnesses and not evidence of a functional link.
"""
import json,hashlib,sys,time,argparse
from pathlib import Path
import cadquery as cq
import numpy as np
from r40_motion import ROOT,A,WIDTH,THICK,DOCK,SLIDE,solve,points
sys.path[:0]=[str(ROOT/'baseline_R38'),str(ROOT/'baseline_R38/baseline_R24'),str(ROOT/'baseline_R38/baseline_R24/baseline_R23/baseline_R22')]
from r25_capture import P
from r24_mechanics import r21
from r38_parts import size_proxy
POSES=[('STOW',0.,0.),('SLIDE_MID',SLIDE/2,0.),('PREDOCK',SLIDE,0.),('DOCK_HALF',SLIDE,DOCK/2),('OPEN_SEATED',SLIDE,DOCK)]
R=16.5; L=119.

def box_disjoint(a,b):
    x=a.BoundingBox();y=b.BoundingBox()
    return any(getattr(x,lo)>=getattr(y,hi)-1e-9 or getattr(y,lo)>=getattr(x,hi)-1e-9 for lo,hi in [('xmin','xmax'),('ymin','ymax'),('zmin','zmax')])

def intersectvol(a,b):
    if box_disjoint(a,b): return 0.
    return float(a.intersect(b).Volume())

def ribbon(s,q):
    sol=solve(s,q,R,L)
    assert sol['kinematic_leg_lengths_nonnegative'] and sol['bend_R15_sensitivity_pass']
    samples=points(sol,each_leg=14,around=60)
    vectors=[cq.Vector(*p) for p in samples]
    # Exact straight legs + one smooth interpolated 3D U; G1 at joins.
    # Single global spline through all vertices fails OCC pipe-shell closure;
    # independent straight segments avoid numerical overshoot and preserve the
    # intended rolling-U geometry. Curve and physical-sweep curvature are
    # only proxies until vendor tests prove this particular stack.
    leg=14;arc=60
    wire=cq.Wire.assembleEdges([
        cq.Edge.makeLine(vectors[0],vectors[leg]),
        cq.Edge.makeSpline(vectors[leg:leg+arc+1]),
        cq.Edge.makeLine(vectors[leg+arc],vectors[-1]),
    ])
    direction=vectors[1].sub(vectors[0]).normalized()
    plane=cq.Plane(origin=vectors[0],xDir=(1,0,0),normal=direction)
    shape=cq.Workplane(plane).rect(WIDTH,THICK).sweep(cq.Workplane().newObject([wire]),isFrenet=False).val()
    assert shape.isValid() and len(shape.Solids())==1
    sol['exported_composite_wire_length_mm']=round(wire.Length(),9)
    sol['exported_composite_wire_length_error_mm']=round(wire.Length()-L,9)
    return sol,shape

def run(kind='all',write=True):
    A_shell=cq.importers.importBrep(str(ROOT/'baseline_R38/cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
    B_shell=cq.importers.importBrep(str(ROOT/'baseline_R38/cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()
    results=[]
    for scene,s,q in POSES:
        t=time.monotonic(); row={'scene':scene,'s_mm':s,'q_mm':q,'R_mm_assumed':R,'nominal_L_mm':L,'STEP':None}
        try:
            sol,wire=ribbon(s,q)
            row['swept_ribbon_valid']=True
            row['STEP_spline_centerline_length_mm']=sol['exported_composite_wire_length_mm']
            row['STEP_spline_centerline_error_mm']=sol['exported_composite_wire_length_error_mm']
            row['swept_volume_mm3']=round(wire.Volume(),6)
            B_world=B_shell.translate((0,s,q-DOCK))
            ref=r21.r17_assembly(P,s,q,1 if scene=='OPEN_SEATED' else 0)
            obstacles={'A_original_protected_chassis':A_shell,'B_original_protected_chassis':B_world,
                        'OLED_unapproved_study_proxy':ref['OLED'],'legacy_display_FPC_unrelated':ref['FPC']}
            row['intersections_mm3']={name:round(intersectvol(wire,part),8) for name,part in obstacles.items()}
            row['any_specified_collision']=any(v>1e-6 for v in row['intersections_mm3'].values())
            # Compare changed anchor's catalogue-only header bbox with B pre-cut R38 shell.
            newBheader=size_proxy((sol['B_RELOCATED_LOCAL_x_mm'],15.,4.5))
            row['relocated_B_header_occupies_protected_core_mm3']=round(intersectvol(newBheader,B_shell),8)
            if scene in ('STOW','PREDOCK','OPEN_SEATED'):
                ass=cq.Assembly(name='R40_GHOST_'+scene)
                shapes={'A_R38_PROTECTED_STUDY':A_shell,
                        'B_R38_PROTECTED_STUDY':B_world,
                        'OLED_NOT_OEM':ref['OLED'],'DISPLAY_FPC_NOT_INTERCHAMBER':ref['FPC'],
                        'A_ANCHOR_RELOCATION_NOT_MOUNTED':size_proxy((A[0],70.,5.75)),
                        'B_HEADER_RELOCATED_NOT_APPROVED':newBheader.translate((0,s,q-DOCK)),
                        'GHOST_R40_MATH_ROLLING_U_CABLE':wire}
                for name,part in shapes.items():
                    ass.add(part,name=name,color=cq.Color(.93,.13,.12) if name.startswith('GHOST') else cq.Color(.54,.57,.61))
                path=ROOT/'cad'/('R40_GHOST_'+scene+'.step')
                ass.save(str(path),exportType='STEP')
                imports=cq.importers.importStep(str(path)).solids().vals()
                assert len(imports)>=len(shapes) and all(p.isValid() for p in imports)
                row['STEP']={'name':path.name,'byte_size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                             'imported_solids':len(imports),'negative_ghost':True}
        except Exception as e:
            row['swept_ribbon_valid']=False
            row['error']=type(e).__name__+': '+str(e)[:260]
        row['elapsed_s']=round(time.monotonic()-t,3)
        results.append(row)
        if write: (ROOT/'verification/R40_OCC.json').write_text(json.dumps({'complete':False,'rows':results},indent=2,ensure_ascii=False)+'\n')
        print(scene,'valid',row['swept_ribbon_valid'],'collisions',row.get('intersections_mm3'), 'error',row.get('error'), 'elapsed',row['elapsed_s'],flush=True)
    doc={'revision':'R40 inboard rolling-U cassette research; negative CAD qualification',
         'complete':True,'rows':results,'valid_ribbon_sweeps':sum(x['swept_ribbon_valid'] for x in results),
         'collision_free_valid_sweeps':sum(x['swept_ribbon_valid'] and not x['any_specified_collision'] for x in results),
         'step_count':sum(bool(x.get('STEP')) for x in results),
         'R15_only_hypothetical':True,'dynamic_vendor_material_missing':True,
         'new_B_header_not_installed':True,'physical_cassette_not_built':True,
         'manufacturing_go':False}
    if write:(ROOT/'verification/R40_OCC.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
    return doc

if __name__=='__main__':run()
