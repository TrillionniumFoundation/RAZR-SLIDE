"""Atomic, hash-bound state for the unchanged PR35 rigid-bearing exchange.

A displacement field is not a checkpoint. The map, response, ordered descriptors,
next exchange and warm force vector must belong to one immutable generation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
import zipfile

import numpy as np
from scipy.sparse import csc_matrix, isspmatrix_csc

SCHEMA = 'razr-rigid-bearing-checkpoint-v1'
FILES = {'C.npz', 'H.npz', 'points.json', 'state.json', 'identity.json'}
HEX = re.compile(r'^[0-9a-f]{64}$')


def json_bytes(value):
    def convert(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       allow_nan=False, default=convert) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _json(data):
    def pairs(rows):
        value = {}
        for key, item in rows:
            if key in value:
                raise ValueError('duplicate JSON key: ' + key)
            value[key] = item
        return value
    def constant(value):
        raise ValueError('non-finite JSON number: ' + value)
    value = json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    json_bytes(value)  # Reject overflow-to-infinity such as 1e999 as well.
    return value


def _integer(value, name, low=0, high=None):
    if type(value) is not int or value < low or (high is not None and value > high):
        raise ValueError('invalid ' + name)
    return value


def validate_payload(C, H, points, state, *, n_dofs, parameters):
    n_dofs = _integer(n_dofs, 'DOF count', 1)
    maximum = _integer(parameters['maximum_columns'], 'maximum columns', 4)
    exchanges = _integer(parameters['max_exchanges'], 'exchange limit', 1)
    if not isinstance(points, list) or not 4 <= len(points) <= maximum:
        raise ValueError('ordered point count outside frozen limits')
    if any(not isinstance(p, dict) for p in points):
        raise ValueError('point descriptor is not an object')
    json_bytes(points)
    if not isspmatrix_csc(C) or C.shape != (n_dofs, len(points)):
        raise ValueError('C shape/format does not match ordered descriptors')
    C.check_format(full_check=True)
    if C.dtype != np.dtype('float64') or not np.isfinite(C.data).all():
        raise ValueError('C must be finite real float64')
    H = np.asarray(H)
    if H.dtype != np.dtype('float64') or H.shape != (len(points), len(points)) or not np.isfinite(H).all():
        raise ValueError('H must be finite float64 with one row/column per point')
    if not isinstance(state, dict) or set(state) != {'phase', 'next_iteration', 'history', 'guess'}:
        raise ValueError('incomplete or unknown exchange state')
    if state['phase'] != 'ready_for_qp':
        raise ValueError('checkpoint is not a pre-QP exchange boundary')
    iteration = _integer(state['next_iteration'], 'next exchange', 0, exchanges - 1)
    history = state['history']
    if not isinstance(history, list) or len(history) != iteration:
        raise ValueError('history does not match next exchange')
    for i, row in enumerate(history):
        if not isinstance(row, dict) or type(row.get('exchange')) is not int or row['exchange'] != i:
            raise ValueError('history exchange order differs')
    guess = state['guess']
    if (iteration == 0) != (guess is None):
        raise ValueError('warm force vector does not match exchange boundary')
    if guess is not None:
        if not isinstance(guess, list) or not 4 <= len(guess) <= len(points):
            raise ValueError('warm force vector length differs')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in guess) or not np.isfinite(guess).all():
            raise ValueError('warm force vector must be finite real values')
    json_bytes(state)


def _write(path, data):
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _sync(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_checkpoint(root, C, H, points, state, *, identity, sources, parameters):
    """Publish a complete immutable generation, then atomically advance LATEST.

    Return the manifest digest for retention outside the checkpoint bundle. A
    failed write leaves the previous pointer intact. No old generation is edited.
    """
    validate_payload(C, H, points, state, n_dofs=C.shape[0], parameters=parameters)
    for value in (identity, sources, parameters):
        if not isinstance(value, dict) or not value:
            raise ValueError('identity/source/parameter binding is required')
        json_bytes(value)
    root = Path(root)
    if root.is_symlink():
        raise ValueError('checkpoint root cannot be a symlink')
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    stage = Path(tempfile.mkdtemp(prefix='.incomplete-', dir=root))
    generation = root / ('checkpoint-%06d-%s' % (state['next_iteration'], uuid.uuid4().hex))
    pointer_temp = root / ('.latest-' + uuid.uuid4().hex)
    try:
        # Array content is validated before serialization; no object/pickle arrays.
        for name, values in [('C.npz', {'data': C.data, 'indices': C.indices,
                                      'indptr': C.indptr, 'shape': np.array(C.shape, dtype=np.int64)}),
                             ('H.npz', {'H': H})]:
            with (stage / name).open('xb') as stream:
                np.savez_compressed(stream, **values)
                stream.flush()
                os.fsync(stream.fileno())
        for name, value in [('points.json', points), ('state.json', state), ('identity.json', identity)]:
            _write(stage / name, json_bytes(value))
        files = {name: {'bytes': (stage / name).stat().st_size,
                        'sha256': file_digest(stage / name)} for name in sorted(FILES)}
        manifest = {'schema': SCHEMA, 'phase': 'ready_for_qp', 'n_dofs': C.shape[0],
                    'n_columns': len(points), 'sources': sources, 'parameters': parameters,
                    'files': files, 'physical_qualification': False,
                    'whole_surface_contact_pass': False}
        payload = json_bytes(manifest)
        _write(stage / 'manifest.json', payload)
        _sync(stage)
        os.rename(stage, generation)
        _sync(root)
        receipt = {'schema': SCHEMA, 'generation': generation.name,
                   'manifest_sha256': digest(payload), 'next_iteration': state['next_iteration']}
        _write(pointer_temp, json_bytes(receipt))
        os.replace(pointer_temp, root / 'LATEST.json')
        _sync(root)
        return {'path': str(generation), **receipt}
    finally:
        if stage.exists():
            shutil.rmtree(stage)  # Only this call's unpublished temporary directory.
        if pointer_temp.exists():
            pointer_temp.unlink()


@dataclass
class Loaded:
    C: object
    H: np.ndarray
    points: list
    state: dict
    identity: dict
    manifest: dict
    manifest_sha256: str


def _read_file(path, *, maximum=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing or symlinked checkpoint member: ' + str(path))
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        if maximum is not None and os.fstat(stream.fileno()).st_size > maximum:
            raise ValueError('checkpoint metadata too large')
        return stream.read()


def _arrays(data, expected_keys):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {key + '.npy' for key in expected_keys}:
            raise ValueError('duplicate/unknown/missing NPZ member')
        for info in archive.infolist():
            if info.is_dir() or '/' in info.filename or '\\' in info.filename:
                raise ValueError('unsafe NPZ member')
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        return {key: z[key] for key in expected_keys}


def load_checkpoint(path, *, expected_manifest_sha256, expected_identity,
                    expected_sources, expected_parameters, expected_n_dofs):
    """Restore only against a caller-held digest and current independently built identity.

    The caller must also regenerate all C columns from the descriptors and call
    ExactResponseCache.restore(..., probes=5) before executing another QP.
    """
    if not isinstance(expected_manifest_sha256, str) or not HEX.fullmatch(expected_manifest_sha256):
        raise ValueError('trusted checkpoint manifest digest required')
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError('checkpoint generation must be a real directory')
    payload = _read_file(path / 'manifest.json', maximum=8 * 1024 * 1024)
    if digest(payload) != expected_manifest_sha256:
        raise ValueError('checkpoint manifest digest changed')
    manifest = _json(payload)
    if manifest.get('schema') != SCHEMA or manifest.get('phase') != 'ready_for_qp':
        raise ValueError('not a complete rigid-bearing checkpoint')
    for key, expected in [('sources', expected_sources), ('parameters', expected_parameters)]:
        if json_bytes(manifest.get(key)) != json_bytes(expected):
            raise ValueError('checkpoint ' + key + ' differ from current controlled inputs')
    if manifest.get('physical_qualification') is not False or manifest.get('whole_surface_contact_pass') is not False:
        raise ValueError('a checkpoint cannot certify a completed solve or hardware')
    if type(manifest.get('n_dofs')) is not int or manifest['n_dofs'] != expected_n_dofs:
        raise ValueError('checkpoint DOF count differs')
    columns = _integer(manifest.get('n_columns'), 'column count', 4, expected_parameters['maximum_columns'])
    if not isinstance(manifest.get('files'), dict) or set(manifest['files']) != FILES:
        raise ValueError('incomplete checkpoint member manifest')
    payloads = {}
    for name in sorted(FILES):
        record = manifest['files'][name]
        if not isinstance(record, dict) or set(record) != {'bytes', 'sha256'}:
            raise ValueError('invalid checkpoint member record')
        _integer(record['bytes'], 'member byte size', 1)
        if not isinstance(record['sha256'], str) or not HEX.fullmatch(record['sha256']):
            raise ValueError('invalid member digest')
        raw = _read_file(path / name)
        if len(raw) != record['bytes'] or digest(raw) != record['sha256']:
            raise ValueError('checkpoint member changed: ' + name)
        payloads[name] = raw
    identity = _json(payloads['identity.json'])
    if json_bytes(identity) != json_bytes(expected_identity):
        raise ValueError('mechanical/trace/load identity differs')
    points = _json(payloads['points.json'])
    state = _json(payloads['state.json'])
    a = _arrays(payloads['C.npz'], {'data', 'indices', 'indptr', 'shape'})
    if a['shape'].shape != (2,) or a['shape'].dtype.kind not in 'iu' or tuple(a['shape']) != (expected_n_dofs, columns):
        raise ValueError('sparse map shape metadata differs')
    if a['data'].ndim != 1 or a['indices'].ndim != 1 or a['indptr'].shape != (columns + 1,):
        raise ValueError('malformed sparse map arrays')
    if a['indices'].dtype.kind not in 'iu' or a['indptr'].dtype.kind not in 'iu':
        raise ValueError('sparse indices must be integral')
    if (len(a['data']) != len(a['indices']) or a['indptr'][0] != 0
            or a['indptr'][-1] != len(a['data']) or np.any(a['indptr'][1:] < a['indptr'][:-1])
            or np.any(a['indices'] < 0) or np.any(a['indices'] >= expected_n_dofs)):
        raise ValueError('invalid sparse index bounds/order')
    C = csc_matrix((a['data'], a['indices'], a['indptr']), shape=(expected_n_dofs, columns))
    H = _arrays(payloads['H.npz'], {'H'})['H']
    validate_payload(C, H, points, state, n_dofs=expected_n_dofs, parameters=expected_parameters)
    if len(points) != columns:
        raise ValueError('manifest/descriptor column count differs')
    return Loaded(C, H, points, state, identity, manifest, expected_manifest_sha256)
