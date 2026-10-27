"""Classify K4 local geometric results, unevaluated work and readback disagreement.

This stdlib verifier cannot supply a native result. A completed job or diagnostic
is never promoted to local clearance, global wall qualification or full motion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
LIMITS={'wall_seconds':1200,'worker_peak_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,
    'runtime_disk_reserve_MiB':100,'startup_disk_reserve_MiB':256,'startup_additional_memory_MiB':2048}
FLAGS=('global_minimum_wall_measured','global_minimum_wall_qualified','complete_continuous_motion_proved',
    'physical_allowed_domain_proved','strength_qualified','candidate_go','fixture_fabrication_go','manufacturing_go')


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def evaluate(case):
    spec=json.loads((HERE/'K4_LOCAL_SECTION_PILOT_SPEC.json').read_text());ids=[r['probe_id'] for r in spec['probes']]
    control_ids=[r['probe_id'] for r in spec['negative_controls']];results={};unresolved=[];rejected=[];disagreements=[];contracts=[]
    for mode in ('producer','readback'):
        base=case/mode;cp=base/'controller.json';rp=base/'worker/report.json'
        if not cp.is_file() or not rp.is_file():
            results[mode]={'present':False};unresolved.append({'mode':mode,'scope':'missing_controller_or_report'});continue
        c=json.loads(cp.read_text());r=json.loads(rp.read_text());rows=r.get('local_window_results',[]);controls=r.get('negative_controls',[])
        result={'present':True,'report_sha256':sha(rp),'controller_completed':c.get('completed') is True,
            'execution_completed':r.get('execution_completed') is True,'local_material_targets_all_matched':r.get('local_material_targets_all_matched') is True,
            'local_window_results':rows,'negative_controls':controls,'Boolean_calls_started':r.get('Boolean_calls_started'),
            'seconds':r.get('elapsed_seconds'),'evaluation_failures':r.get('evaluation_failures',[]),
            'STEP_BREP_whole_material_comparisons':r.get('STEP_BREP_whole_material_comparisons',[])}
        results[mode]=result
        for row in rows:
            if row.get('evaluated') is not True:unresolved.append({'mode':mode,'probe_id':row.get('probe_id'),'scope':'window_not_evaluated'})
            elif row.get('passed') is not True:rejected.append({'mode':mode,'probe_id':row['probe_id'],'scope':'evaluated_local_target_mismatch','values':{k:v for k,v in row.items() if k.endswith('_mm3')}})
            if mode=='readback' and row.get('evaluated') is True and row.get('producer_numeric_and_classification_agreement') is not True:
                disagreements.append({'probe_id':row['probe_id'],'scope':'producer_reader_local_value_or_classification'})
        for row in controls:
            if row.get('evaluated') is not True:unresolved.append({'mode':mode,'probe_id':row.get('probe_id'),'scope':'negative_control_not_evaluated'})
            elif row.get('expected_rejection_observed') is not True:rejected.append({'mode':mode,'probe_id':row['probe_id'],'scope':'oversized_reference_negative_control_not_rejected'})
            if mode=='readback' and row.get('evaluated') is True and row.get('producer_agreement') is not True:
                disagreements.append({'probe_id':row['probe_id'],'scope':'producer_reader_control_value_or_classification'})
        for row in r.get('STEP_BREP_whole_material_comparisons',[]):
            if row.get('evaluated') is not True:unresolved.append({'mode':mode,'scope':'saved_STEP_BREP_not_evaluated','STEP':row.get('STEP')})
            elif row.get('passed') is not True:rejected.append({'mode':mode,'scope':'saved_STEP_BREP_positive_directed_difference',**row})
        for error in r.get('evaluation_failures',[]):
            if error.get('scope')!='independent_STEP_BREP_material_mismatch':unresolved.append({'mode':mode,**error})
        try:
            require(c['completed'] is True and c['worker_exit_code']==0 and c['limits']==LIMITS,'owned controller incomplete or original native limits changed')
            require(c['result_sha256']==sha(rp),'controller/report byte identity differs')
            require(all(c.get(k) is True for k in ('owned_child_identity_verified','owned_channel_descriptors_closed','source_bytes_unchanged','locked_environment_unchanged')),'owned source/environment closure failed')
            expected_schema='razr-K4-native-local-section-producer-v1' if mode=='producer' else 'razr-K4-separate-native-local-section-reader-v1'
            require(r['schema']==expected_schema and r['spec_sha256']==sha(HERE/'K4_LOCAL_SECTION_PILOT_SPEC.json') and r['API_source_sha256']==sha(HERE/'k4_local_section_native_api.py'),'exact native report source/spec identity differs')
            require(r['execution_completed'] is True and [x['probe_id'] for x in rows]==ids and [x['probe_id'] for x in controls]==control_ids,'original complete 12-window/2-control inventory missing or reordered')
            require(all(r[k] is False for k in FLAGS),'unearned global/physical/strength/go flag')
            before,after=r['context_before'],r['context_after']
            require(before['functional_source_commit']==S4 and before['checked_locked_packages_before']==after['checked_locked_packages_after']==43,'immutable source or full locked package count differs')
            require(all(before.get(k) is True for k in ('owned_supervisor_active','source_bytes_before_verified','worktree_clean_before','locked_environment_before_verified','original_resource_guard_unchanged')),'worker preconditions incomplete')
            require(all(after.get(k) is True for k in ('source_bytes_after_verified','locked_environment_after_verified','owned_child_identity_verified')),'worker postconditions incomplete')
            require(set(r['whole_inputs'])=={'A_BACK_PANEL','L_KEY','R_KEY'},'three complete original participants required')
            for role,count in spec['complete_face_inventory_required'].items():
                item=r['whole_inputs'][role];expected=spec['input_three_whole_STEPs'][role+'.step']
                require({k:item[k] for k in ('bytes','sha256')}==expected and item['native_signature']['face_count']==count,'native whole input identity/face count differs')
                require(len(r['complete_native_face_inventory'][role])==count,'complete native face inventory not retained')
            exports=r['all_scientific_exports'];names=[x['name'] for x in exports]
            require(len(names)==len(set(names)),'duplicate native export record')
            actual={p.name for p in (base/'worker').iterdir() if p.suffix.lower() in ('.brep','.step')}
            require(set(names)==actual,'native geometry export inventory includes missing or unregistered partial shapes')
            for x in exports:
                p=base/'worker'/x['name'];require(p.name==x['name'] and p.is_file() and not p.is_symlink(),'unsafe native export path')
                require(p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],'native original export changed after worker')
            journal=base/'worker/journal.jsonl';events=[json.loads(x) for x in journal.read_text().splitlines()]
            require(sha(journal)==r['journal']['sha256'] and journal.stat().st_size==r['journal']['bytes'] and len(events)==r['journal_rows'],'full original operation journal changed')
            identities=[x for x in events if x['phase']=='validated_empty_set_identity'];starts=[x for x in events if x['phase']=='start'];ends=[x for x in events if x['phase'] in ('finish','error')]
            limit=38 if mode=='producer' else 190
            require(r['preregistered_Boolean_call_limit']==limit and len(starts)==r['Boolean_calls_started']<=limit,'Boolean capacity bound exceeded or misreported')
            require([x['operation'] for x in starts]==[x['operation'] for x in ends],'native journal contains an unfinished or unpaired operation')
            for item in identities:
                require(item['native_Boolean_called'] is False and item['result_is_exact_unchanged_left_operand'] is True,'unverified empty set identity')
                left,right=item['left_signature'],item['right_signature']
                require(left['valid_topology'] and right['valid_topology'] and ((left['solid_count']==0 and left['signed_volume_mm3']==0) or (right['solid_count']==0 and right['signed_volume_mm3']==0)),'empty set identity lacks original valid empty material')
            if mode=='producer':require(len(starts)+len(identities)==38,'producer complete Boolean or validated empty-identity inventory differs')
            else:
                prod=json.loads((case/'producer/worker/report.json').read_text());old=prod['all_scientific_exports']
                require(r['producer_report']['sha256']==sha(case/'producer/worker/report.json'),'independent reader not bound to actual producer')
                require(r['separate_process_verified_by_owned_launcher'] is True and r['same_locked_kernel'] is True and r['second_independent_kernel'] is False,'reader process or kernel scope misstated')
                require({x['name'] for x in r['saved_geometry_readbacks']}=={x['name'] for x in old},'not every original saved shape was independently reimported')
                steps={x['name'] for x in old if x['name'].endswith('.step')}
                require({x['STEP'] for x in r['STEP_BREP_whole_material_comparisons']}==steps,'not every nonempty STEP was compared with its BREP in both directions')
                require(len(starts)+len(identities)==62+2*len(steps),'reader exact Boolean or validated empty-identity inventory differs')
        except (KeyError,ValueError,TypeError,OSError) as error:
            contracts.append({'mode':mode,'scope':'complete_execution_contract','exception_type':type(error).__name__,'message_UTF8_bytes':len(str(error).encode('utf-8')),'message_UTF8_sha256':hashlib.sha256(str(error).encode('utf-8')).hexdigest()})
    diagnostic_complete=not contracts and all(results.get(m,{}).get('execution_completed') for m in ('producer','readback'))
    observed=diagnostic_complete and not unresolved
    local_pass=observed and not rejected and not disagreements and all(results[m]['local_material_targets_all_matched'] for m in results)
    return {'schema':'razr-K4-complete-local-section-observation-v1','functional_source_commit':S4,
        'results':results,'complete_bounded_diagnostic_execution':bool(diagnostic_complete),
        'all_requested_native_evaluations_resolved':bool(observed),'twelve_local_targets_and_two_negative_controls_with_independent_readback_passed':bool(local_pass),
        'actual_geometric_rejections':rejected,'unresolved_evaluations':unresolved,'producer_reader_disagreements':disagreements,
        'completion_contract_failures':contracts,'scope':'Only the frozen twelve local masks at actual K3FULL stow_tabs_3 qL=qR=0; no global wall or motion qualification.',
        **{name:False for name in FLAGS}}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True);a=ap.parse_args()
    try:result=evaluate(a.case.resolve())
    except BaseException as error:result={'schema':'razr-K4-complete-local-section-observation-v1','complete_bounded_diagnostic_execution':False,
        'all_requested_native_evaluations_resolved':False,'twelve_local_targets_and_two_negative_controls_with_independent_readback_passed':False,
        'validator_failure':{'exception_type':type(error).__name__},**{name:False for name in FLAGS}}
    (a.case/'K4-complete-observation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result.get(k) for k in ('complete_bounded_diagnostic_execution','all_requested_native_evaluations_resolved','twelve_local_targets_and_two_negative_controls_with_independent_readback_passed')},sort_keys=True))
    return 0 if result['twelve_local_targets_and_two_negative_controls_with_independent_readback_passed'] else 2


if __name__=='__main__':raise SystemExit(main())
