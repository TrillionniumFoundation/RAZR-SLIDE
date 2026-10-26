"""N7: finite adjacent-ULP coordinates on the original five panel equations.

The original float64 CSC gate remains authoritative. Virtual row screens never
claim a native full-field pass. Every full candidate, including rejections, is
retained. Accepted states form one chronological chain; no best-history choice.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import gc
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import re
import subprocess
import sys
import time
import numpy as np
from scipy.sparse import load_npz
from n7_contract import (S4, S4_TREE, ND, NF, NP, FIXED, LIMIT, MAX_FULL, MAX_SCALAR,
 MAX_ROW_SUPPORT, MAX_CACHE_ROWS, MAX_EXACT_TERMS, MAX_READER_EXACT_TERMS,
 MAX_CACHE_BYTES, MAX_FRACTION_BITS, AS_BYTES, OUTPUT_BYTES, RESERVE_BYTES,
 WALL_SECONDS, KFF_SHA, K_SHA, C_SHA, HELPER, HELPER_SHA, POINT_SOURCE,
 POINT_SOURCE_SHA, GateError, CapacityStop, require, sha_file, bits,
 verify_frozen_files, reserve, write_json)

RESIDUAL_LIMIT = LIMIT
def array_sha(value):
    return hashlib.sha256(np.asarray(value, dtype=np.float64).tobytes()).hexdigest()

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

def qpack(q):
    require(max(q.numerator.bit_length(), q.denominator.bit_length()) <= MAX_FRACTION_BITS,
            "exact_integer_size_cap")
    return {"numerator": str(q.numerator), "denominator": str(q.denominator)}

def exact_product(a, b):
    return Fraction.from_float(float(a)) * Fraction.from_float(float(b))

def ordered_row_dot(coefficients, values):
    out = 0.0
    for a, u in zip(coefficients, values):
        out = out + float(a) * float(u)
    return out

def row_screen(coefficients, values, at, direction, rhs, exact_before, denominator):
    old = float(values[at])
    new = math.nextafter(old, -math.inf if direction == -1 else math.inf)
    require(math.isfinite(new) and bits(new) != bits(old), "finite_adjacent_value")
    delta = Fraction.from_float(new) - Fraction.from_float(old)
    exact_after = exact_before + Fraction.from_float(float(coefficients[at])) * delta
    changed = list(values); changed[at] = new
    residual = ordered_row_dot(coefficients, changed) - float(rhs)
    ratio = abs(residual) / denominator
    return new, delta, {
        "old_value_hex": old.hex(), "adjacent_value_hex": new.hex(),
        "actual_ULP_distance": 1, "actual_delta_hex": float(delta).hex(),
        "predicted_original_order_float64_residual_bits": bits(residual),
        "predicted_original_order_float64_residual": residual,
        "predicted_row_ratio": ratio,
        "exact_row_before": qpack(exact_before), "exact_row_after": qpack(exact_after),
        "row_only_gate_predicted": bool(ratio <= LIMIT),
        "exact_row_absolute_nonincrease": abs(exact_after) <= abs(exact_before),
        "eligible_for_full_candidate": bool(ratio <= LIMIT and abs(exact_after) <= abs(exact_before)),
        "native_full_gate_evaluated_by_this_screen": False,
    }

def acceptance_conditions(proof, old, new):
    return {
        "all_affected_exact_infinity_nonincrease": proof["all_affected_exact_infinity_nonincrease"],
        "probe0_violation_count_strictly_decreases": new[0]["over_gate_row_count"] < old[0]["over_gate_row_count"],
        "original_full_five_max_ratio_nonincrease": max(r["free_dof_residual_infinity_ratio"] for r in new)
            <= max(r["free_dof_residual_infinity_ratio"] for r in old),
        "other_four_original_gates_remain_passed": all(new[k]["passes_original_threshold"] for k in range(1,5)),
    }

class ExactCache:
    def __init__(self, csr, rhs, free):
        self.A, self.b, self.free = csr, rhs, free
        self.values = {}
        self.terms = 0
        self.reader_terms_registered = 0
        self.hits = 0
        self.storage_estimate_bytes = 0

    def get(self, row, u):
        row = int(row)
        if row in self.values:
            self.hits += 1
            return self.values[row]
        lo, hi = self.A.indptr[row:row+2]
        count = int(hi-lo)
        if count > 1024 or self.terms + count > MAX_EXACT_TERMS:
            raise CapacityStop("finite_exact_product_addition_cap")
        if len(self.values) >= MAX_CACHE_ROWS:
            raise CapacityStop("finite_exact_cache_row_cap")
        value = -Fraction.from_float(float(self.b[row]))
        for k in range(lo, hi):
            value += exact_product(self.A.data[k], u[self.A.indices[k]])
        qpack(value)
        estimate = 256 + sys.getsizeof(value) + sys.getsizeof(value.numerator) + sys.getsizeof(value.denominator)
        if self.storage_estimate_bytes + estimate > MAX_CACHE_BYTES:
            raise CapacityStop("finite_exact_cache_memory_cap")
        self.terms += count
        self.storage_estimate_bytes += estimate
        self.values[row] = value
        return value

    def candidate(self, column_rows, column_values, delta, u):
        if len(column_rows) > 512:
            raise CapacityStop("finite_affected_row_cap")
        cost = 2 * sum(int(self.A.indptr[int(i)+1]-self.A.indptr[int(i)]) for i in column_rows)
        if self.reader_terms_registered + cost > MAX_READER_EXACT_TERMS:
            raise CapacityStop("finite_independent_direct_exact_recompute_cap")
        before, after, records = {}, {}, []
        for i, a in zip(column_rows, column_values):
            i = int(i); before[i] = self.get(i, u)
            after[i] = before[i] + Fraction.from_float(float(a)) * delta
            records.append({"free_row_index": i, "original_row_DOF": int(self.free[i]),
                            "original_coefficient_hex": float(a).hex(),
                            "before": qpack(before[i]), "after": qpack(after[i])})
        self.reader_terms_registered += cost
        old_max = max((abs(q) for q in before.values()), default=Fraction())
        new_max = max((abs(q) for q in after.values()), default=Fraction())
        return after, {"all_affected_rows": records,
             "affected_row_count": len(records), "direct_reader_product_terms_for_trial": cost,
             "affected_exact_infinity_before": qpack(old_max),
             "affected_exact_infinity_after": qpack(new_max),
             "all_affected_exact_infinity_nonincrease": new_max <= old_max,
             "outside_affected_column_exact_equations_unchanged": True}

    def accept(self, changes):
        self.values.update(changes)
        self.storage_estimate_bytes = sum(256 + sys.getsizeof(q) + sys.getsizeof(q.numerator)
                                         + sys.getsizeof(q.denominator) for q in self.values.values())
        if self.storage_estimate_bytes > MAX_CACHE_BYTES:
            raise CapacityStop("finite_exact_cache_memory_cap")

    def counters(self):
        return {"cached_rows": len(self.values), "exact_product_terms": self.terms,
                "direct_reader_exact_terms_registered": self.reader_terms_registered,
                "cache_hits": self.hits, "cache_storage_estimate_bytes": self.storage_estimate_bytes}

def load_inputs(case, root):
    identities = verify_frozen_files(case)
    require(sha_file(root/HELPER) == HELPER_SHA and sha_file(root/POINT_SOURCE) == POINT_SOURCE_SHA,
            "original_helper_and_point_source")
    require(subprocess.check_output(["git","rev-parse","HEAD"], cwd=root, text=True).strip() == S4
            and subprocess.check_output(["git","rev-parse","HEAD^{tree}"], cwd=root, text=True).strip() == S4_TREE,
            "functional_S4_commit_tree")
    frozen = case/"frozen"; volume = frozen/"volume/panel/level-2"; p = frozen/"probe-N5"
    model = json.loads((volume/"report.engineering.json").read_text())["selected_engineering_fields"]
    require(model["body"] == "panel" and model["level"] == 2 and model["E_normalization"] == 1.0
            and model["nu"] == 0.3 and model["K_sha256"] == K_SHA
            and model["original_faces_and_surface_P2_traces_unchanged"] is True
            and model["body_loads_on_added_internal_DOFs"] is False, "original_model_domain")
    fixed = np.load(p/"fixed-original-DOFs.npy", allow_pickle=False)
    free = np.load(p/"free-original-DOFs.npy", allow_pickle=False)
    require(fixed.dtype == free.dtype == np.int64 and tuple(map(int,fixed)) == FIXED
            and len(set(map(int,fixed))) == 6
            and np.array_equal(free, np.setdiff1d(np.arange(ND),fixed)) and len(free) == NF,
            "original_fixed_order_and_exact_free_complement")
    with np.load(volume/"loads.npz", allow_pickle=False) as loads:
        require(np.array_equal(loads["D"], fixed), "original_load_fixed_order")
    points = json.loads((p/"points.json").read_text())
    seed = json.loads(gzip.decompress((root/POINT_SOURCE).read_bytes()))
    require(seed["case"] == 6 and seed["volume_level"] == 2
            and points == seed["contact_points"] and len(points) == 3885,
            "original_ordered_point_domain")
    C = load_npz(p/"C.npz").tocsc()
    require(C.shape == (ND,3885) and C.nnz == 24518 and C.dtype == np.float64
            and C.has_canonical_format, "original_C_structure")
    directions = np.load(p/"five-probe-directions.npy", allow_pickle=False)
    rhs = np.load(p/"five-probe-rhs.npy", allow_pickle=False)
    require(directions.shape == (3885,5) and rhs.shape == (ND,5)
            and directions.dtype == rhs.dtype == np.float64, "original_five_shapes")
    rng = np.random.default_rng(73021)
    expected = [np.ones(3885)] + [rng.choice([-1.,1.],3885) for _ in range(4)]
    for j,d in enumerate(expected):
        require(np.array_equal(directions[:,j],d) and np.array_equal(rhs[:,j],np.asarray(C@d).ravel()),
                "original_five_directions_RHS_same_C")
    A = load_npz(volume/"K.npz")
    require(A.format == "csc" and A.shape == (ND,ND) and A.nnz == 23646483
            and A.dtype == np.float64 and A.has_canonical_format, "original_K_structure")
    A = A[free][:,free].tocsc()
    require(A.nnz == 23645561, "original_Kff_nnz")
    for key,digest in KFF_SHA.items():
        require(hashlib.sha256(getattr(A,key).tobytes()).hexdigest() == digest, "original_Kff_buffer_identity")
    require(np.array_equal(A.diagonal(),np.load(p/"original-diagonal.npy",allow_pickle=False)),
            "original_diagonal_identity")
    fields = [np.load(p/f"probe-{j}-final-field.npy", allow_pickle=False) for j in range(5)]
    old_errors = [np.load(p/f"probe-{j}-final-residual.npy", allow_pickle=False) for j in range(5)]
    for u,e in zip(fields,old_errors):
        require(u.shape == (ND,) and e.shape == (NF,) and u.dtype == e.dtype == np.float64
                and np.isfinite(u).all() and np.isfinite(e).all() and np.all(u[fixed] == 0),
                "original_five_frozen_fields")
    return A, free, fixed, rhs[free,:], fields, old_errors, identities

def run(args):
    start = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    case, root = args.case.resolve(strict=True), args.root.resolve(strict=True)
    folder = case/"probe-N7"; folder.mkdir(exist_ok=False)
    report = {"schema": "razr-N7-finite-original-five-probe-v1", "completed": False,
        "phase": "frozen_input_validation", "functional_source_commit": S4,
        "functional_source_tree": S4_TREE, "original_gate": LIMIT,
        "original_K_sha256": K_SHA, "original_C_sha256": C_SHA,
        "strategy": "finite adjacent-ULP coordinates with exact all-affected-row nonincrease",
        "full_candidate_limit": MAX_FULL, "scalar_screen_limit": MAX_SCALAR,
        "target_support_limit": MAX_ROW_SUPPORT, "stages": [], "trials": [], "files": {},
        "scalar_screen_count": 0, "accepted_trial_indices": [],
        "original_five_passed": False, "select_best_history": False,
        "H_action_restore_executed": False, "frame_inverse_executed": False,
        "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False}
    cache = None; screen_bytes = 0
    def save():
        report["elapsed_seconds"] = time.monotonic()-start
        report["peak_rss_KiB"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if cache is not None: report["exact_capacity_counters"] = cache.counters()
        write_json(folder/"N7_REPORT.json", report, case)
    def guard():
        if time.monotonic()-start >= WALL_SECONDS:
            raise CapacityStop("original_180_second_worker_wall")
    def save_array(relative, value):
        reserve(case, int(value.nbytes)+4096)
        path = case/relative; path.parent.mkdir(parents=True,exist_ok=True)
        temporary = path.with_name(path.name+".writing")
        with temporary.open("wb") as f:
            np.save(f,value,allow_pickle=False); f.flush(); os.fsync(f.fileno())
        os.replace(temporary,path)
        identity = {"bytes":path.stat().st_size,"sha256":sha_file(path)}
        report["files"][relative] = identity
        return identity
    def append_screen(screen):
        nonlocal screen_bytes
        data = (json.dumps(screen,sort_keys=True,allow_nan=False)+"\n").encode()
        if screen_bytes+len(data)>16*1024**2:
            raise CapacityStop("finite_virtual_screen_log_byte_cap")
        if report["scalar_screen_count"] % 64 == 0: reserve(case, len(data)+1024**2)
        with (folder/"N7_SCALAR_SCREENS.jsonl").open("ab",buffering=0) as f: f.write(data)
        screen_bytes += len(data)
        report["scalar_screen_count"] += 1
    try:
        save()
        A,free,fixed,rhs,current,old_errors,identities = load_inputs(case,root)
        report["input_validation_and_Kff_seconds"] = time.monotonic()-start
        report["frozen_input_identities"] = identities
        report["original_Kff_buffer_hashes"] = dict(KFF_SHA)
        extended = A.astype(np.longdouble)
        require(np.finfo(np.longdouble).eps < np.finfo(np.float64).eps, "additional_diagnostic_extended_precision")
        csr = A.tocsr()
        require(csr.has_canonical_format, "diagnostic_CSR_canonical")
        report["diagnostic_CSR_only_original_gate_stays_CSC"] = True
        report["matrix_array_bytes"] = {
            "original_Kff_CSC": sum(getattr(A,k).nbytes for k in ("data","indices","indptr")),
            "diagnostic_CSR": sum(getattr(csr,k).nbytes for k in ("data","indices","indptr")),
            "diagnostic_longdouble_CSC": sum(getattr(extended,k).nbytes for k in ("data","indices","indptr"))}
        report["input_and_matrix_setup_seconds"] = time.monotonic()-start
        cache = ExactCache(csr,rhs[:,0],free)
        initial_fields = [u.copy() for u in current]
        def measure(fields, prefix=None):
            rows, errors = [], []
            for j,u in enumerate(fields):
                guard()
                measure_start = time.monotonic()
                rec,e = residual_record(A,u[free],rhs[:,j],free)
                rec["probe_index"] = j
                rec["over_gate_row_count"] = int(np.count_nonzero(np.abs(e)/rec["normalization_denominator"] > LIMIT))
                ld = extended@u[free].astype(np.longdouble)-rhs[:,j].astype(np.longdouble)
                rec["longdouble_residual_ratio_diagnostic_only"] = float(np.max(np.abs(ld)))/rec["normalization_denominator"]
                if prefix is not None:
                    field_name = f"{prefix}/probe-{j}-field.npy"
                    residual_name = f"{prefix}/probe-{j}-residual.npy"
                    rec["field_file"] = field_name; rec["field_identity"] = save_array(field_name,u)
                    rec["residual_file"] = residual_name; rec["residual_identity"] = save_array(residual_name,e)
                rec["native_gate_diagnostic_and_persistence_seconds"] = time.monotonic()-measure_start
                rows.append(rec); errors.append(e)
            return rows,errors
        baseline,errors = measure(current)
        for j in range(5):
            require(errors[j].tobytes() == old_errors[j].tobytes(), "baseline_native_matches_frozen_residual_bytes")
        require([r["passes_original_threshold"] for r in baseline] == [False,True,True,True,True],
                "same_N5a_rejected_start")
        report["baseline"] = baseline
        current_rows = baseline
        base_ref = "frozen/probe-N5/probe-0-final-field.npy"
        base_sha = sha_file(case/base_ref)
        report["phase"] = "finite_coordinate_trials"
        save()
        stopped = False
        while not all(r["passes_original_threshold"] for r in current_rows):
            guard()
            if len(report["trials"]) >= MAX_FULL:
                report["termination"] = "32_full_candidate_limit"; break
            if report["scalar_screen_count"] >= MAX_SCALAR:
                raise CapacityStop("finite_scalar_screen_count_cap")
            target = int(np.argmax(np.abs(errors[0])))
            lo,hi = map(int,csr.indptr[target:target+2])
            columns = csr.indices[lo:hi]; coeff = csr.data[lo:hi]
            if len(columns)>MAX_ROW_SUPPORT:
                raise CapacityStop("finite_target_row_support_cap")
            require(np.all(columns[1:]>columns[:-1]), "original_column_sequence_unique_ascending")
            values = current[0][free[columns]]
            require(bits(ordered_row_dot(coeff,values)-float(rhs[target,0])) == bits(errors[0][target]),
                    "virtual_original_order_matches_native_current_row")
            exact_base = cache.get(target,current[0][free])
            stage = {"stage_index":len(report["stages"])+1,"base_field_file":base_ref,
                "base_field_sha256":base_sha,"target_free_index":target,"target_original_DOF":int(free[target]),
                "base_global_ratio":max(r["free_dof_residual_infinity_ratio"] for r in current_rows),
                "base_probe0_violation_count":current_rows[0]["over_gate_row_count"],
                "ordered_support":[{"free_column_index":int(j),"original_column_DOF":int(free[j]),
                                    "coefficient_hex":float(a).hex()} for j,a in zip(columns,coeff)],
                "first_screen_index":report["scalar_screen_count"]+1,"last_screen_index":report["scalar_screen_count"],
                "status":"screening","accepted_trial_index":None}
            report["stages"].append(stage); save()
            accepted = False
            for at,j in enumerate(columns):
                for direction in (-1,1):
                    guard()
                    if len(report["trials"])>=MAX_FULL:
                        stopped=True; report["termination"]="32_full_candidate_limit"; break
                    if report["scalar_screen_count"]>=MAX_SCALAR:
                        raise CapacityStop("finite_scalar_screen_count_cap")
                    new,delta,decision = row_screen(coeff,values,at,direction,rhs[target,0],exact_base,
                                                   current_rows[0]["normalization_denominator"])
                    screen = {"schema":"razr-N7-virtual-row-screen-v1",
                        "screen_index":report["scalar_screen_count"]+1,"stage_index":stage["stage_index"],
                        "base_field_sha256":base_sha,"target_original_DOF":int(free[target]),
                        "support_index":at,"original_free_column_DOF":int(free[j]),
                        "direction":direction,**decision}
                    append_screen(screen); stage["last_screen_index"]=screen["screen_index"]
                    if not decision["eligible_for_full_candidate"]: continue
                    col_start,col_end = map(int,A.indptr[int(j):int(j)+2])
                    affected=A.indices[col_start:col_end]; col_values=A.data[col_start:col_end]
                    nonzero=col_values!=0.0; affected=affected[nonzero]; col_values=col_values[nonzero]
                    changed_exact,proof=cache.candidate(affected,col_values,delta,current[0][free])
                    trial_index=len(report["trials"])+1
                    trial={"trial_index":trial_index,"screen_index":screen["screen_index"],
                        "stage_index":stage["stage_index"],"base_field_file":base_ref,"base_field_sha256":base_sha,
                        "original_changed_DOF":int(free[j]),"actual_ULP_distance":1,"complete":False,
                        "accepted":False,"exact_affected_proof":proof}
                    report["trials"].append(trial); save()
                    candidates=[current[0].copy()]+current[1:]
                    candidates[0][free[j]]=new
                    request=np.zeros(ND,dtype=np.float64); request[free[j]]=float(delta)
                    actual=candidates[0]-current[0]
                    require(np.count_nonzero(actual)==1 and actual.tobytes()==request.tobytes(),
                            "actual_one_ULP_update_exactly_requested")
                    prefix=f"probe-N7/trial-{trial_index:02d}"
                    trial["requested_update_file"]=prefix+"/requested-update.npy"
                    trial["actual_update_file"]=prefix+"/actual-update.npy"
                    save_array(trial["requested_update_file"],request)
                    save_array(trial["actual_update_file"],actual)
                    trial["update_observation"]={"requested_nonzero_DOFs":1,"actually_changed_DOFs":1,
                        "rounded_away_nonzero_requests":0,"actual_ULP_distance":1,
                        "actual_update_infinity_norm":float(np.max(np.abs(actual))),
                        "requested_update_infinity_norm":float(np.max(np.abs(request)))}
                    rows,new_errors=measure(candidates,prefix)
                    require(bits(new_errors[0][target]) == decision["predicted_original_order_float64_residual_bits"],
                            "full_native_target_equals_virtual_prediction")
                    for k in range(1,5):
                        require(candidates[k].tobytes()==initial_fields[k].tobytes()
                                and sha_file(case/rows[k]["field_file"])==identities[f"probe-N5/probe-{k}-final-field.npy"]["sha256"],
                                "four_prior_pass_field_array_and_file_bytes_unchanged")
                    conditions=acceptance_conditions(proof,current_rows,rows)
                    trial.update(complete=True,probes=rows,acceptance_conditions=conditions,
                        accepted=all(conditions.values()),all_five_original_gates_passed=all(r["passes_original_threshold"] for r in rows))
                    if trial["accepted"]:
                        cache.accept(changed_exact)
                        current=candidates; current_rows=rows; errors=new_errors
                        base_ref=rows[0]["field_file"]; base_sha=rows[0]["field_identity"]["sha256"]
                        report["accepted_trial_indices"].append(trial_index)
                        stage["status"]="accepted"; stage["accepted_trial_index"]=trial_index
                        accepted=True
                    save()
                    if accepted: break
                if accepted or stopped: break
            if stopped: stage["status"]="full_candidate_budget_exhausted"; break
            if not accepted:
                stage["status"]="all_finite_target_candidates_rejected"
                report["termination"]="finite_current_target_candidates_exhausted"; break
            if all(r["passes_original_threshold"] for r in current_rows):
                report["termination"]="first_accepted_state_passing_all_five"; break
        report["phase"]="final_sequential_state"
        final_rows,final_errors=measure(current,"probe-N7/final")
        for old,new_error in zip(errors,final_errors):
            require(old.tobytes()==new_error.tobytes(),"final_state_same_sequential_native_residual")
        report.update(completed=True,phase="complete_finite_trial_evidence",
            final=final_rows,final_sequential_base_field_file=base_ref,final_sequential_base_field_sha256=base_sha,
            original_five_passed=all(r["passes_original_threshold"] for r in final_rows),
            full_candidates_completed=sum(t["complete"] for t in report["trials"]),
            exact_global_nonincrease_proof_scope="Each accepted one-coordinate change preserves all equations outside its stored nonzero column and does not increase the exact infinity norm over every affected row.",
            four_prior_pass_fields_array_and_file_bytes_unchanged=True)
        for key,digest in KFF_SHA.items():
            require(hashlib.sha256(getattr(A,key).tobytes()).hexdigest()==digest,"final_original_Kff_unchanged")
        report["final_original_Kff_unchanged"]=True
        save()
        return 0 if report["original_five_passed"] else 2
    except BaseException as e:
        report.update(completed=False,original_five_passed=False,failure_type=type(e).__name__,
                      partial_evidence_preserved=True)
        if isinstance(e,GateError): report["failure_gate"]=str(e)
        if isinstance(e,KeyError) and e.args and isinstance(e.args[0],str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,80}",e.args[0]): report["failure_key"]=e.args[0]
        if isinstance(e,CapacityStop): report["capacity_stop"]=True
        try: save()
        except BaseException: pass
        return 2

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--case",type=Path,required=True); p.add_argument("--root",type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
