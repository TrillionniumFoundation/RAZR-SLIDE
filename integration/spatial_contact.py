"""Spatial unilateral contact in an explicitly supplied elastic displacement space.

Minimize 1/2 u.K.u - f.u subject to affine/quadratic-in-position gap >= 0.
A feasible active-set QP is followed by an exchange step at the *actual*
quadratic gap minima on every supplied common polygon. No penalty spring,
contact-gap clipping or hidden rigid-body anchoring is introduced.

Contact multipliers are generalized forces at enforced trace points, NOT a
reconstructed finite-area pressure field. Passing certifies only the supplied
finite-dimensional energy, reference-plane pairing and audited polygon union,
in floating-point tolerances; not full FE equilibrium outside that space,
FE/contact convergence, finite rotations, strength or hardware qualification.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np
from scipy.linalg import null_space
from scipy.optimize import linprog
from contact_patch_audit import convex_vertices, evaluate, extrema, finite_array

GO = {'candidate_go': False, 'fixture_fabrication_go': False,
      'manufacturing_go': False}


def _real(value, ndim, name):
    a = np.asarray(value)
    if a.dtype.kind not in 'fiu' or a.ndim != ndim or not np.isfinite(a).all():
        raise ValueError(name + ': finite real non-boolean array required')
    return a.astype(float)


def _independent(rows, candidates, tolerance):
    chosen = []
    rank = 0
    for j in candidates:
        newrank = np.linalg.matrix_rank(rows[chosen + [j]], tol=tolerance)
        if newrank > rank:
            chosen.append(j); rank = newrank
    return chosen


def _feasible(A, b, n, preferred, tol):
    if np.all(A @ preferred - b <= tol):
        return preferred.copy(), 'given'
    # Nearest feasible point in infinity norm; no changes to the actual gaps.
    eye = np.eye(n)
    aa = np.block([[A, np.zeros((len(b), 1))],
                   [eye, -np.ones((n, 1))],
                   [-eye, -np.ones((n, 1))]])
    bb = np.r_[b, preferred, -preferred]
    lp = linprog(np.r_[np.zeros(n), 1.], A_ub=aa, b_ub=bb,
                 bounds=[(None, None)]*n + [(0., None)], method='highs',
                 options={'primal_feasibility_tolerance': 1e-9,
                          'dual_feasibility_tolerance': 1e-9})
    if not lp.success:
        return None, 'infeasible' if lp.status == 2 else 'phase_one_failure'
    if np.max(A @ lp.x[:n] - b, initial=0.) > max(tol, 2e-9):
        return None, 'phase_one_residual'
    return lp.x[:n], 'linear_program'


def solve_qp(K, f, A, b, *, equality=None, equality_rhs=None, initial=None,
             tolerance=1e-9, max_iterations=3000):
    """Convex dense/reduced QP with explicit equality and unilateral constraints.

    K may be positive semidefinite. Neutral directions remain neutral; loaded
    unbounded directions return a recession witness, never fake stiffness.
    Equality rows are user-supplied physical/gauge conditions, not defaults.
    Inequality convention is A.u <= b; its multipliers must be nonnegative.
    """
    if type(tolerance) not in (int, float) or not 0 < tolerance < 1e-3:
        raise ValueError('invalid tolerance')
    if type(max_iterations) is not int or max_iterations < 1:
        raise ValueError('positive iteration limit required')
    K = _real(K, 2, 'K'); f = _real(f, 1, 'f')
    n = len(f)
    if not n or K.shape != (n, n):
        raise ValueError('nonempty consistent energy dimensions required')
    A = _real(A, 2, 'A'); b = _real(b, 1, 'b')
    if A.shape != (len(b), n):
        raise ValueError('constraint dimensions differ')
    ks = float(np.max(abs(K)))
    if np.max(abs(K-K.T)) > 1e-11*max(ks, 1e-300):
        raise ValueError('nonreciprocal stiffness')
    K = (K+K.T)/2
    eig = np.linalg.eigvalsh(K)
    if eig.min() < -1e-11*max(float(abs(eig).max()), 1e-300):
        raise ValueError('negative-energy stiffness mode')
    if equality is None:
        if equality_rhs is not None:
            raise ValueError('equality_rhs without equality')
        E = np.zeros((0, n)); er = np.empty(0)
    else:
        E = _real(equality, 2, 'equality'); er = _real(equality_rhs, 1, 'equality_rhs')
        if E.shape != (len(er), n):
            raise ValueError('equality dimensions differ')
    if len(er):
        xpart = np.linalg.lstsq(E, er, rcond=1e-12)[0]
        if np.max(abs(E@xpart-er)) > tolerance*max(float(abs(er).max()), 1e-12):
            return {**GO, 'status':'inconsistent_equalities', 'passed':False}
        Z = null_space(E, rcond=1e-12)
    else:
        xpart = np.zeros(n); Z = np.eye(n)
    H = Z.T @ K @ Z; rhs = Z.T @ (f-K@xpart)
    C = A@Z; d = b-A@xpart; nr = Z.shape[1]
    rn = np.linalg.norm(C, axis=1)
    zero = rn <= 1e-14*np.maximum(np.linalg.norm(A, axis=1), 1e-300)
    if np.any(zero & (d < -tolerance*np.maximum(abs(b), 1e-12))):
        return {**GO, 'status':'infeasible_constraints', 'passed':False}
    used = np.flatnonzero(~zero)
    Cn = C[used]/rn[used, None]; dn = d[used]/rn[used]
    hnorm = float(np.max(abs(H), initial=0.))
    fscale = float(np.max(abs(rhs), initial=0.))
    xscale = max(float(np.max(abs(dn), initial=0.)),
                 fscale/hnorm if hnorm else 0., 1e-12)
    kscale = hnorm if hnorm else max(fscale/xscale, 1.)
    Hs = H/kscale; fs = rhs/(kscale*xscale); ds = dn/xscale
    start = np.zeros(nr)
    if initial is not None:
        u0 = finite_array(initial, (n,), 'initial')
        start = Z.T @ (u0-xpart)/xscale
    x, phase = _feasible(Cn, ds, nr, start, tolerance) if nr else (np.empty(0), 'fixed_by_equalities')
    if x is None:
        return {**GO, 'status':phase, 'passed':False}
    W = _independent(Cn, np.flatnonzero(abs(Cn@x-ds) <= tolerance).tolist(), 1e-11)
    trace = []; mult = np.zeros(len(used)); status = 'iteration_limit'; p = np.zeros(nr)
    for iteration in range(max_iterations):
        grad = Hs@x - fs
        AW = Cn[W]
        N = null_space(AW, rcond=1e-12) if len(W) else np.eye(nr)
        hz = N.T@Hs@N; gz = N.T@grad
        ev, V = np.linalg.eigh((hz+hz.T)/2) if len(gz) else (np.empty(0), np.empty((0,0)))
        cut = 1e-12*max(float(np.max(abs(ev), initial=0.)), 1e-300)
        positive = ev > cut
        nz = V[:, ~positive].T@gz
        null_descent = np.linalg.norm(nz) > tolerance*max(np.linalg.norm(grad), np.linalg.norm(fs), 1e-12)
        if null_descent:
            p = -N@(V[:, ~positive]@nz)
        else:
            p = -N@(V[:, positive]@((V[:, positive].T@gz)/ev[positive]))
        small = np.linalg.norm(p) <= tolerance*max(np.linalg.norm(x), 1.)
        if small and not null_descent:
            mu = np.linalg.lstsq(AW.T, -grad, rcond=1e-12)[0] if len(W) else np.empty(0)
            if not len(mu) or mu.min() >= -tolerance*max(np.linalg.norm(grad), np.linalg.norm(fs), 1e-12):
                mult = np.zeros(len(used)); mult[W] = mu
                status = 'optimal'; break
            del W[int(mu.argmin())]
            continue
        Ap = Cn@p; slack = ds-Cn@x
        eligible = [i for i in range(len(used)) if i not in W and Ap[i] > 1e-12*max(np.linalg.norm(p), 1e-300)]
        ratios = [(max(0., float(slack[i]))/Ap[i], i) for i in eligible]
        step, block = min(ratios) if ratios else (np.inf, None)
        if null_descent and not np.isfinite(step):
            direction = Z@p
            witness = {'direction':direction.tolist(),
                       'curvature':float(direction@K@direction),
                       'load_work':float(f@direction),
                       'maximum_constraint_rate':float(np.max(A@direction)) if len(b) else 0.,
                       'equality_rate_norm':float(np.linalg.norm(E@direction))}
            return {**GO, 'status':'unbounded_free_mode', 'passed':False,
                    'recession_witness':witness, 'iterations':iteration+1}
        alpha = step if null_descent else min(1., step)
        x = x + alpha*p
        trace.append({'iteration':iteration,'active':len(W),'step':float(alpha),'zero_curvature':bool(null_descent)})
        if block is not None and (null_descent or step < 1.-tolerance):
            newW = _independent(Cn, W+[block], 1e-11)
            if len(newW) == len(W) and alpha <= tolerance:
                status = 'dependent_blocking_constraint'; break
            W = newW
    u = xpart+Z@(x*xscale)
    lam = np.zeros(len(b)); lam[used] = mult*kscale*xscale/rn[used]
    residual = K@u-f+A.T@lam
    nu = np.linalg.lstsq(E.T, -residual, rcond=1e-12)[0] if len(er) else np.empty(0)
    stationarity = residual + E.T@nu
    slack = b-A@u
    force_norm = max(float(np.max(abs(f), initial=0.)), float(np.max(abs(K@u), initial=0.)),
                     float(np.max(abs(A.T@lam), initial=0.)), 1e-12)
    gap_norm = max(float(np.max(abs(b), initial=0.)), float(np.max(abs(A@u), initial=0.)), 1e-12)
    errors = {'stationarity_relative':float(np.max(abs(stationarity), initial=0.)/force_norm),
              'inequality_violation_relative':float(max(0., -float(np.min(slack, initial=0.)))/gap_norm),
              'negative_multiplier_relative':float(max(0., -float(np.min(lam, initial=0.)))/force_norm),
              'complementarity_relative':float(np.max(abs(lam*slack), initial=0.)/(force_norm*gap_norm)),
              'equality_residual_norm':float(np.linalg.norm(E@u-er))}
    accepted = status == 'optimal' and max(list(errors.values())[:4]) <= 30*tolerance
    active_rows = A[lam > 30*tolerance*force_norm]
    finalnull = null_space(np.vstack([K/max(ks,1e-300), E, active_rows]), rcond=1e-11).shape[1]
    return {**GO, 'status':status if accepted else 'numerical_'+status,
            'passed':bool(accepted), 'u':u.tolist(), 'multipliers':lam.tolist(),
            'equality_multipliers':nu.tolist(), 'gaps':slack.tolist(),
            'objective':float(.5*u@K@u-f@u), 'kkt':errors,
            'iterations':iteration+1, 'remaining_neutral_modes':int(finalnull),
            'numeric_scaling':{'displacement':xscale,'stiffness':kscale},
            'trace':trace, 'penalty_or_artificial_stiffness_added':False}


@dataclass(frozen=True)
class GapCell:
    """g(x,y;u)=offset[6]+response[6,n]@u over a common convex polygon."""
    name: str
    vertices: np.ndarray
    offset: np.ndarray
    response: np.ndarray
    origin: tuple[float, float] = (0., 0.)

    def validate(self, n):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError('cell identity required')
        vertices = convex_vertices(self.vertices)
        offset = finite_array(self.offset, (6,), 'gap offset')
        response = finite_array(self.response, (6,n), 'gap response')
        origin = tuple(finite_array(self.origin, (2,), 'origin'))
        return GapCell(self.name, vertices, offset, response, origin)


def solve_spatial_contact(K, f, cells: Sequence[GapCell], *, equality=None,
                          equality_rhs=None, gap_tolerance=1e-7,
                          qp_tolerance=1e-10, max_exchanges=64,
                          max_constraints=4096, max_qp_iterations=3000):
    """Adaptive constraints at quadratic minima, with independent full-cell audit.

    Every constraint contributes a local trace reaction; no prescribed average
    pressure shape is carried forward. If limits or errors occur, report failure.
    Positive reactions have zero gap at their trace points to numeric tolerance.
    This does not claim an area-pressure reconstruction or discretization error.
    """
    if type(gap_tolerance) not in (float,int) or not 0 < gap_tolerance < 1:
        raise ValueError('positive explicit gap tolerance required')
    if type(max_exchanges) is not int or max_exchanges < 1:
        raise ValueError('positive exchange count required')
    if type(max_constraints) is not int or max_constraints < 1:
        raise ValueError('positive constraint limit required')
    n = len(f); cells = [c.validate(n) for c in cells]
    if not cells or len({c.name for c in cells}) != len(cells):
        raise ValueError('nonempty uniquely identified cells required')
    constraints = []; bycell = {c.name:[] for c in cells}; rejected = []
    def add(j, xy, reason):
        c = cells[j]; xy = np.asarray(xy, dtype=float)
        diameter = np.max(np.ptp(c.vertices,axis=0))
        if any(np.linalg.norm(xy-old) <= 1e-12*max(diameter, 1e-12) for old in bycell[c.name]):
            return False
        bycell[c.name].append(xy.copy())
        response = evaluate(c.response, xy[None,:], c.origin)[0]
        gap = float(evaluate(c.offset, xy[None,:], c.origin)[0])
        constraints.append((j,xy.copy(),-response,gap,reason)); return True
    # Deliberately not assumed sufficient: the audit also tests edge/interior extrema.
    for j,c in enumerate(cells):
        for xy in c.vertices: add(j,xy,'initial_vertex')
    history = []; initial = None; qp = None; checks = []
    for exchange in range(max_exchanges):
        if len(constraints) > max_constraints:
            return {**GO,'passed':False,'status':'constraint_limit','history':history}
        A = np.stack([c[2] for c in constraints]); b = np.array([c[3] for c in constraints])
        qp = solve_qp(K,f,A,b,equality=equality,equality_rhs=equality_rhs,
                      initial=initial,tolerance=qp_tolerance,max_iterations=max_qp_iterations)
        if not qp['passed']:
            return {**GO,'passed':False,'status':'qp_failure','qp':qp,'history':history}
        initial = np.asarray(qp['u']); checks = []
        for j,c in enumerate(cells):
            ext = extrema(c.offset+c.response@initial,c.vertices,c.origin)
            checks.append({'cell':c.name,**ext})
        bad = [j for j,x in enumerate(checks) if x['minimum'] < -gap_tolerance]
        history.append({'exchange':exchange,'constraints':len(constraints),
                        'minimum_gap':min(x['minimum'] for x in checks),'violating_cells':len(bad),
                        'qp_iterations':qp['iterations']})
        if not bad:
            local = []
            for i,(j,xy,row,gap,reason) in enumerate(constraints):
                local.append({'cell':cells[j].name,'xy':xy.tolist(),'gap':float(gap-row@initial),
                              'reaction':qp['multipliers'][i],'origin':reason})
            return {**GO,'passed':True,'status':'discrete_spatial_equilibrium',
                    'u':qp['u'],'qp':qp,'cell_extrema':checks,'local_reactions':local,
                    'history':history,'rejected_intermediate_fields':rejected,
                    'audited_cells':len(cells),'gap_tolerance':gap_tolerance,
                    'finite_area_pressure_reconstruction':False,
                    'full_FE_outside_supplied_displacement_space_verified':False,
                    'continuum_or_mesh_convergence_verified':False,
                    'certified_interval_arithmetic':False}
        nadded=0
        for j in bad:
            nadded+=add(j, checks[j]['minimum_at'],'minimum_exchange')
        rejected.append({'exchange':exchange,'u':initial.tolist(),'negative_cells':[checks[j] for j in bad]})
        if not nadded:
            return {**GO,'passed':False,'status':'stalled_negative_gap','qp':qp,
                    'cell_extrema':checks,'history':history}
    return {**GO,'passed':False,'status':'exchange_limit','qp':qp,
            'cell_extrema':checks,'history':history}
