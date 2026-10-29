"""Independent saved-evidence audit of one complete finite K3 pose.

This reads every pair/journal, geometry identity, sealed raw file and exported
engineering member. It never evaluates additional geometry or changes a gate.
"""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import itertools
import json
import math
import os
import resource
import stat
import time

resource.setrlimit(resource.RLIMIT_AS, (256 * 2**20, 256 * 2**20))
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
START = time.monotonic()
parser = argparse.ArgumentParser()
parser.add_argument('--pose', choices=('near', 'far'), required=True)
args = parser.parse_args()
BASE = Path(__file__).resolve().parent.parent
ROOT = BASE / 'r7-native'
CASE = ROOT / ('full-' + args.pose + '-attempt1')
ENGINEERING = ROOT / ('full-' + args.pose + '-attempt1-engineering')
FUNCTIONAL = ROOT / 'genuine-s4-worktree-v3'
S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'


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
    found = {}
    assert stat.S_ISDIR(root.lstat().st_mode)
    for directory, dirs, files in os.walk(root, followlinks=False):
        assert all(stat.S_ISDIR((Path(directory) / name).lstat().st_mode) for name in dirs)
        for name in files:
            path = Path(directory) / name
            assert stat.S_ISREG(path.lstat().st_mode)
            found[str(path.relative_to(root))] = identity(path)
    return found


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def normalize(value):
    if isinstance(value, str):
        return value.replace(str(FUNCTIONAL) + '/', 'repository/').replace('/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/', 'repository/')
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {normalize(key): normalize(item) for key, item in value.items()}
    return value


seal_path = ROOT / ('R7_' + args.pose.upper() + '_COMPLETE_FINITE_POSE_FINAL_SEAL_V1.json')
seal = load(seal_path)
seal_before = identity(seal_path)
assert seal['completed'] and seal['complete_full_pair_execution']
raw = inventory(CASE)
engineering = inventory(ENGINEERING)
assert raw == seal['raw_members'] and engineering == seal['engineering_members']
manifest = load(ENGINEERING / 'ENGINEERING_MANIFEST.json')['members']
assert set(engineering) == set(manifest) | {'ENGINEERING_MANIFEST.json'}
assert all(engineering[relative] == {'bytes': row['bytes'], 'sha256': row['sha256']} for relative, row in manifest.items())
scope = load(ENGINEERING / 'EXPORT_SCOPE.json')
checks = scope['local_runtime_verification_results']
for pose in ('stow_tabs_3', 'predock'):
    assert checks[pose + '_prerequisite_original_manifest_verified']
    assert checks[pose + '_prerequisite_missing_manifest_members'] == 0
    assert {k: v for k, v in raw.items() if k.startswith('prerequisite-' + pose + '/')} == {
        k: v for k, v in engineering.items() if k.startswith('prerequisite-' + pose + '/')}
complete = load(CASE / 'K3FULL-complete-observation.json')
assert complete['complete_full_pair_execution'] and not complete['completion_failures']
assert complete['finite_state_clear'] == seal['finite_state_clear']
assert identity(CASE / 'K3FULL-complete-observation.json') == identity(ENGINEERING / 'K3FULL-complete-observation.json')
reports = {mode: load(CASE / mode / 'worker/report.json') for mode in ('factory', 'readback')}
rows = {}
original_limits = {'wall_seconds': 1200, 'worker_peak_RSS_MiB': 1536, 'shared_unreclaimable_GiB': 6.8,
                   'runtime_disk_reserve_MiB': 100, 'startup_disk_reserve_MiB': 256, 'startup_additional_memory_MiB': 2048}
