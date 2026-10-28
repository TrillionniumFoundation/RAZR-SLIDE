"""Launch the byte-bound local V6 pipeline after independent static review.

This adds identity checks only. The frozen original owned supervisors retain
all scientific-stage resource admission and process-ownership decisions.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLAN_SHA = 'd260d8520add1e1354d26acd369d56e87eeefe99f5ef3264b7a6bb905f893083'
LOCK_SHA = '5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499'
STATIC_SHA = 'ec0cba1ff1442ec9cb0d835e429b9134aa47ba6d55330e81262ac27404a1104d'


def identity(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest}


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0,
            'isolated unoptimized Python launcher required')
    receipt_path = HERE / 'R5_V6_LOCAL_LAUNCH_RECEIPT_V1.json'
    require(not receipt_path.exists(), 'preserve the prior launch receipt; never overwrite an attempt')
    started = time.monotonic()
    record = {'schema': 'r5-v6-local-frozen-entry-receipt-v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'launcher_identity': identity(__file__), 'driver_started': False, 'driver_completed': False,
              'local_execution': True, 'GitHub_run_execution_claimed': False,
              'source_lock_sha256_literal': LOCK_SHA, 'original_owned_supervisors_unchanged': True,
              'native_operations_by_launcher': 0, 'mathematical_operations_by_launcher': 0,
              'full_continuous_G2': False, 'all_blockers_closed': False}

    def save():
        record['elapsed_seconds'] = time.monotonic() - started
        receipt_path.write_text(json.dumps(record, indent=2) + '\n')

    save()
    try:
        plan_path = HERE / 'R5_V6_LOCAL_EXECUTION_READINESS.json'
        record['readiness_identity'] = identity(plan_path)
        require(record['readiness_identity']['sha256'] == PLAN_SHA, 'local preregistered plan changed')
        plan = json.loads(plan_path.read_text())
        record['python_identity'] = identity(sys.executable)
        require(record['python_identity'] == plan['python']['executable'], 'planned Python executable changed')
        static_path = ROOT / 'r5-integration/independent-primitive-v6-preexecution-review/R5_V6_FINAL_INDEPENDENT_STATIC_REVIEW.json'
        record['independent_final_static_review'] = identity(static_path)
        require(record['independent_final_static_review']['sha256'] == STATIC_SHA, 'final static review identity differs')
        static = json.loads(static_path.read_text())
        require(static['schema'] == 'razr-r5e-v6-independent-final-static-source-review' and
                static['static_review_completed'] is True and static['new_mathematical_qualification'] is False,
                'the prerequisite is a completed independent static review only')
        lock_path = HERE / 'input-snapshot-v1/source/R5E_PORTABLE_SOURCE_LOCK_V6.json'
        record['actual_snapshot_lock'] = identity(lock_path)
        require(record['actual_snapshot_lock']['sha256'] == LOCK_SHA, 'literal source-lock SHA differs')
        for row in plan['source_snapshots']:
            require(identity(row['source']['path']) == row['source'], 'an original source/input changed')
            require(identity(row['snapshot']['path']) == row['snapshot'], 'a frozen snapshot changed')
        record['source_and_snapshot_files_rehashed_before_launch'] = len(plan['source_snapshots'])
        command = plan['exact_driver_command']
        require(command[0] == sys.executable and command[1:4] == ['-I', '-S', '-B'], 'planned isolated driver command differs')
        require(not Path(plan['new_output_directory']).exists(), 'the driver requires a fresh output directory')
        record['exact_driver_command'] = command
        record['driver_started'] = True
        save()
        log = HERE / 'R5_V6_LOCAL_DRIVER_V1.log'
        with log.open('xb') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=False)
        record['driver_exit_code'] = result.returncode
        record['driver_log'] = identity(log)
        pipeline_path = Path(plan['new_output_directory']) / 'pipeline.json'
        if pipeline_path.exists():
            pipeline = json.loads(pipeline_path.read_text())
            record['actual_pipeline'] = identity(pipeline_path)
            record['driver_completed'] = pipeline.get('completed', False)
            record['actual_registered_stages'] = [row['label'] for row in pipeline['stages']]
            record['actual_completed_stages'] = [row['label'] for row in pipeline['stages'] if row['completed']]
            record['pipeline_failure'] = pipeline.get('failure')
        record['snapshot_files_unchanged_after_execution'] = all(identity(row['snapshot']['path']) == row['snapshot'] for row in plan['source_snapshots'])
        require(record['snapshot_files_unchanged_after_execution'], 'frozen input changed during execution')
    except BaseException as exc:
        record['launcher_failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        print(json.dumps({key: record.get(key) for key in ('driver_started', 'driver_completed', 'driver_exit_code', 'elapsed_seconds', 'launcher_failure', 'pipeline_failure')}), flush=True)
    return 0 if record['driver_completed'] and record.get('driver_exit_code') == 0 and not record.get('launcher_failure') else 2


if __name__ == '__main__':
    raise SystemExit(main())
