"""Diagnose the original five full-operator RHS actions on exact original inputs.

This is a newly source-bound numerical diagnostic. It does not recover an old
K/H, accept a body response, run a contact QP, or qualify hardware. The original
free-DOF infinity residual bound is unchanged at 1e-7. Optional iterative
refinement changes only the solve accuracy, never the matrix, constraints, RHS,
normalization, acceptance threshold, or the recorded baseline rejection.
"""
from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "integration")]
import numpy as np
import scipy
from scipy.sparse import csc_matrix, coo_matrix, hstack, load_npz, save_npz
from scipy.sparse.linalg import LinearOperator, onenormest, splu
from contact_patch_audit import triangle_coefficients, evaluate
from tools.check_environment import inspect_environment

RESIDUAL_LIMIT = 1e-7
RESERVE_BYTES = 500 * 1024**2
EXPECTED = {
    "panel": {
        "dofs": 344103, "fixed": 6,
        "mesh.npz": "310152fc64af21451cc5ea4be683a73075109ed7e6ec588a6e8bcacf4979ac34",
        "loads.npz": "811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6",
    },
    "frame": {
        "dofs": 474726, "fixed": 777,
        "mesh.npz": "fc0eeecf966eda3bf242b0abd90f5603132f47d5235fcf81ea7238c1faf33132",
        "loads.npz": "eb2b180696785a77b71412506760df974fbf54c800090e36f027f2aaf70135a3",
    },
}
CONTACT_INPUTS = {
    "engineering/nested-contact-20261017/level-2/case-6/report.json.gz": "3e0177c8405ddeb27af68325ea65793d5eedb8a5aaf3680a3bfc5b1305fc2d06",
    "engineering/contact-field-20261015/common-cell-results.json.gz": "7d316b2aabb75ea7706f7137a970156b73b680740643465c6c3f33568a9a3493",
    "engineering/contact-field-20261015/coupled-field-audit.json.gz": "cc8655e28957a88de6c8125b7010f60707df8a9a2ea1fff6bf2d2abb806f3c0b",
}
EXPECTED_POINTS_SHA256 = "682a157686b06b4d8a1c8f431eab3453b9a43594801df148c03594435c4bf796"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def array_sha(value):
    return hashlib.sha256(np.asarray(value, dtype=np.float64).tobytes()).hexdigest()


def save_json(path, value):
    tmp = path.with_name(path.name + ".writing")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def free_bytes(path):
    status = os.statvfs(path)
    return status.f_bavail * status.f_frsize


def memory_snapshot():
    base = Path("/sys/fs/cgroup")
    result = {}
    if (base / "memory.current").exists():
        result["cgroup_current_bytes"] = int((base / "memory.current").read_text())
        result["cgroup_limit"] = (base / "memory.max").read_text().strip()
        stats = dict(line.split() for line in (base / "memory.stat").read_text().splitlines())
        result["anon_bytes"] = int(stats.get("anon", 0))
        result["file_bytes"] = int(stats.get("file", 0))
        result["slab_unreclaimable_bytes"] = int(stats.get("slab_unreclaimable", 0))
    return result


