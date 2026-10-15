#!/usr/bin/env python3
"""R44 concept-only single XY rear service loop. Never edits protected OEM research bodies.

No real terminals, rear cover, power wiring, load-bearing cassette, or supplier bend license.
Both A/B endpoints are exterior GHOST positions; B end follows q normal docking motion.
A clean OCC intersection is ONLY a conditional spatial screen, not a feasible circuit.
"""
import json,sys,time,hashlib
from pathlib import Path
import cadquery as cq
import numpy as np
ROOT=Path(__file__).resolve().parent
R42=ROOT/'base_R43/parent_R42'
sys.path[:0]=[str(R42),str(R42/'parent_R41/baseline_R40'),str(R42/'parent_R41/baseline_R40/baseline_R38')]
from r42_double_loop import one_loop, centerline, arc_calcs
from r42_occ import A_SHELL, B_SHELL, make_ribbon
from r25_capture import P
from r24_mechanics import r21
from r40_occ import intersectvol
R=16.5
L=120.
FPC_W=1.2;FPC_T=0.15
SLIDE=79.75; DOCK=8.2
STAGES=[('STOW',0.,0.),('SLIDE_Q1',SLIDE/4,0.),('MID',SLIDE/2,0.),('SLIDE_Q3',3*SLIDE/4,0.),('PREDOCK',SLIDE,0.),('DOCK_Q1',SLIDE,DOCK/4),('DOCK_HALF',SLIDE,DOCK/2),('DOCK_Q3',SLIDE,3*DOCK/4),('OPEN_SEATED',SLIDE,DOCK)]
PROTECT=('A_R38_CORE','B_R38_CORE','OLED_PROXY','DISPLAY_FPC_PROXY')
def ribbon_at(s,q,z0,b_follows_q=True):
    a=np.array([R,70.,z0],dtype=float)
    b=np.array([-R,15.+s,z0+q if b_follows_q else z0],dtype=float)
    section=one_loop(a,b,L,r=R,orientation=1)
    sh,wire=make_ribbon(section)
    return sh,section,float(wire.Length())
def protected(s,q):
    ref=r21.r17_assembly(P,s,q,int(q==DOCK))
    return {'A_R38_CORE':A_SHELL,'B_R38_CORE':B_SHELL.translate((0,s,q-DOCK)),
            'OLED_PROXY':ref['OLED'],'DISPLAY_FPC_PROXY':ref['FPC']}
def run():
    start=time.monotonic(); outdir=ROOT/'evidence';outdir.mkdir(exist_ok=True)
    # Externally exposed back-bypass (not within original Z bound) and a constrained alternative
    options={'REAR_Z_MINUS_8_7_B_FOLLOWS_Q':(-8.7,True),
             'NEAR_REAR_INSIDE_BUDGET_Z_MINUS_7_95':(-7.95,True),
             'NEAR_ORIGINAL_REAR_Z_MINUS_8_15':(-8.15,True),
             'REAR_Z_MINUS_8_7_DECOUPLED_B':(-8.7,False)}
    all_rows=[]
    for option,(z0,follow) in options.items():
        for name,s,q in STAGES:
            sh,sec,wirelen=ribbon_at(s,q,z0,follow)
            obs=protected(s,q)
            vol={k:round(float(intersectvol(sh,b)),8) for k,b in obs.items()}
            bb=sh.BoundingBox()
            maxy=94.25+s
            row={'branch':option,'pose':name,'s_mm':s,'q_mm':q,'hypothetical_a_endpoint_xyz_mm':sec['start'],
                 'hypothetical_b_endpoint_xyz_mm':sec['end'],'length_mm':L,'wire_length_mm':round(wirelen,7),
                 'minimum_centerline_curvature_radius_mm':round(sec['minimum_calculated_centerline_radius_mm'],6),
                 'straight_A_mm':round(sec['leg_A_mm'],6),'straight_B_mm':round(sec['leg_B_mm'],6),
                 'volume_overlap_mm3':vol,
                 'research_z_envelope_excess_below_minus_8p2_mm':round(max(0.,-8.2-bb.zmin),6),
                 'research_y_excess_beyond_case_mm':round(max(0.,bb.ymax-maxy),6),
                 'A_exterior_standoff_to_core_zmin_mm':round(-3.4-z0,5),
                 'no_real_terminal_or_mount':True,
                 'not_an_integrated_cable':True}
            if option in ('REAR_Z_MINUS_8_7_B_FOLLOWS_Q','NEAR_REAR_INSIDE_BUDGET_Z_MINUS_7_95') and name in ('STOW','PREDOCK','OPEN_SEATED'):
                ass=cq.Assembly(name='R44_GHOST_OUT_OF_ENVELOPE_'+name)
                for k,obs_shape in {**obs,'REAR_BYPASS_UNTERMINATED_FPC':sh}.items():ass.add(obs_shape,name=k)
                path=ROOT/'cad'/('R44_GHOST_'+option+'_'+name+'.step'); path.parent.mkdir(exist_ok=True)
                ass.save(str(path),exportType='STEP')
                shapes=cq.importers.importStep(str(path)).solids().vals()
                assert len(shapes)>=5 and all(x.isValid() for x in shapes)
                row['ghost_STEP']={'filename':path.name,'valid_solids':len(shapes),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            all_rows.append(row)
            print(option,name,'overlap',vol,'Zout',row['research_z_envelope_excess_below_minus_8p2_mm'],flush=True)
    rec={'revision':'R44 alternative single-section REAR BYPASS XY loop OCC research negative/conditional screen',
         'source':'immutable R43 base includes R42 OCC A/B protect and R21 OLED proxy',
         'no_core_or_display_proxy_was_cut':True,'radius_assumption_mm':R,'wire_width_mm':FPC_W,'wire_thickness_mm':FPC_T,
         'constant_centerline_length_mm':L,'A_B_finished_design_and_OEM_3D_missing':True,
         'options':options,'rows':all_rows,'poses_per_branch':len(STAGES),
         'tested_poses_count':len(all_rows),
         'number_pose_branches_with_core_penetration':sum(any(row['volume_overlap_mm3'][k]>1e-6 for k in PROTECT[:2]) for row in all_rows),
         'max_abs_wire_length_error_mm':max(abs(row['wire_length_mm']-L) for row in all_rows),
         'actual_A_terminal_cannot_reach_unapproved_exterior_without_feedthrough':True,
         'q_docking_b_termination_needs_hardware_stress_relief':True,
         'zero_volume_overlap_does_not_authorize_thickness_increase':True,
         'wire_bend_life_unproven':True,
         'candidate_go':False,'manufacturing_go':False,'elapsed_s':round(time.monotonic()-start,3)}
    (outdir/'R44_rear_bypass_OCC.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:rec[k] for k in ('tested_poses_count','number_pose_branches_with_core_penetration','elapsed_s')}),flush=True)
    return rec
if __name__=='__main__':run()
