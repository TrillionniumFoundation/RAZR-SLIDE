"""Seal all R4 native/domain evidence with member SHA256 and ZIP CRC checks.

Public projections are generated afterwards and are intentionally not part of
this raw scientific archive, avoiding a circular archive-SHA reference.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import stat
import time
import zipfile
import zlib


ROOT = Path(__file__).resolve().parent


def identity(path):
    p = Path(path); h = hashlib.sha256(); crc = 0; size = 0
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block); crc = zlib.crc32(block, crc); size += len(block)
    return {'bytes': size, 'sha256': h.hexdigest(), 'crc32': f'{crc & 0xffffffff:08x}'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); c = json.loads(a.contract.read_text()); start = time.monotonic()
    observed = identity(__file__)
    assert {k: observed[k] for k in ('bytes', 'sha256')} == c['worker_identity']
    a.out.mkdir(exist_ok=False)
    manifest_path = ROOT / 'R4_SCIENTIFIC_MANIFEST.json'
    assert not manifest_path.exists()
    paths = sorted(p for p in ROOT.rglob('*') if p.is_file() and
                   not p.relative_to(ROOT).parts[0] == 'public')
    assert all(not p.is_symlink() for p in paths)
    members = {}
    for p in paths:
        relative = p.relative_to(ROOT).as_posix()
        assert '..' not in Path(relative).parts and not relative.startswith('/')
        members[relative] = {**identity(p), 'mode': stat.S_IMODE(p.stat().st_mode)}
    manifest = {'schema': 'razr-r4-native-structure-scientific-manifest-v1',
        'sealed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'archive_root': c['archive_root'], 'payload_members': members,
        'payload_member_count': len(members), 'payload_bytes': sum(x['bytes'] for x in members.values()),
        'manifest_self_identity_is_in_external_archive_receipt': True,
        'public_projection_excluded_to_avoid_circular_archive_identity': True,
        'product_geometry_changes': {'added_mm3': 0.0, 'removed_mm3': 0.0},
        'qualification': {'actual_native_jobs_completed': 4, 'physical_release': False,
                          'all_blockers_closed': False, 'full_G2': False, 'G3': False, 'G4': False, 'G5': False}}
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    all_paths = paths + [manifest_path]
    archive = a.out / c['archive_filename']
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in all_paths:
            z.write(p, c['archive_root'] + '/' + p.relative_to(ROOT).as_posix())
    expected = dict(members)
    expected[manifest_path.name] = {**identity(manifest_path), 'mode': stat.S_IMODE(manifest_path.stat().st_mode)}
    verified = []
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist(); names = [x.filename for x in infos]
        assert len(names) == len(set(names)) == len(expected)
        assert set(names) == {c['archive_root'] + '/' + x for x in expected}
        for info in infos:
            relative = info.filename.removeprefix(c['archive_root'] + '/')
            ref = expected[relative]; h = hashlib.sha256(); crc = 0; size = 0
            with z.open(info) as stream:
                for block in iter(lambda: stream.read(1048576), b''):
                    h.update(block); crc = zlib.crc32(block, crc); size += len(block)
            actual = {'bytes': size, 'sha256': h.hexdigest(), 'crc32': f'{crc & 0xffffffff:08x}'}
            assert actual == {k: ref[k] for k in ('bytes', 'sha256', 'crc32')}
            assert actual['crc32'] == f'{info.CRC:08x}' and size == info.file_size
            assert identity(ROOT / relative) == actual
            verified.append({'archive_member': info.filename, **actual, 'ZIP_declared_CRC_matches': True})
    receipt = {'schema': 'razr-r4-native-structure-archive-receipt-v1',
        'sealed_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'archive_filename': archive.name,
        'archive_identity': {k: v for k, v in identity(archive).items() if k != 'crc32'},
        'manifest_identity': identity(manifest_path), 'member_count': len(verified),
        'uncompressed_bytes': sum(x['bytes'] for x in verified), 'members': verified,
        'all_member_SHA256_and_ZIP_CRC_checked': True, 'all_source_files_unchanged_during_seal': True,
        'worker_identity': c['worker_identity'], 'contract_identity': identity(a.contract),
        'seconds': time.monotonic() - start, 'completed': True}
    (a.out / 'R4_NATIVE_SCIENTIFIC_ARCHIVE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('completed', 'archive_filename', 'archive_identity', 'member_count', 'uncompressed_bytes', 'seconds')}))


if __name__ == '__main__':
    main()
