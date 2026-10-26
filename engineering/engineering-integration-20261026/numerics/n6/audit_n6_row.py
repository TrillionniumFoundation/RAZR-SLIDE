"""N6 capacity evidence: exact dyadic audit of one frozen CSC residual row.

Read-only diagnosis, not a new iterative solver. All source fields remain byte
identical. No sparse factorization or full-field candidate is produced. The
original float64 gate is never replaced by this scalar or exact arithmetic.
"""
from __future__ import annotations
from array import array
import argparse
from bisect import bisect_left
from fractions import Fraction
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
from n6_evidence_io import (AuditGateError, Evidence, KFF_COMPONENTS, K_COMPONENTS,
                            K_SHA, C_SHA, LIMIT, MANIFEST_SHA, ND, NF, ROW, S4,
                            S4_TREE, ZIP_BYTES, ZIP_SHA, float_bits, require,
                            sha_file, ulp_distance)

OUTPUT_CAP = 32 * 1024**2
AS_CAP = 2 * 1024**3
RESERVE = 500 * 1024**2
ORIGINAL_KFF_NNZ = 23645561


def dyadic(value):
    return Fraction.from_float(value)


def rational(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator),
            "nearest_float64": float(value), "nearest_float64_hex": float(value).hex()}


def scalar(value):
    return {"float64": value, "hex": value.hex(), "bits": float_bits(value)}


def dot_audit(coefficients, values, rhs, trace=False):
    exact_sum = Fraction(0)
    rounded_product_sum = Fraction(0)
    sequential = 0.0
    terms = []
    for i, (a, u) in enumerate(zip(coefficients, values)):
        exact_product = dyadic(a) * dyadic(u)
        product = a * u
        before = sequential
        sequential = sequential + product
        exact_sum += exact_product
        rounded_product_sum += dyadic(product)
        if trace:
            terms.append({"term_index": i, "rounded_product": scalar(product),
                          "accumulator_before": scalar(before), "accumulator_after": scalar(sequential),
                          "product_rounding_error_exact": rational(dyadic(product) - exact_product),
                          "addition_rounding_error_exact": rational(dyadic(sequential) - dyadic(before) - dyadic(product))})
    exact_residual = exact_sum - dyadic(rhs)
    residual = sequential - rhs
    product_error = rounded_product_sum - exact_sum
    sum_error = dyadic(sequential) - rounded_product_sum
    subtraction_error = dyadic(residual) - (dyadic(sequential) - dyadic(rhs))
    total_error = dyadic(residual) - exact_residual
    require(product_error + sum_error + subtraction_error == total_error, "exact_rounding_decomposition")
    result = {"sequential_float64_dot": scalar(sequential), "sequential_float64_residual": scalar(residual),
              "exact_real_residual_of_original_binary64_K_u_b": rational(exact_residual),
              "exact_real_dot_of_original_binary64_K_u": rational(exact_sum),
              "exact_sum_of_rounded_products": rational(rounded_product_sum),
              "product_rounding_error_exact": rational(product_error),
              "accumulation_rounding_error_exact": rational(sum_error),
              "subtraction_rounding_error_exact": rational(subtraction_error),
              "total_float64_minus_exact_residual": rational(total_error),
              "all_exact_arithmetic_uses_Fraction_of_binary64": True}
    if trace:
        result["all_ordered_terms"] = terms
    return result


def frozen_Kff_hashes_and_row(matrix, free, fixed):
    """Preserve the literal K[free][:,free].tocsc() column and row ordering.

No coefficient is recomputed. Stream-hash the resulting buffers against the
actual original Kff hashes retained by both N4b and N5a before interpreting a row.
"""
    mapping = array("i", [-1]) * ND
    for i, g in enumerate(free):
        mapping[g] = i
    data, indices, indptr = matrix["data"], matrix["indices"], matrix["indptr"]
    dh, ih = hashlib.sha256(), hashlib.sha256()
    pointers = array("i", [0])
    entries = []
    count = 0
    for j, global_col in enumerate(free):
        a, b = indptr[global_col], indptr[global_col + 1]
        col_data, col_indices = array("d"), array("i")
        last = -1
        for pos in range(a, b):
            global_row = indices[pos]
            require(last < global_row < ND, "original_CSC_sorted_unique_rows")
            last = global_row
            r = mapping[global_row]
            if r >= 0:
                col_indices.append(r)
                col_data.append(data[pos])
                if global_row == ROW:
                    entries.append({"original_column_DOF": int(global_col), "free_column_index": j,
                                    "original_CSC_data_position": pos, "coefficient": scalar(data[pos])})
        dh.update(col_data.tobytes())
        ih.update(col_indices.tobytes())
        count += len(col_data)
        pointers.append(count)
    identities = {"data": dh.hexdigest(), "indices": ih.hexdigest(),
                  "indptr": hashlib.sha256(pointers.tobytes()).hexdigest()}
    require(count == ORIGINAL_KFF_NNZ and identities == KFF_COMPONENTS, "actual_original_Kff_buffer_order_exact")
    require(0 < len(entries) <= 4096, "bounded_original_row_support")
    for e in entries:
        col = e["original_column_DOF"]
        a, b = indptr[col], indptr[col + 1]
        affected = [(int(indices[p]), data[p]) for p in range(a, b) if mapping[indices[p]] >= 0]
        e["affected_free_rows_in_original_column"] = len(affected)
        e["maximum_absolute_free_column_coefficient"] = max(abs(v) for _, v in affected)
        e["affected_original_free_row_DOFs"] = [r for r, _ in affected]
    return entries, identities


