#!/usr/bin/env python3
"""One next endpoint gate: small un-routed mount and moved-A G2 route.

This is an original dimensional/locating study, not a fabricated PCBA or an
approved real FPC clamp. Native successes never fill missing supplier fields.
"""
from pathlib import Path
import hashlib,json,math,sys,time,traceback
sys.dont_write_bytecode=True
import cadquery as cq
import numpy as np
from endpoint_relocation import ROOT,R6,POSES,box,sha,write,participant,pairs,failures,free,export,inside_budget,full_payload
from actual_obstacle_and_jacobian import obstacle_factory,regularity
import geometry_candidates as g
from cad_preflight import route_wire,pure_positive_single_solid,sweep_case

AX,AY,AZ=24.,85.,5.35
def moved_segments(c,s,q,fold):
    xa,xb=c.cx_mm-c.radius_mm,c.cx_mm+c.radius_mm
    yb,zb=g.YB0+s,g.ZB0+q
    z=c.alpha*AZ+(1-c.alpha)*(g.Z_BAY_STUDY+q-g.DOCK)
    A,B=np.array([AX,AY,AZ]),np.array([g.XC,yb,zb])
    a0,b1=np.array([xa,AY,AZ]),np.array([xb,yb,zb])
    a=g.Segment('A_STUB','line',{'start':A,'end':a0})
    al=g.Segment('A_LEG','leg',{'start':a0,'dy':fold-AY,'dz':z-AZ})
    arc=g.Segment('U_ARC','arc',{'radius':c.radius_mm,'cx':c.cx_mm,'fold_y':fold,'z':z})
    bl=g.Segment('B_LEG','leg',{'start':np.array([xb,fold,z]),'dy':yb-fold,'dz':zb-z})
    b=g.Segment('B_STUB','line',{'start':b1,'end':B})
    at=1-c.dA_mm/(AX-xa);als=c.dA_mm/(fold-AY);ale=1-c.dJ_mm/(fold-AY)
    bs=c.dJ_mm/(fold-yb);be=1-c.dB_mm/(fold-yb);bt=c.dB_mm/(xb-g.XC);arc_t=math.asin(c.dJ_mm/c.radius_mm)/math.pi
    return [g._trim(a,0,at),g._blend('A_CORNER_G2',a,at,al,als,c.dA_mm),g._trim(al,als,ale),
      g._blend('A_LEG_U_G2',al,ale,arc,arc_t,c.dJ_mm),g._trim(arc,arc_t,1-arc_t),
      g._blend('U_B_LEG_G2',arc,1-arc_t,bl,bs,c.dJ_mm),g._trim(bl,bs,be),
      g._blend('B_CORNER_G2',bl,be,b,bt,c.dB_mm),g._trim(b,bt,1)]
def mini_mount():
    # Original proposed 9x8 mm substrates, without copper, actual pad layout,
    # parts or FPC. These dimensions do NOT resize the frozen routed R2 PCB.
    holes=[(-3.75,-2.75),(3.75,-2.75),(-3.75,2.75)]
    def cyl(x,y,r,z0,z1):return cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x+28.5,y+85,z0))
    base=box(23.5,33.5,80.5,89.5,2.4,3.0)
    for x,y in holes:base=base.fuse(cyl(x,y,.3,2.4,5.5))
    for x in [24.,32.]:
        for y in [81.5,87.5]:base=base.fuse(box(x,x+1,y,y+1,3.,3.3))
    def substrate(z0,z1):
        b=box(24.,33.,81.,89.,z0,z1)
        for x,y in holes:b=b.cut(cyl(x,y,.4,z0-.1,z1+.1))
        return b.clean()
    return {'NEW_UNQUALIFIED_LOCATING_BASE':base.clean(),'NEW_UNROUTED_DS_SUBSTRATE':substrate(3.3,4.1),
      'NEW_UNROUTED_DP_SUBSTRATE':substrate(4.7,5.5),
      'BM28_24_DIMENSION_RESERVATION_NOT_VENDOR':box(25.1,31.9,84.15,85.85,4.1,4.7),
      'CONDITIONAL_56UM_STRAIGHT_EXIT_GUIDE':box(21.,24.,84.4,85.6,AZ-.028,AZ+.028)}
