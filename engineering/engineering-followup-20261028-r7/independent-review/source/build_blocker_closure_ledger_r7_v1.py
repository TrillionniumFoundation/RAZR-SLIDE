"""Produce a new read-only ledger against the user's seven original rows.

No prior report, scientific criterion, source, or artifact is edited.  This is
an evidence/accounting derivative, not another qualification run or a new gate.
The edge189 support/channel diagnostic is deliberately not admitted in V1.
"""
from pathlib import Path
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
LIMIT_SECONDS = 30
LIMIT_AS = 256 * 2**20
REFS = {
    'native_scope': 'r7-native/R7_ACTUAL_NATIVE80_AND_TWO_FINITE_POSES_SCOPE_V1.json',
    'native80_audit': 'r7-audit/native-stage-v4-review/R7_NATIVE80_ACTUAL_PRODUCER_READER_INDEPENDENT_EVIDENCE_READBACK.json',
    'runtime_audit': 'r7-audit/native-stage-v4-review/R7_ACTUAL_RUNTIME_QUALIFICATION_INDEPENDENT_FULL_READBACK_V2.json',
    'near_audit': 'r7-audit/full-factory-review/R7_NEAR_ACTUAL_FULL_FACTORY_INDEPENDENT_EVIDENCE_READBACK.json',
    'far_audit': 'r7-audit/full-factory-review/R7_FAR_ACTUAL_FULL_FACTORY_INDEPENDENT_EVIDENCE_READBACK.json',
    'k1_contract': 'r7-recovery/k3/source/k3full/KEY_FORWARD_LOOP_V1_CONTRACT.json',
    'k3_contract': 'r7-recovery/k3/source/k3full/PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json',
    'k3_source': 'r7-recovery/k3/source/k3full/panel_key_travel_stops_v1.py',
    'full_factory_states': 'r7-recovery/k3/source/k3full/full_stop_states.py',
    's4_motion_source': 'r7-native/genuine-s4-worktree-v3/integration/product_assembly.py',
    's4_contact_profile_source': 'r7-native/genuine-s4-worktree-v3/integration/cam_contact_profile.py',
    's4_source_contract': 'r7-native/R7_SETUP_INSTALL_ONLY_CONTRACT_V3.json',
    'numeric_scope': 'razr-current/engineering/engineering-followup-20261028-r5/numerics/R5_ORIGINAL_NUMERIC_QUALIFICATION_SCOPE.json',
    'numeric_scope_independent_review': 'razr-current/engineering/engineering-followup-20261028-r5/review/numeric-scope/R5_INDEPENDENT_NUMERIC_SCOPE_REVIEW.json',
    'numeric_panel_five': 'r7-recovery/numeric/original-probe-qualification/panel/N13-v3-independent-readback.json',
    'numeric_frame_five': 'r7-recovery/numeric/original-probe-qualification/frame/FRAME_INDEPENDENT_READBACK.json',
    'numeric_H_restore': 'r7-recovery/numeric/independent-audit/H_EXECUTED_READBACK_SUMMARY.json',
    'numeric_restore_call_chain': 'r7-recovery/numeric/independent-audit/ORIGINAL_H_RESTORE_CALL_CHAIN.json',
    'numeric_original_method_review': 'r7-recovery/numeric/independent-audit/NUMERIC_METHOD_REVIEW_V2.json',
    'numeric_four_loads': 'r7-recovery/numeric/actual-results/panel-four-loads/FOUR_LOAD_REPORT.json',
    'numeric_linear_seed': 'r7-recovery/numeric/independent-audit/LINEAR_SEED_EXECUTED_SUMMARY.json',
    'external_original_contract_readback': 'r7-audit/external-status/R7_EXTERNAL_DEPENDENCIES_FROM_RECOVERED_ORIGINALS_V2.json',
    'external_intake_contract': 'razr-current/engineering/engineering-followup-20261028-r5/real-sources/intake/R3_SAME_SPECIMEN_INTAKE_CONTRACT.json',
    'external_field_plan': 'razr-current/engineering/engineering-followup-20261028-r5/real-sources/intake/R5_FIELD_COLLECTION_PLAN.json',
    'original_V6_all16_readback': 'r7-publication/R7_ORIGINAL_V6_ALL16_STATUS_READBACK_V1.json',
    'original_raw_and_conditional_method_scope': 'razr-current/engineering/engineering-followup-20261028-r5/README.md',
    'V9_actual': 'r7-envelope/local-v9/R7E_V9_LOCAL_LAUNCH_RECEIPT_V2.json',
    'V9_source_lock': 'r7-envelope/source-v9/R7E_PORTABLE_SOURCE_LOCK_V9.json',
    'V9_meaning': 'r7-envelope/v9-meaning-review-v1/R7E_V9_PROOF_AND_SPATIAL_CONTINUATION_READBACK_V1.json',
    'correlation_diagnosis': 'r7-envelope/correlation-diagnostic-v1/attempt-1/R7E_V9_SAVED_PREFIX_PLANE_PREIMAGE_DIAGNOSIS_V1.json',
    'wire_diagnosis': 'r7-envelope/wire-meaning-diagnostic-v1/attempt-1-v2/R7E_SAVED_V9_WIRE_MEANING_DIAGNOSIS_V2.json',
    'spatial_cost_probe': 'r7-envelope/spatial-pilot-v1/attempt-1/R7E_ONE_SPLIT_ORIGINAL_SPATIAL_COST_PROBE_V1.json',
    'edge189_metadata_only': 'r7-envelope/edge189-source-diagnostic-v1/SOURCE_METADATA_READBACK_V1.json',
    'new_supervisor_control_audit': 'r7-audit/supervisor-review/R7_MATH_SUPERVISOR_V2_ACTUAL_CONTROLS_INDEPENDENT_QUALIFICATION_V2.json',
    'new_supervisor_entry_appendix': 'r7-audit/supervisor-review/R7_SUPERVISOR_V2_COMPLETE_ENTRY_FIXTURE_INDEPENDENT_APPENDIX.json',
    'vtk_cleanup_correspondence': 'r7-audit/runtime-cleanup-correspondence/R7_EXISTING_CLEANUP_CORRESPONDENCE_ACTUAL_V1.json',
    'near_storage_migration': 'r7-publication/R7_NEAR_ENGINEERING_ARCHIVE_MIGRATION_V1.json',
    'near_storage_failed_read': 'r7-audit/full-factory-review/R7_NEAR_MIGRATION_CURRENT_READ_ATTEMPT1_ACTUAL_FAILURE.json',
    'near_storage_later_read': 'r7-audit/full-factory-review/R7_NEAR_ENGINEERING_MIGRATION_CURRENT_STATE_READBACK_V2.json',
    'native_storage_addendum': 'r7-native/R7_NATIVE_SCOPE_STORAGE_OBSERVATION_ADDENDUM_V2.json',
    'far_two_paths_observation': 'r7-audit/storage-observation/R7_FAR_ARCHIVE_TWO_PATHS_CURRENT_READBACK_V1.json',
    'native80_saved': 'r7-deliverables/R7_NATIVE80_COMPLETE_PRESERVATION_V1.json',
    'near_saved': 'r7-deliverables/R7_NEAR_COMPLETE_PRESERVATION_V1.json',
    'far_saved': 'r7-deliverables/R7_FAR_COMPLETE_PRESERVATION_V1.json',
    'native80_archive_actual': 'r7-audit/native80-archive/R7_NATIVE80_COMPLETE_ARCHIVE_ACTUAL_V3.json',
    'near_archive_actual': 'r7-audit/near-full-archive/R7_NEAR_FULL_ORIGINAL_ARCHIVE_ACTUAL_V1.json',
    'far_archive_actual': 'r7-audit/far-full-archive/R7_FAR_FULL_ORIGINAL_ARCHIVE_ACTUAL_V3.json',
    'native80_zip_cache_migration': 'r7-publication/R7_SAVED_NATIVE80_ZIP_CACHE_RECLAIM_V1.json',
    'original_resource_gate_scope': 'r7-audit/full-factory-review/R7_ORIGINAL_CLOSEOUT_DISK_GATE_SCOPE_READBACK_V1.json',
    'exact_authorized_push_original_reads': 'r7-audit/blocker-ledger/R7_EXACT_AUTHORIZED_PUSH_ORIGINAL_READ_OBSERVATIONS_V1.json',
    'restoration_publication': 'r7-publication/R7_RECOVERY_REMOTE_PUBLICATION_VERIFIED_V1.json',
    'envelope_runtime_publication': 'r7-publication/R7_ENVELOPE_RUNTIME_REMOTE_PUBLICATION_VERIFIED_V1.json',
}


