"""Bounded independent full-source and original prerequisite readback, no CAD."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import os
import resource
import stat
import time

resource.setrlimit(resource.RLIMIT_AS, (256 * 2**20, 256 * 2**20))
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
START = time.monotonic()
BASE = Path(__file__).resolve().parent.parent
ROOT = BASE / 'r7-native'
K3 = BASE / 'r7-recovery/k3'
DRIVERS = K3 / 'source/k3full'


def identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            digest.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def load(path):
    return json.loads(Path(path).read_text())


def inventory(root):
    assert stat.S_ISDIR(root.lstat().st_mode)
    found = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        assert all(stat.S_ISDIR((Path(directory) / name).lstat().st_mode) for name in dirs)
        for name in files:
            path = Path(directory) / name
            assert stat.S_ISREG(path.lstat().st_mode), str(path)
            found[str(path.relative_to(root))] = identity(path)
    return found


source_files = [ROOT / 'register_full_factory_local_r7_v3.py',
                ROOT / 'register_full_case_closeout_r7_v1.py',
                ROOT / 'prepare_full_case_evidence_r7_v1.py',
                ROOT / 'register_and_run_native_local_r7_v4.py',
                ROOT / 'R7_FULL_FACTORY_INPUTS_ACTUAL_READBACK_V1.json',
                K3 / 'K3FULL-driver-source.json']
before = {str(path): identity(path) for path in source_files}
receipt = load(source_files[4])
drivers = inventory(DRIVERS)
assert len(drivers) == 16 and drivers == receipt['original_drivers'] == load(K3 / 'K3FULL-driver-source.json')
assert drivers['supervise_k3full.py']['sha256'] == 'e546a2919ed276331be89ea137de5e8b2121dece92604ea38b80486b3f7d32de'
assert drivers['verify_k3full_complete.py']['sha256'] == 'ce0fbab7c1e5c7d9663bd62d6dcab9ace32ab84f6bba91a495b745ade0daab3d'
assert drivers['export_k3full_engineering.py']['sha256'] == '7a6f42eb5fefb8d12d395de47f31a8780b36212cf4ac9b2151fda50862f43116'
binding = load(DRIVERS / 'K3FULL_K3_BINDING.json')
pose_rows = {}
for pose in ('stow_tabs_3', 'predock'):
    folder = K3 / ('prerequisite-' + pose)
    found = inventory(folder)
    record = receipt['poses'][pose]
    manifest_path = folder / 'ENGINEERING_MANIFEST.json'
    manifest = load(manifest_path)['members']
    assert set(found) == set(manifest) | {'ENGINEERING_MANIFEST.json'}
    for relative, entry in manifest.items():
        assert found[relative] == {'bytes': entry['bytes'], 'sha256': entry['sha256']}
    assert found == record['members']
    assert len(found) == record['actual_regular_files'] == 2167
    assert sum(v['bytes'] for v in found.values()) == record['actual_bytes']
    assert identity(manifest_path) == record['manifest_identity']
    assert identity(manifest_path)['sha256'] == binding['poses'][pose]['engineering_manifest_sha256']
    prior = load(folder / 'K3-pilot-observation.json')
    assert prior['complete_scientific_pilot_execution'] and prior['actual_finite_pilot_clear'] and not prior['completion_failures']
    assert prior['full_pair_matrix_executed'] is False and prior['full_ten_state_campaign_authorized'] is False
    for mode in ('factory', 'readback'):
        original = prior['results'][mode]
        projected = load(folder / mode / 'worker/report.engineering.json')
        assert projected['original']['sha256'] == original['original_report_sha256']
        assert projected['engineering_record']['execution_completed'] and projected['engineering_record']['pilot_clear']
    pose_rows[pose] = {'actual_member_count': len(found), 'actual_bytes': sum(v['bytes'] for v in found.values()),
                       'original_manifest': identity(manifest_path), 'complete_set_and_all_bytes_verified': True,
                       'historical_pilot_completed_clear': True, 'historical_full_pair_claim': False}
assert sum(v['actual_member_count'] for v in pose_rows.values()) == receipt['total_prerequisite_regular_files'] == 4334
assert sum(v['actual_bytes'] for v in pose_rows.values()) == receipt['total_prerequisite_bytes'] == 408408534
states = ast.parse((DRIVERS / 'full_stop_states.py').read_text())
state_assign = next(n for n in states.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STATES' for t in n.targets))
declared = ast.literal_eval(state_assign.value)
for pose in ('near', 'far'):
    assert declared[pose]['expected_bodies'] == 154
    assert declared[pose]['left_tab'] == declared[pose]['right_tab'] == 3.0
    assert declared[pose]['key_offsets'] == [0.0, 0.0]
assert declared['near']['slide'] == 23.142044210239405
assert declared['far']['slide'] == 60.880681403413135
assert all(identity(path) == expected for path, expected in before.items())
result = {
    'schema': 'razr-r7-original-full-factory-local-source-and-input-independent-review-v1',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_and_input_review_pass': True, 'reviewer_identity': identity(__file__),
    'review_resource_limits': {'address_space_bytes': 256 * 2**20, 'CPU_seconds': 120},
    'bound_new_source_and_recovery_record_identities_before_and_after': before,
    'all_16_original_driver_identities': drivers, 'complete_original_prerequisites': pose_rows,
    'near_and_far_original_declared_states': {pose: declared[pose] for pose in ('near', 'far')},
    'expected_unordered_pairs_per_worker': 154 * 153 // 2,
    'original_supervisor_and_6_resource_gates_unchanged': True,
    'original_factory_reader_algorithms_and_1e_minus_7_volume_criterion_unchanged': True,
    'new_registrar_uses_actual_clean_S4_and_qualified_runtime_and_original_core_reader_seal': True,
    'GITHUB_WORKSPACE_used_only_as_actual_functional_path': True, 'hosted_identity_claimed': False,
    'copy_helper_static_review': {'copies_both_complete_original_pilots': True, 'copies_all_16_original_drivers': True,
        'source_and_destination_hash_checks': True, 'fresh_destination_no_overwrite': True,
        'copy_ceiling_bytes': 420000000, 'wall_seconds': 60, 'peak_RSS_bytes': 268435456,
        'original_extra_disk_reserve_bytes': 1536 * 2**20,
        'budget_checks_are_sampled_and_end_of_copy_checks_not_asynchronous_hard_kills': True},
    'closeout_wrapper_static_review': {'unchanged_original_complete_verifier_then_original_exporter': True,
        'qualification_entry_and_original_owned_native_supervisor_retained': True,
        'complete_original_engineering_manifest_readback_and_strict_final_raw_seal': True,
        'finite_clear_failure_separately_retained_from_complete_execution': True,
        'current_copy_originals_separate_from_new_64MiB_core_campaign': True},
    'actual_CAD_executed_by_this_review': False,
    'full_native_execution_not_yet_admitted_by_this_source_review': True,
    'qualification_transient_cleanup_current_state_discrepancy_under_separate_review': True,
    'original_concrete_command_and_original_actual_runtime_gates_still_required': True,
    'full_continuous_G2': False, 'physical_qualification': False,
    'seconds': time.monotonic() - START,
}
output = BASE / 'r7-audit/full-factory-review/R7_FULL_FACTORY_SOURCE_AND_COMPLETE_INPUTS_INDEPENDENT_REVIEW.json'
output.parent.mkdir(parents=True, exist_ok=True)
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'path': str(output), 'identity': identity(output), 'seconds': result['seconds']}))
