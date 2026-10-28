"""Bind the cross-author handoff draft to exact original requirement locators.

This reviews a delivery contract; it never grants specimen or physical passes.
"""
from pathlib import Path
import ast
import collections
import copy
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
draft_path = HERE / 'R5_EXTERNAL_BLOCKER_HANDOFF.json'
draft_bytes = draft_path.read_bytes()
draft = json.loads(draft_bytes)
documents = {}
identities = []
for sid, entry in draft['source_identities'].items():
    data = (ROOT / entry['path']).read_bytes()
    assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']
    identities.append({'source_id': sid, **entry, 'actual_bytes_verified': True})
    documents[sid] = json.loads(data) if entry['path'].endswith('.json') else data.decode()
contract = documents['S01']
requirements = contract['requirements']
by_id = {entry['id']: i for i, entry in enumerate(requirements)}
assert len(requirements) == len(by_id) == 228
result = copy.deepcopy(draft)
result['schema'] = 'razr-r5-external-blocker-handoff-v2-resolved-source-locators'
result['original_draft_identity'] = {'bytes': len(draft_bytes), 'sha256': hashlib.sha256(draft_bytes).hexdigest()}
result['revision_scope'] = 'Replace prose requirement filters and validator locators with exact original indices/function names. No evidence values, acceptance criteria, thresholds or gates changed.'
functions = {node.name for node in ast.parse(documents['S06']).body if isinstance(node, ast.FunctionDef)}
assert 'validate' in functions
for package in result['handoff_packages']:
    refs = []
    for ref in package['source_references']:
        if ref.startswith('S01#/requirements supplier:'):
            refs.extend('S01#/requirements/' + str(by_id[rid]) for rid in package['original_requirement_ids'])
        elif ref.startswith('S06#validate '):
            refs.append('S06#function:validate')
        else:
            refs.append(ref)
    package['source_references'] = list(dict.fromkeys(refs))

def resolve(ref):
    if ref.startswith('user_delivery_scope:'):
        return {'kind': 'visible_user_instruction', 'reference': ref}
    sid, fragment = ref.split('#', 1)
    value = documents[sid]
    if fragment.startswith('function:'):
        assert sid == 'S06' and fragment.removeprefix('function:') in functions
        return {'kind': 'verified_source_function', 'reference': ref}
    assert fragment.startswith('/')
    for part in fragment[1:].split('/'):
        key = part.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return {'kind': 'resolved_json_pointer', 'reference': ref}

resolved = [resolve(ref) for ref in sorted(set(ref for p in result['handoff_packages'] for ref in p['source_references']))]
assigned = {}
handoff_ids = {p['handoff_id'] for p in result['handoff_packages']}
assert len(handoff_ids) == len(result['handoff_packages']) == 13
for package in result['handoff_packages']:
    ids = package['original_requirement_ids']
    assert len(ids) == package['original_requirement_count']
    assert package['new_physical_pass_granted'] is False
    assert set(package['prerequisite_handoff_ids_for_engineering_acceptance']) <= handoff_ids
    for rid in ids:
        assert rid in by_id and rid not in assigned
        assigned[rid] = package['handoff_id']
assert set(assigned) == set(by_id)
assert assigned == result['original_requirement_id_to_primary_handoff']
same_specimen = sum(r['scope'] == 'same_specimen' for r in requirements)
selected_revision = sum(r['scope'] == 'selected_part_revision' for r in requirements)
assert (same_specimen, selected_revision) == (207, 21)
for actual, original in {
    'original_identity_fields': 'identity_fields',
    'original_part_roles': 'part_roles',
    'original_interfaces': 'interfaces',
    'original_measurement_record_requirements': 'measurement_record_requirements',
    'original_FE_contract_unchanged': 'original_FE_contract',
    'original_gate_admission_unchanged': 'gate_admission',
}.items():
    assert result[actual] == contract[original]

def null_paths(value, path=''):
    if value is None:
        return [path]
    if isinstance(value, dict):
        return [p for key, child in value.items() for p in null_paths(child, path + '/' + key.replace('~', '~0').replace('/', '~1'))]
    if isinstance(value, list):
        return [p for i, child in enumerate(value) for p in null_paths(child, path + '/' + str(i))]
    return []

null_counts = {}
for name, entry in result['original_plan_null_locations_and_bindings'].items():
    plan = contract['original_G3_G4_G5_contract']['plan_templates'][name]
    paths = null_paths(plan)
    assert set(paths) == set(entry['null_fields']) and len(paths) == entry['null_fields_count']
    null_counts[name] = len(paths)
assert result['new_fact_values_provided'] == 0
assert result['no_new_threshold_values_provided'] is True
assert result['original_files_modified'] is False
assert result['physical_gate_pass'] == {'G3': False, 'G4': False, 'G5': False}
assert result['all_blockers_closed'] is False
assert [(p['gate'], p['predecessor_gate']) for p in result['physical_gate_progression']] == [('G3', None), ('G4', 'G3'), ('G5', 'G4')]
assert all(p['actual_pass_received'] is False for p in result['physical_gate_progression'])
for original, updated in zip(draft['handoff_packages'], result['handoff_packages']):
    assert {k: v for k, v in original.items() if k != 'source_references'} == {k: v for k, v in updated.items() if k != 'source_references'}
for sid, entry in draft['source_identities'].items():
    data = (ROOT / entry['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256']
target = HERE / 'R5_EXTERNAL_BLOCKER_HANDOFF_V2.json'
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
review = {
    'schema': 'r5-cross-author-handoff-contract-readback-v2',
    'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'completed': True, 'review_scope': 'Existing-source and requirement-map consistency; no input acquisition or engineering acceptance.',
    'handoff_bytes': target.stat().st_size, 'handoff_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'original_draft_identity': result['original_draft_identity'], 'source_bytes_verified': identities,
    'resolved_source_references': resolved, 'handoff_packages': 13,
    'unique_original_requirements': 228, 'same_specimen_requirements': 207,
    'selected_part_revision_requirements': 21, 'omitted_requirements': [], 'duplicate_requirements': [],
    'original_embedded_contract_groups_exactly_equal': 6, 'original_plan_null_counts': null_counts,
    'original_gate_sequence_retained': ['G3', 'G4', 'G5'], 'new_values_or_thresholds': 0,
    'new_physical_passes': 0, 'fact_authenticity_verified': False, 'all_blockers_closed': False,
}
(HERE / 'R5_HANDOFF_CROSS_AUTHOR_READBACK_V2.json').write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'handoff_sha256': review['handoff_sha256'], 'packages': 13, 'requirements': 228, 'sources': len(identities), 'resolved_references': len(resolved), 'plan_null_counts': null_counts, 'new_physical_passes': 0}))
