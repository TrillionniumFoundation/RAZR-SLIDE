"""Package unchanged review/source records and verify every archived byte."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def identity(path):
    data = path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


paths = sorted(path for path in HERE.iterdir() if path.suffix in ('.py','.md','.json') and not path.name.startswith('R5_V7_FINAL_STATIC_PACKAGE'))
paths += sorted(path for path in (ROOT/'r5-integration/v7-independent-checker').iterdir() if path.is_file())
paths += [ROOT/'r5-envelope'/name for name in ['planar_exterior_model_r5e_v7.py','planar_exterior_refinement_r5e_v7.py',
    'verify_planar_exterior_r5e_v7.py','run_portable_planar_r5e_v7.py','R5E_PLANAR_EXTERIOR_V7_BASIS.md',
    'R5E_PORTABLE_SOURCE_LOCK_V7.json','R5E_V7_READINESS.json']]
paths += [ROOT/'r5-integration'/name for name in ['r5-planar-v7-workflow.template.yml','r5-planar-v7-workflow.yml','r5-primitive-v6-workflow.yml']]
paths += [ROOT/'r5-local-v7'/name for name in ['R5_V7_LOCAL_EXECUTION_READINESS.json','prepare_local_snapshot_v1.py','README_R5_V7_PREEXECUTION.md']]
assert len(paths) == len(set(paths))
records = [identity(path) for path in paths]
report = json.loads((HERE/'R5_V7_FINAL_INDEPENDENT_STATIC_REVIEW_V2.json').read_text())
assert report['execution_completed'] is True and report['source_static_review_passed'] is True
assert report['V7_mathematical_experiments_executed'] == report['V7_control_suites_executed'] == 0
manifest = {'schema':'r5-v7-independent-final-static-package-manifest-v1','files':records,
    'final_report':identity(HERE/'R5_V7_FINAL_INDEPENDENT_STATIC_REVIEW_V2.json'),
    'actual_static_failure_retained':identity(HERE/'R5_V7_FINAL_INDEPENDENT_STATIC_REVIEW_V1.json'),
    'source_lock_sha256':'da61d0c1af1b6ac7ca2013990bf6cda43d1e8309a859b7bbfd7ec51abbf9971f',
    'complete_original_inputs_referenced_in_final_report':138,'original_snapshot_bytes':43211475,
    'original_scientific_inputs_duplicated_in_review_archive':False,
    'new_V7_mathematical_runs_claimed':0,'CI_workflow_preparation_is_not_execution':True,
    'original_V6_conditional_result_preserved':[8,16],'native_planar_region_semantics_verified':False,
    'full_continuous_G2':False,'all_blockers_closed':False}
manifest_path = HERE/'R5_V7_FINAL_STATIC_PACKAGE_MANIFEST.json'
assert not manifest_path.exists()
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
paths.append(manifest_path)
destination = ROOT/'R5-V7-INDEPENDENT-FINAL-STATIC-REVIEW-WITH-FAILURE.zip'
assert not destination.exists()
with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for path in paths: archive.write(path,path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None and len(archive.namelist()) == len(paths) and len(set(archive.namelist())) == len(paths)
    for path in paths:
        assert archive.read(path.relative_to(ROOT).as_posix()) == path.read_bytes()
for path,record in zip(paths[:-1],records): assert identity(path) == record
receipt = {'schema':'r5-v7-independent-final-static-package-receipt-v1','archive':identity(destination),
           'manifest':identity(manifest_path),'member_count':len(paths),'full_CRC_check_passed':True,
           'every_member_bytes_equal_source':True,'all_packaged_original_bytes_unchanged':True,
           'V7_mathematical_execution_performed_by_packager':False}
receipt_path = HERE/'R5_V7_FINAL_STATIC_PACKAGE_RECEIPT.json'; assert not receipt_path.exists()
receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
