"""Complete named-candidate endpoint factory, gated by actual dual-clear K1."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from f1_common import *
import frozen_key_factory_adapter as adapter
import k2_endpoints as endpoints


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pose',choices=tuple(endpoints.ENDPOINTS),required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--k1-near',type=Path,required=True)
    ap.add_argument('--k1-far',type=Path,required=True)
    ap.add_argument('--binding',type=Path,required=True)
    args=ap.parse_args();out,r,budget=start(__file__,args.output,args.pose)
    r.update(schema='razr-K2-complete-endpoint-factory-v1',candidate_name=adapter.NAME,
        finite_nominal_endpoint_only=True,remaining_unproved_domains=list(endpoints.REMAINING))
    r['external_source_sha256'].update({str(Path(p).resolve()):sha(p) for p in (adapter.__file__,endpoints.__file__,args.binding)})
    try:
        before=identity.snapshot();executed=identity.record_executed_project_files();r['identity_before']=before
        import cadquery as cq
        import product_nominal_motion as nominal
        import product_routing_ep5 as ep5
        import verify_cam_coupling as cam
        import body_inventory
        p=nominal.p;binding=json.loads(args.binding.read_text())
        r['status']='verifying_actual_K1_dual_clear_whole_material';atomic(out/'report.json',r)
        keys=adapter.load_keys({'near':args.k1_near,'far':args.k1_far},binding,p,cq,budget)
        spec=dict(endpoints.ENDPOINTS[args.pose]);expected=spec.pop('expected_bodies')
        spec.update(flanks=(0.,0.),key_offsets=(0.,0.),crosshead_offsets=(0.,0.),telescope_offsets=None)
        r['pose_input']=spec;r['status']='building_actual_complete_endpoint_factory';atomic(out/'report.json',r)
        parts,meta=adapter.full_scene(keys,nominal,cam,p,**spec)
        ep5.validate_factory_input_coverage(meta['scene'],before['available_source_sha256'])
        require(len(parts)==expected,'complete endpoint body inventory differs')
        inventory=body_inventory.measure(parts,meta,p)
        for side in 'LR':
            inventory[side+'_KEY']['source_functions'].append('frozen_key_factory_adapter.py:full_scene')
            inventory[side+'_KEY']['named_research_candidate']=adapter.NAME
            inventory[side+'_KEY']['candidate_source_sha256']=keys.receipt['candidate_source_sha256']
        r.update(actual_complete_factory_called=True,participant_count=len(parts),
            native_scene_metadata=meta,candidate_inventory=inventory,K1_prerequisite=keys.receipt,
            fixed_pair_certificate_reused=False,geometry_repair_applied=True,whole_motion_claimed=False,
            body_exports={},status='exporting_all_endpoint_bodies')
        (out/'bodies').mkdir()
        for name,body in sorted(parts.items()):
            r['body_exports'][name]=export(body,out/'bodies'/name,p,budget)
            if len(r['body_exports'])%16==0:atomic(out/'report.json',r)
        r['panel_KEY_direct_Common']={}
        for side in 'LR':
            body=parts['A_BACK_PANEL'].intersect(parts[side+'_KEY']);v=p.volume(body)
            row={'a':'A_BACK_PANEL','b':side+'_KEY','common_mm3':v,'rejected':v>1e-7,
                'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[side+'_KEY'])}
            if v>0:row['export']=export(body,out/(side+'-panel-KEY-direct-Common'),p,budget)
            r['panel_KEY_direct_Common'][side]=row
        r['status']='evaluating_all_endpoint_pairs';atomic(out/'report.json',r)
        evaluate_pairs(parts,out,r,p,budget)
        r['identity_after']=identity.finish(before,[*executed,body_inventory.__file__])
        require(r['identity_after']['source_bytes_and_locked_environment_unchanged'],'S4 source/input/runtime changed')
        require(all(sha(k)==v for k,v in r['external_source_sha256'].items()),'external endpoint sources changed')
        r['execution_completed']=bool(r['all_unordered_pairs_present_once'] and not r['evaluation_failures'])
        r['status']='complete' if r['execution_completed'] else 'completed_with_evaluation_failures'
    except BaseException as exc:
        r['failure_stage']=r.get('status');r['status']='failed_or_interrupted';r['failure']=type(exc).__name__+': '+str(exc)
    finally:
        r['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',r)
    print(json.dumps({k:r.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','failure','seconds')}),flush=True)
    return 0 if r['execution_completed'] else 2


if __name__=='__main__':raise SystemExit(main())
