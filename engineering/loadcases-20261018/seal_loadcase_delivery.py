"""Publish compact verified cases only after all actual source/audit/test outcomes exist."""
from pathlib import Path
import datetime,gzip,hashlib,json,shutil,subprocess,tarfile
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-schur-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
E=R/'engineering/loadcases-20261018'
FUNCTIONAL='26539a79b953bdd0b6978551f13c3361f13853b6'
INITIAL='e54d71cc2c838091e9c6b20c1063acf1049e9a06'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def copy(src,dst):
 src=Path(src);dst=Path(dst);assert src.is_file() and not src.is_symlink();assert not dst.exists(),dst
 shutil.copyfile(src,dst);assert sha(src)==sha(dst)
def archive(dest,paths,root):
 assert not dest.exists()
 with tarfile.open(dest,'w:gz') as tar:
  for p in paths:
   if p.is_file() and not p.is_symlink():tar.add(p,arcname=str(p.relative_to(root)))
 assert dest.stat().st_size<95*1024*1024
s=json.loads((O/'nine-case-summary.json').read_text());assert s['coverage']['all_current_model_states_passed'] and len(s['cases'])==9
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==FUNCTIONAL
unit=json.loads((O/'unit1157/report.json').read_text())
assert unit['passed'] and unit['tests_run']==1157 and len(unit['suite_results'])==31 and unit['base_commit']==FUNCTIONAL
assert unit['source_hashes_before']==unit['source_hashes_after'] and not unit['changed_during_tests']
for p,h in unit['source_hashes_after'].items():assert sha(R/p)==h,('changed tested input',p)
assert not (E/'DELIVERY_VERIFICATION.json').exists()
for name in ['run_original_cases.py','audit_all_cases.py','verify_original_case.py','audit_schur_reference.py','summarize_cases.py','summarize_cases_initial_unexecuted.py','nine-case-summary.json','assembly-capture-inputs.json','capture_assembly_rank.py','assembly-executed-capture.py','analyze_assembly_fallback.py','assembly-fallback.json','assembly-rank-analysis.json','assembly-captured-qp-result.json','assembly-captured-independent-kkt.json','assembly-reference-schur-source.json','independent-source-inputs.json','prepare_failed_v1.py','prepare_v2.py','new12.log','new12.exit','schur8.log','schur8.exit','run_complete_units1149.py','run_complete_units1157.py','run-source-identity.json','two-complete-regression-identities.json','case6-control-comparison.json','solve-status.json','audit-status.json','seal_loadcase_delivery.py']:
 copy(O/name,E/name)
for n,commit in [(1149,INITIAL),(1157,FUNCTIONAL)]:
 p=O/f'unit{n}/report.json';u=json.loads(p.read_text());assert u['passed'] and u['tests_run']==n and u['base_commit']==commit
 (E/f'local-unit{n}.json.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0))
 archive(E/f'unit{n}-raw-logs.tar.gz',sorted((O/f'unit{n}').rglob('*')),O/f'unit{n}')
common=E/'common-space';common.mkdir()
for body in ['panel','frame']:shutil.copytree(O/'case-0'/body,common/body)
common_hash={str(p.relative_to(common)):sha(p) for p in common.rglob('*') if p.is_file()}
dump(E/'common-space-index.json',common_hash)
large=[];region_checks=0
for row in s['cases']:
 label=row['source_label'];src=O/label;ad=O/('audit-'+label);dest=E/row['id'];dest.mkdir()
 for name in ['report.json','full-fields.npz','selection.json','progress.json','exact-energy-update.json']:
  copy(src/name,dest/name)
 copy(ad/'report.json',dest/'independent-report.json')
 (dest/'independent-regions.json.gz').write_bytes(gzip.compress((ad/'regions.json').read_bytes(),mtime=0))
 region_checks+=5255
 for f in [O/(label+'.log'),O/(label+'.exit'),O/('audit-'+label+'.log'),O/('audit-'+label+'.exit')]:copy(f,dest/f.name)
 for f in [O/(label+'-command.json'),O/('audit-'+label+'-command.json')]:
  if f.exists():copy(f,dest/f.name)
 # The summary already proves equality of all selections, coupling and energy/load arrays.
 # Record actual source hashes; raw NPZ metadata need not be byte-identical.
 source_hash={str(p.relative_to(src)):sha(p) for body in ['panel','frame'] for p in (src/body).rglob('*') if p.is_file()}
 dump(dest/'body-space-source-index.json',{'compact_common_space':'../common-space','actual_source_directory':str(src),'source_sha256':source_hash,'same_numerical_arrays_and_selection_verified':True})
 archive(dest/'exchange-diagnostics.tar.gz',sorted(src.glob('qp-*.json'))+sorted(src.glob('gaps-*.json')),src)
 for p in sorted(ad.glob('*private.npz'))+sorted(src.glob('field-*.npz')):
  large.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'role':'independently_recovered_private_field' if p.parent==ad else 'intermediate_exchange_field'})
