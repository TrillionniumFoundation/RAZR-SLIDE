"""Copy only completed, byte-verified native output into a portable evidence set."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import shutil
import tarfile

BASE = Path('/workspace/scratch/95cd2986fdf2/ci_audit')
FIRST = BASE/'native-matrix-e76ff339-final/report.json'
LAST = Path('/tmp/razr-native-matrix-e76ff339-remaining/report.json')
AUDIT = BASE/'native-matrix-final-audit.json'
DEST = BASE/'native-matrix-e76ff339-complete'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def copy_verified(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    require(sha(source) == sha(target), 'copied bytes differ: '+str(source))
    return {'path': str(target.relative_to(DEST)), 'bytes': target.stat().st_size,
            'sha256': sha(target), 'original_path': str(source)}


def main():
    audit = json.loads(AUDIT.read_text())
    require(audit['all_ten_jobs_complete'] and audit['strict_unique_workflow_coverage_passed']
            and audit['commands_executed_in_complete_jobs'] == 37
            and audit['old_clear_region_records_satisfy_summed_upper_bound'], 'complete audit required')
    DEST.mkdir(exist_ok=False)
    copied = [copy_verified(AUDIT, DEST/'native-matrix-final-audit.json')]
    for source, name in ((FIRST, 'receipts/capacity-stopped-attempt.json'),
                         (FIRST.with_name('capacity-stop-completion.json'), 'receipts/capacity-stop-completion.json'),
                         (LAST, 'receipts/remaining-five-attempt.json')):
        copied.append(copy_verified(source, DEST/name))
    for name in ('run_native_matrix_final.py', 'run_native_matrix_remaining.py', 'audit_native_matrix.py',
                 'package_native_evidence.py', 'native-matrix-controller-final.log',
                 'native-matrix-controller-remaining.log', 'partition-scanner-contract.json',
                 'partition-scanner-contract-v2.json', 'check_partition_scanner.py',
                 'prepare_completed_native_archives.py', 'native-matrix-incomplete-aggregation-check.log'):
        path = BASE/name
        if path.exists():
            copied.append(copy_verified(path, DEST/'controllers'/name))
    archives = []
    for path in (FIRST, LAST):
        report = json.loads(path.read_text())
        controller = BASE/('run_native_matrix_final.py' if path == FIRST else 'run_native_matrix_remaining.py')
        require(sha(controller) == report['controller_sha256'], 'executed controller source changed')
        for job in report['jobs']:
            if job['passed'] is not True:
                continue
            archive = DEST/'archives'/(job['id']+'.tar.gz')
            archive.parent.mkdir(exist_ok=True)
            prepared = BASE/'native-matrix-e76ff339-archives'/archive.name
            if prepared.exists():
                copied.append(copy_verified(prepared, archive))
            elif job.get('compression'):
                source = path.parent/job['compression']['archive']
                require(sha(source) == job['compression']['sha256'], 'original archive differs')
                copied.append(copy_verified(source, archive))
            else:
                folder = path.parent/job['id']
                with tarfile.open(archive, 'x:gz') as bundle:
                    for item in job['files']:
                        source = folder/item['path']
                        require(source.stat().st_size == item['bytes'] and sha(source) == item['sha256'],
                                'original output changed')
                        bundle.add(source, arcname=job['id']+'/'+item['path'], recursive=False)
                copied.append({'path': str(archive.relative_to(DEST)), 'bytes': archive.stat().st_size,
                               'sha256': sha(archive), 'original_directory': str(folder)})
            with tarfile.open(archive, 'r:gz') as bundle:
                actual = [member.name for member in bundle.getmembers() if member.isfile()]
                expected = [job['id']+'/'+item['path'] for item in job['files']]
                require(sorted(actual) == sorted(expected), 'archive file coverage differs')
                for item in job['files']:
                    data = bundle.extractfile(job['id']+'/'+item['path']).read()
                    require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                            'compressed member differs')
            archives.append({'job': job['id'], 'archive': str(archive.relative_to(DEST)),
                             'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
                             'original_files': job['files'], 'all_members_reread_and_sha256_matched': True,
                             'original_execution_report_sha256': sha(path)})
    require(len(archives) == 10 and len({item['job'] for item in archives}) == 10, 'ten archives required')
    index = {'schema': 'razr-portable-native-workflow-evidence-v1',
             'packaged_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
             'functional_source_commit': audit['functional_source_commit'],
             'all_ten_jobs_complete': True, 'workflow_commands_executed': 37,
             'strict_coverage_and_sum_audit_sha256': sha(AUDIT), 'files': copied,
             'job_archives': archives,
             'retained_failed_attempt': 'receipts/capacity-stopped-attempt.json',
             'capacity_failure_is_not_erased_or_relabelled_as_success': True,
             'source_commit_is_original_execution_identity': True,
             'hosted_execution': False, 'complete_product_motion_acceptance': False,
             'physical_qualification': False, 'candidate_go': False, 'manufacturing_go': False}
    (DEST/'EVIDENCE_INDEX.json').write_text(json.dumps(index, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'directory': str(DEST), 'archives': len(archives),
                      'archive_bytes': sum(item['archive_bytes'] for item in archives),
                      'original_files_verified': sum(len(item['original_files']) for item in archives),
                      'evidence_index_sha256': sha(DEST/'EVIDENCE_INDEX.json')}))


if __name__ == '__main__':
    main()