def stored_residual_summary(residual, free, denominator):
    require(len(residual) == NF and all(math.isfinite(x) for x in residual), "finite_stored_original_residual")
    at = max(range(NF), key=lambda i: abs(residual[i]))
    top = heapq.nlargest(32, range(NF), key=lambda i: abs(residual[i]))
    above = sum(abs(v) / denominator > LIMIT for v in residual)
    return {"numerator": abs(residual[at]), "denominator": denominator,
            "ratio": abs(residual[at]) / denominator, "max_original_DOF": int(free[at]),
            "signed_maximum": residual[at], "above_original_gate_row_count": above,
            "top_32_rows": [{"original_DOF": int(free[i]), "signed_residual": residual[i],
                             "ratio": abs(residual[i]) / denominator} for i in top],
            "scope": "reduction of retained native full residual vector; no new full native SpMV"}


def main(args):
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    result = {"schema": "razr-N6-original-row-capacity-audit-v1", "completed": False,
              "phase": "validating_frozen_evidence", "functional_source_commit": S4, "functional_source_tree": S4_TREE,
              "source_N5a_run_id": 40276429821, "source_release_asset_id": 677184053,
              "source_ZIP_sha256": ZIP_SHA, "source_ZIP_bytes": ZIP_BYTES, "source_manifest_sha256": MANIFEST_SHA,
              "original_K_sha256": K_SHA, "original_C_sha256": C_SHA, "original_float64_gate": LIMIT,
              "original_row_DOF": ROW, "new_solver_executed": False, "new_full_field_candidate_produced": False,
              "new_full_native_SpMV_executed": False, "original_input_fields_modified": False,
              "row_only_sensitivity_is_not_full_gate_acceptance": True,
              "H_action_restore_executed": False, "frame_inverse_executed": False,
              "candidate_go": False, "fixture_fabrication_go": False, "manufacturing_go": False,
              "address_space_limit_bytes": AS_CAP, "output_limit_bytes": OUTPUT_CAP,
              "states": [], "five_original_final_stored_residuals": []}
    evidence = None
    def save():
        result["elapsed_seconds"] = time.monotonic() - started
        result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        raw = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
        require(len(raw) <= OUTPUT_CAP, "row_audit_output_budget")
        temporary = args.output / "N6_ROW_AUDIT.json.writing"
        temporary.write_bytes(raw)
        os.replace(temporary, args.output / "N6_ROW_AUDIT.json")
    try:
        resource.setrlimit(resource.RLIMIT_AS, (AS_CAP, AS_CAP))
        require(sys.float_info.mant_dig == 53 and sys.float_info.radix == 2
                and float.__getformat__("double") == "IEEE, little-endian", "binary64_runtime")
        fs = os.statvfs(args.output)
        require(fs.f_bavail * fs.f_frsize >= RESERVE + OUTPUT_CAP, "audit_disk_reserve")
        evidence = Evidence(args.archive, args.matrix)
        free, fixed = evidence.domain()
        matrix, component_meta = evidence.original_matrix()
        result["original_K_components"] = {k: m["payload_sha256"] for k, m in component_meta.items()}
        row_index = bisect_left(free, ROW)
        result["original_row_free_index"] = row_index
        entries, Kff_identity = frozen_Kff_hashes_and_row(matrix, free, fixed)
        result["original_Kff_buffer_hashes_verified"] = Kff_identity
        result["ordered_original_free_row_entries"] = entries
        result["ordered_support_size"] = len(entries)
        report = evidence.read_json("probe-N5/report.engineering.json")["selected_engineering_fields"]
        readback = evidence.read_json("N5-independent-field-readback.engineering.json")["selected_engineering_fields"]
        require(readback["completed"] is True and readback["five_original_gates_passed"] is False
                and readback["outer_fields_checked"] == readback["correction_fields_checked"]
                == readback["actual_update_fields_checked"] == 32, "prior_independent_readback_complete")
        require(report["original_Kff_identity_before"] == report["original_Kff_identity_after"], "prior_Kff_unchanged")
        require({k: report["original_Kff_identity_before"][k]["sha256"] for k in Kff_identity} == Kff_identity,
                "current_filter_matches_actual_original_submatrix")
        rhs = evidence.npy("probe-N5/five-probe-rhs.npy", (ND, 5))
        diagonal = evidence.npy("probe-N5/original-diagonal.npy", (NF,))
        omega = report["damping"]["omega"]
        coefficients = [e["coefficient"]["float64"] for e in entries]
        cols = [e["original_column_DOF"] for e in entries]
        free_cols = [e["free_column_index"] for e in entries]
        row_matches = []
        states = []

        def read_state(label, field_name, residual_name, probe, expected, trace=False, update=None, previous=None):
            field = evidence.npy(field_name, (ND,))
            require(all(math.isfinite(v) for v in field) and all(field[g] == 0.0 for g in fixed), "full_field_finite_fixed_zero")
            residual = evidence.npy(residual_name, (NF,))
            denominator = max(max(abs(rhs[g * 5 + probe]) for g in free), 1.0)
            summary = stored_residual_summary(residual, free, denominator)
            require(summary["ratio"] == expected["free_dof_residual_infinity_ratio"]
                    and summary["max_original_DOF"] == expected["max_residual_original_dof"]
                    and denominator == expected["normalization_denominator"], "stored_full_residual_matches_original_report")
            values = [field[g] for g in cols]
            b = rhs[ROW * 5 + probe]
            audit = dot_audit(coefficients, values, b, trace)
            matched = audit["sequential_float64_residual"]["bits"] == float_bits(residual[row_index])
            row_matches.append(matched)
            row = {"label": label, "probe_index": probe, "field_member": field_name, "residual_member": residual_name,
                   "original_row_RHS": scalar(b), "ordered_support_values_hex": [v.hex() for v in values],
                   "stored_original_native_row_residual": scalar(residual[row_index]),
                   "sequential_row_replays_stored_native_bitpattern": matched,
                   "full_stored_residual_reduction": summary, "row_arithmetic": audit}
            if update is not None:
                requested = evidence.npy(update["requested"], (ND,))
                actual = evidence.npy(update["actual"], (ND,))
                changes = []
                for j, g in enumerate(cols):
                    old, new, wanted = previous[j], values[j], requested[g]
                    require(float_bits(old + wanted) == float_bits(new)
                            and float_bits(new - old) == float_bits(actual[g]), "support_update_chain_exact")
                    prior_row = update["prior_residual"][free_cols[j]]
                    required_correction = (-prior_row / diagonal[free_cols[j]]) * omega
                    require(float_bits(required_correction) == float_bits(wanted), "support_original_float64_correction_order")
                    changes.append({"original_DOF": g, "before_hex": old.hex(), "requested_hex": wanted.hex(),
                                    "after_hex": new.hex(), "actual_update_hex": actual[g].hex(),
                                    "ULP_distance": ulp_distance(old, new), "changed": old != new,
                                    "nonzero_request_rounded_to_no_change": wanted != 0.0 and old == new})
                row["support_updates"] = changes
                row["changed_support_DOFs"] = sum(x["changed"] for x in changes)
                row["rounded_away_nonzero_support_requests"] = sum(x["nonzero_request_rounded_to_no_change"] for x in changes)
            return row, values, residual

        result["phase"] = "replaying_baseline_and_all_32_original_history_states"
        baseline = report["baseline_probes"][0]
        state, previous, previous_residual = read_state("probe-0-baseline", "probe-N5/probe-0-baseline-field.npy",
            "probe-N5/probe-0-baseline-residual.npy", 0, baseline, trace=True)
        states.append(state)
        result["states"] = states
        save()
        history = report["refined_probes"][0]["iterations"]
        require(len(history) == 32, "frozen_32_actual_updates")
        for i, item in enumerate(history, 1):
            require(item["outer_iteration"] == i, "history_original_order")
            state, previous, previous_residual = read_state(f"probe-0-outer-{i:02d}",
                "probe-N5/" + item["field_file"], "probe-N5/" + item["residual_file"], 0,
                item["equation_residual"], update={"requested": "probe-N5/" + item["local_return"]["field_file"],
                    "actual": "probe-N5/" + item["actual_update_file"], "prior_residual": previous_residual}, previous=previous)
            state["recorded_longdouble_ratio_diagnostic_only"] = item["longdouble_equation_residual_ratio_diagnostic_only"]
            states.append(state)
            if i % 8 == 0:
                save()
        final_values = None
        for probe in range(5):
            entry = report["refined_probes"][probe]
            state, values, unused = read_state(f"probe-{probe}-final", f"probe-N5/probe-{probe}-final-field.npy",
                f"probe-N5/probe-{probe}-final-residual.npy", probe, entry["final_original_residual"], trace=(probe == 0))
            if probe == 0:
                final_values = values
                require(state["ordered_support_values_hex"] == states[-1]["ordered_support_values_hex"], "final_is_step_32_support")
            else:
                a = evidence.byte_check(f"probe-N5/probe-{probe}-baseline-field.npy")
                require(a == evidence.used[f"probe-N5/probe-{probe}-final-field.npy"], "four_passing_original_field_files_unchanged")
            states.append(state)
            result["five_original_final_stored_residuals"].append(state["full_stored_residual_reduction"])
        result["all_38_retained_states_replay_original_row_bitpattern"] = all(row_matches)
        result["row_state_count"] = len(states)
        require(len(states) == 38, "all_original_states_recorded")
        result["phase"] = "bounded_row_only_ULP_sensitivity"
        trials = []
        if all(row_matches):
            denominator = report["refined_probes"][0]["final_original_residual"]["normalization_denominator"]
            b = rhs[ROW * 5]
            baseline_exact = sum((dyadic(a) * dyadic(u) for a, u in zip(coefficients, final_values)), Fraction()) - dyadic(b)
            baseline_row = states[33]["stored_original_native_row_residual"]["float64"]
            ld_ratio = history[-1]["longdouble_equation_residual_ratio_diagnostic_only"]
            for j, (e, u) in enumerate(zip(entries, final_values)):
                for direction in (-1, 1):
                    adjacent = math.nextafter(u, -math.inf if direction < 0 else math.inf)
                    require(math.isfinite(adjacent) and ulp_distance(u, adjacent) == 1, "finite_adjacent_ULP")
                    values = list(final_values)
                    values[j] = adjacent
                    sequential = 0.0
                    for a, x in zip(coefficients, values):
                        sequential = sequential + a * x
                    residual = sequential - b
                    exact_delta = dyadic(e["coefficient"]["float64"]) * (dyadic(adjacent) - dyadic(u))
                    exact_residual = baseline_exact + exact_delta
                    delta = adjacent - u
                    heuristic = ld_ratio + e["maximum_absolute_free_column_coefficient"] * abs(delta) / denominator
                    trials.append({"trial_index": len(trials), "original_free_column_DOF": e["original_column_DOF"],
                        "support_index": j, "direction": direction, "old_value_hex": u.hex(), "adjacent_value_hex": adjacent.hex(),
                        "actual_ULP_distance": 1, "delta_hex": delta.hex(), "row_float64_residual": scalar(residual),
                        "row_ratio": abs(residual) / denominator, "row_only_original_gate_passes": abs(residual) / denominator <= LIMIT,
                        "row_absolute_float64_residual_improves": abs(residual) < abs(baseline_row),
                        "exact_original_equation_row_residual": rational(exact_residual),
                        "exact_row_error_does_not_increase": abs(exact_residual) <= abs(baseline_exact),
                        "exact_row_residual_change": rational(exact_delta),
                        "recorded_longdouble_plus_column_delta_ratio_estimate": heuristic,
                        "estimate_is_not_certified_bound_or_acceptance": True,
                        "full_native_float64_gate_evaluated": False, "candidate_field_created_or_accepted": False})
        result["all_row_only_adjacent_ULP_trials"] = trials
        result["sensitivity"] = {"finite_registered_trial_count": 2 * len(entries), "actual_trial_count": len(trials),
            "disabled_if_original_row_replay_mismatch": not all(row_matches),
            "row_only_float64_improvement_count": sum(t["row_absolute_float64_residual_improves"] for t in trials),
            "row_only_float64_pass_count": sum(t["row_only_original_gate_passes"] for t in trials),
            "row_only_pass_and_exact_row_error_nonincrease_count": sum(t["row_only_original_gate_passes"] and t["exact_row_error_does_not_increase"] for t in trials),
            "full_five_probe_qualification_conclusion": "not executed; prior original qualification remains rejected",
            "new_iteration_or_search_strategy_execution_authorized_by_this_audit": False}
        result["used_original_member_identities"] = evidence.used
        result["source_file_identity"] = sha_file(__file__)
        result["completed"] = True
        result["phase"] = "complete_read_only_capacity_evidence"
        save()
        print(json.dumps({k: result[k] for k in ("completed", "row_state_count", "ordered_support_size", "all_38_retained_states_replay_original_row_bitpattern", "sensitivity", "elapsed_seconds", "peak_rss_kib")}, indent=2))
        return 0 if all(row_matches) else 2
    except BaseException as e:
        result["failure_type"] = type(e).__name__
        if isinstance(e, AuditGateError):
            result["failure_gate"] = str(e)
        if evidence is not None:
            result["used_original_member_identities"] = evidence.used
        save()
        return 2
    finally:
        if evidence is not None:
            evidence.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