# Retain the actual blocked first assembly attempt, not a reclassified success.
rejected=E/'original-assembly-timeout';rejected.mkdir()
for name in ['assembly-reference.log','assembly-reference.exit','assembly-reference-command.json']:copy(O/name,rejected/name)
for name in ['progress.json','field-000.npz','gaps-000.json','qp-000.json']:
 p=O/'assembly-reference'/name
 if p.exists():copy(p,rejected/name)
for p in [O/'assembly-fallback.npz',O/'assembly-small-schur-candidate.npz']:
 large.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'role':'actual_assembly_dependent_equality_system_or_diagnostic_solution'})
dump(E/'durable-large-field-manifest.json',{'files':large,'bytes':sum(x['bytes'] for x in large),'host':'qian-qi','not_included_in_git_or_conversation':True})
jobroot=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs')
ids=['1a14dc1505e-1b6abb-e91','1a14dc4aab9-1b6abb-ea0','1a14dc201ad-1b6abb-e94','1a14dda6617-1b6abb-ef8','1a14dce418c-1b6abb-ecc','1a14dd51c1c-1b6abb-eeb','1a14dd98dfa-1b6abb-ef4','1a14dde600c-1b6abb-f04','1a14ddf7789-1b6abb-f0f','1a14dbf63d7-1b6abb-e8b']
job_records=[]
for jid in ids:
 ex=json.loads((jobroot/jid/'exit.json').read_text());job_records.append({'job_id':jid,'exit':ex})
 if jid not in ['1a14dc1505e-1b6abb-e91','1a14dc4aab9-1b6abb-ea0','1a14dbf63d7-1b6abb-e8b']:assert ex['exit_code']==0,(jid,ex)
