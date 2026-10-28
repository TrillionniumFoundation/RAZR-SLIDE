"""Preserve the frozen executed V6 checkpoint, including actual audit failures."""
from pathlib import Path
import datetime
import hashlib
import json
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'r5-deliverables'
TARGET = DEST / 'RAZR-R5-V6-primitive-support-actual-and-independent-evidence-20261028.zip'
DIRECTORIES = (
    'r5-local-v6',
    'r5-integration/independent-primitive-v6-preexecution-review',
    'r5-integration/independent-primitive-v6-execution-review',
    'r5-integration/v6-independent-checker',
    'r5-integration/independent-envelope-v5-execution-review',
    'r5-integration/independent-trim-v5-preexecution-review',
)


def identity(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1048576), b''):
            h.update(data)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


start = time.monotonic()
assert not TARGET.exists(), 'Do not overwrite an existing science archive'
paths = []
for name in DIRECTORIES:
    for path in sorted((ROOT / name).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and '.private.' not in path.name:
            assert not path.is_symlink()
            paths.append(path)
for name in (
    'r5-integration/r5-primitive-v6-workflow.yml',
    'r5-integration/r5-primitive-v6-workflow.template.yml',
    'r5-ci-results/RAZR-R5-trim-model-v5-run-40645988108.zip',
    'r5-ci-results/R5_V5_CI_ARTIFACT_RECEPTION.json',
    'r5-integration/build_v6_scientific_checkpoint_archive_r5.py',
):
    paths.append(ROOT / name)
assert len(paths) == len(set(paths))
rows = [{'path': path.relative_to(ROOT).as_posix(), **identity(path)} for path in paths]
total = sum(row['bytes'] for row in rows)
assert total < 64 * 2**20
plan = {
    'schema': 'r5-v6-archival-capacity-and-source-plan-v1',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'maximum_uncompressed_input_bytes': 64 * 2**20,
    'maximum_archive_bytes': 64 * 2**20,
    'maximum_wall_seconds': 180,
    'maximum_single_member_in_memory_bytes': max(row['bytes'] for row in rows),
    'files': rows, 'total_input_bytes': total,
    'archival_operation_only': True, 'new_scientific_worker_execution': False,
    'V7_draft_files_included': False,
}
DEST.mkdir(exist_ok=True)
plan_path = DEST / 'R5_V6_SCIENTIFIC_CHECKPOINT_ARCHIVE_PLAN.json'
assert not plan_path.exists()
plan_path.write_text(json.dumps(plan, indent=2) + '\n')
readme = '''# R5 V6: complete actual evidence and independent review

This archive preserves the complete local V6 experiment and its immutable
input snapshot, all 53 original outputs, source and entry reviews, the actual
cross-author readback, and both failed earlier audit attempts. V6 completed
all five stages under the original owned resource gates. The result remains
8/16 conditional-model frame passes; there were no new complete-frame passes.
The original raw 4/16 result, actual V4 failure, and V5 8/16 result are unchanged.

Start with `r5-local-v6/README_R5_V6_LOCAL_EXECUTION.md` and the README in
`r5-integration/independent-primitive-v6-execution-review/`. The original V5
Actions ZIP is included separately and unchanged. The local V6 input snapshot
contains the actual frozen source, original R4 inputs, and actual V5 files
used by this run. Earlier complete native inventories remain in their original
previously preserved science archives and are explicitly identified by the
source projection receipts; no native membership proof is claimed here.

The two workflow files are prepared, unexecuted CI configurations. The actual
V6 execution was local, not a GitHub Actions run. V7 drafts are excluded.
Native trim/primitive semantics, compiled-error bounds, the current complete
factory continuous domain, same-specimen/OEM data and physical G3-G5 are not
qualified by this archive. No threshold, source, or failure was rewritten.

`MANIFEST.json` binds every archived original by byte count and SHA-256.
'''
with zipfile.ZipFile(TARGET, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for row, path in zip(rows, paths):
        assert time.monotonic() - start < plan['maximum_wall_seconds']
        assert identity(path) == {key: row[key] for key in ('bytes', 'sha256')}
        data = path.read_bytes()
        archive.writestr(row['path'], data, compress_type=zipfile.ZIP_STORED if path.suffix in ('.gz', '.zip') else zipfile.ZIP_DEFLATED)
    archive.writestr('README.md', readme)
    archive.writestr('MANIFEST.json', json.dumps(plan, indent=2) + '\n')
assert TARGET.stat().st_size < plan['maximum_archive_bytes']
with zipfile.ZipFile(TARGET) as archive:
    assert len(archive.infolist()) == len(rows) + 2
    assert len(set(archive.namelist())) == len(archive.namelist())
    assert json.loads(archive.read('MANIFEST.json')) == plan
    for row in rows:
        data = archive.read(row['path'])
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
seal = {'schema': 'r5-v6-science-checkpoint-full-readback-v1', 'path': TARGET.relative_to(ROOT).as_posix(),
        **identity(TARGET), 'members': len(rows) + 2, 'all_member_CRC_and_SHA_verified': True,
        'originals_unchanged_after_packaging': all(identity(p) == {k: row[k] for k in ('bytes', 'sha256')} for p, row in zip(paths, rows)),
        'elapsed_seconds': time.monotonic() - start, 'V7_drafts_included': False,
        'new_scientific_execution': False, 'all_blockers_closed': False}
assert seal['originals_unchanged_after_packaging']
(DEST / 'R5_V6_SCIENTIFIC_CHECKPOINT_ARCHIVE_SEAL.json').write_text(json.dumps(seal, indent=2) + '\n')
print(json.dumps(seal))
