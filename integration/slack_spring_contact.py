"""Optional tensile-only spring/contact law on the existing force-QP backend.

This named entry retains PR25's useful slack-spring semantics without replacing
the main spatial_contact API or copying another optimizer.  Every spring and
contact force is nonnegative.  A released spring has zero force and nonnegative
constitutive slack.  The supplied H is complementary compliance, not stiffness.

The backend requires positive diagonal response after spring compliance is
added.  Zero-response contact columns are rejected, not discarded or anchored.
No old PR25 full-body result, physical preload, or continuum pressure is implied.
"""
from __future__ import annotations

import numpy as np

from contact_dual_active import solve_force_qp


def _array(value, shape, name):
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "fiu" or not np.isfinite(raw).all():
        raise ValueError(f"{name}: finite real array of shape {shape} required")
    return raw.astype(float, copy=True)


def solve_tension_contact(compliance, rigid_map, free_displacement,
                          rigid_resultant, spring_compliance,
                          spring_initial_force, contact_gaps, *,
                          initial=None, tolerance=2e-10, max_iterations=5000):
    """Solve unilateral springs followed by ordinary normal contact reactions.

    q = q_free - H @ force + G @ rigid_coordinates.
    A spring obeys force >= 0, c*(force-initial_force)-q >= 0, with
    complementary force/slack.  Contacts obey force >= 0, gap-q >= 0.
    The initial force is a constitutive parameter, not measured installation.
    Original rigid equilibrium and complete KKT checks remain in the backend.
    """
    h = np.asarray(compliance)
    if h.ndim != 2 or h.shape[0] != h.shape[1] or not len(h):
        raise ValueError("nonempty square complementary compliance required")
    count = len(h)
    h = _array(h, (count, count), "compliance")
    hscale = max(float(np.max(abs(h))), 1e-300)
    if np.max(abs(h-h.T)) > 1e-9*hscale:
        raise ValueError("nonreciprocal complementary compliance")
    h = (h+h.T)/2
    if np.linalg.eigvalsh(h).min() < -1e-9*hscale:
        raise ValueError("negative complementary compliance energy")
    g = np.asarray(rigid_map)
    if g.ndim != 2 or g.shape[0] != count:
        raise ValueError("one rigid-map row per generalized force required")
    g = _array(g, g.shape, "rigid_map")
    q0 = _array(free_displacement, (count,), "free_displacement")
    load = _array(rigid_resultant, (g.shape[1],), "rigid_resultant")
    c = np.asarray(spring_compliance)
    if c.ndim != 1 or len(c) > count:
        raise ValueError("one compliance per leading spring required")
    springs = len(c)
    c = _array(c, (springs,), "spring_compliance")
    pre = _array(spring_initial_force, (springs,), "spring_initial_force")
    gaps = _array(contact_gaps, (count-springs,), "contact_gaps")
    if np.any(c <= 0) or np.any(pre < 0) or np.any(gaps < 0):
        raise ValueError("positive spring compliance and nonnegative initial force/gaps required")
    s = h.copy()
    s[np.arange(springs), np.arange(springs)] += c
    d = q0.copy()
    d[:springs] += c*pre
    d[springs:] -= gaps
    result = solve_force_qp(s, d, g, load, free_prefix=0, initial=initial,
                            tolerance=tolerance, max_iterations=max_iterations,
                            factor_reuse=True, rank_fallback="qr_pivot")
    result.update({"connector_law": "tensile_only_springs_then_normal_contacts",
                   "spring_count": springs,
                   "backend": "contact_dual_active.solve_force_qp/free_prefix=0",
                   "between_point_gap_audit_required": True,
                   "pr25_full_body_driver_or_results_adopted": False,
                   "physical_installation_or_capacity_qualified": False,
                   "candidate_go": False, "fixture_fabrication_go": False,
                   "manufacturing_go": False})
    if not result["passed"]:
        return result
    force = np.asarray(result["forces"])
    rigid = np.asarray(result["rigid_mode_coordinates"])
    q = q0-h@force+g@rigid
    scale = max(float(np.max(abs(force))), 1e-15)
    result.update({"spring_forces": force[:springs].tolist(),
                   "contact_forces": force[springs:].tolist(),
                   "spring_constitutive_slacks": (c*(force[:springs]-pre)-q[:springs]).tolist(),
                   "remaining_contact_gaps": (gaps-q[springs:]).tolist(),
                   "relative_displacements": q.tolist(),
                   "slack_springs": np.flatnonzero(force[:springs] <= 1e-12*scale).tolist()})
    return result
