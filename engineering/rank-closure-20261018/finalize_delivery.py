"""Seal independently completed strict fields; never mutate tested core files."""
from pathlib import Path
import datetime, gzip, hashlib, json, shutil, subprocess, tarfile
R=Path('/home/qian-qi/RAZR-SLIDE-rank-delivery-20261018')
B=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-followup-20261018')
E=R/'engineering/rank-closure-20261018'
COMMIT='4b180d500be53ad7ab07905d6adc35dfd8945be0'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def dump(p,data):p.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def copy(src,dst):
    assert src.is_file() and not src.is_symlink(),src
    shutil.copyfile(src,dst)
    assert sha(src)==sha(dst)
def pack(target,paths,root):
    with tarfile.open(target,'w:gz') as tar:
        for p in paths:
            if p.is_file() and not p.is_symlink():tar.add(p,arcname=str(p.relative_to(root)))
    assert target.stat().st_size<95*1024*1024,('archive too large',target)
s=json.loads((O/'four-cell-summary.json').read_text())
assert s['all_four_cells_independently_passed']
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==COMMIT
u=json.loads((B/'current/unit1137/report.json').read_text())
assert u['base_commit']==COMMIT and u['tests_run']==1137 and u['passed'] and len(u['suite_results'])==31
assert u['source_hashes_before']==u['source_hashes_after'] and not u['changed_during_tests']
for name,h in u['source_hashes_after'].items():assert sha(R/name)==h,('changed tested input',name)
jobids=['1a14d8bee0d-1b6abb-d8e','1a14d8c33fb-1b6abb-d92','1a14d8f2a51-1b6abb-dab']
jobroot=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs')
records=[]
for jid in jobids:
    ex=json.loads((jobroot/jid/'exit.json').read_text());assert ex['exit_code']==0,(jid,ex)
    records.append({'job_id':jid,'exit':ex})
assert not E.exists();E.mkdir()
for name in ['summarize_verified_study.py','four-cell-summary.json','test_identity_readback.json','same-space-preflight.json','hosted-status.json','diagnostic-scope.json','capture_next.py','capture_next_scope_fixed_not_executed.py','input-identity.json','finalize_delivery.py']:
    copy(O/name,E/name)
for name in ['capture_actual_fallback.py','compare_captured_system.py','rank-comparison.json','null-pivot-diagnostic.json','captured-qp-independent.json','captured-qp-pivot-result.json','resume_strict_v2.py','verify_rank_field.py','audit_strict_pair.py','durable-volume-identity.json']:
    copy(B/'current'/name,E/name)
