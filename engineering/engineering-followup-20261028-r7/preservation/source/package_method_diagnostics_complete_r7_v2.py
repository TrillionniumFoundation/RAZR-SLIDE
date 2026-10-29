"""Preserve complete consumed method inputs, actual diagnostics and supervision."""
from pathlib import Path
import hashlib
import json
import resource
import shutil
import signal
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'r7-deliverables/RAZR-R7-method-diagnostics-and-supervision-complete-originals-20261028.zip'
PLAN=ROOT/'r7-deliverables/R7_METHOD_COMPLETE_ARCHIVE_PLAN_V2.json'
SEAL=ROOT/'r7-deliverables/R7_METHOD_COMPLETE_ARCHIVE_SEAL_V2.json'

def ident(p):
    with p.open('rb') as f:
        h=hashlib.file_digest(f,'sha256').hexdigest()
    return {'bytes':p.stat().st_size,'sha256':h}

def main():
    assert not any(p.exists() for p in (OUT,PLAN,SEAL))
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('120-second method archive budget')))
    signal.alarm(120)
    entries={};bound=[]

    def include(p,expected=None):
        p=Path(p)
        assert not p.is_symlink() and p.is_file() and p.resolve().is_relative_to(ROOT)
        assert '.private.' not in p.name and 'r7-private-helpers' not in p.parts
        assert '__pycache__' not in p.parts and p.suffix!='.pyc'
        p=p.resolve();actual=ident(p)
        if expected is not None:
            assert actual=={k:expected[k] for k in ('bytes','sha256')}
            bound.append({'path':str(p),**actual})
        entries[p.relative_to(ROOT).as_posix()]=p

    original_plan=json.loads((ROOT/'r7-deliverables/R7_V9_COMPLETE_ARCHIVE_PLAN_V1.json').read_text())
    for row in original_plan['members']:
        include(row['original_path'],row['identity'])
    include(ROOT/'r7-deliverables/R7_V9_COMPLETE_ARCHIVE_PLAN_V1.json')
    include(ROOT/'r7-deliverables/R7_V9_COMPLETE_ARCHIVE_SEAL_V1.json')
    include(ROOT/'r7-deliverables/R7_V9_COMPLETE_PRESERVATION_V1.json')

    method_directories=(
        'r7-envelope/correlation-diagnostic-v1','r7-envelope/wire-meaning-diagnostic-v1',
        'r7-envelope/v9-meaning-review-v1','r7-envelope/spatial-pilot-v1',
        'r7-envelope/edge189-source-diagnostic-v1',
    )
    for directory in method_directories:
        d=ROOT/directory
        assert (d/'MANIFEST.json').is_file(), 'Each actual diagnostic must be closed before archiving: '+directory
        for c in sorted(d.rglob('*CONTRACT*.json')):
            contract=json.loads(c.read_text())
            for key in ('inputs','original_V6_archive_files'):
                if key in contract:
                    for row in contract[key].values():
                        assert isinstance(row,dict) and all(k in row for k in ('path','bytes','sha256'))
                        include(row['path'],row)
            for key in ('source','basis','static_capacity','source_function_mapping','checker_interface','independent_line_checker'):
                row=contract.get(key)
                if isinstance(row,dict) and all(k in row for k in ('path','bytes','sha256')):
                    include(row['path'],row)

    directories=method_directories+(
        'r7-supervisor','r7-native/edge189-independent-v1','r7-native/edge189-actual-readback-v1',
        'r7-audit/envelope-correlation-review','r7-audit/envelope-wire-review',
        'r7-audit/envelope-spatial-probe-review','r7-audit/envelope-edge189-review',
        'r7-audit/supervisor-review','r7-audit/storage-observation','r7-audit/blocker-ledger',
    )
    for directory in directories:
        d=ROOT/directory;assert d.is_dir()
        for p in sorted(d.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':include(p)
    for p in sorted((ROOT/'r7-audit').glob('*.py')):
        if any(s in p.name for s in ('blocker','contact_profile','profile','positive_q','a11','authorized_push')):
            include(p)
    for p in sorted((ROOT/'r7-audit').glob('R7_REAL_SPECIMEN*.json')):include(p)
    for relative in (
        'r7-recovery-tools/package_method_diagnostics_complete_r7_v1.py',
        'r7-deliverables/R7_METHOD_ARCHIVE_ATTEMPT1_ACTUAL_CAPACITY_FAILURE_V1.json',
        'r7-deliverables/R7_METHOD_ARCHIVE_V2_SOURCE_REVISION_V1.json',
        'r7-publication/reclaim_complete_archived_factory_expansions_v1.py',
        'r7-publication/R7_COMPLETE_FACTORY_ARCHIVE_EXPANSION_MIGRATION_V1.json',
        'r7-publication/R7_ORIGINAL_V6_ALL16_STATUS_READBACK_V1.json',
        'r7-publication/R7_ENVELOPE_RUNTIME_REMOTE_PUBLICATION_VERIFIED_V1.json',
        'r7-publication/R7_NATIVE_FINITE_REMOTE_PUBLICATION_VERIFIED_V1.json',
        'r7-publication/R7_NATIVE_PUBLICATION_TRANSPORT_ATTEMPT1_ACTUAL_FAILURE_V1.json',
        'r7-publication/R7_NATIVE_FINITE_REMOTE_WRITE_RECEIPTS_V1.json',
        'r7-publication/R7_FAR_REDUNDANT_PARTIAL_CACHE_RECLAIM_V1.json',
        'r7-publication/reclaim_far_redundant_partial_cache_v1.py',
        'r7-deliverables/R7_NATIVE80_COMPLETE_PRESERVATION_V1.json',
        'r7-deliverables/R7_NEAR_COMPLETE_PRESERVATION_V1.json',
        'r7-deliverables/R7_FAR_COMPLETE_PRESERVATION_V1.json',
    ):include(ROOT/relative)
    include(Path(__file__))
    rows=[{'member':name,'original_path':str(p),'identity':ident(p)} for name,p in sorted(entries.items())]
    total=sum(r['identity']['bytes'] for r in rows)
    assert total<=320*1024*1024
    assert shutil.disk_usage(ROOT).free>=96*1024*1024+128*1024*1024
    plan={'schema':'razr-r7-complete-method-originals-archive-plan-v2',
          'complete_V9_bound_originals_inherited_without_reclassification':True,
          'complete_new_method_contract_inputs_included_and_hash_verified':True,
          'registered_input_binding_rows_including_duplicates':bound,
          'all_actual_diagnostic_and_supervision_failures_preserved':True,
          'native_full_originals_are_bound_separate_saved_archives':True,
          'native_runtime_or_physical_qualification_claimed_by_this_archive':False,
          'maximum_input_bytes':320*1024*1024,'maximum_archive_bytes':96*1024*1024,
          'ordinary_disk_floor_bytes':128*1024*1024,'address_space_bytes':268435456,'wall_seconds':120,
          'member_count_before_manifest':len(rows),'full_original_input_bytes':total,
          'all_blockers_closed':False,'members':rows}
    PLAN.write_text(json.dumps(plan,indent=2)+'\n')
    minimum_free=shutil.disk_usage(ROOT).free
    with zipfile.ZipFile(OUT,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for row in rows:
            z.write(entries[row['member']],row['member'])
            assert OUT.stat().st_size<=96*1024*1024
            free=shutil.disk_usage(ROOT).free;minimum_free=min(minimum_free,free)
            assert free>=128*1024*1024
        z.writestr('ARCHIVE_MANIFEST.json',json.dumps(plan,indent=2)+'\n')
    assert OUT.stat().st_size<=96*1024*1024
    with zipfile.ZipFile(OUT) as z:
        names={row['member'] for row in rows}|{'ARCHIVE_MANIFEST.json'}
        assert set(z.namelist())==names and len(z.infolist())==len(names)
        for row in rows:
            h=hashlib.sha256();n=0
            with z.open(row['member']) as f:
                while data:=f.read(1048576):h.update(data);n+=len(data)
            assert {'bytes':n,'sha256':h.hexdigest()}==row['identity']
        assert json.loads(z.read('ARCHIVE_MANIFEST.json'))==plan
    assert all(ident(entries[row['member']])==row['identity'] for row in rows)
    seal={'schema':'razr-r7-complete-method-originals-archive-seal-v2','archive_name':OUT.name,
          'identity':ident(OUT),'members':len(rows)+1,
          'all_registered_inputs_and_actual_results_unchanged':True,
          'full_member_set_CRC_SHA_verified':True,'minimum_observed_disk_free_bytes':minimum_free,
          'seconds':time.monotonic()-started,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
          'science_results_or_original_failures_reclassified':False,'all_blockers_closed':False}
    SEAL.write_text(json.dumps(seal,indent=2)+'\n');signal.alarm(0)
    print(json.dumps(seal))

if __name__=='__main__':main()
