"""Seal V9 actual failure, independently completed mathematics and full inputs."""
import hashlib,json,os,resource,signal,time,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root/'r7-deliverables/RAZR-R7-V9-complete-actual-source-and-failed-supervision-20261028.zip'
plan_path=root/'r7-deliverables/R7_V9_COMPLETE_ARCHIVE_PLAN_V1.json'
seal_path=root/'r7-deliverables/R7_V9_COMPLETE_ARCHIVE_SEAL_V1.json'
assert not any(p.exists() for p in (out,plan_path,seal_path))
started=time.monotonic()
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('registered120sarchivebudget')))
signal.alarm(120)

def identity(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}

entries={}
def include(p):
    p=Path(p).resolve()
    assert p.is_relative_to(root) and p.is_file() and not p.is_symlink()
    entries[p.relative_to(root).as_posix()]=p

registration=json.loads((root/'r7-envelope/local-v9/R7E_V9_LOCAL_EXECUTION_REGISTRATION_V1.json').read_text())
bound=[row for rows in registration['groups'].values() for row in rows]
assert len(bound)==146 and len({r['path'] for r in bound})==146
for row in bound:
    p=Path(row['path']);assert identity(p)=={k:row[k] for k in ('bytes','sha256')};include(p)
diagnostic=json.loads((root/'r7-envelope/diagnostic-v1/R7E_ORIGINAL_DOMAIN_DIAGNOSTIC_CONTRACT_V2.json').read_text())
for row in diagnostic['inputs'].values():
    p=Path(row['path']);assert identity(p)=={k:row[k] for k in ('bytes','sha256')};include(p)
for directory in ('r7-envelope/source-v9','r7-envelope/local-v9','r7-envelope/diagnostic-v1',
                  'r7-envelope/independent-checker-review','r7-audit/envelope-domain-review',
                  'r7-audit/envelope-v9-checker','r7-audit/envelope-v9-final-review'):
    for p in sorted((root/directory).rglob('*')):
        if p.is_file():include(p)
for name in ('prepare_v9_helper_draft.py','prepare_v9_producer_and_driver.py','freeze_v9_sources_v1.py',
             'register_v9_local_execution_v1.py','record_v9_actual_exit_v1.py','record_v9_actual_exit_v2.py',
             'R7E_V9_ORIGINAL_V7_SOURCE_RECOVERY.json','R7E_V9_SOURCE_FREEZE_RECEIPT_V1.json',
             'R7E_V9_STATIC_SOURCE_CAPACITY_PRE_FREEZE_DRAFT.json','R7E_V9_LEGACY_SOURCE_PRESERVATION_STATIC.json',
             'R7E_V9_HELPER_FROM_ORIGINAL_V7.diff','R7E_V9_PRODUCER_FROM_ORIGINAL_V7.diff','R7E_V9_DRIVER_FROM_ORIGINAL_V7.diff'):
    include(root/'r7-envelope'/name)
include(Path(__file__))
rows=[{'member':n,'original_path':str(p),'identity':identity(p)} for n,p in sorted(entries.items())]
total=sum(r['identity']['bytes'] for r in rows)
assert total<=268435456
disk=os.statvfs(root);assert disk.f_bavail*disk.f_frsize>2*total+268435456
pipeline=json.loads((root/'r7-envelope/local-v9/attempt-1/pipeline.json').read_text())
control=json.loads((root/'r7-envelope/local-v9/attempt-1/verify-single-supervision/controller.json').read_text())
assert pipeline['completed'] is False and control['completed'] is False
assert control['failure']['message']=="still-running owned child RSS unavailable: KeyError: 'VmRSS'"
plan={'schema':'razr-r7-v9-complete-actual-archive-plan-v1','wall_seconds':120,'address_space_bytes':268435456,
      'maximum_uncompressed_input_bytes':268435456,'full_input_bytes':total,'member_count_before_manifest':len(rows),
      'full_146_execution_inputs_included':True,'full_6_source_domain_diagnostic_inputs_included':True,
      'new_V9_source_and_original_failed_attempts_included':True,
      'V9_owned_pipeline_pass':False,'V9_owned_verifier_stage_pass':False,
      'V9_independent_math_report_completed':True,'V9_first_u_gate_actually_reached':False,
      'V9_full_16_stage_executed':False,'missing_V8_originals_reconstructed':False,
      'native_or_full_continuous_G2_pass_claimed':False,'all_blockers_closed':False,'members':rows}
plan_path.write_text(json.dumps(plan,indent=2)+'\n')
with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
    for row in rows:z.write(entries[row['member']],row['member'])
    z.writestr('ARCHIVE_MANIFEST.json',json.dumps(plan,indent=2)+'\n')
with zipfile.ZipFile(out) as z:
    assert len(z.infolist())==len(rows)+1
    for row in rows:
        h=hashlib.sha256();length=0
        with z.open(row['member']) as f:
            while b:=f.read(1048576):h.update(b);length+=len(b)
        assert {'bytes':length,'sha256':h.hexdigest()}==row['identity']
    assert json.loads(z.read('ARCHIVE_MANIFEST.json'))==plan
assert all(identity(entries[row['member']])==row['identity'] for row in rows)
seal={'schema':'razr-r7-v9-complete-actual-archive-seal-v1','archive_name':out.name,
      'identity':identity(out),'members':len(rows)+1,'all_original_inputs_and_actual_results_unchanged':True,
      'complete_archive_member_SHA_CRC_verified':True,'elapsed_seconds':time.monotonic()-started,
      'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
      'V9_failure_preserved':True,'all_blockers_closed':False}
seal_path.write_text(json.dumps(seal,indent=2)+'\n');signal.alarm(0)
print(json.dumps(seal))
