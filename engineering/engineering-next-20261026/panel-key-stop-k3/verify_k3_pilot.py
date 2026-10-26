"""Preserve actual pilot completion separately from candidate acceptance."""
from __future__ import annotations
import argparse,hashlib,itertools,json
from pathlib import Path
from k3_pilot_states import PILOTS,REMAINING

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True)
 ap.add_argument('--pose',choices=tuple(PILOTS),required=True);a=ap.parse_args();results={};failures=[]
 for mode in ('factory','readback'):
  cp=a.case/mode/'controller.json';rp=a.case/mode/'worker/report.json'
  if not cp.is_file() or not rp.is_file():
   results[mode]={'present':False,'execution_completed':False,'pilot_clear':False};failures.append(mode+'_missing');continue
  c=json.loads(cp.read_text());r=json.loads(rp.read_text());result={'present':True,'original_report_sha256':hashlib.sha256(rp.read_bytes()).hexdigest(),
   'execution_completed':r.get('execution_completed') is True,'pilot_clear':r.get('pilot_clear') is True,
   'pilot_preconditions_passed':r.get('pilot_preconditions_passed') is True,'status':r.get('status'),
   'original_failure_stage':r.get('failure_stage'),'seconds':r.get('seconds'),'panel_pair_count':len(r.get('pairs',[])),
   'precondition_failures':r.get('precondition_failures',[]),
   'independent_early_gate_records':r.get('independent_early_gate_records'),
   'positive_panel_pairs':[{'a':x['a'],'b':x['b'],'common_mm3':x['common_mm3'],'rejected':x['rejected']} for x in r.get('positive_pairs',[])],
   'factory_reader_precondition_consistent':r.get('producer_reader_precondition_classification_consistent')}
  results[mode]=result
  try:
   assert c['completed'] is True and c['worker_exit_code']==0 and c['result_sha256']==result['original_report_sha256']
   assert all(c[x] is True for x in ('owned_child_identity_verified','source_bytes_unchanged','locked_environment_unchanged','owned_channel_descriptors_closed'))
   assert c['limits']=={'wall_seconds':1200,'worker_peak_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,'runtime_disk_reserve_MiB':100,'startup_disk_reserve_MiB':256,'startup_additional_memory_MiB':2048}
   assert r['functional_source_commit']=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560' and r['pose']==a.pose and r['candidate_name']=='panel_key_travel_stops_v1'
   assert r['execution_completed'] is True and len(r['participant_names'])==len(set(r['participant_names']))==154
   assert r['identity_before']['repository_head_at_start']==r['identity_after']['repository_head_at_finish']==r['functional_source_commit']
   assert not r['identity_before']['worktree_status_at_start'] and r['identity_after']['source_bytes_and_locked_environment_unchanged'] is True
   assert all(r[x] is False for x in ('complete_product_motion_proved','continuous_backlash_domain_proved','physical_qualification','candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass','all_unordered_pairs_present_once','finite_pose_clear','full_ten_state_campaign_authorized'))
   if r.get('all_panel_pairs_present_once'):
    expected=[('A_BACK_PANEL',x) for x in sorted(r['participant_names']) if x!='A_BACK_PANEL']
    assert len(expected)==153 and [(x['a'],x['b']) for x in r['pairs']]==expected
    assert not r['evaluation_failures'] and not r['mismatches_to_factory']
    journal=[json.loads(x) for x in (a.case/mode/'worker/pairs.jsonl').read_text().splitlines()]
    assert len(journal)==306 and [x['row'] for x in journal if x['event']=='completed']==r['pairs']
   else:assert not r['pairs'] and not r['pilot_clear']
   if mode=='readback':
    assert len(r['body_readbacks'])==154 and all(x['passed'] for x in r['body_readbacks'].values())
    gates=r['independent_early_gate_records'];assert len(gates)==18
    assert r['pilot_preconditions_passed']==all(x['evaluated'] and x['passed'] for x in gates.values())
   derived_clear=bool(r['pilot_preconditions_passed'] and r.get('all_panel_pairs_present_once') and not r['evaluation_failures'] and not r['mismatches_to_factory'] and not any(x.get('rejected') for x in r['pairs']))
   if mode=='readback':derived_clear=derived_clear and r['producer_reader_precondition_classification_consistent'] and results['factory']['pilot_clear']
   assert r['pilot_clear']==derived_clear
  except Exception as exc:failures.append(mode+'_completion_contract_failed')
 complete=not failures;clear=complete and all(x['pilot_clear'] for x in results.values())
 summary={'schema':'razr-K3-preliminary-pilot-observation-v1','pose':a.pose,'declared_pose':PILOTS[a.pose],
  'complete_scientific_pilot_execution':complete,'actual_finite_pilot_clear':clear,'results':results,'completion_failures':failures,
  'full_pair_count_per_pose_required_later':11781,'full_pair_matrix_executed':False,
  'full_ten_state_campaign_authorized':False,'remaining_unproved_domains':list(REMAINING),
  'complete_product_motion_proved':False,'physical_allowed_domain_proved':False,'strength_qualified':False,
  'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
 (a.case/'K3-pilot-observation.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
 print(json.dumps(summary,sort_keys=True),flush=True)
 return 0 if complete else 2

if __name__=='__main__':raise SystemExit(main())
