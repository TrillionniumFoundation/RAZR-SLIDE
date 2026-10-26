"""Independent complete STEP/all-pair and scalar-panel reconstruction reader."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from f1_common import *
import frozen_key_factory_adapter as adapter
import actual_stop_prerequisite as prerequisite
import full_stop_states as states
import independent_stop_checks as independent

NAME='panel_key_travel_stops_v1'

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('output','k3-stow','k3-predock','binding','key-binding','contract','k1-contract','factory-report'):ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--pose',choices=tuple(states.STATES),required=True)
 a=ap.parse_args();out,r,budget=start(__file__,a.output,a.pose)
 r.update(schema='razr-K3FULL-independent-full-STEP-all-pair-reader-v1',candidate_name=NAME,pilot_only=False,
  full_finite_campaign_only=True,preregistered_state_count=10,finite_pose_clear=False,all_unordered_pairs_present_once=False,
  remaining_unproved_domains=list(states.REMAINING),body_readbacks={},candidate_material_readbacks={},candidate_material_exports={},
  independent_material_builder_does_not_import_candidate_source=True,pairs=[],positive_pairs=[],evaluation_failures=[],mismatches_to_factory=[])
 r['external_source_sha256'].update({str(Path(x).resolve()):sha(x) for x in
  (adapter.__file__,prerequisite.__file__,states.__file__,independent.__file__,a.binding,a.key_binding,a.contract,a.k1_contract)})
 try:
  original=json.loads(a.factory_report.read_text());base=a.factory_report.parent.resolve();binding=json.loads(a.binding.read_text())
  spec=dict(states.STATES[a.pose]);expected=spec.pop('expected_bodies');expected_q=spec.pop('actual_binary64_q_from_declared_factory_inputs')
  require(original['functional_source_commit']==S4 and original['candidate_name']==NAME and original['pose']==a.pose
   and original.get('complete_preview_exports_retained') is True and len(original['body_exports'])==expected and original['pose_input']==spec,
   'complete actual preregistered K3 factory preview required')
  contract=json.loads(a.contract.read_text());design=contract['design_contract']
  require(original['candidate_source_sha256']==contract['candidate_source_sha256']==binding['candidate_source_sha256']
   and original['candidate_contract_sha256']==sha(a.contract)==binding['contract_sha256'] and original['design_contract']==design,
   'exact K3 source/contract identity differs')
  require(sha(a.k1_contract)==design['required_K1_contract_sha256'] and sha(a.key_binding)==binding['original_K1_binding_sha256'],'original K1 input bytes differ')
  before=identity.snapshot();executed=identity.record_executed_project_files();r['identity_before']=before
  import cadquery as cq
  import product_assembly as p
  import verify_cam_coupling as cam
  verified=prerequisite.load({'stow_tabs_3':a.k3_stow,'predock':a.k3_predock},binding,json.loads(a.key_binding.read_text()),p,cq,budget);keys=verified.keys
  r.update(K3_prerequisite=verified.receipt,factory_report_sha256=sha(a.factory_report),native_STEP_readback_executed=True,
   separate_process_from_factory=True,independent_CAD_kernel=False,pose_input=spec,candidate_contract_sha256=sha(a.contract),
   candidate_source_sha256=contract['candidate_source_sha256'],design_contract=design,
   participant_names=original['participant_names'],participant_count=expected,status='importing_every_complete_factory_STEP')
  def read(entry,label,group):
   budget.check();ref=entry['files']['step'];path=(base/ref['path']).resolve()
   require(path.is_relative_to(base) and path.is_file() and not path.is_symlink() and sha(path)==ref['sha256'] and path.stat().st_size==ref['bytes'],'complete STEP identity differs')
   roots=cq.importers.importStep(str(path)).vals();require(len(roots)==1,'one complete STEP root required')
   body=roots[0];now=signature(body,p);old=entry['signature_before']
   dv=now['signed_volume_mm3']-old['signed_volume_mm3'];db=[x-y for x,y in zip(now['bounds_mm'],old['bounds_mm'])]
   passed=now['is_valid'] and now['solid_count']==old['solid_count'] and abs(dv)<=1e-7 and max(map(abs,db))<=1e-7
   group[label]={'STEP':ref,'signature':now,'volume_delta_mm3':dv,'bounds_delta_mm':db,'passed':passed}
   require(passed,'independent complete STEP material signature differs');return body
  parts={name:read(entry,name,r['body_readbacks']) for name,entry in sorted(original['body_exports'].items())}
  require(len(parts)==expected and set(parts)==set(original['participant_names']),'complete participant readback differs')
  old_panel=read(original['candidate_material_exports']['original_panel'],'original_panel',r['candidate_material_readbacks'])
  r['original_panel_to_verified_pilot_material']=adapter.compare(old_panel,verified.original_panel,p)
  r['new_panel_to_actual_dual_pilot_material']=adapter.compare(parts['A_BACK_PANEL'],verified.candidate_panel,p)
  q={side:cam.K*spec['slide']+offset for side,offset in zip('LR',spec['key_offsets'])}
  require([q[s] for s in 'LR']==expected_q,'actual independent q coordinates differ')
  r['actual_q_by_side_mm']=q
  r['candidate_q0_material_comparisons']={s:adapter.compare(parts[s+'_KEY'].translate((0.,-q[s],0.)),keys.candidate_q0[s],p) for s in 'LR'}
  r['status']='independent_scalar_material_contact_and_functional_gate_replay';atomic(out/'report.json',r)
  def emit(rows):r['independent_early_gate_records']=rows;atomic(out/'report.json',r)
  gates,materials=independent.all_checks(parts,old_panel,keys,design,q,p,cq,budget,emit)
  count=12+3*sum(v is not None for v in states.EXPECTED_CONTACT_ENDS[a.pose].values())
  require(len(gates)==count,'complete declared independent early-gate inventory differs')
  r['independent_native_evaluation_failures']=[name for name,row in gates.items() if not row['evaluated']]
  r['independent_geometric_gate_rejections']=[name for name,row in gates.items() if row['evaluated'] and not row['passed']]
  r['native_early_conditions_rechecked']=all(row['evaluated'] and row['passed'] for row in gates.values())
  (out/'materials').mkdir()
  for name,body in materials.items():r['candidate_material_exports'][name]=export(body,out/'materials'/name,p,budget)
  if original.get('all_unordered_pairs_present_once') is True:
   r['status']='independent_fresh_all_pair_STEP_evaluation';atomic(out/'report.json',r)
   evaluate_pairs(parts,out,r,p,budget,original=original)
   require(not r['mismatches_to_factory'],'independent all-pair Common mismatch')
  else:r['all_pairs_not_evaluated_reason']='producer did not complete full original matrix; partial evidence retained'
  r['panel_KEY_direct_Common']={}
  for side in 'LR':
   common=parts['A_BACK_PANEL'].intersect(parts[side+'_KEY']);v=p.volume(common)
   row={'a':'A_BACK_PANEL','b':side+'_KEY','common_mm3':v,'rejected':v>1e-7,'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[side+'_KEY'])}
   if side in original.get('panel_KEY_direct_Common',{}):
    row['factory_volume_delta_mm3']=v-original['panel_KEY_direct_Common'][side]['common_mm3']
    require(abs(row['factory_volume_delta_mm3'])<=1e-7,'full direct panel/KEY Common differs')
   if v>0:row['export']=export(common,out/(side+'-panel-KEY-direct-Common'),p,budget)
   r['panel_KEY_direct_Common'][side]=row
  r['identity_after']=identity.finish(before,[*executed])
  require(r['identity_after']['source_bytes_and_locked_environment_unchanged'],'reader original S4 source/runtime changed')
  require(all(sha(k)==v for k,v in r['external_source_sha256'].items()),'reader external source/input changed')
  r['execution_completed']=bool(r['all_unordered_pairs_present_once'] and not r['evaluation_failures'] and not r['mismatches_to_factory'])
  r['finite_pose_clear']=bool(r.get('finite_pose_clear') and r['native_early_conditions_rechecked'])
  r['status']='complete' if r['execution_completed'] else 'incomplete_or_failed_independent_readback'
 except BaseException as exc:
  r['failure_stage']=r.get('status');r['status']='failed_or_interrupted';r['failure']=type(exc).__name__+': '+str(exc)
 finally:
  r['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',r)
 print(json.dumps({k:r.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','seconds')}),flush=True)
 return 0 if r['execution_completed'] else 2

if __name__=='__main__':raise SystemExit(main())
