"""Independent read-only audit of the frozen R13 science integration.

Only bytes, saved JSON records, rational results and local Git objects are read.
No producer, updater, native geometry, scientific solver or tests are executed.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import subprocess

ROOT = Path('/workspace/scratch/1b842ca762be/RAZR-SLIDE')
REL = Path('engineering/engineering-followup-20261030-r13')
R13 = ROOT / REL
R12REL = Path('engineering/engineering-followup-20261030-r12')
R12 = ROOT / R12REL
BASE_COMMIT = 'ab9ef3270a9a0d0d28f605f7188038db133dbcd8'
OUTDIR = Path(__file__).resolve().parent
OUT = OUTDIR / 'R13_INTEGRATED_FINAL_SCOPE_REVIEW.json'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def bound(row, path):
    assert path.is_file(), f'missing file {path}'
    assert path.stat().st_size == row['bytes'], f'length mismatch {path}'
    assert sha(path) == row['sha256'], f'SHA mismatch {path}'


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True)
    return result.stdout


ledger = read(R13 / 'R13_COMPLETED_WORK_LEDGER.json')
assert len(ledger['bound_records']) == 31
assert len({r['path'] for r in ledger['bound_records']}) == 31
for row in ledger['bound_records']:
    bound(row, ROOT / row['path'])
assert ledger['base_public_commit'] == BASE_COMMIT
assert ledger['base_public_tree'] == '922ab085590d0f8a59d1dd8675bad9bc8f3b27c5'
assert len(ledger['workstreams']) == 7
assert all(v is False for v in ledger['release'].values())
assert ledger['historical_S4_full_unit_run'] == {
    'commit': 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
    'suites': 36, 'tests': 1654, 'new_R13_execution': False,
}
streams = {w['id']: w for w in ledger['workstreams']}

# Independently bind all four imported groups, not the root additions.
imports = read(R13 / 'independent-review/COMPONENT_IMPORT_READBACK.json')
import_names = []
component_counts = {}
for name, group in imports['components'].items():
    rows = group['files']
    assert len(rows) == group['imported_files']
    assert sum(r['bytes'] for r in rows) == group['imported_bytes']
    assert group['all_source_and_destination_bytes_equal'] is True
    for row in rows:
        bound(row, Path(row['source']))
        bound(row, ROOT / row['repository_path'])
        import_names.append(row['repository_path'])
    component_counts[name] = {'files': len(rows), 'bytes': group['imported_bytes']}
assert len(import_names) == len(set(import_names)) == imports['file_count'] == 313
assert sum(c['bytes'] for c in component_counts.values()) == imports['total_bytes'] == 13068336
assert imports['private_OEM_response_bodies_imported'] is False
assert imports['R12_scientific_files_modified'] is False
assert imports['scientific_scope_promoted_by_copy'] is False

geo = read(R13 / 'geometry/R13_GEOMETRY_SCOPE.json')
gm = read(R13 / 'geometry/DELIVERY_MANIFEST.json')
assert len(gm['files']) == gm['file_count'] == 150
assert sum(r['bytes'] for r in gm['files'].values()) == gm['total_bytes'] == 3989140
for name, row in gm['files'].items():
    bound(row, R13 / 'geometry' / name)
structure = streams['2_named_structure_and_allowed_domain']
assert structure['actual_native_readback'] == geo['new_native_executions']
assert structure['complete_region_models'] == geo['complete_source_region_models']
assert structure['remaining'] == geo['open_qualification']
assert not any(structure['remaining'].values())
qs = structure['source_q_subsystem']
assert (qs['complete_profile_branches'], qs['merged_branch_pairs'], qs['feasible_branch_pairs'], qs['infeasible_branch_pairs']) == (16, 25, 17, 8)
assert all(qs[k] is False for k in ('full_float64_acceptance_equivalence_proved', 'all_15D_mechanical_constraints_projected_and_qualified', 'physical_allowable_domain_proved'))

env = read(R13 / 'envelope/R13_ENVELOPE_SCOPE.json')
envelope = streams['3_conservative_continuous_envelope']
assert envelope['pairs'] == env['pairs']
assert envelope['premises'] == env['premises']
assert (envelope['all_original_positive_boxes'], envelope['full_positive_contributions_retained'], envelope['inherited_KEY_exclusions'], envelope['new_panel_exclusions_under_T']) == (169, 157, 4, 8)
assert all(envelope[k] is False for k in ('old_B0_only_bound_replaced', 'native_B0_and_T_membership_proved', 'complete_global_native_realization_existence_proved', 'uniform_compiled_error_proved', 'native_tolerance_is_certified_evaluator_error', 'full_continuous_G2', 'positive_upper_is_measured_collision'))
first_review = read(OUTDIR / 'ENVELOPE_AND_MOTION_SCOPE_REVIEW.json')
assert first_review['completed'] is True and first_review['concrete_consistency_defects_found'] == []
for row in first_review['bound_documents']:
    bound(row, Path(row['path']))
for row in first_review['geometry_motion_projection_review']['bound_documents']:
    bound(row, Path(row['path']))

# The numerical and original witness workstream are literal R12 inheritance.
old = read(R12 / 'R12_COMPLETED_WORK_LEDGER.json')
numeric = read(R12 / 'numerics/evidence/NUMERICAL_SCOPE.json')
old_streams = {w['id']: w for w in old['workstreams']}
inherited_checks = {}
for key, added in (
    ('1_midtravel_whole_factory_witnesses', 'new_R13_full_factory_execution'),
    ('parallel_original_numerical_qualification', 'new_R13_numerical_product_or_solver_execution'),
):
    reduced = copy.deepcopy(streams[key])
    assert reduced.pop(added) is False
    assert 'Retain' in reduced.pop('scope_of_R13_action')
    assert reduced == old_streams[key]
    inherited_checks[key] = True
num = streams['parallel_original_numerical_qualification']
assert num['panel_five'] == numeric['original_panel_five_residuals']
assert num['frame_five'] == numeric['original_frame_five_residuals']
assert len(num['panel_five']) == len(num['frame_five']) == 5
assert all(0 <= x <= num['threshold'] == 1e-7 for x in num['panel_five'] + num['frame_five'])
assert num['restore'] == numeric['original_ExactResponseCache_restore']
assert num['restore']['probes'] == num['restore']['response_calls'] == 5
assert num['restore']['largest_relative_error'] <= num['restore_threshold'] == 2e-7
assert num['original_H_columns'] == numeric['H_columns'] == {'panel': 3885, 'frame': 3885}
assert num['basis_RHS_and_saved_projection_hashes_checked'] == 7770
assert all(num[k] is False for k in ('new_solver_executed', 'all_7770_K_products_executed', 'all_7770_successful_full_fields_available', 'legacy_whole_seed_bitwise_replay_passed', 'arbitrary_RHS_inverse_or_full_QP_resume_qualified', 'new_R13_numerical_product_or_solver_execution'))

qual = read(R12 / 'qualification/SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json')
inherited_qual = ledger['inherited_R12_qualification_validation']
assert inherited_qual['source_identities'] == qual['source_identities']
for row in inherited_qual['source_identities']:
    bound(row, ROOT / row['path'])
assert (inherited_qual['targeted_tests'], inherited_qual['independent_admission_controls'], inherited_qual['independent_donor_configurations']) == (133, 7, 12)
assert all(inherited_qual[k] is False for k in ('new_R13_contract_source_change', 'new_R13_test_execution', 'full_tree_qualification_at_current_source', 'physical_pass'))
unchanged_paths = [str(R12REL), 'integration', 'tests/test_product_qualification_contracts.py', 'engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py']
assert git('diff', '--name-only', BASE_COMMIT, '--', *unchanged_paths) == b''
assert git('ls-files', '--others', '--exclude-standard', '--', str(R12REL)) == b''

real = streams['parallel_same_specimen_and_OEM_originals']
delta = read(R13 / 'real-inputs/CURRENT_INPUT_DELTA.json')
assert all(real[k] == 0 for k in ('complete_new_OEM_PDFs_acquired', 'new_same_specimen_originals', 'new_physical_measurements', 'new_selected_PN_revision_bindings'))
assert (real['same_specimen_identity_fields'], real['part_roles'], real['actual_interfaces'], real['original_required_facts']) == (10, 7, 12, 228)
assert delta['new_same_specimen_originals'] == delta['new_physical_measurements'] == 0
assert real['distinct_service_PNs_proved_equivalent_or_XT2551_3_compatible'] is False
assert real['private_third_party_complete_response_bodies_published'] is False
assert not list((R13 / 'real-inputs').rglob('*.pdf')) and not list((R13 / 'real-inputs').rglob('*.html'))
physical = streams['last_sequential_physical_acceptance']
assert physical['actual_physical_runs'] == 0
assert all(physical[k] is False for k in ('G3_pass', 'G4_pass', 'G5_pass', 'software_tests_or_publication_are_physical_acceptance'))

# Four source/current entrypoints: check retained receipt bytes and content links.
sync = read(R13 / 'status/R13_CURRENT_ENTRYPOINT_SYNC_RESULT.json')
entry_names = ['design/current_product.json', 'CURRENT_DESIGN.md', 'docs/RESEARCH_OVERVIEW.md', 'status.json']
assert set(sync['source_and_outputs']) == set(entry_names)
for name, row in sync['source_and_outputs'].items():
    bound(row, ROOT / name)
assert len(sync['runs']) == 2 and all(r['returncode'] == 0 and r['stderr'] == '' for r in sync['runs'])
assert json.loads(sync['runs'][1]['stdout']) == {'mode': 'check', 'changed': []}
current = read(ROOT / entry_names[0])
status = read(ROOT / 'status.json')
assert current['current_execution_summary'] == status['current_execution_summary'] == str(REL / 'R13_COMPLETED_WORK_LEDGER.json')
assert current['stage_summary'] == status['current_product_stage']
assert current['verification_summary'] == status['current_fresh_verification']
assert current['work_packages'] == status['current_work_packages']
for name in ('CURRENT_DESIGN.md', 'docs/RESEARCH_OVERVIEW.md'):
    text = (ROOT / name).read_text()
    assert current['stage_summary'] in text and current['verification_summary'] in text
for source in (current, status):
    assert all(source[k] is False for k in ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go'))
active = current['active_followup']
assert active['R12_publication_verified'] is True and active['new_branch_pushed'] is False
assert active['new_R13_original_numerical_products_executed'] is False
assert active['new_full_unit_execution'] is False and active['new_full_factory_execution'] is False
assert active['new_conditional_B0_AND_T_bound_qualified_under_stated_model'] is True
assert active['exact_real_q_subsystem_projection_proved'] is True
for k in ('full_float64_or_15D_acceptance_equivalence_proved', 'native_material_set_identity_proved', 'native_T_membership_proved', 'complete_global_native_realization_existence_proved', 'uniform_compiled_geometry_error_proved', 'physical_allowed_domain_proved', 'complete_G2_qualification', 'current_K1_K3_FE_qualified', 'complete_OEM_electrical_stack_qualified', 'physical_G3_G4_G5_executed_this_run', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go', 'all_blockers_closed'):
    assert active[k] is False
source = current['current_verified_functional_source']
assert source['commit'] == 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
assert (source['actual_suites'], source['actual_tests']) == (36, 1654)
assert source['containing_ledger_commit_is_tested_functional_source'] is False
base_current = json.loads(git('show', f'{BASE_COMMIT}:design/current_product.json'))
prior = current['prior_current_summary_before_20261030_r13']
assert all(value == base_current[key] for key, value in prior.items())

# Publication mapping is checked with retained exact commit objects plus the
# already fetched Git objects. This review makes no new network request.
publication = read(R13 / 'publication/R12/R12_PUBLICATION_READBACK.json')
assert current['publication_record'] == str(REL / 'publication/R12/R12_PUBLICATION_READBACK.json')
assert publication['remote_branch_head'] == BASE_COMMIT
assert publication['source_trees_identical'] is True
assert publication['commit_metadata_identical'] is False
assert publication['scientific_or_physical_qualification_changed_by_publication'] is False
assert publication['literal_original_local_commit_SHAs_are_remote_branch_commits'] is False
raw_local = {}
for row in publication['original_local_commit_objects']:
    path = R13 / 'publication/R12' / row['path']
    bound(row, path)
    raw = path.read_bytes()
    oid = hashlib.sha1(b'commit ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert oid == row['git_commit_id_reconstructed_from_exact_raw_bytes']
    header = raw.split(b'\n\n', 1)[0].decode().splitlines()
    raw_local[oid] = {'tree': next(x[5:] for x in header if x.startswith('tree ')), 'parents': [x[7:] for x in header if x.startswith('parent ')]}
publication_mapping = []
last_local = last_remote = publication['base_commit']
for row in publication['commits']:
    line = git('show', '-s', '--format=%T %P', row['remote']).decode().strip().split()
    assert line[0] == row['tree'] == raw_local[row['local']]['tree']
    assert line[1:] == [last_remote]
    assert raw_local[row['local']]['parents'] == [last_local]
    assert row['local'] != row['remote']
    publication_mapping.append({**row, 'local_parent': last_local, 'remote_parent': last_remote, 'exact_tree_and_order_match': True})
    last_local, last_remote = row['local'], row['remote']
assert last_remote == BASE_COMMIT
assert ledger['publication_at_science_seal']['R13_publication_not_yet_claimed_by_this_science_record'] is True
assert current['prior_current_summary_before_20261030_r13']['active_followup']['automatic_publication_review_rejected'] is True

readme = (R13 / 'README.md').read_text()
assert '对该子系统消元后' in readme
assert '不是完整 15D 机械约束的投影' in readme
assert 'R13 没有再次运行这些已通过的乘积' in readme
assert '313 个组件文件，13,068,336 B' in readme
assert '该计数只指这四组导入' in readme
assert 'R12 封存时的' in readme and '完整 PDF 新取得数为 0' in readme

report = {
    'schema': 'razr-r13-independent-integrated-final-scope-review-v1',
    'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
    'review_source': identity(Path(__file__).resolve()),
    'completed': True,
    'concrete_consistency_defects_found': [],
    'review_method': 'Read-only SHA/length/inventory checks, saved JSON comparison, exact prior-review binding, textual scope review and existing local Git object reads. No CAD, numerical product, scientific producer, updater, unit test, source download or publication executed.',
    'bound_root_documents': [identity(R13 / name) for name in ('README.md', 'R13_COMPLETED_WORK_LEDGER.json', 'build_r13_ledger.py', 'import_components_r13.py', 'update_current_entrypoints.py', 'status/R13_CURRENT_ENTRYPOINT_SYNC_RESULT.json')],
    'prior_component_scope_review': identity(OUTDIR / 'ENVELOPE_AND_MOTION_SCOPE_REVIEW.json'),
    'all_31_root_bound_records_match': True,
    'component_import_readback': {'file_count': 313, 'total_bytes': 13068336, 'components': component_counts, 'each_retained_source_and_imported_destination_matches': True, 'count_excludes_root_additions_and_later_reproduction_or_review_supplements': True},
    'geometry_scope': {'complete_declared_modification_windows_only': True, 'counts_match_sealed_geometry_scope': True, 'zero_native_differences_not_promoted_to_exact_material_identity': True, 'projection_is_listed_shared_slide_and_side_deviation_q_subsystem_only': True, 'no_claim_of_full_13D_or_15D_source_acceptance_or_physical_domain': True, 'all_15D_projected_and_qualified_flag': False},
    'envelope_scope': {'old_B0_bound_unchanged': True, 'new_bound_only_under_B0_AND_T': True, '169_boxes_and_157_positive_contributions_match': True, 'native_membership_global_realization_compiled_error_and_continuous_G2_not_proved': True, 'no_observed_collision_or_physical_clearance_claim': True},
    'inherited_R12_numeric_scope': {'literal_R12_workstream_retained_except_explicit_R13_nonexecution_scope': inherited_checks['parallel_original_numerical_qualification'], 'panel_residuals': num['panel_five'], 'frame_residuals': num['frame_five'], 'original_threshold': num['threshold'], 'all_ten_saved_values_below_original_threshold': True, 'H_columns': num['original_H_columns'], 'basis_RHS_and_saved_projection_identity_count': 7770, 'fresh_7770_K_products_claimed': False, 'restore': num['restore'], 'restore_threshold': num['restore_threshold'], 'new_R13_solve_or_original_product_claimed': False, 'legacy_whole_seed_replay_passed': False, 'arbitrary_RHS_or_full_QP_qualified': False},
    'qualification_validation_scope': {'targeted_tests_inherited': 133, 'older_independent_admission_controls': 7, 'additional_donor_configurations': 12, 'three_bound_source_files_match_R12_final_identity': True, 'new_R13_test_run_claimed': False, 'historical_S4_full_run_separate': True},
    'retained_R12_science_and_functional_source': {'git_diff_from_published_R12_empty_for_checked_paths': unchanged_paths, 'untracked_new_files_inside_R12_directory': 0, 'original_finite_factory_witness_scope_retained': inherited_checks['1_midtravel_whole_factory_witnesses']},
    'real_inputs_scope': {'new_complete_PDFs': 0, 'new_specimen_originals': 0, 'new_measurements': 0, 'new_qualified_selected_PN_revision_bindings': 0, 'same_specimen_10_7_12_unclosed': True, 'required_facts_retained': 228, 'metadata_only_no_third_party_PDF_or_HTML_bodies': True, 'source_access_claims_come_from_bound_receipts_no_new_web_verification_in_this_review': True},
    'current_entrypoints': {'files': [identity(ROOT / name) for name in entry_names], 'all_match_saved_sync_receipt': True, 'three_generated_entrypoints_refer_to_same_current_stage_and_verification': True, 'complete_prior_R12_summary_archive_equals_published_R12_values': True, 'S4_36_1654_identity_retained_as_historical_only': True, 'all_current_release_flags_false': True},
    'publication': {'R12_two_commit_mapping': publication_mapping, 'original_raw_local_commit_objects_reconstruct_their_SHA1': True, 'two_source_trees_and_parent_order_match_existing_fetched_git_objects': True, 'commit_metadata_identical': False, 'prior_automatic_rejection_retained_as_history': True, 'current_science_seal_R12_published_R13_not_yet_claimed': True, 'R13_future_actual_publication_requires_separate_post_commit_receipt': True, 'new_network_or_git_mutation_in_this_review': False},
    'all_science_release_flags_false': ledger['release'],
    'manual_scope_conclusions': [
        'The root README and ledger preserve B0 versus B0 AND T, explicitly block promotion into native or physical qualification, and retain unresolved material/global-realization/error premises.',
        'The root q-subsystem language meets the explicit qualifier; neither a complete 13D/15D source acceptance projection nor full float64 execution equivalence is claimed.',
        'Six declared local windows and complete local analytic partitions are not promoted into all inherited parent CSG, whole-part minimum thickness, weakest load section or current FE qualification.',
        'Original R12 numerical products, H identities, five saved restore actions and 133 synthetic tests are inherited with their original scope; they are not counted as new R13 executions.',
        'Three indexed OEM documents and service-part leads remain source metadata. The current access failure is retained and no same-specimen or selected-revision binding is inferred.',
        'The 313-file import count applies only to its four named component groups; root integration, final review and subsequent reproduction supplements are outside that count.',
        'The R12 public mapping concerns identical source trees, not identical commit metadata; historical pre-authorization rejection is preserved without contradicting the later actual publication.',
    ],
    'exclusions': [
        'This is a consistency closeout, not a new independent proof or rerun of all scientific predicates.',
        'Any later reproduction supplement or future R13 publication is a distinct record; this review does not pre-certify a future commit or remotely published branch.',
    ],
}
assert not OUT.exists(), 'Preserve previous reviews; use a separate follow-on receipt.'
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'completed': True, 'review': identity(OUT)}, ensure_ascii=False))
