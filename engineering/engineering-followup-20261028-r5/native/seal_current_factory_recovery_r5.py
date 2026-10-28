"""Freeze R5 original-factory recovery, with exact scientific/public maps."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import shutil
import zipfile


def ident(path):
    with Path(path).open('rb') as stream:
        return {'bytes': Path(path).stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def main():
    work = Path(__file__).resolve().parent
    root = work.parent
    reports = {p: json.loads((work/('archive-audit-'+p+'-v2')/'R5_K3_ARCHIVE_AUDIT.json').read_text()) for p in ('near','far')}
    need = lambda b: None if b else (_ for _ in ()).throw(ValueError('Sealing precondition failed'))
    need(all(x['completed'] and not x['issues'] for x in reports.values()))
    prep = json.loads((work/'R5_CURRENT_FACTORY_REPLAY_PREPARATION.json').read_text())
    need(prep['original_startup_refusal_observed'] and not prep['native_started'])
    receipts = json.loads((work/'R5_HISTORICAL_GIT_SOURCE_RECEIPT.json').read_text())
    for x in receipts['records']:
        p = work/'historical-source'/Path(x['path']).name
        raw = p.read_bytes()
        need(len(raw) == x['received_UTF8_bytes'])
        need(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == x['git_blob_sha'])
    current = {}
    for pose, r in reports.items():
        current[pose] = {**r['current_pose_summary'], 'audit_seconds':r['seconds'],
                        'audit_peak_RSS_bytes':r['peak_RSS_bytes'],
                        'archive_identity':r['archive_actual'],
                        'verified_members':r['verified_member_count'],
                        'verified_member_bytes':r['verified_member_bytes'],
                        'audit_report':{'relative':f'archive-audit-{pose}-v2/R5_K3_ARCHIVE_AUDIT.json',
                                        **ident(work/f'archive-audit-{pose}-v2/R5_K3_ARCHIVE_AUDIT.json')}}
    unique = {}
    for r in reports.values():
        for row in r['matrices']:
            unique[row['projection_identity']['sha256']] = row
    summary = {'schema':'razr-r5-current-factory-historical-recovery-summary-v1',
        'current_candidate':{'KEY':'key_forward_loop_v1','panel':'panel_key_travel_stops_v1'},
        'historical_functional_source':'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
        'historical_full_K3_run_id':40285103942,
        'historical_diagnostic_commit':'566197a97ee137ce4a58097656eb4fd6bc084b05',
        'historical_data_recovered_and_stream_verified_this_round':True,
        'new_native_CAD_execution_this_round':False,
        'new_candidate_material_change_this_round_mm3':{'KEY_added':0,'KEY_removed':0,'panel_added':0,'panel_removed':0},
        'both_current_intermediate_finite_factory_evidence_recovery_closed':True,
        'both_current_whole_material_bindings_exact_byte_verified':True,
        'current_whole_factory_newly_recomputed':False,
        'original_raw_runtime_reports_reconstructed':False,
        'historical_runtime_requalified':False,
        'current_poses':current,
        'top_current_pose_totals':{'factory_plus_reader_pair_rows':sum(r['current_pose_summary']['current_pose_pair_rows_factory_plus_reader'] for r in reports.values()),
            'selected_and_completed_journal_events':sum(r['current_pose_summary']['current_pose_journal_rows'] for r in reports.values()),
            'body_STEP_readbacks':308,'independent_middle_pose_material_gates':24},
        'nested_historical_report_copies_read':sum(len(r['matrices']) for r in reports.values()),
        'unique_historical_full_matrix_projection_SHA_count':len(unique),
        'nested_original_S4_collision_records_retained':[
            {'projection_SHA256':sha,'member_example':r['report_member'],'rejected_pairs':r['retained_rejected_pairs']}
            for sha,r in unique.items() if r['retained_rejected_pairs']],
        'R5_auditor_first_attempt_failed_and_preserved':{'reason':'Original F1 independent reader names its value direct_Common_mm3; V1 required common_mm3 for all nested records.',
            'report':{'relative':'archive-audit-near-attempt1/R5_K3_ARCHIVE_AUDIT.json',**ident(work/'archive-audit-near-attempt1/R5_K3_ARCHIVE_AUDIT.json')},
            'original_geometry_data_or_threshold_modified':False},
        'actual_unchanged_original_CAD_startup_refusal':{'worker_started':False,'resource_observations':prep['original_supervisor_recorded_observations'],
            'source_identity':prep['original_supervisor'],'receipt':prep['actual_original_supervisor_receipt']},
        'full_continuous_G2_closed':False,'physical_independent_motion_domain_closed':False,
        'force_hold_return_relock_qualified':False,'current_FE_and_tolerance_qualified':False,
        'same_specimen_OEM_and_electrical_qualified':False,'G3_pass':False,'G4_pass':False,'G5_pass':False,
        'all_blockers_closed':False,
        'remaining':['continuous native all-pair coverage with complete correlated left/right controls',
                     'native boundary and compiled-transform error guarantees',
                     'physical holds, return force, relock, materials and manufacturing tolerances',
                     'current complete geometry FE and sourced acceptance thresholds',
                     'same-specimen OEM interconnect and sequential physical G3/G4/G5 evidence']}
    (work/'R5_CURRENT_FACTORY_RECOVERY_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    archives = [{'file_name':'K3FULL-'+pose+'-original-40285103942.zip',**r['archive_actual'],
                 'complete_ZIP_bytes_not_embedded_again':True,'all_member_CRC_size_SHA_checked_this_round':True,
                 'original_preservation_receipt_relative':'r5-resource/R5_RECOVERED_K3_PRESERVATION.json'} for pose,r in reports.items()]
    (work/'R5_ORIGINAL_SCIENTIFIC_ARCHIVE_IDENTITIES.json').write_text(json.dumps({'schema':'razr-r5-current-factory-external-originals-v1','archives':archives},indent=2)+'\n')
    readme = '''# R5：恢复当前 K1／K3 两个中途完整 factory 原证据

本轮关闭的是当前同一 `key_forward_loop_v1`／`panel_key_travel_stops_v1` 候选在两个中途姿态上的**原有限 factory 证据恢复缺口**。两份原 ZIP 从原 GitHub Actions artifact 实际接收，并与已发布的完整 ZIP 大小、SHA256 和原 manifest 对上；每个成员均流式读到 EOF，重新核对 CRC、大小和 SHA。没有重新执行 CAD、改变候选材料、改判据或把历史工程投影补写成缺失的原始运行时报告。

## 坐标与当前材料

| 姿态 | phone slide，mm | 左右 KEY q，mm | 完整参与体 | producer＋reader 全体对行 | 选中＋完成 journal 事件 |
|---|---:|---:|---:|---:|---:|
| near | 23.142044210239405 | 3.482188470506243 | 154 | 23,562 | 47,124 |
| far | 60.880681403413135 | 9.160729490168748 | 154 | 23,562 | 47,124 |

前一列是整体滑动坐标，后一列是原 factory 算出的 KEY 坐标，不能混用。每姿态包含原 producer 和另一个进程的原 STEP reader，各 11,781 个无序体对；本轮逐行比对保存的完整矩阵与原 journal。两姿态共 308 个完整 STEP 读回和 24 个独立中途物料门，原记录均通过。左右 panel／KEY 的直接 Common、严格 Common 和矩阵在两个姿态均为零，原 `1e-7 mm³` 判据保留。

这条身份链包含实际字节：原 near／far ZIP 都含与 R3／R4 当前使用的 panel BREP 完全一致的原件，以及左右 K1 q0 KEY 的完整 STEP 原件。panel BREP 为 256,490 B，SHA256 `95a98b5933f0f7201d2f6a602bcd0d4d40c6170c583ef6694f0c9f03ce289222`。KEY q0 STEP 分别为 338,523 B／344,792 B。原全件差集与独立标量重建、panel 正连接、功能接触面记录也全部保留。STEP 序列化头可能不同，因此没有把不相同的 STEP 字节称为相同；panel 使用实际相同的 BREP 字节建立桥接。

## 实际恢复与审计

原执行为 run `40285103942`，诊断提交 `566197a97ee137ce4a58097656eb4fd6bc084b05`，功能源为 S4 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`。已有公开记录覆盖十个有限态，本轮完整接收和审核其中 near／far 两件，不能把公开十态摘要改称本轮已重新核验十份 ZIP。

near 原 ZIP 为 62,073,711 B，SHA256 `cb4db333a525375928efb59ba4cb4b55afc8d6d3024dd04ebdc438c816b613ff`；far 为 62,068,019 B，SHA256 `e9e68c7accdc32ac261cd9e19ad45218c08f8896c686c874ef77bdacfec32fa0`。各自 4,715 个 manifest 成员，读取的成员总字节分别为 441,440,793 和 441,444,765。V2 实际审计耗时分别约 9.25／8.32 秒，峰值 RSS 约 77.2 MB。

嵌套 prerequisite 的原 F1 碰撞见证与原 K1 修复证据也存在于这两份原 ZIP。包含的重复副本按 SHA 明确去重统计；没有把重复读取说成新增 native 试验。原 F1 的 panel／KEY 正 Common 继续作为真实失败保留，不因当前 K1／K3 有限态通过而删除。

首次审计 V1 在完成 near 全部成员 SHA／CRC 后，遇到原 F1 reader 使用 `direct_Common_mm3` 而不是 K3 的 `common_mm3`，触发 KeyError。原源码与失败报告保留。新命名 V2 显式辨认这两个原 schema，分别核对原体积、阈值分类和读回差值；原科学数据未改。

## 再执行准备与真实资源拒绝

已冻结恢复的 971 个功能源文件、原 K3 driver 和完整 factory／reader 命令。原 `supervise_k3full.py` 字节不变，实际执行其纯 stdlib 启动路径，记录普通可用磁盘为 0、共享不可回收估计为 5,519,083,496 B；原 256 MiB 磁盘门和增加 2 GiB 后不得超过 6.8 GiB 的启动门未满足，退出码为 3，`worker_started=false`。没有进入 CAD、原 43 包入口或运行时重验，也没有把权限允许写入元数据解释为普通磁盘容量足够。

恢复的功能源码不是 S4 Git checkout，也没有原 `.venv` 入口。前瞻命令明确要求先恢复真实源码身份与受资格验证的执行入口；本轮没有伪造它们。相同候选相同有限姿态的已有证据现已完整恢复，不需重复 native 来增加通过次数。

## 仍未闭合

这两个有限状态不能证明全程和全部左右相关控制域。严格连续 G2、原生边界语义和变换误差、力保持／回程／重锁、当前结构 FE／制造公差、同 specimen 原件及 OEM 互连、电气合同和 G3→G4→G5 实物试验仍待相应证据。本轮 KEY／panel 新增与切除材料均为 0。

`R5_CURRENT_FACTORY_RECOVERY_SUMMARY.json` 给出机器可读状态；每姿态的 `R5_K3_ARCHIVE_AUDIT.json`、完整矩阵 gzip 和全件读回 gzip 保留逐项结果。两个原 ZIP 已分别保存，补充科学归档只索引其完整身份，不重复嵌入约 124 MB 数据。公共投影仅替换工作区前缀，其原字节／投影字节分别列入 manifest；它不替代原科学归档。
'''
    (work/'README_R5_CURRENT_FACTORY.md').write_text(readme)
    public = work/'public'
    need(not public.exists());public.mkdir()
    raw_members = [p for p in sorted(work.rglob('*')) if p.is_file() and not p.is_relative_to(public)
                   and not p.name.endswith('.private.json') and p.suffix != '.zip']
    public_rows = []
    private_pattern = re.compile(r'libfile_[A-Za-z0-9]+|[?&](?:sig|se|skoid)=|sdmnt[^\s]*oaiusercontent')
    for p in raw_members:
        rel = p.relative_to(work);raw = p.read_bytes()
        if p.suffix == '.gz':
            decoded = gzip.decompress(raw).decode('utf-8')
            need(str(root) not in decoded and not private_pattern.search(decoded))
            data = raw; transformed = False
        else:
            text = raw.decode('utf-8')
            projected = text.replace(str(root), 'workspace')
            need(not private_pattern.search(projected))
            data = projected.encode();transformed = data != raw
        dst = public/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        public_rows.append({'relative':str(rel),'original_identity':ident(p),'public_identity':ident(dst),
                            'workspace_prefix_only_projection':transformed})
    pubmanifest = {'schema':'razr-r5-current-factory-public-map-v1','members':public_rows,
                   'original_science_replaced':False,'private_download_descriptors_excluded':True}
    (public/'PUBLIC_SOURCE_MAP_R5.json').write_text(json.dumps(pubmanifest,indent=2)+'\n')
    # All source and audit records are immutable after this seal. Public copies
    # are reproducible from these files and this source, not embedded twice.
    manifest = {'schema':'razr-r5-current-factory-science-manifest-v1',
        'members':{str(p.relative_to(work)):ident(p) for p in raw_members},
        'external_originals':archives, 'public_source_map_identity':ident(public/'PUBLIC_SOURCE_MAP_R5.json'),
        'new_native_execution':False,'all_blockers_closed':False}
    manifest_path = work/'R5_CURRENT_FACTORY_SCIENCE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    target = work/'RAZR-R5-current-factory-original-recovery-and-audit-20261028.zip'
    need(not target.exists())
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in [*raw_members,manifest_path]:
            zi=zipfile.ZipInfo(str(p.relative_to(work)),date_time=(2026,10,28,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED
            zi.external_attr=0o100644<<16;z.writestr(zi,p.read_bytes())
    with zipfile.ZipFile(target) as z:
        need(z.testzip() is None)
        for name,expected in manifest['members'].items():
            raw=z.read(name);need({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==expected)
    seal={'schema':'razr-r5-current-factory-archive-seal-v1','archive':{'file_name':target.name,**ident(target)},
        'members_excluding_manifest':len(raw_members),'all_members_read_back_SHA_size_and_CRC_verified':True,
        'public_file_count':len(public_rows)+1,'public_source_map_identity':ident(public/'PUBLIC_SOURCE_MAP_R5.json'),
        'science_manifest_identity':ident(manifest_path),'public_original_projection_map_complete':True,
        'original_large_ZIPs_embedded_again':False}
    (work/'R5_CURRENT_FACTORY_ARCHIVE_SEAL.json').write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps(seal))


if __name__=='__main__':
    main()
