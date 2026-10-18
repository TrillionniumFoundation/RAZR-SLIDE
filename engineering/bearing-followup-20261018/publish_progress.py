"""Publish bounded follow-up evidence without promoting an unfinished contact model."""
from pathlib import Path
import datetime, gzip, hashlib, json, shutil, subprocess
D=Path('/home/qian-qi/RAZR-SLIDE-bearing-delivery-20261018')
R=Path('/home/qian-qi/RAZR-SLIDE-bearing-orderfix-20261018')
B=Path('/home/qian-qi/.local/share/razr-slide-evidence/bearing-contact-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/bearing-followup-20261018')
E=D/'engineering/bearing-followup-20261018'
HEAD='79b73bb3720bcc5b4e9d86ea6d6c8864988cbd1d'
J=Path('/home/qian-qi/.local/state/hepta-runtime-operator-host/jobs')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for q in iter(lambda:f.read(4*1024*1024),b''):h.update(q)
    return h.hexdigest()
def dump(p,z):p.write_text(json.dumps(z,indent=2,allow_nan=False)+'\n')
def copy(src,dst):
    assert src.is_file() and not src.is_symlink()
    shutil.copyfile(src,dst);assert sha(src)==sha(dst)
assert subprocess.check_output(['git','-C',str(D),'rev-parse','HEAD'],text=True).strip()==HEAD
assert not subprocess.check_output(['git','-C',str(D),'status','--porcelain','--untracked-files=all'],text=True)
u=json.loads((B/'unit1216/report.json').read_text());assert u['passed'] and u['tests_run']==1216 and u['base_commit']==HEAD and len(u['suite_results'])==31
assert u['source_hashes_before']==u['source_hashes_after'] and not u['changed_during_tests']
for p,h in u['source_hashes_after'].items():assert sha(D/p)==h
# Our two linear attempts must be settled before this record is emitted.
owned=['1a14ecaa19f-1b6abb-1270','1a14ed8a549-1b6abb-12c0','1a14ee22349-1b6abb-12e9'];jobs=[]
for job in owned:
    ex=json.loads((J/job/'exit.json').read_text());jobs.append({'job_id':job,'exit':ex})
assert not E.exists();E.mkdir()
for name in ['frame_release_diagnostic.py','frame_release_block_diagnostic.py','frame-block-preparation.json','test-identity-readback.json','service-support-resultant.json','recover_free_frame.py','publish_progress.py']:
    copy(O/name,E/name)
copy(J/'1a14ed805e8-1b6abb-12ba/stdin.bin',E/'service_support_resultant.py')
for name in ['prior-bearing-flatness.json','audit_prior_bearings.py','actual-edge-order-check.json','verify_actual_edge_order.py','bearing29.log','bearing29.exit','hosted-status-79b73bb.json']:
    copy(B/name,E/name)
(E/'full-unit1216.json.gz').write_bytes(gzip.compress((B/'unit1216/report.json').read_bytes(),mtime=0))
linear=None
p=O/'frame-release-block/report.json'
if p.exists():
    linear=json.loads(p.read_text());assert linear['passed_frozen_load_linear_diagnostic']
    (E/'frame-release').mkdir();copy(p,E/'frame-release/report.json');copy(p.parent/'frame-release-field.npz',E/'frame-release/frame-release-field.npz')
private_report=O/'frame-release-block/private-recovery/report.json'
private=json.loads(private_report.read_text()) if private_report.exists() else None
if private is not None:
    assert private['passed'];copy(private_report,E/'frame-release/private-recovery-report.json')
for job in owned+['1a14ec599b3-1b6abb-1252','1a14ed805e8-1b6abb-12ba']:
    dest=E/'runtime'/job;dest.mkdir(parents=True)
    for name in ['stdout.log','stderr.log','exit.json']:
        if (J/job/name).exists():copy(J/job/name,dest/name)
# Only fully written immutable exchange artifacts are bound; counts remain partial.
src=B/'rigid-install-v3';progress=json.loads((src/'bearing-progress.json').read_text())
complete=[]
for p in sorted(src.glob('bearing-field-*.npz')):
    i=int(p.stem.rsplit('-',1)[-1]);need=[p,src/f'bearing-qp-{i:03d}.json',src/f'bearing-gaps-{i:03d}.json',src/f'body-gaps-{i:03d}.json']
    if not all(x.exists() for x in need):continue
    if i>=len(progress):continue
    if len(progress)>1 and i==len(progress)-1:continue
    complete.append((i,need))
