"""Freeze byte-identical local V6 inputs and an execution plan, without math."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'r5-local-v6'
SNAPSHOT = HERE / 'input-snapshot-v1'
SOURCE = ROOT / 'r5-envelope'
R4 = ROOT / 'razr-current/engineering/engineering-followup-20261027-r4/envelope'
V5 = ROOT / 'r5-ci-results/run-40645988108'
LOCK_SHA = '5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499'
started = time.monotonic()


def ident(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest}


def equal(actual, wanted):
    return all(actual[k] == wanted[k] for k in ('bytes', 'sha256'))


def snapshot(root, records, name):
    assert len(records) == len({r['path'] for r in records}), 'Duplicate source path'
    result = []
    for record in records:
        old = (root / record['path']).resolve()
        assert old.is_relative_to(root.resolve()) and not old.is_symlink()
        before = ident(old)
        assert equal(before, record), 'Original differs: ' + str(old)
        new = SNAPSHOT / name / record['path']
        new.parent.mkdir(parents=True, exist_ok=True)
        assert not new.exists(), 'Do not overwrite an existing frozen input'
        shutil.copyfile(old, new)
        os.chmod(new, 0o444)
        copied = ident(new)
        after = ident(old)
        assert equal(copied, record) and before == after
        result.append({'source': before, 'snapshot': copied, 'mode': '0444', 'original_bytes_changed': False})
    return result


assert sys.flags.isolated and sys.flags.no_site and not sys.flags.optimize
assert not SNAPSHOT.exists(), 'A prior snapshot must remain immutable'
lock_path = SOURCE / 'R5E_PORTABLE_SOURCE_LOCK_V6.json'
lock_identity = ident(lock_path)
assert lock_identity['sha256'] == LOCK_SHA
lock = json.loads(lock_path.read_text())
assert len(lock['r5_files']) == 25 and len(lock['r4_source_files']) == 3
bridge = json.loads((SOURCE / 'R5E_PUBLIC_INPUT_BRIDGE.json').read_text())
actual_bridge = json.loads((SOURCE / 'R5E_V6_BASE_V5_INPUT_BRIDGE.json').read_text())
assert len(bridge['files']) == 19 and len(actual_bridge['files']) == 25
r4_records = lock['r4_source_files'] + [dict(r['public_identity'], path=r['path']) for r in bridge['files']]
r4_unique = {}
for item in r4_records:
    if item['path'] in r4_unique:
        assert equal(item, r4_unique[item['path']])
    r4_unique[item['path']] = item
source_records = lock['r5_files'] + [dict(lock_identity, path=lock_path.name)]
rows = snapshot(SOURCE, source_records, 'source')
rows += snapshot(R4, list(r4_unique.values()), 'r4')
rows += snapshot(V5, actual_bridge['files'], 'base-v5')
assert all(ident(row['source']['path']) == row['source'] and ident(row['snapshot']['path']) == row['snapshot'] for row in rows)
memory = {k: int(v) for k, v in (line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())}
disk = os.statvfs(HERE)
unreclaimable = memory['anon'] + memory['shmem'] + max(memory['kernel'] - memory['slab_reclaimable'], 0) + memory.get('unevictable', 0)
available = disk.f_bavail * disk.f_frsize
command = [sys.executable, '-I', '-S', '-B', str(SNAPSHOT / 'source/run_portable_primitive_r5e_v6.py'),
           '--r4-root', str(SNAPSHOT / 'r4'), '--base-v5-root', str(SNAPSHOT / 'base-v5'),
           '--output', str(HERE / 'attempt-1')]
record = {
    'schema': 'r5-v6-local-execution-readiness-v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
    'source_lock_sha256_literal': LOCK_SHA, 'source_lock': lock_identity,
    'preparation_source': ident(__file__), 'source_snapshots': rows,
    'source_R5_count_including_lock': len(source_records), 'R4_files_count': len(r4_unique), 'actual_V5_files_count': len(actual_bridge['files']),
    'snapshot_bytes': sum(r['snapshot']['bytes'] for r in rows),
    'python': {'version': sys.version, 'executable': ident(sys.executable), 'flags': {'isolated': sys.flags.isolated, 'no_site': sys.flags.no_site, 'optimize': sys.flags.optimize}},
    'exact_driver_command': command, 'new_output_directory': str(HERE / 'attempt-1'),
    'resource_snapshot': {'disk_available_bytes': available, 'shared_unreclaimable_bytes': unreclaimable,
                          'startup_disk_required_bytes': 150994944, 'worker_RSS_limit_bytes': 805306368,
                          'shared_ceiling_bytes': 7301444403, 'shared_plus_worker_limit_bytes': unreclaimable + 805306368,
                          'instant_snapshot_admits_original_limits': available >= 150994944 and unreclaimable + 805306368 <= 7301444403},
    'original_limits_per_stage': {'wall_seconds': 600, 'RSS_limit_bytes': 805306368, 'shared_ceiling_bytes': 7301444403,
                                  'disk_floor_bytes': 104857600, 'maximum_output_bytes': 41943040, 'metadata_margin_bytes': 4194304},
    'stage_order': ['single-primitive-support-leaf', 'verify-single', 'preflight-primitive-support', 'all-primitive-support-frames', 'verify-all'],
    'whole_pipeline_worker_wall_bound_seconds': 3000,
    'resource_snapshot_is_not_actual_supervisor_admission': True,
    'actual_owned_supervisor_must_admit_each_stage': True,
    'formal_execution_waits_for_final_independent_static_review': True,
    'formal_worker_executions_so_far': 0, 'V6_mathematical_controls_executed_here': 0,
    'actual_output_and_failures_preserved': True,
    'native_geometry_executed': False, 'original_reports_or_certificates_edited': False,
    'conditional_primitive_support_model_only': True, 'native_primitive_semantics_verified': False,
    'native_trim_class_membership_verified': False, 'original_raw_gate_reclassified': False, 'full_continuous_G2': False,
    'elapsed_seconds': time.monotonic() - started, 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
}
target = HERE / 'R5_V6_LOCAL_EXECUTION_READINESS.json'
assert not target.exists()
target.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({k: record[k] for k in ('source_R5_count_including_lock', 'R4_files_count', 'actual_V5_files_count', 'snapshot_bytes', 'resource_snapshot', 'elapsed_seconds', 'peak_RSS_bytes')}))
