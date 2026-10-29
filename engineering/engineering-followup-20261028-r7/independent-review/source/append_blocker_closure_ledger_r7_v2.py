"""Append actual bounded findings to the preserved original seven-row ledger.

No original report, V1 ledger, source criterion, or scientific gate is edited.
This derivative reads saved evidence only; it does not rerun any algorithm.
"""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import resource
import signal
import stat
import time
import traceback

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / 'r7-audit/blocker-ledger'
START = time.monotonic()
WALL = 30
AS = 256 * 2**20
EXTRA = {
    'prior_ledger_V1_JSON': 'r7-audit/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_V1.json',
    'prior_ledger_V1_Markdown': 'r7-audit/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_V1.md',
    'prior_ledger_generation': 'r7-audit/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_GENERATION_RECEIPT_V1.json',
    'prior_ledger_writer': 'r7-audit/build_blocker_closure_ledger_r7_v1.py',
    'prior_ledger_scope_independent_review': 'r7-audit/blocker-ledger/R7_BLOCKER_LEDGER_V1_NATIVE_NUMERIC_SCOPE_INDEPENDENT_REVIEW.json',
    'positive_q_source_mapping': 'r7-audit/blocker-ledger/positive-q-source-readback/R7_POSITIVE_Q_SOURCE_AND_FACTORY_MAPPING_READBACK_V1.json',
    'positive_q_complete_original_manifest': 'r7-audit/blocker-ledger/positive-q-source-readback/MANIFEST.json',
    'positive_q_independent_source_scope_review': 'r7-audit/blocker-ledger/positive-q-source-readback/R7_POSITIVE_Q_MAPPING_INDEPENDENT_SOURCE_SCOPE_REVIEW_V1.json',
    'positive_q_writer': 'r7-audit/read_positive_q_source_mapping_r7_v1.py',
    'native_finite_publication': 'r7-publication/R7_NATIVE_FINITE_REMOTE_PUBLICATION_VERIFIED_V1.json',
    'scoped_uploaded_original_retrieval': 'r7-audit/R7_REAL_SPECIMEN_SCOPED_RETRIEVAL_OBSERVATION_V1.json',
    'far_partial_later_cache_reclamation': 'r7-publication/R7_FAR_REDUNDANT_PARTIAL_CACHE_RECLAIM_V1.json',
    'far_partial_cache_reclamation_source': 'r7-publication/reclaim_far_redundant_partial_cache_v1.py',
    'edge189_actual_report': 'r7-envelope/edge189-source-diagnostic-v1/attempt-1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_V1.json',
    'edge189_actual_producer_claim': 'r7-envelope/edge189-source-diagnostic-v1/attempt-1/PRODUCER_LINE_SUPPORT_CLAIM_V1.json',
    'edge189_original_contract': 'r7-envelope/edge189-source-diagnostic-v1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_CONTRACT_V1.json',
    'edge189_original_source': 'r7-envelope/edge189-source-diagnostic-v1/diagnose_edge189_line_support_r7e_v1.py',
    'edge189_external_actual_readback': 'r7-envelope/edge189-source-diagnostic-v1/ACTUAL_LAUNCH_AND_READBACK_RECEIPT_V1.json',
    'edge189_independent_actual_evidence_audit': 'r7-native/edge189-actual-readback-v1/R7I_EDGE189_ACTUAL_INDEPENDENT_EVIDENCE_READBACK_V1.json',
    'edge189_root_actual_readback': 'r7-audit/envelope-edge189-review/R7E_EDGE189_ACTUAL_ROOT_READBACK_V1.json',
    'edge189_independent_corner_checker_source': 'r7-native/edge189-independent-v1/verify_edge189_line_support_r7i_v2.py',
    'edge189_original_line_and_tolerance_scope': 'r7-native/edge189-independent-v1/R7I_EDGE189_ORIGINAL_LINE_AND_TOLERANCE_SCOPE_REVIEW_V1.json',
    'edge189_complete_manifest': 'r7-envelope/edge189-source-diagnostic-v1/MANIFEST.json',
    'edge189_actual_summary': 'r7-envelope/edge189-source-diagnostic-v1/RESULT_SUMMARY_V1.json',
}


class LedgerBudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    need(stat.S_ISREG(path.lstat().st_mode), 'Ledger input is not a regular file: ' + str(path))
    h = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(2**20), b''):
            h.update(data)
            total += len(data)
    need(total == path.stat().st_size, 'Ledger input size changed during read')
    return {'bytes': total, 'sha256': h.hexdigest()}


