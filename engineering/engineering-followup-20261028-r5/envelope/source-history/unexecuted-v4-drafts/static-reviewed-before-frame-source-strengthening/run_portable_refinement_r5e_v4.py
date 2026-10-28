"""Sequential owned-supervisor execution using only the published R4 inputs.

Usage: python3 -I -S -B run_portable_refinement_r5e_v4.py
       --r4-root PATH/TO/R4/envelope --output NEW_OUTPUT_DIRECTORY

No package installation, network operation, CAD import, native Common, token,
credential, or remote mutation is performed by this entry. On any failed stage
later stages remain unexecuted. Preserve its entire output directory on failure.
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
    with path.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h}


def matches(path,record):
    actual=identity(path)
    need(all(actual[k]==record[k] for k in ('bytes','sha256')),'source/input identity differs: '+str(path))
    return actual


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--r4-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0,'isolated unoptimized Python entry required')
    src=Path(__file__).resolve().parent;r4=args.r4_root.resolve();out=args.output.resolve()
    need(not out.exists(),'new output directory required')
    out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    run={'schema':'razr-r5e-portable-exact-refinement-pipeline-v4','started_utc':datetime.now(timezone.utc).isoformat(),
         'completed':False,'stages':[],'native_Common_called':False,'native_material_semantics_verified':False,
         'compiled_transform_error_verified':False,'full_continuous_G2':False,'all_blockers_closed':False,
         'original_clearance_threshold_changed':False,'original_displacement_boxes_changed':False,
         'source_root':str(src),'public_r4_root':str(r4),'source_commit':'c5f6606924937d716b007cd3ffa8e54df8ecfa5d'}
    def save():
        run['elapsed_seconds']=time.monotonic()-started
        write(out/'pipeline.json',run)
    save()
    try:
        lock_path=src/'R5E_PORTABLE_SOURCE_LOCK_V4.json';lock=json.loads(lock_path.read_text())
        run['source_lock_identity']=identity(lock_path)
        need(lock['source_commit']==run['source_commit'],'unexpected R4 source anchor')
        all_sources=[]
        for record in lock['r5_files']:
            path=src/record['path'];need(path.resolve().is_relative_to(src),'R5 source path escapes registered root')
            all_sources.append(matches(path,record))
        for record in lock['r4_source_files']:
            path=r4/record['path'];need(path.resolve().is_relative_to(r4),'R4 source path escapes registered root')
            all_sources.append(matches(path,record))
        run['actual_source_identities']=all_sources
        bridge_path=src/'R5E_PUBLIC_INPUT_BRIDGE.json';bridge=json.loads(bridge_path.read_text())
        need(bridge['source_commit']==run['source_commit'] and len(bridge['files'])==19,'complete public bridge required')
        run['public_inputs']=[]
        for row in bridge['files']:
            path=r4/row['path'];need(path.resolve().is_relative_to(r4),'public input path escapes registered root')
            need(row['decoded_json_equal'] and not row['changed_strings'],'bridge altered decoded values')
            run['public_inputs'].append(matches(path,row['public_identity']))
        need(len({r['path'] for r in bridge['files']})==19,'duplicate public input bridge path')
        baseline=json.loads((r4/'support-v4/report.json').read_text())
        expected=[[case,frame] for case in ['case-001','case-006','case-028','case-037','case-054','case-063','case-072','case-089'] for frame in (1,2)]
        need([[r['case_id'],r['frame']] for r in baseline['frames']]==expected,'original 16 case/frame sequence differs')
        supervisor=r4/'supervise_owned_pure_math_r4e_v2.py'
        entry=r4/'run_owned_pure_math_r4e_v3.py'
        owned=r4/'additional-bspline-v1/source/source-original/owned_process.py'
        shared_base={'wall_seconds':600,'RSS_limit_bytes':805306368,'shared_ceiling_bytes':7301444403,
                     'disk_floor_bytes':104857600,'expected_output_bytes':41943040,'maximum_output_bytes':41943040,
                     'metadata_margin_bytes':4194304,'zero_RSS_missing_observations_allowed':False,
                     'supervisor_sha256':identity(supervisor)['sha256'],'worker_entry':str(entry),
                     'worker_entry_sha256':identity(entry)['sha256'],'owned_process':identity(owned),
                     'canonical_worker_options':['--contract','--output']}
        run['unchanged_process_limits']={k:shared_base[k] for k in ['wall_seconds','RSS_limit_bytes','shared_ceiling_bytes','disk_floor_bytes','maximum_output_bytes','metadata_margin_bytes']}
        run['environment']={'python':sys.version,'executable':identity(sys.executable),'platform':sys.platform,
                            'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
        save()
        finished={}
        sequence=[('single-retained-cell','single_retained_cell'),('verify-single','verify_single'),
                  ('preflight','preflight'),('all-refined','all_raw_refined'),('verify-all','verify_all')]
        for label,phase in sequence:
            verifying=phase.startswith('verify_')
            worker=src/('verify_exterior_refinement_r5e_v4.py' if verifying else 'exterior_refinement_r5e_v4.py')
            worker_output=out/label
            contract={'schema':'razr-r5e-portable-public-refinement-contract-v4','registered_utc':datetime.now(timezone.utc).isoformat(),
                      'phase':phase,'producer_sha256':identity(worker)['sha256'],
                      'r4_report':identity(r4/'support-v4/report.json'),
                      'r4_independent_report':identity(r4/'independent-support-v4/report.json'),
                      'r4_stationary_diagnostic':identity(r4/'remaining-spatial-diagnostic/report.json'),
                      'public_input_bridge':identity(bridge_path),'method':identity(src/'R5E_REFINEMENT_V4_BASIS.md'),
                      'capacity':{'wall_seconds':600,'RSS_limit_bytes':805306368,'maximum_splits':4096,'maximum_depth':24,'maximum_boundary_box_tests':12000000,
                                  'tiny_retained_volume_exact':str(Fraction(1e-7)/100000)},
                      'completed_prerequisites':[],'source_commit':run['source_commit'],
                      'base_producer_source':identity(src/'exterior_channels_r5e_v3.py'),
                      'base_verifier_source':identity(src/'verify_exterior_channels_r5e_v3.py'),
                      'real_retained_cell_selection':identity(src/'R5E_V4_REAL_RETAINED_CELL.json'),
                      'native_Common_as_acceptance_premise':False,'all_original_D_components_retained':True,
                      'original_float64_TOL_unchanged':True,'native_boundary_semantics_remains_a_premise':True,'current_factory_G2_qualified':False}
            if phase=='single_retained_cell':contract.update(case_id='case-001',frame=1)
            if phase in ('preflight','all_raw_refined'):
                need(finished['verify_single']['report']['execution_completed'],'retained-cell independent verification must precede larger work')
                contract['independent_single_verification']={
                    'report':identity(finished['verify_single']['report_path']),
                    'supervisor':identity(finished['verify_single']['controller_path'])}
                prereq=['single_retained_cell']+(['preflight'] if phase=='all_raw_refined' else [])
                for prior in prereq:
                    item=finished[prior]
                    contract['completed_prerequisites'].append({'phase':prior,'report':identity(item['report_path']),'supervisor':identity(item['controller_path'])})
            if phase=='all_raw_refined':
                capacity=finished['preflight']['report']
                need(capacity['execution_completed'] and capacity['total_original_roots']==1474,'actual full preflight required')
                need(capacity['complete_phase_maximum_tree_nodes']==9666 and capacity['new_predicate_hard_budget']==12000000,'finite preflight exceeds registered algorithm bound')
                contract['actual_capacity_basis']=identity(finished['preflight']['report_path'])
            if verifying:
                prior='single_retained_cell' if phase=='verify_single' else 'all_raw_refined'
                contract['verifier_sha256']=identity(worker)['sha256']
                contract['producer_report']=identity(finished[prior]['report_path'])
                contract['expected_phase']=prior
                contract['expected_case_frames']=[['case-001',1]] if prior=='single_retained_cell' else expected
                contract['producer_owned_supervision']=identity(finished[prior]['controller_path'])
            cp=out/(label+'-contract.json');write(cp,contract)
            supervision=dict(shared_base,schema='razr-r5e-portable-owned-refinement-supervision-v4',registered_utc=contract['registered_utc'],
                             registered_math_contract_sha256=identity(cp)['sha256'],worker=identity(worker),
                             worker_output_directory=str(worker_output),
                             algorithm_basis='Bounded exact endpoint split trees over unchanged complete original boundary boxes; actual retained-cell proof and measured all16 preflight precede full refinement. All pending and thin leaves retain exact volume.')
            sp=out/(label+'-supervision-contract.json');write(sp,supervision)
            supervision_dir=out/(label+'-supervision')
            command=[sys.executable,'-I','-S','-B',str(supervisor),'--contract',str(sp),'--out',str(supervision_dir),
                     '--','--contract',str(cp),'--output',str(worker_output)]
            stage={'label':label,'phase':phase,'worker_started_by_driver':False,'completed':False,
                   'contract':identity(cp),'supervision_contract':identity(sp),'command':command}
            run['stages'].append(stage);save()
            log=out/(label+'-driver.log')
            with log.open('wb') as stream:
                stage['worker_started_by_driver']=True;save()
                completed=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=False)
            stage['supervisor_exit_code']=completed.returncode;stage['driver_log']=identity(log)
            controller_path=supervision_dir/'controller.json'
            if controller_path.exists():
                stage['controller']=identity(controller_path)
                controller=json.loads(controller_path.read_text())
                stage['actual_worker_started']=controller.get('worker_started',False)
                stage['resource_stop']=controller.get('resource_stop')
                stage['owned_supervisor_completed']=controller.get('completed',False)
            else:controller={}
            save()
            need(completed.returncode==0 and controller.get('completed') is True,'owned stage failed; later stages remain unexecuted: '+label)
            report_path=worker_output/'report.json';report=json.loads(report_path.read_text())
            need(report['execution_completed'],'scientific stage incomplete: '+label)
            stage['report']=identity(report_path);stage['completed']=True
            finished[phase]={'report':report,'report_path':report_path,'controller_path':controller_path}
            save()
            if phase=='verify_single':
                witness=finished['single_retained_cell']['report']
                need(Fraction(witness['frames'][0]['excluded_open_leaf_sum_exact'])>0 and witness['frames'][0]['exact_splits_this_frame']>0 and witness['conditional_clearance_passes']==1,
                     'first actual retained cell not reduced below original TOL; full execution withheld')
        run['conditional_raw_clearance_passes']=finished['all_raw_refined']['report']['conditional_clearance_passes']
        run['independent_conditional_raw_clearance_passes']=finished['verify_all']['report']['conditional_clearance_passes']
        need(run['conditional_raw_clearance_passes']==run['independent_conditional_raw_clearance_passes'],'independent overall gates differ')
        run['actual_frame_count']=len(finished['all_raw_refined']['report']['frames'])
        run['source_and_public_inputs_unchanged']=all(identity(r['path'])==r for r in run['actual_source_identities']+run['public_inputs'])
        need(run['source_and_public_inputs_unchanged'],'source/public input changed during pipeline')
        run['completed']=True
    except BaseException as exc:
        run['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        run['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        print(json.dumps({k:run.get(k) for k in ('completed','conditional_raw_clearance_passes','independent_conditional_raw_clearance_passes','actual_frame_count','elapsed_seconds','failure')}),flush=True)
    return 0 if run['completed'] else 2


if __name__=='__main__':raise SystemExit(main())
