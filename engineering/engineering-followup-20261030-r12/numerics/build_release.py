"""Collect small source-bound numerical deliverables; original archives stay separate."""
import hashlib,json,pathlib,shutil


def identity(p,base=None):
    p=pathlib.Path(p)
    with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(p.relative_to(base)) if base else str(p),bytes=p.stat().st_size,sha256=h)


def main():
    p=pathlib.Path(__file__).resolve().parent;e=p/'evidence';dest=p/'release'
    panel=json.loads((e/'PANEL_ORIGINAL_FIVE_REPLAY.json').read_text());frame=json.loads((e/'FRAME_ORIGINAL_FIVE_REPLAY.json').read_text());h=json.loads((e/'H_RESTORE_REPLAY.json').read_text())
    portable=json.loads((e/'portable-map-attempt1/PORTABLE_LOAD_MAP.json').read_text());independent=json.loads((e/'PORTABLE_MAP_INDEPENDENT_READBACK.json').read_text());tests=json.loads((e/'portable-map-tests-attempt1/TEST_REPORT.json').read_text())
    assert panel['completed'] and frame['completed'] and h['completed'] and portable['completed'] and independent['completed'] and tests['completed']
    residuals=panel['original_five_ratios'];frame_residuals=[r['ratio'] for r in frame['scalar_actions']]
    assert all(x<=1e-7 for x in residuals+frame_residuals)
    metadata={}
    for filename in ['download_initial.json','download_h.json']:
        obj=json.loads((p/filename).read_text())['result']
        while 'structuredContent' in obj:obj=obj['structuredContent']
        for row in obj['results']:
            metadata[row['name']]=dict(library_file_id=row['library_file_id'],file_id=row['file_id'],name=row['name'],bytes=row['size_bytes'],
                native_link='https://chatgpt.com/library?file_id='+row['library_file_id']+'&account_id=personal')
    for name,row in metadata.items():
        rec=identity(p/'original_archives'/name);assert rec['bytes']==row['bytes'];row['sha256']=rec['sha256']
    (e/'ORIGINAL_ARCHIVE_RECOVERY_IDENTITIES.json').write_text(json.dumps(dict(schema='r12.original_archive_recovery_identities.v1',archives=list(metadata.values()),all_seven_SHA_verified=True,archive_bytes_not_duplicated_in_public_small_bundle=True),indent=2)+'\n')
    scope=dict(schema='r12.completed_original_numeric_and_portable_auxiliary_scope.v1',completed=True,
        original_controlling_source_commit='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',original_K_b_C_fields_and_threshold_unchanged=True,
        current_runtime=panel['runtime'],historical_dependency_runtime_reproduced=False,new_solver_executed=False,
        original_panel_five_residuals=residuals,original_frame_five_residuals=frame_residuals,all_ten_original_native_float64_gates_passed=True,
        panel_correction_process=dict(native_gates=panel['native_original_float64_gate_evaluations'],exact_equations=panel['direct_exact_equations_checked'],candidate_rows=panel['all_target_pairs_independently_reconstructed_and_accumulated'],anchors=panel['unchanged_exact_anchors_checked']),
        H_columns={body:h['bodies'][body]['columns'] for body in ['panel','frame']},all_7770_basis_RHS_and_saved_projection_hashes_rechecked=True,
        all_7770_successful_full_fields_available=False,all_7770_K_products_executed=False,original_failed_frame_8_520_excluded_but_retained=True,
        original_ExactResponseCache_restore=h['original_ExactResponseCache_restore'],restore_scope=h['callback_scope'],
        original_raw_and_derived_H_bytes_retained=True,portable_loadG_new_algorithm_identity=True,
        portable_exact_terms=independent['term_count'],portable_exact_dots=independent['exact_dot_entries'],portable_rounding_cells_independently_checked=True,
        portable_original24_permutations=tests['original24_order_permutations_passed'],portable_differential_cases=len(tests['independent_fraction_edge_and_random_cases']),
        portable_actual_tamper_rejections=len(tests['actual_retained_mutation_controls']),legacy_map_comparisons=independent['comparisons'],
        original_seed_overwritten=False,legacy_whole_seed_bitwise_replay_passed=False,portable_whole_seed_created_or_qualified=False,
        arbitrary_RHS_inverse_qualified=False,finite_QP_resume_qualified=False,current_geometry_FE_qualified=False,physical_G3_G5_qualified=False,
        actual_worker_peak_RSS_KiB=dict(panel=panel['peak_RSS_KiB'],frame=frame['peak_rss_kib'],H_restore=h['peak_rss_kib']),
        worker_seconds=dict(panel=panel['elapsed_seconds'],frame=frame['seconds'],H_restore=h['seconds']),
        external_RSS_sampling_scope='Nested launcher only. Two initial receipt field labels corrected by separately retained scope-correction records; actual numerical worker peaks come from worker getrusage.',
        retained_failures=['Initial Library helper network failure; supported sandbox escalation succeeded.','Selective extraction postflight exceeded2GiB including transient duplicate files; canonical payload recovery and subsequent bounded phases recorded.','Historical full seed bitwise replay remains false.'],
        next_numeric_blocker='A fully reconstructed portable seed and arbitrary-RHS/full contact-QP verification require separate source-bound execution; the exact auxiliary map does not supply those qualifications.')
    (e/'NUMERICAL_SCOPE.json').write_text(json.dumps(scope,indent=2)+'\n')
    lines=['# 原数值资格复验与可复现的辅助载荷映射','',
        '本轮已实际恢复并校验7个原归档，按原 K/b/C、原 float64 运算与 1e-7 判据，重新执行 panel 原五探针、完整修正历史以及 frame 原五探针。随后执行原 H/restore 读回。没有重新求解或修改原系统。','',
        '| 原探针 | Panel 残差 | Frame 残差 |','|---|---:|---:|']
    for i,(a,b) in enumerate(zip(residuals,frame_residuals)):lines.append(f'| {i} | {a:.17g} | {b:.17g} |')
    lines+=['',f"Panel 验证 {panel['native_original_float64_gate_evaluations']} 个原门、{panel['direct_exact_equations_checked']} 条精确方程、{panel['all_target_pairs_independently_reconstructed_and_accumulated']} 个候选行和7个未改变的精确锚。其最坏残差仍靠近原1e-7门槛；没有将它描述成更宽的误差裕度。",'',
        f"H读回覆盖两体各3885列，核对7770个原基底RHS和保存投影SHA。原 `ExactResponseCache.restore` 实际调用五个原有序、SHA绑定全场动作，最大相对误差 {h['original_ExactResponseCache_restore']['largest_relative_error']:.17g}，满足原2e-7门。原失败frame8:520块保留并排除。",'',
        '历史未保存全部7770列成功全场，本轮也没有声称重算全部K乘积或一般逆算子。restore资格仍限五个原保存动作，未知或重排RHS被原合同拒绝。','',
        '## 新的确定性 loadG 运算','',
        '原 `R.T @ F` 在不同运行环境下存在末位差异。本轮从SHA绑定原loads中抽取4221项非零乘积，使用整数精确乘积与累加，最后显式执行一次binary64最近偶数舍入，得到新的版本化24项辅助映射。独立reader使用Fraction重新求和、检查24个舍入单元，并重新从原R/F提取每一项。',
        '', '新映射与R9保存的正确舍入精确参考24/24逐位相等。它与历史BLAS映射有10项不同、与R9当前BLAS映射有6项不同，最大差均为2.220446049250313e-16。这些差异保留；旧seed没有覆盖，旧whole-seed逐位复现仍为false。',
        '', '171个独立Fraction差分用例覆盖抵消、极值、亚正常数、最近偶数中点、正负下溢和最终溢出拒绝；24个原点积各5种乱序，共120次顺序不变检查通过。3种无效输入和4个实际篡改文件被拒绝；篡改文件保存在测试目录。',
        '', '对表示矩阵在实数算术下作用于四个系数[-1,1]的情形，独读通过每行全部16个角点验证差值界。对历史映射，六行界依次为4.440892098500626e-16、0、0、0、2.0816681711721685e-17、2.220446049250313e-16。该界不包含下游QP/接触活跃集敏感性，也没有混用不同物理量的安全阈值。',
        '', '## 范围与重现','',
        '本轮闭合原有限数值资格的当前执行读回，以及新辅助loadG运算的精确与舍入确定性。全seed的新版本、一般RHS逆算子、finite-QP断点续算、当前改型几何FE和G3–G5实物资格仍不在此次结果范围内。',
        '', '当前Python3.12.14/NumPy2.3.5/SciPy1.17.0；没有冒称历史依赖运行环境。实际数值worker峰值来自自身getrusage，外部/proc只观测到嵌套launcher。两份最初命名错误的RSS字段及其独立纠正记录均保留。',
        '', '原大归档由 `evidence/ORIGINAL_ARCHIVE_RECOVERY_IDENTITIES.json` 的精确名称、长度、SHA及持久文件身份恢复。新的小型包保留源码、原reader、每次执行报告、容量依据、失败记录、独立精确项和篡改文件，不重复塞入GB级原矩阵。',
        '', '恢复归档后可执行：','', '```sh',
        'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1',
        'python prepare_numeric_replay.py',
        'python run_with_receipt_v2.py --receipt evidence/PANEL_NEW_EXECUTION.json -- python original_inputs/n13/source/current/readback_n13.py --input original_inputs/n12 --run original_inputs/n13/native/N13-v3 --output evidence/PANEL_NEW_READBACK.json',
        '```','',
        '完整已执行命令见各 `*_EXECUTION.json`；`NUMERICAL_SCOPE.json` 为结果边界，`PORTABLE_MAP_INDEPENDENT_READBACK.json` 为独立数学核验。为避免覆盖既有证据，重跑请指定新输出路径。','']
    (p/'README.md').write_text('\n'.join(lines))
    dest.mkdir(exist_ok=False)
    source_names=['README.md','exact_dyadic.py','run_portable_load_map.py','read_portable_load_map.py','test_exact_dyadic.py','read_saved_fields.py','read_saved_h_restore.py','prepare_numeric_replay.py','prepare_h_readback.py','run_with_receipt.py','run_with_receipt_v2.py','build_release.py']
    for name in source_names:shutil.copyfile(p/name,dest/name)
    shutil.copytree(e,dest/'evidence',ignore=shutil.ignore_patterns('__pycache__'))
    original=dest/'original-reader';original.mkdir();shutil.copyfile(p/'original_inputs/n13/source/current/readback_n13.py',original/'readback_n13.py')
    members=[identity(q,dest) for q in sorted(dest.rglob('*')) if q.is_file()]
    manifest=dict(schema='r12.numerical_small_release_manifest.v1',files=members,count=len(members),bytes=sum(x['bytes'] for x in members))
    (dest/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(release=str(dest),count=len(members),bytes=manifest['bytes'],scope=scope),indent=2))


if __name__=='__main__':main()