def run():
    start=time.monotonic();factory,_=obstacle_factory();before={str(p.relative_to(R6)):sha(p) for p in sorted(R6.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    own_before={f:sha(ROOT/f) for f in ['corner_bay_followup.py','endpoint_relocation.py']};mount=mini_mount();mount_rows=[]
    for pose,s,q in POSES:
        ob=factory(s,q);pc=pairs(mount,ob);mount_rows.append({'pose':pose,'pairs':pc,'positive_or_rejected':failures(pc),'sampled_obstacle_clear':free(pc),
          'all_parts_within_original_A_research_proxy_bbox':all(inside_budget(b,participant(ob['A_R38_CORE'])['bounds_mm']) for b in mount.values())})
    # Also retain mounting self-interference rather than testing only phones.
    own_pairs={}
    for i,(a,ap) in enumerate(mount.items()):
        for b,bp in list(mount.items())[i+1:]:own_pairs[a+'__'+b]=pairs({a:ap},{b:bp})[a][b]
    mount_export=export(mount,'CONDITIONAL_MINI_MOUNT_NOT_ROUTED_PCBA.step')
    write(ROOT/'corner_bay_mount_report.json',{'mount_rows':mount_rows,'self_pairs':own_pairs,'export':mount_export,
      '9x8mm_substrates_are_new_unrouted_proposal':True,'frozen_R2_40x36_routed_boards_resized':False,'BM28_real_installed_stack_verified':False,
      'actual_FPC_clamp_or_reinforcement_or_artwork_included':False,'real_equal_finished_cabin_budget_known':False,'large_A_battery_space_budget_verified':False,
      'manufacturing_go':False})
    # Replace geometry only inside this fresh experiment process. The frozen
    # R6 source bytes are unchanged; old A is not treated as a user constraint.
    old_globals={'YA':g.YA,'ZA':g.ZA,'segment_function':'geometry_candidates._segments'}
    g.YA=AY;g.ZA=AZ;g._segments=moved_segments
    cfg=g.Config(target_length_mm=148.20738578362864,dA_mm=1.,dB_mm=1.,dJ_mm=.25)
    rows=[]
    for pose,s,q in POSES:
        row={'pose':pose,'A_moved_endpoint_xyz_mm':[AX,AY,AZ],'B_unchanged_endpoint_xyz_mm':[g.XC,g.YB0+s,g.ZB0+q],
          'nominal_width_mm':1.2,'unprocessed_conditional_thickness_mm':.056,'finite_body_accepted':False,'specific_finished_FPC_received':False,
          'candidate_route_accepted':False,'manufacturing_go':False};body=None
        try:
            curve=g.build_candidate(cfg,s,q);wire=route_wire(curve)
            row['fixed_material_length_mm']=curve.target;row['actual_path_length_mm']=wire.Length();row['G2_joint_errors']=curve.joint_errors()
            row['minimum_screened_radius_mm'],row['radius_witness']=curve.min_radius()
            path=ROOT/'cad'/('MOVED_A_'+pose+'_PATH_ONLY.step');cq.exporters.export(wire,str(path))
            row['path_only_STEP']={'path':str(path.relative_to(ROOT)),'sha256':sha(path),'manufacturing_solid':False}
            pts,_,_=curve.evaluate(np.linspace(0,curve.target,401));maxY=max(93.9,94.25+s)
            row['actual_sampled_centerline_union_proxy_bbox_y_excess_mm']=max(0.,float(pts[:,1].max())-maxY)
            row['centerline_points_only_are_finite_envelope_certificate']=False
            row['conditional_Bishop_width_Y_local_J']=regularity(curve,(0.,1.,0.),99)
            curve,wire,body=sweep_case(cfg,s,q,(0.,1.,0.));row['full_finite_payload_guard']=pure_positive_single_solid(body);row['finite_body_accepted']=True
            row['pairs']=pairs({'NEW_MOVED_A_FINITE_FPC':body},factory(s,q));row['positive_or_rejected']=failures(row['pairs'])
            row['finite_swept_union_proxy_y_excess_mm']=max(0.,body.BoundingBox().ymax-maxY)
            p=ROOT/'cad'/('REJECTED_MOVED_A_'+pose+'_FINITE_56UM.step');cq.exporters.export(body,str(p));loaded=cq.importers.importStep(str(p))
            if len(loaded.vals())!=1:raise ValueError('multiple finite import payloads')
            row['finite_reimport_guard']=pure_positive_single_solid(loaded.val());row['finite_STEP']={'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
        except Exception as exc:
            row['actual_exception']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
            if body is not None:
                p=ROOT/'cad'/('REJECTED_MOVED_A_'+pose+'_RAW_PAYLOAD.brep');cq.exporters.export(body,str(p));row['actual_rejected_BREP']={'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
        rows.append(row);print('moved A actual route',pose,'bodyvalid',row['finite_body_accepted'],'failures',row.get('positive_or_rejected'),flush=True)
    after={str(p.relative_to(R6)):sha(p) for p in sorted(R6.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};own_after={f:sha(ROOT/f) for f in own_before}
    if before!=after or own_before!=own_after:raise ValueError('input source bytes changed')
    write(ROOT/'corner_bay_followup_receipt.json',{'host':__import__('platform').node(),'CadQuery':cq.__version__,'own_sources_before':own_before,'own_sources_after':own_after,
      'frozen_R6_sources_unchanged':before==after,'frozen_R6_source_hashes':before,'memory_only_old_geometry_parameters':old_globals,
      'new_A_coordinate_is_explicit_research_proposal_not_controlled_clamp':True,'B_motion_and_B_coordinate_not_changed':True,
      'mini_mount_pose_count':3,'mini_mount_clear_in_all_three_sampled_poses':all(r['sampled_obstacle_clear'] for r in mount_rows),
      'new_moved_A_route_pose_count':3,'rows':rows,'candidate_route_accepted':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start})
if __name__=='__main__':run()
