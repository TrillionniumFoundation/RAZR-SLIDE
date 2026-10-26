"""N4: bounded LU-preconditioned GMRES iterative refinement of the original five panel actions.

The original float64 residual_record, force_maps and array_sha functions remain
byte-for-byte unchanged. Longdouble products choose corrections only; acceptance
is always the original float64 Kff @ u - b infinity ratio <= 1e-7. No K, b, C,
constraint, model, point ordering or source qualification claim is changed.
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

_root_parser = argparse.ArgumentParser(add_help=False)
_root_parser.add_argument("--root", type=Path, required=True)
ROOT = _root_parser.parse_known_args()[0].root.resolve(strict=True)
sys.path[:0] = [str(ROOT), str(ROOT / "integration")]
import numpy as np
import scipy
from scipy.sparse import csc_matrix, coo_matrix, hstack, load_npz, save_npz
from scipy.sparse.linalg import LinearOperator, gmres, splu
from contact_patch_audit import triangle_coefficients, evaluate
from tools.check_environment import inspect_environment

SOURCE_S4 = "dd7def6e6a4de9f47dc91ca2ab336fb1a8828560"
SOURCE_ORIGINAL_HELPER_SHA256 = '1f8334a1dda34a4101662ccdbd14c2db0bb77b8a3e080b5f5ec74d918955a2c6'
EXPECTED_PANEL_K_SHA256 = "80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb"
EXPECTED_PANEL_C_SHA256 = "9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f"
EXPECTED_RHS_SHA256 = ['abae22600aa78c69bd1ac06e08df22e8a2740f4d5752d04e9f0922d71eeef2e7', 'e47ab9c4cc6707f8f549aeb8c27c099c02d03a5e0e2101de8ea97218d3b7848f', 'cc9ff568a50adf56034282b90e95b37dac1ba64219efaed23e7ca9bcab72e4f8', 'de6fa75d5fd4d63ecc5588e27eb097a31411720e71454b4c5bfe62457080513f', 'ada335a73f4a47813c3d14192adacd242e833155f224f1346bed0a586f1d2adc']
EXPECTED_DIRECTION_SHA256 = ['4d9dc6cf2bf3be139d0858e5a2ccdd996c5f76eac2fa0ee16f3166223ba2e8cb', 'ed71e39c886f4ff054a8f4a010756a3784ee4f727da5fe23d856b134fdbf92b7', 'f1aad589d38d6667299b5f7eaf934fdad37aebe7612cf03783bb72355280cd8a', '8fb443e916b10eaf2087860b05409a6030f13df620f5a8afd3417a66e405d8cb', '5b2fa88303ef4c095bc1cfa7b6e3ffa4db205527a6bac3b2e5a955c3ec81aaf3']

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


def save_array(path, value):
    """Atomically publish each actual array; never expose a half-written .npy."""
    tmp = path.with_name(path.name + ".writing")
    with tmp.open("wb") as stream:
        np.save(stream, value, allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    return sha(path)


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


def worker_process_memory_snapshot():
    """Read-only phase telemetry; absent counters remain unknown, never zero."""
    result = {"status_path": "/proc/self/status", "observational_only": True,
              "readable": False, "all_required_fields_present": False}
    required = ("VmSize", "VmPeak", "VmRSS", "VmHWM")
    try:
        raw = Path(result["status_path"]).read_bytes()
        result["readable"] = True
        result["raw_status_sha256"] = hashlib.sha256(raw).hexdigest()
        rows = {line.split(":", 1)[0]: line for line in raw.decode().splitlines() if ":" in line}
        result["captured_status_lines"] = [rows[name] for name in required if name in rows]
        result["missing_fields"] = [name for name in required if name not in rows]
        result["values_bytes"] = {}
        for name in required:
            if name not in rows:
                continue
            fields = rows[name].split()
            if len(fields) != 3 or fields[2] != "kB" or int(fields[1]) < 0:
                raise ValueError("unexpected /proc/self/status memory counter format: " + name)
            result["values_bytes"][name] = int(fields[1]) * 1024
        result["all_required_fields_present"] = not result["missing_fields"]
    except (OSError, ValueError) as exc:
        result["capture_error"] = type(exc).__name__ + ": " + str(exc)
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


def matrix_identity(K):
    return {"shape": list(K.shape), "format": K.format,
            **{name: {"dtype": str(getattr(K, name).dtype),
                       "sha256": hashlib.sha256(getattr(K, name).tobytes()).hexdigest()}
               for name in ("data", "indices", "indptr")}}



N4_MAX_OUTER = 8
N4_GMRES_RESTART = 20
N4_GMRES_MAX_CYCLES = 2
N4_GMRES_RTOL = 1e-4
N4_AS_GIB = 4.5


def refine_one(Kff, extended, factor, rhs, original_solution, free, persist, observe_inner):
    """One predeclared GMRES-IR rule; does not change the acceptance operator.

    persist(label, solution, details) retains a full field and original residual.
    All returned GMRES corrections and outer solution fields are retained; every
    inner preconditioned residual and actual inner iteration count is recorded.
    GMRES info is recorded separately from the original five-probe acceptance.
    """
    solution = np.asarray(original_solution, dtype=np.float64).copy()
    history = []
    original, error = residual_record(Kff, solution, rhs, free)
    if original['passes_original_threshold']:
        return solution, history, original
    calls = {'extended_product': 0, 'preconditioner': 0}
    def accurate_product(v):
        calls['extended_product'] += 1
        return np.asarray(extended @ np.asarray(v, dtype=np.longdouble), dtype=np.float64)
    def precondition(v):
        calls['preconditioner'] += 1
        return factor.solve(np.asarray(v, dtype=np.float64))
    operator = LinearOperator(Kff.shape, matvec=accurate_product, dtype=np.float64)
    preconditioner = LinearOperator(Kff.shape, matvec=precondition, dtype=np.float64)
    for iteration in range(1, N4_MAX_OUTER + 1):
        residual_long = extended @ solution.astype(np.longdouble) - rhs.astype(np.longdouble)
        correction_rhs = -np.asarray(residual_long, dtype=np.float64)
        callbacks = []
        def on_inner(preconditioned_norm):
            row = {'outer_iteration': iteration, 'inner_iteration': len(callbacks)+1,
                'preconditioned_residual_norm': float(preconditioned_norm),
                'cumulative_operator_calls': dict(calls),
                'not_original_acceptance': True}
            callbacks.append(row)
            observe_inner(iteration, callbacks)
        inner_started = time.monotonic()
        correction, info = gmres(operator, correction_rhs, M=preconditioner,
            restart=N4_GMRES_RESTART, maxiter=N4_GMRES_MAX_CYCLES,
            rtol=N4_GMRES_RTOL, atol=0.0, callback=on_inner, callback_type='pr_norm')
        if not np.isfinite(correction).all():
            raise ValueError('nonfinite GMRES correction')
        correction_record = persist(f'outer-{iteration:02d}-gmres-return', correction, {
            'kind': 'correction', 'outer_iteration': iteration, 'gmres_info': int(info),
            'correction_equation_rhs_sha256': array_sha(correction_rhs),
            'gmres_seconds': time.monotonic()-inner_started, 'actual_inner_iterations': len(callbacks),
            'not_an_accepted_displacement_field': True,
        }, correction_rhs)
        solution += correction
        row = persist(f'outer-{iteration:02d}-field', solution, {
            'kind': 'solution', 'outer_iteration': iteration, 'gmres_info': int(info),
            'correction_infinity_norm': float(np.max(np.abs(correction))),
            'correction_rhs_sha256': array_sha(correction_rhs),
            'correction_rhs_infinity_norm': float(np.max(np.abs(correction_rhs))),
            'gmres_callbacks': callbacks, 'gmres_return': correction_record,
            'actual_inner_iterations': len(callbacks), 'gmres_seconds': time.monotonic()-inner_started,
            'cumulative_operator_calls': dict(calls),
            'longdouble_residual_before_infinity_ratio':
                float(np.max(np.abs(residual_long))) / max(float(np.max(np.abs(rhs))), 1.0),
        }, rhs)
        history.append(row)
        original, error = residual_record(Kff, solution, rhs, free)
        if original['passes_original_threshold']:
            break
    return solution, history, original


def main(args):
    if sys.flags.optimize:
        raise RuntimeError('optimized Python is not authorized')
    started = time.monotonic()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('outputs must be outside immutable S4 checkout')
    output.mkdir(parents=True, exist_ok=False)
    state = {
        'schema': 'razr-panel-N4-bounded-GMRES-IR-v1',
        'source_candidate': SOURCE_S4, 'source_baseline_helper_sha256': SOURCE_ORIGINAL_HELPER_SHA256,
        'new_solver_research_identity': True, 'new_resource_budget_identity': True,
        'diagnostic_completed': False, 'historical_K_or_H_recovered': False,
        'H_action_restore_executed': False, 'complete_body_response_accepted': False,
        'new_QP_executed': False, 'candidate_go': False, 'fixture_fabrication_go': False,
        'manufacturing_go': False, 'original_probe_seed': 73021, 'original_probe_count': 5,
        'original_residual_threshold': RESIDUAL_LIMIT,
        'original_residual_denominator': 'max(max(abs(rhs[original_free_DOFs])), 1.0)',
        'original_gate_matvec_precision': 'float64',
        'all_five_rhs_prepared': False, 'baseline_probes': [], 'refined_probes': [],
        'probe_execution': [{'probe_index': i, 'status': 'not_started'} for i in range(5)],
        'solver_strategy': {
            'permc_spec': 'MMD_AT_PLUS_A', 'diag_pivot_thresh': 0.0, 'SymmetricMode': True,
            'symmetric_scaling': False, 'refinement': 'bounded LU-preconditioned GMRES-IR',
            'outer_maximum': N4_MAX_OUTER, 'restart': N4_GMRES_RESTART,
            'maximum_restart_cycles': N4_GMRES_MAX_CYCLES, 'inner_rtol': N4_GMRES_RTOL,
            'inner_atol': 0.0, 'callback_type': 'pr_norm',
            'correction_residual_and_matvec_precision': 'longdouble cast to float64',
            'Kff_and_original_acceptance_unchanged': True,
            'GMRES_convergence_is_not_original_gate_acceptance': True,
            'accepted_early_only_when_original_float64_gate_passes': True,
        },
    }
    def progress(phase, **values):
        state.update(phase=phase, seconds=time.monotonic()-started,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            disk_free_bytes=free_bytes(output), memory=memory_snapshot(), **values)
        observation = worker_process_memory_snapshot()
        state.setdefault('phase_memory', []).append({'phase': phase, 'seconds': state['seconds'], **observation})
        save_json(output/'progress.json', state)
        print(json.dumps({'phase': phase, 'seconds': state['seconds'],
            'peak_rss_kib': state['peak_rss_kib'], **values}, allow_nan=False), flush=True)
    try:
        state['environment'] = inspect_environment(ROOT)
        if not state['environment']['passed']:
            raise ValueError('locked environment mismatch')
        state['source_base_commit'] = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip()
        if state['source_base_commit'] != SOURCE_S4:
            raise ValueError('exact S4 checkout required')
        if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=all'], text=True).strip():
            raise ValueError('clean immutable S4 checkout required')
        baseline = ROOT/'engineering/engineering-integration-20261025/numerics/probe_original_actions.py'
        if sha(baseline) != SOURCE_ORIGINAL_HELPER_SHA256:
            raise ValueError('original helper differs')
        state['source_sha256'] = {str(p): sha(p) for p in (
            Path(__file__), baseline, ROOT/'integration/contact_patch_audit.py',
            ROOT/'integration/contact_exchange.py', ROOT/'tools/check_environment.py',
            ROOT/'pyproject.toml', ROOT/'uv.lock')}
        state['output_data_budget_bytes'] = 1536 * 1024**2
        if free_bytes(output) < RESERVE_BYTES + state['output_data_budget_bytes']:
            raise RuntimeError('insufficient capacity for all five bounded histories and 500MiB reserve')
        limit = int(N4_AS_GIB * 1024**3)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        state['address_space_limit_bytes'] = limit
        folder = args.volume.resolve()/'panel'/'level-2'
        if sha(folder/'K.npz') != EXPECTED_PANEL_K_SHA256:
            raise ValueError('original K bytes differ')
        C, fixed, inputs = force_maps('panel', folder, output)
        state['input_sha256'] = inputs
        state['C_sha256'] = sha(output/'C.npz')
        if state['C_sha256'] != EXPECTED_PANEL_C_SHA256:
            raise ValueError('original C bytes differ')
        n, m = C.shape
        free = np.setdiff1d(np.arange(n), fixed)
        save_array(output/'fixed-original-DOFs.npy', fixed)
        save_array(output/'free-original-DOFs.npy', free)
        generator = np.random.default_rng(73021)
        directions = [np.ones(m)] + [generator.choice([-1.0, 1.0], m) for _ in range(4)]
        right_sides = [np.asarray(C @ direction).ravel() for direction in directions]
        for i, (direction, rhs) in enumerate(zip(directions, right_sides)):
            if array_sha(direction) != EXPECTED_DIRECTION_SHA256[i] or array_sha(rhs) != EXPECTED_RHS_SHA256[i]:
                raise ValueError('original direction or RHS bytes differ')
        state['prepared_input_arrays_sha256'] = {
            'five-probe-rhs.npy': save_array(output/'five-probe-rhs.npy', np.stack(right_sides, axis=1)),
            'five-probe-directions.npy': save_array(output/'five-probe-directions.npy', np.stack(directions, axis=1)),
        }
        state['all_five_rhs_prepared'] = True
        progress('all_five_original_rhs_saved_before_factorization')
        K = load_npz(folder/'K.npz').tocsc()
        if K.shape != (n,n):
            raise ValueError('original K shape differs')
        Kff = K[free][:,free].tocsc()
        del K; gc.collect()
        state['original_Kff_identity_before'] = matrix_identity(Kff)
        state['original_Kff_shape'] = list(Kff.shape)
        state['original_Kff_nnz'] = int(Kff.nnz)
        progress('original_full_operator_ready')
        factor_start = time.monotonic()
        factor = splu(Kff, permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0.0, options={'SymmetricMode': True})
        state['factorization'] = {'seconds': time.monotonic()-factor_start,
            'nnz': int(factor.nnz), 'ordering': 'MMD_AT_PLUS_A',
            'diag_pivot_thresh': 0.0, 'SymmetricMode': True,
            'permutation_r_sha256': save_array(output/'factor-perm-r.npy', factor.perm_r),
            'permutation_c_sha256': save_array(output/'factor-perm-c.npy', factor.perm_c)}
        if matrix_identity(Kff) != state['original_Kff_identity_before']:
            raise ValueError('factorization changed original Kff')
        progress('original_factorization_completed', factorization=state['factorization'])
        fields = []
        for index, rhs in enumerate(right_sides):
            state['probe_execution'][index]['status'] = 'baseline_solving'
            solution = factor.solve(rhs[free])
            full = np.zeros(n); full[free] = solution
            field_hash = save_array(output/f'probe-{index}-baseline-field.npy', full)
            record, error = residual_record(Kff, solution, rhs[free], free)
            record.update(probe_index=index, direction_sha256=array_sha(directions[index]),
                rhs_full_sha256=array_sha(rhs), full_field_file_sha256=field_hash,
                residual_file_sha256=save_array(output/f'probe-{index}-baseline-residual.npy', error))
            state['baseline_probes'].append(record)
            state['probe_execution'][index]['status'] = 'baseline_saved'
            fields.append(full)
            progress('baseline_probe_recorded', probe_index=index,
                residual_ratio=record['free_dof_residual_infinity_ratio'],
                passes_original_threshold=record['passes_original_threshold'])
        save_array(output/'baseline-five-probe-fields.npy', np.stack(fields, axis=1))
        state['baseline_all_five_passed'] = all(r['passes_original_threshold'] for r in state['baseline_probes'])
        extended = Kff.astype(np.longdouble)
        state['longdouble_finfo'] = {'bits': np.finfo(np.longdouble).bits,
            'nmant': np.finfo(np.longdouble).nmant, 'epsilon': float(np.finfo(np.longdouble).eps),
            'diagnostic_and_correction_only': True}
        if np.finfo(np.longdouble).eps >= np.finfo(np.float64).eps:
            raise ValueError('N4 correction strategy requires wider longdouble accumulation')
        refined_fields = []
        for index, (rhs, field) in enumerate(zip(right_sides, fields)):
            folder_probe = output/f'probe-{index}-history'; folder_probe.mkdir()
            state['probe_execution'][index]['status'] = 'refinement_running'
            def persist(label, value, details, equation_rhs):
                full = np.zeros(n); full[free] = value
                entry = dict(details)
                entry['field_file'] = str((folder_probe/(label+'.npy')).relative_to(output))
                entry['field_file_sha256'] = save_array(output/entry['field_file'], full)
                # The equation residual of correction vectors is retained separately;
                # only solution entries can qualify the original RHS.
                record, error = residual_record(Kff, value, equation_rhs, free)
                entry['equation_residual'] = record
                entry['equation_rhs_file'] = str((folder_probe/(label+'-rhs.npy')).relative_to(output))
                entry['equation_rhs_file_sha256'] = save_array(output/entry['equation_rhs_file'], equation_rhs)
                entry['residual_file'] = str((folder_probe/(label+'-residual.npy')).relative_to(output))
                entry['residual_file_sha256'] = save_array(output/entry['residual_file'], error)
                ex = extended @ np.asarray(value, dtype=np.longdouble) - np.asarray(equation_rhs, dtype=np.longdouble)
                entry['longdouble_equation_residual_ratio_diagnostic_only'] = float(np.max(np.abs(ex)))/record['normalization_denominator']
                entry['acceptance_uses_original_float64_only'] = True
                save_json(folder_probe/(label+'.json'), entry)
                if details['kind'] == 'solution':
                    progress('refinement_outer_field_saved', probe_index=index,
                        outer_iteration=details['outer_iteration'],
                        residual_ratio=record['free_dof_residual_infinity_ratio'],
                        passes_original_threshold=record['passes_original_threshold'])
                return entry
            def observe_inner(iteration, rows):
                save_json(folder_probe/f'outer-{iteration:02d}-inner-residuals.json', {'iterations': rows, 'count': len(rows), 'preconditioned_not_acceptance': True})
            solution, history, final_record = refine_one(Kff, extended, factor, rhs[free], field[free], free, persist, observe_inner)
            refined = np.zeros(n); refined[free] = solution
            final_hash = save_array(output/f'probe-{index}-final-field.npy', refined)
            full_error = Kff @ solution - rhs[free]
            final_error_hash = save_array(output/f'probe-{index}-final-residual.npy', full_error)
            refined_fields.append(refined)
            row = {'probe_index': index, 'direction_sha256': array_sha(directions[index]),
                'rhs_full_sha256': array_sha(rhs), 'iterations': history,
                'final_original_residual': final_record,
                'passes_original_threshold': final_record['passes_original_threshold'],
                'final_field_file_sha256': final_hash, 'final_residual_file_sha256': final_error_hash}
            state['refined_probes'].append(row)
            state['probe_execution'][index]['status'] = 'passed' if row['passes_original_threshold'] else 'residual_rejected'
            progress('refined_probe_recorded', probe_index=index, outer_iterations=len(history),
                residual_ratio=final_record['free_dof_residual_infinity_ratio'],
                passes_original_threshold=row['passes_original_threshold'])
        save_array(output/'refined-five-probe-fields.npy', np.stack(refined_fields, axis=1))
        state['refined_all_five_passed'] = all(r['passes_original_threshold'] for r in state['refined_probes'])
        state['five_probe_residuals_passed_after_optional_refinement'] = state['refined_all_five_passed']
        state['original_Kff_identity_after'] = matrix_identity(Kff)
        if state['original_Kff_identity_before'] != state['original_Kff_identity_after']:
            raise ValueError('original Kff was changed')
        for path, digest in {**inputs, **state['source_sha256']}.items():
            if sha(path) != digest:
                raise ValueError('source or input changed: '+path)
        if free_bytes(output) < RESERVE_BYTES:
            raise RuntimeError('500MiB reserve not retained')
        state['diagnostic_completed'] = True
        state['runtime'] = {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__}
        state['files_sha256'] = {str(p.relative_to(output)): sha(p) for p in output.rglob('*')
            if p.is_file() and p.name not in ('report.json','progress.json')}
        progress('diagnostic_completed')
        save_json(output/'report.json', state)
        return 0 if state['refined_all_five_passed'] else 2
    except BaseException as exc:
        progress('diagnostic_failed', error_type=type(exc).__name__, error=str(exc))
        save_json(output/'report.json', state)
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Exact clean S4 checkout')
    parser.add_argument('--volume', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
