"""Collect completed installation-control evidence without changing tested code."""
from pathlib import Path
import json,hashlib,gzip,shutil,tarfile,subprocess,datetime
R=Path('/home/qian-qi/RAZR-SLIDE-installation-control-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/installation-control-20261018')
E=R/'engineering/installation-control-20261018'
COMMIT='2303ac50f7f881ca243cc7315718aba99354fd6a'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def copy(p,d):shutil.copyfile(p,d);assert sha(p)==sha(d)
def pack(name,paths,root):
    with tarfile.open(name,'w:gz') as tar:
        for p in paths:
            if p.is_file() and not p.is_symlink():tar.add(p,arcname=str(p.relative_to(root)))
    assert name.stat().st_size<95*1024*1024
summary=json.loads((O/'installation-sequence-summary.json').read_text());u=json.loads((O/'unit1187/report.json').read_text())
assert summary['new_independently_verified_full_fields']==2 and u['passed'] and u['base_commit']==COMMIT and u['tests_run']==1187 and len(u['suite_results'])==31
assert u['source_hashes_before']==u['source_hashes_after'] and not u['changed_during_tests']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==COMMIT
for name,h in u['source_hashes_after'].items():assert sha(R/name)==h,('changed tested source',name)
core={p:sha(R/p) for p in ['integration/installation_control.py','engineering/trace-enrichment-20261017/solve_trace_probe.py','tools/test_suites.json','integration/manufacturing-tests/test_installation_control.py']}
assert not (E/'DELIVERY_VERIFICATION.json').exists()
for name in ['installation-sequence-summary.json','locked-installation.json','independent-input-readback.json','verify_installation_field.py','run_installation_sequence.py','summarize_installation.py','run_complete_units1187.py','new-tests.log','new-tests.exit','sequence-status.json','seal_delivery.py']:
    copy(O/name,E/name)
(E/'local-unit1187.json.gz').write_bytes(gzip.compress((O/'unit1187/report.json').read_bytes(),mtime=0))
pack(E/'unit1187-raw-logs.tar.gz',sorted((O/'unit1187').rglob('*')),O/'unit1187')
large=[]
for name in ['install-force','service-locked']:
    src=O/name;ad=O/('audit-'+name);dest=E/name;assert not dest.exists();dest.mkdir()
    for p in src.iterdir():
        if p.is_file() and not p.name.startswith(('field-','gaps-','qp-')):copy(p,dest/p.name)
    for body in ['panel','frame']:shutil.copytree(src/body,dest/body)
    copy(ad/'report.json',dest/'independent-report.json')
    (dest/'independent-regions.json.gz').write_bytes(gzip.compress((ad/'regions.json').read_bytes(),mtime=0))
    pack(dest/'contact-exchange-traces.tar.gz',sorted(src.glob('gaps-*.json'))+sorted(src.glob('qp-*.json')),src)
    fields=sorted(src.glob('field-*.npz'))
    for i in range(0,len(fields),6):pack(dest/f'partial-fields-{i:03d}.tar.gz',fields[i:i+6],src)
    for p in ad.glob('*private.npz'):large.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
    for p in [O/('audit-'+name+'.log'),O/('audit-'+name+'.exit')]:copy(p,dest/p.name)
(E/'durable-private-fields.json').write_text(json.dumps({'files':large,'bytes':sum(p['bytes'] for p in large),'not_uploaded_to_git_or_conversation':True},indent=2)+'\n')
jobroot=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs')
jobs=['1a14e07127f-1b6abb-f77','1a14e0821fa-1b6abb-f79','1a14e0878c4-1b6abb-f7b','1a14e0b118a-1b6abb-f7e'];records=[]
for jid in jobs:
    ex=json.loads((jobroot/jid/'exit.json').read_text());assert ex['exit_code']==0,(jid,ex)
    records.append({'job_id':jid,'exit':ex})
