"""Independent complete STEP reader and scalar-contract K3 early-gate replay."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from f1_common import *
import frozen_key_factory_adapter as adapter
import k3_pilot_states as states
import k3_pilot_common as common
import independent_stop_checks as independent

NAME='panel_key_travel_stops_v1'

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('output','k1-near','k1-far','binding','contract','k1-contract','factory-report'):ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--pose',choices=tuple(states.PILOTS),required=True)
 a=ap.parse_args();out,r,budget=start(__file__,a.output,a.pose)
 r.update(schema='razr-K3-independent-stop-pilot-STEP-reader-v1',candidate_name=NAME,pilot_only=True,
  finite_pose_clear=False,pilot_clear=False,all_unordered_pairs_present_once=False,pilot_preconditions_passed=False,
  full_ten_state_campaign_authorized=False,remaining_unproved_domains=list(states.REMAINING),body_readbacks={},
  candidate_material_readbacks={},candidate_material_exports={},independent_material_builder_does_not_import_candidate_source=True,
  pairs=[],positive_pairs=[],evaluation_failures=[],mismatches_to_factory=[],persisted_pair_count=0,
  expected_pair_count=153,all_panel_pairs_present_once=False)
 r['external_source_sha256'].update({str(Path(x).resolve()):sha(x) for x in
  (adapter.__file__,states.__file__,common.__file__,independent.__file__,a.binding,a.contract,a.k1_contract)})
 try:
  original=json.loads(a.factory_report.read_text());base=a.factory_report.parent.resolve()
  require(original['functional_source_commit']==S4 and original['candidate_name']==NAME and original['pose']==a.pose
   and original.get('complete_preview_exports_retained') is True and len(original['body_exports'])==154,
   'complete exported actual K3 preview required even after precondition rejection')
  frozen=json.loads(a.contract.read_text());design=frozen['design_contract']
  require(original['candidate_source_sha256']==frozen['candidate_source_sha256'] and original['candidate_contract_sha256']==sha(a.contract)
   and original['design_contract']==design,'exact original K3 source/contract identity differs')
  require(sha(a.k1_contract)==design['required_K1_contract_sha256'],'reader K1 scalar contract bytes differ')
  expected_spec=dict(states.PILOTS[a.pose]);expected_spec.pop('expected_bodies')
  expected_spec.update(flanks=[0.,0.],key_offsets=[0.,0.],crosshead_offsets=[0.,0.],telescope_offsets=None)
  require(original['pose_input']==expected_spec,'original pilot input differs from frozen state')
  before=identity.snapshot();executed=identity.record_executed_project_files();r['identity_before']=before
  import cadquery as cq
  import product_assembly as p
  import verify_cam_coupling as cam
  keys=adapter.load_keys({'near':a.k1_near,'far':a.k1_far},json.loads(a.binding.read_text()),p,cq,budget)
  r.update(K1_prerequisite=keys.receipt,factory_report_sha256=sha(a.factory_report),native_STEP_readback_executed=True,
   separate_process_from_factory=True,independent_CAD_kernel=False,pose_input=original['pose_input'],
   candidate_contract_sha256=sha(a.contract),candidate_source_sha256=frozen['candidate_source_sha256'],design_contract=design,
   participant_names=original['participant_names'],participant_count=154,status='importing_complete_factory_and_original_panel')
  def read(entry,root,label,group):
   budget.check();ref=entry['files']['step'];path=(root/ref['path']).resolve()
   require(path.is_relative_to(root) and path.is_file() and not path.is_symlink() and sha(path)==ref['sha256']
    and path.stat().st_size==ref['bytes'],'pilot STEP original identity differs')
   values=cq.importers.importStep(str(path)).vals();require(len(values)==1,'one complete STEP root required')
   body=values[0];now=signature(body,p);old=entry['signature_before']
   dv=now['signed_volume_mm3']-old['signed_volume_mm3'];db=[x-y for x,y in zip(now['bounds_mm'],old['bounds_mm'])]
   passed=now['is_valid'] and now['solid_count']==old['solid_count'] and abs(dv)<=1e-7 and max(map(abs,db))<=1e-7
   group[label]={'STEP':ref,'signature':now,'volume_delta_mm3':dv,'bounds_delta_mm':db,'passed':passed}
   require(passed,'pilot STEP complete signature differs');return body
  parts={name:read(entry,base,name,r['body_readbacks']) for name,entry in sorted(original['body_exports'].items())}
  require(set(parts)==set(original['participant_names']) and len(parts)==154,'complete pilot STEP inventory differs')
  oldpanel=read(original['candidate_material_exports']['original_panel'],base,'original_panel',r['candidate_material_readbacks'])
  r['original_panel_to_actual_K1_material']={}
  for pose,root in (('near',a.k1_near),('far',a.k1_far)):
   prior=json.loads((root/'factory/worker/report.engineering.json').read_text())['engineering_record']
   body=read(prior['body_exports']['A_BACK_PANEL'],(root/'factory/worker').resolve(),'K1_'+pose+'_panel',r['candidate_material_readbacks'])
   r['original_panel_to_actual_K1_material'][pose]=adapter.compare(body,oldpanel,p)
  spec=original['pose_input'];q={s:cam.K*spec['slide']+x for s,x in zip('LR',spec['key_offsets'])}
  r['candidate_q0_material_comparisons']={s:adapter.compare(parts[s+'_KEY'].translate((0.,-q[s],0.)),keys.candidate_q0[s],p) for s in 'LR'}
  r['status']='independent_reconstruction_and_all_early_gate_measurements';atomic(out/'report.json',r)
  def emit(rows):r['independent_early_gate_records']=rows;atomic(out/'report.json',r)
  rows,materials=independent.all_checks(parts,oldpanel,keys,design,q,p,cq,budget,emit)
  require(len(rows)==18,'all independent connection/functional/contact/negative-control gates required')
  r['pilot_preconditions_passed']=bool(rows and all(x['evaluated'] and x['passed'] for x in rows.values()))
  r['independent_native_evaluation_failures']=[name for name,x in rows.items() if not x['evaluated']]
  (out/'materials').mkdir()
  for label,body in materials.items():r['candidate_material_exports'][label]=export(body,out/'materials'/label,p,budget)
  r['producer_reader_precondition_classification_consistent']=r['pilot_preconditions_passed']==original['pilot_preconditions_passed']
  if original['pilot_preconditions_passed'] and original.get('all_panel_pairs_present_once'):
   r['status']='independent_replay_of_all_changed_panel_pairs';atomic(out/'report.json',r)
   common.panel_pairs(parts,out,r,p,budget,original=original)
  else:r['panel_pairs_not_evaluated_reason']='producer early gate rejected; whole-matrix campaign remains blocked'
  r['identity_after']=identity.finish(before,[*executed])
  require(r['identity_after']['source_bytes_and_locked_environment_unchanged'],'reader source/runtime changed')
  require(all(sha(k)==v for k,v in r['external_source_sha256'].items()),'reader external source changed')
  r['execution_completed']=bool(not r['evaluation_failures'] and not r['mismatches_to_factory'])
  r['pilot_clear']=bool(r['execution_completed'] and r['producer_reader_precondition_classification_consistent']
   and r['pilot_preconditions_passed'] and original.get('pilot_clear') is True and r.get('pilot_panel_pairs_clear'))
  r['status']='complete_pilot_clear' if r['pilot_clear'] else 'complete_pilot_rejected'
 except BaseException as exc:
  r['failure_stage']=r.get('status');r['status']='failed_or_interrupted';r['failure']=type(exc).__name__+': '+str(exc)
 finally:
  r['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',r)
 print(json.dumps({k:r.get(k) for k in ('status','execution_completed','pilot_clear','pilot_preconditions_passed','seconds')}),flush=True)
 return 0 if r['execution_completed'] else 2

if __name__=='__main__':raise SystemExit(main())
