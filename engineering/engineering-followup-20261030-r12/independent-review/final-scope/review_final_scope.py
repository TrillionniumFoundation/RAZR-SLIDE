"""Read-only R12 final ledger/entrypoint consistency review.

No CAD, numerical products, solver, unit tests, network calls or publication are
executed.  The only output mutation is a new review receipt in this directory.
"""
from __future__ import annotations

import ast
import datetime as dt
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess


WORK = Path('/workspace/scratch/1b842ca762be')
ROOT = WORK / 'RAZR-SLIDE'
BASE = ROOT / 'engineering/engineering-followup-20261030-r12'
OUTPUT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path):
    path = path.resolve()
    try:
        name = path.relative_to(ROOT).as_posix()
    except ValueError:
        name = str(path)
    return {'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)}


def verify_rows(base, rows):
    results = []
    for row in rows:
        p = base / row['path']
        assert p.is_file(), str(p)
        assert p.stat().st_size == row['bytes'], str(p)
        assert sha(p) == row['sha256'], str(p)
        results.append(dict(row))
    return results


def main():
    output = OUTPUT / 'FINAL_SCOPE_REVIEW.json'
    if output.exists():
        raise FileExistsError(output)
    ledger = read(BASE / 'R12_COMPLETED_WORK_LEDGER.json')
    records = ledger['bound_records']
    assert len(records) == len({r['path'] for r in records}) == 30
    checked = verify_rows(BASE, records)
    builder = ast.parse((BASE / 'build_root_ledger.py').read_text())
    report_lists = [ast.literal_eval(n.value) for n in ast.walk(builder)
                    if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'reports' for t in n.targets)]
    assert report_lists == [[r['path'] for r in records]]
    workstreams = {w['id']: w for w in ledger['workstreams']}
    assert len(workstreams) == 7

    q = read(BASE / 'qualification/SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json')
    qwork = workstreams['subsequent_current_structure_electrical_test_contract']
    source_rows = verify_rows(ROOT, q['source_identities'])
    assert qwork['final_qualification_sources'] == source_rows
    assert qwork['final_targeted_software_tests_passed'] == q['tests_total'] == 133
    assert qwork['prior_independent_admission_controls'] == q['independent_prior_admission_controls'] == 7
    assert qwork['additional_independent_donor_configurations'] == q['independent_donor_configurations'] == 12
    assert q['three_after_controls_already_included_in_twelve'] is True
    log_checks = []
    for row in q['final_disjoint_test_executions']:
        path = BASE / 'qualification' / row['log']
        assert sha(path) == row['log_sha256']
        text = path.read_text()
        count = int(re.search(r'Ran (\d+) tests in ', text).group(1))
        assert count == row['tests'] and text.rstrip().endswith('OK')
        log_checks.append({'tests': count, 'identity': identity(path)})
    assert [x['tests'] for x in log_checks] == [76, 57]
    assert sum(x['tests'] for x in log_checks) == 133
    old_q = read(BASE / 'qualification/SOURCE_AND_TEST_READBACK.json')
    assert old_q['tests_total'] == 127
    old_review = read(BASE / 'independent-review/qualification/INDEPENDENT_REVIEW.json')
    assert len(old_review['independent_admission_cases']) + len(old_review['independent_g5_chain_cases']) == 7
    donor_review = read(BASE / 'independent-review/qualification-donor-followon/FOLLOWON_REVIEW.json')
    assert donor_review['shared_G4_G5_scope']['actual_admission_controls'] == 12
    assert donor_review['shared_G4_G5_scope']['all_expected_semantics_met'] is True
    donor_sources = {x['repository_path']: (x['bytes'], x['sha256']) for x in donor_review['current_source_identities']}
    assert donor_sources == {x['path']: (x['bytes'], x['sha256']) for x in source_rows}
    assert old_review['source_identities'][0]['sha256'] == '4db012ceee0a67d41c9db2ce812085b232bdac3786b50b72128e265e383527f2'
    assert source_rows[0]['sha256'] == '975b3dc3cb43cc9093108bf661dd6a89d2a4211a3587221004edd963a54b411c'
    assert q['new_full_tree_test_execution'] is False
    assert q['physical_executions'] == 0 and q['physical_G3_G4_G5_pass'] is False

    panel = read(BASE / 'panel-filling/R12_PANEL_FILL_SCOPE.json')
    envelope_work = workstreams['3_conservative_continuous_envelope']
    assert envelope_work['current_panel_filling_scope'] == panel
    panel_checks = []
    threshold = Fraction(panel['original_float64_threshold_exact'])
    assert threshold == Fraction.from_float(1e-7)
    for pair in panel['pairs']:
        exact = Fraction(pair['final_upper_exact_mm3'])
        approximate = pair['final_upper_approx_mm3']
        assert float(exact) == approximate == 0.9600000000000029
        assert exact > threshold
        assert pair['original_1e_minus7_gate_passes_under_stated_model'] is False
        panel_checks.append({'key': pair['key'], 'approximate_conditional_upper_mm3': approximate,
                             'exact_upper_exceeds_original_threshold': True,
                             'original_gate_pass': False})
    for k in ('actual_collision_proved', 'native_material_set_identity_proved',
              'uniform_compiled_error_proved', 'continuous_G2', 'whole_15D_G2',
              'G3', 'G4', 'G5', 'manufacturing_go'):
        assert panel[k] is False, k
    assert envelope_work['actual_panel_KEY_collision_proved_by_positive_upper'] is False
    assert envelope_work['all_positive_RLE_boxes'] == sum(x['all_positive_RLE_boxes'] for x in panel['pairs']) == 169
    assert envelope_work['remaining_full_positive_RLE_boxes'] == 169 - sum(x['exterior_channel_excluded_boxes'] for x in panel['pairs']) == 165
    assert not any(ledger['release'].values())
    assert all(value is False for value in ledger['release'].values())

    numeric = read(BASE / 'numerics/evidence/NUMERICAL_SCOPE.json')
    nwork = workstreams['parallel_original_numerical_qualification']
    assert nwork['panel_five'] == numeric['original_panel_five_residuals']
    assert nwork['frame_five'] == numeric['original_frame_five_residuals']
    assert len(nwork['panel_five']) == len(nwork['frame_five']) == 5
    assert all(0 <= v <= 1e-7 for v in nwork['panel_five'] + nwork['frame_five'])
    assert nwork['restore'] == numeric['original_ExactResponseCache_restore']
    for k in ('new_solver_executed', 'all_7770_K_products_executed',
              'all_7770_successful_full_fields_available', 'legacy_whole_seed_bitwise_replay_passed',
              'arbitrary_RHS_inverse_or_full_QP_resume_qualified'):
        assert nwork[k] is False, k

    current = read(ROOT / 'design/current_product.json')
    status = read(ROOT / 'status.json')
    parent_commit = ledger['baseline']['parent_commit']
    old_bytes = subprocess.check_output(['git', 'show', parent_commit + ':design/current_product.json'], cwd=ROOT)
    historical = json.loads(old_bytes)
    archive = current['prior_current_summary_before_20261030_r12']
    assert all(v == historical[k] for k, v in archive.items())
    assert current['completed_unit_runs'] == historical['completed_unit_runs']
    assert current['current_entrypoint_sync_r9'] == historical['current_entrypoint_sync_r9']
    s4 = current['current_verified_functional_source']
    assert s4['commit'] == historical['current_verified_functional_source']['commit'] == 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
    assert s4['tree'] == historical['current_verified_functional_source']['tree'] == 'cdd9e2c41216201b6cd04dd610d45fde80499045'
    assert (s4['actual_suites'], s4['actual_tests']) == (36, 1654)
    assert s4['containing_ledger_commit_is_tested_functional_source'] is False
    active = current['active_followup']
    assert active['current_contract_sources_changed'] is True
    assert active['new_full_unit_execution'] is False
    assert active['targeted_tests_passed'] == 133
    assert active['independent_admission_controls_passed'] == 7
    assert active['independent_donor_configurations_passed'] == 12
    assert ledger['current_qualification_contract_source_changed'] is True
    assert ledger['new_full_tree_unit_run'] is False
    assert ledger['historical_S4_full_unit_run'] == {'suites': 36, 'tests': 1654, 'new_R12_execution': False}
    for d in (current, status, active):
        for key in ('candidate_go', 'fixture_fabrication_go', 'manufacturing_go'):
            assert d[key] is False
    assert all(v == 'missing' for v in status['physical_qualification'].values())
    for key in ('native_material_set_identity_proved', 'uniform_compiled_geometry_error_proved',
                'physical_allowed_domain_proved', 'full_motion_qualified', 'complete_G2_qualification',
                'current_K1_K3_FE_qualified', 'complete_OEM_electrical_stack_qualified',
                'physical_G3_G4_G5_executed_this_run', 'physical_phone_verified', 'all_blockers_closed'):
        assert active[key] is False
    ledger_ref = 'engineering/engineering-followup-20261030-r12/R12_COMPLETED_WORK_LEDGER.json'
    assert current['current_execution_summary'] == status['current_execution_summary'] == ledger_ref
    sync_spec = importlib.util.spec_from_file_location('readonly_sync_review', ROOT / 'tools/sync_current_design.py')
    sync = importlib.util.module_from_spec(sync_spec)
    sync_spec.loader.exec_module(sync)
    generated = sync.expected_files(ROOT)
    for path, expected in generated.items():
        assert path.read_text() == expected, str(path)
    sync_receipt = read(BASE / 'status/R12_CURRENT_ENTRYPOINT_SYNC_RESULT.json')
    verify_rows(ROOT, sync_receipt['identities'])

    publication = ledger['publication']
    remote = read(BASE / 'publication/READONLY_REMOTE_SNAPSHOT.json')
    rejection = read(BASE / 'publication/PUBLIC_PUSH_REJECTION.json')
    assert publication['public_R9_restoration_verified'] is True
    assert publication['public_R9_commit'] == parent_commit == remote['refs']['refs/heads/evidence/full-sprint-20261029-r9']
    assert publication['R12_public_push_completed'] is False
    assert remote['requested_R12_branch_returned'] is False
    assert remote['remote_write_performed'] is False
    assert rejection['automatic_approval_review'] == 'rejected_before_process_execution'
    assert rejection['public_push_completed'] is False
    assert rejection['alternate_publication_transport_attempted'] is False
    assert active['new_branch_pushed'] is False
    assert active['automatic_publication_review_rejected'] is True

    readme = (BASE / 'README.md').read_text()
    assert '原 whole-seed bitwise replay 仍未通过，历史失败保留' in readme
    assert '原 whole-seed bitwise failure 仍为 false' not in readme
    assert '这个上界不是实际碰撞体积' in readme
    assert '133 项针对性测试' in readme
    assert '新增 12 种 donor 配置' in readme
    assert '这里没有新的全仓回归成绩，也没有实物 pass' in readme
    links = []
    for href in re.findall(r'\[[^\]]+\]\(([^)]+)\)', readme):
        if '://' in href or href.startswith('#'):
            continue
        path = (BASE / href.split('#', 1)[0]).resolve()
        assert path.exists(), href
        links.append(href)

    observed_files = [BASE / 'README.md', BASE / 'R12_COMPLETED_WORK_LEDGER.json',
                      BASE / 'build_root_ledger.py', ROOT / 'design/current_product.json',
                      ROOT / 'CURRENT_DESIGN.md', ROOT / 'docs/RESEARCH_OVERVIEW.md',
                      ROOT / 'status.json', ROOT / 'tools/sync_current_design.py',
                      BASE / 'status/R12_CURRENT_ENTRYPOINT_SYNC_RESULT.json']
    result = {
        'schema': 'r12.independent_final_root_scope_review.v1',
        'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'review_source': identity(Path(__file__)),
        'reviewed_root_identities': [identity(p) for p in observed_files],
        'bound_records': {'declared': 30, 'unique': 30, 'verified_bytes_and_SHA256': 30,
                          'builder_inventory_matches_exactly': True,
                          'total_bound_record_bytes': sum(r['bytes'] for r in checked), 'records': checked},
        'qualification': {'targeted_tests': 133, 'producer_logs_read_back': log_checks,
                          'prior_independent_controls': 7, 'new_independent_donor_configurations': 12,
                          'three_after_controls_not_double_counted': True,
                          'final_sources': source_rows, 'source_bound_followon_matches_final_sources': True,
                          'old_127_and_old_7_review_preserved_at_their_older_source_identity': True,
                          'new_full_tree_or_physical_pass': False},
        'conditional_current_panel_upper': {'pairs': panel_checks,
                                           'native_and_compiled_error_premises_remain_unproved': True,
                                           'positive_upper_is_not_actual_collision_evidence': True,
                                           'all_169_positive_boxes_preserved_with_4_validated_exclusions': True,
                                           'remaining_full_positive_boxes': 165},
        'numerics': {'all_ten_ledger_values_match_sealed_numeric_scope': True,
                     'original_H_and_five_saved_restore_scope_preserved': True,
                     'legacy_whole_seed_bitwise_replay_passed': False,
                     'numerical_execution_performed_by_this_review': False},
        'entrypoints': {'four_files': ['design/current_product.json', 'CURRENT_DESIGN.md',
                                      'docs/RESEARCH_OVERVIEW.md', 'status.json'],
                       'three_generated_files_exactly_match_readonly_sync_render': True,
                       'sync_receipt_source_identities_match': True,
                       'R9_archived_current_summary_keys_verified_against_parent_git_object': list(archive),
                       'R9_parent_commit': parent_commit,
                       'completed_unit_runs_and_R9_sync_record_preserved': True,
                       'S4_commit_tree_and_36_1654_historical_scope_preserved': True,
                       'R12_changed_source_and_absence_of_full_run_explicit': True,
                       'README_relative_links_verified': len(links)},
        'publication': {'R9_publication_matches_retained_remote_snapshot': True,
                        'R12_publication_completed': False,
                        'prior_automatic_rejection_and_no_alternate_route_preserved': True,
                        'live_remote_requery_or_write_by_this_review': False,
                        'final_containing_commit_tree_and_delivery_manifest_are_external_postcommit_step': True},
        'release': dict(ledger['release']),
        'findings': {'corrected_before_seal': [
            'README ambiguity saying whole-seed bitwise failure was false was changed to replay still not passed; historical failure retained.'],
            'remaining_concrete_inconsistency_in_requested_scope': []},
        'scope_limits': [
            'Read-only file identities, retained report/log claims and generated entrypoint consistency only.',
            'No fresh CAD, numeric product, solver, physical test or unit regression executed.',
            'This review does not establish the native material/compiled error bridge or physical allowed domain.',
            'The prior seven admission controls retain their older reviewed source; this report does not relabel them as freshly executed on final source.',
            'Public state is based on the retained timestamped read-only remote snapshot and approval rejection; no network mutation or fresh remote query was made.',
            'The containing local commit/tree and delivery package must be bound separately after commit; no completed publication is asserted.'],
        'repository_files_modified_by_reviewer': 0,
        'all_requested_consistency_checks_passed': True,
    }
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'review': identity(output), 'final_README': identity(BASE / 'README.md'),
                      'ledger': identity(BASE / 'R12_COMPLETED_WORK_LEDGER.json'),
                      'all_requested_consistency_checks_passed': True}, indent=2))


if __name__ == '__main__':
    main()
