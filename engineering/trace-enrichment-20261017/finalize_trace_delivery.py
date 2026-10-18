"""Publish only after both selected-space cases and all current tests finish."""
from pathlib import Path
import json,gzip,hashlib,tarfile,shutil,subprocess,datetime
R=Path('/home/qian-qi/RAZR-SLIDE-trace-enrichment-20261017');O=Path('/tmp/razr-trace-enrichment-20261017');E=R/'engineering/trace-enrichment-20261017'
F='e905b4f39991f565017d15f73fcb821f0d1c6143';BASE='faee1e95e5e3b86baa9b21fe6a9d4a205aa5d752'
D=Path('/home/qian-qi/.local/share/razr-slide-evidence/trace-enrichment-20261017')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
unit=load(O/'unit1040/report.json');assert unit['passed'] and unit['tests_run']==1040 and len(unit['suite_results'])==31
assert unit['source_bytes_unchanged'] and unit['base_commit']==F and not unit['changed_during_tests'] and not unit['syntax_errors']
for path,value in unit['source_hashes_after'].items():assert sha(R/path)==value,('source changed after full test',path)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==F
assert not subprocess.check_output(['git','status','--porcelain','-uno'],cwd=R,text=True).strip()
assert not D.exists();D.mkdir(parents=True)
rows=[];durable=[];keysets=[]
for label,runname,auditname,elementname in [('selected-2','original-selected-v3','independent-field-v1','independent-elements'),('selected-4','original-selected64-v1','independent-field-expanded-v1','independent-elements-expanded')]:
    run=O/runname;audit=O/auditname;elements=O/elementname
    r=load(run/'report.json');v=load(audit/'report.json');el=load(elements/'report.json')
    assert r['passed'] and v['passed'] and el['passed'] and v['total_regions']==5255
    assert r['source_sha256']==sha(E/'solve_trace_probe.py') and v['source_sha256']==sha(O/'verify_trace_field.py')
    assert el['maximum_relative_error']<1e-8 and v['minimum_covered_bound_mm']>=-1e-7
    for path,h in v['input_sha256'].items():assert sha(path)==h,('field dependency changed',path)
    finalgap=load(run/f'gaps-{len(r["history"])-1:03d}.json')
    assert not finalgap['negative_cells'] and not finalgap['unresolved_cells']
    target=E/label;target.mkdir(exist_ok=False);dt=D/label;dt.mkdir()
    for file in ['report.json','progress.json','selection.json','old-tractions-new-space.json','exact-energy-update.json']:
        (target/(file+'.gz')).write_bytes(gzip.compress((run/file).read_bytes(),mtime=0))
    shutil.copyfile(run/'full-fields.npz',target/'full-fields.npz')
    (target/'gap-bounds.json.gz').write_bytes(gzip.compress((run/f'gaps-{len(r["history"])-1:03d}.json').read_bytes(),mtime=0))
    shutil.copyfile(audit/'report.json',target/'independent-field.json')
    (target/'independent-regions.json.gz').write_bytes(gzip.compress((audit/'regions.json').read_bytes(),mtime=0))
    shutil.copyfile(elements/'report.json',target/'independent-element-checks.json')
    with tarfile.open(target/'independent-element-matrices.tar.gz','w:gz') as t:
        for p in sorted(elements.glob('*.npz')):t.add(p,arcname=p.name)
    with tarfile.open(target/'selected-element-private-fields.tar.gz','w:gz') as t:
        for p in sorted(audit.glob('*selected-tet-*-private.npz')):t.add(p,arcname=p.name)
    for name in ('panel','frame'):
        body=target/name;body.mkdir()
        for file in ['assembly.json','selection.json','coupling.npz','local-blocks.npz']:
            shutil.copyfile(run/name/file,body/file)
        (body/'local-records.json.gz').write_bytes(gzip.compress((run/name/'local-records.json').read_bytes(),mtime=0))
        p=audit/f'{name}-all-unselected-private.npz';q=dt/p.name;shutil.copyfile(p,q);assert sha(q)==sha(p)
        durable.append({'source':str(p),'durable_path':str(q),'sha256':sha(q),'bytes':q.stat().st_size,'role':'all unselected L2 private coefficients plus parent ordering'})
    with tarfile.open(dt/'all-exchange-fields-and-gap-audits.tar.gz','w:gz') as t:
        for p in sorted(run.glob('field-*.npz'))+sorted(run.glob('gaps-*.json')):t.add(p,arcname=p.name)
    p=dt/'all-exchange-fields-and-gap-audits.tar.gz';durable.append({'source':str(run),'durable_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'role':'all initial rejected and accepted finite point-contact fields'})
    selection=r['selected_faces'];keys={(x['body'],tuple(x['vertices'])) for x in selection};keysets.append(keys)
    patch_counts={}
    for item in selection:
        key=item['body']+':'+item['patch'];patch_counts[key]=patch_counts.get(key,0)+1
    rows.append({'label':label,'face_limit_per_patch_body':r['face_per_patch_body'],'selected_faces':len(selection),'actual_faces_by_body_patch':patch_counts,
        'new_trace_dofs':r['new_trace_dofs'],'retained_global_dimension':818829+r['new_trace_dofs'],'full_L2_dimension_including_recovered_interiors':11112429+r['new_trace_dofs'],
        'case':6,'audited_original_regions':5255,'cubic_regions':v['cubic_regions'],'finite_QP_solves':len(r['history']),'initial_old_pointset_negative_regions':r['history'][0]['negative_cells'],
        'initial_old_pointset_minimum_witness_mm':r['history'][0]['minimum_witness_mm'],'final_contacts':r['history'][-1]['contacts'],'final_negative_regions':0,'final_unresolved_regions':0,
        'final_independent_lower_bound_mm':v['minimum_covered_bound_mm'],'old_fixed_traction_new_space':load(run/'old-tractions-new-space.json'),
        'cubic_subtriangle_checks':sum(c['subtriangles'] for c in finalgap['cubic_checks']),'largest_cubic_roundoff_allowance_mm':max(c.get('roundoff_guard_max',0.) for c in finalgap['cubic_checks']),
        'full_independent_checks':v['full_checks'],'independent_contact_complementarity':v['contact_complementarity'],'force_moment_balance':v['balance'],
        'relative_elastic_energy_change_from_L2_reference':v['relative_elastic_energy_change'],'relative_load_displacement_change_from_L2_reference':v['relative_load_displacement_change'],
        'maximum_bolt_force_change_from_L2_reference':v['maximum_bolt_force_change'],'independent_element_comparisons':len(el['checks']),'independent_element_max_relative_error':el['maximum_relative_error'],
        'full_fields_sha256':sha(run/'full-fields.npz'),'solver_report_sha256':sha(run/'report.json'),'independent_report_sha256':sha(audit/'report.json'),
        'source_hash':r['source_sha256'],'all_internal_DOFs_recovered':True,'shared_bernstein_auditor_independent_tetra_evaluation':True})
assert keysets[0]<keysets[1], 'selected spaces not nested'
comparison={
    'larger_space_contains_all_smaller_selected_faces':True,
    'added_faces':len(keysets[1]-keysets[0]),
    'relative_load_displacement_change_larger_over_smaller':(1+rows[1]['relative_load_displacement_change_from_L2_reference'])/(1+rows[0]['relative_load_displacement_change_from_L2_reference'])-1,
    'relative_elastic_energy_change_larger_over_smaller':(1+rows[1]['relative_elastic_energy_change_from_L2_reference'])/(1+rows[0]['relative_elastic_energy_change_from_L2_reference'])-1,
    'residual_contact_target_error_not_separated':True,'not_continuum_error_estimate':True}
write(E/'selected-trace-comparison.json',{'levels':rows,'comparison':comparison})
(E/'local-unit1040.json.gz').write_bytes(gzip.compress((O/'unit1040/report.json').read_bytes(),mtime=0))
with tarfile.open(E/'unit-raw-logs.tar.gz','w:gz') as t:
    for p in sorted((O/'unit1040').rglob('*.log')):t.add(p,arcname=str(p.relative_to(O/'unit1040')))
identity_check=load(O/'selection-and-DOF-identity.json');assert identity_check['passed'] and identity_check['actual_nested_sets_checked']
for path,value in identity_check['input_sha256'].items():assert sha(path)==value
shutil.copyfile(O/'selection-and-DOF-identity.json',E/'selection-and-DOF-identity.json')
for name in ['run_complete_units1040.py','verify_trace_field.py','check_trace_identity.py','finalize_trace_delivery.py']:
    shutil.copyfile(O/name,E/name)
with tarfile.open(E/'rejected-preparation.tar.gz','w:gz') as t:
    t.add(O/'rejected-cubic-numpy-cross.py',arcname='rejected-cubic-numpy-cross.py')
    t.add(O/'original-selected-v2',arcname='failed-dimension-v2')
jobs={
    'face20':'1a14cc96bc5-1b6abb-4f2','cubic16-initial-error':'1a14ccf407e-1b6abb-53b','cancelled-v1':'1a14ccf89dc-1b6abb-53f',
    'dimension-error-v2':'1a14cd0d43f-1b6abb-54c','cubic16-fixed':'1a14cd07917-1b6abb-547','element56':'1a14cd3f298-1b6abb-578',
    'first-trace-solve':'1a14cd50f81-1b6abb-587','complete1040':'1a14cd54c73-1b6abb-589','first-independent-field':'1a14cdd8a92-1b6abb-5eb',
    'expanded-trace-solve':'1a14ce0e363-1b6abb-627','expanded-elements':'1a14ce43b3b-1b6abb-666'}
# Additional finished job IDs are read from an explicit file created after launch.
jobs.update(load(O/'additional-jobs.json'))
terminal={}
with tarfile.open(E/'execution-logs.tar.gz','w:gz') as t:
    for label,jid in jobs.items():
        d=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs')/jid
        terminal[label]=load(d/'exit.json')
        if label not in ('cubic16-initial-error','cancelled-v1','dimension-error-v2'):assert terminal[label]['exit_code']==0,(label,terminal[label])
        for name in ('stdout.log','stderr.log','exit.json'):t.add(d/name,arcname=label+'/'+name)
write(E/'execution-jobs.json',{'jobs':jobs,'terminal':terminal})
write(E/'durable-private-fields.json',{'root':str(D),'files':durable,'complete_large_private_fields_not_claimed_uploaded_to_git_or_chat':True})
if (O/'hosted-summary.json').exists():shutil.copyfile(O/'hosted-summary.json',E/'hosted-summary.json')
final={'base_main':BASE,'functional_commit':F,'full_local_tests':1040,'suites':31,'new_unit_tests_included':36,'all_tests_passed':True,'source_snapshot_unchanged':True,
    'old_CAD_native_tasks_not_rerun':True,'selected_trace_cases_independently_passed':rows,'selected_space_comparison':comparison,
    'old_volume_space_L2_retained':True,'same_prior_nodal_load_functionals_preserved':True,'continuous_traction_projection_not_done':True,
    'exact_block_energy_update_not_blind_old_cache_reuse':True,'all_added_XYZ_trace_coefficients_free':True,
    'all_element_face_and_edge_spaces_refined':False,'full_P3_or_global_h_convergence':False,'other_load_cases_resolved_in_new_space':False,
    'continuum_pressure_or_error_bound':False,'point_reactions_not_area_pressure':True,'Bernstein_bounds_not_directed_rounding_interval_arithmetic':True,
    'CAD_3mm_screws_actual_material_preload_load_inputs_dependencies_workflow_unchanged':True,
    'ideal_remote_frame_fixture_neutralY_and_uncovered_edge_strips_retained':True,
    'initial_spring_force_not_actual_installation_preload':True,'large_private_fields_durable_manifest':'durable-private-fields.json',
    'hosted_CI':load(O/'hosted-summary.json') if (O/'hosted-summary.json').exists() else {'status':'not verified'},
    'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
write(E/'DELIVERY_VERIFICATION.json',final)
(E/'METHOD_AND_LIMITS.md').write_text('''# Method and limits

This experiment adds cubic face functions 27 lambda_i lambda_j lambda_k to selected exterior contact faces of the unchanged L2 volume-interior space. The smaller selected set is contained in the larger one. Selection ranks the prior fixed case6 discrete contact-force resultant per triangle, before either new solve. A per-patch limit is not a guarantee that every patch has that many eligible faces. Actual counts are in the delivery JSON.

Every new face has independent XYZ coefficients. The function is zero on its other faces and at all original P2 nodes; the old volume-space subblock is retained. Shared-face continuity is unit-tested, but actual enrichment here is exterior-only. Other exterior/interior faces and edge-polynomial directions remain unchanged. These are two selected-space solutions of case6, not full P3, complete interface refinement, global h convergence or all original cases.

The previous nodal force and bolt-port functionals are retained. Their action on a bubble which vanishes at every old node is zero. This defines the SAME discrete nodal loading, NOT the action of an independently reprojected continuous surface traction. The old physical load-distribution approximation is not silently upgraded by enlarging displacement space.

The augmented response uses exact block elimination, including changed point-force maps. Both base and augmented full-operator actions are checked. Independent flat child-mesh assembly uses different quadrature and a Voigt strain form. Complete retained/new trace residuals, force/moment balance and independent tetrahedral point-force maps are checked. All private L2 coefficients are recovered; enriched-parent coefficients use independently assembled flat matrices. The hierarchical private coefficients are not total physical displacement without their cubic part.

Only regions on selected faces change from quadratic to cubic. Bernstein subdivision gives convex-hull bounds over ALL fan triangles, with explicit floating-point allowances. The existing quadratic audit is used only on unaffected regions. The independent verifier shares the Bernstein algorithm but rebuilds values through library tetrahedral shape functions and a separately evaluated face bubble. Thus it is not a wholly different polynomial-certification algorithm. The allowances are not directed-rounding interval arithmetic or a continuum certificate. Budget exhaustion is rejected.

Reported displacement and elastic-energy differences are descriptive at the unchanged1e-7mm contact target; residual contact-solve error has not been separated. Point count is not an accuracy metric. Point reactions are not face pressure/stress. Original normalized E/nu, synthetic initial spring force, ideal remote frame fixture, neutralY mode, positive bolt branch and omitted edge strips remain. No actual material, installed preload, service load, friction or strength is assigned.

The old NumPy2D cross-call error, cancelled first solve, and FE-integer cache rejection remain explicit. Full1040/31 canonical current coverage passed without changing source, timeout or dependency. No old native-CAD-task rerun is claimed. Hardware and fabrication flags remain false.
''')
(E/'README.md').write_text('# Selected cubic interface traces\n\nSee DELIVERY_VERIFICATION.json for the two completed case6 selected-space solutions, full1040-test record, and explicit limitations. The source defaults to two faces per patch/body; the second recorded run raises that input cap to four. Actual selected counts may be smaller. No CAD or hardware release.\n')
(E/'PREVIOUS_CURRENT_DESIGN.md').write_bytes((R/'CURRENT_DESIGN.md').read_bytes())
(R/'CURRENT_DESIGN.md').write_text(f'''# 当前研究入口：选定接触面位移增广已获得两档独立全场结果

主线CAD仍为panel_bearing_web与3mm螺钉，真实材料/载荷/预紧、依赖和工作流均未改变。
功能提交{F}通过本机1040项/31组完整回归。新增36项已包含其中。
在L2体内部空间上加入选定接触面三次函数：两档实际为{rows[0]['selected_faces']}/{rows[1]['selected_faces']}个面、{rows[0]['new_trace_dofs']}/{rows[1]['new_trace_dofs']}个XYZ未知量。
它们改变实际面位移空间，不是仅增加接触检查点。两档只重求原工况6，均独立通过原5255个共同区域、完整力/能量和全部私有内部自由度恢复。
三次区域使用Bernstein子三角形界，未受影响区域仍用原二次极值。浮点界不是严格区间或连续体证书。

本轮保留原离散节点载荷函数；新函数在旧节点为零，不代表已重投影真实连续面载荷。
没有完成全界面、单元面/边的完整P3或全局h收敛；其他工况、接触容差分离、真实支撑和载荷仍须推进。
下一步优先统一载荷表示后扩大完整面/边空间，与体细化和接触目标交叉复核；不能把本轮小变化当成物理资格。
证据engineering/trace-enrichment-20261017/DELIVERY_VERIFICATION.json。
框架远端理想固定、Y中性模式、未覆盖边缘、螺钉正拉力分支保持明确。
OLED/B储屏、FPC、主板、双电池及展开锁未闭合。candidate/fixture/manufacturing go均false。
''')
s=load(R/'status.json');s['current_unit_tests']={'manifest':'tools/test_suites.json','configured_minimum':1040,'groups':31,'actual_local_passed':True,'functional_commit':F,'report':'engineering/trace-enrichment-20261017/local-unit1040.json.gz'}
s['current_selected_trace_study']={'evidence':'engineering/trace-enrichment-20261017/DELIVERY_VERIFICATION.json','functional_commit':F,'case':6,'actual_faces':[x['selected_faces'] for x in rows],'new_trace_dofs':[x['new_trace_dofs'] for x in rows],'both_full_field_audits_passed':True,'full_interface_or_continuum_convergence':False,'load_functionals':'unchanged discrete nodal functions, not a new continuous traction projection'}
for k in ('candidate_go','fixture_fabrication_go','manufacturing_go'):s[k]=False
write(R/'status.json',s)
print('TRACE_DELIVERY_READY',F,1040,'ACTUAL_FACES',[x['selected_faces'] for x in rows],'TWO_INDEPENDENT_CASE6_SOLUTIONS',flush=True)
