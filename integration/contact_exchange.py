"""Exact-response continuation and batched quadratic-gap inspection.

This module changes storage and algebraic evaluation, not contact mechanics.
It never replaces full elastic K with the historical twelve-pressure-port
model, introduces penalty stiffness, or widens the contact gap tolerance.
The response callback must solve the original, explicitly constrained K.
For numerical gauges, callers must retain rigid equilibrium and audit the
reconstructed gauge reactions. A small linear residual alone cannot make a
physically incompatible gauge load admissible.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, Sequence
import numpy as np
from scipy.sparse import csc_matrix, hstack, issparse
from contact_patch_audit import convex_vertices, finite_array


def _real(a, ndim, name):
    v = np.asarray(a)
    if v.ndim != ndim or v.dtype.kind not in 'fiu' or not np.isfinite(v).all():
        raise ValueError(f'{name}: finite non-boolean {ndim}-D array required')
    return v.astype(float, copy=False)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


class QuadraticGapBatch:
    """Vectorized version of the existing extrema candidate enumeration.

    Evaluates vertices, interior edge extrema, and nonsingular feasible
    interior stationary points on each convex polygon. All coordinates use
    the supplied per-cell origin. This is floating-point FE-field inspection,
    not interval certification, continuum error control, or load qualification.
    """
    def __init__(self, polygons: Sequence, origins):
        if not len(polygons):
            raise ValueError('nonempty polygon collection required')
        self.origins = finite_array(origins, (len(polygons), 2), 'origins').copy()
        vv = [convex_vertices(p) for p in polygons]
        self.counts = np.array([len(v) for v in vv], dtype=int)
        self.n = len(vv)
        self.width = int(self.counts.max())
        self.valid = np.arange(self.width)[None, :] < self.counts[:, None]
        self.p = np.zeros((self.n, self.width, 2))
        self.e = np.zeros_like(self.p)
        for i, v in enumerate(vv):
            self.p[i, :len(v)] = v - self.origins[i]
            self.e[i, :len(v)] = np.roll(v, -1, axis=0) - v
        self.edge_scale2 = np.max(abs(self.e), axis=(1, 2))**2

    @staticmethod
    def _value(c, xy):
        x, y = xy[..., 0], xy[..., 1]
        return (c[:, 0, None] + c[:, 1, None]*x + c[:, 2, None]*y
                + c[:, 3, None]*x*x + c[:, 4, None]*x*y + c[:, 5, None]*y*y)

    def extrema(self, coefficients):
        c = finite_array(coefficients, (self.n, 6), 'gap coefficients')
        p, d = self.p, self.e
        x, y = p[..., 0], p[..., 1]
        dx, dy = d[..., 0], d[..., 1]
        aa = c[:, 3, None]*dx*dx + c[:, 4, None]*dx*dy + c[:, 5, None]*dy*dy
        bb = ((2*c[:, 3, None]*x+c[:, 4, None]*y+c[:, 1, None])*dx
              + (c[:, 4, None]*x+2*c[:, 5, None]*y+c[:, 2, None])*dy)
        t = np.zeros_like(aa)
        with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
            np.divide(-bb, 2*aa, out=t, where=aa != 0)
        edge_ok = self.valid & (aa != 0) & (t > 0) & (t < 1) & np.isfinite(t)
        edge = p + np.where(edge_ok, t, 0.)[..., None]*d
        A = np.zeros((self.n, 2, 2))
        A[:, 0, 0] = c[:, 3]; A[:, 1, 1] = c[:, 5]
        A[:, 0, 1] = A[:, 1, 0] = .5*c[:, 4]
        eigen = np.linalg.eigvalsh(A)
        nonsingular = np.min(abs(eigen), axis=1) > 1e-13*np.maximum(np.max(abs(eigen), axis=1), 1e-300)
        stationary = np.zeros((self.n, 2))
        if nonsingular.any():
            stationary[nonsingular] = np.linalg.solve(2*A[nonsingular], -c[nonsingular, 1:3, None])[..., 0]
        difference = stationary[:, None, :] - p
        cross = d[..., 0]*difference[..., 1] - d[..., 1]*difference[..., 0]
        feasible = np.all((cross >= -1e-12*np.maximum(self.edge_scale2[:, None], 1e-300)) | ~self.valid, axis=1)
        interior_ok = nonsingular & feasible
        xy = np.concatenate((p, edge, stationary[:, None, :]), axis=1)
        mask = np.concatenate((self.valid, edge_ok, interior_ok[:, None]), axis=1)
        val = self._value(c, xy)
        if not np.isfinite(val[mask]).all():
            raise ValueError('nonfinite evaluated gap')
        lo = np.argmin(np.where(mask, val, np.inf), axis=1)
        hi = np.argmax(np.where(mask, val, -np.inf), axis=1)
        rows = np.arange(self.n)
        return {
            'minimum': val[rows, lo], 'maximum': val[rows, hi],
            'minimum_at': xy[rows, lo] + self.origins,
            'maximum_at': xy[rows, hi] + self.origins,
            'candidate_count': mask.sum(axis=1),
            'floating_point_not_interval_certificate': True,
        }


@dataclass(frozen=True)
class ResponseCheck:
    probes: int
    largest_relative_error: float
    response_calls: int


class ExactResponseCache:
    """C.T K^-1 C without retaining a full displacement vector per column.

    Only sparse force maps C and their dense complementary-energy matrix H
    are kept. Reconstructing a full field performs ONE full-system response
    solve for the combined force. A verified checkpoint requires zero solves
    per old contact column; independent probe actions validate the checkpoint.

    This is a linear response cache, not a contact solver. Mean-pressure ports
    must not be substituted for missing spatial maps. Fingerprints of K, mesh,
    boundary conditions, loads and point identities belong in input_identity.
    """
    def __init__(self, size: int, response: Callable, input_identity: dict):
        if type(size) is not int or size < 1 or not callable(response):
            raise ValueError('positive dimension and response callback required')
        encoded = json.dumps(input_identity, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if not isinstance(input_identity, dict) or not input_identity:
            raise ValueError('nonempty input identity required')
        self.identity = json.loads(encoded)
        self.size = size
        self.response = response
        self.C = csc_matrix((size, 0), dtype=float)
        self.H = np.empty((0, 0), dtype=float)
        self.calls = 0
        self._busy = False

    def _maps(self, C):
        if not issparse(C) or C.ndim != 2 or C.shape[0] != self.size or C.dtype.kind not in 'fiu':
            raise ValueError('real sparse force-map matrix with original row count required')
        C = csc_matrix(C, dtype=float, copy=True)
        C.sum_duplicates(); C.eliminate_zeros(); C.sort_indices()
        if not np.isfinite(C.data).all():
            raise ValueError('nonfinite force map')
        return C

    def _response(self, rhs):
        if self._busy:
            raise RuntimeError('recursive response callback')
        self._busy = True
        try:
            u = _real(self.response(rhs.copy()), 1, 'full elastic response')
        finally:
            self._busy = False
        self.calls += 1
        if u.shape != (self.size,):
            raise ValueError('response did not retain full displacement dimension')
        return u

    def append(self, maps, *, reciprocity_tolerance=2e-8):
        """Solve only the new columns; commits state after all checks succeed."""
        if type(reciprocity_tolerance) not in (float, int) or not 0 < reciprocity_tolerance < 1e-3:
            raise ValueError('invalid reciprocity tolerance')
        new = self._maps(maps)
        n, k = self.H.shape[0], new.shape[1]
        if not k:
            return
        cross = np.zeros((n, k)); block = np.zeros((k, k))
        for j in range(k):
            u = self._response(new[:, j].toarray().ravel())
            if n:
                cross[:, j] = np.asarray(self.C.T @ u).ravel()
            block[:, j] = np.asarray(new.T @ u).ravel()
        scale = max(float(np.max(abs(block))), 1e-300)
        if np.max(abs(block-block.T)) > reciprocity_tolerance*scale:
            raise ValueError('nonreciprocal new elastic response')
        if np.min(np.diag(block)) < -reciprocity_tolerance*scale:
            raise ValueError('negative elastic self-energy')
        H = np.empty((n+k, n+k))
        H[:n, :n] = self.H
        H[:n, n:] = cross; H[n:, :n] = cross.T
        H[n:, n:] = (block+block.T)/2
        self.C = hstack((self.C, new), format='csc')
        self.H = H

    def restore(self, maps, H, identity, *, probes=5, relative_tolerance=2e-7):
        """Verify identity and deterministic full-K actions; never trust shape alone.

        Probe tests supplement immutable matrix/map fingerprints, not replace
        provenance or prove every matrix entry independently. A changed force
        map or checkpoint should be rejected first by its byte identity.
        """
        if self.C.shape[1]:
            raise ValueError('restore only into an empty cache')
        if identity != self.identity:
            raise ValueError('checkpoint input identity differs')
        if type(probes) is not int or probes < 1 or probes > 64:
            raise ValueError('invalid probe count')
        if type(relative_tolerance) not in (int, float) or not 0 < relative_tolerance < 1e-3:
            raise ValueError('invalid response validation tolerance')
        C = self._maps(maps); h = _real(H, 2, 'checkpoint response')
        n = C.shape[1]
        if not n or h.shape != (n, n):
            raise ValueError('checkpoint shape differs')
        scale = max(float(np.max(abs(h))), 1e-300)
        if np.max(abs(h-h.T)) > 2e-8*scale:
            raise ValueError('nonreciprocal checkpoint')
        rng = np.random.default_rng(73021)
        directions = [np.ones(n)] + [rng.choice([-1., 1.], n) for _ in range(probes-1)]
        err = 0.
        for v in directions:
            rhs = np.asarray(C @ v).ravel()
            measured = np.asarray(C.T @ self._response(rhs)).ravel()
            saved = h @ v
            denom = max(float(np.max(abs(measured))), float(np.max(abs(saved))), 1e-300)
            ratio = float(np.max(abs(measured-saved)))/denom
            if ratio > relative_tolerance:
                raise ValueError('checkpoint differs from current complete elastic operator')
            err = max(err, ratio)
        self.C = C; self.H = (h+h.T)/2
        return ResponseCheck(probes, err, probes)

    def reconstruct(self, external_force, interface_force, *, rigid_displacement=None):
        f = _real(external_force, 1, 'external force')
        lam = _real(interface_force, 1, 'interface force')
        if f.shape != (self.size,) or lam.shape != (self.C.shape[1],):
            raise ValueError('full field dimensions differ')
        applied = f - np.asarray(self.C @ lam).ravel()
        u = self._response(applied)
        if rigid_displacement is not None:
            r = _real(rigid_displacement, 1, 'rigid displacement')
            if r.shape != (self.size,):
                raise ValueError('rigid field dimensions differ')
            u = u + r
        return u, applied

    def storage_bytes(self):
        return int(self.H.nbytes + self.C.data.nbytes + self.C.indices.nbytes + self.C.indptr.nbytes)


def select_violations(checks, existing, *, maximum_new=128, duplicate_distance=1e-9):
    """Round-robin worst-gap selection; existing constraints are never removed.

    No geometry-based spacing cutoff discards a distinct violating witness.
    A patch gets a turn before a second point from another patch is selected.
    Candidate feasibility is established only by the caller's complete audit.
    """
    if type(maximum_new) is not int or maximum_new < 1:
        raise ValueError('positive maximum_new required')
    if type(duplicate_distance) not in (int, float) or not 0 < duplicate_distance < 1e-4:
        raise ValueError('invalid duplicate distance')
    if not isinstance(existing, dict):
        raise ValueError('patch-keyed prior witness collection required')
    prior = {}
    for label, points in existing.items():
        if not isinstance(label, str) or not label:
            raise ValueError('nonempty patch identity required')
        p = np.asarray(points)
        if p.shape == (0,):
            p = np.empty((0, 2))
        if p.ndim != 2 or p.shape[1] != 2 or p.dtype.kind not in 'fiu' or not np.isfinite(p).all():
            raise ValueError('invalid prior witness positions')
        prior[label] = [v.astype(float, copy=True) for v in p]
    groups = {}
    for row in checks:
        xy = finite_array(row['minimum_at'], (2,), 'witness')
        minimum = finite_array([row['minimum']], (1,), 'gap')[0]
        if type(row['cell']) is not int or row['cell'] < 0 or not isinstance(row['patch'], str) or not row['patch']:
            raise ValueError('invalid witness identity')
        groups.setdefault(row['patch'], []).append((minimum, row['cell'], xy))
    for values in groups.values():
        values.sort(key=lambda t: (t[0], t[1], t[2][0], t[2][1]))
    selected = []; offsets = {k: 0 for k in groups}
    while len(selected) < maximum_new:
        progress = False
        for label in sorted(groups):
            values = groups[label]; prior.setdefault(label, [])
            while offsets[label] < len(values):
                minimum, cell, xy = values[offsets[label]]; offsets[label] += 1
                if any(np.linalg.norm(xy-p) < duplicate_distance for p in prior[label]):
                    continue
                selected.append({'patch': label, 'cell': cell, 'minimum': float(minimum), 'minimum_at': xy.tolist()})
                prior[label].append(xy); progress = True
                break
            if len(selected) >= maximum_new:
                break
        if not progress:
            break
    return selected