pack(E/'runtime-logs.tar.gz',[jobroot/jid/name for jid in jobs for name in ['stdout.log','stderr.log','exit.json']],jobroot)
if (O/'hosted-status.json').exists():copy(O/'hosted-status.json',E/'hosted-status.json')
verification={'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_main':'ee9a30831208c7e282c3518abdca2cf1cfe50726','tested_functional_commit':COMMIT,'full_tests':1187,'suites':31,'new_tests_included':30,
  'all_current_tests_freshly_executed':True,'same_source_snapshots':True,'stages':summary['stages'],
  'same_energy_trace_pressure_and_frame_support':True,'unit_report_sha256':sha(O/'unit1187/report.json'),'core_sha256':core,'runtime_jobs':records,
  'state_sha256':sha(O/'locked-installation.json'),'physical_targets_are_research_not_measured':True,
  'separate_zero_external_fixed_adjustment_FE_run':False,'zero_external_hold_checked_algebraically_against_independent_full_installation_field':True,
  'previous_eight_cases_and_unloaded_reference_not_rerun':True,'current_CAD_3mm_screws_actual_input_files_dependency_lock_workflows_unchanged':True,
  'resolved_head_nut_contact_sequential_torque_actual_preload_or_service_rating':False,
  'two_equilibrated_states_with_carried_adjustment_not_unique_loading_trajectory':True,
  'large_private_files':len(large),'large_private_bytes':sum(p['bytes'] for p in large),
  'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
(E/'DELIVERY_VERIFICATION.json').write_text(json.dumps(verification,indent=2,allow_nan=False)+'\n')
method='''# Force installation and fixed-adjustment service sequence

The original model prescribed an initial spring parameter t0, not the equilibrated installed force. Its relation is c*t-q=delta with c=Epanel/k, t=force/Epanel and q the prescribed pressure-weighted bolt separation. Historically delta=c*t0. This study first prescribes t for each bolt with four actuator force equations, extracts delta=c*t-q, then retains delta for the service step. It neither holds bolt force constant during service nor prevents elastic bolt extension.

The force-control multipliers are installation adjustments, not extra rigid supports. Only the original six body rigid coordinates enter reconstructed displacement. Full original equilibrium rows, unilateral contacts, KKT tests, gap criteria and ideal frame restraint remain. The optional branch uses the unchanged contact solver. No-load force targets are separate from the initial parameter, and source-bound fixed-adjustment states cannot be silently applied to other stiffness, mesh, surface load or trace maps.

Targets are all 2e-4 force/Epanel mm2 solely to compare with the historical initial-parameter value. Compliance Epanel/k remains 5 permm. These are normalized research inputs, not measured preload, selected torque, real material or rated capacity. Equal targets are imposed individual actuator goals, not an equal-load-sharing assertion. The fixed-adjustment loaded forces may differ.

Two new full fields are executed: simultaneous force installation at zero external load, and original case6 external load 1e-5 after locking the derived adjustment. Independent audits reconstruct loads, original and extra trace energy, complete force/moment equilibrium and all 5255 common gap regions, restoring every internal coefficient. The no-load fixed-adjustment check reuses the exact accepted installation field and verifies the changed connector law algebraically; it is not a third FEA run. Prior eight load cases and original unloaded reference are historical comparisons, not reruns or the same installation condition.

Head/nut pressures are still prescribed affine shape functions, not solved contact pressures. Frame support is still ideal, Y neutrality and omitted edge strips remain. This is not sequential screw tightening, a torque/friction history, a nonlinear head/nut model, or a physical installation test. The service solve carries the sealed adjustment into a separately equilibrated state, not the previous full displacement trajectory. Its optimizer starts from the historical force guess; contact-set history, frictional loading path and unique free-play placement are not established by these two equilibria. Numerical gap tolerance is not manufacturing precision.

Reference for force-to-fixed-adjustment analysis procedure: SIMULIA Abaqus, Prescribed Assembly Loads / Controlling the pre-tension node during the analysis, https://abaqus.uclouvain.be/English/SIMACAEPRCRefMap/simaprc-c-pretension.htm ; and Creating and editing bolt loads, https://docs.software.vt.edu/abaqusv2025/English/SIMACAECAERefMap/simacae-t-advboltloadscreate.htm . These establish the analysis concept, not validation of this implementation or the hardware.
'''
(E/'METHOD_AND_LIMITS.md').write_text(method)
copy(R/'CURRENT_DESIGN.md',E/'PREVIOUS_CURRENT_DESIGN.md')
(R/'CURRENT_DESIGN.md').write_text('''# Current research: force installation followed by fixed adjustment

See engineering/installation-control-20261018/DELIVERY_VERIFICATION.json and installation-sequence-summary.json. Optional force-controlled four-bolt installation and subsequent fixed-adjustment original case6 loading have independent full-field results on the existing 86-face/258-coefficient L2 model. The derived installed adjustment is retained; bolt force is not held constant during service. Targets and stiffness are normalized research inputs, not measurements or installation torque.

Fresh complete 1187 tests / 31 suites passed at 2303ac5 with unchanged source snapshots. Historical default spring-parameter behavior remains. The prior eight loadcases/reference and prior strict-target study are preserved, not rerun here. Full field, contact and physical rigid-equilibrium checks distinguish actuator multipliers from supports. The unloaded fixed-adjustment reproduction is algebraic, not an additional FEA run.

Next replace prescribed head/nut bearing shapes and ideal frame restraint with defined interfaces or measured data before claiming physical preload or service capacity. No actual material/preload/thread/assembly unknowns were filled, no CAD or 3 mm fastener was changed, and no manufacturing or hardware action occurred. candidate_go=false; fixture_fabrication_go=false; manufacturing_go=false.
''')
for p,h in core.items():assert sha(R/p)==h
print('DELIVERY_SEALED',json.dumps({'tests':1187,'full_fields':2,'large_files':len(large),'large_bytes':sum(p['bytes'] for p in large)}),flush=True)
