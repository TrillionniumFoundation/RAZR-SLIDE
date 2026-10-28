"""Freeze an unchanged original factory replay and observe its actual startup gate.

This preparation never manufactures S4 Git identity or a virtual environment.
The original K3 supervisor is invoked only while its live startup preview is
refused. A completed historical archive audit makes a duplicate native run
unnecessary; the commands remain explicit for a future material change.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time


def ident(path):
    with Path(path).open('rb') as stream:
        return {'bytes': Path(path).stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def observe(path):
    stat = os.statvfs(path)
    m = {k: int(v) for k, v in (line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())}
    amount = m['anon'] + m['shmem'] + max(m['kernel'] - m['slab_reclaimable'], 0) + m.get('unevictable', 0)
    available = stat.f_bavail * stat.f_frsize
    return {'ordinary_available_disk_bytes': available, 'all_free_blocks_bytes': stat.f_bfree * stat.f_frsize,
            'shared_unreclaimable_bytes': amount, 'original_disk_startup_pass': available >= 268435456,
            'original_memory_startup_pass': amount + 2147483648 <= 6.8 * 2**30}


def main():
    root = Path(__file__).resolve().parents[1]
    work = root / 'r5-native'
    source = root / 'recovered-inputs/RAZR-F1a-R2-near-fresh-native-complete-raw-evidence-20261027/functional-source'
    drivers = root / 'r4-native/recovered/k3full-original/source/k3full'
    originals = root / 'recovered-inputs/K3FULL-open_installed-original'
    supervisor = drivers / 'supervise_k3full.py'
    start = time.monotonic()
    report = {'schema': 'razr-r5-original-current-factory-replay-preparation-v1',
              'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'preparer': ident(__file__),
              'original_supervisor': {'path': str(supervisor), **ident(supervisor)},
              'original_source_bytes_changed': False, 'native_started': False,
              'historical_originals_recovery_replaces_redundant_finite_rerun': True,
              'new_geometry_or_continuous_qualification': False,
              'R4_qualified_runtime_used_for_CAD': False,
              'readonly_supervisor_startup_path_does_not_import_CAD': True,
              'original_six_CAD_limits': {'wall_seconds': 1200, 'worker_RSS_limit_bytes': 1610612736,
                  'shared_limit_bytes': 6.8 * 2**30, 'startup_disk_floor_bytes': 268435456,
                  'startup_extra_shared_bytes': 2147483648, 'runtime_disk_floor_bytes': 104857600},
              'capacity_basis_from_recovered_actual_K3': {
                  'near_factory_seconds': 278.12116997699997, 'near_reader_seconds': 191.78153347900002,
                  'near_factory_peak_RSS_bytes': 573534208, 'near_reader_peak_RSS_bytes': 563171328,
                  'bodies_per_pose': 154, 'unordered_pairs_per_worker': 11781,
                  'future_heavy_native_jobs_concurrent': 1,
                  'fresh_single_pose_output_reservation_bytes': 64 * 2**20},
              'future_commands': [], 'issues': []}
    source_manifest = {str(p.relative_to(source)): ident(p) for p in sorted(source.rglob('*')) if p.is_file()}
    path = work / 'R5_RECOVERED_FUNCTIONAL_SOURCE_MANIFEST.json'
    path.write_text(json.dumps({'schema':'razr-r5-recovered-functional-bytes-v1', 'source_root':str(source),
        'source_reference':'RAZR-F1a-R2-near-fresh-native-complete-raw-evidence-20261027.tar.gz',
        'Git_S4_checkout_claimed':False, 'members':source_manifest}, indent=2) + '\n')
    report['source_snapshot'] = {'path':str(path), 'identity':ident(path), 'file_count':len(source_manifest),
                                'total_bytes':sum(x['bytes'] for x in source_manifest.values())}
    report['original_driver_files'] = {str(p): ident(p) for p in sorted(drivers.iterdir()) if p.is_file()}
    env = dict(os.environ)
    for key in ('GIT_DIR','GIT_WORK_TREE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(key, None)
    env.update(GITHUB_WORKSPACE=str(source), PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    proc = subprocess.run(['git','-C',str(source),'rev-parse','--show-toplevel','HEAD'],
                          capture_output=True, text=True, env=env, check=False)
    report['actual_Git_source_readiness'] = {'exit_code':proc.returncode, 'stdout':proc.stdout,
        'stderr':proc.stderr, 'required_root':str(source),
        'required_commit':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
        'exact_original_checkout_ready':proc.returncode == 0 and proc.stdout.splitlines() == [str(source),'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560']}
    report['original_venv_entry_exists'] = (source/'.venv/bin/python').is_file()
    for pose in ('near','far'):
        for mode in ('factory','readback'):
            out = work/'prepared-replay'/pose/mode
            command = [sys.executable, '-B', str(supervisor), '--mode', mode, '--pose', pose,
                '--output', str(out), '--k3-stow', str(originals/'prerequisite-stow_tabs_3'),
                '--k3-predock', str(originals/'prerequisite-predock'),
                '--binding', str(drivers/'K3FULL_K3_BINDING.json'),
                '--key-binding', str(drivers/'K3FULL_K1_BINDING.json'),
                '--contract', str(drivers/'PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'),
                '--k1-contract', str(drivers/'KEY_FORWARD_LOOP_V1_CONTRACT.json')]
            if mode == 'readback':
                command += ['--report',str(work/'prepared-replay'/pose/'factory/worker/report.json')]
            report['future_commands'].append({'pose':pose,'mode':mode,'command':command,
                'GITHUB_WORKSPACE':str(source), 'executed':False,
                'actual_original_Git_checkout_and_original_43_runtime_entry_required':True})
    report['resource_preview'] = observe(work)
    contract_path = work/'R5_CURRENT_FACTORY_REPLAY_PREPARATION.json'
    def save():
        report['elapsed_seconds'] = time.monotonic() - start
        contract_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    save()
    if not report['resource_preview']['original_disk_startup_pass'] or not report['resource_preview']['original_memory_startup_pass']:
        command = list(report['future_commands'][0]['command'])
        command[command.index('--output')+1] = str(work/'original-supervisor-actual-refusal')
        with (work/'original-supervisor-startup.stdout').open('xb') as stdout, (work/'original-supervisor-startup.stderr').open('xb') as stderr:
            actual = subprocess.run(command, env=env, stdout=stdout, stderr=stderr, check=False)
        receipt = work/'original-supervisor-actual-refusal/controller.json'
        report['actual_supervisor_command'] = command
        report['actual_supervisor_exit_code'] = actual.returncode
        if receipt.exists():
            record = json.loads(receipt.read_text())
            report['actual_original_supervisor_receipt'] = {'path':str(receipt), 'identity':ident(receipt)}
            report['original_startup_refusal_observed'] = actual.returncode == 3 and record.get('resource_start_refused') is True
            report['native_started'] = record.get('worker_started') is True
            report['original_supervisor_recorded_limits'] = record['limits']
            report['original_supervisor_recorded_observations'] = record['resource_observations']
        else:
            report['issues'].append('Original supervisor did not create a receipt')
    else:
        report['resource_refusal_run_skipped_because_original_capacity_now_passes'] = True
    report['all_original_driver_bytes_unchanged'] = all(ident(p) == v for p,v in report['original_driver_files'].items())
    report['all_recovered_source_bytes_unchanged'] = all(ident(source/p) == v for p,v in source_manifest.items())
    report['completed_preparation_only'] = not report['issues'] and not report['native_started'] and report['all_original_driver_bytes_unchanged'] and report['all_recovered_source_bytes_unchanged']
    save()
    print(json.dumps({k:report.get(k) for k in ('completed_preparation_only','original_startup_refusal_observed','native_started','elapsed_seconds','issues')}))
    return 0 if report['completed_preparation_only'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
