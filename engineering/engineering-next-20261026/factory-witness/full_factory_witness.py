"""Actually construct the complete S4 factory at an L1-derived finite witness."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from fractions import Fraction
import json
from pathlib import Path
from f1_common import *

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pose',choices=tuple(Q),required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out,report,budget=start(__file__,args.output,args.pose)
    try:
        before=identity.snapshot();executed=identity.record_executed_project_files();report['identity_before']=before
        import product_nominal_motion as nominal
        import product_routing_ep5 as ep5
        import verify_cam_coupling as cam
        import body_inventory
        p=nominal.p;q=Q[args.pose];s=q*Fraction('79.75')/12;slide=float(s)
        q_factory=cam.K*slide
        report['pose_input']={'q_L1_exact_mm':str(q),'q_L1_binary64_mm':float(q),'q_L1_binary64_hex':float(q).hex(),
              'slide_exact_from_rational_ratio_mm':str(s),'slide_mm':slide,'slide_binary64_hex':slide.hex(),
              'native_cam_K':cam.K,'native_q_from_K_times_slide_mm':q_factory,'native_q_binary64_hex':q_factory.hex(),
              'native_q_minus_L1_binary64_mm':q_factory-float(q),'descent_mm':0.,'tabs_mm':[3.,3.],
              'flanks':[0.,0.],'KEY_offsets_mm':[0.,0.],'crosshead_offsets_mm':[0.,0.],
              'telescope_allocation':'factory nominal equal allocation; not physically enforced',
              'open_hold':False,'open_support':False,'same_bit_pattern_as_L1_not_assumed':True}
        report['status']='building_complete_factory';atomic(out/'report.json',report);budget.check()
        parts,metadata=nominal.full_scene(slide,0.,3.,3.,flanks=(0.,0.),key_offsets=(0.,0.),crosshead_offsets=(0.,0.),open_hold=False,open_support=False)
        ep5.validate_factory_input_coverage(metadata['scene'],before['available_source_sha256'])
        require(len(parts)==154,'complete 154-body S4 factory expected')
        report.update(actual_complete_factory_called=True,native_scene_metadata=metadata,participant_count=len(parts),
                      nominal_inventory=body_inventory.measure(parts,metadata,p),fixed_pair_certificate_reused=False,
                      whole_motion_claimed=False,geometry_repair_applied=False,status='exporting_complete_factory')
        profiles=p.native_inputs()[4];profile_rows={}
        for side in 'LR':
            profile_rows[side]=[]
            for i,profile in enumerate(profiles[side]):
                breaks=[0.,*profile.breakpoints,profile.q_max]
                profile_rows[side].append({'stop_index':i,'parameters':asdict(profile),'receipt':profile.receipt(),
                    'current_q_state':profile.evaluate(q_factory),'baseline_q0_state':profile.evaluate(0.),
                    'segments':[{'closed_q_interval_mm':[lo,hi],'midpoint_branch':profile.evaluate((lo+hi)/2)[2],
                                 'height_bounds_mm':list(profile.height_bounds(lo,hi))} for lo,hi in zip(breaks[:-1],breaks[1:])],
                    'actual_STOP_signature':signature(parts[f'{side}_STOP_{i}'],p),
                    'actual_SPRING_envelope_signature':signature(parts[f'{side}_SPRING_{i}_OD_TOL_ENVELOPE'],p)})
        report['native_positive_q_STOP_SPRING_profiles']=profile_rows
        report['body_exports']={};(out/'bodies').mkdir()
        for name,body in sorted(parts.items()):
            report['body_exports'][name]=export(body,out/'bodies'/name,p,budget)
            if len(report['body_exports'])%16==0:atomic(out/'report.json',report)
        report['panel_KEY_direct_Common']={}
        for side in 'LR':
            name=side+'_KEY';common=parts['A_BACK_PANEL'].intersect(parts[name]);value=p.volume(common)
            row={'a':'A_BACK_PANEL','b':name,'common_mm3':value,'rejected':value>1e-7,
                 'common_bounds_mm':list(p.bounds(common)) if value>0 else None,
                 'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[name])}
            if value>0:row['export']=export(common,out/(side+'-panel-KEY-direct-Common'),p,budget)
            report['panel_KEY_direct_Common'][side]=row
        report['status']='evaluating_all_factory_pairs';atomic(out/'report.json',report)
        evaluate_pairs(parts,out,report,p,budget)
        report['identity_after']=identity.finish(before,[*executed,body_inventory.__file__])
        require(report['identity_after']['source_bytes_and_locked_environment_unchanged'],'S4 source/input/runtime changed')
        require(all(sha(k)==v for k,v in report['external_source_sha256'].items()),'external experiment source changed')
        report['execution_completed']=bool(report['all_unordered_pairs_present_once'] and not report['evaluation_failures'])
        report['status']='complete' if report['execution_completed'] else 'completed_with_evaluation_failures'
    except BaseException as exc:
        report['status']='failed_or_interrupted';report['failure']=type(exc).__name__+': '+str(exc)
    finally:
        report['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',report)
    print(json.dumps({k:report.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','failure','seconds')}),flush=True)
    return 0 if report['execution_completed'] else 2

if __name__=='__main__':raise SystemExit(main())
