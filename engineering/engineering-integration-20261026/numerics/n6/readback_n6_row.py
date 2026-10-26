"""Independent scalar readback from original archive arrays, not producer rows.

Shares only hash-checked stdlib input I/O. Extracts the row by a linear scan of
original CSC row indices (producer streams filtered columns); independently
replays every retained state and exact dyadic identity. No full sparse solve or
new native full-matrix residual evaluation is performed.
"""
from __future__ import annotations
import argparse
from bisect import bisect_left, bisect_right
from fractions import Fraction
import json
import math
from pathlib import Path
import resource
import struct
import time
from n6_evidence_io import (AuditGateError, Evidence, KFF_COMPONENTS, LIMIT, ND, NF,
                            ROW, require, sha_file)


def bits(x):
    return struct.pack("<d", x)


def F(x):
    a, b = x.as_integer_ratio()
    return Fraction(a, b)


def equal_rational(record, value):
    require(int(record["numerator"]) == value.numerator and int(record["denominator"]) == value.denominator
            and bits(record["nearest_float64"]) == bits(float(value))
            and record["nearest_float64_hex"] == float(value).hex(), "independent_exact_dyadic_identity")


def check_scalar(record, value):
    require(record == {"float64": value, "hex": value.hex(), "bits": struct.pack(">d", value).hex()}, "independent_scalar_bits")


def ulps(a, b):
    def key(x):
        raw = int.from_bytes(struct.pack(">d", x), "big")
        return (2**64 - 1 - raw) if raw >= 2**63 else raw + 2**63
    return abs(key(a) - key(b))


def independently_check_arithmetic(record, coefficients, values, rhs):
    exact_products = [F(a) * F(u) for a, u in zip(coefficients, values)]
    rounded_products = [a * u for a, u in zip(coefficients, values)]
    total = 0.0
    if "all_ordered_terms" in record:
        require(len(record["all_ordered_terms"]) == len(coefficients), "independent_all_term_count")
    for index, p in enumerate(rounded_products):
        old = total
        total += p
        if "all_ordered_terms" in record:
            trace = record["all_ordered_terms"][index]
            require(trace["term_index"] == index, "independent_trace_order")
            check_scalar(trace["rounded_product"], p)
            check_scalar(trace["accumulator_before"], old)
            check_scalar(trace["accumulator_after"], total)
            equal_rational(trace["product_rounding_error_exact"], F(p) - exact_products[index])
            equal_rational(trace["addition_rounding_error_exact"], F(total) - F(old) - F(p))
    original_residual = total - rhs
    exact_dot = sum(exact_products, Fraction())
    rounded_sum = sum((F(p) for p in rounded_products), Fraction())
    exact_residual = exact_dot - F(rhs)
    check_scalar(record["sequential_float64_dot"], total)
    check_scalar(record["sequential_float64_residual"], original_residual)
    equal_rational(record["exact_real_residual_of_original_binary64_K_u_b"], exact_residual)
    equal_rational(record["exact_real_dot_of_original_binary64_K_u"], exact_dot)
    equal_rational(record["exact_sum_of_rounded_products"], rounded_sum)
    equal_rational(record["product_rounding_error_exact"], rounded_sum - exact_dot)
    equal_rational(record["accumulation_rounding_error_exact"], F(total) - rounded_sum)
    equal_rational(record["subtraction_rounding_error_exact"], F(original_residual) - F(total) + F(rhs))
    equal_rational(record["total_float64_minus_exact_residual"], F(original_residual) - exact_residual)
    require(record["all_exact_arithmetic_uses_Fraction_of_binary64"] is True, "independent_exact_arithmetic_scope")
    return original_residual, exact_residual


