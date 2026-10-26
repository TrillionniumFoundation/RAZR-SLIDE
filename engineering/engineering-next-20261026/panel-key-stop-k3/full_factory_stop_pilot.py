"""Complete K1 factory plus K3 early gates; at most 153 changed-panel pairs."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from f1_common import *
import frozen_key_factory_adapter as adapter
import panel_key_travel_stops_v1 as candidate
import k3_pilot_states as states
import k3_pilot_common as common

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('output','k1-near','k1-far','binding','contract','k1-contract'):ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--pose',choices=tuple(states.PILOTS),required=True)
 a=ap.parse_args();out,r,budget=start(__file__,a.output,a.pose)
 r.update(schema='razr-K3-complete-factory-preliminary-stop-pilot-v1',candidate_name=candidate.NAME,
  pilot_only=True,all_unordered_pairs_present_once=False,finite_pose_clear=False,pilot_clear=False,
  pilot_preconditions_passed=False,full_ten_state_campaign_authorized=False,
  remaining_unproved_domains=list(states.REMAINING),body_exports={},candidate_material_exports={},
  pairs=[],positive_pairs=[],evaluation_failures=[],mismatches_to_factory=[],persisted_pair_count=0,
  expected_pair_count=153,all_panel_pairs_present_once=False,precondition_failures=[])
 r['external_source_sha256'].update({str(Path(x).resolve()):sha(x) for x in
  (adapter.__file__,candidate.__file__,states.__file__,common.__file__,a.binding,a.contract,a.k1_contract)})
 try:
  frozen=json.loads(a.contract.read_text());require(sha(candidate.__file__)==frozen['candidate_source_sha256'],'K3 candidate bytes differ')
  design=candidate.frozen_design(a.k1_contract);require(design==frozen['design_contract'],'K3 frozen design differs')
  r.update(candidate_contract_sha256=sha(a.contract),candidate_source_sha256=sha(candidate.__file__),design_contract=design)
  before=identity.snapshot();executed=identity.record_executed_project_files();r['identity_before']=before
  import cadquery as cq
  import product_nominal_motion as nominal
  import product_routing_ep5 as ep5
  import verify_cam_coupling as cam
  import body_inventory
  p=nominal.p
  r['status']='verifying_actual_dual_clear_K1';atomic(out/'report.json',r)
  keys=adapter.load_keys({'near':a.k1_near,'far':a.k1_far},json.loads(a.binding.read_text()),p,cq,budget)
  spec=dict(states.PILOTS[a.pose]);expected=spec.pop('expected_bodies')
  spec.update(flanks=(0.,0.),key_offsets=(0.,0.),crosshead_offsets=(0.,0.),telescope_offsets=None)
  r.update(pose_input=spec,K1_prerequisite=keys.receipt,status='building_complete_actual_factory');atomic(out/'report.json',r)
  baseline,meta=adapter.full_scene(keys,nominal,cam,p,**spec)
  ep5.validate_factory_input_coverage(meta['scene'],before['available_source_sha256'])
  require(len(baseline)==expected,'pilot complete inventory differs')
  r.update(actual_complete_factory_called=True,participant_count=len(baseline),participant_names=sorted(baseline),
   native_scene_metadata=meta,original_K1_inventory=body_inventory.measure(baseline,meta,p),
   all_nonpanel_participants_retained_unchanged=True,geometry_repair_applied=True,
   fixed_pair_certificate_reused=False,whole_motion_claimed=False,status='saving_original_panel_and_stop_components')
  (out/'materials').mkdir();old=p.single(baseline['A_BACK_PANEL']);materials={'original_panel':old};pieces={}
  r['candidate_material_exports']['original_panel']=export(old,out/'materials/original_panel',p,budget)
  new=old;r['preliminary_actual_join_measurements']={}
  for side in 'LR':
   for role,bounds in design['additive_boxes_R_mm'].items():
    budget.check();label=side+'_'+role;body=p.box(*candidate.handed_bounds(side,bounds));pieces[label]=body
    r['candidate_material_exports'][label]=export(body,out/'materials'/label,p,budget)
    join=body.intersect(old);outside=body.cut(old)
    row={'join_to_original_panel_mm3':p.volume(join),'new_component_outside_original_panel_mm3':p.volume(outside)}
    for suffix,shape in (('join',join),('outside',outside)):
     if p.volume(shape)>0:r['candidate_material_exports'][label+'_'+suffix]=export(shape,out/'materials'/(label+'_'+suffix),p,budget)
    r['preliminary_actual_join_measurements'][label]=row;atomic(out/'report.json',r)
    new=new.fuse(body).clean()
  r['preliminary_candidate_panel_signature']=signature(new,p)
  parts=dict(baseline);parts['A_BACK_PANEL']=new
  r['status']='saving_all_candidate_factory_material_before_gates';atomic(out/'report.json',r)
  (out/'bodies').mkdir()
  for name,body in sorted(parts.items()):
   r['body_exports'][name]=export(body,out/'bodies'/name,p,budget)
   if len(r['body_exports'])%16==0:atomic(out/'report.json',r)
  r['complete_preview_exports_retained']=True
  r['status']='checking_positive_joins_and_original_functional_faces';atomic(out/'report.json',r)
  try:
   accepted,verified_materials,receipt=candidate.apply(baseline,meta,p,a.k1_contract)
   agreement=compare_material(accepted['A_BACK_PANEL'],new,p)
   require(agreement['equal_within_original_1e_minus_7_mm3'],'saved whole panel differs from candidate builder')
   r.update(candidate_application=receipt,preview_to_named_candidate_material=agreement)
   r['status']='checking_endpoint_area_whole_KEY_overtravel_and_release';atomic(out/'report.json',r)
   q={side:cam.K*spec['slide']+offset for side,offset in zip('LR',spec['key_offsets'])}
   checks,controls=candidate.endpoint_and_overtravel_checks(parts,keys,p,a.k1_contract,q)
   expected_end='lower' if a.pose=='stow_tabs_3' else 'upper'
   require(all(set(checks[s]['endpoint_contacts'])=={expected_end} for s in 'LR'),'both actual endpoint contacts required')
   r['endpoint_and_overtravel_checks']=checks
   for name,body in controls.items():
    r['candidate_material_exports'][name]=export(body,out/'materials'/name,p,budget)
   r['pilot_preconditions_passed']=True
  except Exception as exc:
   r['precondition_failures'].append({'stage':r['status'],**common.public_failure(exc)})
   r['original_precondition_failure']=type(exc).__name__+': '+str(exc)
  if r['pilot_preconditions_passed']:
   r['status']='checking_all_changed_panel_pairs_only';atomic(out/'report.json',r)
   common.panel_pairs(parts,out,r,p,budget)
  else:r['panel_pairs_not_evaluated_reason']='native early precondition failed; no 11781-pair or ten-state campaign executed'
  r['identity_after']=identity.finish(before,[*executed,body_inventory.__file__])
  require(r['identity_after']['source_bytes_and_locked_environment_unchanged'],'S4 source/runtime changed')
  require(all(sha(k)==v for k,v in r['external_source_sha256'].items()),'K3 external source changed')
  r['execution_completed']=bool(r['complete_preview_exports_retained'] and (not r['pilot_preconditions_passed'] or (r['all_panel_pairs_present_once'] and not r['evaluation_failures'])))
  r['pilot_clear']=bool(r['execution_completed'] and r['pilot_preconditions_passed'] and r.get('pilot_panel_pairs_clear'))
  r['status']='complete_pilot_clear' if r['pilot_clear'] else 'complete_pilot_rejected' if r['execution_completed'] else 'incomplete_pilot'
 except BaseException as exc:
  r['failure_stage']=r.get('status');r['status']='failed_or_interrupted';r['failure']=type(exc).__name__+': '+str(exc)
 finally:
  r['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',r)
 print(json.dumps({k:r.get(k) for k in ('status','execution_completed','pilot_clear','pilot_preconditions_passed','seconds')}),flush=True)
 return 0 if r['execution_completed'] else 2

if __name__=='__main__':raise SystemExit(main())
