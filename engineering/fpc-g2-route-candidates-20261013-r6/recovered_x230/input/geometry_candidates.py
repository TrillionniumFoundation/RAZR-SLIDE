#!/usr/bin/env python3
"""Conditional G2 replacements of R46's four discontinuous route junctions.

This module only changes the path, never either anchor or the motion sequence.
It does not represent a supplier FPC, material directors, clearance, or fatigue.
Lengths are curve arc lengths, not lengths of a plotting polygon.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad
from scipy.optimize import brentq, minimize_scalar

sys.dont_write_bytecode = True
SLIDE = 79.75
DOCK = 8.2
XC, YA, YB0, ZA, ZB0 = 32.7, 70.0, 15.0, 6.05, -3.4
RADIUS, CX, ALPHA, Z_BAY_STUDY = 15.0, 19.0, .25, 3.5
TARGET_LENGTHS = (160.20738578362864, 148.20738578362864, 153.20738578362864)
GAUSS_X, GAUSS_W = leggauss(64)
GAUSS_U, GAUSS_W = (GAUSS_X + 1) / 2, GAUSS_W / 2
ARC_INVERSE_ATOL_MM = 2e-13


class GeometryRejected(ValueError):
    """Candidate is rejected without changing anchors or adding length."""


@dataclass(frozen=True)
class Config:
    target_length_mm: float = TARGET_LENGTHS[0]
    dA_mm: float = .5
    dB_mm: float = .25
    dJ_mm: float = .25
    radius_mm: float = RADIUS
    cx_mm: float = CX
    alpha: float = ALPHA

    @property
    def name(self):
        return ('L%.6f_A%.2f_B%.2f_J%.2f' %
                (self.target_length_mm, self.dA_mm, self.dB_mm, self.dJ_mm))


def candidate_configs():
    return [Config(*args) for args in itertools.product(
        TARGET_LENGTHS, (.5, 1.), (.25, .5, 1.), (.25, .5))]


def _unit_curvature(first, second):
    speed2 = np.sum(first * first, axis=-1)
    if np.any(~np.isfinite(speed2)) or np.any(speed2 < 1e-16):
        raise GeometryRejected('zero/invalid parameter speed')
    tangent = first / np.sqrt(speed2)[..., None]
    curvature = (second - tangent * np.sum(tangent * second, axis=-1)[..., None]) / speed2[..., None]
    return tangent, curvature


def _bezier(control, u):
    """Vectorized Bernstein evaluation, including exact one-sided endpoints."""
    n = len(control) - 1
    u = np.atleast_1d(np.asarray(u, float))
    basis = np.column_stack([math.comb(n, j) * u**j * (1-u)**(n-j)
                             for j in range(n+1)])
    return basis @ control


@dataclass
class Segment:
    tag: str
    kind: str
    data: dict
    t0: float = 0.
    t1: float = 1.

    def derivatives(self, u):
        u = np.atleast_1d(np.asarray(u, float))
        if np.any(~np.isfinite(u)) or np.any(u < -1e-12) or np.any(u > 1+1e-12):
            raise GeometryRejected('segment parameter outside [0,1]')
        u = np.clip(u, 0, 1)
        span = self.t1 - self.t0
        v = self.t0 + span*u
        if self.kind == 'bezier':
            control = self.data['control']
            n = len(control)-1
            p = _bezier(control, v)
            first = _bezier(n*np.diff(control, axis=0), v)*span
            second = _bezier(n*(n-1)*np.diff(control, n=2, axis=0), v)*span**2
        elif self.kind == 'line':
            start, end = self.data['start'], self.data['end']
            p = start + v[:, None]*(end-start)
            first = np.tile((end-start)*span, (len(u), 1))
            second = np.zeros_like(first)
        elif self.kind == 'leg':
            start, dy, dz = self.data['start'], self.data['dy'], self.data['dz']
            p = start + np.column_stack((np.zeros_like(v), dy*v, dz*(3*v*v-2*v*v*v)))
            first = np.column_stack((np.zeros_like(v), np.full_like(v, dy), dz*6*v*(1-v)))*span
            second = np.column_stack((np.zeros_like(v), np.zeros_like(v), dz*(6-12*v)))*span**2
        elif self.kind == 'arc':
            r, cx, fy, z = (self.data[k] for k in ('radius', 'cx', 'fold_y', 'z'))
            theta = math.pi*v
            p = np.column_stack((cx-r*np.cos(theta), fy+r*np.sin(theta), np.full_like(v, z)))
            first = r*math.pi*np.column_stack((np.sin(theta), np.cos(theta), np.zeros_like(v)))*span
            second = r*math.pi**2*np.column_stack((np.cos(theta), -np.sin(theta), np.zeros_like(v)))*span**2
        else:
            raise GeometryRejected('unknown segment kind')
        return p, first, second

    def evaluate(self, u):
        p, first, second = self.derivatives(u)
        t, k = _unit_curvature(first, second)
        return p, t, k

    def partial_length(self, u):
        u = np.atleast_1d(np.asarray(u, float))
        if self.kind in ('line', 'arc'):
            speed = np.linalg.norm(self.derivatives([0.])[1][0])
            return u*speed
        probes = (u[:, None]*GAUSS_U).reshape(-1)
        speed = np.linalg.norm(self.derivatives(probes)[1], axis=1).reshape(len(u), -1)
        return u*np.sum(speed*GAUSS_W, axis=1)

    def length(self):
        return float(self.partial_length([1.])[0])

    def adaptive_length(self):
        result, err = quad(lambda u: float(np.linalg.norm(self.derivatives([u])[1][0])),
                           0., 1., epsabs=1e-10, epsrel=1e-12, limit=150)
        return result, err

    def inverse_length(self, distance):
        distance = np.atleast_1d(np.asarray(distance, float))
        full = self.length()
        if np.any(~np.isfinite(distance)) or np.any(distance < -1e-9) or np.any(distance > full+1e-9):
            raise GeometryRejected('segment material distance outside integrated length')
        # The fold root has a reported few-picometre length residual. Snap only
        # that numerical endpoint range; do not stretch the physical curve.
        distance = np.clip(distance, 0., full)
        u = np.clip(distance/full, 0, 1)
        lo, hi = np.zeros_like(u), np.ones_like(u)
        for _ in range(45):
            residual = self.partial_length(u) - distance
            if not len(residual) or np.max(np.abs(residual)) < ARC_INVERSE_ATOL_MM:
                break
            lo = np.where(residual < 0, u, lo)
            hi = np.where(residual > 0, u, hi)
            speed = np.linalg.norm(self.derivatives(u)[1], axis=1)
            proposal = u - residual/speed
            u = np.where((proposal > lo) & (proposal < hi), proposal, (lo+hi)/2)
        if len(u) and np.max(np.abs(self.partial_length(u)-distance)) > ARC_INVERSE_ATOL_MM:
            raise GeometryRejected('fixed material arc-length inverse failed')
        return u


def _trim(seg, t0, t1):
    if not 0 <= t0 < t1 <= 1:
        raise GeometryRejected('trims consumed an original segment')
    return Segment(seg.tag, seg.kind, seg.data, t0, t1)


def _blend(tag, left, lt, right, rt, trim):
    p0, T0, K0 = [v[0] for v in left.evaluate([lt])]
    p1, T1, K1 = [v[0] for v in right.evaluate([rt])]
    # Hermite endpoint v uses research scale 2*trim; a is purely normal.
    # K is the geometric arc-length derivative dT/dsigma in world coordinates.
    v0, v1 = 2*trim*T0, 2*trim*T1
    a0, a1 = (2*trim)**2*K0, (2*trim)**2*K1
    controls = np.array([p0, p0+v0/5, p0+2*v0/5+a0/20,
                         p1-2*v1/5+a1/20, p1-v1/5, p1])
    return Segment(tag, 'bezier', {'control': controls})


def _segments(config, s, q, fold):
    c = config
    xa, xb = c.cx_mm-c.radius_mm, c.cx_mm+c.radius_mm
    yb, zb = YB0+s, ZB0+q
    z = c.alpha*ZA + (1-c.alpha)*(Z_BAY_STUDY+q-DOCK)
    A, B = np.array([XC, YA, ZA]), np.array([XC, yb, zb])
    a0, b1 = np.array([xa, YA, ZA]), np.array([xb, yb, zb])
    a = Segment('A_STUB', 'line', {'start': A, 'end': a0})
    al = Segment('A_LEG', 'leg', {'start': a0, 'dy': fold-YA, 'dz': z-ZA})
    arc = Segment('U_ARC', 'arc', {'radius': c.radius_mm, 'cx': c.cx_mm, 'fold_y': fold, 'z': z})
    bl = Segment('B_LEG', 'leg', {'start': np.array([xb, fold, z]), 'dy': yb-fold, 'dz': zb-z})
    b = Segment('B_STUB', 'line', {'start': b1, 'end': B})
    a_stub_t = 1-c.dA_mm/(XC-xa)
    a_start_t, a_end_t = c.dA_mm/(fold-YA), 1-c.dJ_mm/(fold-YA)
    b_start_t, b_end_t = c.dJ_mm/(fold-yb), 1-c.dB_mm/(fold-yb)
    b_stub_t = c.dB_mm/(xb-XC)
    arc_t = math.asin(c.dJ_mm/c.radius_mm)/math.pi
    return [_trim(a, 0, a_stub_t), _blend('A_CORNER_G2', a, a_stub_t, al, a_start_t, c.dA_mm),
            _trim(al, a_start_t, a_end_t), _blend('A_LEG_U_G2', al, a_end_t, arc, arc_t, c.dJ_mm),
            _trim(arc, arc_t, 1-arc_t), _blend('U_B_LEG_G2', arc, 1-arc_t, bl, b_start_t, c.dJ_mm),
            _trim(bl, b_start_t, b_end_t), _blend('B_CORNER_G2', bl, b_end_t, b, b_stub_t, c.dB_mm),
            _trim(b, b_stub_t, 1)]


class CandidateCurve:
    def __init__(self, config, s, q, fold, segments):
        self.config, self.s, self.q, self.fold = config, s, q, fold
        self.segments = self.ordered_segments = segments
        self.lengths = np.array([seg.length() for seg in segments])
        self.bounds = np.r_[0., np.cumsum(self.lengths)]
        self.target = config.target_length_mm
        if abs(self.bounds[-1]-self.target) > 1e-8:
            raise GeometryRejected('constant material length root not converged')

    def evaluate(self, fixed_sigma):
        """Return (position, unit tangent, world arc-length curvature), N by 3."""
        sigma = np.atleast_1d(np.asarray(fixed_sigma, float))
        if np.any(~np.isfinite(sigma)) or np.any(sigma < -1e-9) or np.any(sigma > self.target+1e-9):
            raise GeometryRejected('fixed material stations outside candidate length')
        sigma = np.clip(sigma, 0, self.target)
        ids = np.minimum(np.searchsorted(self.bounds, sigma, side='right')-1, len(self.segments)-1)
        p, t, k = [np.empty((len(sigma), 3)) for _ in range(3)]
        for i, seg in enumerate(self.segments):
            mask = ids == i
            if np.any(mask):
                u = seg.inverse_length(sigma[mask]-self.bounds[i])
                p[mask], t[mask], k[mask] = seg.evaluate(u)
        return p, t, k

    def joint_errors(self):
        rows = []
        for a, b in zip(self.segments[:-1], self.segments[1:]):
            av, bv = a.evaluate([1.]), b.evaluate([0.])
            errors = [float(np.linalg.norm(x[0]-y[0])) for x, y in zip(av, bv)]
            rows.append(dict(left=a.tag, right=b.tag, position_error_mm=errors[0],
                             tangent_error=errors[1], curvature_error_per_mm=errors[2]))
        return rows

    def min_radius(self, refine=True):
        """Find sampled curvature maxima; optional bounded local refinement.

        This is numerical screening, not a proof of a vendor radius limit.
        """
        highest = 0.
        witness = None
        for seg in self.segments:
            grid = np.linspace(0., 1., 49)
            norms = np.linalg.norm(seg.evaluate(grid)[2], axis=1)
            indices = [0, 48] + [i for i in range(1, 48) if norms[i] >= norms[i-1] and norms[i] >= norms[i+1]]
            for i in indices:
                u, k = float(grid[i]), float(norms[i])
                if refine and 0 < i < 48 and seg.kind not in ('arc', 'line'):
                    opt = minimize_scalar(lambda x: -float(np.linalg.norm(seg.evaluate([x])[2][0])),
                                          bounds=(grid[i-1], grid[i+1]), method='bounded',
                                          options={'xatol': 1e-11})
                    if opt.success and -opt.fun > k:
                        u, k = float(opt.x), float(-opt.fun)
                if k > highest:
                    highest, witness = k, dict(segment=seg.tag, parameter=u,
                                              xyz_mm=seg.evaluate([u])[0][0].tolist())
        return (1/highest if highest > 1e-14 else None), witness


def build_candidate(config, s, q):
    if isinstance(config, dict):
        config = Config(**config)
    values = list(asdict(config).values()) + [s, q]
    if not all(math.isfinite(v) for v in values):
        raise GeometryRejected('nonfinite config/pose')
    if not (0 <= s <= SLIDE and 0 <= q <= DOCK and (q == 0 or s == SLIDE)):
        raise GeometryRejected('pose outside authorized sequential slide then dock')
    if (config.radius_mm, config.cx_mm, config.alpha) != (RADIUS, CX, ALPHA):
        raise GeometryRejected('this bounded experiment cannot relocate or resize the U')
    if not (0 < config.dA_mm < XC-(CX-RADIUS) and 0 < config.dB_mm < CX+RADIUS-XC
            and 0 < config.dJ_mm < RADIUS and config.target_length_mm > 0):
        raise GeometryRejected('trims would consume an anchor stub or U')
    lower = max(YA+config.dA_mm+config.dJ_mm, YB0+s+config.dB_mm+config.dJ_mm)+1e-5
    def residual(fold):
        return sum(seg.length() for seg in _segments(config, s, q, fold))-config.target_length_mm
    low = residual(lower)
    if low > 1e-9:
        raise GeometryRejected('fixed target shorter than minimum trimmed geometry: %.12g mm' % low)
    upper = lower+config.target_length_mm
    if residual(upper) <= 0:
        raise GeometryRejected('no constant-length fold root in bounded search')
    fold = brentq(residual, lower, upper, xtol=1e-11, rtol=1e-14)
    return CandidateCurve(config, float(s), float(q), fold, _segments(config, s, q, fold))


def poses(slide_steps=81, dock_steps=41):
    return [(float(s), 0.) for s in np.linspace(0, SLIDE, slide_steps)] + [
        (SLIDE, float(q)) for q in np.linspace(0, DOCK, dock_steps)[1:]]


def polyline_self_intersections(points, tolerance=1e-8):
    """Actual nonadjacent 3D chord intersection screen, never a curve proof.

    All nonadjacent chords are considered. Expanded AABBs only reject pairs;
    each remaining pair gets a constrained closest-segment calculation.
    """
    points = np.asarray(points, float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.all(np.isfinite(points)):
        raise GeometryRejected('invalid polyline')
    starts, ends = points[:-1], points[1:]
    low, high = np.minimum(starts, ends), np.maximum(starts, ends)
    overlapping = np.all((high[:, None, :] + tolerance >= low[None, :, :]) &
                         (high[None, :, :] + tolerance >= low[:, None, :]), axis=2)
    i, j = np.where(np.triu(overlapping, k=2))
    witnesses = []
    for ia, ib in zip(i, j):
        u, v, w = ends[ia]-starts[ia], ends[ib]-starts[ib], starts[ia]-starts[ib]
        a, b, c = float(u@u), float(u@v), float(v@v)
        d, e = float(u@w), float(v@w)
        if min(a, c) < 1e-24:
            raise GeometryRejected('degenerate self-intersection chord')
        denominator = a*c-b*b
        s = float(np.clip((b*e-c*d)/denominator, 0, 1)) if denominator > 1e-18*a*c else 0.
        t = (b*s+e)/c
        if t < 0:
            t, s = 0., float(np.clip(-d/a, 0, 1))
        elif t > 1:
            t, s = 1., float(np.clip((b-d)/a, 0, 1))
        pa, pb = starts[ia]+s*u, starts[ib]+t*v
        distance = float(np.linalg.norm(pa-pb))
        if distance <= tolerance:
            witnesses.append(dict(first_chord=int(ia), second_chord=int(ib),
                                  distance_mm=distance, first_xyz_mm=pa.tolist(),
                                  second_xyz_mm=pb.tolist()))
    return dict(chord_count=len(starts), nonadjacent_AABB_candidate_pairs=len(i),
                intersecting_chord_pairs=len(witnesses), first_witnesses=witnesses[:4],
                distance_tolerance_mm=tolerance, analytical_curve_self_intersection_proved_absent=False)


def _gross_screen(curve, p):
    # Original R46 gross research bounds; not proof that FPC fits a bay.
    # Union of equal-size A and translated B gross boxes in Y/Z.
    A = ((np.abs(p[:, 0]) <= 36.995) & (p[:, 1] >= 0) & (p[:, 1] <= 94.25)
         & (p[:, 2] >= -3.4) & (p[:, 2] <= 7.2))
    B = ((np.abs(p[:, 0]) <= 36.995) & (p[:, 1] >= curve.s) & (p[:, 1] <= 94.25+curve.s)
         & (p[:, 2] >= -DOCK+curve.q) & (p[:, 2] <= 7.2-DOCK+curve.q))
    outside = np.flatnonzero(~(A | B))
    return dict(centerline_outside_union_count=len(outside),
                first_outside_xyz_mm=p[outside[0]].tolist() if len(outside) else None,
                U_top_beyond_B_gross_y_mm=max(0., curve.fold+RADIUS-curve.s-94.25),
                gross_boxes_are_only_research_proxies=True,
                finite_ribbon_bay_clearance_checked=False)


def scan(output, slide_steps=81, dock_steps=41):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    rows = []
    for config in candidate_configs():
        record = dict(config=asdict(config), name=config.name, pose_rows=[], failure_rows=[])
        for s, q in poses(slide_steps, dock_steps):
            try:
                curve = build_candidate(config, s, q)
                # Every exact join plus 481 fixed material stations is evaluated.
                stations = np.unique(np.r_[np.linspace(0, curve.target, 481), curve.bounds])
                p, t, k = curve.evaluate(stations)
                joints = curve.joint_errors()
                radius, witness = curve.min_radius(refine=False)
                speeds = [float(np.linalg.norm(seg.derivatives(np.linspace(0,1,49))[1], axis=1).min())
                          for seg in curve.segments]
                endpoints = max(float(np.linalg.norm(p[0]-[XC,YA,ZA])),
                                float(np.linalg.norm(p[-1]-[XC,YB0+s,ZB0+q])))
                chord_points = np.vstack([seg.evaluate(np.linspace(0,1,65))[0][0 if i==0 else 1:]
                                          for i,seg in enumerate(curve.segments)])
                self_check = polyline_self_intersections(chord_points)
                row = dict(slide_mm=s, normal_mm=q, fold_y_mm=curve.fold,
                           actual_integrated_length_mm=float(curve.bounds[-1]),
                           fixed_target_length_error_mm=abs(curve.bounds[-1]-curve.target),
                           endpoint_error_mm=endpoints,
                           max_joint_position_error_mm=max(x['position_error_mm'] for x in joints),
                           max_joint_tangent_error=max(x['tangent_error'] for x in joints),
                           max_joint_curvature_error_per_mm=max(x['curvature_error_per_mm'] for x in joints),
                           minimum_sampled_radius_mm=radius, radius_witness=witness,
                           minimum_sampled_parameter_speed_mm=min(speeds),
                           fixed_material_station_count=len(stations), gross=_gross_screen(curve,p),
                           self_intersection_screen=self_check,
                           analytical_g2_only=True, self_intersection_not_proven_absent=True)
                if s in (0.,SLIDE) and q in (0.,DOCK):
                    adaptive = [seg.adaptive_length() for seg in curve.segments]
                    row['independent_adaptive_integrated_length_mm'] = sum(v[0] for v in adaptive)
                    row['gauss64_minus_adaptive_length_mm'] = curve.bounds[-1]-row['independent_adaptive_integrated_length_mm']
                    row['adaptive_sum_estimated_error_mm'] = sum(v[1] for v in adaptive)
                    row['minimum_refined_radius_mm'], row['refined_radius_witness'] = curve.min_radius()
                record['pose_rows'].append(row)
            except (GeometryRejected, ValueError, RuntimeError) as error:
                record['failure_rows'].append(dict(slide_mm=s, normal_mm=q,
                                                   exception=type(error).__name__, reason=str(error)))
        good = record['pose_rows']
        record['summary'] = dict(actual_successful_poses=len(good), actual_rejected_poses=len(record['failure_rows']),
            max_length_error_mm=max((r['fixed_target_length_error_mm'] for r in good), default=None),
            global_minimum_sampled_radius_mm=min((r['minimum_sampled_radius_mm'] for r in good), default=None),
            gross_outside_union_poses=sum(r['gross']['centerline_outside_union_count'] > 0 for r in good),
            sampled_chord_self_intersection_poses=sum(r['self_intersection_screen']['intersecting_chord_pairs'] > 0 for r in good),
            maximum_U_top_B_gross_y_overrun_mm=max((r['gross']['U_top_beyond_B_gross_y_mm'] for r in good), default=None),
            vendor_radius_qualification=False, manufacturing_go=False)
        rows.append(record)
        print(config.name, json.dumps(record['summary'], sort_keys=True), flush=True)
    report = dict(schema='RAZR_SLIDE_CONDITIONAL_G2_GEOMETRY_R6', source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  sequential_pose_count=len(poses(slide_steps,dock_steps)), candidate_count=len(rows),
                  unchanged_A_anchor_mm=[XC,YA,ZA], unchanged_B_anchor_formula='[32.7,15+s,-3.4+q]',
                  trim_model='Four quintic Bezier Hermite blends; v=2*trim*T; a=|v|^2*kappa',
                  arc_length_quadrature='64-point Gauss; endpoint poses independently adaptive-integrated',
                  finite_ribbon_OLED_rail_body_clearance_checked=False, supplier_material_or_fatigue_qualified=False,
                  manufacturing_go=False, elapsed_seconds=time.monotonic()-start, candidates=rows)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(Path(__file__).with_name('geometry_scan.json')))
    parser.add_argument('--slide-steps', type=int, default=81)
    parser.add_argument('--dock-steps', type=int, default=41)
    args = parser.parse_args()
    scan(args.output, args.slide_steps, args.dock_steps)
