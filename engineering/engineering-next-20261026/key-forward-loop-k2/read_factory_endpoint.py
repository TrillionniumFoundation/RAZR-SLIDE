"""Independent whole STEP/all-pair endpoint reader and frozen KEY comparison."""
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
    ap.add_argument('--factory-report',type=Path,required=True)
    ap.add_argument('--k1-near',type=Path,required=True)
    ap.add_argument('--k1-far',type=Path,required=True)
    ap.add_argument('--binding',type=Path,required=True)
    args=ap.parse_args();out,r,budget=start(__file__,args.output,args.pose)
    r.update(schema='razr-K2-independent-endpoint-STEP-reader-v1',candidate_name=adapter.NAME,
        finite_nominal_endpoint_only=True,remaining_unproved_domains=list(endpoints.REMAINING))
    r['external_source_sha256'].update({str(Path(p).resolve()):sha(p) for p in (adapter.__file__,endpoints.__file__,args.binding)})
    try:
        original=json.loads(args.factory_report.read_text());base=args.factory_report.parent.resolve()
        expected=endpoints.ENDPOINTS[args.pose]['expected_bodies']
        require(original['functional_source_commit']==S4 and original['candidate_name']==adapter.NAME
                and original['pose']==args.pose and original['execution_completed'] is True
                and original['participant_count']==expected and original['all_unordered_pairs_present_once'],
                'complete actual endpoint factory required')
        before=identity.snapshot();executed=identity.record_executed_project_files();r['identity_before']=before
        import cadquery as cq
        import product_assembly as p
        import verify_cam_coupling as cam
        keys=adapter.load_keys({'near':args.k1_near,'far':args.k1_far},json.loads(args.binding.read_text()),p,cq,budget)
        r.update(K1_prerequisite=keys.receipt,factory_report_sha256=sha(args.factory_report),
            native_STEP_readback_executed=True,separate_process_from_factory=True,independent_CAD_kernel=False,
            body_readbacks={},candidate_q0_material_comparisons={},status='importing_all_endpoint_STEP_bodies')
        parts={}
        for name,entry in sorted(original['body_exports'].items()):
            budget.check();ref=entry['files']['step'];path=(base/ref['path']).resolve()
            require(path.is_relative_to(base) and path.is_file() and not path.is_symlink()
                    and sha(path)==ref['sha256'] and path.stat().st_size==ref['bytes'],'complete endpoint STEP identity differs')
            roots=cq.importers.importStep(str(path)).vals();require(len(roots)==1,'one complete endpoint STEP root required')
            body=p.single(roots[0]);sig=signature(body,p);previous=entry['signature_before']
            dv=sig['signed_volume_mm3']-previous['signed_volume_mm3'];db=[a-b for a,b in zip(sig['bounds_mm'],previous['bounds_mm'])]
            ok=sig['is_valid'] and sig['solid_count']==previous['solid_count'] and abs(dv)<=1e-7 and max(map(abs,db))<=1e-7
            require(ok,'endpoint STEP whole material signature differs')
            r['body_readbacks'][name]={'STEP':ref,'signature':sig,'volume_delta_mm3':dv,'bounds_delta_mm':db,'passed':ok};parts[name]=body
        require(len(parts)==expected and set(parts)==set(original['participant_names']),'complete STEP inventory differs')
        spec=original['pose_input']
        for side,dq in zip('LR',spec['key_offsets']):
            q=cam.K*spec['slide']+dq
            r['candidate_q0_material_comparisons'][side]=adapter.compare(parts[side+'_KEY'].translate((0,-q,0)),keys.candidate_q0[side],p)
        r['status']='evaluating_all_imported_endpoint_pairs';atomic(out/'report.json',r)
        evaluate_pairs(parts,out,r,p,budget,original=original)
        require(not r['mismatches_to_factory'],'independent endpoint all-pair mismatch')
        r['panel_KEY_direct_Common']={}
        for side in 'LR':
            common=parts['A_BACK_PANEL'].intersect(parts[side+'_KEY']);v=p.volume(common)
            row={'a':'A_BACK_PANEL','b':side+'_KEY','common_mm3':v,'rejected':v>1e-7,
                'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[side+'_KEY']),
                'factory_volume_delta_mm3':v-original['panel_KEY_direct_Common'][side]['common_mm3']}
            require(abs(row['factory_volume_delta_mm3'])<=1e-7,'endpoint direct panel/KEY Common differs')
            if v>0:row['export']=export(common,out/(side+'-panel-KEY-direct-Common'),p,budget)
            r['panel_KEY_direct_Common'][side]=row
        r['identity_after']=identity.finish(before,[*executed])
        require(r['identity_after']['source_bytes_and_locked_environment_unchanged'],'endpoint reader S4 source/input/runtime changed')
        require(all(sha(k)==v for k,v in r['external_source_sha256'].items()),'endpoint reader sources changed')
        r['execution_completed']=bool(r['all_unordered_pairs_present_once'] and not r['evaluation_failures'] and not r['mismatches_to_factory'])
        r['status']='complete' if r['execution_completed'] else 'completed_with_readback_failures'
    except BaseException as exc:
        r['failure_stage']=r.get('status');r['status']='failed_or_interrupted';r['failure']=type(exc).__name__+': '+str(exc)
    finally:
        r['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',r)
    print(json.dumps({k:r.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','failure','seconds')}),flush=True)
    return 0 if r['execution_completed'] else 2


if __name__=='__main__':raise SystemExit(main())
