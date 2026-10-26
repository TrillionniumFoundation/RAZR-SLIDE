"""Independent process: import every F1 STEP, repeat all pairs, compare L1 materials."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from f1_common import *

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pose',choices=tuple(Q),required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--factory-report',type=Path,required=True)
    ap.add_argument('--l1-inputs',type=Path,required=True);ap.add_argument('--binding',type=Path,required=True)
    args=ap.parse_args();out,report,budget=start(__file__,args.output,args.pose)
    try:
        original=json.loads(args.factory_report.read_text());base=args.factory_report.parent.resolve()
        require(original['functional_source_commit']==S4 and original['pose']==args.pose,'factory source or pose mismatch')
        require(original['execution_completed'] and original['participant_count']==154 and original['all_unordered_pairs_present_once'],'complete factory required')
        before=identity.snapshot();executed=identity.record_executed_project_files();report['identity_before']=before
        import cadquery as cq
        import product_assembly as p
        report.update(factory_report_sha256=sha(args.factory_report),native_STEP_readback_executed=True,
                      separate_process_from_factory=True,independent_CAD_kernel=False,
                      body_readbacks={},status='importing_all_factory_STEP_bodies')
        parts={}
        def read_step(path,expected):
            budget.check();require(path.is_file() and not path.is_symlink() and sha(path)==expected['sha256'] and path.stat().st_size==expected['bytes'],'STEP byte identity failed')
            values=cq.importers.importStep(str(path)).vals();require(len(values)==1,'one complete STEP root required')
            return p.single(values[0])
        for name,record in sorted(original['body_exports'].items()):
            entry=record['files']['step'];path=(base/entry['path']).resolve();require(path.is_relative_to(base),'STEP outside factory evidence')
            body=read_step(path,entry);sig=signature(body,p);previous=record['signature_before']
            volume_delta=sig['signed_volume_mm3']-previous['signed_volume_mm3']
            bounds_delta=[a-b for a,b in zip(sig['bounds_mm'],previous['bounds_mm'])]
            ok=abs(volume_delta)<=1e-7 and max(map(abs,bounds_delta))<=1e-7 and sig['solid_count']==previous['solid_count'] and sig['is_valid']
            report['body_readbacks'][name]={'STEP':entry,'signature':sig,'volume_delta_mm3':volume_delta,'bounds_delta_mm':bounds_delta,'passed':ok}
            require(ok,'STEP material signature mismatch: '+name);parts[name]=body
        require(set(parts)==set(original['participant_names']) and len(parts)==154,'STEP inventory incomplete')
        report['status']='repeating_all_pairs_from_STEP';atomic(out/'report.json',report)
        evaluate_pairs(parts,out,report,p,budget,original=original)
        require(not report['mismatches_to_factory'],'independent all-pair readback mismatch')
        binding=json.loads(args.binding.read_text());report['L1_binding_sha256']=sha(args.binding)
        require(binding['L1_run_id']==40210275856 and binding['artifact_id']==12605885469,'wrong historical artifact identity')
        inputs=args.l1_inputs.resolve()
        for rel,entry in binding['selected_original_members'].items():
            path=(inputs/rel).resolve();require(path.is_relative_to(inputs) and path.is_file() and not path.is_symlink(),'unsafe original member')
            require(path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],'L1 original input hash mismatch')
        report['L1_original_input_members_verified']=len(binding['selected_original_members'])
        report['L1_whole_endpoint_material_comparisons']=[]
        report['panel_KEY_direct_Common']={}
        cache={}
        def l1_material(case,index):
            key=(case,index)
            if key not in cache:
                raw=json.loads((inputs/f'run/{case}/result.json').read_text())
                record=next(r for r in raw['material_exports'] if r['id']==index)
                entry=record['exports']['step'];path=inputs/'run'/case/entry['path']
                cache[key]=read_step(path,entry)
            return cache[key]
        for side in 'LR':
            name=side+'_KEY';common=parts['A_BACK_PANEL'].intersect(parts[name]);v=p.volume(common)
            report['panel_KEY_direct_Common'][side]={'a':'A_BACK_PANEL','b':name,'direct_Common_mm3':v,
                'strict_common':p.strict_common(parts['A_BACK_PANEL'],parts[name]),
                'factory_direct_Common_mm3':original['panel_KEY_direct_Common'][side]['common_mm3'],
                'factory_volume_delta_mm3':v-original['panel_KEY_direct_Common'][side]['common_mm3']}
        for row in binding['whole_endpoint_frame_references']:
            if Fraction(row['original_rational_q_endpoint_mm']) != Q[args.pose]:continue
            budget.check();case=row['case_id'];q=row['binary64_q_from_translation_recipe_mm'];name=row['pair'][1]
            raw=json.loads((inputs/f'run/{case}/result.json').read_text())
            require(raw['target']['a']=='A_BACK_PANEL' and raw['target']['b']==name,'historical material role mismatch')
            endpoint=l1_material(case,row['whole_endpoint_region_material_id'])
            common_old=l1_material(case,row['actual_Common_material_id'])
            coef=row['native_translation_recipe']['reference_frame_coefficient_Y']
            if coef == -1.:
                require(row['frame_index']==1,'unexpected negative frame')
                old_panel=endpoint.translate((0,q,0));old_key=l1_material(case,2).translate((0,q,0));old_common=common_old.translate((0,q,0))
                transform={'whole_panel_endpoint_to_factory_frame':[0.,q,0.],'base_KEY_to_factory_frame':[0.,q,0.],'Common_to_factory_frame':[0.,q,0.]}
            elif coef == 1.:
                require(row['frame_index']==2,'unexpected positive frame')
                old_panel=l1_material(case,1);old_key=endpoint;old_common=common_old
                transform={'whole_KEY_endpoint_already_in_factory_frame':True,'Common_already_in_factory_frame':True}
            else:raise ValueError('unrepresented L1 frame coefficient')
            actual_common=parts['A_BACK_PANEL'].intersect(parts[name])
            panel_comparison=compare_material(old_panel,parts['A_BACK_PANEL'],p)
            key_comparison=compare_material(old_key,parts[name],p)
            common_comparison=compare_material(old_common,actual_common,p)
            actual_value=p.volume(actual_common);old_value=p.volume(old_common)
            item={'case_id':case,'frame_index':row['frame_index'],'pair':row['pair'],
                'historical_q_exact_mm':row['original_rational_q_endpoint_mm'],'historical_q_binary64_mm':q,
                'native_factory_q_mm':original['pose_input']['native_q_from_K_times_slide_mm'],
                'bitwise_equal_q':q.hex()==original['pose_input']['native_q_binary64_hex'],
                'original_whole_endpoint_STEP_sha256':row['whole_endpoint_export_sha256']['step'],
                'original_Common_STEP_sha256':row['Common_export_sha256']['step'],
                'frame_transform':transform,'panel_directed_material_difference':panel_comparison,
                'KEY_directed_material_difference':key_comparison,'Common_directed_material_difference':common_comparison,
                'original_L1_Common_mm3':row['actual_Common_mm3'],'imported_original_Common_mm3':old_value,
                'current_factory_STEP_direct_Common_mm3':actual_value,'native_Common_delta_from_L1_mm3':actual_value-row['actual_Common_mm3'],
                'passed':all(x['equal_within_original_1e_minus_7_mm3'] for x in (panel_comparison,key_comparison,common_comparison)) and abs(actual_value-row['actual_Common_mm3'])<=1e-7}
            report['L1_whole_endpoint_material_comparisons'].append(item);atomic(out/'report.json',report)
        require(len(report['L1_whole_endpoint_material_comparisons'])==8,'all eight historical whole endpoint frames at this pose required')
        report['identity_after']=identity.finish(before,[*executed])
        require(report['identity_after']['source_bytes_and_locked_environment_unchanged'],'readback source/input/runtime changed')
        require(all(sha(k)==v for k,v in report['external_source_sha256'].items()),'external reader changed')
        report['execution_completed']=bool(report['all_unordered_pairs_present_once'] and not report['evaluation_failures'] and not report['mismatches_to_factory'] and all(x['passed'] for x in report['L1_whole_endpoint_material_comparisons']))
        report['status']='complete' if report['execution_completed'] else 'completed_with_material_mismatch'
    except BaseException as exc:
        report['status']='failed_or_interrupted';report['failure']=type(exc).__name__+': '+str(exc)
    finally:
        report['seconds']=time.monotonic()-budget.start;atomic(out/'report.json',report)
    print(json.dumps({k:report.get(k) for k in ('status','execution_completed','finite_pose_clear','persisted_pair_count','failure','seconds')}),flush=True)
    return 0 if report['execution_completed'] else 2

if __name__=='__main__':raise SystemExit(main())
