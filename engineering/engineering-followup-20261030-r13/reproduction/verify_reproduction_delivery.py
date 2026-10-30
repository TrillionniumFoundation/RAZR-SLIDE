"""Byte readback of newly delivered reproduction files, not a scientific replay."""
from pathlib import Path
import datetime,hashlib,json

ROOT=Path('/workspace/scratch/1b842ca762be')
REPO=ROOT/'RAZR-SLIDE'
DEST=REPO/'engineering/engineering-followup-20261030-r13/reproduction'
WORK=ROOT/'r13_reproduction_work'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):
    p=Path(p);return {'repository_relative_path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}

def main():
    report_path=DEST/'REPRODUCTION_READBACK.json';assert not report_path.exists()
    copies=[('first-snapshot/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json','first-snapshot/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json'),
            ('first-snapshot/README.md','first-snapshot/README.md'),
            ('after-recovery/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json','after-recovery/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json'),
            ('map_execution_inputs.py','map_execution_inputs.py'),('map_execution_inputs_v2.py','map_execution_inputs_v2.py'),
            ('MAPPING_ATTEMPT_1_FAILURE.json','MAPPING_ATTEMPT_1_FAILURE.json'),('README.md','README.md'),
            ('RECOVERED_R11_INPUT_IDENTITIES.json','RECOVERED_R11_INPUT_IDENTITIES.json')]
    for original,destination in copies:assert (WORK/original).read_bytes()==(DEST/destination).read_bytes()
    first=json.loads((DEST/'first-snapshot/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json').read_text())
    after=json.loads((DEST/'after-recovery/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json').read_text())
    assert first['summary']['records_with_exact_repository_match']==58 and first['summary']['records_without_exact_repository_match']==2
    assert after['summary']['records_with_exact_repository_match']==60 and after['summary']['records_without_exact_repository_match']==0
    assert first['repository']['observed_HEAD']==after['repository']['observed_HEAD']=='ab9ef3270a9a0d0d28f605f7188038db133dbcd8'
    assert len(first['entries'])==len(after['entries'])==60 and after['summary']['unique_size_SHA256_identities']==52
    assert first['mapper_source']['sha256']==after['mapper_source']['sha256']==sha(DEST/'map_execution_inputs_v2.py')
    current_checks=[]
    for row in after['entries']:
        p=REPO/row['preferred_repository_path'];assert p.stat().st_size==row['required_bytes'] and sha(p)==row['required_sha256']
        current_checks.append({'entry_id':row['entry_id'],'repository_path':row['preferred_repository_path'],'bytes':row['required_bytes'],'sha256':row['required_sha256']})
    recovered=json.loads((DEST/'RECOVERED_R11_INPUT_IDENTITIES.json').read_text())
    for r in recovered['files']:
        source=Path(r['original_absolute_path']);p=REPO/r['recovered_repository_relative_path']
        assert source.read_bytes()==p.read_bytes() and p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
    sealed_checks=[]
    for original,imported in [
        (ROOT/'r13_envelope_work/R13_ENVELOPE_DELIVERY_MANIFEST.json',REPO/'engineering/engineering-followup-20261030-r13/envelope/R13_ENVELOPE_DELIVERY_MANIFEST.json'),
        (ROOT/'r13_geometry_work/DELIVERY_MANIFEST.json',REPO/'engineering/engineering-followup-20261030-r13/geometry/DELIVERY_MANIFEST.json')]:
        assert original.read_bytes()==imported.read_bytes();sealed_checks.append(ref(imported))
    files=[]
    for p in sorted(DEST.rglob('*')):
        assert not p.is_symlink()
        if p.is_file():files.append(ref(p))
    report={'schema':'razr-r13-reproduction-content-recovery-and-delivery-readback-v1','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checker_source':ref(DEST/'verify_reproduction_delivery.py'),
        'first_snapshot_preserved_byte_identically':True,'after_recovery_snapshot_preserved_byte_identically':True,
        'first_snapshot_sha256':sha(DEST/'first-snapshot/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json'),
        'after_recovery_snapshot_sha256':sha(DEST/'after-recovery/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json'),
        'all_60_selected_actual_repository_files_size_and_SHA256_rechecked':True,'selected_inputs_rechecked':current_checks,
        'both_recovered_R11_reports_reread_equal_original_bytes':True,'recovered_R11_reports':[ref(REPO/r['recovered_repository_relative_path']) for r in recovered['files']],
        'sealed_manifest_files_still_byte_identical_to_originals':sealed_checks,
        'new_delivery_files_excluding_this_readback':files,'file_count_excluding_this_readback':len(files),
        'bytes_excluding_this_readback':sum(x['bytes'] for x in files),
        'scope':{'content_identity_and_path_location_only':True,'new_R11_or_R13_scientific_execution':False,
            'sealed_geometry_envelope_sources_or_reports_written_by_this_step':False,'original_absolute_layout_recreated':False,
            'original_execution_environment_reproduced':False,'remote_publication_verified_by_this_readback':False,'git_mutation_or_push_performed':False}}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for r in files:
        p=REPO/r['repository_relative_path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
    print(json.dumps({'total_files_including_readback':len(files)+1,'total_bytes_including_readback':report['bytes_excluding_this_readback']+report_path.stat().st_size,
        'readback_bytes':report_path.stat().st_size,'readback_sha256':sha(report_path),'first_snapshot_sha256':report['first_snapshot_sha256'],
        'after_recovery_snapshot_sha256':report['after_recovery_snapshot_sha256'],'README_sha256':sha(DEST/'README.md')},ensure_ascii=False))

if __name__=='__main__':main()