def force_maps(body, folder, output):
    """Preserve the original 3885-point order, six P2 coefficients and signs."""
    expected = EXPECTED[body]
    report_path = folder / "report.json"
    report = json.loads(report_path.read_text())
    if (report["body"] != body or report["level"] != 2 or report["E_normalization"] != 1.0
            or report["nu"] != 0.3 or report["original_faces_and_surface_P2_traces_unchanged"] is not True
            or report["body_loads_on_added_internal_DOFs"] is not False):
        raise ValueError("volume reconstruction does not preserve the original model")
    identities = {str(report_path): sha(report_path)}
    for name, key in (("K.npz", "K_sha256"), ("mesh.npz", "mesh_sha256"), ("loads.npz", "loads_sha256")):
        path = folder / name
        digest = sha(path)
        if digest != report[key] or name != "K.npz" and digest != expected[name]:
            raise ValueError("volume input identity mismatch: " + name)
        identities[str(path)] = digest
    for relative, expected_hash in CONTACT_INPUTS.items():
        path = ROOT / relative
        digest = sha(path)
        if digest != expected_hash:
            raise ValueError("original contact input changed: " + relative)
        identities[str(path)] = digest
    seed, common, meta = [ROOT / name for name in CONTACT_INPUTS]
    initial = json.loads(gzip.decompress(seed.read_bytes()))
    points = initial["contact_points"]
    if initial["case"] != 6 or initial["volume_level"] != 2 or len(points) != 3885:
        raise ValueError("original point set not present")
    if points[:4] != [{"kind": "bolt", "index": i} for i in range(4)]:
        raise ValueError("original point order changed")
    save_json(output / "points.json", points)
    if sha(output / "points.json") != EXPECTED_POINTS_SHA256:
        raise ValueError("original point byte identity changed")
    with np.load(folder / "loads.npz", allow_pickle=False) as loads:
        fixed, xyz, bolts = loads["D"], loads["xyz"], loads["C"]
    n = xyz.shape[1]
    if n != expected["dofs"] or len(fixed) != expected["fixed"]:
        raise ValueError("original DOFs or fixed-coordinate set changed")
    raw = json.loads(gzip.decompress(common.read_bytes()))
    patches = json.loads(gzip.decompress(meta.read_bytes()))["contact_patches"]
    by_name = {row["patch"]: row for row in patches}
    cells = [(by_name[group["patch"]], cell) for group in raw for cell in group["cells"]]
    if len(cells) != 5255:
        raise ValueError("original contact cell coverage changed")
    prepared = []
    for descriptor, cell in cells:
        tangent = [i for i in range(3) if i != descriptor["normal_axis"]]
        origin = np.asarray(descriptor["origin_tangent_mm"])
        dofs = np.asarray(cell[body + "_P2_dofs"], dtype=int)
        coefficients = triangle_coefficients(xyz[tangent][:, dofs[:3]].T, np.eye(6), origin)
        prepared.append((descriptor, dofs, coefficients, origin))
    columns = []
    for point in points:
        if point["kind"] == "bolt":
            columns.append(csc_matrix(bolts[:, point["index"], None]))
            continue
        descriptor, dofs, coefficients, origin = prepared[point["cell"]]
        if point["patch"] != descriptor["patch"] or point["gap"] != descriptor["initial_gap_mm"]:
            raise ValueError("point descriptor changed")
        sign = descriptor["normal_sign"] * (1 if body == "panel" else -1)
        weights = sign * evaluate(coefficients, np.asarray(point["xy"])[None], origin)[0]
        if not np.isfinite(weights).all() or abs(weights.sum() - sign) >= 2e-9:
            raise ValueError("original force partition failed")
        columns.append(coo_matrix((weights, (dofs, np.zeros(len(dofs), dtype=int))), shape=(n, 1)).tocsc())
    C = hstack(columns, format="csc")
    C.sum_duplicates()
    C.eliminate_zeros()
    C.sort_indices()
    save_npz(output / "C.npz", C)
    return C, fixed, identities


def residual_record(K, solution, rhs, free):
    if not np.isfinite(solution).all() or not np.isfinite(rhs).all():
        raise ValueError('nonfinite solution or original RHS')
    error = K @ solution - rhs
    if not np.isfinite(error).all():
        raise ValueError('nonfinite original float64 residual')
    numerator = float(np.max(np.abs(error)))
    denominator = max(float(np.max(np.abs(rhs))), 1.0)
    ratio = numerator / denominator
    at = int(np.argmax(np.abs(error)))
    result = {
        "free_dof_residual_infinity_ratio": ratio,
        "residual_numerator": numerator,
        "normalization_denominator": denominator,
        "threshold": RESIDUAL_LIMIT,
        "passes_original_threshold": bool(np.isfinite(ratio) and ratio <= RESIDUAL_LIMIT),
        "max_residual_original_dof": int(free[at]),
        "signed_residual_at_max_dof": float(error[at]),
        "rhs_at_max_dof": float(rhs[at]),
        "solution_infinity_norm": float(np.max(np.abs(solution))),
        "rhs_free_sha256": array_sha(rhs),
        "solution_free_sha256": array_sha(solution),
        "residual_sha256": array_sha(error),
    }
    return result, error


