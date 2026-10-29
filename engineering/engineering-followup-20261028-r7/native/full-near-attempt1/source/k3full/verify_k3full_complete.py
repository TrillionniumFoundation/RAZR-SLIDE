"""Verify all freshly evaluated body pairs; keep finite failure and undecided gates."""
from __future__ import annotations
import argparse,hashlib,itertools,json
from collections import Counter
from pathlib import Path
from full_stop_states import STATES,EXPECTED_CONTACT_ENDS,REMAINING

LIMITS={'wall_seconds':1200,'worker_peak_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,'runtime_disk_reserve_MiB':100,'startup_disk_reserve_MiB':256,'startup_additional_memory_MiB':2048}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True);ap.add_argument('--pose',choices=tuple(STATES),required=True)
 a=ap.parse_args();expected=STATES[a.pose]['expected_bodies'];count=expected*(expected-1)//2;results={};errors=[]
 for mode in ('factory','readback'):
  cp=a.case/mode/'controller.json';rp=a.case/mode/'worker/report.json'
  if not cp.is_file() or not rp.is_file():results[mode]={'present':False,'execution_completed':False,'finite_pose_clear':False};errors.append(mode+'_missing');continue
  c=json.loads(cp.read_text());r=json.loads(rp.read_text())
  result={'present':True,'original_report_sha256':hashlib.sha256(rp.read_bytes()).hexdigest(),'execution_completed':r.get('execution_completed') is True,
   'finite_pose_clear':r.get('finite_pose_clear') is True,'status':r.get('status'),'failure_stage':r.get('failure_stage'),
   'seconds':r.get('seconds'),'body_count':r.get('participant_count'),'pair_count':len(r.get('pairs',[])),
   'actual_q_by_side_mm':r.get('actual_q_by_side_mm'),'expected_contacts':EXPECTED_CONTACT_ENDS[a.pose],
   'native_early_conditions_rechecked':r.get('native_early_conditions_rechecked') is True,
   'independent_native_evaluation_failures':r.get('independent_native_evaluation_failures',[]),
   'independent_geometric_gate_rejections':r.get('independent_geometric_gate_rejections',[]),
   'positive_pairs':[{'a':x['a'],'b':x['b'],'common_mm3':x['common_mm3'],'rejected':x['rejected']} for x in r.get('positive_pairs',[])],
   'pair_evaluation_failures':r.get('evaluation_failures',[]),'pair_readback_mismatches':r.get('mismatches_to_factory',[]),
   'method_counts':dict(Counter(x.get('method','evaluation_failed') for x in r.get('pairs',[])))};results[mode]=result
  try:
   assert c['completed'] is True and c['worker_exit_code']==0 and c['result_sha256']==result['original_report_sha256'] and c['limits']==LIMITS
   assert all(c[k] is True for k in ('owned_child_identity_verified','source_bytes_unchanged','locked_environment_unchanged','owned_channel_descriptors_closed'))
   assert r['functional_source_commit']=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560' and r['pose']==a.pose and r['candidate_name']=='panel_key_travel_stops_v1'
   assert r['execution_completed'] is True and len(r['participant_names'])==len(set(r['participant_names']))==expected
   assert r['all_unordered_pairs_present_once'] is True and r['expected_pair_count']==r['persisted_pair_count']==len(r['pairs'])==count
   assert [(x['a'],x['b']) for x in r['pairs']]==list(itertools.combinations(sorted(r['participant_names']),2))
   assert not r['evaluation_failures'] and not r['mismatches_to_factory']
   assert r['identity_before']['repository_head_at_start']==r['identity_after']['repository_head_at_finish']==r['functional_source_commit']
   assert not r['identity_before']['worktree_status_at_start'] and r['identity_after']['source_bytes_and_locked_environment_unchanged'] is True
   assert all(r[k] is False for k in ('complete_product_motion_proved','continuous_backlash_domain_proved','physical_qualification','candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass'))
   journal=[json.loads(x) for x in (a.case/mode/'worker/pairs.jsonl').read_text().splitlines()]
   assert len(journal)==2*count and [x['row'] for x in journal if x['event']=='completed']==r['pairs']
   if mode=='readback':
    assert len(r['body_readbacks'])==expected and all(x['passed'] for x in r['body_readbacks'].values())
    gates=r['independent_early_gate_records'];assert len(gates)==12+3*sum(v is not None for v in EXPECTED_CONTACT_ENDS[a.pose].values())
    assert r['native_early_conditions_rechecked']==all(x['evaluated'] and x['passed'] for x in gates.values())
   assert r['finite_pose_clear']==bool(r['native_early_conditions_rechecked'] and not any(x.get('rejected') for x in r['pairs']))
  except Exception:errors.append(mode+'_complete_execution_contract_failed')
 complete=not errors
 summary={'schema':'razr-K3FULL-complete-finite-state-observation-v1','pose':a.pose,'declared_pose':STATES[a.pose],
  'results':results,'expected_pair_count_per_worker':count,'complete_full_pair_execution':complete,
  'finite_state_clear':complete and all(x['finite_pose_clear'] for x in results.values()),'completion_failures':errors,
  'remaining_unproved_domains':list(REMAINING),'full_continuous_motion_proved':False,'physical_allowed_domain_proved':False,
  'strength_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
 (a.case/'K3FULL-complete-observation.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');print(json.dumps(summary,sort_keys=True),flush=True)
 return 0 if complete else 2

if __name__=='__main__':raise SystemExit(main())