class LedgerBudgetExceeded(BaseException):
    pass


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    need(stat.S_ISREG(path.lstat().st_mode), 'Ledger input must be a regular file: ' + str(path))
    h = hashlib.sha256()
    count = 0
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(2**20), b''):
            h.update(data)
            count += len(data)
    need(count == path.stat().st_size, 'Ledger input length changed during read')
    return {'bytes': count, 'sha256': h.hexdigest()}


def read(name):
    return json.loads((BASE / REFS[name]).read_bytes())


def save(path, data):
    need(not path.exists(), 'New immutable ledger artifact required')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def link(name):
    return '[' + name + '](sandbox:' + str(BASE / REFS[name]) + ')'


def build():
    evidence = {name: {'workspace_relative_path': rel, **identity(BASE / rel)} for name, rel in REFS.items()}
    native = read('native_scope')
    near, far = read('near_audit'), read('far_audit')
    native80, runtime = read('native80_audit'), read('runtime_audit')
    number = read('numeric_scope')
    panel, frame, H = read('numeric_panel_five'), read('numeric_frame_five'), read('numeric_H_restore')
    external = read('external_original_contract_readback')
    v6, v9, meaning = read('original_V6_all16_readback'), read('V9_actual'), read('V9_meaning')
    correlation, wire, spatial = read('correlation_diagnosis'), read('wire_diagnosis'), read('spatial_cost_probe')
    k1, k3 = read('k1_contract')['design_contract'], read('k3_contract')['design_contract']
    source_contract = read('s4_source_contract')
    for name in ('s4_motion_source', 's4_contact_profile_source'):
        relative = str((BASE / REFS[name]).relative_to(BASE / 'r7-native/genuine-s4-worktree-v3'))
        need(identity(BASE / REFS[name]) == source_contract['expected_sources'][relative], 'Actual S4 source binding differs')
    need(native['finite_pose_count'] == 2 and not native['all_blockers_closed'], 'Expected completed finite native scope required')
    for pose in (near, far):
        need(pose['evidence_readback_pass'] and pose['finite_state_clear'], 'Actual complete finite pose readback missing')
        need(pose['original_complete_pair_execution'] and not pose['full_continuous_G2'], 'Finite/continuous scope changed')
    need(native80['evidence_readback_pass'] and native80['native_area_bit_inequality_count'] == 80, 'Original native80 scope differs')
    need(runtime['runtime_payload_readback_pass'] and not runtime['review_pass_with_no_unresolved_discrepancies'], 'Runtime cleanup discrepancy must remain')
    need(panel['original_five_qualification_verified'] and frame['original_five_qualification_verified'], 'Original five-probe qualification absent')
    need(panel['original_five_ratios'] == number['panel_original_five_residuals'], 'Original panel residuals differ')
    need(frame['original_five_ratios'] == number['frame_original_five_residuals'], 'Original frame residuals differ')
    need(all(value <= 1e-7 for value in panel['original_five_ratios'] + frame['original_five_ratios']), 'An original reported probe exceeds its unchanged threshold')
    numeric_original_records = {}
    for name, row in number['source_records'].items():
        path = BASE / 'r7-recovery/numeric' / row['archive_relative_path']
        actual = identity(path)
        need(actual == {key: row[key] for key in ('bytes', 'sha256')}, 'Recovered complete original numeric report differs: ' + name)
        numeric_original_records[name] = {'workspace_relative_path': str(path.relative_to(BASE)), **actual}
    need(H['both_body_complete_H_accepted'] and H['original_combined_ExactResponseCache_restore_passed'], 'Historical original H/restore qualification absent')
    need(not number['independent_all_7770_column_K_products_executed'] and not number['current_K1_K3_geometry_FE_qualified'], 'Unsupported numerical scope upgrade')
    need(external['original_fact_requirement_count'] == 228 and external['recovered_admitted_fact_count'] == 0, 'Original external fact status differs')
    need(all(not external['physical_gate_pass'][gate] for gate in ('G3', 'G4', 'G5')), 'Physical gate status changed')
    need(v6['frame_count'] == 16 and v6['prior_conditional_pass_count'] == 8, 'Original full16 conditional scope differs')
    need(not v9['pipeline_completed'] and not v9['formal_owned_single_verification_passed'], 'V9 failure must remain failed')
    need(v9['actual_independent_saved_planar_u'] == 0 and not v9['original_first_u_gate_reached_by_driver'], 'Original first-u status differs')
    need(spatial['finite_cost_diagnostic_only'] and not spatial['original_V6_depth_gate_passed'], 'Depth25 cost probe is not an original depth24 pass')
    need(not wire['native_trimmed_region_membership_proved'] and not correlation['new_scientific_qualification'], 'Diagnostic scope upgraded')
    storage_near, storage_far = read('near_storage_later_read'), read('far_two_paths_observation')
    need(storage_near['historical_migration_end_state_to_current_membership_correspondence_unresolved'], 'Near storage correspondence must remain unresolved')
    need(storage_far['both_paths_currently_observed'] and not storage_far['deletion_then_reappearance_proved'], 'Current far two-path observation misclassified')
    saved = {}
    for name in ('native80', 'near', 'far'):
        receipt, actual = read(name + '_saved'), read(name + '_archive_actual')
        need(receipt['saved_file']['status'] == 'succeeded', 'Complete evidence archive not durably saved')
        need({'bytes': receipt['bytes'], 'sha256': receipt['sha256']} == actual['archive']['identity'], 'Saved archive bytes differ from complete archive readback')
        saved[name] = {'filename': receipt['saved_file']['file_name'], 'bytes': receipt['bytes'], 'sha256': receipt['sha256'],
                       'library_file_id': receipt['saved_file']['library_file_id'],
                       'version': receipt['saved_file']['current_version_number'],
                       'complete_ZIP_members': actual['exact_archive_members'],
                       'all_member_CRC_SHA_verified': actual['complete_member_set_CRC_SHA256_verified'],
                       'save_receipt_evidence': name + '_saved', 'archive_completion_evidence': name + '_archive_actual'}
    rows = [
        {
            'user_row': '1．复现中途几何见证', 'owner_role': '机械/CAD、独立几何验证',
            'original_acceptance': 'factory 与原 whole-endpoint 材料身份可对应；直接 Common、独立读回和全对记录一致',
            'status': 'closed_for_two_finite_current_candidate_poses', 'status_zh': '两指定姿态限域闭合',
            'closed_scope': '真实 S4 来源闭包与冻结 K1/KEY、K3/panel 候选下，near/far 都重新完成完整 factory、独立 STEP reader、原完整验证器、原工程导出与逐成员保存。',
            'actual_evidence': ['每姿态154体；每个 producer/reader 各11781完整体对；每个 reader 154个STEP及12个早期门。',
                                'Near 每进程777次 native_common＋11004条 positive_axis_gap；Far 为747＋11034。11781不是直接Common调用次数。',
                                '两姿态左右 panel/KEY 显式direct Common均为0；positive/evaluation/mismatch均为0。原whole输入和4个有限材料/姿态映射另有native80独立读回。'],
            'limits_or_remaining': ['这是当前修复候选的两个有限姿态；不是未修改S4所有材料不变、第二种独立CAD内核、完整连续G2或实物通过。',
                                    '旧F1真实干涉和V5失败不由新候选结果重判；其恢复原件和后续修复身份分别保留。'],
            'evidence_ids': ['native_scope', 'native80_audit', 'near_audit', 'far_audit', 'native80_saved', 'near_saved', 'far_saved'],
        },
        {
            'user_row': '2．完成结构与允许域定义', 'owner_role': '机构、接触/运动学',
            'original_acceptance': '新命名源码、切除材料、剩余壁厚、功能接触面和完整域证据；行程限制有实际机构支持',
            'status': 'finite_repair_evidence_closed_whole_domain_and_physical_limits_open', 'status_zh': '有限修复证据成立；完整域与实物限位未闭合',
            'closed_scope': 'K1 key_forward_loop_v1 的切除/加料合同及K3 panel_key_travel_stops_v1的加料合同原样保留，连接、原功能面和两中途姿态已取得本轮实际native证据。',
            'actual_evidence': ['K3当前新增材料4.624559999999989 mm³；native80的80原核心、8控制、4有限映射、80新增材料核心及396保存BREP完成独立读回。',
                                'S4源码保留每侧q=cam.K*slide+dq、独立tab/flank、耦合crosshead/KEY间隙约束和左右独立telescope allocation。',
                                'ContactProfile的正q定义保留plateau、rounded_corner、ramp、lower_stop四支；STOP随height差平移，SPRING OD tolerance envelope按同一差值改变范围。此为源码定义，不是实物恢复力证明。'],
            'limits_or_remaining': ['冻结K1合同的[0,12] mm只是声明的ContactProfile域，原slot未被候选裁短；模型允许输入不能冒充真实全独立运动域。',
                                    '0.38×0.36 mm的声明局部腿截面不是整个KEY最小剩余壁厚、强度或制造放行；真实载荷、预紧、材料/工艺、公差、行程限位和装配/维修路径仍须原验收证据。',
                                    '两姿态不覆盖全部STOW/OPEN、左右独立offset、STOP/SPRING、telescope、返回与重锁域；不靠缩行程替代实际机构。'],
            'evidence_ids': ['k1_contract', 'k3_contract', 'k3_source', 'full_factory_states', 's4_motion_source', 's4_contact_profile_source', 'native80_audit', 'near_audit', 'far_audit'],
        },
        {
            'user_row': '3．修复连续包络方法', 'owner_role': '几何算法、验证',
            'original_acceptance': '保守包含、有效拓扑、有向体积和原判据同时满足；逐项保留真实失败和未决',
            'status': 'continuous_method_unresolved', 'status_zh': '连续方法未决',
            'closed_scope': '原反例/原D/原判据继续保留，恢复V6全16记录；本轮V9和相关性、wire含义、一次split成本诊断都有新命名原件与实际读回。新owned监督器另有真实控制资格。',
            'actual_evidence': ['原完整边界模型V3仍4/16；原V6条件primitive/trim模型8/16，8个nonpass不被本轮局部诊断销项。',
                                'V9选中旧叶的最终上界为0，但最终新UV贡献u=0；原owned checker阶段因VmRSS KeyError失败，driver未到达first-u门，后续全16阶段未执行。',
                                '相关性诊断读取81个保存prefix/972通道；wire诊断不提供native filling证明。单次原空间split的两子仍pending、excluded=0，累计depth25超过原V6 depth24，明确仅为成本诊断。'],
            'limits_or_remaining': ['需要在原语义及完整D下建立仍缺的保守包含/native材料成员与连续域证明；条件模型、单叶上界或源码例点不能替代完整16帧验收。',
                                    '原V6在case-028 frame1耗尽全局4096 split，另外7个nonpass当次0新split；不能把修某个case局部写为全16闭合。',
                                    'edge189在V1仅纳入原件metadata读取，未纳入新的support/channel实际结果；不声称已验证。'],
            'evidence_ids': ['original_raw_and_conditional_method_scope', 'original_V6_all16_readback', 'V9_actual', 'V9_source_lock', 'V9_meaning', 'correlation_diagnosis', 'wire_diagnosis', 'spatial_cost_probe', 'edge189_metadata_only', 'new_supervisor_control_audit', 'new_supervisor_entry_appendix'],
        },
        {
            'user_row': '并行：恢复原数值资格', 'owner_role': '数值、计算资源',
            'original_acceptance': '五个原 float64 残差均满足1e-7，保留全场和修正过程；随后验证frame/H/restore',
            'status': 'closed_for_original_historical_numeric_contract', 'status_zh': '原数值资格范围可闭合',
            'closed_scope': '恢复并按精确身份读回原N15科学证据：panel与frame各原五探针5/5、原H、五个有序已保存动作的restore及四载荷/linear seed原资格。此轮是原件恢复与读回，不是再跑求解器。',
            'actual_evidence': ['原panel最大float64残差9.983337773558199e-8，frame最大5.659897926075834e-9，十项均不超过原1e-7。原K/b/C/固定自由DOF/方向身份及全场、残差和修正记录保留。',
                                '原两体各3885列H生产记录与全局检查保留；原combined ExactResponseCache restore的5次response调用通过，最大相对误差1.1659935073707673e-8。'],
            'limits_or_remaining': ['不授予任意RHS逆算子、有限QP checkpoint/resume、当前K1/K3 FE或当前真实结构资格；restore只接收五个有序SHA绑定的真实已保存完整动作，未知RHS被拒绝。',
                                    '未执行独立全部7770列K乘积，也未保留每个成功H列的全部全场。这些是原证据范围限制，不新增为本表数值行必须重算的blocker。当前K1/K3 FE另归第6行。'],
            'evidence_ids': ['numeric_scope', 'numeric_scope_independent_review', 'numeric_panel_five', 'numeric_frame_five', 'numeric_H_restore', 'numeric_restore_call_chain', 'numeric_original_method_review', 'numeric_four_loads', 'numeric_linear_seed'],
        },
        {
            'user_row': '并行：取得真实器件资料', 'owner_role': '现场计量、显示、柔性互连、电气',
            'original_acceptance': '同一specimen的10/7/12原件；原照片/标签、PN/revision、尺寸和不确定度、方向、端子来源及原机功能可追溯',
            'status': 'external_original_facts_missing', 'status_zh': '仍缺外部原始事实',
            'closed_scope': '原接收合同、现场收集计划和缺项定义已恢复并核对，不以通用型号资料替代指定样件。',
            'actual_evidence': ['原228个事实要求保持10身份＋77部件字段＋120接口字段＋21供应商/所选revision字段；其中207项要求同一样件，21项要求所选PN/revision。',
                                '本轮新增可接纳的真实测量/器件事实为0；G3/G4/G5新增实物pass为0。228是原事实要求计数，不是新增的全局blocker总数。'],
            'limits_or_remaining': ['仍需同一样件10身份、7部件、12接口对应的照片/标签、原始尺寸与不确定度、方向、terminal来源和原机功能；真实OLED/COF/FPC、连接器、材料/工艺revision来源不能从通用资料推定。'],
            'evidence_ids': ['external_original_contract_readback', 'external_intake_contract', 'external_field_plan'],
        },
        {
            'user_row': '随后：冻结当前结构、电气和试验合同', 'owner_role': '结构、工艺、电气、测试/质量',
            'original_acceptance': '当前几何FE/公差、OEM互连、完整叠层及有来源G3–G5阈值；全域最坏工况、原生电气、采样校准、计划与版本绑定',
            'status': 'current_candidate_qualification_contract_not_complete', 'status_zh': '当前资格合同尚不可完整冻结',
            'closed_scope': '原S4绑定空模板和工程合同原件已恢复；本轮finite几何与原数值资格的来源清楚，尚未把空字段写成测量或批准。',
            'actual_evidence': ['原合同列154个名义材料赋值与13类需来源的载荷；新K1/K3几何需要新的网格/材料/接触/公差绑定。',
                                'G3仍有14项无来源阈值与5项采样要求；G4有9功能协议、14通道待真实身份/限值；G5有8指标、4暴露范围待来源。'],
            'limits_or_remaining': ['真实材料、工艺、预紧、摩擦/接触、相关公差、完整OEM pin/stackup/原生电气和同候选版本绑定的阈值、校准、采样/相位计划仍不完整。',
                                    '原五探针/旧H通过不能转移为当前K1/K3强度、最坏工况或产品FE pass；仍需原合同规定的全域和最坏情况证据。'],
            'evidence_ids': ['external_original_contract_readback', 'external_intake_contract', 'numeric_scope', 'k1_contract', 'k3_contract'],
        },
        {
            'user_row': '最后：逐级实物验收', 'owner_role': '样机、系统测试、质量',
            'original_acceptance': '同候选同样件依次G3→G4→G5；每一级真实pass支持下一阶段；缺测、失效、维修和换件分别保留',
            'status': 'physical_gates_not_passed', 'status_zh': '真实G3/G4/G5均未通过',
            'closed_scope': '原顺序和同样件/同候选/revision约束保留，尚没有本轮真实实物pass。',
            'actual_evidence': ['G3=false、G4=false、G5=false；前级真实pass完成后才允许进入后级，换件/维修及assembly revision变化不继承旧pass。'],
            'limits_or_remaining': ['需要真实样件、完整原始采样/校准/相位记录和原合同阈值逐级执行；缺测、失效、维修与换件不能相互覆盖。有限CAD、条件包络或数值残差不能代替实物验收。'],
            'evidence_ids': ['external_original_contract_readback', 'external_intake_contract', 'external_field_plan'],
        },
    ]
    publication = read('envelope_runtime_publication')
    exact_reads = read('exact_authorized_push_original_reads')
    result = {
        'schema': 'razr-r7-user-seven-row-blocker-closure-ledger-v1',
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'read_only_accounting_derivative_not_a_replacement_report': True,
        'source_writer': {'workspace_relative_path': str(Path(__file__).resolve().relative_to(BASE)), **identity(Path(__file__))},
        'resource_limits': {'wall_seconds': LIMIT_SECONDS, 'address_space_bytes': LIMIT_AS},
        'original_user_acceptance_controls': True, 'new_mandatory_gates_added': [],
        'new_CAD_solver_K_product_or_H_action_executed': False,
        'original_reports_or_criteria_modified': False,
        'functional_source_commit': 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
        'current_named_KEY_candidate': 'key_forward_loop_v1', 'current_named_panel_candidate': 'panel_key_travel_stops_v1',
        'rows': rows,
        'numerical_original_scope_detail': {
            'original_float64_residual_threshold': number['original_float64_residual_threshold'],
            'panel_five_ratios': panel['original_five_ratios'], 'frame_five_ratios': frame['original_five_ratios'],
            'all_original_ten_reported_float64_residuals_within_original_gate': True,
            'same_original_input_identity_and_fields_are_historical_verified_evidence_not_reexecuted_here': True,
            'full_original_eight_report_bytes_rechecked': numeric_original_records,
            'H_column_producer_scope': number['historical_H_column_producer_scope'],
            'original_combined_H_checks': number['historical_combined_H_checks'],
            'restore': number['historical_restore'], 'restore_callback_scope': number['historical_restore_callback_scope'],
            'four_load_residuals': number['historical_four_load_residuals'],
            'original_ten_probe_fields_and_corrections_preserved': number['original_ten_probe_full_fields_and_corrections_preserved'],
            'independent_all_7770_column_K_products_executed': False,
            'all_successful_H_column_full_fields_historically_retained': False,
            'independent_all_7770_recomputation_added_as_a_new_required_gate': False,
            'arbitrary_RHS_inverse_or_finite_QP_resume_qualified': False,
            'current_K1_K3_FE_qualified': False,
        },
        'native80_detail': {
            'original_core_Common_count': len(native80['original_80_witness_ids']),
            'saved_BREP_readback_count': native80['independent_native_saved_BREP_readback_count'],
            'reader_comparison_count': native80['reader_comparison_count'],
            'native_area_binary64_inequality_count': native80['native_area_bit_inequality_count'],
            'maximum_native_area_difference_mm2': native80['maximum_observed_native_area_difference_mm2'],
            'all_native_areas_binary64_equal': native80['all_native_areas_binary64_equal'],
            'new_physical_area_threshold_introduced': False,
            'reader_is_same_kernel_separate_process': True,
            'whole_current_exact_native_trim_membership_verified': False,
        },
        'finite_pose_scope': {pose: native['finite_poses'][pose] for pose in ('near', 'far')},
        'continuous_method_scope': {
            'original_V3_complete_boundary_raw_pass_count_of_16': 4,
            'original_V6_conditional_pass_count_of_16': v6['prior_conditional_pass_count'],
            'original_V6_nonpass_count_of_16': v6['prior_conditional_nonpass_count'],
            'original_V6_global_split_limit': v6['original_capacity']['maximum_splits'],
            'V9_pipeline_completed': v9['pipeline_completed'],
            'V9_owned_verification_passed': v9['formal_owned_single_verification_passed'],
            'V9_final_saved_planar_u': v9['actual_independent_saved_planar_u'],
            'V9_first_u_gate_reached': v9['original_first_u_gate_reached_by_driver'],
            'V9_new_full16_qualification_claimed': False,
            'V9_selected_leaf_zero_is_not_full_frame_zero': True,
            'correlation_saved_prefix_count': correlation['actual_saved_failed_prefix_node_count'],
            'wire_native_filling_membership_proved': wire['native_trimmed_region_membership_proved'],
            'one_spatial_split_cumulative_original_depth': spatial['cumulative_depth_from_original_V6_root'],
            'one_spatial_split_original_depth24_gate_passed': spatial['original_V6_depth_gate_passed'],
            'one_spatial_split_excluded_positive_volume_exact': spatial['local_excluded_open_volume_exact'],
            'one_spatial_split_pending_is_not_native_interference': spatial['pending_is_not_evidence_of_native_interference'],
            'edge189_revision_V1_scope': 'Original source metadata only; new support/channel actual result is not admitted in this ledger version.',
            'edge189_new_support_or_channel_verified_in_this_ledger': False,
        },
        'external_original_fact_scope': {
            'original_requirement_count': 228,
            'categories': external['original_fact_requirements_by_category'],
            'scope_counts': external['original_fact_requirements_by_scope'],
            'admitted_facts': 0, 'new_physical_measurements': 0,
            'required_original_identity_part_interface_counts': [10, 7, 12],
            'this_is_not_a_new_global_blocker_count': True,
        },
        'publication_separate_obligation': {
            'requested_commit': exact_reads['requested_commit'], 'requested_branch': exact_reads['requested_branch'],
            'successful_exact_authorized_push_completed': False,
            'dated_original_query_observations': [{'name': x['name'], 'observed_at': x['observed_at'],
                                                   'status': x['result']['structuredContent']['error_data']['status']}
                                                  for x in exact_reads['original_tool_response_values_preserved']],
            '404_is_proof_of_global_absence': False,
            'separately_verified_R7_evidence_publication_in_this_ledger': {
                'branch': publication['branch'], 'commit': publication['commit'], 'parent': publication['parent'],
                'new_files_checked': publication['new_files_checked'],
                'all_remote_Git_blob_hashes_and_byte_counts_match': publication['all_remote_Git_blob_hashes_and_byte_counts_match']},
            'new_commit_may_substitute_for_a11': False,
            'existing_user_push_authorization_needs_to_be_requested_again': False,
            'remaining': 'Need the exact original Git object/history to be accessible and verified, then a successful push/readback of that exact object at the authorized ref; no successful receipt is present in this ledger.',
        },
        'storage_observations': {
            'classification': 'Two families: qualification scratch correspondence and archived-storage/path correspondence. Three dated observations are retained.',
            'vtk': {'evidence_ids': ['runtime_audit', 'vtk_cleanup_correspondence'],
                    'original_43_per_wheel_removed_flags_recorded_true': True,
                    'later_byte_identical_vtk_wheel_present': True,
                    'field_is_an_instantaneous_exists_check_not_a_final_scratch_inventory': True,
                    'cause_proved': False, 'historical_to_current_correspondence_resolved': False},
            'near_expansion': {'evidence_ids': ['near_storage_migration', 'near_storage_failed_read', 'near_storage_later_read', 'native_storage_addendum'],
                               'historical_migration_end_state_retained_members': 2,
                               'later_observed_members': storage_near['current_member_count'],
                               'later_observed_bytes': storage_near['current_bytes'],
                               'historically_removed_but_later_observed': storage_near['historical_removed_but_current_observed_count'],
                               'all_later_observed_hashes_match_original_seal': True,
                               'current_expansion_complete_at_later_observation': False,
                               'complete_archive_bytes_still_match_original_verified_archive': True,
                               'cause_proved': False, 'historical_end_state_correspondence_resolved': False},
            'far_final_and_partial': {'evidence_ids': ['far_two_paths_observation'],
                                      'two_current_regular_paths_with_equal_historical_archive_hash': True,
                                      'distinct_inodes_and_one_link_each': True,
                                      'original_builder_uses_partial_rename_TARGET': True,
                                      'original_success_receipt_recorded_post_rename_partial_absence': False,
                                      'deletion_then_reappearance_proved': False,
                                      'cause_proved': False},
            'finite_scientific_pass_or_original_archive_content_pass_reclassified': False,
            'no_unresolved_discrepancies_claimed': False,
            'new_scientific_gate_added': False,
        },
        'complete_evidence_archives_saved': saved,
        'all_seven_user_rows_fully_closed': False,
        'full_continuous_G2': False, 'current_K1_K3_FE_qualified': False,
        'physical_gate_pass': {'G3': False, 'G4': False, 'G5': False},
        'all_blockers_closed': False,
        'evidence_catalog': evidence,
    }
    for name, item in evidence.items():
        need(identity(BASE / item['workspace_relative_path']) == {k: item[k] for k in ('bytes', 'sha256')}, 'Original ledger input changed: ' + name)
    result['all_bound_original_source_and_report_bytes_unchanged_before_after'] = True
    result['actual_reader_seconds'] = time.monotonic() - START
    result['actual_reader_peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    need(result['actual_reader_seconds'] <= LIMIT_SECONDS, 'Ledger read exceeded its budget')
    json_bytes = (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    json_path = OUT / 'R7_BLOCKER_CLOSURE_LEDGER_V1.json'
    md = [
        '# R7 blocker closure ledger V1', '',
        '**本轮已关闭两指定有限姿态的 native 执行阻断，并恢复原数值资格证据；所有 blocker 尚未全部闭合。** 当前 K1/K3 完整连续域、真实器件、当前结构/电气资格、G3–G5 以及精确 a11 推送仍不能写为通过。', '',
        '本文件是按用户原七行验收整理的新账本，不替代或改写任何原报告。本轮未在此运行 CAD、K 乘积、H action 或求解器，也没有新增必须验收门。冻结源码合同的登记时状态与后来实际报告分别保留。', '',
        '记录时间：' + result['recorded_utc'] + '。Edge189 在本版本只引用原件 metadata；新 support/channel 结果尚未纳入，后续只能另立增补版本。', '',
        '## 七行状态', '',
        '| 原交付行 | 本账本状态 | 已有证据与剩余边界 | 原件来源 |',
        '|---|---|---|---|',
    ]
    for row in rows:
        brief = row['closed_scope'] + ' ' + row['limits_or_remaining'][0]
        md.append('| ' + row['user_row'] + ' | **' + row['status_zh'] + '** | ' + brief.replace('|', '\\|') + ' | ' + '、'.join(link(x) for x in row['evidence_ids'][:3]) + ' |')
    md += ['', '## 两个有限姿态究竟通过了什么', '',
           '来源是 S4 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`，候选为 `key_forward_loop_v1` 与 `panel_key_travel_stops_v1`。Near slide 为 23.142044210239405 mm、qL=qR=3.482188470506243 mm；Far slide 为 60.880681403413135 mm、qL=qR=9.160729490168748 mm。每个姿态每个进程都有154体、11781完整体对；每个 reader 都有154个STEP和12个早期门。', '',
           '| 姿态 | native_common / 进程 | positive_axis_gap / 进程 | 左右显式 panel/KEY Common | 原四阶段 |',
           '|---|---:|---:|---|---|',
           '| Near | 777 | 11004 | 均0 mm³ | factory、reader、原完整验证器、原工程导出均完成 |',
           '| Far | 747 | 11034 | 均0 mm³ | factory、reader、原完整验证器、原工程导出均完成 |', '',
           '11781 是体对记录数，不是直接 Common 次数。独立 reader 使用相同 OCP 内核的另一进程，不声称第二种 CAD 内核。Native80 保留80原核心、8控制、4有限映射、80新增材料核心及396个保存BREP；728项比较中80项存在binary64面积差，最大2.842170943040401e-14 mm²，没有新增物理面积阈值。参见 ' + '、'.join(link(x) for x in ('native_scope', 'native80_audit', 'near_audit', 'far_audit')) + '。', '',
           'K1切除/加料和K3加料、有限连接与原功能面证据已保留；K3当前增加4.624559999999989 mm³。声明的局部0.38×0.36 mm腿截面与0.1368 mm²面积不代表整个KEY最小壁厚或强度资格。[0,12] mm是源码ContactProfile域，实际独立运动域、恢复力、预紧及实物行程不能因此认定。参见 ' + '、'.join(link(x) for x in ('k1_contract', 'k3_contract', 's4_motion_source', 's4_contact_profile_source')) + '。', '',
           '## 原数值资格：可闭合的原范围', '',
           '原 N15 科学证据已恢复；本账本重新核对了所引用八份原 JSON 的完整字节与原登记 SHA。原 panel 与 frame 的五个 float64 残差如下，原判据仍为1e-7；这里没有重算 K 残差或重做因式分解。', '',
           '| 原探针索引 | Panel | Frame |', '|---|---:|---:|']
    for index, (p, f) in enumerate(zip(panel['original_five_ratios'], frame['original_five_ratios'])):
        md.append(f'| {index} | `{p!r}` | `{f!r}` |')
    md += ['', '原两体各3885列 H 的生产记录和全局检查、原组合H的五次已保存动作restore，以及四载荷/linear seed资格按原合同保留。Restore 最大相对误差为1.1659935073707673e-8；回调仅接收五个有序SHA绑定的真实完整动作，未知RHS被拒绝。原十探针全场、残差和修正记录保留。参见 ' + '、'.join(link(x) for x in ('numeric_scope', 'numeric_scope_independent_review', 'numeric_panel_five', 'numeric_frame_five', 'numeric_H_restore', 'numeric_restore_call_chain')) + '。', '',
           '**不把全部7770列独立K复算或所有H列全场补存加入本表的新必须门。** 原记录没有这些资格，也没有任意RHS逆算子或有限QP checkpoint/resume资格；这些范围限制原样保留。当前K1/K3几何的FE、材料、公差、接触与最坏载荷仍归第6行，不由旧数值通过继承。', '',
           '## 连续方法：实际失败和未决继续保留', '',
           '原V3完整边界模型仍为4/16；原V6条件primitive/trim模型仍为8/16。V6全局4096次split在case-028 frame1用尽，另外7个nonpass当次0次新split；局部改进不能写成全16闭合。V9选中的旧叶最终上界虽为0，但最终新UV证明数u=0，原owned验证阶段又因VmRSS KeyError失败；driver未到first-u门，后续全16阶段未执行。新监督器的真实控制资格不重判这次V9失败。参见 ' + '、'.join(link(x) for x in ('original_V6_all16_readback', 'V9_actual', 'V9_meaning', 'new_supervisor_control_audit')) + '。', '',
           '相关性诊断、wire含义诊断和一次原空间split成本探针均有实际输出。一次split的两个子盒仍pending、excluded=0，累计depth25超出原V6 depth24，因此只记为成本诊断；pending不能称为native干涉。原有向体积、完整D、保守包含、原判据、native filling/材料语义和全域证明要求不被删除。Edge189的新support/channel结果在V1尚未纳入。参见 ' + '、'.join(link(x) for x in ('correlation_diagnosis', 'wire_diagnosis', 'spatial_cost_probe', 'edge189_metadata_only')) + '。', '',
           '## 外部事实、当前合同与G3–G5', '',
           '原228个事实要求为10身份、77部件字段、120接口字段、21所选部件/供应商revision字段；207项要求同一样件，21项要求所选PN/revision。本轮新增可接纳原事实与实际测量为0。型号资料不能替代同一样件的10身份、7部件、12接口，也不能推定OLED/COF/FPC、连接器方向/端子、材料/工艺或原机功能。这个228是原事实要求数，不是新增全局blocker数。', '',
           '当前合同中的154个名义材料赋值、13类需来源载荷、真实接触/预紧与相关公差，以及完整OEM互连/叠层尚不完整。G3仍有14项阈值和5项采样要求未有来源；G4为9功能协议、14通道；G5为8指标和4暴露范围。G3、G4、G5均无本轮真实pass；只允许同候选、同样件、同assembly revision的逐级真实结果支持后级，缺测/失效/维修/换件分别保留。参见 ' + '、'.join(link(x) for x in ('external_original_contract_readback', 'external_intake_contract', 'external_field_plan')) + '。', '',
           '## 精确a11推送是单独未完成的义务', '',
           '用户授权的提交是 `a11b00f71231ef3516d2a79c73fa441c375ac755`，目标分支是 `evidence/full-sprint-20261027-n13-l6`。保存的2026-10-28 23:51 UTC定向查询返回404；这不证明其在任何位置都不存在。本账本没有该精确对象推送成功的回执。已核对的另一路R7证据发布为R5分支的 `8bb6f52b624cd40a0570f8710f140bb5a0abf96f`，304个文件远端Git blob/字节数一致；这不能替代a11。原用户推送授权继续有效，不需要重问授权；缺的是精确对象/历史可取得并验证及目标ref的成功回执。参见 ' + '、'.join(link(x) for x in ('exact_authorized_push_original_reads', 'restoration_publication', 'envelope_runtime_publication')) + '。', '',
           '## 存储观察：保持未决，不重判finite-pass', '',
           '第一类是运行时临时scratch对应关系：原43条removed=true是逐轮finally中的即时exists观察，不是结束时scratch全清点；后来完整同哈希vtk wheel仍可见。源码没有留下逐轮unlink/inode/时间事件链，原因未证。第二类是已归档副本和路径状态：near迁移原回执末态只有2个manifest，但后来观察为2359文件、210541721 B，其中2357条在removed列表；这些当前可见文件SHA仍全部等于原seal，完整ZIP也仍等于原SHA。near失败的第一次读回与后来观察同时保留，不把历史末态改写。', '',
           '新增far观察为最终ZIP与.partial两条regular路径同时存在、内容均为127370781 B / `7bc806653be9c7e70dea0ad195bcf992d899a06d73e170af499d8f7b10804130`，不同inode、各nlink=1。源码有partial.rename(TARGET)，但原success回执没有rename后partial缺席记录；因此不声称已证明“删后重现”，也不推断平台原因。这些观察不改原finite科学pass或完整归档内容通过，同时不能写no-unresolved。参见 ' + '、'.join(link(x) for x in ('vtk_cleanup_correspondence', 'near_storage_migration', 'near_storage_failed_read', 'near_storage_later_read', 'far_two_paths_observation')) + '。', '',
           '## 已完整保存的三份原件归档', '',
           '| 原件归档 | 字节 | 全成员数 | SHA256 |', '|---|---:|---:|---|']
    for name, item in saved.items():
        url = 'https://chatgpt.com/library?file_id=' + item['library_file_id'] + '&account_id=personal'
        md.append('| [' + item['filename'] + '](' + url + ') | ' + str(item['bytes']) + ' | ' + str(item['complete_ZIP_members']) + ' | `' + item['sha256'] + '` |')
    md += ['', '归档覆盖完整原件，不只保留投影；三份均有全成员CRC/SHA读回及成功保存回执。原native80科学seal为22619921 B，保持原64 MiB门内。Near工程展开目录的后来部分状态与native80 ZIP缓存回收另有记录，不能与已保存完整原件混为一谈。', '',
           '## 来源身份目录', '',
           '下表给出本账本实际读取的全部来源及完整SHA256；数值八份原记录的补充身份也保留在JSON。原证据全部只读，读前读后字节一致。', '',
           '| Evidence ID / 原件 | 字节 | SHA256 |', '|---|---:|---|']
    for name, item in evidence.items():
        md.append('| ' + link(name) + ' | ' + str(item['bytes']) + ' | `' + item['sha256'] + '` |')
    md += ['', '本版结论：`all_blockers_closed=false`，`full_continuous_G2=false`，`current_K1_K3_FE_qualified=false`，`G3/G4/G5=false`。Edge189的新实际诊断和之后的发布回执应另立增补版本，保留本版。', '']
    md_bytes = '\n'.join(md).encode()
    save(json_path, json_bytes)
    md_path = OUT / 'R7_BLOCKER_CLOSURE_LEDGER_V1.md'
    save(md_path, md_bytes)
    receipt = {'schema': 'razr-r7-seven-row-ledger-generation-receipt-v1',
               'completed': True, 'new_scientific_qualification': False, 'all_original_bound_inputs_unchanged': True,
               'source': {'path': str(Path(__file__).resolve().relative_to(BASE)), **identity(Path(__file__))},
               'outputs': {p.name: identity(p) for p in (json_path, md_path)},
               'input_count': len(evidence), 'additional_original_numeric_reports_checked': len(numeric_original_records),
               'all_blockers_closed': False, 'edge189_new_support_or_channel_result_admitted': False,
               'seconds': time.monotonic() - START,
               'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    save(OUT / 'R7_BLOCKER_CLOSURE_LEDGER_GENERATION_RECEIPT_V1.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt))


def main():
    resource.setrlimit(resource.RLIMIT_AS, (LIMIT_AS, LIMIT_AS))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(LedgerBudgetExceeded('Registered ledger read wall budget exceeded')))
    signal.alarm(LIMIT_SECONDS)
    try:
        build()
        return 0
    except BaseException as exc:
        failure = {'schema': 'razr-r7-blocker-ledger-attempt1-actual-reader-failure',
                   'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc(),
                   'original_reports_modified': False, 'new_CAD_or_solver_execution': False,
                   'source_identity': identity(Path(__file__)), 'seconds': time.monotonic() - START}
        save(OUT / 'R7_BLOCKER_LEDGER_ATTEMPT1_ACTUAL_FAILURE.json', (json.dumps(failure, indent=2) + '\n').encode())
        print(json.dumps(failure))
        return 2
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    raise SystemExit(main())