def main(args):
    started = time.monotonic()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("large diagnostic outputs must be outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    state = {
        "schema": "razr-original-five-probe-diagnostic-v1",
        "body": args.body,
        "diagnostic_completed": False,
        "historical_K_or_H_recovered": False,
        "H_action_restore_executed": False,
        "complete_body_response_accepted": False,
        "new_QP_executed": False,
        "candidate_go": False,
        "fixture_fabrication_go": False,
        "manufacturing_go": False,
        "original_probe_seed": 73021,
        "original_probe_count": 5,
        "original_residual_threshold": RESIDUAL_LIMIT,
        "original_residual_denominator": "max(max(abs(rhs[original_free_DOFs])), 1.0)",
        "baseline_probes": [],
        "refined_probes": [],
    }

    def progress(phase, **values):
        state.update(phase=phase, seconds=time.monotonic() - started,
                     peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                     disk_free_bytes=free_bytes(output), memory=memory_snapshot(), **values)
        save_json(output / "progress.json", state)
        print(json.dumps({"phase": phase, "seconds": state["seconds"],
                          "peak_rss_kib": state["peak_rss_kib"], **values}, allow_nan=False), flush=True)

    try:
        environment = inspect_environment(ROOT)
        state["environment"] = environment
        if not environment["passed"]:
            raise ValueError("locked environment mismatch: " + "; ".join(environment["errors"]))
        field_bytes = EXPECTED[args.body]['dofs'] * 5 * 8 * (2 if args.refinement_steps else 1)
        diagnostic_bytes = field_bytes + 8 * 1024**2
        state['output_data_budget_bytes'] = diagnostic_bytes
        if free_bytes(output) < RESERVE_BYTES + diagnostic_bytes:
            raise RuntimeError("insufficient space for diagnostic fields and 500MiB reserve")
        limit = int(args.memory_gib * 1024**3)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        state["address_space_limit_bytes"] = limit
        state["source_base_commit"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        sources = (Path(__file__), ROOT / "integration/contact_patch_audit.py",
                   ROOT / "integration/contact_exchange.py", ROOT / "tools/check_environment.py",
                   ROOT / "pyproject.toml", ROOT / "uv.lock")
        state["source_sha256"] = {str(path): sha(path) for path in sources}
        folder = args.volume.resolve() / args.body / "level-2"
        C, fixed, inputs = force_maps(args.body, folder, output)
        state["input_sha256"] = inputs
        state["C_sha256"] = sha(output / "C.npz")
        state["points_sha256"] = sha(output / "points.json")
        n, m = C.shape
        free = np.setdiff1d(np.arange(n), fixed)
        K = load_npz(folder / "K.npz").tocsc()
        if K.shape != (n, n):
            raise ValueError("complete K shape changed")
        Kff = K[free][:, free].tocsc()
        del K
        gc.collect()
        progress("original_full_operator_ready", original_vector_dofs=n, fixed_dofs=len(fixed),
                 free_dofs=len(free), Kff_nnz=int(Kff.nnz), response_columns=m)
        start_factor = time.monotonic()
        scales = np.ones(len(free))
        factor_operator = Kff
        if args.symmetric_scaling:
            diagonal = Kff.diagonal()
            if not np.isfinite(diagonal).all() or np.any(diagonal <= 0):
                raise ValueError('positive finite original diagonal required for symmetric scaling')
            scales = 1.0 / np.sqrt(diagonal)
            factor_operator = Kff.copy()
            for first in range(0, len(free), 512):
                end = min(first+512, len(free))
                lo, hi = factor_operator.indptr[first], factor_operator.indptr[end]
                factor_operator.data[lo:hi] *= scales[factor_operator.indices[lo:hi]]
                factor_operator.data[lo:hi] *= np.repeat(scales[first:end], np.diff(factor_operator.indptr[first:end+1]))
        factor = splu(factor_operator, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0,
                      options={"SymmetricMode": True})
        if args.symmetric_scaling:
            del factor_operator
            gc.collect()
        def solve_original(rhs, trans='N'):
            scale = scales if rhs.ndim == 1 else scales[:, None]
            return scale * factor.solve(scale * rhs, trans=trans)
        state["factorization"] = {
            "ordering": "MMD_AT_PLUS_A", "diag_pivot_thresh": 0.0, "SymmetricMode": True,
            "seconds": time.monotonic() - start_factor, "nnz": int(factor.nnz),
            "symmetric_diagonal_scaling": bool(args.symmetric_scaling),
            "scaling_min": float(scales.min()), "scaling_max": float(scales.max()),
            "scaling_sha256": array_sha(scales),
            "physical_solve_formula": 'u = S solve(S Kff S, S rhs)',
            "original_matrix_rhs_constraints_and_residual_metric_unchanged": True}
        progress("original_factorization_completed", factorization=state["factorization"])
        generator = np.random.default_rng(73021)
        directions = [np.ones(m)] + [generator.choice([-1.0, 1.0], m) for _ in range(4)]
        right_sides, fields = [], []
        for index, direction in enumerate(directions):
            rhs = np.asarray(C @ direction).ravel()
            solution = solve_original(np.asarray(rhs[free]))
            record, error = residual_record(Kff, solution, rhs[free], free)
            record.update(probe_index=index, direction_sha256=array_sha(direction), rhs_full_sha256=array_sha(rhs))
            state["baseline_probes"].append(record)
            right_sides.append(rhs)
            field = np.zeros(n)
            field[free] = solution
            fields.append(field)
            progress("baseline_probe_recorded", probe_index=index,
                     residual_ratio=record["free_dof_residual_infinity_ratio"],
                     passes_original_threshold=record["passes_original_threshold"])
        np.save(output / "baseline-five-probe-fields.npy", np.stack(fields, axis=1))
        state["baseline_all_five_passed"] = all(row["passes_original_threshold"] for row in state["baseline_probes"])
        if args.refinement_steps:
            # Extended-precision residual is used only to choose corrections.
            # Acceptance is still the exact original float64 Kff@u-rhs metric.
            refinement_dtype = np.longdouble if args.refinement_precision == 'longdouble' else np.float64
            extended = Kff.astype(refinement_dtype, copy=False)
            refined_fields = []
            for index, (rhs, original) in enumerate(zip(right_sides, fields)):
                solution = original[free].copy()
                record, error = residual_record(Kff, solution, rhs[free], free)
                iterations = [dict(iteration=0, **record)]
                for step in range(1, args.refinement_steps + 1):
                    if record["passes_original_threshold"]:
                        break
                    long_error = (extended @ solution.astype(refinement_dtype)
                                  - rhs[free].astype(refinement_dtype))
                    correction = solve_original(-np.asarray(long_error, dtype=np.float64))
                    if not np.isfinite(correction).all():
                        raise ValueError("nonfinite iterative refinement correction")
                    solution += correction
                    record, error = residual_record(Kff, solution, rhs[free], free)
                    iterations.append(dict(iteration=step, correction_infinity_norm=float(np.max(abs(correction))), **record))
                field = np.zeros(n)
                field[free] = solution
                refined_fields.append(field)
                state["refined_probes"].append({"probe_index": index, "iterations": iterations,
                                                "passes_original_threshold": record["passes_original_threshold"],
                                                "rhs_full_sha256": array_sha(rhs)})
                progress("refined_probe_recorded", probe_index=index,
                         refinement_iterations=len(iterations)-1,
                         residual_ratio=record["free_dof_residual_infinity_ratio"],
                         passes_original_threshold=record["passes_original_threshold"])
            np.save(output / "refined-five-probe-fields.npy", np.stack(refined_fields, axis=1))
            state["refined_all_five_passed"] = all(row["passes_original_threshold"] for row in state["refined_probes"])
            state["refinement_contract"] = {
                "maximum_steps": args.refinement_steps,
                "correction_residual_precision": str(np.dtype(refinement_dtype)),
                "unchanged_acceptance_precision": "float64",
                "matrix_rhs_fixed_dofs_and_acceptance_threshold_unchanged": True,
            }
            del extended
        if args.condition_estimate:
            calls = [0]
            def inverse_action(value):
                calls[0] += 1
                return solve_original(value)
            def inverse_transpose_action(value):
                calls[0] += 1
                return solve_original(value, trans='T')
            absolute = abs(Kff)
            norm_one = float(np.max(np.asarray(absolute.sum(axis=0))))
            norm_infinity = float(np.max(np.asarray(absolute.sum(axis=1))))
            del absolute
            inverse = LinearOperator(Kff.shape, matvec=inverse_action, rmatvec=inverse_transpose_action,
                                     matmat=inverse_action, rmatmat=inverse_transpose_action, dtype=np.float64)
            inverse_norm_estimate = float(onenormest(inverse, t=2, itmax=5))
            u0 = fields[0][free]
            rayleigh = float(u0 @ (Kff @ u0) / (u0 @ u0))
            with np.load(folder/'loads.npz', allow_pickle=False) as loads:
                rigid = loads['R'][free]
            coefficients = np.linalg.solve(rigid.T @ rigid, rigid.T @ u0)
            nonrigid = u0-rigid @ coefficients
            state['condition_diagnostics'] = {
                'original_Kff_one_norm': norm_one, 'original_Kff_infinity_norm': norm_infinity,
                'inverse_one_norm_estimate': inverse_norm_estimate,
                'estimated_one_norm_condition_number': norm_one*inverse_norm_estimate,
                'estimator': 'scipy.sparse.linalg.onenormest, t=2, itmax=5; estimate, not certified eigenanalysis',
                'inverse_estimator_solve_calls': calls[0],
                'probe0_rayleigh_quotient': rayleigh,
                'probe0_nonrigid_to_full_l2_ratio': float(np.linalg.norm(nonrigid)/np.linalg.norm(u0)),
                'probe0_rigid_least_squares_coefficients': coefficients.tolist(),
                'normalized_material_E': 1.0,
                'probe_is_synthetic_operator_action_not_a_physical_loading_qualification': True,
            }
            del rigid, nonrigid
            extended_check = Kff.astype(np.longdouble)
            comparison = []
            candidates = [('baseline', fields[0])]
            if args.refinement_steps:
                candidates.append(('after_bounded_refinement', refined_fields[0]))
            for label, full_field in candidates:
                original_metric, _ = residual_record(Kff, full_field[free], right_sides[0][free], free)
                extended_residual = extended_check @ full_field[free].astype(np.longdouble)-right_sides[0][free].astype(np.longdouble)
                extended_ratio = float(np.max(abs(extended_residual)))/original_metric['normalization_denominator']
                comparison.append({'iterate': label,
                    'original_float64_ratio': original_metric['free_dof_residual_infinity_ratio'],
                    'extended_residual_ratio': extended_ratio,
                    'extended_residual_is_diagnostic_only': True,
                    'original_threshold_still_controls_acceptance': True})
            state['precision_comparison'] = comparison
            del extended_check
        for path, digest in {**inputs, **state["source_sha256"]}.items():
            if sha(path) != digest:
                raise ValueError("source or input changed during computation: " + path)
        if free_bytes(output) < RESERVE_BYTES:
            raise RuntimeError("500MiB disk reserve not retained")
        state["diagnostic_completed"] = True
        state["files_sha256"] = {p.name: sha(p) for p in output.iterdir() if p.is_file() and p.name not in ("progress.json", "report.json")}
        state["runtime"] = {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__}
        state["five_probe_residuals_passed_after_optional_refinement"] = state.get("refined_all_five_passed", state["baseline_all_five_passed"])
        progress("diagnostic_completed")
        save_json(output / "report.json", state)
        return 0 if state["five_probe_residuals_passed_after_optional_refinement"] else 2
    except BaseException as exc:
        progress("diagnostic_failed", error_type=type(exc).__name__, error=str(exc))
        save_json(output / "report.json", state)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", choices=("panel", "frame"), required=True)
    parser.add_argument("--volume", type=Path, required=True,
                        help="Parent of body/level-2 with source-bound complete reconstructed K")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-gib", type=float, choices=(4.25, 4.5, 5.0), default=4.25)
    parser.add_argument("--refinement-steps", type=int, choices=range(0, 9), default=0)
    parser.add_argument('--refinement-precision', choices=('float64', 'longdouble'), default='longdouble')
    parser.add_argument('--symmetric-scaling', action='store_true')
    parser.add_argument('--condition-estimate', action='store_true')
    raise SystemExit(main(parser.parse_args()))

