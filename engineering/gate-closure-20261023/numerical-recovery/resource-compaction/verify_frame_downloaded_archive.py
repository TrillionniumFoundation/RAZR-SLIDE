"""Verify the preserved full frame archive before reclaiming its raw duplicate."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import tarfile

WORK = Path('/workspace/scratch/95cd2986fdf2')
ARCHIVE = WORK / 'frame-compute-archive-20261023/frame-full-L2-rebuild-20261023.tar.xz'
MANIFEST = WORK / 'input_recovery/resource_compaction/frame-original-artifact-manifest.json'
RAW = Path('/tmp/razr-fe-20261023/volume-rebuild/frame/level-2/K.npz')
RECEIPT = WORK / 'input_recovery/resource_compaction/frame-downloaded-archive-readback.json'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reclaim-raw-duplicate', action='store_true')
    args = parser.parse_args()
    expected = json.loads(MANIFEST.read_text())['members']
    archive_sha = sha256(ARCHIVE)
    assert ARCHIVE.stat().st_size == 243162164
    assert archive_sha == '1c41ae773f93e7259293e3e09db78099f4dce574c05cdc2c5d46b093ad36d90b'
    rows, extra = [], []
    with tarfile.open(ARCHIVE, 'r|xz') as tf:
        for member in tf:
            if not member.isfile():
                raise ValueError('Unexpected non-file archive member')
            h, length = hashlib.sha256(), 0
            with tf.extractfile(member) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
                    length += len(block)
            row = {'path': member.name, 'bytes': length, 'sha256': h.hexdigest()}
            if member.name in expected:
                e = expected[member.name]
                assert length == e['bytes'] and row['sha256'] == e['sha256']
                rows.append(row)
            else:
                extra.append(row)
    assert len(rows) == len(expected) == 22
    assert {r['path'] for r in rows} == set(expected)
    assert extra == [{'path': 'ARTIFACT_MANIFEST.json', 'bytes': MANIFEST.stat().st_size,
                      'sha256': sha256(MANIFEST)}]
    receipt = {
        'schema': 'razr-frame-downloaded-archive-exact-readback-v1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'archive': str(ARCHIVE), 'archive_bytes': ARCHIVE.stat().st_size,
        'archive_sha256': archive_sha, 'member_manifest': str(MANIFEST),
        'member_manifest_sha256': sha256(MANIFEST), 'all_original_members_verified': True,
        'original_member_count': len(rows), 'total_archive_file_members': len(rows) + len(extra),
        'members': rows, 'extra_manifest_members': extra,
        'verifier_source_sha256': sha256(Path(__file__)),
        'download_result': 'frame-download-result.json',
        'raw_K_deleted': False, 'panel_or_response_artifacts_modified': False,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')
    if args.reclaim_raw_duplicate:
        assert RAW.is_file() and not RAW.is_symlink() and RAW.stat().st_nlink == 1
        size = RAW.stat().st_size
        assert size == 394530277
        assert sha256(RAW) == 'e077f8d0176c041041b984b5dbb016e140219b34223d235ac739978b1dddd95d'
        refs = []
        for process in Path('/proc').iterdir():
            if not process.name.isdecimal():
                continue
            try:
                for fd in (process / 'fd').iterdir():
                    try:
                        if fd.resolve() == RAW:
                            refs.append(str(fd))
                    except (OSError, RuntimeError):
                        continue
                if str(RAW) in (process / 'maps').read_text():
                    refs.append(str(process / 'maps'))
            except (OSError, UnicodeError):
                continue
        if refs:
            raise ValueError('Raw K is in use by an observed process: ' + str(refs))
        RAW.unlink()
        receipt.update({'raw_K_deleted': True, 'reclaimed_raw_bytes': size,
                        'raw_duplicate_path': str(RAW),
                        'observed_open_FD_or_mapping_count': 0,
                        'process_observation_scope': 'current namespace plus explicit owner-agent no-worker confirmation',
                        'restore_command': 'python restore_frame_raw.py --restore --archive ' + str(ARCHIVE)})
        RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')
    s = os.statvfs(WORK)
    print(json.dumps({'all_original_members_verified': True, 'members': len(rows),
                      'total_files': len(rows) + len(extra), 'raw_K_deleted': receipt['raw_K_deleted'],
                      'receipt': str(RECEIPT), 'available_disk_bytes': s.f_bavail * s.f_frsize}))


if __name__ == '__main__':
    main()
