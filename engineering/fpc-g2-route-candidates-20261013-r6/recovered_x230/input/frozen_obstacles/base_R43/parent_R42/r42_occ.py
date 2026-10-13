"""R42 two *separate* FPC ribbons and floating mid-speed junction GHOST, OpenCascade.
The interim carrier has no bearings, actuator, flexible electrical junction or secure mount.
All R38 protected bodies are read-only and must not be trimmed for a 'successful' result.
"""
from pathlib import Path
import json, hashlib, sys, time, math
import cadquery as cq
import numpy as np
ROOT=Path(__file__).resolve().parent
PR=ROOT/'parent_R41/baseline_R40'
sys.path[:0]=[str(ROOT),str(PR),str(PR/'baseline_R38'),str(PR/'baseline_R38/baseline_R24'),str(PR/'baseline_R38/baseline_R24/baseline_R23'),str(PR/'baseline_R38/baseline_R24/baseline_R23/baseline_R22')]
from r42_double_loop import solve, centerline, RADIUS, FPC_WIDTH, FPC_THICK, SLIDE, DOCK
from r40_occ import intersectvol
from r25_capture import P
from r24_mechanics import r21
POSES=[('STOW',0.,0.),('SLIDE_Q1',SLIDE/4,0.),('MID',SLIDE/2,0.),('SLIDE_Q3',3*SLIDE/4,0.),('PREDOCK',SLIDE,0.),('DOCK_Q1',SLIDE,DOCK/4),('DOCK_HALF',SLIDE,DOCK/2),('DOCK_Q3',SLIDE,3*DOCK/4),('OPEN_SEATED',SLIDE,DOCK)]
A_SHELL=cq.importers.importBrep(str(PR/'baseline_R38/cad/R38_A_R37_BYTE_IDENTICAL.brep')).val()
B_SHELL=cq.importers.importBrep(str(PR/'baseline_R38/cad/R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep')).val()

def make_ribbon(section):
    p,(leg,narc)=centerline(section,leg_samples=12,arc_samples=70)
    vv=[cq.Vector(*(float(w) for w in pos)) for pos in p]
    wire=cq.Wire.assembleEdges([cq.Edge.makeLine(vv[0],vv[leg]),
         cq.Edge.makeSpline(vv[leg:leg+narc+1]),cq.Edge.makeLine(vv[leg+narc],vv[-1])])
    direction=vv[1].sub(vv[0]).normalized()
    plane=cq.Plane(origin=vv[0],xDir=(1,0,0),normal=direction)
    shape=cq.Workplane(plane).rect(FPC_WIDTH,FPC_THICK).sweep(cq.Workplane().newObject([wire]),isFrenet=False).val()
    assert shape.isValid() and len(shape.Solids())==1,("ribbon invalid",section)
    return shape,wire

def carriage(c):
    # 4 x 3 x .6 mm STUDY package ONLY; anchors on one side would need real pads.
    return cq.Workplane('XY').box(4.,3.,.6).translate(tuple(float(x) for x in c)).val()

def do_pose(name,s,q,export=True):
    started=time.monotonic(); m=solve(s,q);b_world=B_SHELL.translate((0,s,q-DOCK))
    ref=r21.r17_assembly(P,s,q,int(name=='OPEN_SEATED'))
    protected={'A_R38_PROTECTED':A_SHELL,'B_R38_PROTECTED':b_world,
            'OLED_NO_VENDOR':ref['OLED'],'DISPLAY_FPC_NOT_CROSS_CHAMBER':ref['FPC']}
    shapes={}; path_measures={}
    for k in ('section_1','section_2'):
        f,center=make_ribbon(m[k]);shapes[k]=f
        path_measures[k]={'nominal_centerline_length_mm':m[k]['total_length_mm'],
          'swept_wire_length_mm':float(center.Length()),
          'wire_vs_analytic_difference_mm':float(center.Length()-m[k]['total_length_mm']),
          'volume_mm3':float(f.Volume()),'single_valid_solid':True}
    shapes['GHOST_MID_CARRIAGE_WITHOUT_MOUNTS']=carriage(m['C_MOVING_JUNCTION'])
    c={} 
    for part_name,sh in shapes.items():
        c[part_name]={obs:round(intersectvol(sh,other),8) for obs,other in protected.items()}
    # Note the two sections meet at C; their termination may overlap at C, but
    # a real interposer mechanically/electrically joining them is NOT built.
    interflex=intersectvol(shapes['section_1'],shapes['section_2'])
    bounds={}
    for part_name,sh in shapes.items():
        bb=sh.BoundingBox()
        bounds[part_name]={k:round(getattr(bb,k),6) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')}
    maxover=max(max(0,-36.995-b['xmin'],b['xmax']-36.995,-8.20-b['zmin'],b['zmax']-7.68) for b in bounds.values())
    row={'stage':name,'s_mm':s,'q_mm':q,'analytic':m,'wire_measures':path_measures,
         'collisions_with_original_protected_bodies_mm3':c,
         'collision_count_above_1e_minus6':sum(v>1e-6 for x in c.values() for v in x.values()),
         'two_ribbons_nominal_intersection_mm3':round(interflex,8),
         'component_bbox':bounds,'research_XZ_envelope_excess_mm':round(maxover,7),
         'GHOST_carriage_not_a_real_moving_stage':True,
         'electrical_interposer_absent':True,
         'copper_lifetime_unqualified':True,
         'no_OEM_core_cuts':True}
    if export and name in ('STOW','PREDOCK','OPEN_SEATED'):
        ass=cq.Assembly(name='R42_GHOST_'+name)
        entries={**protected,'GHOST_FLEX_A_TO_FLOATING_C':shapes['section_1'],
                 'GHOST_FLEX_C_TO_B':shapes['section_2'],
                 'GHOST_NOT_BUILT_HALF_RATE_CARRIER':shapes['GHOST_MID_CARRIAGE_WITHOUT_MOUNTS']}
        for k,v in entries.items():ass.add(v,name=k)
        path=ROOT/'cad'/('R42_GHOST_TWO_FLEXES_'+name+'.step')
        ass.save(str(path),exportType='STEP')
        imported=cq.importers.importStep(str(path)).solids().vals()
        assert len(imported)>=7 and all(sh.isValid() for sh in imported)
        row['STEP_reimport']={'filename':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'valid_solids':len(imported)}
    row['elapsed_s']=round(time.monotonic()-started,3)
    return row

def run():
    result={'revision':'R42 two separated flex loops and unbuilt half-rate junction',
            'complete':False,'ghost_poses':[],
            'no_original_OEM_research_Brep_cut':True,'manufacturing_go':False}
    (ROOT/'verification').mkdir(exist_ok=True);(ROOT/'cad').mkdir(exist_ok=True)
    for name,s,q in POSES:
        row=do_pose(name,s,q)
        result['ghost_poses'].append(row)
        (ROOT/'verification/R42_OCC_progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(name,'collision count',row['collision_count_above_1e_minus6'],
              'vols',row['collisions_with_original_protected_bodies_mm3'],'elapsed',row['elapsed_s'],flush=True)
    result['complete']=True
    result['poses_with_protected_obstruction']=sum(row['collision_count_above_1e_minus6']>0 for row in result['ghost_poses'])
    result['all_sampled_poses_collision_free']=result['poses_with_protected_obstruction']==0
    result['tested_new_topology_candidate_go']=False # no electrical interposer/OEM clearance even with 0 overlap
    (ROOT/'verification/R42_OCC_two_flexes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
if __name__=='__main__':run()
