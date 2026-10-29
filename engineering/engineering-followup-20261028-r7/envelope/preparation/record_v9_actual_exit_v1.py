"""Record completed V9 driver exit and read every frozen input/output byte."""
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
HERE = ROOT / 'local-v9'
ACTUAL = HERE / 'attempt-1'


def ident(path):
    path = path.resolve()
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return {'path':str(path), 'bytes':path.stat().st_size, 'sha256':h.hexdigest()}


def main():
    started = time.monotonic()
    registration_path = HERE / 'R7E_V9_LOCAL_EXECUTION_REGISTRATION_V1.json'
    registration = json.loads(registration_path.read_text())
    launch_request = HERE / 'R7E_V9_LOCAL_LAUNCH_REQUEST_V1.json'
    pipeline = json.loads((ACTUAL / 'pipeline.json').read_text())
    producer_path = ACTUAL / 'single-planar-exterior-leaf/report.json'
    checker_path = ACTUAL / 'verify-single/report.json'
    producer = json.loads(producer_path.read_text()); checker = json.loads(checker_path.read_text())
    watch = [r for group in registration['groups'].values() for r in group]
    after = [ident(Path(r['path'])) for r in watch]
    unchanged = after == watch
    file_rows = []
    for p in sorted(ACTUAL.rglob('*')):
        if p.is_file():
            assert not p.is_symlink()
            actual = ident(p)
            file_rows.append(dict(actual,path=p.relative_to(ACTUAL).as_posix()))
    manifest = {'schema':'razr-r7e-v9-actual-output-byte-manifest-v1','created_utc':datetime.now(timezone.utc).isoformat(),
                'actual_root':str(ACTUAL),'files':file_rows,'member_count':len(file_rows),
                'total_bytes':sum(r['bytes'] for r in file_rows),'complete_actual_member_set_enumerated':True,
                'failed_original_first_gate_preserved':True,'actual_driver_exit_code':2}
    mp = HERE / 'R7E_V9_LOCAL_ACTUAL_OUTPUT_MANIFEST_V1.json'; assert not mp.exists()
    mp.write_text(json.dumps(manifest,indent=2)+'\n')
    frame = producer['frames'][0]
    controls = {name: {'record_count':len(value),'actual_rejected_count':sum(x.get('actual_rejected') is True for x in value),
                       'not_applicable_count':sum(x.get('status') == 'not_applicable' for x in value)}
                for name,value in checker.items() if name.endswith('negative_controls') and isinstance(value,list)}
    stages = []
    for stage in pipeline['stages']:
        controller = json.loads(Path(stage['controller']['path']).read_text())
        entry = json.loads((Path(stage['controller']['path']).parent / 'entry-receipt.json').read_text())
        stages.append({'label':stage['label'],'phase':stage['phase'],'stage_completed':stage['completed'],
                       'worker_started':controller['worker_started'],'worker_exit_code':controller['worker_exit_code'],
                       'controller_completed':controller['completed'],'resource_stop':controller['resource_stop'],
                       'controller_elapsed_seconds':controller['elapsed_seconds'],
                       'entry_peak_RSS_bytes':entry['peak_RSS_bytes'],
                       'native_geometry_imported':entry['native_geometry_imported']})
    receipt = {'schema':'razr-r7e-v9-local-launch-and-actual-exit-receipt-v1',
        'recorded_utc':datetime.now(timezone.utc).isoformat(),'source':ident(Path(__file__)),
        'registration':ident(registration_path),'launch_request':ident(launch_request),
        'exact_command':registration['command'],'working_directory':registration['working_directory'],
        'actual_driver_exit_code':2,'exit_observation':'Completed execution tool returned process exit code 2 after original driver ended.',
        'actual_pipeline_started_utc':pipeline['started_utc'],'actual_pipeline_finished_utc':pipeline['finished_utc'],
        'actual_pipeline_elapsed_seconds':pipeline['elapsed_seconds'],
        'timing_scope':'driver-reported actual monotonic duration; outer API waiting time is not substituted',
        'pipeline':ident(ACTUAL / 'pipeline.json'),'stdout':ident(HERE / 'driver.stdout.log'),'stderr':ident(HERE / 'driver.stderr.log'),
        'complete_actual_output_manifest':ident(mp),'input_count_before':len(watch),'input_count_after':len(after),
        'all146_original_inputs_and_frozen_sources_unchanged':unchanged,
        'post_execution_input_identities':after,'stages':stages,
        'producer':ident(producer_path),'independent_checker':ident(checker_path),
        'producer_execution_completed':producer['execution_completed'],'independent_execution_completed':checker['execution_completed'],
        'actual_first_frame':{'case_id':frame['case_id'],'frame':frame['frame'],'source_leaf':[76,47],
            'upper_exact':frame['planar_exterior_model_conditional_upper_exact_mm3'],
            'saved_planar_u':frame['actual_planar_exterior_separator_count_in_excluded_leaves'],
            'producer_conditional_upper_pass_count':producer['planar_exterior_model_conditional_clearance_passes'],
            'independent_conditional_upper_pass_count':checker.get('planar_exterior_model_conditional_clearance_passes'),
            'models_applied':frame['applied_planar_model_count'],'models_rejected':frame['rejected_planar_model_count'],
            'additional_planes_applied':frame['additional_applied_plane_count'],'additional_planes_rejected':frame['additional_rejected_plane_count'],
            'complete_UV_boundary_pieces':frame['UV_boundary_piece_count']},
        'counters':producer['counters'],'actual_independent_controls':controls,
        'actual_independent_saved_planar_u':checker.get('total_saved_planar_u_separations_verified'),
        'original_first_leaf_gate_passed':bool(Fraction(frame['newly_excluded_open_leaf_sum_exact']) > 0 and
            producer['planar_exterior_model_conditional_clearance_passes'] == 1 and frame['actual_planar_exterior_separator_count_in_excluded_leaves'] > 0),
        'pipeline_completed':pipeline['completed'],'actual_pipeline_failure':pipeline.get('failure'),
        'unexecuted_later_phases':['preflight_planar_exterior','all_planar_exterior_frames','verify_all'],
        'original_resource_gates_relaxed':False,'original_first_leaf_gate_relaxed':False,
        'original_full16_qualification_claimed':False,'native_qualification_claimed':False,'full_continuous_G2':False,
        'all_blockers_closed':False,'readback_elapsed_seconds':time.monotonic()-started}
    p = HERE / 'R7E_V9_LOCAL_LAUNCH_RECEIPT_V1.json'; assert not p.exists()
    p.write_text(json.dumps(receipt,indent=2)+'\n')
    assert unchanged
    assert producer['execution_completed'] and checker['execution_completed']
    assert len(stages) == 2 and all(s['worker_exit_code'] == 0 and s['controller_completed'] and s['resource_stop'] is None for s in stages)
    assert len(file_rows) == 16 and not receipt['original_first_leaf_gate_passed'] and not pipeline['completed']
    print(json.dumps({'receipt':ident(p),'manifest':ident(mp),'output_files':len(file_rows),
        'output_bytes':manifest['total_bytes'],'all146_inputs_unchanged':unchanged,
        'pipeline_elapsed_seconds':pipeline['elapsed_seconds'],'stages':stages,'first':receipt['actual_first_frame'],
        'controls':controls,'failure':pipeline.get('failure')}))


if __name__ == '__main__':
    main()
