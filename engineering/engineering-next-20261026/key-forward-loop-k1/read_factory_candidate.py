"""Separate native STEP process: all pairs and independently rebuilt material account.

This reader does not import the candidate builder. It constructs the frozen
cutter and added prisms from the independent contract and compares whole solids.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from f1_common import *
import k1_evidence


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pose', choices=tuple(Q), required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--factory-report', type=Path, required=True)
    ap.add_argument('--f1-evidence', type=Path, required=True)
    ap.add_argument('--binding', type=Path, required=True)
    ap.add_argument('--contract', type=Path, required=True)
    args = ap.parse_args(); out,report,budget = start(__file__,args.output,args.pose)
    report['schema'] = 'razr-S4-K1-independent-candidate-readback-v1'
    report['external_source_sha256'].update({str(Path(x).resolve()):sha(x)
        for x in (k1_evidence.__file__,args.binding,args.contract)})
    try:
        original = json.loads(args.factory_report.read_text()); base = args.factory_report.parent.resolve()
        require(original['functional_source_commit'] == S4 and original['pose'] == args.pose
                and original['execution_completed'] and original['participant_count'] == 154
                and original['all_unordered_pairs_present_once'], 'complete candidate factory required')
        proofs,receipt = k1_evidence.prerequisite(args.f1_evidence,args.binding,args.pose)
        report['F1a_prerequisite'] = receipt
        frozen = json.loads(args.contract.read_text()); contract = frozen['design_contract']
        require(original['candidate_name'] == contract['candidate_name'] == 'key_forward_loop_v1', 'named candidate differs')
        require(original['candidate_application']['design_contract'] == contract,
                'actual candidate contract differs from independent frozen contract')
        require(original['candidate_application']['source_sha256'] == frozen['candidate_source_sha256'],
                'candidate source bytes differ from independently frozen contract')
        before = identity.snapshot(); executed = identity.record_executed_project_files()
        report['identity_before'] = before
        import cadquery as cq
        import product_assembly as p
        report.update(candidate_name=contract['candidate_name'],candidate_contract_sha256=sha(args.contract),
            factory_report_sha256=sha(args.factory_report),native_STEP_readback_executed=True,
            separate_process_from_factory=True,independent_CAD_kernel=False,
            independent_material_builder_does_not_import_candidate_source=True,
            body_readbacks={},candidate_material_readbacks={},material_reconstruction={},
            status='importing_all_candidate_STEP_bodies')
        def read_step(path,entry):
            budget.check(); path=Path(path)
            require(path.is_file() and not path.is_symlink()
                    and sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'],
                    'whole STEP byte identity failed')
            values=cq.importers.importStep(str(path)).vals()
            require(len(values) == 1,'one complete STEP root required')
            # Actual added/removed material may have several valid fragments.
            # Preserve the complete root; only assembly participants and the
            # complete original/result KEY require one positive solid.
            p.whole_material(values[0])
            return values[0]
        def read_material(entry):
            ref=entry['files']['step'];path=(base/ref['path']).resolve()
            require(path.is_relative_to(base),'candidate evidence path escaped')
            body=read_step(path,ref);sig=signature(body,p);old=entry['signature_before']
            deltas=[a-b for a,b in zip(sig['bounds_mm'],old['bounds_mm'])]
            ok=(sig['is_valid'] and sig['solid_count']==old['solid_count']
                and abs(sig['signed_volume_mm3']-old['signed_volume_mm3'])<=1e-7
                and max(map(abs,deltas))<=1e-7)
            require(ok,'STEP complete material signature differs')
            return body,{'STEP':ref,'signature':sig,'volume_delta_mm3':sig['signed_volume_mm3']-old['signed_volume_mm3'],
                         'bounds_delta_mm':deltas,'passed':ok}
        parts={}
        for name,entry in sorted(original['body_exports'].items()):
            body,row=read_material(entry);parts[name]=p.single(body);report['body_readbacks'][name]=row
        require(set(parts)==set(original['participant_names']) and len(parts)==154,'whole STEP body inventory incomplete')
        q=original['pose_input']['native_q_from_K_times_slide_mm']
        require(0<=q<=12 and q.hex()==proofs['factory']['engineering_record']['pose_input']['native_q_binary64_hex'],
                'original unmodified q witness required')
        def box(side,bounds):
            lo,hi=bounds
            if side=='L':lo,hi=(-hi[0],lo[1],lo[2]),(-lo[0],hi[1],hi[2])
            return p.box(lo,hi)
        for side in 'LR':
            name=side+'_KEY';materials={};report['candidate_material_readbacks'][name]={}
            for role,entry in original['candidate_material_exports'][name].items():
                materials[role],report['candidate_material_readbacks'][name][role]=read_material(entry)
            old=p.single(materials['original_q0']);new=p.single(materials['candidate_q0'])
            cutter=box(side,contract['cut_box_R_local_q0_mm'])
            cutcmp=compare_material(cutter,materials['cutter_q0'],p)
            require(cutcmp['equal_within_original_1e_minus_7_mm3'],'independent cutter geometry differs')
            prisms={k:box(side,b) for k,b in contract['added_boxes_R_local_q0_mm'].items()}
            prismcmp={}
            rebuilt=old.cut(cutter)
            for key,prism in prisms.items():
                prismcmp[key]=compare_material(prism,materials['new_prism_q0_'+key],p)
                require(prismcmp[key]['equal_within_original_1e_minus_7_mm3'],'independent added prism differs')
                rebuilt=rebuilt.fuse(prism)
            rebuilt=p.single(rebuilt.clean());reconstruction=compare_material(rebuilt,new,p)
            require(reconstruction['equal_within_original_1e_minus_7_mm3'],'independent whole material reconstruction differs')
            globalcmp=compare_material(new.translate((0,q,0)),parts[name],p)
            savedglobal=compare_material(parts[name],materials['candidate_at_witness'],p)
            require(globalcmp['equal_within_original_1e_minus_7_mm3'] and savedglobal['equal_within_original_1e_minus_7_mm3'],
                    'q0 whole KEY and actual factory KEY differ')
            original_ref=proofs['factory']['engineering_record']['body_exports'][name]['files']['step']
            original_at_pose=read_step(args.f1_evidence/'factory/worker'/original_ref['path'],original_ref)
            baselinecmp=compare_material(old.translate((0,q,0)),original_at_pose,p)
            require(baselinecmp['equal_within_original_1e_minus_7_mm3'],'original KEY material differs from F1a')
            loss=old.cut(new);gain=new.cut(old)
            removedcmp=compare_material(loss,materials['removed_q0'],p)
            addedcmp=compare_material(gain,materials['added_q0'],p)
            require(removedcmp['equal_within_original_1e_minus_7_mm3'] and addedcmp['equal_within_original_1e_minus_7_mm3'],
                    'reported removed or added whole material differs')
            vloss,vgain=p.volume(loss),p.volume(gain)
            account={'original_mm3':p.volume(old),'removed_mm3':vloss,'added_mm3':vgain,'new_mm3':p.volume(new),
                     'signed_material_balance_error_mm3':p.volume(old)-vloss+vgain-p.volume(new),
                     'retained_original_material_loss_mm3':p.volume(old.cut(cutter).cut(new)),
                     'unintended_loss_outside_declared_cutter_mm3':p.volume(loss.cut(cutter)),
                     'material_restored_inside_clearance_cut_mm3':p.volume(new.intersect(cutter))}
            require(abs(vloss-1.10*1.50*.36)<=1e-7,'original crossbar removal differs')
            require(max(abs(account[k]) for k in ('signed_material_balance_error_mm3','retained_original_material_loss_mm3',
                    'unintended_loss_outside_declared_cutter_mm3','material_restored_inside_clearance_cut_mm3'))<=1e-7,
                    'independent material account failed')
            for key,value in account.items():
                require(abs(value-original['candidate_application']['material_accounts'][name][key])<=1e-7,
                        'producer material account differs: '+key)
            protected={}
            for key,bounds in contract['protected_old_material_masks_R_mm'].items():
                mask=box(side,bounds);protected[key]=compare_material(old.intersect(mask),new.intersect(mask),p)
                require(protected[key]['equal_within_original_1e_minus_7_mm3'],'functional-region material differs')
            report['material_reconstruction'][name]={'cutter':cutcmp,'added_prisms':prismcmp,
                'whole_reconstructed_candidate':reconstruction,'q0_to_factory_KEY':globalcmp,
                'saved_candidate_at_witness':savedglobal,'original_KEY_to_F1a':baselinecmp,
                'actual_removed_material':removedcmp,'actual_added_material':addedcmp,
                'independent_account':account,'protected_original_material':protected,
                'single_positive_valid_solid_observed':True,'local_section_area_mm2':.38*.36,
                'local_section_ratio_to_original':.38/1.50,'minimum_whole_KEY_wall_measured':False,
                'strength_qualified':False,'passed':True}
            atomic(out/'report.json',report)
        report['status']='repeating_all_candidate_pairs_from_STEP';atomic(out/'report.json',report)
        evaluate_pairs(parts,out,report,p,budget,original=original)
        require(not report['mismatches_to_factory'],'independent all-pair readback mismatch')
        report['panel_KEY_direct_Common']={}
        for side in 'LR':
            common=parts['A_BACK_PANEL'].intersect(parts[side+'_KEY']);v=p.volume(common)
            row={'common_mm3':v,'rejected':v>1e-7,'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[side+'_KEY']),
                 'factory_direct_Common_mm3':original['panel_KEY_direct_Common'][side]['common_mm3'],
                 'factory_volume_delta_mm3':v-original['panel_KEY_direct_Common'][side]['common_mm3']}
            require(abs(row['factory_volume_delta_mm3'])<=1e-7,'direct panel/KEY Common differs')
            if v>0:row['export']=export(common,out/(side+'-panel-KEY-direct-Common'),p,budget)
            report['panel_KEY_direct_Common'][side]=row
        report['identity_after']=identity.finish(before,[*executed])
        require(report['identity_after']['source_bytes_and_locked_environment_unchanged'],'reader S4 source/input/runtime changed')
        require(all(sha(k)==v for k,v in report['external_source_sha256'].items()),'external reader source or prerequisites changed')
        report['execution_completed']=bool(report['all_unordered_pairs_present_once'] and not report['evaluation_failures']
            and not report['mismatches_to_factory'] and all(x['passed'] for x in report['material_reconstruction'].values()))
        report['status']='complete' if report['execution_completed'] else 'completed_with_material_mismatch'
    except BaseException as exc:
        report['failure_stage']=report.get('status')
        report['status']='failed_or_interrupted';report['failure']=type(exc).__name__+': '+str(exc)
    finally:
        report['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',report)
    print(json.dumps({k:report.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','failure','seconds')}),flush=True)
    return 0 if report['execution_completed'] else 2


if __name__=='__main__':raise SystemExit(main())
