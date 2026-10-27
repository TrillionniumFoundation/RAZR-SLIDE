"""Owned L5 original-seven/current-K1 diagnostic, with unchanged S4 gates."""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import time
from types import SimpleNamespace

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
ROOT=Path(os.environ['GITHUB_WORKSPACE']).resolve();HERE=Path(__file__).resolve().parent
GEOMETRY=ROOT/'engineering/engineering-integration-20261025/geometry'
sys.path[:0]=[str(GEOMETRY/'slide'),str(GEOMETRY/'seating'),str(GEOMETRY),str(ROOT/'integration'),str(ROOT/'tools')]
import owned_process
import execution_identity as identity
import cylindrical_sweep_l5 as l5
import l5_science_contract as contract_rules
import full_slide_api_v4 as api
import capacity_stage_v4 as stage

SOURCES=('run_l5.py','supervise_l5.py','cylindrical_sweep_l5.py','exact_xy_support_l5.py',
 'test_l5_native.py','check_l5_plan.py','l5_science_contract.py','read_l5_native.py','read_l5_records.py',
 'export_l5.py','test_export_l5.py','capacity_stage_v4.py','full_slide_api_v4.py','envelope_v2.py',
 'correlated_v3.py','test_l2_native.py','frozen_key_factory_adapter.py','K1_BINDING.json','L5_ORIGINAL_SEVEN_BINDING.json')


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def signature(body,p,positive=True):
    result={'shape_type':body.ShapeType(),'is_valid':body.isValid(),'signed_volume_mm3':float(body.Volume()),
        'solid_signed_volumes_mm3':[float(s.Volume()) for s in body.Solids()]}
    if positive:
        p.whole_material(body);result.update(positive_whole_material_passed=True,bounds_mm=list(p.bounds(body)))
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scope',choices=('original','current'),required=True)
    ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--k1-near',type=Path);ap.add_argument('--k1-far',type=Path)
    args=ap.parse_args();owned_process.announce_worker_from_environment(Path(__file__).resolve())
    out=args.output.resolve();require(not out.exists() and not out.is_relative_to(ROOT),'fresh external result directory required')
    out.mkdir(parents=True);science=out/'science';science.mkdir();begin=time.monotonic()
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(InterruptedError('owned SIGTERM')))
    report={'schema':'razr-L5-owned-whole-material-worker-v1','functional_source_commit':S4,'scope':args.scope,
        'execution_completed':False,'all_original_postguards_passed':False,'source_runtime_unchanged':False,
        'native_started':False,'calls':[],'expected_original_case_ids':['case-'+x for x in contract_rules.CASE_NUMBERS],
        'distinct_physical_pairs':7,'complete_source_q_interval_exact':['0','12'],
        'complete_product_pair_inventory':11781,'outside_this_worker_not_evaluated_pairs':11774,
        'new_scientific_output_cap_bytes':128*2**20,**{k:False for k in contract_rules.FALSE_FLAGS}}
    own={n:sha(HERE/n) for n in SOURCES};report['external_source_sha256']=own
    before=None;budget=None;frozen_identity=None;executed=[];exported=[]
    def save():
        report['elapsed_seconds']=time.monotonic()-begin
        report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        identity.atomic_json(science/'report.json',report)
    save()
    try:
        require(identity.git('rev-parse','HEAD')==S4 and not identity.git('status','--porcelain'),'immutable clean S4 required')
        before=identity.snapshot();executed=identity.record_executed_project_files();identity.atomic_json(out/'source-before-private.json',before)
        import verify_slide_native as original
        budget=stage.ForwardBudget(original.Budget(SimpleNamespace(output=science/'report.json')),api)
        budget.check()
        binding=json.loads((HERE/'L5_ORIGINAL_SEVEN_BINDING.json').read_text())
        require(binding['functional_commit']==S4 and len(binding['original_cases'])==7,'original seven binding changed')
        for name,row in binding['source_files'].items():
            path=ROOT/name;require(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'pinned original source changed')
        source=args.inputs.resolve()
        def original_path(row):
            path=(source/row['path']).resolve()
            require(path.is_relative_to(source) and path.is_file() and not path.is_symlink(),'unsafe original artifact member')
            require(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'original scientific bytes changed')
            return path
        for row in binding['original_cases']:
            raw=json.loads(original_path(row['original_result']).read_text())
            require(raw['target']==row['target'],'original exact case specification changed')
            for m in row['inputs']:
                for item in m['exports'].values():original_path(item)
        for m in binding['original_EXTRUSION_direct_control']['original_saved_materials']:
            for item in m['exports'].values():original_path(item)
        report['original_scientific_input_binding_verified']=True;save()
        import cadquery as cq
        import product_assembly as p
        import product_nominal_motion as nominal
        import validate_product_nominal_report as guard
        import envelope_v2 as v2
        import test_l2_native
        import test_l5_native
        frozen_identity=nominal.execution_identity(S4);identity.atomic_json(out/'nominal-source-before-private.json',frozen_identity)
        report['native_started']=True;report['stage']='native_controls';save()
        report['unchanged_L2_native_controls']=test_l2_native.execute();save()
        def emit(prefix,label,body,positive=True):
            budget.check();name=prefix+'-'+label+'.brep'
            require(contract_rules.scientific_filename(name),'producer name outside frozen science grammar')
            path=science/name;require(not path.exists(),'new native export path required')
            status=body.exportBrep(str(path));require(status is True and path.stat().st_size>0,'native BREP export failed')
            record={'path':name,'bytes':path.stat().st_size,'sha256':sha(path),'native_export_status':str(status),
                'positive_whole_material_required':positive}
            exported.append(record);record['signature']=signature(body,p,positive)
            if sum(r['bytes'] for r in exported)>128*2**20:raise api.CapacityStop('new L5 scientific output capacity exhausted')
            budget.check();return record
        def keep_original(prefix,label,row,body=None,positive=True):
            result={}
            for extension,item in row['exports'].items():
                src=original_path(item);name=prefix+'-'+label+'.'+extension
                require(contract_rules.scientific_filename(name),'original science name outside grammar')
                dst=science/name;require(not dst.exists(),'original scientific copy already exists')
                shutil.copyfile(src,dst);record={'path':name,'bytes':dst.stat().st_size,'sha256':sha(dst),
                    'original_source_member_sha256':item['sha256'],'byte_identical_original':True,
                    'positive_whole_material_required':positive}
                if body is not None and extension=='brep':record['signature']=signature(body,p,positive)
                exported.append(record);result[extension]=record
            return result
        def control_checkpoint(rows):report['L5_primitive_controls_partial']=rows;save()
        report['L5_primitive_controls']=test_l5_native.execute(cq=cq,p=p,emit=emit,budget_check=budget.check,checkpoint=control_checkpoint)
        direct=binding['original_EXTRUSION_direct_control'];shapes=[];record=[]
        for m in direct['original_saved_materials']:
            body=cq.Shape.importBrep(str(original_path(m['exports']['brep'])))
            shapes.append(body);record.append(keep_original('control-original-extrusion',m['role'],m,body,m['role']=='original-shape'))
        report['original_EXTRUSION_retained_materials']=record
        def extrusion_checkpoint(value):report['original_EXTRUSION_direct_control']=value;save()
        test_l5_native.extrusion(source_shape=shapes[0],source_face=shapes[1],vector=direct['original_vector_xyz'],
            cq=cq,p=p,v2=v2,emit=emit,budget_check=budget.check,checkpoint=extrusion_checkpoint)
        bodies=None;current_contract=None
        if args.scope=='current':
            require(args.k1_near is not None and args.k1_far is not None,'actual dual-clear K1 input required')
            import frozen_key_factory_adapter as adapter
            import verify_cam_coupling as cam
            import slide_evidence as evidence
            import slide_domain as domain
            report['stage']='actual_K1_loader_and_original_five_factory_probes';save()
            k1=json.loads((HERE/'K1_BINDING.json').read_text())
            keys=adapter.load_keys({'near':args.k1_near,'far':args.k1_far},k1,p,cq,budget)
            report['actual_K1_material_prerequisite']=keys.receipt
            def construction_checkpoint(value):report['construction']=value;save()
            current_contract,bodies,construction=stage.construct_and_probe(keys=keys,adapter=adapter,nominal=nominal,cam=cam,p=p,
                original_driver=original,source_evidence=evidence,domain=domain,identity_before=frozen_identity,
                budget=budget,checkpoint=construction_checkpoint)
            report['construction']=construction;report['current_factory_five_original_probes_passed']=construction['five_factory_probes_complete']
            report['complete_current_factory_participant_names']=current_contract.names
        report['stage']='whole_q_pairs';save()
        for case in binding['original_cases']:
            budget.check();old_id=case['case_id'];call_id=args.scope+'-'+old_id;target=case['target'];spec=target['specification']
            entry={'schema':'razr-L5-whole-q-case-v1','call_id':call_id,'original_case_id':old_id,'target':target,
                'original_result_sha256':case['original_result']['sha256'],'original_disposition':case['original_disposition'],
                'execution_completed':False,'unchanged_original_postguards_passed':False,'material_readbacks':[],
                'scientific_exports':[],'original_volume_gate_mm3':1e-7,'audit':{}}
            entry_path=science/(call_id+'.json');t=time.monotonic();first=len(exported)
            def save_case():
                entry['whole_call_seconds_including_exports']=time.monotonic()-t
                entry['scientific_exports']=exported[first:];identity.atomic_json(entry_path,entry)
            save_case()
            try:
                originals=[]
                for role,m in zip(('moving-input','fixed-input'),case['inputs']):
                    body=p.single(cq.Shape.importBrep(str(original_path(m['exports']['brep']))))
                    values=cq.importers.importStep(str(original_path(m['exports']['step']))).vals();require(len(values)==1,'one whole original STEP root required')
                    step=p.single(values[0]);delta=l5.compare(p,body,step);originals.append(body)
                    entry['material_readbacks'].append({'role':role,'original_BREP_sha256':m['exports']['brep']['sha256'],
                        'original_STEP_sha256':m['exports']['step']['sha256'],'original_BREP_signature':signature(body,p),
                        'original_STEP_signature':signature(step,p),'original_BREP_STEP_identity':delta})
                if args.scope=='original':
                    participants=originals
                    for role,m,body in zip(('moving-input','fixed-input'),case['inputs'],participants):keep_original(call_id,role,m,body)
                else:
                    specifications=current_contract.specifications(target['a'],target['b'],F(0),F(12),'A')
                    require(specifications==[spec],'current whole source specification differs from original frozen full-q law')
                    participants=[bodies.material(spec[k],F(0),F(12)) for k in ('moving','fixed')]
                    for role,actual,old in zip(('moving-input','fixed-input'),participants,originals):
                        delta=l5.compare(p,actual,old)
                        entry.setdefault('current_complete_material_to_original_L1',[]).append({'role':role,'bidirectional_identity':delta})
                        emit(call_id,role,actual)
                        path=science/(call_id+'-'+role+'.step');require(not path.exists(),'new current STEP path required')
                        cq.exporters.export(actual,str(path),exportType='STEP')
                        require(path.stat().st_size>0,'current complete input STEP export failed')
                        exported.append({'path':path.name,'bytes':path.stat().st_size,'sha256':sha(path),'native_export_status':'STEP exporter returned'})
                entry['fresh_complete_input_native_bounds_mm']=[list(p.bounds(x)) for x in participants]
                save_case()
                def retain(label,body,positive=True):
                    result=emit(call_id,label,body,positive);save_case();return result
                result=l5.evaluate(*participants,spec,target,root=ROOT,cq=cq,p=p,guard=guard,emit=retain,
                    budget_check=budget.check,preserve_annular_holes=False,audit=entry['audit'])
                entry['new_result']=result;entry['execution_completed']=True
                entry['unchanged_original_postguards_passed']=contract_rules.validate_result(result,target,spec,ROOT,guard)
            except (api.CapacityStop,InterruptedError):
                entry['capacity_stop']=True;raise
            except Exception as exc:
                entry['failure_type']=type(exc).__name__
                if hasattr(exc,'partial_bridge_audit'):entry['partial_bridge_audit']=exc.partial_bridge_audit
            finally:
                save_case();report['calls'].append({'call_id':call_id,'case_json_sha256':sha(entry_path),
                    'case_json_bytes':entry_path.stat().st_size,'whole_call_seconds_including_exports':entry['whole_call_seconds_including_exports'],
                    'pair':[target['a'],target['b']],'source_q_interval_exact':target['q_interval_exact'],
                    'execution_completed':entry['execution_completed'],
                    'disposition':entry.get('new_result',{}).get('disposition','unresolved_budget' if entry.get('capacity_stop') else 'unresolved_evaluation'),
                    'unchanged_original_postguards_passed':entry['unchanged_original_postguards_passed']});save()
        report['execution_completed']=len(report['calls'])==7 and all(x['execution_completed'] for x in report['calls'])
        report['all_original_postguards_passed']=report['execution_completed'] and all(x['unchanged_original_postguards_passed'] for x in report['calls'])
        report['disposition_counts']=dict(Counter(x['disposition'] for x in report['calls']))
        report['all_seven_whole_q_pairs_clear']=report['execution_completed'] and all(x['disposition']=='clear' for x in report['calls'])
    except (api.CapacityStop,InterruptedError) as exc:
        report['capacity_failure_type']=type(exc).__name__
    except BaseException as exc:
        report['failure_type']=type(exc).__name__
    finally:
        report['all_scientific_exports']=exported
        try:
            if before is not None:
                after=identity.finish(before,executed);identity.atomic_json(out/'source-after-private.json',after)
                report['source_runtime_unchanged']=after['source_bytes_and_locked_environment_unchanged']
                report['original_executed_source_sha256']={str(Path(k).relative_to(ROOT)):v for k,v in after['executed_source_and_input_sha256'].items()}
                require(after['repository_head_at_finish']==S4 and not identity.git('status','--porcelain'),'final immutable S4 changed')
            if frozen_identity is not None:
                final=nominal.execution_identity(S4);identity.atomic_json(out/'nominal-source-after-private.json',final)
                require(final==frozen_identity,'native original source/runtime closure changed')
                report['original_nominal_identity_closure_unchanged']=True
            require(own=={n:sha(HERE/n) for n in SOURCES},'external L5 source changed');report['external_source_unchanged']=True
        except Exception as exc:
            report['postflight_failure_type']=type(exc).__name__;report['source_runtime_unchanged']=False
        if budget is not None:report['original_resource_record']=budget.record()
        save()
    print(json.dumps({k:report.get(k) for k in ('scope','execution_completed','all_original_postguards_passed','disposition_counts',
        'failure_type','capacity_failure_type','elapsed_seconds')}),flush=True)
    return 0 if (report['execution_completed'] and report['all_original_postguards_passed'] and report['source_runtime_unchanged']
        and report.get('external_source_unchanged') is True and not report.get('postflight_failure_type') and not report.get('failure_type')) else 2

if __name__=='__main__':raise SystemExit(main())
