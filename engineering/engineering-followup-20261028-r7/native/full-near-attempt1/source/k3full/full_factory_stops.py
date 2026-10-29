"""Fresh complete K3 full-factory/all-pair experiment after two actual pilots."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from f1_common import *
import frozen_key_factory_adapter as adapter
import actual_stop_prerequisite as prerequisite
import panel_key_travel_stops_v1 as candidate
import full_stop_states as states

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('output','k3-stow','k3-predock','binding','key-binding','contract','k1-contract'):ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--pose',choices=tuple(states.STATES),required=True)
 a=ap.parse_args();out,r,budget=start(__file__,a.output,a.pose)
 r.update(schema='razr-K3FULL-complete-factory-ten-state-campaign-v1',candidate_name=candidate.NAME,pilot_only=False,
  full_finite_campaign_only=True,preregistered_state_count=10,finite_pose_clear=False,
  all_unordered_pairs_present_once=False,remaining_unproved_domains=list(states.REMAINING),
  body_exports={},candidate_material_exports={},pairs=[],positive_pairs=[],evaluation_failures=[],mismatches_to_factory=[])
 r['external_source_sha256'].update({str(Path(x).resolve()):sha(x) for x in
  (adapter.__file__,prerequisite.__file__,candidate.__file__,states.__file__,a.binding,a.key_binding,a.contract,a.k1_contract)})
 try:
  binding=json.loads(a.binding.read_text());require(sha(a.key_binding)==binding['original_K1_binding_sha256'],'original actual K1 binding differs')
  contract=json.loads(a.contract.read_text());require(sha(candidate.__file__)==contract['candidate_source_sha256']==binding['candidate_source_sha256']
   and sha(a.contract)==binding['contract_sha256'],'K3 frozen candidate source or contract differs')
  design=candidate.frozen_design(a.k1_contract);require(design==contract['design_contract'],'K3 scalar design contract differs')
  r.update(candidate_source_sha256=sha(candidate.__file__),candidate_contract_sha256=sha(a.contract),design_contract=design)
  before=identity.snapshot();executed=identity.record_executed_project_files();r['identity_before']=before
  import cadquery as cq
  import product_nominal_motion as nominal
  import product_routing_ep5 as ep5
  import verify_cam_coupling as cam
  import body_inventory
  p=nominal.p;r['status']='verifying_actual_K3_dual_pilot_and_whole_material';atomic(out/'report.json',r)
  verified=prerequisite.load({'stow_tabs_3':a.k3_stow,'predock':a.k3_predock},binding,json.loads(a.key_binding.read_text()),p,cq,budget)
  keys=verified.keys;spec=dict(states.STATES[a.pose]);expected=spec.pop('expected_bodies');expected_q=spec.pop('actual_binary64_q_from_declared_factory_inputs')
  r.update(pose_input=spec,K3_prerequisite=verified.receipt,status='building_complete_actual_K1_factory');atomic(out/'report.json',r)
  baseline,meta=adapter.full_scene(keys,nominal,cam,p,**spec)
  ep5.validate_factory_input_coverage(meta['scene'],before['available_source_sha256']);require(len(baseline)==expected,'full K3 factory inventory differs')
  q={side:cam.K*spec['slide']+offset for side,offset in zip('LR',spec['key_offsets'])}
  require([q[s] for s in 'LR']==expected_q,'actual binary64 independent KEY coordinates differ')
  r.update(actual_complete_factory_called=True,participant_count=len(baseline),participant_names=sorted(baseline),
   native_scene_metadata=meta,actual_q_by_side_mm=q,original_K1_inventory=body_inventory.measure(baseline,meta,p),
   original_panel_to_verified_pilot_material=adapter.compare(baseline['A_BACK_PANEL'],verified.original_panel,p),
   all_nonpanel_participants_retained_unchanged=True,geometry_repair_applied=True,fixed_pair_certificate_reused=False,whole_motion_claimed=False)
  (out/'materials').mkdir();r['candidate_material_exports']['original_panel']=export(baseline['A_BACK_PANEL'],out/'materials/original_panel',p,budget)
  # Preserve full preview before any prospective contact assertion can fail.
  new=baseline['A_BACK_PANEL']
  for side in 'LR':
   for role,bounds in design['additive_boxes_R_mm'].items():
    label=side+'_'+role;body=p.box(*candidate.handed_bounds(side,bounds))
    r['candidate_material_exports'][label]=export(body,out/'materials'/label,p,budget);new=new.fuse(body).clean()
  parts=dict(baseline);parts['A_BACK_PANEL']=new
  r['status']='exporting_all_complete_factory_participants';atomic(out/'report.json',r);(out/'bodies').mkdir()
  for name,body in sorted(parts.items()):
   r['body_exports'][name]=export(body,out/'bodies'/name,p,budget)
   if len(r['body_exports'])%16==0:atomic(out/'report.json',r)
  r['complete_preview_exports_retained']=True
  r['status']='rechecking_exact_candidate_material_and_functional_faces';atomic(out/'report.json',r)
  accepted,materials,receipt=candidate.apply(baseline,meta,p,a.k1_contract)
  r['candidate_application']=receipt
  r['new_panel_to_named_candidate_material']=adapter.compare(parts['A_BACK_PANEL'],accepted['A_BACK_PANEL'],p)
  r['new_panel_to_actual_dual_pilot_material']=adapter.compare(parts['A_BACK_PANEL'],verified.candidate_panel,p)
  checks,controls=candidate.endpoint_and_overtravel_checks(parts,keys,p,a.k1_contract,q)
  for side in 'LR':
   expected_end=states.EXPECTED_CONTACT_ENDS[a.pose][side]
   require(set(checks[side]['endpoint_contacts'])==({expected_end} if expected_end else set()),'actual independent endpoint contacts differ')
  r['endpoint_and_overtravel_checks']=checks
  for name,body in controls.items():r['candidate_material_exports'][name]=export(body,out/'materials'/name,p,budget)
  r['native_early_conditions_rechecked']=True;r['panel_KEY_direct_Common']={}
  for side in 'LR':
   common=parts['A_BACK_PANEL'].intersect(parts[side+'_KEY']);v=p.volume(common)
   row={'a':'A_BACK_PANEL','b':side+'_KEY','common_mm3':v,'rejected':v>1e-7,'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[side+'_KEY'])}
   if v>0:row['export']=export(common,out/(side+'-panel-KEY-direct-Common'),p,budget)
   r['panel_KEY_direct_Common'][side]=row
  r['status']='evaluating_every_fresh_complete_factory_body_pair';atomic(out/'report.json',r)
  evaluate_pairs(parts,out,r,p,budget)
  r['identity_after']=identity.finish(before,[*executed,body_inventory.__file__])
  require(r['identity_after']['source_bytes_and_locked_environment_unchanged'],'full factory original S4 source/runtime changed')
  require(all(sha(k)==v for k,v in r['external_source_sha256'].items()),'full factory external source/input changed')
  r['execution_completed']=bool(r['all_unordered_pairs_present_once'] and not r['evaluation_failures'])
  r['status']='complete' if r['execution_completed'] else 'completed_with_evaluation_failures'
 except BaseException as exc:
  r['failure_stage']=r.get('status');r['status']='failed_or_interrupted';r['failure']=type(exc).__name__+': '+str(exc)
 finally:
  r['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',r)
 print(json.dumps({k:r.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','seconds')}),flush=True)
 return 0 if r['execution_completed'] else 2

if __name__=='__main__':raise SystemExit(main())
