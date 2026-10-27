"""Read the one immutable scientific ZIP; extract exactly three whole bodies.

No CAD imports, no remote writes, no new geometry. The download URL is an input
only and is never copied into the engineering receipt.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import time
import urllib.request
import zipfile

EXPECTED_BYTES = 63227765
EXPECTED_SHA = 'bd237005fcb5749eacf7592e71256b4128e5b0e00fbd260f5252b24bbc1bb0e1'
MANIFEST_SHA = '559eb0c4eb37923281eadc68e51cd203d535b0fbab48f775bde48cb4d3e0d201'
SELECTED = {
    'factory/worker/bodies/A_BACK_PANEL.step': (937636, '90f035bc9a033f467f17259e449786ae9519a4a4ad5f08db784c27551e26bd32'),
    'factory/worker/bodies/L_KEY.step': (336902, '348e68445442c0286dd0d531dc3c2d8fb661f38b0f68810e81252ab216a24179'),
    'factory/worker/bodies/R_KEY.step': (343291, '253b91c1f7858d667aeece23b64a0806f092ff25d8d26519f63181522d715494'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def guard(root):
    if shutil.disk_usage(root).free < 2 * 1024 ** 3:
        raise ValueError('original retained free disk requirement 2 GiB not met')
    used = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if used > 128 * 1024 ** 2:
        raise ValueError('new source/audit/download subtree exceeds 128 MiB allowance')


def run(url, root):
    started = time.monotonic()
    guard(root)
    dest = root / 'K3FULL_stow_tabs_3_original.zip'
    if dest.exists():
        raise ValueError('existing ZIP is not overwritten or redownloaded by this recovery invocation')
    h = hashlib.sha256()
    count = 0
    with urllib.request.urlopen(url, timeout=45) as stream, dest.open('xb') as f:
        while True:
            raw = stream.read(1024 * 1024)
            if not raw:
                break
            guard(root)
            count += len(raw)
            if count > EXPECTED_BYTES:
                raise ValueError('ZIP exceeds immutable byte count')
            h.update(raw)
            f.write(raw)
    if count != EXPECTED_BYTES or h.hexdigest() != EXPECTED_SHA:
        raise ValueError('whole scientific ZIP size/SHA mismatch')
    rows = []
    whole_members = 0
    total_uncompressed = 0
    target = root / 'current-whole-STEP'
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest) as archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        names = [i.filename for i in infos]
        if len(set(names)) != len(names):
            raise ValueError('duplicate ZIP member names')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:
                raise ValueError('unsafe ZIP member path')
        manifest_raw = archive.read('ENGINEERING_MANIFEST.json')
        if sha(manifest_raw) != MANIFEST_SHA:
            raise ValueError('immutable engineering manifest differs')
        manifest = json.loads(manifest_raw)
        members = manifest['members']
        if set(names) != set(members) | {'ENGINEERING_MANIFEST.json'}:
            raise ValueError('archive regular file inventory differs from exact manifest')
        for info in infos:
            if info.filename == 'ENGINEERING_MANIFEST.json':
                continue
            expected = members[info.filename]
            if expected['bytes'] != info.file_size:
                raise ValueError('manifest/member size differs')
            digest = hashlib.sha256()
            n = 0
            with archive.open(info) as stream:
                while True:
                    raw = stream.read(1024 * 1024)
                    if not raw:
                        break
                    digest.update(raw)
                    n += len(raw)
            if n != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                raise ValueError('scientific member SHA/size differs')
            # ZipExtFile's complete read independently checks each member CRC.
            whole_members += 1
            total_uncompressed += n
        for name, (size, digest) in SELECTED.items():
            raw = archive.read(name)
            if len(raw) != size or sha(raw) != digest or members[name] != {'bytes': size, 'sha256': digest}:
                raise ValueError('selected whole-body immutable bytes differ')
            output = target / PurePosixPath(name).name
            if output.exists():
                raise ValueError('existing whole-body original is not overwritten')
            output.write_bytes(raw)
            if output.stat().st_size != size or sha(output.read_bytes()) != digest:
                raise ValueError('selected whole-body disk readback differs')
            rows.append({'original_member': name, 'selected_basename': output.name,
                         'bytes': size, 'sha256': digest, 'disk_readback_equal': True})
    guard(root)
    receipt = {
        'schema': 'razr-K3-whole-STEP-scientific-subset-recovery-v1',
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'original_run_id': 40285103942, 'original_artifact_id': 12633972884,
        'original_pose': 'stow_tabs_3', 'original_native_q_L_R_mm': [0.0, 0.0],
        'whole_ZIP_bytes': count, 'whole_ZIP_sha256': h.hexdigest(),
        'engineering_manifest_sha256': MANIFEST_SHA,
        'original_manifest_members_SHA_size_CRC_verified': whole_members,
        'exact_regular_file_count_including_manifest': whole_members + 1,
        'uncompressed_member_bytes_excluding_manifest': total_uncompressed,
        'selected_unchanged_original_whole_bodies': rows,
        'other_geometry_members_extracted': False,
        'native_CAD_execution': False, 'whole_pose_pairs_rerun': False,
        'raw_runtime_reconstructed': False, 'public_upload_performed': False,
        'minimum_retained_free_disk_GiB': 2,
        'new_subtree_storage_ceiling_MiB': 128,
        'elapsed_seconds': time.monotonic() - started,
    }
    out = root / 'K3_WHOLE_STEP_SUBSET_READBACK.json'
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'complete': True, 'receipt_name': out.name,
                      'receipt_sha256': sha(out.read_bytes()), 'receipt_bytes': out.stat().st_size,
                      'original_members_verified': whole_members,
                      'selected_whole_bodies': len(rows), 'native_executed': False}))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--root', type=Path, required=True)
    a = ap.parse_args()
    run(a.url, a.root)
