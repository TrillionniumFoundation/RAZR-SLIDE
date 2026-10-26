from pathlib import Path
import copy, datetime, hashlib, json, subprocess

R=Path('/home/qian-qi/RAZR-SLIDE-product-integration-20261018')
E=Path('/home/qian-qi/.local/share/razr-slide-evidence/product-followup-20261020-phase4')
D='engineering/product-integration-20261018'; P=D+'/phase4-20261020'
N='9a8307fe4bd4163b53515698fb12cfc0a8cc27e7';M='90b09f5ef7c25aafd812909101b3d7d80081ba05'
PY='/home/qian-qi/.local/share/razr-slide-evidence/product-integration-20261018/venv-recheck-20261019/bin/python'
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==N
n=read(R/P/'native-summary.json');u=read(E/'unit-9a8307f/report.json');ur=read(E/'unit-execution-9a8307f/execution.json')
a=read(E/'a-head-relief-9a8307f/report.json');key=read(E/'key-local-study-9a8307f/native/native-report.json')
small=read(E/'small-native-9a8307f/native-regression/native-regressions.json')
ci=read(E/'actions-90b09f5-final/report.json');cs=ci['summary']
assert u['tests_run']==137 and u['passed'] and n['all_three_poses_rejected']
assert cs['actual_run_head']==M and len(cs['jobs'])==len(cs['billing_block_job_ids'])==12
assert not cs['successful_hosted_report'] and not any(j['executed_step_records'] for j in cs['jobs'])
unit_entry={'label':'Product branch phase4: 137 relevant tests PASS','functional_commit':N,
 'scope':'product108_routing14_EP3_7_EP4_8','tests':137,'suites':4,'passed':True,'result':'PASS',
 'single_full_execution':False,'failures':0,'errors':0,'skipped':0,'in_main':False,
 'seconds':ur['seconds'],'source_bytes_unchanged':True,'report':P+'/validation/unit/report.json.gz',
 'uncompressed_report_sha256':sha(E/'unit-9a8307f/report.json'),'hardware_qualification':False,
 'candidate_go':False,'manufacturing_go':False}
