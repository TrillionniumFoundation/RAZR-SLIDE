"""Prepare completed job archives for upload; never assert a ten-job pass."""
from pathlib import Path
import hashlib
import io
import json
import shutil
import tarfile
from audit_native_matrix import FIRST, CONTINUATION, raw_files, require, sha

BASE = Path('/workspace/scratch/95cd2986fdf2/ci_audit')
OUT = BASE/'native-matrix-e76ff339-archives'
REPO_DEST = 'engineering/gate-closure-20261023/native-matrix-e76ff339/archives'


def main():
    OUT.mkdir(exist_ok=False)
    rows = []
    for path in (FIRST, CONTINUATION):
        report = json.loads(path.read_text())
        for job in report['jobs']:
            if job['passed'] is not True:
                continue
            require(job['source_bytes_unchanged'] and job['present_tracked_bytes_match_head'], 'invalid job source')
            require(job['source_head_before'] == job['source_head_after'] == report['expected_head'], 'wrong job head')
            destination = OUT/(job['id']+'.tar.gz')
            if job.get('compression'):
                # Read every original member before copying its immutable archive.
                for item, data in raw_files(path, job):
                    pass
                source = path.parent/job['compression']['archive']
                shutil.copyfile(source, destination)
                require(sha(destination) == job['compression']['sha256'], 'archive copy changed')
            else:
                with tarfile.open(destination, 'x:gz') as bundle:
                    for item, data in raw_files(path, job):
                        member = tarfile.TarInfo(job['id']+'/'+item['path'])
                        member.size = len(data)
                        member.mode = 0o644
                        bundle.addfile(member, io.BytesIO(data))
            with tarfile.open(destination, 'r:gz') as bundle:
                actual = [member.name for member in bundle.getmembers() if member.isfile()]
                require(sorted(actual) == sorted(job['id']+'/'+item['path'] for item in job['files']), 'archive coverage differs')
                for item in job['files']:
                    data = bundle.extractfile(job['id']+'/'+item['path']).read()
                    require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                            'archived bytes differ')
            rows.append({'job': job['id'], 'absolute_path': str(destination),
                         'repository_path': REPO_DEST+'/'+destination.name,
                         'bytes': destination.stat().st_size, 'sha256': sha(destination),
                         'original_files': len(job['files']), 'original_bytes': job['output_bytes'],
                         'all_members_reread_and_sha256_matched': True,
                         'executed_source_commit': report['expected_head']})
    require(len(rows) == 9 and len({row['job'] for row in rows}) == 9, 'nine completed jobs required')
    result = {'schema': 'razr-native-archive-upload-preparation-v1', 'completed_archives': rows,
              'completed_job_count': 9, 'all_ten_jobs_complete': False,
              'final_strict_workflow_coverage_audit_pending': True,
              'functional_source_commit': report['expected_head'],
              'hosted_execution': False, 'physical_qualification': False}
    (OUT/'DELIVERY_MANIFEST.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'manifest': str(OUT/'DELIVERY_MANIFEST.json'), 'jobs': 9,
                      'archive_bytes': sum(row['bytes'] for row in rows),
                      'original_files_verified': sum(row['original_files'] for row in rows)}))


if __name__ == '__main__':
    main()