assert complete
idx,files=complete[-1];partial=progress[idx];manifest=[]
for p in files+[src/'bearing-domains.json']:
    manifest.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
copy(src/f'bearing-qp-{idx:03d}.json',E/'last-bound-finite-qp.json')
source_job='1a14eb3ee97-1b6abb-11c8';terminal=J/source_job/'exit.json'
state=json.loads(terminal.read_text()) if terminal.exists() else {'state':'running_at_snapshot'}
final_src=json.loads((src/'bearing-report.json').read_text()) if (src/'bearing-report.json').exists() else None
ind=json.loads((B/'independent-v3-status.json').read_text()) if (B/'independent-v3-status.json').exists() else None
summary={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PR':35,'base_main':'a1b3cc1e0773446f2e36d0a607edf61211dd9919','tested_functional_commit':HEAD,
 'tests':1216,'suites':31,'all_recorded_tested_files_revalidated':len(u['source_hashes_after']),'tests_already_completed_before_followup_not_rerun':True,'test_report_sha256':sha(B/'unit1216/report.json'),
 'rigid_probe_source_job':source_job,'rigid_probe_terminal_or_snapshot':state,'last_bound_completed_exchange':partial,'partial_field_files_not_copied':manifest,
 'rigid_probe_final_pass':bool(final_src and final_src.get('passed')),'independent_rigid_probe_status':ind,
 'not_complete_head_nut_contact_qualification':not bool(ind and ind.get('passed')),
 'frame_release_attempts':jobs,'frame_release_linear_result':linear,'frame_private_recovery':private,
 'service_support_equilibrium_diagnostic':json.loads((O/'service-support-resultant.json').read_text()),
 'new_frame_probe_retains_old_PR34_loads_not_recoupled_contact':True,'core_CAD_screws_actual_material_preload_dependencies_workflow_unchanged':True,
 'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
dump(E/'PROGRESS_DELIVERY.json',summary)
(E/'METHOD_AND_LIMITS.md').write_text('''# Bearing-contact and frame-restraint follow-up

Current product source remains at 79b73bb. Existing completed 1216 tests / 31 suites and every recorded source file are revalidated, not counted as another execution. The separate rigid head/nut comparator remains subject to the full body and bearing-domain audit. A finite-QP pass or declining negative-region count is not a final surface-contact pass. No old partial or incorrect-order field is promoted.

The new frame experiment keeps the actual PR34 unloaded installation member load and entire selected elastic energy fixed, removes the 777 ideal fixed-face coordinates, and selects six pure coordinate gauges from the rigid-motion basis. Full residual, zero gauge-reaction, rigid null action, work/energy and alternate coordinate reexpression checks are required. The second coordinate gauge is not a second FEA solve. If no accepted linear report exists, the attempt is explicitly uncompleted; a timeout is not structural failure. A successful frozen-load field is still NOT a re-equilibrated contact or bolt solution.

The separate service-resultant calculation sums the previously independently accepted nodal forces and moments. Added face bubbles do no work under rigid motion. Zero-external installation is self-equilibrated; the loaded case needs a physical counter-force and counter-moment. Removing the ideal frame fixture without supplying that external action has no static free-frame interpretation. Numerical gauges must not supply the missing load. This calculation does not identify a real grip/support surface or stiffness.

No actual screw-head stiffness, material lot, torque, preload, service load rating or manufacturing precision is assigned. Rigid bearing planes are a conditional comparator, not verified M1 material behavior. Reference: GetFEM small sliding contact documentation distinguishes equivalent point/nodal forces from resolved pressure; SIMULIA rigid-part documentation describes rigidity as a modeling approximation. Neither package was installed or used by these probes. Original head/nut, volume/trace and fixture assumptions must remain explicit.

Large live/partial bearing fields remain in persistent host storage and are hash-bound here, not copied wholesale into Git or the conversation. These diagnostics are additive evidence; historical CAD tests are not claimed freshly repeated.
''')
for p,h in u['source_hashes_after'].items():assert sha(D/p)==h
print('FOLLOWUP_EVIDENCE_READY',json.dumps({'linear_passed':linear is not None,'rigid_final_pass':summary['rigid_probe_final_pass'],'independent_status':ind,'last_bound_exchange':partial,'files':len(list(E.rglob('*')))}),flush=True)