local={
 'A_head_relief':{'script':P+'/local-studies/ep4_a_head_relief.py',
    'report':P+'/local-studies/A-head-relief/report.json.gz',
    'checks_passed':a['local_declared_geometry_checks_passed'],'removed_mm3':a['material_accounting']['removed_mm3'],
    'added_mm3':a['material_accounting']['added_mm3'],'head_common_before_mm3':a['head_Common_mm3']['original'],
    'head_common_after_mm3':a['head_Common_mm3']['revised'],'self_pairs':190},
 'KEY_closed_end':{'script':P+'/local-studies/key-source/key_endcap_local_study.py',
    'report':P+'/local-studies/KEY/native/native-report.json.gz',
    'checks_passed':key['all_declared_local_checks_passed'],'checks':len(key['checks']),
    'failure_count':len(key['declared_failures']),'source_bytes_unchanged':key['source_bytes_unchanged'],
    'nominal_side_gap_request_mm':.2,'manufacturing_tolerance_or_strength_qualified':False},
 'baseline_three_pose_assemblies_modified':False,'whole_scene_recomputed_with_local_changes':False,
 'current_PAWL_interlock_and_relocking_verified':False,'physical_parts_built':False,
 'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for label in ['a-head-relief','key-local']:
    p=E/('readback-'+label+'-9a8307f')/'report.json';v=read(p)
    assert v['execution_completed'] and v['declared_readback_checks_passed']
    local[label+'_independent_readback']={'passed':True,
        'report':P+'/validation/readback-'+label+'/report.json.gz',
        'uncompressed_sha256':sha(p),'scope':'all declared nonempty artifact solid counts, validity and injective bounds/volume; no topological or label identity proof'}
ep4={'state':'three_pose_native_completed_rejected_local_followups_separate','source_commit':N,
    'native_summary':P+'/native-summary.json','raw_reports':n['raw_reports'],
    'all_three_poses_rejected':True,'unique_declared_pairs':n['unique_declared_pairs'],
    'actual_declared_pairs_across_two_executions':n['actual_declared_pairs_across_two_executions'],
    'pair_evaluation_errors':n['pair_evaluation_errors'],'containment_evaluation_errors':n['containment_evaluation_errors'],
    'independent_STEP_readback_executed':True,'all_assembly_parts_have_metric_comparison':True,
    'independent_readbacks':n['independent_readbacks'],'local_studies':local,
    'full_cycle_internal_route_accepted':False,'physical_fabrication_executed':False,
    'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
c=read(R/'design/current_product.json')
c.setdefault('historical_product_executions',[]).append(copy.deepcopy(c['latest_product_execution']))
c['prior_phase3_active_followup']=copy.deepcopy(c['active_followup'])
c.setdefault('historical_publication_records',[]).append({'record':c.get('publication_record'),'scope':c.get('publication_record_scope'),'preserved_before_phase4':True})
c['publication_record']=P+'/validation/ep4-source-commit.json'
c['current_execution_summary']=P+'/SUMMARY.json'
c['completed_unit_runs'].append(unit_entry)
c['stage_summary']='PR36 now contains EP4 S+U routing and complete endpoints executed on 9a8307f, plus a physical-evidence anchor fix. All three finite assemblies remain rejected, although outer-domain escape and all material/end and A/B-end intersections are absent at these poses. Every assembly body has an independent STEP numeric comparison. A head relief and KEY closed-end studies are separate local candidates. The actual XT2551-3 donor still lacks physical labels, geometry and all 12 terminal-interface bindings. Main remains a1b3cc1; PR35 remains separate draft research; PR25 is closed unmerged.'
c['verification_summary']=(
 'On 9a8307f, 137 relevant tests in four suites passed with zero failures/errors/skips and unchanged source bytes; configured 1324 tests / 35 suites are not a full new run. '
 'Seven bounded native regression groups passed. PREDOCK and OPEN/STOW ran separately on the same unchanged source, retaining '+str(n['actual_declared_pairs_across_two_executions'])+' declared pair evaluations including repeated endpoint-self checks; '+str(n['unique_declared_pairs'])+' unique pose/self pair declarations. '
 'STOW/PREDOCK/OPEN have 154/154/161 bodies and 17/12/25 external positive Common pairs, with zero pair/context/containment evaluation errors and no outside-outer-domain parts. '
 'Baseline A has one 0.180811856-mm3 screw-head/web self Common; B self, A/B end and all finite-material/end pairs are clear at the selected poses. '
 'Independent STEP processes passed all recorded assembly-body metrics plus exported positive Common and local material contexts. These are numeric comparisons, not full material or label equivalence. '
 'Separate A head relief removes 0.269207426 mm3, adds zero, clears 190 local self pairs and retains finite side-web/bearing probes. KEY local results and independent readers have their own source/report identities and do not replace the rejected whole-scene baseline. '
 'The old 18-mm3 A-cell allocation overlap is absent in EP4; the old PREDOCK outer-domain escape is absent. New B board/shell and OPEN frame intersections, STOW OLED/FPC overlap and other real obstacles remain. '
 'The source evidence bug now prevents OEM documents alone from establishing physical donor observations. Actual donor data and terminal states remain unchanged. '
 'All prior failed/native/unit records retain their historical commits and scopes. Run 39378151409 on prior publication 90b09f5 settled at 12 new failed jobs, no runner steps and 12 direct payment-or-spending annotations. New publication-head CI is recorded separately in PR36. '
 'No physical prototype, material/strength qualification, full phone motion, modified powered phone or new FE/QP solve is claimed.')
c['latest_product_execution']={'phase':'phase4-20261020','execution_summary':P+'/SUMMARY.json',
 'functional_commit':N,'native_execution_commit':N,'selected_product_unit_execution':unit_entry,
 'EP4':ep4,'native_CAD_reports_completed':True,'physical_phone_verified':False,
 'source_commit_is_executed_functional_identity':True,'full_local_unit_execution_passed':False,
 'hosted_execution_restored':False,'candidate_go':False,'manufacturing_go':False}
for historical_key in ['bounded_EP3_API_repair_passed','selected_109_test_commit','selected_109_tests_passed']:
 c['active_followup'].pop(historical_key,None)
c['active_followup'].update(scope='EP4 three-pose native, physical-evidence fix and separate local A/KEY studies',
 execution_summary=P+'/SUMMARY.json',state='bounded_native_and_local_studies_complete_physical_acceptance_open',
 functional_commit=N,native_execution_commit=N,native_verification_complete=True,
 native_verification_scope='bounded computations and independent numeric readback completed; whole candidate rejected',
 selected_137_test_commit=N,selected_137_tests_passed=True,
 full_local_unit_execution_passed=False,hosted_execution_restored=False)
c['product_pull_request'].update(evidence_commit=N,functional_commit=N,native_execution_commit=N,
 evidence_commit_scope='actual EP4/unit execution source; final evidence publication and its post-push hosted observation are recorded in PR36')
prior=c['hosted_ci']['product_PR36']
if not any(x.get('run_id')==prior['run_id'] for x in c['hosted_ci']['previous_product_runs']):c['hosted_ci']['previous_product_runs'].append(prior)
hosted={'run_id':39378151409,'run_attempt':1,'head_sha':M,
 'url':'https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39378151409',
 'conclusion':'failure','job_records':12,'newly_attempted_jobs':12,'inherited_job_results':0,
 'steps_executed':0,'billing_block_jobs':12,'current_failure_cause_verified':True,
 'cause':'direct provider annotation: account payments failed or spending limit needs increasing; account settings not read',
 'successful_hosted_report':False,'evidence':P+'/actions/90b09f5-run39378151409-final.json',
 'report_sha256':sha(E/'actions-90b09f5-final/report.json')}
c['hosted_ci'].update(product_PR36=hosted,billing_reason_source=hosted['evidence'],
 billing_reason_source_scope='Exact prior publication head 90b09f5, run39378151409 completed: all 12 new jobs have zero steps and direct payment-or-spending annotations. Early 11-job queued snapshot is retained as history.',
 archive_scope='last settled publication-head report archived here; this publication head is inspected and recorded separately in PR36')
results={
 'WP0':('Current entries distinguish EP4 native source, 137 selected tests, local A/KEY studies and exact prior/new publication hosted heads.',P+'/README.md','Resolve account payment/spending condition and obtain actual runner steps; keep main, PR35 and closed PR25 identities separate.'),
 'WP1':('The existing formal XT2551-3 partial readback is preserved. A reproduced validator bug was fixed: OEM documents alone cannot establish physical labels, components or terminals.',P+'/reviews/phase4-platform-physical-handoff.md','Obtain same-specimen physical labels, dimensions, heights, exits and terminals for the 10 unknown identity fields, 7 part roles and 12 interfaces.'),
 'WP2':('EP4 includes 154/154/161 finite bodies; independent readbacks now cover every recorded body metric. A-cell 18-mm3 overlap is absent, but B board/shell and OPEN frame overlaps remain.',P+'/native-summary.json','Freeze actual geometry and redesign B board placement/stack/orientation with RF, heat and cell swelling/tabs. The current b/L-only behind-wall branch has no feasible interval.'),
 'WP3':('The actual STOW finite FPC has 0.713045601 mm3 Common with the OLED geometric trial; screen/FPC integration is explicitly unfinished.',P+'/native-summary.json','Jointly redesign OLED storage, COF, support and FPC using actual material dimensions and supplier bending conditions.'),
 'WP4':('EP4 preserves both complete 20-body ends. Selected poses have no material/end or cross-end Common and no outer escape, while all whole-scene states are rejected. A local relief clears the head/web Common.',P+'/README.md','Change the remaining full endpoint and path arrangement, define fastener retention and actual conductor/material stack, then check continuous forward and return states.'),
 'WP5':('A head clearance and a KEY closed-end finite capture study provide separate local geometry evidence; original whole-device and current PAWL relocking qualification remain open.',P+'/local-studies/README.md','Select real processes and joining details; incorporate approved local changes into a new common assembly and prove actual ordered assembly, release/hold/skew/return.'),
 'WP6':('All 12 physical terminal interfaces remain unbound. Source classification is hardened without changing the actual donor record or original protected-chain assumptions.',P+'/reviews/phase4-platform-physical-handoff.md','Bind original protected power/charging, USB, OLED and touch terminals; capture baseline and moving continuity logs from actual hardware.'),
 'WP7':('An independent bounded constraint study excludes the fixed S+U behind-wall b/L relocation branch; A web material accounting has an analytic/native cross-check. No new FE/QP was launched.',P+'/reviews/ep4-b-anchor-and-a-web-followup.md','Use measured materials, spans and forces for structural study; restore identified PR35 cache before a separately bounded restart.'),
 'WP8':('Full EP4 STEP/Common artifacts, local A/KEY studies, independent readers and execution receipts are retained. No complete physical opening/closing assembly has been observed.',P+'/README.md','Build dimension/process specimens and unpowered assemblies after the real geometry/joining gates, then flexible samples and original protected electronics; return original calibrated logs.')}
for w in c['work_packages']:
    w['result'],w['path'],w['remaining']=results[w['id']]
c['publication_record_scope']='functional source9a8307f is fixed; this evidence publication and its post-push CI are recorded by containing commit and PR36'
write(R/'design/current_product.json',c)
summary={'schema':'razr-phase4-summary-v1','updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'functional_source_commit':N,'previous_publication_commit':M,'EP4':ep4,'selected_unit_execution':unit_entry,
 'configured_tests':1324,'configured_suites':35,'full_registry_rerun':False,'hosted_prior_publication':hosted,
 'physical_platform_frozen':False,'physical_phone_verified':False,'physical_prototype_built':False,
 'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
 'artifact_index':P+'/artifact-index.json','publication_identity_scope':'containing Git commit and PR36; executed sources retain N'}
write(R/P/'SUMMARY.json',summary)
write(R/P/'local-studies/SUMMARY.json',local)
entry=R/D/'README.md'
assert sha(entry)=='df21ea3bd9db67225ff80e222d8877b2be6e263b0d6689f57deefd9d3678c344'
old_entry=entry.read_text()
entry.write_text('> 当前交付见 [2026-10-20 第四阶段](phase4-20261020/README.md)：EP4 三态原生与独立回读、物理证据修复、A/KEY 局部改形。此前[第三阶段](phase3-20261020/README.md)和[第二阶段](phase2-20261019/README.md)保留各自执行身份。本页正文与 DELIVERY_VERIFICATION.json 是第一阶段历史快照，其中“本轮”“最新”和空 donor 观测均限于原日期；当前状态以第四阶段和根目录生成入口为准。\n'+old_entry.split('\n',1)[1])
subprocess.run([PY,'-B','tools/sync_current_design.py'],cwd=R,check=True)
receipt={'native_source_commit':N,'metadata_sha256':sha(R/'design/current_product.json'),
 'current_summary_sha256':sha(R/P/'SUMMARY.json'),'candidate_go':False,'manufacturing_go':False,
 'local_KEY_declared_checks_passed':key['all_declared_local_checks_passed']}
write(E/'phase4-state-update-receipt.json',receipt)
print(json.dumps(receipt,indent=2))
