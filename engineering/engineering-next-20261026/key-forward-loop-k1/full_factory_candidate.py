"""Complete immutable-S4 factory with the named KEY forward-loop candidate."""
from __future__ import annotations
import argparse
from fractions import Fraction
import json
from pathlib import Path
from f1_common import *
import k1_evidence
import key_forward_loop_v1 as candidate


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pose', choices=tuple(Q), required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--f1-evidence', type=Path, required=True)
    ap.add_argument('--binding', type=Path, required=True)
    args = ap.parse_args(); out, report, budget = start(__file__, args.output, args.pose)
    report['schema'] = 'razr-S4-K1-full-factory-candidate-v1'
    report['candidate_name'] = candidate.NAME
    report['external_source_sha256'].update({str(Path(x).resolve()):sha(x)
        for x in (candidate.__file__, k1_evidence.__file__, args.binding)})
    try:
        proofs, receipt = k1_evidence.prerequisite(args.f1_evidence, args.binding, args.pose)
        original = proofs['factory']['engineering_record']; report['F1a_prerequisite'] = receipt
        before = identity.snapshot(); executed = identity.record_executed_project_files()
        report['identity_before'] = before
        import cadquery as cq
        import product_nominal_motion as nominal
        import product_routing_ep5 as ep5
        import verify_cam_coupling as cam
        import body_inventory
        p = nominal.p; q = Q[args.pose]; slide = float(q*Fraction('79.75')/12)
        require(slide.hex() == original['pose_input']['slide_binary64_hex'], 'original slide changed')
        require((cam.K*slide).hex() == original['pose_input']['native_q_binary64_hex'], 'original q changed')
        report['pose_input'] = original['pose_input']
        report['status'] = 'building_complete_original_S4_factory'; atomic(out/'report.json', report)
        parts, metadata = nominal.full_scene(slide,0.,3.,3.,flanks=(0.,0.),key_offsets=(0.,0.),crosshead_offsets=(0.,0.),open_hold=False,open_support=False)
        ep5.validate_factory_input_coverage(metadata['scene'], before['available_source_sha256'])
        require(len(parts) == 154, 'complete original S4 factory required')
        report.update(actual_complete_factory_called=True, original_S4_scene_metadata=metadata,
            participant_count=len(parts), fixed_pair_certificate_reused=False,
            whole_motion_claimed=False, geometry_repair_applied=False,
            original_baseline_material_comparisons={})
        baseline = args.f1_evidence.resolve()/'factory/worker'
        # Every original body is compared as whole material with the F1a STEP,
        # not identified merely by matching volume and bounding box.
        for name, body in sorted(parts.items()):
            budget.check(); entry = original['body_exports'][name]['files']['step']
            path = (baseline/entry['path']).resolve()
            require(path.is_relative_to(baseline) and path.is_file() and not path.is_symlink()
                    and sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'],
                    'original complete STEP identity differs')
            values = cq.importers.importStep(str(path)).vals()
            require(len(values) == 1, 'one whole original STEP root required')
            comparison = compare_material(body, p.single(values[0]), p)
            report['original_baseline_material_comparisons'][name] = comparison
            require(comparison['equal_within_original_1e_minus_7_mm3'],
                    'rebuilt original whole material differs: '+name)
            if len(report['original_baseline_material_comparisons']) % 16 == 0:
                atomic(out/'report.json', report)
        report['baseline_panel_KEY_direct_Common'] = {}
        for side in 'LR':
            actual = p.strict_common(parts['A_BACK_PANEL'], parts[side+'_KEY'])
            actual['difference_from_original_F1a_mm3'] = actual['common_mm3']-original['panel_KEY_direct_Common'][side]['common_mm3']
            require(abs(actual['difference_from_original_F1a_mm3']) <= 1e-7 and actual['common_mm3'] > 1e-7,
                    'original actual rejection did not reproduce')
            report['baseline_panel_KEY_direct_Common'][side] = actual
        report['status'] = 'applying_named_candidate'; atomic(out/'report.json', report)
        parts, materials, application = candidate.apply(parts, proofs['factory'], proofs['readback'], p)
        inventory=body_inventory.measure(parts, metadata, p)
        for side in 'LR':
            inventory[side+'_KEY']['source_functions'].append('key_forward_loop_v1.py:apply')
            inventory[side+'_KEY']['named_research_candidate']=candidate.NAME
            inventory[side+'_KEY']['candidate_source_sha256']=sha(candidate.__file__)
            inventory[side+'_KEY']['original_strength_result_transferable']=False
        report.update(candidate_application=application, geometry_repair_applied=True,
                      candidate_inventory=inventory, candidate_material_exports={}, body_exports={})
        (out/'candidate-materials').mkdir(); (out/'bodies').mkdir()
        for name, records in sorted(materials.items()):
            report['candidate_material_exports'][name] = {}
            for role, shape in sorted(records.items()):
                report['candidate_material_exports'][name][role] = export(shape,out/'candidate-materials'/(name+'-'+role),p,budget)
            atomic(out/'report.json', report)
        for name, body in sorted(parts.items()):
            report['body_exports'][name] = export(body,out/'bodies'/name,p,budget)
            if len(report['body_exports']) % 16 == 0: atomic(out/'report.json', report)
        report['panel_KEY_direct_Common'] = {}
        for side in 'LR':
            common = parts['A_BACK_PANEL'].intersect(parts[side+'_KEY']); value = p.volume(common)
            row = {'a':'A_BACK_PANEL','b':side+'_KEY','common_mm3':value,'rejected':value>1e-7,
                   'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[side+'_KEY'])}
            if value > 0: row['export'] = export(common,out/(side+'-panel-KEY-direct-Common'),p,budget)
            report['panel_KEY_direct_Common'][side] = row
        report['status'] = 'evaluating_all_candidate_factory_pairs'; atomic(out/'report.json', report)
        evaluate_pairs(parts,out,report,p,budget)
        report['candidate_application']['all_pairs_rerun_complete'] = report['all_unordered_pairs_present_once'] and not report['evaluation_failures']
        report['identity_after'] = identity.finish(before,[*executed,body_inventory.__file__])
        require(report['identity_after']['source_bytes_and_locked_environment_unchanged'], 'S4 source/input/runtime changed')
        require(all(sha(k) == v for k,v in report['external_source_sha256'].items()), 'external candidate sources changed')
        report['execution_completed'] = bool(report['all_unordered_pairs_present_once'] and not report['evaluation_failures'])
        report['status'] = 'complete' if report['execution_completed'] else 'completed_with_evaluation_failures'
    except BaseException as exc:
        report['failure_stage']=report.get('status')
        report['status'] = 'failed_or_interrupted'; report['failure'] = type(exc).__name__+': '+str(exc)
    finally:
        report['seconds'] = time.monotonic()-budget.start; atomic(out/'report.json',report)
    print(json.dumps({k:report.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','failure','seconds')}),flush=True)
    return 0 if report['execution_completed'] else 2


if __name__ == '__main__': raise SystemExit(main())
