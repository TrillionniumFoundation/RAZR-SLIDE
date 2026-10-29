"""Five original owned stages for new V9 original Line-plane source hulls.

No network, package installation, native operation or old producer rerun is
performed. Every new source and original V5/V6 artifact remains byte-bound.
"""
import argparse
from datetime import datetime,timezone
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


def need(ok,message):
    if not ok:raise ValueError(message)


def identity(path):
    path=Path(path).resolve()
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha}


def matches(path,record):
    actual=identity(path);need(all(actual[k]==record[k] for k in ('bytes','sha256')),'source/input differs: '+str(path));return actual


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--r4-root',type=Path,required=True);parser.add_argument('--base-v5-root',type=Path,required=True)
    parser.add_argument('--base-v6-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0,'isolated unoptimized Python entry required')
    src=Path(__file__).resolve().parent;r4=args.r4_root.resolve();v5=args.base_v5_root.resolve();v6=args.base_v6_root.resolve();out=args.output.resolve()
    need(not out.exists(),'new output directory required');out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    run={'schema':'razr-r7e-portable-planar-exterior-pipeline-v9','started_utc':datetime.now(timezone.utc).isoformat(),
         'completed':False,'stages':[],'source_root':str(src),'public_r4_root':str(r4),'base_V5_root':str(v5),'base_V6_root':str(v6),
         'source_commit':'c5f6606924937d716b007cd3ffa8e54df8ecfa5d','native_Common_called':False,'native_material_semantics_verified':False,
         'compiled_transform_error_verified':False,'full_continuous_G2':False,'all_blockers_closed':False,
         'conditional_planar_exterior_model_only':True,'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
         'native_planar_region_semantics_verified':False,'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
         'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,
         'original_clearance_threshold_changed':False,'original_displacement_boxes_changed':False,
         'original_V3_raw_clearance_passes_unchanged':4,'original_V4_selected_cell_bound_and_control_failure_unchanged':True,
         'original_V7_failure_preserved':True,'missing_V8_archived_bytes_not_reconstructed':True,
         'actual_V5_conditional_passes_preserved':8,'actual_V6_conditional_passes_preserved':8,
         'V5_producer_rerun':False,'V6_producer_rerun':False}
    def save():
        run['elapsed_seconds']=time.monotonic()-started;write(out/'pipeline.json',run)
    save()
    try:
        lock_path=src/'R7E_PORTABLE_SOURCE_LOCK_V9.json';lock=json.loads(lock_path.read_text());run['source_lock_identity']=identity(lock_path)
        need(lock['schema']=='razr-r7e-portable-source-lock-v9-original-Line-plane-hulls' and lock['source_commit']==run['source_commit'],
             'registered new source lock or original anchor differs')
        sources=[]
        for row in lock['r5_files']:
            path=src/row['path'];need(path.resolve().is_relative_to(src),'registered R5 source escapes root');sources.append(matches(path,row))
        for row in lock['r4_source_files']:
            path=r4/row['path'];need(path.resolve().is_relative_to(r4),'original R4 source escapes root');sources.append(matches(path,row))
        run['actual_source_identities']=sources
        bridge_path=src/'R5E_PUBLIC_INPUT_BRIDGE.json';bridge=json.loads(bridge_path.read_text())
        need(bridge['source_commit']==run['source_commit'] and len(bridge['files'])==19,'complete original R4 bridge required')
        run['public_inputs']=[]
        for row in bridge['files']:
            path=r4/row['path'];need(path.resolve().is_relative_to(r4),'original public input escapes root')
            need(row['decoded_json_equal'] and not row['changed_strings'],'original public bridge alters scientific values')
            run['public_inputs'].append(matches(path,row['public_identity']))
        v5_bridge_path=src/'R5E_V6_BASE_V5_INPUT_BRIDGE.json';v5_bridge=json.loads(v5_bridge_path.read_text())
        need(v5_bridge['actual_run_id']==40645988108 and v5_bridge['original_reports_or_certificates_edited'] is False and
             v5_bridge['path_mapping_only'] is True and len(v5_bridge['files'])==25,'immutable actual V5 bridge differs')
        run['actual_V5_inputs']=[]
        for row in v5_bridge['files']:
            path=v5/row['path'];need(path.resolve().is_relative_to(v5),'actual V5 input escapes root');run['actual_V5_inputs'].append(matches(path,row))
        v6_bridge_path=src/'R5E_V7_BASE_V6_INPUT_BRIDGE.json';v6_bridge=json.loads(v6_bridge_path.read_text())
        need(v6_bridge['actual_execution_kind']=='local_owned_pipeline' and v6_bridge['original_reports_or_certificates_edited'] is False and
             v6_bridge['path_mapping_only'] is True and len(v6_bridge['files'])==53,'immutable actual V6 bridge differs')
        run['actual_V6_inputs']=[]
        for row in v6_bridge['files']:
            path=v6/row['path'];need(path.resolve().is_relative_to(v6),'actual V6 input escapes root');run['actual_V6_inputs'].append(matches(path,row))
        for name,rows,count in [('R4',run['public_inputs'],19),('V5',run['actual_V5_inputs'],25),('V6',run['actual_V6_inputs'],53)]:
            need(len(rows)==len({r['path'] for r in rows})==count,'complete unique '+name+' input census required')
        expected=[[c,f] for c in ['case-001','case-006','case-028','case-037','case-054','case-063','case-072','case-089'] for f in (1,2)]
        baseline=json.loads((r4/'support-v4/report.json').read_text())
        need([[r['case_id'],r['frame']] for r in baseline['frames']]==expected,'original full16 case/frame order differs')
        supervisor=r4/'supervise_owned_pure_math_r4e_v2.py';entry=r4/'run_owned_pure_math_r4e_v3.py'
        owned=r4/'additional-bspline-v1/source/source-original/owned_process.py'
        shared_base={'wall_seconds':600,'RSS_limit_bytes':805306368,'shared_ceiling_bytes':7301444403,
                     'disk_floor_bytes':104857600,'expected_output_bytes':41943040,'maximum_output_bytes':41943040,
                     'metadata_margin_bytes':4194304,'zero_RSS_missing_observations_allowed':False,
                     'supervisor_sha256':identity(supervisor)['sha256'],'worker_entry':str(entry),'worker_entry_sha256':identity(entry)['sha256'],
                     'owned_process':identity(owned),'canonical_worker_options':['--contract','--output']}
        run['unchanged_process_limits']={k:shared_base[k] for k in ['wall_seconds','RSS_limit_bytes','shared_ceiling_bytes','disk_floor_bytes','maximum_output_bytes','metadata_margin_bytes']}
        run['environment']={'python':sys.version,'executable':identity(sys.executable),'platform':sys.platform,
                            'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
        save();finished={}
        sequence=[('single-planar-exterior-leaf','single_planar_exterior_leaf'),('verify-single','verify_single'),
                  ('preflight-planar-exterior','preflight_planar_exterior'),('all-planar-exterior-frames','all_planar_exterior_frames'),('verify-all','verify_all')]
        for label,phase in sequence:
            verifying=phase.startswith('verify_');worker=src/('verify_planar_exterior_r7e_v9.py' if verifying else 'planar_exterior_refinement_r7e_v9.py')
            output=out/label
            contract={'schema':'razr-r7e-portable-planar-exterior-contract-v9','registered_utc':datetime.now(timezone.utc).isoformat(),
                      'phase':phase,'producer_sha256':identity(worker)['sha256'],'source_commit':run['source_commit'],
                      'r4_report':identity(r4/'support-v4/report.json'),'r4_independent_report':identity(r4/'independent-support-v4/report.json'),
                      'r4_stationary_diagnostic':identity(r4/'remaining-spatial-diagnostic/report.json'),'public_input_bridge':identity(bridge_path),
                      'method':identity(src/'R7E_ORIGINAL_LINE_PLANE_V9_BASIS.md'),
                      'capacity':{'wall_seconds':600,'RSS_limit_bytes':805306368,'maximum_splits':4096,'maximum_depth':24,
                                  'maximum_boundary_box_tests':12000000,'maximum_support_inequality_tests':12000000,
                                  'tiny_retained_volume_exact':str(Fraction(1e-7)/100000),'maximum_boundary_pieces_per_material':4096,
                                  'cylinder_angular_patch_count':64,'circle_angular_patch_count':64,'Taylor_term_count':24,'centre_grid_denominator':65536,
                                  'maximum_UV_pieces_per_face':225,'maximum_total_UV_pieces':4100,'maximum_planar_models':50,
                                  'maximum_actual_V6_retained_roots':4943,'all_UV_tests_charged_to_original_combined_budgets':True},
                      'completed_prerequisites':[],
                      'base_channel_source':identity(src/'exterior_channels_r5e_v3.py'),
                      'base_verifier_source':identity(src/'verify_exterior_channels_r5e_v3.py'),
                      'single_verifier_source':identity(src/'verify_planar_exterior_r7e_v9.py'),
                      'planar_producer_source':identity(src/'planar_exterior_refinement_r7e_v9.py'),
                      'planar_model_source':identity(src/'planar_exterior_model_r7e_v9.py'),
                      'extra_line_plane_source':identity(src/'R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json'),
                      'primitive_producer_source':identity(src/'primitive_refinement_r5e_v6.py'),
                      'primitive_model_source':identity(src/'primitive_support_model_r5e_v6.py'),
                      'primitive_source_bundle':identity(src/'R5E_V6_PRIMITIVE_SOURCE.json.gz'),
                      'base_V6_verifier_source':identity(src/'verify_primitive_support_r5e_v6.py'),
                      'base_V6_root':str(v6),'base_V6_input_bridge':identity(v6_bridge_path),
                      'base_V6_source_lock':identity(src/'R5E_PORTABLE_SOURCE_LOCK_V6.json'),
                      'base_V6_actual_report':identity(v6/'all-primitive-support-frames/report.json'),
                      'base_V6_actual_independent_report':identity(v6/'verify-all/report.json'),
                      'base_V6_actual_owned_supervision':identity(v6/'all-primitive-support-frames-supervision/controller.json'),
                      'base_V6_actual_independent_owned_supervision':identity(v6/'verify-all-supervision/controller.json'),
                      'base_V5_root':str(v5),'base_V5_input_bridge':identity(v5_bridge_path),
                      'base_V5_source_lock':identity(src/'R5E_PORTABLE_SOURCE_LOCK_V5.json'),
                      'base_V5_verifier_source':identity(src/'verify_exterior_trim_r5e_v5.py'),
                      'V5_trim_source_bundle':identity(src/'R5E_V5_PLANAR_TRIM_SOURCE.json.gz'),
                      'base_V5_actual_report':identity(v5/'all-trim-model-frames/report.json'),
                      'base_V5_actual_independent_report':identity(v5/'verify-all/report.json'),
                      'base_V5_actual_owned_supervision':identity(v5/'all-trim-model-frames-supervision/controller.json'),
                      'base_V5_actual_independent_owned_supervision':identity(v5/'verify-all-supervision/controller.json'),
                      'real_retained_leaf_selection':identity(src/'R5E_V7_REAL_RETAINED_LEAF.json'),
                      'static_source_capacity':identity(src/'R7E_V9_STATIC_SOURCE_CAPACITY.json'),
                      'all_original_D_components_retained':True,'original_float64_TOL_unchanged':True,'native_Common_as_acceptance_premise':False,
                      'conditional_planar_exterior_model_only':True,'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
                      'native_planar_region_semantics_verified':False,'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
                      'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,'full_continuous_G2':False}
            if phase=='single_planar_exterior_leaf':contract.update(case_id='case-028',frame=1)
            if phase in ('preflight_planar_exterior','all_planar_exterior_frames'):
                need(finished['verify_single']['report']['execution_completed'],'actual independent selected-leaf proof required')
                contract['independent_single_verification']={'report':identity(finished['verify_single']['report_path']),
                                                             'supervisor':identity(finished['verify_single']['controller_path'])}
                prerequisites=['single_planar_exterior_leaf']+(['preflight_planar_exterior'] if phase=='all_planar_exterior_frames' else [])
                for prior in prerequisites:
                    item=finished[prior];contract['completed_prerequisites'].append({'phase':prior,'report':identity(item['report_path']),
                                                                                  'supervisor':identity(item['controller_path'])})
            if phase=='all_planar_exterior_frames':
                capacity=finished['preflight_planar_exterior']['report']
                need(capacity['execution_completed'] and capacity['all_frame_capacity_observations_completed'] and
                     capacity['total_actual_V6_retained_roots']==4943 and capacity['complete_phase_maximum_tree_nodes']==13135,
                     'actual finite all16 retained-forest preflight required')
                need(capacity['maximum_UV_pieces_per_face']<=225 and capacity['actual_total_UV_boundary_pieces']<=4100 and
                     capacity['maximum_complete_spatial_pieces_per_material']<=4096,'actual fixed source census exceeds capacity')
                contract['actual_capacity_basis']=identity(finished['preflight_planar_exterior']['report_path'])
            if verifying:
                prior='single_planar_exterior_leaf' if phase=='verify_single' else 'all_planar_exterior_frames'
                contract['verifier_sha256']=identity(worker)['sha256'];contract['producer_report']=identity(finished[prior]['report_path'])
                contract['expected_phase']=prior;contract['expected_case_frames']=[['case-028',1]] if prior=='single_planar_exterior_leaf' else expected
                contract['producer_owned_supervision']=identity(finished[prior]['controller_path'])
            cp=out/(label+'-contract.json');write(cp,contract)
            supervision=dict(shared_base,schema='razr-r7e-portable-owned-planar-exterior-supervision-v9',registered_utc=contract['registered_utc'],
                             registered_math_contract_sha256=identity(cp)['sha256'],worker=identity(worker),worker_output_directory=str(output),
                             algorithm_basis='New complete closed-UV exterior paths for immutable actual V6 retained leaves. Exact plane inverse and full original D, complete original Line/Circle covers and explicit bounded closure model, strict closed separation, no winding/sample membership. Fixed64 patches/24 terms/4100 totalUV source pieces, including only the two original Line-plane additions; original48plane census unchanged. All spatial and UV tests share original12M budgets. Actual first retained leaf and independent controls precede all16 measured source preflight and bounded full refinement; source/native membership stays open.')
            sp=out/(label+'-supervision-contract.json');write(sp,supervision);supervision_dir=out/(label+'-supervision')
            command=[sys.executable,'-I','-S','-B',str(supervisor),'--contract',str(sp),'--out',str(supervision_dir),
                     '--','--contract',str(cp),'--output',str(output)]
            stage={'label':label,'phase':phase,'worker_started_by_driver':False,'completed':False,
                   'contract':identity(cp),'supervision_contract':identity(sp),'command':command};run['stages'].append(stage);save()
            log=out/(label+'-driver.log')
            with log.open('wb') as stream:
                stage['worker_started_by_driver']=True;save();completed=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=False)
            stage['supervisor_exit_code']=completed.returncode;stage['driver_log']=identity(log);controller_path=supervision_dir/'controller.json'
            if controller_path.exists():
                stage['controller']=identity(controller_path);controller=json.loads(controller_path.read_text())
                stage['actual_worker_started']=controller.get('worker_started',False);stage['resource_stop']=controller.get('resource_stop')
                stage['owned_supervisor_completed']=controller.get('completed',False)
            else:controller={}
            save();need(completed.returncode==0 and controller.get('completed') is True,'owned stage failed; later stages unexecuted: '+label)
            report_path=output/'report.json';report=json.loads(report_path.read_text());need(report['execution_completed'],'scientific stage incomplete: '+label)
            stage['report']=identity(report_path);stage['completed']=True;finished[phase]={'report':report,'report_path':report_path,'controller_path':controller_path};save()
            if phase=='verify_single':
                first=finished['single_planar_exterior_leaf']['report'];row=first['frames'][0]
                need(Fraction(row['newly_excluded_open_leaf_sum_exact'])>0 and first['planar_exterior_model_conditional_clearance_passes']==1 and
                     row['actual_planar_exterior_separator_count_in_excluded_leaves']>0,
                     'first actual planar-exterior witness failed the original TOL or lacked actual new planar proof; later work withheld')
                need(report['planar_exterior_model_conditional_clearance_passes']==1,'actual independent first-leaf conditional pass required')
        run['planar_exterior_model_conditional_clearance_passes']=finished['all_planar_exterior_frames']['report']['planar_exterior_model_conditional_clearance_passes']
        run['independent_planar_exterior_model_conditional_clearance_passes']=finished['verify_all']['report']['planar_exterior_model_conditional_clearance_passes']
        need(run['planar_exterior_model_conditional_clearance_passes']==run['independent_planar_exterior_model_conditional_clearance_passes'],'independent whole-stage counts differ')
        run['actual_frame_count']=len(finished['all_planar_exterior_frames']['report']['frames'])
        watched=run['actual_source_identities']+run['public_inputs']+run['actual_V5_inputs']+run['actual_V6_inputs']
        run['source_and_public_inputs_unchanged']=all(identity(row['path'])==row for row in watched)
        need(run['source_and_public_inputs_unchanged'],'source or immutable input changed');run['completed']=True
    except BaseException as exc:
        run['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        run['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        print(json.dumps({k:run.get(k) for k in ('completed','planar_exterior_model_conditional_clearance_passes','independent_planar_exterior_model_conditional_clearance_passes','actual_frame_count','elapsed_seconds','failure')}),flush=True)
    return 0 if run['completed'] else 2


if __name__=='__main__':raise SystemExit(main())
