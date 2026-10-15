#!/usr/bin/env python3
"""New G2 candidates against unchanged historical A/B/OLED/rail proxies.

Whole finite sweeps, full-payload guards, full-motion fixed material center
queries and conditional Bishop local-section regularity are distinct evidence.
None of the public nominal 56um layer cases is a specified finished FPC.
"""
from pathlib import Path
import argparse,hashlib,json,math,platform,sys,time,traceback
import numpy as np
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt
from geometry_candidates import Config,build_candidate,poses
from cad_preflight import sweep_case,pure_positive_single_solid

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def unit(v):
    n=np.linalg.norm(v)
    if not math.isfinite(n) or n<1e-12:raise ValueError('undefined Bishop director')
    return v/n

def obstacle_factory():
    source=ROOT/'frozen_obstacles';manifest=json.loads((source/'minimal_source_manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if sha(source/name)!=digest:raise ValueError('frozen obstacle source changed: '+name)
    sys.path.insert(0,str(source))
    from r44_rear_bypass import protected,P
    from r35_parts import bored_cap,pin,inboard_rail,arm_guide,te_signal_envelope
    from r36_parts import keeper,catalog_m08x2_screw
    from r17_cad import a_fixed_leaf,a_moving_leaf
    from r44_rear_bypass import A_SHELL,B_SHELL
    reference=source/'base_R43/parent_R42/parent_R41/baseline_R40/baseline_R38'
    original_b=cq.importers.importBrep(str(reference/'cad/R37_B_INTEGRAL_FRONT_STOP_LIPS.brep')).val()
    fittings={f'B_{name}_{side}_RESEARCH_PROXY':factory(side) for side in 'LR' for name,factory in (
        ('INBOARD_RAIL',inboard_rail),('ARM_GUIDE',arm_guide),('CAP',bored_cap),('PIN',pin),('KEEPER',keeper),('M08_SCREW',catalog_m08x2_screw),('TE_GAUGE',te_signal_envelope))}
    bridges={'A_FIXED_BRIDGE_SKIN_PROXY':a_fixed_leaf(P)}
    for deployment in (0.,.5,1.):bridges[f'A_MOVING_BRIDGE_DEPLOY_{deployment}_PROXY']=a_moving_leaf(P,deployment)
    def objects(s,q):
        obs=protected(s,q);obs['B_R37_BEFORE_UNAPPROVED_HEADER_CUT']=original_b.translate((0,s,q-8.2))
        obs.update(bridges);obs.update({name:part.translate((0,s,q-8.2)) for name,part in fittings.items()})
        if len(obs)!=23:raise ValueError('whole historical assembly obstacle coverage differs')
        return obs
    return objects,manifest['files']

def regularity(curve,seed,nper=49):
    """Numerical rotation-minimizing directors, no actual clamped boundary."""
    sigma=np.unique(np.r_[np.linspace(0,curve.target,161),*[curve.bounds[i]+part.partial_length(np.linspace(0,1,nper)) for i,part in enumerate(curve.segments)]])
    xyz,t,k=curve.evaluate(sigma)
    w=[];prior=unit(np.asarray(seed,float)-t[0]*np.dot(seed,t[0]));prev_t=t[0]
    for tangent in t:
        cross=np.cross(prev_t,tangent);cosine=float(np.dot(prev_t,tangent))
        if cosine<=-1+1e-10:raise ValueError('antiparallel tangents leave discrete Bishop continuation undefined')
        next_w=prior+np.cross(cross,prior)+np.cross(cross,np.cross(cross,prior))/(1+cosine)
        # Remove only accumulated floating error in orthogonality. No radius,
        # curvature or negative section Jacobian is regularized or clamped.
        next_w=unit(next_w-tangent*np.dot(next_w,tangent));w.append(next_w);prior=next_w;prev_t=tangent
    w=np.asarray(w);d=np.cross(t,w)
    kw=np.sum(k*w,axis=1);kt=np.sum(k*d,axis=1)
    J=1-np.abs(kw)*.6-np.abs(kt)*.056/2
    idx=int(np.argmin(J));end_w=w[-1];roll=math.degrees(math.atan2(np.dot(t[-1],np.cross(seed,end_w)),np.dot(seed,end_w)))
    return {'spatial_sample_count':len(sigma),'per_segment_parameter_samples':nper,'width_seed':list(map(float,seed)),'research_width_mm':1.2,'nominal_unprocessed_thickness_mm':.056,
      'minimum_conditional_section_J':float(J[idx]),'J_min_witness':{'fixed_material_sigma_mm':float(sigma[idx]),'xyz_mm':xyz[idx].tolist(),'curvature_width_per_mm':float(kw[idx]),'curvature_thickness_per_mm':float(kt[idx])},
      'nonpositive_J_spatial_sample_count':int(np.sum(J<=0)),'local_section_mapping_rejected':bool(np.any(J<=0)),
      'required_conditional_B_endpoint_director_roll_deg':roll,'B_clamp_direction_or_torsion_limit_supplied':False,'formula':'1 - abs(k_width)*width/2 - abs(k_thickness)*thickness/2',
      'numeric_spatial_frame_grid_is_material_fatigue_history':False,'positive_J_is_global_selfintersection_or_manufacturing_proof':False,'manufacturing_go':False}

def point_inside_queries(points,body,certificate):
    bb=certificate['bounds_mm'];near=np.flatnonzero(np.logical_and.reduce([points[:,i]>=bb[ax+'min']-1e-6 for i,ax in enumerate('xyz')]+[points[:,i]<=bb[ax+'max']+1e-6 for i,ax in enumerate('xyz')]))
    classifier=BRepClass3d_SolidClassifier(body.wrapped);inside=[]
    for i in near:
        classifier.Perform(gp_Pnt(*map(float,points[i])),1e-6)
        if classifier.State()==TopAbs_IN or classifier.IsOnAFace():inside.append(int(i))
    return {'validated_bbox_rejections':len(points)-len(near),'actual_native_point_queries':len(near),'inside_or_on_face_count':len(inside),'first_inside_index':inside[0] if inside else None}

def run(out,slide_steps=81,dock_steps=41):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    # The exact same guard used by the completed strict-motion review.
    sys.path.insert(0,str(ROOT/'guards'))
    from strict_intersections import participant,strict_common
    build_obstacles,files=obstacle_factory();before={n:sha(ROOT/'frozen_obstacles'/n) for n in files}
    own=['actual_obstacle_and_jacobian.py','geometry_candidates.py','cad_preflight.py']
    own_before={n:sha(ROOT/n) for n in own}
    configs=[Config(target_length_mm=L,dA_mm=1.,dB_mm=1.,dJ_mm=.25) for L in (148.20738578362864,153.20738578362864,160.20738578362864)]
    seeds={'WIDTH_Y':(0.,1.,0.),'WIDTH_Z':(0.,0.,1.)};rows=[];finite=[];convergence=[];started=time.monotonic()
    states=poses(slide_steps,dock_steps)
    for n,(s,q) in enumerate(states):
        obstacles=build_obstacles(s,q);cert={name:participant(body) for name,body in obstacles.items()}
        for cfg in configs:
            curve=build_candidate(cfg,s,q);sigma=np.linspace(6,curve.target-6,129);point,_,_=curve.evaluate(sigma)
            pairs={name:point_inside_queries(point,body,cert[name]) for name,body in obstacles.items()}
            reg={label:regularity(curve,seed) for label,seed in seeds.items()}
            rows.append({'candidate':cfg.name,'slide_mm':s,'normal_mm':q,'material_length_mm':curve.target,'material_stations_from_A_mm':sigma.tolist(),'all_23_complete_obstacles_validated_before_any_bbox_skip':True,
              'all_23_obstacles':pairs,'centerline_inside_or_on_obstacle_counts_are_route_rejection':True,'local_section_regularity':reg,'manufacturing_go':False})
        if n%20==0:print('actual motion obstacle pose',n+1,'of',len(states),flush=True)
    selected=[('STOW',0.,0.),('MID',39.875,0.),('PREDOCK',79.75,0.),('DOCK_HALF',79.75,4.1),('OPEN_SEATED',79.75,8.2)]
    cad=out/'cad';cad.mkdir(exist_ok=True)
    for cfg in configs:
        for pose,s,q in selected:
            obstacles=build_obstacles(s,q)
            for name,seed in seeds.items():
                tag=cfg.name+'_'+pose+'_'+name;body=None
                record={'candidate':cfg.name,'pose':pose,'slide_mm':s,'normal_mm':q,'width_seed':name,'requested_width_mm':1.2,'conditional_nominal_thickness_mm':.056,'specific_finished_FPC_received':False,'actual_finite_sweep_valid':False,'pairs':None,'manufacturing_go':False}
                try:
                    curve,wire,body=sweep_case(cfg,s,q,seed)
                    record['complete_payload_guard']=pure_positive_single_solid(body);participant(body)
                    record['actual_finite_sweep_valid']=True;record['wire_length_mm']=float(wire.Length())
                    record['fixed_analytic_material_length_mm']=curve.target
                    record['pairs']={label:strict_common(body,other) for label,other in obstacles.items()}
                    record['positive_obstacles']=[label for label,pair in record['pairs'].items() if pair['checked_volume_mm3']>1e-7]
                    path=cad/(tag+'_NOMINAL_56UM_RESEARCH.step');cq.exporters.export(body,str(path));loaded=cq.importers.importStep(str(path))
                    if len(loaded.vals())!=1:raise ValueError('finite STEP reimport contains extra top-level payloads')
                    record['full_reimport_payload_guard']=pure_positive_single_solid(loaded.val());record['STEP']={'file':path.name,'sha256':sha(path)}
                except Exception as exc:
                    record['actual_exception']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
                    if body is not None:
                        try:
                            path=cad/(tag+'_REJECTED_ACTUAL_PAYLOAD.brep');cq.exporters.export(body,str(path));record['rejected_native_BREP']={'file':path.name,'sha256':sha(path)}
                        except Exception as save:record['rejected_payload_save_error']=str(save)
                base=regularity(build_candidate(cfg,s,q),seed,49);fine=regularity(build_candidate(cfg,s,q),seed,99)
                record['conditional_local_J']=fine;record['candidate_route_accepted']=False
                convergence.append({'case':tag,'J_min_49':base['minimum_conditional_section_J'],'J_min_99':fine['minimum_conditional_section_J'],'rejection_sign_stable':base['local_section_mapping_rejected']==fine['local_section_mapping_rejected'],'difference_is_not_certified_discretization_error':True})
                finite.append(record);print('actual finite sweep',tag,'valid',record['actual_finite_sweep_valid'],'positive',record.get('positive_obstacles'),'J',fine['minimum_conditional_section_J'],flush=True)
    after={n:sha(ROOT/'frozen_obstacles'/n) for n in files};own_after={n:sha(ROOT/n) for n in own}
    if before!=after or own_before!=own_after:raise ValueError('bounded experiment input bytes changed')
    report={'state_count':len(states),'candidate_count':len(configs),'new_centerline_motion_candidate_rows':len(rows),'fixed_material_station_samples_per_row':129,'full_23_obstacle_centerline_rows':len(rows)*23,
      'new_actual_finite_sweep_requests':len(finite),'actual_valid_swept_cases':sum(r['actual_finite_sweep_valid'] for r in finite),'actual_rejected_sweep_cases':sum(not r['actual_finite_sweep_valid'] for r in finite),
      'valid_sweep_cases_with_positive_obstacle_common':sum(bool(r.get('positive_obstacles')) for r in finite),'all_specific_dynamic_FPC_and_artwork_and_USB_power_roles_unknown':True,'geometry_is_research_not_actual_complete_phone_assembly':True,
      'source_236_obstacle_files_unchanged':before==after,'own_execution_source_hashes_before':own_before,'own_execution_source_hashes_after':own_after,'rows':rows,'finite_sweep_rows':finite,'regularity_refinement_records':convergence,
      'continuous_between_grid_interference_or_fatigue_certificate':False,'candidate_route_accepted':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-started,'host':platform.node(),'CadQuery':cq.__version__}
    (out/'actual_obstacle_and_J_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('state_count','candidate_count','new_actual_finite_sweep_requests','actual_valid_swept_cases','actual_rejected_sweep_cases','candidate_route_accepted','manufacturing_go')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out-dir',type=Path,required=True);p.add_argument('--slide-steps',type=int,default=81);p.add_argument('--dock-steps',type=int,default=41);a=p.parse_args();run(a.out_dir,a.slide_steps,a.dock_steps)