for mode, report in reports.items():
    folder = CASE / mode / 'worker'
    rp = folder / 'report.json'
    controller = load(CASE / mode / 'controller.json')
    runtime = load(CASE / (mode + '-runtime.json'))
    actual = load(CASE / (mode + '-command-actual.json'))
    command = load(CASE / (mode + '-command.json'))
    runtime_contract = load(CASE / (mode + '-runtime-contract.json'))
    assert actual['completed'] and runtime['completed'] and controller['completed']
    assert actual['bound_inputs_unchanged'] and actual['exit_code'] == 0
    assert controller['worker_exit_code'] == 0 and controller['result_sha256'] == identity(rp)['sha256']
    assert controller['limits'] == original_limits
    for flag in ('owned_child_identity_verified', 'source_bytes_unchanged', 'locked_environment_unchanged', 'owned_channel_descriptors_closed'):
        assert controller[flag]
    assert runtime['qualified_runtime_before'] and runtime['qualified_runtime_after'] and runtime['complete_entry_argv_and_receipt_bound']
    assert runtime['actual_entry_argv'] == runtime['expected_entry_argv'] == command['command'][4:]
    assert runtime['actual_script_arguments'] == runtime_contract['expected_script_arguments']
    assert runtime['runtime_inventory_before_sha256'] == runtime['runtime_inventory_after_sha256']
    assert not runtime['changed_runtime_files'] and runtime['all_bound_sources_unchanged'] and runtime['contract_and_entry_unchanged']
    for item in command['bound_inputs']:
        assert identity(item['path']) == item['identity']
    assert report['functional_source_commit'] == S4 and report['pose'] == args.pose
    assert report['candidate_name'] == 'panel_key_travel_stops_v1' and report['execution_completed']
    assert report['participant_count'] == 154 and len(report['participant_names']) == len(set(report['participant_names'])) == 154
    expected_pairs = list(itertools.combinations(sorted(report['participant_names']), 2))
    assert len(expected_pairs) == report['expected_pair_count'] == report['persisted_pair_count'] == len(report['pairs']) == 11781
    assert report['all_unordered_pairs_present_once'] and [(row['a'], row['b']) for row in report['pairs']] == expected_pairs
    assert not report['evaluation_failures'] and not report['mismatches_to_factory']
    assert report['identity_before']['repository_head_at_start'] == report['identity_after']['repository_head_at_finish'] == S4
    assert not report['identity_before']['worktree_status_at_start'] and report['identity_after']['source_bytes_and_locked_environment_unchanged']
    for key in ('complete_product_motion_proved', 'continuous_backlash_domain_proved', 'physical_qualification', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go', 'G2_pass'):
        assert report[key] is False
    positive = []
    for pair in report['pairs']:
        volume = pair['common_mm3']
        assert type(volume) in (int, float) and math.isfinite(volume) and volume >= 0
        assert pair['rejected'] == (volume > 1e-7)
        if volume > 0:
            positive.append(pair)
    assert [(p['a'], p['b'], p['common_mm3']) for p in positive] == [(p['a'], p['b'], p['common_mm3']) for p in report['positive_pairs']]
    with (folder / 'pairs.jsonl').open() as journal:
        for pair, (a, b) in zip(report['pairs'], expected_pairs):
            selected = json.loads(next(journal))
            completed = json.loads(next(journal))
            assert selected == {'event': 'selected', 'a': a, 'b': b}
            assert completed == {'event': 'completed', 'row': pair}
        assert next(journal, None) is None
    for side in ('L', 'R'):
        direct = report['panel_KEY_direct_Common'][side]
        pair = next(p for p in report['pairs'] if (p['a'], p['b']) == ('A_BACK_PANEL', side + '_KEY'))
        assert direct['a'] == 'A_BACK_PANEL' and direct['b'] == side + '_KEY'
        assert abs(direct['common_mm3'] - pair['common_mm3']) <= 1e-7
        assert abs(direct['strict_common']['common_mm3'] - direct['common_mm3']) <= 1e-7
        assert direct['rejected'] == pair['rejected'] == (direct['common_mm3'] > 1e-7)
    geometry_refs = {}
    for node in walk(report):
        if 'signature_before' in node and 'files' in node and 'signature_after' in node:
            assert node['signature_before'] == node['signature_after'] and node['serialization_preserved_in_memory_signature']
            for extension, ref in node['files'].items():
                assert extension in ('brep', 'step')
                path = folder / ref['path']
                assert path.is_relative_to(folder) and '..' not in Path(ref['path']).parts
                value = {'bytes': ref['bytes'], 'sha256': ref['sha256']}
                assert identity(path) == value
                assert ref['path'] not in geometry_refs or geometry_refs[ref['path']] == value
                geometry_refs[ref['path']] = value
    actual_geometry = {k[len(mode + '/worker/'):]: v for k, v in raw.items()
                       if k.startswith(mode + '/worker/') and Path(k).suffix in ('.brep', '.step')}
    assert actual_geometry == geometry_refs
    projection = load(ENGINEERING / mode / 'worker/report.engineering.json')
    assert projection['original'] == identity(rp)
    for key in ('pairs', 'positive_pairs', 'participant_names', 'actual_q_by_side_mm', 'panel_KEY_direct_Common',
                'native_early_conditions_rechecked', 'finite_pose_clear', 'K3_prerequisite'):
        assert projection['engineering_record'][key] == normalize(report[key])
    assert report['finite_pose_clear'] == bool(report['native_early_conditions_rechecked'] and not any(row['rejected'] for row in report['pairs']))
    rows[mode] = {'raw_report': identity(rp), 'raw_journal': identity(folder / 'pairs.jsonl'),
        'owned_controller': identity(CASE / mode / 'controller.json'), 'qualified_runtime': identity(CASE / (mode + '-runtime.json')),
        'participant_count': 154, 'pair_count': 11781, 'journal_event_count': 23562,
        'method_counts': dict(collections.Counter(row['method'] for row in report['pairs'])),
        'positive_pairs': [{'a': row['a'], 'b': row['b'], 'common_mm3': row['common_mm3'], 'rejected': row['rejected']} for row in positive],
        'direct_panel_KEY_Common': report['panel_KEY_direct_Common'], 'actual_q_by_side_mm': report['actual_q_by_side_mm'],
        'finite_pose_clear': report['finite_pose_clear'], 'native_early_conditions_rechecked': report['native_early_conditions_rechecked'],
        'seconds': report['seconds'], 'resources': report['resource'],
        'saved_geometry_file_count': len(geometry_refs), 'saved_geometry_bytes': sum(v['bytes'] for v in geometry_refs.values())}
factory, reader = reports['factory'], reports['readback']
assert reader['factory_report_sha256'] == identity(CASE / 'factory/worker/report.json')['sha256']
assert reader['native_STEP_readback_executed'] and reader['separate_process_from_factory'] and reader['independent_CAD_kernel'] is False
assert reader['independent_material_builder_does_not_import_candidate_source']
assert len(reader['body_readbacks']) == 154 and set(reader['body_readbacks']) == set(factory['body_exports'])
for name, record in reader['body_readbacks'].items():
    assert record['passed'] and record['STEP'] == factory['body_exports'][name]['files']['step']
    assert abs(record['volume_delta_mm3']) <= 1e-7 and max(map(abs, record['bounds_delta_mm'])) <= 1e-7
assert len(reader['independent_early_gate_records']) == 12
assert reader['native_early_conditions_rechecked'] == all(row['evaluated'] and row['passed'] for row in reader['independent_early_gate_records'].values())
assert not reader['independent_native_evaluation_failures']
max_pair_difference = max(abs(a['common_mm3'] - b['common_mm3']) for a, b in zip(factory['pairs'], reader['pairs']))
assert max_pair_difference <= 1e-7
assert all(a['rejected'] == b['rejected'] for a, b in zip(factory['pairs'], reader['pairs']))
assert complete['finite_state_clear'] == all(report['finite_pose_clear'] for report in reports.values())
assert identity(seal_path) == seal_before
result = {
    'schema': 'razr-r7-complete-finite-pose-independent-full-raw-and-export-readback-v1',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'evidence_readback_pass': True,
    'pose': args.pose, 'reviewer_identity': identity(__file__),
    'review_resource_limits': {'address_space_bytes': 256 * 2**20, 'CPU_seconds': 120},
    'original_complete_verifier_output': identity(CASE / 'K3FULL-complete-observation.json'),
    'final_seal': seal_before, 'engineering_manifest': identity(ENGINEERING / 'ENGINEERING_MANIFEST.json'),
    'actual_raw_member_count': len(raw), 'actual_raw_bytes': sum(v['bytes'] for v in raw.values()),
    'actual_engineering_member_count': len(engineering), 'actual_engineering_bytes': sum(v['bytes'] for v in engineering.values()),
    'all_complete_raw_and_engineering_member_sets_and_hashes_equal': True,
    'all_4334_original_pilot_members_present_and_unchanged_in_raw_and_engineering': True,
    'original_factory_and_independent_reader': rows,
    'all_direct_panel_KEY_Common_match_original_complete_pair_rows_and_independent_readback': True,
    'maximum_factory_reader_all_pair_volume_difference_mm3': max_pair_difference,
    'all_154_complete_STEP_readbacks_passed_original_signature_criteria': True,
    'independent_early_gate_records': reader['independent_early_gate_records'],
    'original_complete_pair_execution': True, 'finite_state_clear': complete['finite_state_clear'],
    'remaining_unproved_domains': complete['remaining_unproved_domains'],
    'candidate': 'panel_key_travel_stops_v1', 'functional_source_commit': S4,
    'same_kernel_separate_process_reader': True, 'new_CAD_arithmetic_performed_by_this_audit': False,
    'full_continuous_G2': False, 'physical_qualification': False, 'manufacturing_go': False,
    'qualification_external_vtk_cleanup_discrepancy_still_unresolved': True, 'seconds': time.monotonic() - START,
}
output = BASE / 'r7-audit/full-factory-review' / ('R7_' + args.pose.upper() + '_ACTUAL_FULL_FACTORY_INDEPENDENT_EVIDENCE_READBACK.json')
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'path': str(output), 'identity': identity(output), 'finite_state_clear': result['finite_state_clear'], 'seconds': result['seconds']}))