archive(E/'runtime-terminal-logs.tar.gz',[jobroot/jid/f for jid in ids for f in ['stdout.log','stderr.log','exit.json']],jobroot)
copy(jobroot/'1a14dd98dfa-1b6abb-ef4'/'stdin.bin',E/'executed_captured_assembly_qp_check.py')
method='''# Original loadcase and unloaded assembly reference study

Eight normalized original cases use the same frozen 86 faces / 258 added XYZ coefficients, L2 energy, 512-sided load representation and 1e-7 mm target. Cases 0–3 use zero initial spring parameter; 4–7 use 2e-4. All eight were freshly solved at e54d71c and independently audited. The unloaded assembly reference was freshly solved at 26539a7 after a separately diagnosed active-equality fix. These are distinct software identities but equal physical energy, boundary/trace space and load maps, checked array by array. The eight earlier fields were not rerun after the optional linear-equality change. Final 1157 tests / 31 suites were freshly executed on 26539a7, not substituted from the earlier 1149 run.

The first unloaded attempt hit its 1800-second limit. Identity-checked first-field replay captured its 2598-row working system: the force Hessian block was positive definite while five active equality rows had rank three. Solving the five-row Schur system with rank-revealing QR and retaining the original full KKT residual avoids repeatedly factorizing the singular augmented matrix. The reduction is local to a working system: every original equality, unilateral constraint and admission test remains. No penalty, false support or stiffness regularization is added. It is enabled only on the optional qr_pivot path; default behavior remains unchanged. The actual 3989-variable QP also passed a separate algebraic recomputation of its original KKT inequalities in the same process that called the solver; it is not claimed to be a no-solver-import independent process.

Zero external load with a given initial spring parameter is an independently equilibrated research reference. It is not measured installation preload, a tightening/lock-length procedure or an actual load-path experiment. The equilibrium force divided by the initial parameter is model redistribution, not measured relaxation. Incremental bolt forces are referenced to that state; the no-initial-force cases reference the exact zero-load/zero-force algebraic state. Those force-transfer ratios are not assumed equal among bolts, not capacity limits, and weighted displacement values include free-play and rigid-body placement. They are not tangent stiffnesses or unique loading histories.

Ideal remote frame fixation, the neutral Y mode, prescribed pressure-weighted springs, positive accepted bolt branch, normalized E and nu, selected trace functions and omitted edge strips remain assumptions. Point forces are not continuum pressure. No actual material, screw/preload/torque, CAD or service-load data were invented. All hardware and manufacturing go flags remain false.

Each accepted field was independently reconstructed using tetrahedral basis maps, independently checked local energy/projection inputs, complete force and moment balance, all 5255 gap regions, bolt spring relations and full recovery of 4,321,500 panel plus 5,972,100 frame private coefficients. The cubic Bernstein checker is shared with independently reconstructed values; no interval-arithmetic or continuum certificate is claimed. Existing independent element/projection archives were hash-revalidated as inputs, not counted as new standalone tests. Large raw fields and the captured system are in durable host storage with exact hashes; compact same-space arrays are stored once in common-space.

A first preparation command incorrectly assumed a module-level helper import and exited at an assertion. Its partial source was restored from the recorded baseline and corrected before tests/commits. That preparation failure and the original reference timeout are retained as failures, not relabeled passes. The original nine-run supervisor and its audit supervisor correctly report failure because their initial reference timed out; accepted reference qualification comes only from the separately identified replacement run/audit.
'''
(E/'METHOD_AND_LIMITS.md').write_text(method)
corepaths=['integration/contact_dual_active.py','integration/rank_fallback.py','engineering/trace-enrichment-20261017/solve_trace_probe.py','engineering/consistent-load-20261017/surface_archive.py','tools/test_suites.json']
cores={p:sha(R/p) for p in corepaths}
summary={'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PR':33,'base_main':'15d3286e0eff22eaa717993eef0c3736bb9ecc93','tested_functional_commit':FUNCTIONAL,
 'original_eight_fields_functional_commit':INITIAL,'eight_original_cases_freshly_solved_this_turn':True,'eight_fields_not_rerun_after_optional_equality_fix':True,
 'final_full_tests':1157,'suites':31,'new_tests_included':20,'latest_tests_freshly_rerun':True,'prior1149_not_substituted':True,
 'source_snapshots_unchanged':True,'test_report_sha256':sha(O/'unit1157/report.json'),'coverage':s['coverage'],
 'preload_reference':s['preload_reference'],'load_to_bolt_transfers':s['load_to_bolt_transfers'],
 'source_cases':[{'id':x['id'],'commit':x['source_functional_commit'],'minimum_gap_bound_mm':x['minimum_gap_bound_mm'],'contact_constraints':x['contact_constraints'],'finite_exchange_solves':x['finite_exchange_solves'],'bolt_forces_over_Epanel_mm2':x['bolt_forces_over_Epanel_mm2']} for x in s['cases']],
 'accepted_region_field_checks':region_checks,'original_assembly_timeout_preserved':True,'original_supervisor_failure_not_relabelled':True,
 'captured_rank_analysis':json.loads((O/'assembly-rank-analysis.json').read_text()),'actual_QP_KKT':json.loads((O/'assembly-captured-independent-kkt.json').read_text()),
 'core_sha256':cores,'jobs':job_records,'large_files':len(large),'large_bytes':sum(x['bytes'] for x in large),
 'CAD_screws_actual_physical_unknowns_dependencies_workflow_unchanged':True,'no_new_hardware_or_supplier_action':True,
 'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
if (O/'hosted-status.json').exists():copy(O/'hosted-status.json',E/'hosted-status.json');summary['hosted_CI']=json.loads((O/'hosted-status.json').read_text())
dump(E/'DELIVERY_VERIFICATION.json',summary)
current=R/'CURRENT_DESIGN.md';copy(current,E/'PREVIOUS_CURRENT_DESIGN.md')
current.write_text('''# Current research: original loadcases and unloaded assembly reference

See engineering/loadcases-20261018/DELIVERY_VERIFICATION.json, nine-case-summary.json and METHOD_AND_LIMITS.md. Eight original normalized loadcases and an unloaded assembly reference now have independent whole-field evidence on the same fixed 86-face/258-coefficient L2 space with 512-sided prescribed load domains and 1e-7 mm gap target. This is not global trace/volume convergence or hardware capacity.

The initial spring parameter is distinguished from equilibrated assembly force; per-bolt transfer ratios are not equal-sharing assumptions or installed preload measurements. A residual-checked small-Schur solve handles dependent active equalities only in optional qr_pivot mode. All original support/equality/contact conditions remain. Fresh complete 1157 tests / 31 suites on 26539a7 and explicit e54d71c identities for the eight loading fields are preserved. The original unloaded-reference timeout is not a pass; its separately verified replacement is used.

Next define actual frame restraint, head/nut contact and installation/load path, and obtain real thread/preload/material data before applying normalized responses to a service-load budget. Current CAD, 3 mm screws and actual unknown inputs stay unchanged. candidate_go=false; fixture_fabrication_go=false; manufacturing_go=false.
''')
for p,h in cores.items():assert sha(R/p)==h
for p in E.rglob('*'):
 if p.is_file():assert p.stat().st_size<95*1024*1024,('oversize file',p)
print('SEALED_ACCEPTED_EIGHT_CASES_AND_REFERENCE',json.dumps(summary['preload_reference']),flush=True)
