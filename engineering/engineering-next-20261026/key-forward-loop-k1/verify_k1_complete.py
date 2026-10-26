"""Check complete K1 evidence without promoting finite geometry to qualification."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',type=Path,required=True)
    ap.add_argument('--pose',choices=('near','far'),required=True)
    args=ap.parse_args();case=args.case;results={}
    for kind in ('factory','readback'):
        controller=json.loads((case/kind/'controller.json').read_text())
        path=case/kind/'worker/report.json';r=json.loads(path.read_text())
        assert controller['completed'] is True and controller['worker_exit_code']==0
        assert all(controller[k] is True for k in ('owned_child_identity_verified','source_bytes_unchanged',
            'locked_environment_unchanged','owned_channel_descriptors_closed'))
        assert controller['limits']['wall_seconds']==1200 and controller['limits']['worker_peak_RSS_MiB']==1536
        assert controller['limits']['shared_unreclaimable_GiB']==6.8
        assert controller['result_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        assert r['functional_source_commit']=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
        assert r['candidate_name']=='key_forward_loop_v1' and r['pose']==args.pose and r['execution_completed'] is True
        assert r['all_unordered_pairs_present_once'] and r['expected_pair_count']==len(r['pairs'])==r['persisted_pair_count']==11781
        assert len(r['participant_names'])==154 and not r['evaluation_failures'] and not r['mismatches_to_factory']
        assert r['identity_before']['repository_head_at_start']==r['functional_source_commit']
        assert not r['identity_before']['worktree_status_at_start']
        assert r['identity_after']['source_bytes_and_locked_environment_unchanged']
        assert r['identity_after']['repository_head_at_finish']==r['functional_source_commit']
        assert all(r[k] is False for k in ('complete_product_motion_proved','continuous_backlash_domain_proved',
            'physical_qualification','candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass'))
        journal=[json.loads(x) for x in (case/kind/'worker/pairs.jsonl').read_text().splitlines()]
        assert len(journal)==23562 and [x['row'] for x in journal if x['event']=='completed']==r['pairs']
        results[kind]={'report_sha256':controller['result_sha256'],'seconds':r['seconds'],'pairs':len(r['pairs']),
            'finite_pose_clear':r['finite_pose_clear'],'panel_KEY_direct_Common':r['panel_KEY_direct_Common'],
            'positive_pairs':[{'a':x['a'],'b':x['b'],'common_mm3':x['common_mm3'],'rejected':x['rejected']} for x in r['positive_pairs']],
            'method_counts':dict(Counter(x['method'] for x in r['pairs']))}
        if kind=='factory':
            assert len(r['original_baseline_material_comparisons'])==154
            assert all(x['equal_within_original_1e_minus_7_mm3'] for x in r['original_baseline_material_comparisons'].values())
            results[kind]['baseline_panel_KEY_direct_Common']=r['baseline_panel_KEY_direct_Common']
            results[kind]['material_accounts']=r['candidate_application']['material_accounts']
        else:
            assert len(r['body_readbacks'])==154 and all(x['passed'] for x in r['body_readbacks'].values())
            assert set(r['material_reconstruction'])=={'L_KEY','R_KEY'} and all(x['passed'] for x in r['material_reconstruction'].values())
            assert r['independent_material_builder_does_not_import_candidate_source'] is True
            assert r['native_STEP_readback_executed'] is True and r['independent_CAD_kernel'] is False
    observation={'schema':'razr-K1-complete-finite-observation-v1','pose':args.pose,'results':results,
        'all_154_baseline_bodies_compared_as_whole_material_to_F1a':True,
        'all_154_candidate_STEP_bodies_independently_imported':True,
        'all_11781_pairs_recomputed_from_imported_STEP':True,
        'independent_removed_added_and_retained_material_account_rebuilt':True,
        'finite_witness_clear':all(x['finite_pose_clear'] for x in results.values()),
        'both_witnesses_clear_not_inferred_from_this_one_pose':True,
        'continuous_motion_or_hardware_qualification':False,'strength_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (case/'K1-complete-observation.json').write_text(json.dumps(observation,indent=2)+'\n')
    print(json.dumps(observation,sort_keys=True),flush=True)


if __name__=='__main__':main()
