#!/usr/bin/env python3
"""R6 split-root key, return path and outside spring approach; no force qualification."""
from pathlib import Path
import sys,itertools,json,time,platform
sys.dont_write_bytecode=True
import split_root_cartridges_v9 as s
b=s.b;HERE=Path(__file__).resolve().parent
from strict_intersections import CheckedBody,Checker
def checks(moving,fixed):return s.check(moving,fixed)
def append(rows,port,side,operation,position,checked,extra=None):
 rows.append({'port':port,'side':side,'operation':operation,'position':position,'checks':checked,'positive_intersections':[r for r in checked if r['checked_common_mm3']>b.EPS],**(extra or {})})
def main():
 start=time.monotonic();before={str(p.relative_to(HERE.parent)):b.sha(p) for p in (HERE.parent/'inputs').rglob('*') if p.is_file()};rows=[];brackets=[]
 for port,side in itertools.product(('STOW','OPEN'),'LR'):
  p,_=s.scene(port,side);Q=1.3 if port=='STOW' else 6.2;ee=4. if port=='OPEN' else 0.;stroke=1.1 if port=='STOW' else .55
  roots={n:v for n,v in p.items() if n.startswith('ROOT_')};park=p['PAWL'].translate(b.identity.evec(port,side,stroke))
  # Actual cam collision-free brackets, using each original integral pin and
  # uncut KEY. The rigid per-pose contact trajectory is not a measured force.
  for q in (12.,8.,4.,2.,1.4,1.2,1.,.8,.7,.4,.2,.1,.05,0.):
   key=p['KEY'].translate(b.identity.qvec(port,q));lifts=[];stops={};guard=Checker()
   for i in range(2):
    zero=p['STOP_'+str(i)].translate(b.rvec(port,-1.14));kb=CheckedBody(key)
    def cv(v):return guard.common(CheckedBody(zero.translate(b.rvec(port,v))),kb)['checked_common_mm3']
    lo,hi=-.02,1.2
    if cv(lo)<=1e-10:hi=lo
    else:
     assert cv(hi)<=1e-10
     for _ in range(27):
      mid=(lo+hi)/2
      if cv(mid)>1e-10:lo=mid
      else:hi=mid
    lifts.append(hi);stops['STOP_'+str(i)]=zero.translate(b.rvec(port,hi))
   brackets.append({'port':port,'side':side,'q_mm':q,'actual_cam_collision_free_lifts_mm':lifts,'numeric_collision_threshold_mm3':1e-10,'actual_occ_query_count':guard.actual_occ_common_count,'not_a_position_or_force_qualification':True})
   fixed={**roots,**stops,'PARKED_PAWL':park};append(rows,port,side,'KEY_POSITIVE_Q_INSERT',q,checks(key,fixed),{'cam_contact_lifts_mm':lifts})
   for i in range(2):append(rows,port,side,'CAM_STOP_DURING_KEY_INSERT_'+str(i),q,checks(stops['STOP_'+str(i)],{**roots,'PARKED_PAWL':park,'KEY':key}))
  # Actual closing/release rigid interval, at fully present KEY only.
  fixed={n:v for n,v in p.items() if n!='PAWL'}
  for i in range(23):append(rows,port,side,'PAWL_FULL_KEY_CLOSE_RELEASE',i/22,checks(p['PAWL'].translate(b.identity.evec(port,side,stroke*i/22)),fixed))
  # All upper parts remain present. 3.13 is a conservative sensitivity case
  # interpreting the public free-length tolerance field as nominal +.13;
  # it is explicitly not a controlled lot tolerance or qualified spring model.
  for i in range(2):
   qc=Q+(.9 if i==0 else 3.);ec=(3.8 if i==0 else 2.8)+ee;off=5*i
   fixed={n:v for n,v in p.items() if n not in {f'SPRING_{i}_OD_TOL_ENVELOPE',f'SPRING_CAP_{i}',f'SPRING_SCREW_{i}_M1x3_NOMINAL'}}
   for length in (3.,3.13):
    free=b.world(b.cyl(.43,length,ec,qc,2.94+off),port,side)
    for d in (10.,6.,3.,1.,.5,0.):
     moving=free.translate(b.rvec(port,1.6)).translate(b.identity.evec(port,side,d));append(rows,port,side,'SPRING_EXTERNAL_E_APPROACH',d,checks(moving,fixed),{'i':i,'free_length_mm':length,'raised_r_mm':1.6,'sampled_pose_only':True})
    for d in (1.6,1.5,1.,.5,.1,0.):append(rows,port,side,'SPRING_AXIAL_DROP_AFTER_EXTERNAL_APPROACH',d,checks(free.translate(b.rvec(port,d)),fixed),{'i':i,'free_length_mm':length,'sampled_pose_only':True})
   cap=p[f'SPRING_CAP_{i}']
   for d in (10.,6.,3.,1.,.5,0.):append(rows,port,side,'CAP_EXTERNAL_E_APPROACH',d,checks(cap.translate(b.rvec(port,1.8)).translate(b.identity.evec(port,side,d)),fixed),{'i':i,'raised_r_mm':1.8,'sampled_pose_only':True})
   for d in (1.8,1.7,1.5,1.,.5,.1,0.):append(rows,port,side,'CAP_AXIAL_DROP',d,checks(cap.translate(b.rvec(port,d)),fixed),{'i':i,'free_spring_is_compressed_by_contact_not_a_rigid_overlapping_cylinder':True,'sampled_pose_only':True})
   screw_e=(7.5 if i==0 else 4.5)+ee;tool=b.world(b.cyl(1.5,60.,screw_e,qc,5.15+off),port,side)
   fixed_tool={n:v for n,v in p.items() if n!=f'SPRING_SCREW_{i}_M1x3_NOMINAL'};append(rows,port,side,'SPRING_PH0_FULL50_PLUS10_CONTINUOUS_UNION',10.,checks(tool,fixed_tool),{'i':i,'actual_catalog_diameter_mm':3.,'actual_catalog_visible_length_mm':50.,'socket_engagement_torque_and_full_handle_geometry_unqualified':True})
  print(json.dumps({'port':port,'side':side,'completed_rows':len(rows),'bad_rows':sum(bool(r['positive_intersections']) for r in rows)}),flush=True)
 after={str(p.relative_to(HERE.parent)):b.sha(p) for p in (HERE.parent/'inputs').rglob('*') if p.is_file()};assert before==after
 ops={op:{'rows':sum(r['operation']==op for r in rows),'positive_intersection_rows':sum(bool(r['positive_intersections']) for r in rows if r['operation']==op)} for op in sorted({r['operation'] for r in rows})}
 report={'host':platform.node(),'source_sha256':b.sha(__file__),'scene_source_sha256':b.sha(s.__file__),'protected_R4_SHA256':before,'protected_source_unchanged':True,'rows':rows,'cam_brackets':brackets,'row_count':len(rows),'summary':ops,'unexpected_positive_rows':sum(bool(r['positive_intersections']) for r in rows),'physical_return_capture_force_friction_and_fatigue_qualified':False,'supplier_controlled_free_length_tolerance_interpretation_qualified':False,'all_installation_paths_except_tool_union_are_sampled_not_continuous_proof':True,'complete_phone_assembly':False,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'final-sequence-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(ops,indent=2),flush=True)
 if report['unexpected_positive_rows']:raise ValueError('New actual sequence has geometry interference; receipt retained')
if __name__=='__main__':main()
