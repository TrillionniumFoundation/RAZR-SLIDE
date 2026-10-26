"""Check complete actual endpoint execution separately from finite clearance."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from k2_endpoints import ENDPOINTS,REMAINING


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True)
    ap.add_argument('--pose',choices=tuple(ENDPOINTS),required=True);a=ap.parse_args()
    n=ENDPOINTS[a.pose]['expected_bodies'];count=n*(n-1)//2;results={}
    for name in ('factory','readback'):
        c=json.loads((a.case/name/'controller.json').read_text());path=a.case/name/'worker/report.json';r=json.loads(path.read_text())
        assert c['completed'] is True and c['worker_exit_code']==0
        assert all(c[k] is True for k in ('owned_child_identity_verified','source_bytes_unchanged','locked_environment_unchanged','owned_channel_descriptors_closed'))
        assert c['limits']['wall_seconds']==1200 and c['limits']['worker_peak_RSS_MiB']==1536 and c['limits']['shared_unreclaimable_GiB']==6.8
        assert c['result_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        assert r['functional_source_commit']=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560' and r['pose']==a.pose
        assert r['candidate_name']=='key_forward_loop_v1' and r['execution_completed'] is True
        assert r['all_unordered_pairs_present_once'] and r['expected_pair_count']==r['persisted_pair_count']==len(r['pairs'])==count
        assert len(r['participant_names'])==n and not r['evaluation_failures'] and not r['mismatches_to_factory']
        assert r['identity_before']['repository_head_at_start']==r['identity_after']['repository_head_at_finish']==r['functional_source_commit']
        assert not r['identity_before']['worktree_status_at_start'] and r['identity_after']['source_bytes_and_locked_environment_unchanged']
        assert all(r[k] is False for k in ('complete_product_motion_proved','continuous_backlash_domain_proved','physical_qualification',
            'candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass'))
        journal=[json.loads(x) for x in (a.case/name/'worker/pairs.jsonl').read_text().splitlines()]
        assert len(journal)==2*count and [x['row'] for x in journal if x['event']=='completed']==r['pairs']
        if name=='readback':
            assert len(r['body_readbacks'])==n and all(x['passed'] for x in r['body_readbacks'].values())
            assert set(r['candidate_q0_material_comparisons'])=={'L','R'} and r['native_STEP_readback_executed'] is True
        results[name]={'original_report_sha256':c['result_sha256'],'seconds':r['seconds'],'participants':n,'pairs':count,
            'finite_pose_clear':r['finite_pose_clear'],'panel_KEY_direct_Common':r['panel_KEY_direct_Common'],
            'positive_pairs':[{'a':x['a'],'b':x['b'],'common_mm3':x['common_mm3'],'rejected':x['rejected']} for x in r['positive_pairs']],
            'method_counts':dict(Counter(x['method'] for x in r['pairs']))}
    summary={'schema':'razr-K2-complete-endpoint-observation-v1','pose':a.pose,'declared_finite_pose':ENDPOINTS[a.pose],
        'results':results,'finite_endpoint_clear':all(x['finite_pose_clear'] for x in results.values()),
        'complete_motion_or_hardware_qualification':False,'remaining_unproved_domains':list(REMAINING),
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (a.case/'K2-complete-observation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,sort_keys=True),flush=True)


if __name__=='__main__':main()
