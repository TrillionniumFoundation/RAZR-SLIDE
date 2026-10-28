"""Package complete immutable V6 reviews; do not duplicate actual run inputs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
STATIC = HERE.parent / 'independent-primitive-v6-preexecution-review'


def identity(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def package(directory, filename, manifest_name, external):
    archive = directory / filename
    manifest_path = directory / manifest_name
    assert not archive.exists() and not manifest_path.exists()
    files = [(p.name, p) for p in sorted(directory.iterdir()) if p.is_file() and p.suffix in ('.json', '.py', '.md') and p.name != 'R5_V6_REVIEW_PACKAGE_RECEIPTS.json']
    if directory == STATIC:
        for name in ('r5-primitive-v6-workflow.template.yml', 'r5-primitive-v6-workflow.yml'):
            files.append(('prepared-workflow/' + name, HERE.parent / name))
    rows = [dict(identity(path), archive_path=name) for name, path in files]
    manifest = {'schema': 'r5-v6-complete-independent-review-package-manifest-v1',
                'created_utc': datetime.now(timezone.utc).isoformat(), 'files': rows,
                'external_inputs_and_actual_run_not_duplicated': external,
                'preserved_failed_audits_are_not_reclassified': True,
                'conditional_model_only': True, 'native_geometry_qualified': False, 'full_continuous_G2': False}
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    files.append((manifest_name, manifest_path))
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name, path in files:
            original = path.read_bytes()
            if name != manifest_name:
                record = next(row for row in rows if row['archive_path'] == name)
                assert len(original) == record['bytes'] and hashlib.sha256(original).hexdigest() == record['sha256']
            target.writestr(name, original)
    with zipfile.ZipFile(archive) as received:
        assert received.testzip() is None
        assert set(received.namelist()) == {name for name, unused in files} and len(received.namelist()) == len(files)
        for name, path in files:
            assert received.read(name) == path.read_bytes()
    return dict(identity(archive), members=len(files), all_member_CRC_and_bytes_reverified=True, manifest=identity(manifest_path))


def main():
    audit = json.loads((HERE/'R5_V6_INDEPENDENT_ACTUAL_LOCAL_READBACK_V3.json').read_text())
    assert audit['audit_completed'] and audit['registered_budget_respected']
    results = [package(STATIC, 'R5-V6-INDEPENDENT-FINAL-STATIC-AND-LOCAL-ENTRY-REVIEW.zip',
                       'R5_V6_FINAL_STATIC_LOCAL_PACKAGE_MANIFEST.json',
                       {'source_lock': identity(ROOT/'r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V6.json'),
                        'actual_geometry_executed_by_static_reviews': False}),
               package(HERE, 'R5-V6-INDEPENDENT-ACTUAL-LOCAL-READBACK-WITH-FAILURES.zip',
                       'R5_V6_ACTUAL_LOCAL_REVIEW_PACKAGE_MANIFEST.json',
                       {'closed_pipeline': audit['actual_pipeline'], 'actual_output_files': audit['complete_actual_output_census'],
                        'input_source_lock': identity(ROOT/'r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V6.json'),
                        'source_snapshot_scientific_payloads_retained_by_parent_archive': True})]
    out = HERE/'R5_V6_REVIEW_PACKAGE_RECEIPTS.json'
    assert not out.exists()
    out.write_text(json.dumps({'schema': 'r5-v6-independent-review-package-receipts-v1', 'packages': results}, indent=2)+'\n')
    print(json.dumps(results))


if __name__ == '__main__':
    main()
