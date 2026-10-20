"""Read-only, bounded preflight for a retained rigid-bearing restart.

Inspect ZIP/NPY headers and small JSON metadata. Do not load a dense response,
factor K, rebuild FE, execute a QP, or write into an old evidence directory.
The original PR35 driver stores fields but does not persist its bearing H/C.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time
import zipfile

import numpy as np

DOMAIN_SHA = '9e6f489b7adc9f4ae4579f6f9e822a85fc38a2296d44fc64f0dd60401d3b0d14'


def digest(path, deadline):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            if time.monotonic() > deadline:
                raise TimeoutError('read-only inspection budget exhausted')
            h.update(block)
    return h.hexdigest()


def array_headers(path):
    result = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist()[:64]:
            if not name.endswith('.npy'):
                continue
            with archive.open(name) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, order, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0):
                    shape, order, dtype = np.lib.format.read_array_header_2_0(stream)
                else:
                    result[name[:-4]] = {'unsupported_header_version': list(version)}
                    continue
                result[name[:-4]] = {'shape': list(shape), 'dtype': str(dtype), 'fortran_order': order}
    return result


def inspect_response(path, deadline):
    headers = array_headers(path)
    result = {'path': str(path), 'bytes': path.stat().st_size, 'arrays': headers,
              'bearing_restart_candidate': False}
    meta, points_file = path.parent/'manifest.json', path.parent/'points.json'
    result['manifest_exists'] = meta.is_file()
    result['points_exists'] = points_file.is_file()
    if not (meta.is_file() and points_file.is_file() and 'H' in headers):
        return result
    if max(meta.stat().st_size, points_file.stat().st_size) > 8*1024*1024:
        result['metadata_inspection_skipped'] = 'over_8MiB_bound'
        return result
    manifest = json.loads(meta.read_text())
    points = json.loads(points_file.read_text())
    result['points'] = len(points)
    result['bearing_points'] = sum(p.get('kind') == 'bearing' for p in points)
    result['H_shape_matches_points'] = headers['H']['shape'] == [len(points), len(points)]
    result['manifest_points_hash_matched'] = digest(points_file, deadline) == manifest.get('points_sha256')
    expected = manifest.get('response_sha256')
    result['manifest_response_hash_matched'] = bool(expected) and digest(path, deadline) == expected
    result['original_bearing_domain_hash_in_identity'] = DOMAIN_SHA in json.dumps(manifest)
    result['manifest_top_level_keys'] = sorted(manifest)
    result['bearing_restart_candidate'] = all(result[k] for k in (
        'H_shape_matches_points', 'bearing_points', 'manifest_points_hash_matched',
        'manifest_response_hash_matched', 'original_bearing_domain_hash_in_identity'))
    result['classification'] = ('bearing_response_candidate_needs_exact_trace_identity_and_restore_probes'
        if result['bearing_restart_candidate'] else
        'legacy_or_incomplete_response_not_current_bearing_restart')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, action='append', required=True)
    parser.add_argument('--seconds', type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 60:
        parser.error('inspection budget must be between 1 and 60 seconds')
    start = time.monotonic()
    deadline = start+args.seconds
    responses, samples, errors = [], [], []
    scanned, complete = 0, True
    for root in args.root:
        if not root.is_dir():
            errors.append({'path': str(root), 'error': 'missing_directory'})
            complete = False
            continue
        for folder, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in ('.git', '.venv', 'node_modules') and not (Path(folder)/d).is_symlink()]
            if time.monotonic() > deadline or scanned > 50000:
                complete = False
                break
            for name in files:
                scanned += 1
                path = Path(folder)/name
                if path.is_symlink() or path.suffix != '.npz':
                    continue
                try:
                    if 'response' in name or 'cache' in name:
                        responses.append(inspect_response(path, deadline))
                    elif name in ('bearing-field-016.npz', 'local-blocks.npz') and len(samples) < 20:
                        samples.append({'path': str(path), 'arrays': array_headers(path)})
                except Exception as error:
                    errors.append({'path': str(path), 'error': type(error).__name__+': '+str(error)})
                    complete = False
    candidates = [r['path'] for r in responses if r['bearing_restart_candidate']]
    print(json.dumps({'scope': 'bounded_read_only_restart_cache_inventory',
        'roots': [str(r) for r in args.root], 'files_scanned': scanned, 'scan_complete': complete,
        'seconds': time.monotonic()-start, 'response_candidates': responses,
        'retained_field_or_local_block_examples': samples, 'errors': errors,
        'bearing_restart_candidates': candidates,
        'preflight_decision': 'inspect_exact_trace_identity_and_restore_probes_before_solving' if candidates else 'stop_no_identified_bearing_response_restart',
        'new_fe_solve': False, 'current_bearing_cache_restore_verified': False,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