def load(name, catalog):
    return json.loads((BASE / catalog[name]['workspace_relative_path']).read_bytes())


def emit(path, raw):
    need(not path.exists(), 'New ledger version/output required')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def link(name, catalog):
    return '[' + name + '](sandbox:' + str(BASE / catalog[name]['workspace_relative_path']) + ')'


def section(text, first, following):
    need(text.count(first) == 1 and text.count(following) == 1, 'Original Markdown section anchors differ')
    return text.split(first, 1)[1].split(following, 1)[0]


def run():
    prior_path = BASE / EXTRA['prior_ledger_V1_JSON']
    prior = json.loads(prior_path.read_bytes())
    need(prior['schema'] == 'razr-r7-user-seven-row-blocker-closure-ledger-v1', 'Original V1 schema differs')
    need(not prior['all_blockers_closed'] and not prior['new_mandatory_gates_added'], 'Original V1 scope differs')
    catalog = copy.deepcopy(prior['evidence_catalog'])
    for name, value in catalog.items():
        need(identity(BASE / value['workspace_relative_path']) == {k: value[k] for k in ('bytes', 'sha256')}, 'A bound original V1 input differs: ' + name)
    for name, relative in EXTRA.items():
        need(name not in catalog, 'Duplicate source identity key')
        catalog[name] = {'workspace_relative_path': relative, **identity(BASE / relative)}
    pub = load('native_finite_publication', catalog)
    retrieval = load('scoped_uploaded_original_retrieval', catalog)
    reclaim = load('far_partial_later_cache_reclamation', catalog)
    qread = load('positive_q_source_mapping', catalog)
    qmanifest = load('positive_q_complete_original_manifest', catalog)
    edge = load('edge189_actual_report', catalog)
    edge_exit = load('edge189_external_actual_readback', catalog)
    edge_review = load('edge189_independent_actual_evidence_audit', catalog)
    edge_manifest = load('edge189_complete_manifest', catalog)
    need(pub['commit'] == '34764db3c8d61d6e53ea22da8caf4dc57b931463'
         and pub['all_remote_new_blob_sha_and_size_match'] and pub['all_prior_R7_blob_sha_and_size_match']
         and not pub['exact_a11_requested_push_fulfilled'], 'New native publication scope differs')
    need(retrieval['source_filter'] == 'uploaded' and not retrieval['qualification_claimed'], 'Scoped retrieval interpretation differs')
    for key in ('initial_result', 'simpler_retry_result'):
        need(retrieval[key]['structuredContent']['results'] == [], 'Scoped uploaded retrieval is not an empty result')
    need(reclaim['partial_absent_at_receipt'] and reclaim['final_original_unchanged']
         and reclaim['historical_rename_to_later_two_path_correspondence_unresolved']
         and not reclaim['science_results_or_original_gates_changed'], 'Later cache reclamation scope differs')
    need(reclaim['exact_identity'] == {k: prior['complete_evidence_archives_saved']['far'][k] for k in ('bytes', 'sha256')}, 'Far saved bytes differ from the later cache receipt')
    need(qread['all_original_inputs_unchanged_before_after'] and len(qread['four_profiles']) == 4
         and not qread['new_CAD_project_import_force_contact_or_motion_execution'], 'Positive q source read scope differs')
    for pose in ('near', 'far'):
        need(qread['two_actual_pose_report_mappings'][pose]['actual_factory_q_by_side_mm']
             == prior['finite_pose_scope'][pose]['actual_q_by_side_mm'], 'Actual finite q mapping differs')
        for rows in qread['two_actual_pose_report_mappings'][pose]['program_branch_selections'].values():
            need(all(row['selected_source_branch'] == 'lower_stop'
                     and row['branch_selection_is_program_semantics_not_actual_contact_or_reachability']
                     for row in rows), 'Source-only lower_stop selection scope differs')
    checked_manifest_members = {}
    qroot = (BASE / EXTRA['positive_q_complete_original_manifest']).parent
    for relative, expected in qmanifest['outputs'].items():
        need(identity(qroot / relative) == expected, 'A complete original q appendix member differs')
        checked_manifest_members[str((qroot / relative).relative_to(BASE))] = expected
    eroot = (BASE / EXTRA['edge189_complete_manifest']).parent
    need(edge_manifest['member_count'] == len(edge_manifest['files']) == 22, 'Edge complete manifest count differs')
    for row in edge_manifest['files']:
        path = eroot / row['path']
        expected = {k: row[k] for k in ('bytes', 'sha256')}
        need(identity(path) == expected, 'An original edge diagnostic member differs')
        checked_manifest_members[str(path.relative_to(BASE))] = expected
    need(edge['completed'] and edge['finite_source_model_diagnostic_only'], 'Actual edge finite diagnosis absent')
    need(edge['source_child_cumulative_depth'] == 25 and not edge['original_V6_depth_gate_passed'], 'Original depth gate may not be upgraded')
    need(edge['new_splits'] == 0 and edge['actual_fixed_whole_channel_attempts'] == 1, 'Unexpected new search scope')
    need(not edge['V9_first_u_qualification'] and not edge['original_V9_owned_failure_reclassified']
         and not edge['new_full_frame_execution'] and not edge['native_operations']
         and not edge['native_BREP_error_bound_certified'] and not edge['full_continuous_G2'], 'Unsupported edge scientific upgrade')
    support = edge['independent_source_support_readback']
    need(support['claim_verified'] and support['source_box_equals_original_carrier']
         and support['bare_source_contained_in_original_carrier_box']
         and not support['hypothetical_tube_contained_in_original_carrier'], 'Original B/source/tube distinction lost')
    need(len(support['exact_vertices']) == 16 and len(support['hypothetical_tube_vertices']) == 128, 'Independent saved corner census differs')
    need(all(row['inside_original_carrier_box'] for row in support['exact_vertices'])
         and all(not row['inside_original_carrier_box'] for row in support['hypothetical_tube_vertices']), 'Saved exact/tube inclusion outcomes differ')
    comparisons = edge['actual_three_fixed_piece_comparisons']
    need([row['separation_code'] for row in comparisons] == [None, '7', '7'], 'Three fixed source comparisons differ')
    channel = edge['fixed_whole_channel_result']
    codes = channel['separated_original_piece_prefix_codes']
    need(channel['executed'] and len(codes) == channel['original_complete_material_piece_count'] == 523
         and channel['first_unresolved_original_piece_index'] is None
         and channel['conditional_source_model_open_interior_excluded'], 'Complete fixed conditional channel not passed')
    nonaxis = [i for i, code in enumerate(codes) if code == '7']
    need(nonaxis == [77, 332] and channel['original_independent_certificate_readback'] == {'pieces': 523, 'nonaxis': 2}, 'Saved original independent certificate scope differs')
    need(len(edge['actual_negative_controls']) == 5 and all(row['executed'] and row['rejected']
         and row['expected_rejection_confirmed'] for row in edge['actual_negative_controls']), 'Five phase-specific actual negative controls differ')
    need(edge['conditional_complete_channel_omitted_code_control']['rejected'], 'Actual omitted-code rejection absent')
    need(edge_exit['actual_exit_code'] == 0 and edge_exit['registered_input_and_artifact_count'] == 118
         and edge_exit['all_registered_inputs_unchanged'] and edge_exit['all_readback_checks_passed'], 'Complete actual launch/readback receipt differs')
    need(edge_review['all_requested_read_only_checks_passed']
         and edge_review['original_launch_worker_post_and_current_118_hashes_all_equal']
         and edge_review['all_118_sources_and_all_actual_evidence_unchanged_during_readback']
         and not edge_review['new_geometry_support_or_channel_execution'], 'Independent actual edge evidence audit differs')
    for key, ref in [('source', 'edge189_original_source'), ('contract', 'edge189_original_contract'),
                     ('source_support_claim', 'edge189_actual_producer_claim')]:
        need({k: edge[key][k] for k in ('bytes', 'sha256')} == {k: catalog[ref][k] for k in ('bytes', 'sha256')}, 'Edge actual bound identity differs: ' + key)

    result = copy.deepcopy(prior)
    result['schema'] = 'razr-r7-user-seven-row-blocker-closure-ledger-v2'
    result['recorded_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['source_writer'] = {'workspace_relative_path': str(Path(__file__).resolve().relative_to(BASE)), **identity(Path(__file__))}
    result['resource_limits'] = {'wall_seconds': WALL, 'address_space_bytes': AS}
    result['prior_V1_preserved_unchanged'] = catalog['prior_ledger_V1_JSON']
    result['version_scope'] = 'Append actual edge189 finite source result, positive-q original mapping, native remote receipt, scoped retrieval and dated redundant-cache reclamation; preserve all prior failures and original gates.'
    result['evidence_catalog'] = catalog
    result['rows'][1]['closed_scope'] += ' 四个原ContactProfile完整字节及正q开闭分段、实际factory同一q映射和STOP/SPRING源码依赖现已读回；仍仅为程序和原资料范围。'
    result['rows'][1]['actual_evidence'].append('完整原profile的a=0.0011145618000001356、b=0.09055728089999172 mm；contact0/1的c分别0.6429179606749895/0.64291796067499 mm。正q区间为(0,a]、(a,b)、[b,c)、[c,12]。两有限姿态的同一q在程序中选择lower_stop，不形成实际接触/可达性资格。')
    result['rows'][1]['evidence_ids'] += ['positive_q_source_mapping', 'positive_q_complete_original_manifest', 'positive_q_independent_source_scope_review']
    result['rows'][2]['closed_scope'] += ' 后续edge189固定低子、固定−Y完整523-piece通道在新增slab的条件源模型中取得一次开放内部排除，原完整域资格仍未闭合。'
    result['rows'][2]['actual_evidence'][2] = '相关性诊断读取81个保存prefix/972通道；wire诊断不提供native filling证明。此前一次原空间split的两子在其原报告中仍pending、excluded=0；累计depth25超过原V6 depth24，原报告不重判。'
    result['rows'][2]['actual_evidence'].append('edge189保留原完整Line、全D、nonzero Vz及原AABB六端点；原AABB-only失败，新增exact/τ slab均给code7。唯一固定完整通道523/523，原独立reader记录523件/2个nonaxis，128个假设tube角点均在原B外，native误差证书仍为false。')
    result['rows'][2]['limits_or_remaining'][2] = '这一新证书只针对原depth25低子一个固定通道的条件源模型开放内部；高子、其他旧叶、完整16帧、原depth24、V9 u/owned和native材料资格全部未升级。scalar support gap使用未单位化normal，不能叫物理净间隙。'
    result['rows'][2]['evidence_ids'] += ['edge189_actual_report', 'edge189_original_contract', 'edge189_external_actual_readback', 'edge189_independent_actual_evidence_audit', 'edge189_complete_manifest']
    result['rows'][4]['actual_evidence'].append('当前可访问 uploaded 原件的5个定向查询及一次简化重试均无返回结果；索引/提取覆盖可能不完整，不证明原件不存在，也没有新增qualified事实。')
    result['rows'][4]['evidence_ids'].append('scoped_uploaded_original_retrieval')
    result['rows'][6]['status_zh'] = '尚无真实G3/G4/G5 pass'
    result['positive_q_original_source_appendix'] = {
        'source_evidence': ['positive_q_source_mapping', 'positive_q_complete_original_manifest', 'positive_q_independent_source_scope_review'],
        'four_complete_original_profiles': qread['four_profiles'],
        'same_q_variable_mapping': qread['q_coordinate_definition'],
        'actual_near_far_program_branch_selections': qread['two_actual_pose_report_mappings'],
        'STOP_SPRING_source_dependency': qread['STOP_SPRING_source_dependency'],
        'source_defined_independent_input_domain': qread['source_defined_independent_input_domain_not_physical_allowed_domain'],
        'lower_stop_breakpoint_is_height_branch_transition_and_source_accepts_q_up_to12': True,
        'physical_contact_preload_force_reachability_or_full_domain_qualified': False,
        'complete_original_report_and_four_exact_JSON_spans_preserved': True,
    }
    continuous = result['continuous_method_scope']
    continuous['edge189_revision_V1_scope'] = prior['continuous_method_scope']['edge189_revision_V1_scope']
    continuous['edge189_new_support_or_channel_verified_in_this_ledger'] = True
    continuous['edge189_V2_scope'] = 'Actual finite serialized source-model result only; original depth25 low child fixed material0/-Y channel, open interior, original full D and carrier B retained. This does not certify native error tubes/material, closed boundary, original depth24, V9 or full frame.'
    continuous['edge189_actual_detail'] = {
        'source_child_cumulative_depth': edge['source_child_cumulative_depth'],
        'new_splits': edge['new_splits'], 'fixed_low_child_index': edge['fixed_low_child_index'],
        'fixed_original_piece_index': edge['fixed_original_piece_index'],
        'fixed_material_channel': edge['fixed_material_channel'],
        'full_original_D_exact': edge['full_original_D_exact'],
        'original_nonzero_Vz_exact': edge['original_nonzero_Vz_exact'],
        'source_box_equals_all_six_original_B_endpoints': True,
        'source_interval_and_independent_corner_methods_agree': edge['source_interval_and_independent_corner_methods_agree'],
        'exact_corner_count': 16, 'hypothetical_tube_corner_count': 128,
        'hypothetical_tube_saved_outside_corner_count': 128,
        'hypothetical_tube_containment_in_original_AABB': False,
        'native_BREP_error_bound_certified': False,
        'three_fixed_piece_comparisons': comparisons,
        'complete_fixed_channel_piece_count': 523,
        'complete_fixed_channel_separation_codes': codes,
        'nonaxis_piece_indices': nonaxis,
        'original_independent_certificate_readback': channel['original_independent_certificate_readback'],
        'closed_boundary_retained_as_zero_volume_carrier': channel['closed_cell_boundary_retained_as_zero_volume_carrier'],
        'whole_closed_cell_disjoint_claimed': channel['whole_closed_cell_disjoint_claimed'],
        'conditional_source_model_open_interior_excluded': channel['conditional_source_model_open_interior_excluded'],
        'fixed_low_child_positive_directed_volume_exact': edge['fixed_low_child_positive_directed_volume_exact'],
        'five_actual_negative_controls': [{key: row[key] for key in ('name', 'executed', 'rejected', 'expected_rejection_mechanism', 'expected_rejection_confirmed', 'actual_exception')} for row in edge['actual_negative_controls']],
        'conditional_complete_channel_omitted_code_control': edge['conditional_complete_channel_omitted_code_control'],
        'whole_original_piece_count': edge['original_total_piece_count'],
        'unchanged_original_piece_count': edge['completely_unchanged_piece_count'],
        'carrier_with_one_added_slab_count': edge['carrier_with_one_added_slab_count'],
        'actual_elapsed_seconds': edge['elapsed_seconds'], 'actual_peak_RSS_bytes': edge['peak_RSS_bytes'],
        'all118_original_inputs_unchanged': True,
        'historical_additional_stage_debit': edge['cumulative_conservative_additional_stage_debit'],
        'new_global_remaining_volume_or_full16_pass_recalculated': False,
        'scalar_gap_is_not_a_physical_clearance': True,
        'old_spatial_probe_reclassified': False,
        'original_V6_depth24_gate_passed': False,
        'original_V9_owned_failure_reclassified': False,
        'V9_first_u_qualification': False,
        'new_full_frame_execution': False,
        'native_trim_membership_verified': False,
    }
    result['external_original_fact_scope']['scoped_uploaded_retrieval'] = {
        'evidence_id': 'scoped_uploaded_original_retrieval', 'source_filter': 'uploaded',
        'original_query_batches': retrieval['queries'], 'both_returned_result_counts': [0, 0],
        'no_underlying_file_absence_proved': True, 'new_qualified_facts': 0,
    }
    result['publication_separate_obligation']['previous_included_publication'] = prior['publication_separate_obligation']['separately_verified_R7_evidence_publication_in_this_ledger']
    result['publication_separate_obligation']['separately_verified_R7_evidence_publication_in_this_ledger'] = {
        'branch': pub['branch'], 'commit': pub['commit'], 'parent': pub['parent'],
        'new_exact_blob_count': pub['new_exact_blob_count'],
        'prior_R7_blob_count_preserved': pub['prior_R7_blob_count_preserved'],
        'all_remote_new_blob_sha_and_size_match': pub['all_remote_new_blob_sha_and_size_match'],
        'complete_source_and_original_selected_files': pub['complete_source_and_original_selected_files'],
        'individual_original_files': pub['individual_original_files'],
        'lossless_original_ZIP_members': pub['lossless_original_ZIP_members'],
        'exact_original_ZIP_bytes': pub['exact_original_ZIP_bytes'],
        'transport_parts': pub['transport_parts'],
        'first_oversized_request_failure_preserved': pub['first_oversized_request_failure_preserved'],
        'not_a_substitute_for_exact_a11': True,
    }
    storage = result['storage_observations']
    storage['observation_times_are_historical_not_live_path_presence_claims'] = True
    storage['new_live_storage_tree_census_or_partial_presence_requirement_added'] = False
    far_storage = storage['far_final_and_partial']
    far_storage['two_regular_paths_were_observed_with_equal_historical_archive_hash'] = far_storage.pop('two_current_regular_paths_with_equal_historical_archive_hash')
    far_storage['later_cache_reclamation'] = {
        'evidence_id': 'far_partial_later_cache_reclamation',
        'started_unix_ns': reclaim['started_unix_ns'], 'finished_unix_ns': reclaim['finished_unix_ns'],
        'removed_only_redundant_cache_bytes': reclaim['removed_redundant_cache_bytes'],
        'partial_absent_at_that_receipt': reclaim['partial_absent_at_receipt'],
        'final_original_unchanged': reclaim['final_original_unchanged'],
        'saved_original_identity': reclaim['exact_identity'],
        'historical_cause_explained': False,
        'historical_correspondence_unresolved': True,
        'partial_path_persistence_is_a_new_qualification_gate': False,
    }
    far_storage['evidence_ids'] += ['far_partial_later_cache_reclamation', 'far_partial_cache_reclamation_source']
    result['exact_complete_original_manifest_member_identities_rechecked_in_V2'] = checked_manifest_members
    need(len(result['rows']) == 7 and not result['all_blockers_closed'] and not result['full_continuous_G2']
         and not result['current_K1_K3_FE_qualified'] and not any(result['physical_gate_pass'].values()), 'Original overall blocker scope changed')
    need(result['numerical_original_scope_detail'] == prior['numerical_original_scope_detail'], 'Original numerical qualification scope may not be expanded')
    for name, value in catalog.items():
        need(identity(BASE / value['workspace_relative_path']) == {k: value[k] for k in ('bytes', 'sha256')}, 'An original ledger input changed during V2 read: ' + name)
    for relative, expected in checked_manifest_members.items():
        need(identity(BASE / relative) == expected, 'An original manifest member changed during V2 read')
    result['all_bound_original_source_and_report_bytes_unchanged_before_after'] = True
    result['actual_reader_seconds'] = time.monotonic() - START
    result['actual_reader_peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    original_md = (BASE / EXTRA['prior_ledger_V1_Markdown']).read_text()
    md = ['# R7 blocker closure ledger V2', '',
          '**两指定有限姿态的native执行阻断已闭合，原数值资格证据已恢复；本轮新增正q源码映射和edge189一项局部条件源模型结果。所有blocker仍未全部闭合。** 完整连续域、真实器件、当前结构/电气资格、G3–G5及精确a11推送继续保留未完成状态。', '',
          '记录时间：' + result['recorded_utc'] + '。V1及全部原报告原样保留；V2只读追加实际证据，不新增必须门、不重跑CAD、K/H或包络算法，也不把新阳性重判为原V9、V6全16或实物通过。参见 ' + link('prior_ledger_V1_JSON', catalog) + '。', '',
          '## 七行状态', '', '| 原交付行 | 本账本状态 | 已有证据与剩余边界 | 原件来源 |', '|---|---|---|---|']
    for row in result['rows']:
        brief = row['closed_scope'] + ' ' + row['limits_or_remaining'][0]
        ids = row['evidence_ids'][:3]
        if row['user_row'].startswith('2'):
            ids = ['positive_q_source_mapping', 'k1_contract', 'k3_contract']
        elif row['user_row'].startswith('3'):
            ids = ['edge189_actual_report', 'edge189_independent_actual_evidence_audit', 'original_V6_all16_readback']
        md.append('| ' + row['user_row'] + ' | **' + row['status_zh'] + '** | ' + brief.replace('|', '\\|') + ' | ' + '、'.join(link(x, catalog) for x in ids) + ' |')
    md += ['', '## 两个有限姿态究竟通过了什么',
           section(original_md, '## 两个有限姿态究竟通过了什么', '## 原数值资格：可闭合的原范围'),
           '## 正q分段与实际factory的同一变量映射', '',
           '原完整profile报告gzip为15,509 B / SHA256 `88a8993fcbf5ee41246df2459725e2784ca84c2eacb720850faf0dd6f7e9c77d`；完整403,638 B解压JSON、四个逐字节profile对象和16份完整源码均已保留。两实际factory报告的source_inputs与available_source_sha256都绑定这份原件，四个profile值的左右对称性和contact0/1末位差异没有被合并。', '',
           '| Contact | plateau结束a (mm) | corner结束b (mm) | lower_stop开始c (mm) | 左右 |',
           '|---|---:|---:|---:|---|',
           '| 0 | 0.0011145618000001356 | 0.09055728089999172 | 0.6429179606749895 | 原字段相同 |',
           '| 1 | 0.0011145618000001356 | 0.09055728089999172 | 0.64291796067499 | 原字段相同 |', '',
           '正q四支依次为 plateau `(0,a]`、rounded_corner `(a,b)`、ramp `[b,c)`、lower_stop `[c,12]`；q=0是plateau参考点。原evaluate按 `q>=c`、`q>=b`、`q<=a` 的顺序选段，并拒绝[0,12]外输入。c是跟随高度进入恒定lower_stop_height的分支转折，源码在c之后继续接受q直到12。', '',
           '实际调用链为 full_factory_stops → frozen_key_factory_adapter → product_nominal_motion → product_split_assembly → product_assembly.product_scene → native_scene；slide与左右KEY偏置逐层原样转交。每侧 `q=(12/79.75)*slide+dq`，同一q用于profile.evaluate及冻结KEY材料的Y平移；profile内部另定义 `x=pin_q−q`，四个原pin_q都是0。Near/far原dq、dx都为0且telescope allocation为None，所以STOP/SPRING实际走 endpoint → serviceable → pawl → cam.scene 的nominal源码支路；显式偏置/分配是native_scene的另一覆盖支路。', '',
           'Near的q=3.482188470506243、Far的q=9.160729490168748均在四profile的lower_stop程序支路。原高度分别为contact0 −0.01999999999999935、contact1 4.98 mm；按原表达式得到STOP的X增量，左侧为+1.16/+1.1600000000000001 mm，右侧相反。这是保存输入及源码的binary64推导，不是实际接触或可达性证明。', '',
           'SPRING生成的是半径0.43 mm、沿+X的外径公差圆柱包络：xlo=old_xmin+min(0,sign·delta)，xhi=old_xmax+max(0,sign·delta)，长度=xhi−xlo。源码要求真实恢复力，但本读回未提供实际自由长、刚度、预载、摩擦、接触保持或动态冲击证明。左右tab/flank、耦合KEY/crosshead间隙、独立三节telescope及其固定和约束都仍是源码允许输入；真实独立允许域继续未决。参见 ' + '、'.join(link(x, catalog) for x in ('positive_q_source_mapping', 'positive_q_complete_original_manifest', 'positive_q_independent_source_scope_review')) + '。', '',
           '## 原数值资格：可闭合的原范围',
           section(original_md, '## 原数值资格：可闭合的原范围', '## 连续方法：实际失败和未决继续保留'),
           '## 连续方法：保留旧失败，追加一次局部结果', '',
           '原V3完整边界模型仍为4/16；原V6条件primitive/trim模型仍为8/16。V6全局4096 split在case-028 frame1用尽，另外7个nonpass当次0新split。V9选中旧叶上界虽为0，最终新UV贡献u=0，原owned checker因VmRSS KeyError失败，driver未到first-u门，后续全16阶段未执行。新监督器真实控制资格不重判这次失败。此前原空间split探针的两子pending/excluded=0原报告保持原样，累计depth25超过原depth24。参见 ' + '、'.join(link(x, catalog) for x in ('original_V6_all16_readback', 'V9_actual', 'spatial_cost_probe')) + '。', '',
           '**新增edge189结果仅覆盖原depth25低子一个固定−Y通道的条件源模型开放内部。** 完整Line参数、full D、原nonzero Vz和原AABB的六个端点均保留。原AABB-only仍无分离码；加入exact Line slab或τ扩张slab后均得code7。固定完整523-piece通道通过，原独立reader记录523件、2个nonaxis（旧piece77和新增piece332）；另有五个指定phase的真实ClaimError负控制与删一code的coverage真实拒绝。', '',
           '独立角点法的16个exact和128个假设tube保存结果与source interval法一致，但128个假设tube角点全部在未扩张的原B之外，tube⊆B=false，native BREP误差界证书仍false。该结果支持绑定的导出Line+D条件源模型，不能把旧AABB与slab交集写成整个native误差管的保守包络。闭盒边界保留为零体积载体；非单位normal下的scalar support gap不能叫物理净间隙。高子、其他旧叶、完整16帧、原depth24、V9 u/owned、native trim及完整G2均未升级，也没有重新计算全局剩余体积。', '',
           '实际worker exit0，1.682883049 s，峰RSS315,944,960 B；118个已登记输入完整字节保持，随后另一个只读审阅核对全部159,865,741 B输入的launch/worker/post/当前双遍身份一致，没有重算support或channel。参见 ' + '、'.join(link(x, catalog) for x in ('edge189_actual_report', 'edge189_original_contract', 'edge189_external_actual_readback', 'edge189_independent_actual_evidence_audit', 'edge189_complete_manifest')) + '。', '',
           '## 外部事实、当前合同与G3–G5',
           section(original_md, '## 外部事实、当前合同与G3–G5', '## 精确a11推送是单独未完成的义务'),
           '新增定向查询仅限当前可访问uploaded原件：RAZR、RAZR specimen OLED COF FPC、RAZR原照片/标签/量测，并按提示简化为OLED及Motorola一次。两个批次均无返回结果；这不证明原件不存在，索引、提取和检索覆盖可能不全，没有增加任何qualified事实。参见 ' + link('scoped_uploaded_original_retrieval', catalog) + '。', '',
           '## 精确a11推送仍是单独未完成义务', '',
           '用户授权的精确提交 `a11b00f71231ef3516d2a79c73fa441c375ac755` 与目标分支 `evidence/full-sprint-20261027-n13-l6` 没有成功推送回执。保存的2026-10-28 23:51 UTC定向查询返回404，不构成全局不存在证明。原授权持续有效，缺的是精确对象/历史可取得并验证及目标ref的成功回执。', '',
           'V2纳入的另一路R7实际发布为 `evidence/full-sprint-20261028-r5` 的 `34764db3c8d61d6e53ea22da8caf4dc57b931463`，parent为8bb6f52…；462个新增blob和305个先前R7 blob均远端SHA/size对应，1909个selected originals包括452单文件＋1457无损ZIP成员。两段精确ZIP合16,468,003 B；先前超过16 MiB的真实请求失败另行保留。这份已核验checkpoint不替代a11，也不声称包含本账本之后尚未发布的增补。参见 ' + '、'.join(link(x, catalog) for x in ('exact_authorized_push_original_reads', 'restoration_publication', 'envelope_runtime_publication', 'native_finite_publication')) + '。', '',
           '## 存储观察：保持未决，不重判finite-pass',
           section(original_md, '## 存储观察：保持未决，不重判finite-pass', '## 已完整保存的三份原件归档'),
           '后续已另记一次有日期的冗余缓存回收：最终Far ZIP与已保存原件匹配，.partial也完整核对为相同127,370,781 B/SHA后，只回收该冗余.partial；回执当时记录partial缺席、最终ZIP未改。该新操作未解释历史rename与双路径观察的对应原因。本账本依赖历史观察与回收原回执，不要求.partial持续存在，也未重新查询整个当前存储树。参见 ' + link('far_partial_later_cache_reclamation', catalog) + '。', '',
           '## 已完整保存的三份原件归档',
           section(original_md, '## 已完整保存的三份原件归档', '## 来源身份目录'),
           '## 来源身份目录', '',
           '下表是V2实际绑定的完整来源身份；52个V1来源全部保持原字节。正q附录23个原件/输出和edge189目录22个原件另按各自完整manifest逐成员前后核对。原数值范围未扩大，原7770列独立K复算没有变成新必须门。', '',
           '| Evidence ID / 原件 | 字节 | SHA256 |', '|---|---:|---|']
    for name, value in catalog.items():
        md.append('| ' + link(name, catalog) + ' | ' + str(value['bytes']) + ' | `' + value['sha256'] + '` |')
    md += ['', '`all_blockers_closed=false`；`full_continuous_G2=false`；`current_K1_K3_FE_qualified=false`；G3/G4/G5尚无真实pass。后来新增工作应另立版本，不回写本版或原报告。', '']
    outputs = {
        'R7_BLOCKER_CLOSURE_LEDGER_V2.json': (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode(),
        'R7_BLOCKER_CLOSURE_LEDGER_V2.md': '\n'.join(md).encode(),
    }
    for name, raw in outputs.items():
        emit(OUT / name, raw)
        need((OUT / name).read_bytes() == raw, 'New ledger bytes differ on readback')
    receipt = {'schema': 'razr-r7-seven-row-ledger-v2-append-generation-receipt-v1',
               'completed': True, 'prior_V1_and_all_bound_originals_unchanged': True,
               'source': result['source_writer'], 'source_catalog_count': len(catalog),
               'complete_manifest_members_checked': len(checked_manifest_members),
               'outputs': {name: identity(OUT / name) for name in outputs},
               'new_scientific_algorithm_execution': False, 'new_required_gates': [],
               'all_blockers_closed': False, 'seconds': time.monotonic() - START,
               'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    emit(OUT / 'R7_BLOCKER_CLOSURE_LEDGER_GENERATION_RECEIPT_V2.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt))


def main():
    resource.setrlimit(resource.RLIMIT_AS, (AS, AS))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(LedgerBudgetExceeded('Registered ledger append read budget exceeded')))
    signal.alarm(WALL)
    try:
        run()
        return 0
    except BaseException as exc:
        failure = {'schema': 'razr-r7-blocker-ledger-v2-attempt1-actual-failure-v1',
                   'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc(),
                   'source': identity(Path(__file__)), 'original_inputs_or_V1_modified': False,
                   'new_CAD_or_scientific_algorithm_execution': False, 'seconds': time.monotonic() - START}
        emit(OUT / 'R7_BLOCKER_LEDGER_V2_ATTEMPT1_ACTUAL_FAILURE.json', (json.dumps(failure, indent=2) + '\n').encode())
        print(json.dumps(failure))
        return 2
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    raise SystemExit(main())
