"""Actual dual-clear K3 pilot input verifier; no candidate builder import."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,itertools,json
from pathlib import Path
import frozen_key_factory_adapter as keys_adapter

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
NAME='panel_key_travel_stops_v1'

def require(ok,message):
 if not ok:raise ValueError(message)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
 return h.hexdigest()

@dataclass(frozen=True)
class VerifiedStops:
 original_panel:object
 candidate_panel:object
 keys:object
 receipt:dict

def load(roots,binding,key_binding,p,cq,budget):
 require(binding['actual_two_complete_pilots_reviewed_clear'] is True and binding['run_id']==40281153812
  and binding['head_sha']=='4497cfb9726d26d2b1452008ac23b6b0ec9b6223','actual complete dual K3 pilot required')
 require(set(roots)==set(binding['poses'])=={'stow_tabs_3','predock'},'both actual finite K3 pilot originals required')
 panels={};originals={};receipts={}
 for pose in ('stow_tabs_3','predock'):
  root=Path(roots[pose]).resolve();manifest=root/'ENGINEERING_MANIFEST.json'
  require(sha(manifest)==binding['poses'][pose]['engineering_manifest_sha256'],'frozen K3 engineering manifest differs')
  members=json.loads(manifest.read_text())['members']
  require({str(x.relative_to(root)) for x in root.rglob('*') if x.is_file()}==set(members)|{'ENGINEERING_MANIFEST.json'},'complete K3 engineering member set differs')
  for rel,ref in members.items():
   path=(root/rel).resolve()
   require(path.is_relative_to(root) and path.is_file() and not path.is_symlink() and sha(path)==ref['sha256'] and path.stat().st_size==ref['bytes'],'complete actual K3 byte identity differs')
  reports={};wrappers={}
  for mode in ('factory','readback'):
   rp=root/mode/'worker/report.engineering.json';w=json.loads(rp.read_text());r=w['engineering_record'];reports[mode]=r;wrappers[mode]=w
   require(w['derived_projection_not_raw_original'] is True and w['original']['sha256']==binding['poses'][pose]['original_report_sha256'][mode]
    and sha(rp)==binding['poses'][pose]['projection_sha256'][mode],'frozen actual K3 projection identity differs')
   require(r['functional_source_commit']==S4 and r['pose']==pose and r['candidate_name']==NAME and r['candidate_source_sha256']==binding['candidate_source_sha256']
    and r['candidate_contract_sha256']==binding['contract_sha256'],'K3 candidate source or contract differs')
   require(r['execution_completed'] is True and r['pilot_clear'] is True and r['pilot_preconditions_passed'] is True
    and r['all_panel_pairs_present_once'] is True and not r['evaluation_failures'] and not r['mismatches_to_factory'],'complete actual K3 pilot clearance absent')
   require(len(r['participant_names'])==len(set(r['participant_names']))==154 and [(x['a'],x['b']) for x in r['pairs']]==[('A_BACK_PANEL',x) for x in sorted(r['participant_names']) if x!='A_BACK_PANEL']
    and all(not x['rejected'] and 0<=x['common_mm3']<=1e-7 for x in r['pairs']),'K3 actual 153 changed-panel pair clearance differs')
   ident=r['source_identity_projection']
   require(ident['source_commit_before']==ident['source_commit_after']==S4 and ident['worktree_clean_before'] is True
    and ident['source_bytes_and_locked_environment_unchanged'] is True and ident['locked_environment_before_passed'] is True
    and ident['locked_environment_after_passed'] is True and ident['checked_package_count_before']==ident['checked_package_count_after']==43,
    'actual K3 original source/environment audit incomplete')
  factory=reports['factory'];reader=reports['readback']
  require(reader['factory_report_sha256']==wrappers['factory']['original']['sha256'],'K3 original independent reader mismatch')
  gates=reader['independent_early_gate_records']
  require(len(gates)==18 and all(x['evaluated'] is True and x['passed'] is True for x in gates.values())
   and reader['producer_reader_precondition_classification_consistent'] is True and not reader['independent_native_evaluation_failures'],
   'actual K3 geometric rejection, evaluation unresolved or classification disagreement blocks full campaign')
  require(len(reader['body_readbacks'])==154 and all(x['passed'] for x in reader['body_readbacks'].values())
   and reader['native_STEP_readback_executed'] is True and reader['independent_material_builder_does_not_import_candidate_source'] is True,'complete independent K3 STEP readback absent')
  def read(entry):
   budget.check();ref=entry['files']['step'];path=(root/'factory/worker'/ref['path']).resolve()
   require(path.is_relative_to(root) and sha(path)==ref['sha256'] and path.stat().st_size==ref['bytes'],'actual K3 whole panel STEP differs')
   values=cq.importers.importStep(str(path)).vals();require(len(values)==1,'one actual whole panel STEP root required')
   return p.single(values[0])
  panels[pose]=read(factory['body_exports']['A_BACK_PANEL'])
  originals[pose]=read(factory['candidate_material_exports']['original_panel'])
  receipts[pose]={'engineering_manifest_sha256':sha(manifest),'original_report_sha256':{mode:wrappers[mode]['original']['sha256'] for mode in wrappers},
   'original_panel_material_account':factory['candidate_application']['actual_added_only_panel_account'],
   'all_18_independent_native_gates_true':True,'both_153_pair_originals_clear':True}
 agreement={'original_panel':keys_adapter.compare(originals['stow_tabs_3'],originals['predock'],p),
  'candidate_panel':keys_adapter.compare(panels['stow_tabs_3'],panels['predock'],p)}
 # K1 originals are complete nested engineering exports, not fabricated raw runtime.
 key_roots={pose:Path(roots['stow_tabs_3'])/('prerequisite-'+pose) for pose in ('near','far')}
 keys=keys_adapter.load_keys(key_roots,key_binding,p,cq,budget)
 return VerifiedStops(originals['stow_tabs_3'],panels['stow_tabs_3'],keys,{
  'candidate_name':NAME,'candidate_source_sha256':binding['candidate_source_sha256'],'contract_sha256':binding['contract_sha256'],
  'actual_dual_pilot_run_id':binding['run_id'],'actual_dual_pilot_head_sha':binding['head_sha'],
  'actual_pilot_originals':receipts,'complete_two_pose_panel_material_identity':agreement,
  'actual_K1_prerequisite':keys.receipt,'raw_runtime_report_reconstructed':False,
  'full_all_pair_campaign_proved_by_prerequisite':False,'physical_allowed_domain_proved':False,'strength_qualified':False})