def run(args):
    started = time.monotonic()
    result = {"schema": "razr-N6-independent-scalar-row-readback-v1", "completed": False,
              "native_full_SpMV_or_solve_executed": False, "new_field_produced": False,
              "original_five_qualification_status": "rejected by retained N5a native evidence",
              "states_checked": 0, "support_update_chains_checked": 0, "row_only_trials_checked": 0,
              "exact_arithmetic": "integer-ratio Fraction; no decimal precision assumption",
              "original_array_input_parser_shared_with_producer": True,
              "numeric_audit_or_row_extraction_code_shared_with_producer": False}
    evidence = None
    try:
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        require(args.audit.stat().st_size <= 32 * 1024**2, "bounded_row_packet")
        packet = json.loads(args.audit.read_text())
        result["producer_audit_identity"] = sha_file(args.audit)
        require(packet["schema"] == "razr-N6-original-row-capacity-audit-v1" and packet["completed"] is True, "producer_audit_complete")
        require(packet["source_file_identity"] == sha_file(args.worker), "producer_source_byte_identity")
        for key in ("new_solver_executed", "new_full_field_candidate_produced", "new_full_native_SpMV_executed",
                    "original_input_fields_modified", "H_action_restore_executed", "frame_inverse_executed",
                    "candidate_go", "fixture_fabrication_go", "manufacturing_go"):
            require(packet[key] is False, "producer_read_only_scope")
        evidence = Evidence(args.archive, args.matrix)
        free, fixed = evidence.domain()
        matrix, unused = evidence.original_matrix()
        indices, data, pointers = matrix["indices"], matrix["data"], matrix["indptr"]
        fixed_set = set(fixed)
        original_positions = [p for p, row in enumerate(indices) if row == ROW]
        independent = []
        for pos in original_positions:
            col = bisect_right(pointers, pos) - 1
            if col in fixed_set:
                continue
            fcol = bisect_left(free, col)
            require(free[fcol] == col, "independent_column_in_original_free_domain")
            independent.append((col, fcol, pos, data[pos]))
        actual = packet["ordered_original_free_row_entries"]
        require(len(actual) == len(independent) == packet["ordered_support_size"], "independent_original_row_support")
        require(packet["original_Kff_buffer_hashes_verified"] == KFF_COMPONENTS, "producer_Kff_hashes_match_original_record")
        for item, (col, fcol, pos, coefficient) in zip(actual, independent):
            require(item["original_column_DOF"] == col and item["free_column_index"] == fcol
                    and item["original_CSC_data_position"] == pos, "independent_CSC_column_position")
            check_scalar(item["coefficient"], coefficient)
            affected = [p for p in range(pointers[col], pointers[col + 1]) if indices[p] not in fixed_set]
            require(item["affected_original_free_row_DOFs"] == [indices[p] for p in affected]
                    and item["affected_free_rows_in_original_column"] == len(affected)
                    and item["maximum_absolute_free_column_coefficient"] == max(abs(data[p]) for p in affected),
                    "independent_original_column_effective_rows")
        coefficients = [x[3] for x in independent]
        cols = [x[0] for x in independent]
        fcols = [x[1] for x in independent]
        at = bisect_left(free, ROW)
        require(at == packet["original_row_free_index"], "independent_target_free_index")
        report = evidence.read_json("probe-N5/report.engineering.json")["selected_engineering_fields"]
        rhs = evidence.npy("probe-N5/five-probe-rhs.npy", (ND, 5))
        diagonal = evidence.npy("probe-N5/original-diagonal.npy", (NF,))
        require(len(packet["states"]) == 38, "independent_38_states")
        matched = []
        previous = previous_residual = final_values = final_exact = None
        final_float = None
        for index, state in enumerate(packet["states"]):
            probe = state["probe_index"]
            if index == 0:
                expected_field = "probe-N5/probe-0-baseline-field.npy"
                expected_residual = "probe-N5/probe-0-baseline-residual.npy"
                expected_report = report["baseline_probes"][0]
                require(probe == 0 and state["label"] == "probe-0-baseline", "independent_baseline_order")
            elif index <= 32:
                history = report["refined_probes"][0]["iterations"][index - 1]
                expected_field = "probe-N5/" + history["field_file"]
                expected_residual = "probe-N5/" + history["residual_file"]
                expected_report = history["equation_residual"]
                require(probe == 0 and state["label"] == f"probe-0-outer-{index:02d}", "independent_history_order")
            else:
                require(probe == index - 33 and state["label"] == f"probe-{probe}-final", "independent_final_order")
                expected_field = f"probe-N5/probe-{probe}-final-field.npy"
                expected_residual = f"probe-N5/probe-{probe}-final-residual.npy"
                expected_report = report["refined_probes"][probe]["final_original_residual"]
            require(state["field_member"] == expected_field and state["residual_member"] == expected_residual, "independent_original_member_binding")
            field = evidence.npy(expected_field, (ND,))
            residual = evidence.npy(expected_residual, (NF,))
            values = [field[g] for g in cols]
            require(state["ordered_support_values_hex"] == [x.hex() for x in values], "independent_full_field_row_values")
            b = rhs[ROW * 5 + probe]
            check_scalar(state["original_row_RHS"], b)
            check_scalar(state["stored_original_native_row_residual"], residual[at])
            computed, exact = independently_check_arithmetic(state["row_arithmetic"], coefficients, values, b)
            same = bits(computed) == bits(residual[at])
            matched.append(same)
            require(state["sequential_row_replays_stored_native_bitpattern"] is same, "independent_actual_order_match_boolean")
            denominator = max(max(abs(rhs[g * 5 + probe]) for g in free), 1.0)
            maximum_index, maximum = max(enumerate(residual), key=lambda pair: abs(pair[1]))
            row = state["full_stored_residual_reduction"]
            require(row["numerator"] == abs(maximum) and row["denominator"] == denominator
                    and row["ratio"] == abs(maximum) / denominator == expected_report["free_dof_residual_infinity_ratio"]
                    and row["max_original_DOF"] == free[maximum_index] == expected_report["max_residual_original_dof"]
                    and row["signed_maximum"] == maximum
                    and row["above_original_gate_row_count"] == sum(abs(x) / denominator > LIMIT for x in residual),
                    "independent_whole_stored_residual_reduction")
            top = sorted(range(NF), key=lambda i: abs(residual[i]), reverse=True)[:32]
            require(row["top_32_rows"] == [{"original_DOF": int(free[i]), "signed_residual": residual[i],
                                            "ratio": abs(residual[i]) / denominator} for i in top], "independent_top_stored_rows")
            if 1 <= index <= 32:
                requested = evidence.npy("probe-N5/" + history["local_return"]["field_file"], (ND,))
                actual_delta = evidence.npy("probe-N5/" + history["actual_update_file"], (ND,))
                require(len(state["support_updates"]) == len(cols), "independent_all_support_updates")
                for j, rec in enumerate(state["support_updates"]):
                    g, old, new, correction = cols[j], previous[j], values[j], requested[cols[j]]
                    require(rec["original_DOF"] == g and rec["before_hex"] == old.hex()
                            and rec["after_hex"] == new.hex() and rec["requested_hex"] == correction.hex()
                            and rec["actual_update_hex"] == actual_delta[g].hex(), "independent_update_source_values")
                    require(bits(old + correction) == bits(new) and bits(new - old) == bits(actual_delta[g])
                            and bits((-previous_residual[fcols[j]] / diagonal[fcols[j]]) * report["damping"]["omega"]) == bits(correction),
                            "independent_exact_support_correction_and_actual_update")
                    require(rec["ULP_distance"] == ulps(old, new) and rec["changed"] is (old != new)
                            and rec["nonzero_request_rounded_to_no_change"] is (correction != 0.0 and old == new), "independent_ULP_quantization")
                require(state["changed_support_DOFs"] == sum(x["changed"] for x in state["support_updates"])
                        and state["rounded_away_nonzero_support_requests"] == sum(x["nonzero_request_rounded_to_no_change"] for x in state["support_updates"]),
                        "independent_support_change_counts")
                result["support_update_chains_checked"] += 1
            if index == 33:
                require(values == previous, "independent_final_is_original_step_32")
                final_values, final_exact, final_float = values, exact, computed
            if index >= 33:
                require(packet["five_original_final_stored_residuals"][probe] == row, "independent_five_stored_summary_binding")
                if probe > 0:
                    baseline_identity = evidence.byte_check(f"probe-N5/probe-{probe}-baseline-field.npy")
                    require(baseline_identity == evidence.used[expected_field], "independent_four_passing_files_unchanged")
            previous, previous_residual = values, residual
            result["states_checked"] += 1
        require(packet["all_38_retained_states_replay_original_row_bitpattern"] is all(matched), "independent_all_row_replay_state")
        trials = packet["all_row_only_adjacent_ULP_trials"]
        require(len(trials) == (2 * len(cols) if all(matched) else 0), "independent_finite_trial_count")
        denominator = report["refined_probes"][0]["final_original_residual"]["normalization_denominator"]
        b = rhs[ROW * 5]
        ld = report["refined_probes"][0]["iterations"][-1]["longdouble_equation_residual_ratio_diagnostic_only"]
        for t in trials:
            i = result["row_only_trials_checked"]
            j, direction = i // 2, (-1 if i % 2 == 0 else 1)
            u = final_values[j]
            value = math.nextafter(u, -math.inf if direction < 0 else math.inf)
            require(t["trial_index"] == i and t["support_index"] == j and t["direction"] == direction
                    and t["original_free_column_DOF"] == cols[j] and t["old_value_hex"] == u.hex()
                    and t["adjacent_value_hex"] == value.hex() and t["delta_hex"] == (value - u).hex()
                    and t["actual_ULP_distance"] == ulps(value, u) == 1, "independent_adjacent_trial")
            accum = 0.0
            for k, a in enumerate(coefficients):
                accum += a * (value if k == j else final_values[k])
            r = accum - b
            exact_delta = F(coefficients[j]) * (F(value) - F(u))
            ex = final_exact + exact_delta
            check_scalar(t["row_float64_residual"], r)
            equal_rational(t["exact_original_equation_row_residual"], ex)
            equal_rational(t["exact_row_residual_change"], exact_delta)
            require(t["row_ratio"] == abs(r) / denominator
                    and t["row_only_original_gate_passes"] is (abs(r) / denominator <= LIMIT)
                    and t["row_absolute_float64_residual_improves"] is (abs(r) < abs(final_float))
                    and t["exact_row_error_does_not_increase"] is (abs(ex) <= abs(final_exact)), "independent_row_only_trial_criteria")
            require(t["recorded_longdouble_plus_column_delta_ratio_estimate"] == ld + actual[j]["maximum_absolute_free_column_coefficient"] * abs(value - u) / denominator
                    and t["estimate_is_not_certified_bound_or_acceptance"] is True
                    and t["full_native_float64_gate_evaluated"] is False
                    and t["candidate_field_created_or_accepted"] is False, "independent_no_full_gate_claim")
            result["row_only_trials_checked"] += 1
        sensitivity = packet["sensitivity"]
        require(sensitivity["finite_registered_trial_count"] == 2 * len(cols)
                and sensitivity["actual_trial_count"] == len(trials)
                and sensitivity["disabled_if_original_row_replay_mismatch"] is (not all(matched))
                and sensitivity["row_only_float64_improvement_count"] == sum(t["row_absolute_float64_residual_improves"] for t in trials)
                and sensitivity["row_only_float64_pass_count"] == sum(t["row_only_original_gate_passes"] for t in trials)
                and sensitivity["row_only_pass_and_exact_row_error_nonincrease_count"] == sum(t["row_only_original_gate_passes"] and t["exact_row_error_does_not_increase"] for t in trials)
                and sensitivity["new_iteration_or_search_strategy_execution_authorized_by_this_audit"] is False,
                "independent_sensitivity_summary_counts")
        require(all(evidence.members.get(n) == identity for n, identity in packet["used_original_member_identities"].items()), "producer_used_member_bindings")
        require(all(packet["used_original_member_identities"].get(n) == identity for n, identity in evidence.used.items()), "reader_used_member_bindings")
        result.update(completed=True, all_original_row_bitpatterns_match=all(matched),
                      original_row_support_size=len(cols), original_free_support_proven=True,
                      all_exact_rounding_components_recomputed=True, all_row_only_trials_recomputed=True,
                      used_original_member_identities=evidence.used)
        return_code = 0
    except BaseException as e:
        result["failure_type"] = type(e).__name__
        if isinstance(e, AuditGateError):
            result["failure_gate"] = str(e)
        return_code = 2
    finally:
        if evidence is not None:
            evidence.close()
        result["elapsed_seconds"] = time.monotonic() - started
        result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "used_original_member_identities"}, indent=2))
    return return_code


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--matrix", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--worker", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(p.parse_args()))