copy(B/'current/capture256/capture.json',E/'actual-capture.json')
(E/'local-unit1137.json.gz').write_bytes(gzip.compress((B/'current/unit1137/report.json').read_bytes(),mtime=0))
pack(E/'unit1137-raw-logs.tar.gz',sorted((B/'current/unit1137').rglob('*')),B/'current/unit1137')
large=[]
for sides in (256,512):
    src=B/f'strict{sides}-v2';ad=B/f'audit{sides}-v2';dest=E/f'strict-{sides}';dest.mkdir()
    for name in ['report.json','progress.json','selection.json','reconstructed-checkpoint.json','reconstructed-points.json','full-fields.npz','exact-energy-update.json']:
        copy(src/name,dest/name)
    for name in ['panel','frame']:shutil.copytree(src/name,dest/name)
    copy(ad/'report.json',dest/'independent-report.json')
    (dest/'independent-regions.json.gz').write_bytes(gzip.compress((ad/'regions.json').read_bytes(),mtime=0))
    for f in sorted(ad.glob('*private.npz')):
        large.append({'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f),'kind':'restored_private_coefficients'})
    for f in [src/'reconstructed-C.npz',src/'reconstructed-response.npz']:
        large.append({'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f),'kind':'reconstructed_optimizer_input'})
    pack(dest/'exchange-traces.tar.gz',sorted(src.glob('gaps-*.json'))+sorted(src.glob('qp-*.json')),src)
    partials=sorted(src.glob('field-*.npz'))
    for i in range(0,len(partials),6):pack(dest/f'partial-fields-{i:03d}.tar.gz',partials[i:i+6],src)
    for f in [B/f'audit{sides}-v2.log',B/f'audit{sides}-v2.exit']:copy(f,dest/f.name)
for f in [B/'current/capture256/fallback-system.npz']:
    large.append({'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f),'kind':'actual_failed_active_linear_and_full_QP_arrays'})
dump(E/'durable-large-field-manifest.json',{'files':large,'bytes':sum(x['bytes'] for x in large),'not_copied_into_git_or_conversation':True})
failedjobs=['1a14d9bfd8d-1b6abb-dfc','1a14da52676-1b6abb-e25','1a14daa3edb-1b6abb-e37']
for jid in failedjobs:
    ex=json.loads((jobroot/jid/'exit.json').read_text());records.append({'job_id':jid,'diagnostic_or_evidence_preparation_only':True,'exit':ex})
pack(E/'runtime-logs.tar.gz',[jobroot/jid/name for jid in jobids+failedjobs for name in ['stdout.log','stderr.log','exit.json']],jobroot)
corepaths=['integration/contact_dual_active.py','integration/rank_fallback.py','engineering/trace-enrichment-20261017/solve_trace_probe.py']
core={p:sha(R/p) for p in corepaths}
summary={'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PR':32,'base_main':'fb95a3b9a7d58849303287d7321bb7846254f029',
 'tested_functional_commit':COMMIT,'full_tests':1137,'suites':31,'prior_completed_tests_all4294_files_revalidated_now':True,'tests_not_reexecuted_this_followup':True,
 'all_four_cells_independently_passed':True,'old_target_cases_prior_verified_baselines_not_rerun':True,
 'strict_results':[{k:row[k] for k in ['circle_sides','gap_target_mm','contact_constraints','new_exchange_solves','independent_gap_bound_mm','common_512_external_observation','elastic_energy','bolt_forces','full_checks']} for row in s['cases'] if row['gap_target_mm']==2e-8],
 'effects':s['effects'],'interaction':s['interaction'],'unit_report_sha256':sha(B/'current/unit1137/report.json'),'core_sha256':core,'runtime_jobs':records,
 'same_frozen86_faces258_coefficients':True,'all_contact_unilateral_constraints_retained':True,'working_force_releases_not_constraint_deletions':True,
 'default_rank_fallback_svd_optional_qr_pivot_only':True,'regularization_added':False,'gap_or_KKT_thresholds_relaxed':False,
 'large_files':len(large),'large_bytes':sum(x['bytes'] for x in large),'supplementary_capture_and_evidence_script_failures_preserved':True,
 'hosted_CI':json.loads((O/'hosted-status.json').read_text()),'CAD_actual_material_load_preload_screws_dependencies_workflow_unchanged':True,
 'full_interface_volume_continuum_or_hardware_qualification':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
dump(E/'DELIVERY_VERIFICATION.json',summary)
method='''# Rank-aware strict contact continuation

The first failed active system and full force QP were captured after identity-checked replay. QR and SVD on that captured 2714-row system both estimated rank 2713 at cutoff 1e-13 and satisfied the original residual. This does not claim rank-estimator agreement on every matrix. The optional null-direction pivot changes only a feasible working-force vector, moves a unilateral force to zero, and retains that contact in the complete constraint/admission loop. Complete KKT and full-field checks remain required. Default SVD behavior remains.

Two already running original case6 jobs were continued to their terminal states and independently audited. No duplicate baseline solve was launched in this follow-up. Earlier 256/512 polygon baselines at 1e-7 mm are distinguished from the new 2e-8 mm fields. Comparisons use the same frozen 86 faces, 258 coefficients, L2 energy and common 512-external-work observation. Four-cell changes are descriptive sensitivity, not continuum error bounds, pressure estimates or rated capacity.

The normalized materials, prescribed affine bolt-pressure weighted displacement, synthetic initial spring force, positive tensile branch, ideal remote frame fixation, neutral Y mode and omitted edge strips remain assumptions. Point reactions are not area pressures, and numerical gap tolerances are not manufacturing precision.

Full 1137 tests were completed at 4b180d5 before this follow-up. The raw report and all 4294 recorded source files were revalidated against the isolated delivery tree; they are not counted as another 1137 executions. Evidence-only additions follow that check. Large failed-system and recovered private arrays remain in durable host storage with exact hashes; they have not been copied to the conversation.

An auxiliary next-capture wrapper collided with a local stiffness-variable name and exited 1 before replay. The original script and logs are retained. A renamed copy was syntax checked, not executed, because the live strict solves passed that replay point. Two evidence-preparation commands also failed due quoting/missing-file errors, changed no functional source, and retain their exit records. None is relabeled as a successful physical or numerical check. The earlier actual 2714 system is separately verified evidence.
'''
(E/'METHOD_AND_LIMITS.md').write_text(method)
current=R/'CURRENT_DESIGN.md';copy(current,E/'PREVIOUS_CURRENT_DESIGN.md')
current.write_text('''# Current research: stricter frozen-space contact closure

See engineering/rank-closure-20261018/DELIVERY_VERIFICATION.json and four-cell-summary.json. Both original normalized case6 head-circle 256/512 representations now have independent full-field results at 2e-8 mm in the same frozen 86-face/258-coefficient L2 model, alongside explicitly prior 1e-7 mm baselines. This closes the predeclared four-cell numerical study, not global contact/trace/volume convergence, actual pressure, installed preload or hardware capacity.

The optional rank-aware working-set pivot releases a force that reaches zero while retaining all unilateral constraints. Default SVD, full KKT checks and target tolerances remain. Full 1137 tests/31 suites at 4b180d5 were read back with all recorded source hashes; no new full rerun is implied by this evidence-only commit. CAD, 3mm fasteners, actual physical unknowns, dependencies and workflow remain unchanged. candidate_go=false; fixture_fabrication_go=false; manufacturing_go=false.

Next separate discretization sensitivity from physical pressure, support and preload assumptions, then evaluate other original cases rather than treating this single case as universal capacity. Large inputs and fields require identity-checked restoration from recorded durable locations.
''')
for p,h in core.items():assert sha(R/p)==h
for p in E.rglob('*'):
    if p.is_file():assert p.stat().st_size<95*1024*1024,('oversize Git file',p)
print('READY_TO_PUBLISH_COMPLETE_STRICT_STUDY',json.dumps(summary['effects']),flush=True)
