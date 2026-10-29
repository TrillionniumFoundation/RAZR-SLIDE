"""Audit saved original native producer/reader results; no CAD recomputation."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import math
import os
import resource
import stat
import time

resource.setrlimit(resource.RLIMIT_AS, (256 * 2**20, 256 * 2**20))
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
START = time.monotonic()
BASE = Path(__file__).resolve().parent.parent
ROOT = BASE / 'r7-native'
CASE = ROOT / 'native80-attempt1'
PRODUCER = CASE / 'core-producer-owned/worker'
READER = CASE / 'core-reader-owned/worker'
P_REPORT = PRODUCER / 'R5_NATIVE_TRIM_CORE_WITNESS.json'
R_REPORT = READER / 'R5_NATIVE_TRIM_CORE_READBACK.json'


def identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            digest.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def load(path):
    return json.loads(Path(path).read_text())


def walk(value, location=''):
    if isinstance(value, dict):
        yield location, value
        for key, item in value.items():
            yield from walk(item, location + '/' + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, location + '/' + str(index))


def empty(native):
    assert native['valid'] and not native['is_null']
    assert native['classification'] == 'topologically_empty'
    assert all(count == 0 for count in native['counts'].values())
    assert native['native_area_mm2'] == 0.0
    assert native['zero_3D_volume_used_as_face_emptiness'] is False


p, r = load(P_REPORT), load(R_REPORT)
pc, rc = load(CASE / 'core-producer-science-contract.json'), load(CASE / 'core-reader-science-contract.json')
assert p['completed'] and r['completed'] and not p['issues'] and not r['issues']
assert p['contract_identity'] == identity(CASE / 'core-producer-science-contract.json')
assert r['contract_identity'] == identity(CASE / 'core-reader-science-contract.json')
assert r['producer_report_identity'] == identity(P_REPORT)
assert p['selection_identity'] == pc['selection']['identity'] and p['mapping_identity'] == pc['mapping']['identity']
for binding in pc['bound_sources'] + pc['bound_records']:
    assert identity(binding['path']) == binding['identity']
assert p['worker_identity']['sha256'] == 'b1c1c90f44a74a06d6b19350536b5dd5bf6d47ed77a2ee41247f7fc6e49bd1a8'
assert r['reader_identity']['sha256'] == 'dd054cdabd3c1f0a6aa6ff1649127036f2c614edb5f8c5e766f02ebcb4a06891'
assert r['separate_native_process'] and not r['producer_module_imported'] and not r['independent_CAD_kernel']
assert p['scope'] == r['scope'] == pc['scope'] == rc['scope']
assert len(p['whole_inputs']) == 6 and len(p['native_face_bindings']) == 40
for face in p['native_face_bindings']:
    assert face['source_face_canonical_sha256'] == face['fresh_face_canonical_sha256']
    assert face['boundary_parameters_and_topology_equal'] and face['native_area_binary64_equal']
    assert face['original_native_area']['hex'] == face['fresh_native_area']['hex']
assert len(p['original_core_intersections']) == len(r['original_core_readbacks']) == 80
ids = [row['witness_id'] for row in p['original_core_intersections']]
assert len(set(ids)) == 80 and ids == [row['witness_id'] for row in r['original_core_readbacks']]
for row in p['original_core_intersections']:
    assert row['failure'] is None and row['topological_empty_observed'] and row['absence_of_positive_face_area_observed']
    assert row['patch']['native']['classification'] == 'positive_face_area'
    empty(row['actual_common']['native'])
for row in r['original_core_readbacks']:
    empty(row['common']['native'])
assert len(p['native_controls']) == len(r['control_readbacks']) == 8
control_counts = collections.Counter(row['kind'] for row in p['native_controls'])
for left, right in zip(p['native_controls'], r['control_readbacks']):
    assert (left['material_key'], left['kind']) == (right['material_key'], right['kind'])
    assert left['expected_class_observed']
    assert left['common']['native']['classification'] == right['common']['native']['classification']
assert len(p['material_mapping']) == len(r['material_mapping_readbacks']) == 4
for left, right in zip(p['material_mapping'], r['material_mapping_readbacks']):
    assert left['material_key'] == right['material_key'] and left['finite_native_material_and_pose_gate_passed'] and right['finite_gate_passed']
    for node in (left['mapped_minus_K3_original'], left['K3_original_minus_mapped'], right['first_difference'], right['second_difference']):
        empty(node['native'])
        assert node['native']['original_whole_material_guard']['passed']
assert p['current_K3_native_identity_gate_passed'] and not p['current_K3_candidate_geometry_changed']
assert p['current_added_material_account']['original_native_material_account_gate_passed']
empty(p['current_added_material_account']['original_minus_current']['native'])
empty(r['current_added_material_account']['removed']['native'])
added = p['current_added_material_account']['current_minus_original']['native']['original_whole_material_guard']['signed_volume_mm3']
assert added == r['current_added_material_account']['added']['native']['original_whole_material_guard']['signed_volume_mm3']
assert added == p['current_added_material_account']['original_saved_account']['added_mm3']
assert len(p['current_added_core_intersections']) == len(r['current_added_core_readbacks']) == 80
assert ids == [row['witness_id'] for row in p['current_added_core_intersections']] == [row['witness_id'] for row in r['current_added_core_readbacks']]
for left, right in zip(p['current_added_core_intersections'], r['current_added_core_readbacks']):
    assert left['executed'] and right['executed'] and left['failure'] is None
    assert left['added_material_topologically_absent_on_native_patch'] and left['whole_current_native_trim_model_membership_proved'] is False
    empty(left['actual_added_material_common']['native']); empty(right['added_common']['native'])

geometry_files = {}
for name, root, report in (('producer', PRODUCER, p), ('reader', READER, r)):
    exported = {}
    for location, node in walk(report):
        if {'path', 'bytes', 'sha256'} <= set(node) and node['path'].endswith('.brep'):
            assert not Path(node['path']).is_absolute() and '..' not in Path(node['path']).parts
            expected = {key: node[key] for key in ('bytes', 'sha256')}
            assert node['path'] not in exported or exported[node['path']] == expected
            assert identity(root / node['path']) == expected
            exported[node['path']] = expected
    actual = {}
    for directory, dirs, files in os.walk(root / 'geometry', followlinks=False):
        assert all(stat.S_ISDIR((Path(directory) / item).lstat().st_mode) for item in dirs)
        for item in files:
            path = Path(directory) / item
            assert stat.S_ISREG(path.lstat().st_mode)
            actual[str(path.relative_to(root))] = identity(path)
    assert actual == exported
    geometry_files[name] = {'count': len(actual), 'bytes': sum(v['bytes'] for v in actual.values()), 'members': actual}
assert len(r['saved_BREP_readbacks']) == len(geometry_files['producer']['members']) == 396
assert {row['path']: row['identity'] for row in r['saved_BREP_readbacks']} == geometry_files['producer']['members']
comparisons = [{'location': location, **node} for location, node in walk(r) if 'topology_and_classification_equal' in node]
assert len(comparisons) == r['native_area_comparisons']['count'] == 728
assert all(row['topology_and_classification_equal'] for row in comparisons)
assert all(math.isfinite(row['area_difference_mm2']) for row in comparisons)
area_differences = [row for row in comparisons if not row['area_binary64_equal']]
assert bool(not area_differences) == r['native_area_comparisons']['all_binary64_equal']
assert max(abs(row['area_difference_mm2']) for row in comparisons) == r['native_area_comparisons']['maximum_absolute_difference_mm2']
assert r['native_area_comparisons']['new_physical_area_threshold_introduced'] is False

stages = {}
for phase, report in (('core-producer', p), ('core-reader', r)):
    command = load(CASE / (phase + '-command.json'))
    actual = load(CASE / (phase + '-command-actual.json'))
    controller = load(CASE / (phase + '-owned/controller.json'))
    runtime = load(CASE / (phase + '-runtime.json'))
    runtime_contract = load(CASE / (phase + '-runtime-contract.json'))
    assert all(value['completed'] for value in (actual, controller, runtime))
    assert actual['inputs_unchanged'] and actual['actual_supervisor_and_worker_arguments_bound']
    assert controller['command'] == command['worker_command'] == command['command'][7:]
    assert controller['resource_stop'] is None and controller['exit_code'] == 0
    assert controller['limits'] == command['original_six_resource_limits'] == runtime_contract['native_original_six_limits']
    assert runtime['complete_entry_argv_and_receipt_bound'] and runtime['actual_entry_argv'] == runtime['expected_entry_argv']
    assert runtime['qualified_runtime_before'] and runtime['qualified_runtime_after'] and not runtime['issues']
    assert runtime['runtime_inventory_before_sha256'] == runtime['runtime_inventory_after_sha256']
    assert not runtime['changed_runtime_files'] and runtime['all_bound_sources_unchanged'] and runtime['contract_and_entry_unchanged']
    assert not runtime['historical_runtime_qualification_reused'] and not runtime['native_gate_numbers_changed']
    for binding in command['bound_inputs']:
        assert identity(binding['path']) == binding['identity']
    limits = controller['limits']
    assert controller['seconds'] <= limits['wall_seconds'] and report['peak_RSS_bytes'] <= limits['worker_RSS_limit_bytes']
    stages[phase] = {'report': identity(P_REPORT if phase == 'core-producer' else R_REPORT),
        'controller': identity(CASE / (phase + '-owned/controller.json')), 'runtime': identity(CASE / (phase + '-runtime.json')),
        'worker_seconds': report['seconds'], 'worker_peak_RSS_bytes': report['peak_RSS_bytes'],
        'original_controller_seconds': controller['seconds'], 'original_resource_sample_count': len(controller['samples']),
        'original_observed_zero_RSS_sample_count': sum(row.get('worker_RSS_bytes') == 0 for row in controller['samples']),
        'zero_RSS_records_preserved_not_used_as_peak_or_new_completion_evidence': True,
        'original_supervisor_resource_stop': controller['resource_stop']}
for report in (p, r):
    for key in ('native_exact_membership_verified', 'full_continuous_G2', 'physical_qualification'):
        assert report[key] is False
assert p['original_V5_raw_result_reclassified'] is False and p['sources_and_records_unchanged'] and p['runtime_versions_unchanged']
assert r['sources_and_original_inputs_unchanged'] and r['producer_report_and_contract_unchanged'] and r['runtime_versions_unchanged']
seal_path = CASE / 'core-reader-seal.json'
seal = load(seal_path)
assert seal['completed_scientific_stage'] and seal['scientific_raw_bytes_including_current_inputs'] <= seal['registered_scientific_output_budget_bytes'] == 67108864
for relative, expected in seal['raw_case_members'].items():
    assert identity(CASE / relative) == expected
result = {
    'schema': 'razr-r7-original-native80-actual-producer-reader-independent-evidence-readback-v1',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'evidence_readback_pass': True,
    'reviewer_identity': identity(__file__), 'review_resource_limits': {'address_space_bytes': 256 * 2**20, 'CPU_seconds': 60},
    'actual_stages': stages, 'original_80_witness_ids': ids,
    'source_bound_faces': 40, 'original_whole_inputs': 6,
    'original_80_patch_Common_topologically_empty': True, 'original_controls': dict(control_counts),
    'four_finite_material_and_pose_mappings_passed': True, 'current_added_material_signed_volume_mm3': added,
    'current_added_material_original_80_patch_Common_topologically_empty': True,
    'complete_producer_and_reader_saved_geometry': geometry_files,
    'independent_native_saved_BREP_readback_count': 396, 'reader_comparison_count': len(comparisons),
    'all_comparison_topology_and_classification_equal': True,
    'native_area_bit_inequality_count': len(area_differences), 'native_area_bit_inequality_rows': area_differences,
    'maximum_observed_native_area_difference_mm2': r['native_area_comparisons']['maximum_absolute_difference_mm2'],
    'all_native_areas_binary64_equal': r['native_area_comparisons']['all_binary64_equal'],
    'new_physical_area_threshold_introduced': False,
    'same_kernel_separate_process_reader_not_a_second_independent_CAD_kernel': True,
    'qualified_phase_seal': identity(seal_path), 'aggregate_scientific_bytes': seal['scientific_raw_bytes_including_current_inputs'],
    'original_V5_raw_failure_reclassified': False, 'whole_current_exact_native_trim_model_membership_verified': False,
    'full_continuous_G2': False, 'physical_qualification': False, 'additional_CAD_execution_by_this_audit': False,
    'qualification_external_vtk_cleanup_discrepancy_still_unresolved': True, 'seconds': time.monotonic() - START,
}
output = BASE / 'r7-audit/native-stage-v4-review/R7_NATIVE80_ACTUAL_PRODUCER_READER_INDEPENDENT_EVIDENCE_READBACK.json'
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'path': str(output), 'identity': identity(output), 'seconds': result['seconds'],
                  'area_bit_inequality_count': len(area_differences), 'evidence_readback_pass': True}))
