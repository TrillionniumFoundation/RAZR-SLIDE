"""Owned native capacity measurement of complete original SLIDE laws on K1.

This is a new diagnostic schema. Original S4 defaults, domain, native predicates
and all capacity guards remain unchanged. The seventeen selected pairs do not
constitute a complete 11,781-pair execution or a physical-domain qualification.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
from types import SimpleNamespace

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
ROOT=Path(os.environ['GITHUB_WORKSPACE']).resolve()
HERE=Path(__file__).resolve().parent
GEOMETRY=ROOT/'engineering/engineering-integration-20261025/geometry'
sys.path[:0]=[str(GEOMETRY/'slide'),str(GEOMETRY/'seating'),str(GEOMETRY),
             str(ROOT/'integration'),str(ROOT/'tools')]
import owned_process
import execution_identity as identity
import full_slide_api_v4 as api
import capacity_stage_v4 as stage

SOURCES=('run_capacity_v4.py','capacity_stage_v4.py','full_slide_api_v4.py','envelope_v2.py',
         'correlated_v3.py','test_l2_native.py','frozen_key_factory_adapter.py','K1_BINDING.json',
         'supervise_capacity_v4.py','read_capacity_v4.py','export_capacity_v4.py','check_capacity_stage.py')


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def validate_native_specification(result,guard):
    require(result['schema']==api.SCHEMA,'unknown new-method schema')
    require(result['original_volume_gate_mm3']==1e-7,'original gate changed')
    require(result['physical_qualification'] is False and result['formal_directed_rounding_certificate'] is False,
            'unsupported qualification asserted')
    if 'affine_raw' in result:
        guard.validate_frame(result['affine_raw'])
        require(result['disposition']==result['affine_raw']['disposition'],'affine disposition differs')
        return
    native=result['correlated_result'];checks=[]
    def visit(v):
        if isinstance(v,dict):
            if 'original_static_carrier_postguard_record' in v:
                record=v['original_static_carrier_postguard_record'];guard.validate_frame(record)
                value=v['strict_common']['common_mm3']
                require(type(value) in (int,float) and math.isfinite(value) and value>=0,'invalid original Common')
                require(value==record.get('common_upper_bound_mm3',record.get('examined_region_common_sum_mm3')),
                        'static postguard bound differs from original Common')
                checks.append(value)
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(native)
    require(checks and native['common_upper_bound_is_sum_not_union_volume'] is True,'static Common inventory absent')
    if native['method']=='whole_STOP_pin_and_remainder_correlated_contact_path':
        require(len(native['carrier_checks'])==4,'whole STOP carrier omitted')
        sums={f:math.fsum(c[f+'_frame']['strict_common']['common_mm3'] for c in native['carrier_checks']) for f in ('contact','phone')}
        require(sums==native['frame_common_sums_mm3'],'full frame Common sum differs')
        upper=max(sums.values())
    else:
        require(native['method']=='matched_spring_STOP_co_moving_nested_complete_cylinder','unknown correlated method')
        upper=native['static_carrier_check']['strict_common']['common_mm3']
        require(len(native['finite_crosschecks'])==3,'finite corroboration incomplete')
        require(all(0<=r['whole_relative_cylinder_outside_mm3']<=1e-7 for r in native['finite_crosschecks']),
                'finite cylinder escaped recorded carrier')
    require(upper==native['common_upper_bound_mm3']==result['common_upper_bound_mm3'],'full Common bound changed')
    require(native['negative_control']['strict_common']['common_mm3']>1e-7,'negative control failed to reject')
    require(native['disposition']==result['disposition']==('clear' if upper<=1e-7 else 'unresolved_enclosure_overlap'),
            'correlated original-threshold disposition changed')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--k1-near',type=Path,required=True);ap.add_argument('--k1-far',type=Path,required=True)
    ap.add_argument('--binding',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    owned_process.announce_worker_from_environment(Path(__file__).resolve())
    out=args.output.resolve();require(not out.exists() and not out.is_relative_to(ROOT),'fresh external result directory required')
    out.mkdir(parents=True);science=out/'science';science.mkdir()
    begin=time.monotonic();signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(InterruptedError('owned SIGTERM')))
    report={'schema':'razr-V4-K1-owned-capacity-worker-v1','functional_source_commit':S4,
        'candidate_name':'key_forward_loop_v1','execution_completed':False,'source_runtime_unchanged':False,
        'all_original_postguards_passed':False,'construction_probes_complete':False,'native_started':False,
        'full_11781_pairs_executed':False,'complete_G2_qualification':False,'physical_qualification':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
        'calls':[],'stage':'source_identity','actual_K1_binding_sha256':sha(args.binding)}
    own={name:sha(HERE/name) for name in SOURCES}
    require(sha(args.binding)==own['K1_BINDING.json'],'input K1 binding differs from frozen driver bundle')
    report['external_source_sha256']=own
    before=None;contract=None;budget=None;after=None;frozen_identity=None;executed=[];counter=0
    def save():
        report['elapsed_seconds']=time.monotonic()-begin
        report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        identity.atomic_json(science/'report.json',report)
    save()
    try:
        require(identity.git('rev-parse','HEAD')==S4 and not identity.git('status','--porcelain'),'immutable clean S4 required')
        before=identity.snapshot();executed=identity.record_executed_project_files()
        identity.atomic_json(out/'source-before-private.json',before)
        import verify_slide_native as original
        import slide_evidence as evidence
        import slide_domain as domain
        initial_names=evidence.expected_names()
        initial_inventory=science/'pair-inventory.json'
        identity.atomic_json(initial_inventory,{'schema':'razr-V4-complete-pair-inventory-v1',
            'rows':api.initialize_inventory(initial_names),'full_native_execution_claimed':False})
        report['complete_participant_names']=initial_names
        report['complete_pair_inventory']={'path':initial_inventory.name,'sha256':sha(initial_inventory),
                                          'bytes':initial_inventory.stat().st_size}
        save()
        original_budget=original.Budget(SimpleNamespace(output=science/'report.json'))
        budget=stage.ForwardBudget(original_budget,api)
        budget.check()
        import cadquery as cq
        import product_nominal_motion as nominal
        import verify_cam_coupling as cam
        import product_assembly as p
        import validate_product_nominal_report as guard
        import frozen_key_factory_adapter as adapter
        import envelope_v2 as v2
        import correlated_v3 as v3
        import test_l2_native
        frozen_identity=nominal.execution_identity(S4)
        identity.atomic_json(out/'nominal-source-before-private.json',frozen_identity)
        report['native_started']=True
        report['native_V2_controls']=test_l2_native.execute()
        report['stage']='actual_K1_dual_clear_material_loader';save()
        binding=json.loads(args.binding.read_text())
        keys=adapter.load_keys({'near':args.k1_near,'far':args.k1_far},binding,p,cq,budget)
        report['actual_K1_material_prerequisite']=keys.receipt
        report['stage']='original_five_factory_law_probes';save()
        def construction_checkpoint(value):
            report['construction']=value;save()
        contract,bodies,construction=stage.construct_and_probe(keys=keys,adapter=adapter,nominal=nominal,
            cam=cam,p=p,original_driver=original,source_evidence=evidence,domain=domain,
            identity_before=frozen_identity,budget=budget,checkpoint=construction_checkpoint)
        report['construction_probes_complete']=construction['five_factory_probes_complete']
        report['source_domain']=evidence.recorded_domain(contract.profiles)
        report['complete_participant_names']=contract.names
        report['stage']='capacity_pairs';save()

        def evaluate(moving,fixed,spec,target):
            nonlocal counter
            counter+=1;call_id='call-'+str(counter).zfill(6);started=time.monotonic()
            entry={'schema':'razr-V4-native-call-v1','call_id':call_id,'target':target,
                   'original_source_specification':spec,'material_exports':[],
                   'original_volume_gate_mm3':1e-7,'execution_completed':False}
            entry_path=science/(call_id+'.json')
            def save_entry():
                entry['whole_call_seconds_including_exports']=time.monotonic()-started
                identity.atomic_json(entry_path,entry)
            save_entry()
            def export_body(label,body,positive=True):
                budget.check()
                path=science/(call_id+'-'+label+'.brep')
                require(not path.exists(),'actual native body export path already exists')
                ok=body.exportBrep(str(path));require(ok is True and path.stat().st_size>0,'native BREP export failed')
                record={'label':label,'path':path.name,'bytes':path.stat().st_size,'sha256':sha(path),
                        'native_export_status':str(ok)}
                entry['material_exports'].append(record);save_entry()
                try:
                    record['signature']={'is_valid':body.isValid(),'signed_volume_mm3':float(body.Volume()),
                        'solid_signed_volumes_mm3':[s.Volume() for s in body.Solids()]}
                    if positive:
                        p.whole_material(body)
                        record['positive_whole_material_passed']=True
                except Exception as exc:
                    record['signature_or_validation_failure_type']=type(exc).__name__
                    save_entry()
                    if positive:raise
                save_entry();budget.check();return record
            def retain(carrier,obstacle,detail):
                label=detail['frame']+'-region-'+str(detail['region_index'])
                row={'frame':detail['frame'],'region_index':detail['region_index'],
                     'carrier':export_body(label,carrier,False)}
                try:
                    common=carrier.intersect(obstacle)
                    row['followup_Common']=export_body(label+'-Common',common,False)
                    row['followup_is_new_operation_not_original_failed_Common']=True
                    if 'strict_common' in detail:
                        value=row['followup_Common']['signature']['signed_volume_mm3']
                        require(abs(value-detail['strict_common']['common_mm3'])<=1e-7,'retained Common differs')
                except (api.CapacityStop,InterruptedError):raise
                except Exception as exc:
                    row['followup_failure_type']=type(exc).__name__
                entry.setdefault('retained_carriers',[]).append(row);save_entry()
                if 'strict_common' in detail:require('followup_failure_type' not in row,'retained checked Common failed')
                return row
            try:
                export_body('moving-input',moving);export_body('fixed-input',fixed)
                result=api.evaluate_specification(moving,fixed,spec,target,contract=contract,source_root=ROOT,
                    p=p,v2=v2,v3=v3,original_postguard=guard,budget_check=budget.check,
                    emit=export_body,retain_v2=retain)
                result['capacity_call_id']=call_id
                entry['new_result']=result;entry['execution_completed']=True
                try:
                    validate_native_specification(result,guard)
                    entry['unchanged_original_postguards_passed']=True
                except Exception as exc:
                    entry['unchanged_original_postguards_passed']=False
                    entry['postguard_failure_type']=type(exc).__name__
                return result
            except (api.CapacityStop,InterruptedError):
                entry['capacity_stop']=True;raise
            except Exception as exc:
                entry['evaluation_failure_type']=type(exc).__name__;raise
            finally:
                save_entry()
                report['calls'].append({'call_id':call_id,'target':target,
                    'case_json_sha256':sha(entry_path),'case_json_bytes':entry_path.stat().st_size,
                    'whole_call_seconds_including_exports':entry['whole_call_seconds_including_exports'],
                    'native_specification_seconds':entry.get('new_result',{}).get('specification_elapsed_seconds'),
                    'disposition':entry.get('new_result',{}).get('disposition','unresolved_budget' if entry.get('capacity_stop') else 'unresolved_evaluation'),
                    'unchanged_original_postguards_passed':entry.get('unchanged_original_postguards_passed',False)})
                save()
        previous_inventory=None
        def compact(value):
            # Full call bodies and region evidence are written once in individually
            # hashed call JSON files. The interval tree retains every reference.
            if isinstance(value,list):return [compact(x) for x in value]
            if isinstance(value,dict):
                if value.get('schema')==api.SCHEMA:
                    return {k:value[k] for k in ('schema','capacity_call_id','disposition')}
                return {k:compact(v) for k,v in value.items() if k!='all_11781_pair_slots'}
            return value
        def pair_checkpoint(value):
            nonlocal previous_inventory
            inventory=value['all_11781_pair_slots']
            states=tuple(r['disposition'] for r in inventory)
            if states!=previous_inventory:
                path=science/'pair-inventory.json'
                identity.atomic_json(path,{'schema':'razr-V4-complete-pair-inventory-v1','rows':inventory,
                    'full_native_execution_claimed':False})
                report['complete_pair_inventory']={'path':path.name,'sha256':sha(path),'bytes':path.stat().st_size}
                previous_inventory=states
            report['capacity']=compact(value)
            report['full_call_details_in_individually_hashed_JSON']=True
            save()
        capacity=stage.run_capacity_pairs(contract=contract,bodies=bodies,api=api,evaluate_specification=evaluate,
            budget_check=budget.check,checkpoint=pair_checkpoint,construction_receipt=construction)
        pair_checkpoint(capacity)
        report['execution_completed']=capacity['execution_completed']
        report['all_original_postguards_passed']=bool(report['calls']) and all(c['unchanged_original_postguards_passed'] for c in report['calls'])
        report['selected_pair_disposition_counts']=dict(Counter(r['disposition'] for r in capacity['selected_pair_results']))
        report['stage']='postflight'
        save()
        if capacity['execution_completed']:
            for row in capacity['selected_pair_results']:
                stage.validate_interval_record(row,row['a'],row['b'],F(0),F(12),contract=contract,api=api,
                    validate_specification=lambda r:validate_native_specification(r,guard))
            report['complete_source_interval_records_independently_rebuilt']=True
    except (api.CapacityStop,InterruptedError) as exc:
        report['capacity_failure_type']=type(exc).__name__;report['failure_stage']=report['stage']
    except BaseException as exc:
        report['failure_type']=type(exc).__name__;report['failure_stage']=report['stage']
    finally:
        try:
            if before is not None:
                after=identity.finish(before,executed)
                identity.atomic_json(out/'source-after-private.json',after)
                report['source_runtime_unchanged']=after['source_bytes_and_locked_environment_unchanged']
                report['original_executed_source_sha256']={str(Path(k).relative_to(ROOT)):v
                    for k,v in after['executed_source_and_input_sha256'].items()}
                require(after['repository_head_at_finish']==S4 and not identity.git('status','--porcelain'),
                        'final immutable source HEAD or clean worktree differs')
            if frozen_identity is not None:
                final_frozen_identity=nominal.execution_identity(S4)
                identity.atomic_json(out/'nominal-source-after-private.json',final_frozen_identity)
                require(final_frozen_identity==frozen_identity,'original source and locked runtime closure changed')
                report['original_nominal_identity_closure_unchanged']=True
            require(own=={name:sha(HERE/name) for name in SOURCES},'frozen external sources changed')
            report['external_source_unchanged']=True
        except Exception as exc:
            report['postflight_failure_type']=type(exc).__name__;report['source_runtime_unchanged']=False
        if budget is not None:report['original_resource_record']=budget.record()
        report['method_has_not_received_full_product_qualification']=True
        save()
    print(json.dumps({k:report.get(k) for k in ('execution_completed','all_original_postguards_passed',
        'selected_pair_disposition_counts','failure_type','capacity_failure_type','elapsed_seconds')}),flush=True)
    return 0 if (report['execution_completed'] and report['all_original_postguards_passed']
        and report['source_runtime_unchanged'] and report.get('external_source_unchanged') is True
        and report.get('complete_source_interval_records_independently_rebuilt') is True
        and not report.get('failure_type') and not report.get('postflight_failure_type')) else 2


if __name__=='__main__':raise SystemExit(main())
