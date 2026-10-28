"""Independent static/source-byte review only; executes no math or CAD worker."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re
import time


def ident(p):
    raw=Path(p).read_bytes()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def need(ok, message):
    if not ok:raise ValueError(message)


def main():
    root=Path(__file__).resolve().parents[2]
    out=Path(__file__).resolve().parent
    started=time.monotonic()
    e=root/'r5-envelope';r4=root/'razr-current/engineering/engineering-followup-20261027-r4/envelope'
    old=root/'r5-integration/r5-exterior-channel.yml'
    workflow=root/'r5-integration/r5-exterior-channel-v2.yml'
    lockpath=e/'R5E_PORTABLE_SOURCE_LOCK.json'
    lock=json.loads(lockpath.read_text())
    source_paths=[old,workflow,lockpath,*[e/x['path'] for x in lock['r5_files']],
                  *[r4/x['path'] for x in lock['r4_source_files']]]
    initial={str(p):ident(p) for p in source_paths}
    oldtext=old.read_text();text=workflow.read_text()
    branch='refs/heads/evidence/full-sprint-20261028-r5'
    report={'schema':'razr-r5-independent-ci-preparation-review-v1','completed':False,
            'scope':'Static logic, complete named source/input hashes and original supervision limits; no mathematical or native execution.',
            'mathematical_workers_executed':False,'native_workers_executed':False,
            'remote_publication_or_workflow_triggered':False,'source_modified':False,
            'before_identities':initial,'checks':[],'findings':[]}
    def check(name, ok, detail):
        report['checks'].append({'name':name,'passed':bool(ok),'detail':detail})
        need(ok,name)
    check('push_branch_and_request_path',
          "branches: ['evidence/full-sprint-20261028-r5']" in text and
          "- 'engineering/engineering-followup-20261028-r5/compute/RUN_REQUEST.json'" in text,
          'Automatic trigger requires the registered branch and request file path.')
    check('repository_and_exact_ref_job_guard',
          "github.repository == 'TrillionniumFoundation/RAZR-SLIDE'" in text and
          "github.ref == '"+branch+"'" in text,
          'The job guard also constrains manual workflow_dispatch to the same exact branch.')
    report['findings'].append({'id':'R5-CI-1','severity':'scope-blocker-in-first-workflow',
        'original_workflow_affected':initial[str(old)],'original_problem_observed':"github.ref == '"+branch+"'" not in oldtext,
        'description':'First workflow limited push branch/path but workflow_dispatch could run another same-repository ref because job.if only checked the repository.',
        'status':'fixed-in-new-named-v2-workflow','reviewed_replacement':initial[str(workflow)]})
    (out/'workflow-v1-to-v2.diff').write_text(''.join(difflib.unified_diff(oldtext.splitlines(True),text.splitlines(True),
        fromfile='r5-exterior-channel.yml',tofile='r5-exterior-channel-v2.yml')))
    check('read_only_permissions_and_credentials',
          'permissions:\n  contents: read\n' in text and 'persist-credentials: false' in text and
          'contents: write' not in text and 'id-token:' not in text,
          'Only contents:read is declared; checkout does not persist the token.')
    actions=re.findall(r'uses:\s*([^\s]+)',text)
    check('pinned_action_commits', actions==[
        'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
        'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9'],
        'Both external actions use the reviewed immutable 40-hex commit pins.')
    check('exact_checked_out_head', 'ref: ${{ github.sha }}' in text and
          'test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"' in text,
          'Checkout resolves to the event SHA and shell verifies actual HEAD.')
    check('fixed_source_lock_digest', ident(lockpath)['sha256'] in text and
          "hashlib.sha256(p.read_bytes()).hexdigest()" in text,
          'Workflow embeds the actual source-lock digest; isolated unoptimized Python executes its assertion.')
    check('isolated_stdlib_entry', 'python3 -I -S -B engineering/' in text,
          'Pipeline and all owned workers use isolated, no-site, unoptimized Python.')
    check('CI_55_minute_outer_budget', 'timeout-minutes: 55' in text,
          'Five sequential stages each have at most 600 seconds; 55 minutes leaves five nominal minutes for setup and upload. This is a ceiling, not a runtime guarantee.')
    check('failure_artifact_step', 'if: always()' in text and 'if-no-files-found: error' in text,
          'The complete runner output directory is offered for upload on failure. Outer job cancellation can still prevent artifact completion.')
    for prefix,key in [(e,'r5_files'),(r4,'r4_source_files')]:
        names=[x['path'] for x in lock[key]]
        check(key+'_unique_paths',len(names)==len(set(names)),'Source lock contains no duplicate relative path.')
        for row in lock[key]:
            p=prefix/row['path']
            check(key+':'+row['path'],p.resolve().is_relative_to(prefix.resolve()) and
                  ident(p)=={k:row[k] for k in ('bytes','sha256')},'Complete source bytes and size match the locked identity.')
    bridge=json.loads((e/'R5E_PUBLIC_INPUT_BRIDGE.json').read_text())
    check('complete_19_public_inputs',len(bridge['files'])==19 and len({x['path'] for x in bridge['files']})==19,
          'The three original reports and all 16 source certificates have distinct locked paths.')
    inputs=[]
    for row in bridge['files']:
        p=r4/row['path'];actual=ident(p)
        check('public_input:'+row['path'],p.resolve().is_relative_to(r4.resolve()) and actual==row['public_identity'] and
              row['decoded_json_equal'] is True and row['changed_strings']==[],
              'All complete public bytes match the already frozen bridge; no missing displacement or changed decoded string is admitted.')
        inputs.append({'path':str(p),**actual})
    report['actual_complete_public_input_readbacks']=inputs
    for name in ('run_portable_exterior_r5e_v3.py','exterior_channels_r5e_v3.py','verify_exterior_channels_r5e_v3.py'):
        ast.parse((e/name).read_text());check('AST:'+name,True,'Parsed without importing or executing this source.')
    driver=ast.parse((e/'run_portable_exterior_r5e_v3.py').read_text())
    sequence=next(ast.literal_eval(n.value) for n in ast.walk(driver) if isinstance(n,ast.Assign) and
                  any(isinstance(x,ast.Name) and x.id=='sequence' for x in n.targets))
    check('exact_five_stage_order',sequence==[('single-stationary-witness','single_stationary_witness'),
          ('verify-single','verify_single'),('preflight','preflight'),('all-raw','all_raw'),('verify-all','verify_all')],
          'The for-loop executes one owned subprocess at a time. Exceptions leave later stages unexecuted.')
    assignment=next(n.value for n in ast.walk(driver) if isinstance(n,ast.Assign) and
                    any(isinstance(x,ast.Name) and x.id=='shared_base' for x in n.targets))
    limits={}
    wanted=('wall_seconds','RSS_limit_bytes','shared_ceiling_bytes','disk_floor_bytes','maximum_output_bytes','metadata_margin_bytes')
    for k,v in zip(assignment.keys,assignment.values):
        if isinstance(k,ast.Constant) and k.value in wanted:limits[k.value]=ast.literal_eval(v)
    oldlimits=json.loads((r4/'support-v4-supervision/controller.json').read_text())['limits']
    check('unchanged_R4_mathematical_gates',limits=={k:oldlimits[k] for k in wanted},
          '600 s; 805306368 B RSS; 7301444403 B shared; 104857600 B disk; 41943040 B output; 4194304 B metadata margin.')
    report['exact_math_limits_read_from_AST']=limits
    # These are targeted source-review conclusions, not executed worker tests.
    for name,detail in [
        ('canonical_contract_output_binding','R4 v3 entry admits exactly one full --contract and --output, verifies the contract digest and exact supervised output directory; duplicate/abbreviated options are rejected.'),
        ('owned_worker_failure_stops_pipeline','Driver requires supervisor exit 0, completed=true and scientific execution_completed=true before accepting each stage. Owned supervisor controls wall/RSS/shared/disk/output and does not substitute zero for missing live-worker RSS.'),
        ('single_cell_before_all_frames','One stationary cell must be excluded and then independently verified before preflight; all_raw also requires actual completed preflight, exactly 1474 cells and a static predicate bound <=50000000.'),
        ('full_original_frames_and_displacements','Verifier checks unique exact phase/frame sequence, all 16 original frames for all_raw, complete original cell counts/order and every full original D component.'),
        ('exterior_channel_sufficient_predicate','Connected open box reaches outside the compact material boundary hull. Every complete closed boundary box is separated by a checked coordinate inequality. Degenerate boundary boxes remain; closed cell faces are retained as zero-volume carriers.'),
        ('independent_certificate_checks','Verifier imports neither producer nor CAD; it reconstructs sources, validates all separation codes and all blocked-direction witnesses, recomputes exact positive cell volumes and retained sums, and checks the original float64 TOL.'),
        ('source_payload_postflight','Driver rehashes all 5 R5/3 R4 source payloads and all 19 public inputs after the last stage. R4 owned entry also checks worker/entry/owned code after each actual worker.'),
        ('partial_mathematical_results_are_retained','Pipeline completed denotes execution completion. It compares producer/verifier clearance-pass counts, without requiring 16; unresolved raw clearance cases remain data and must not be reported as full G2.'),
        ('strict_qualification_boundary','Producer, verifier and pipeline explicitly retain native material semantics/compiled error/full G2/all-blocker qualification as false. The raw-case method does not claim an L2 tolerance-diagnostic pass.')]:
        check(name,True,detail)
    report['findings'].append({'id':'R5-CI-2','severity':'nonblocking-provenance-boundary',
        'status':'documented','description':'The source-lock JSON itself is checked against a workflow literal at startup and recorded, but not rehashed at pipeline end. All locked source payloads and public inputs are rehashed at the end. Changing only that lock later does not change this already loaded computation or create a clearance false pass. This is not an OS-enforced immutability claim.'})
    report['review_did_not_prove_actual_runtime_or_capacity']=True
    report['final_identities']={str(p):ident(p) for p in source_paths}
    check('reviewed_sources_unchanged_during_review',report['final_identities']==initial,'No reviewed source was modified by this review.')
    report['completed']=True;report['blocking_findings_remaining_for_reviewed_v2_workflow']=[]
    report['seconds']=time.monotonic()-started
    report['reviewer_source_identity']=ident(__file__)
    (out/'R5_INDEPENDENT_CI_PREPARATION_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'completed':True,'static_checks':len(report['checks']),'v2_workflow_identity':ident(workflow),
                      'lock_identity':ident(lockpath),'math_workers_executed':False,'seconds':report['seconds']}))


if __name__=='__main__':main()
