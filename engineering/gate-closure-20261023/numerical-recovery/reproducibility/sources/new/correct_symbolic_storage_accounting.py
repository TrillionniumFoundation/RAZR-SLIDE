"""Preserve executed symbolic receipts and correct the L/U storage labels.

This performs arithmetic on source-bound symbolic counts only.  It does not
repeat symbolic elimination, numeric factorization, or alter previous receipts.
"""
from pathlib import Path
import hashlib
import json

BASE = Path(__file__).resolve().parent
PRIVATE = Path('/tmp/razr-fe-20261023')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    results = []
    for name in ('symbolic-panel-v2', 'symbolic-frame-v2',
                 'symbolic-frame-v2-fixed'):
        path = PRIVATE / name / 'report.json'
        report = json.loads(path.read_text())
        assert report['completed'] is True
        assert report['numeric_factorization_executed'] is False
        n = 3 * report['scalar_nodes']
        lower = report.get('block_L_nnz_after_removing_fully_fixed_nodes',
                           report.get('full_unconstrained_block_L_nnz_upper_bound'))
        old_union = report.get('symmetric_L_plus_U_nnz_after_removing_fully_fixed_nodes',
                               report.get('symmetric_L_plus_U_nnz_upper_bound_before_fixed_DOF_removal'))
        assert old_union == 2 * lower - n
        assert lower == 9 * (report['symbolic_scalar_L_nnz_including_diagonal']
                             - report['scalar_nodes']) + 6 * report['scalar_nodes']
        factor_entries = 2 * lower
        # Two CSC factors, float64 values, int32 row indices and indptr.
        # This counts both diagonal copies.  It is a storage estimate for
        # these symbolic patterns, not a bound on SuperLU's allocation peak.
        arrays = 12 * factor_entries + 8 * (n + 1)
        results.append({
            'original_report': str(path),
            'original_report_sha256': sha(path),
            'body': report['body'],
            'scalar_nodes_counted': report['scalar_nodes'],
            'vector_rows_counted': n,
            'block_lower_factor_nnz_including_diagonal': lower,
            'old_count_is_L_U_structural_union_with_diagonal_once': old_union,
            'separate_L_and_U_array_entries_with_two_diagonals': factor_entries,
            'separate_float64_int32_CSC_array_storage_bytes': arrays,
            'old_array_estimate_bytes': report['float64_plus_int32_LU_array_bytes_upper_bound'],
            'increase_from_double_diagonal_accounting_bytes': 12 * n,
            'fixed_scalar_nodes_removed': report.get('removed_fully_fixed_nodes', 0),
            'remaining_partial_fixed_nodes': report.get('remaining_partial_fixed_nodes'),
            'exact_free_block_pattern': report.get('exact_free_block_pattern_if_zero_partial_nodes', False),
            'pivoting_or_numerical_cancellation_modeled': False,
            'SuperLU_RSS_or_address_space_peak_predicted': False,
        })
        assert arrays - report['float64_plus_int32_LU_array_bytes_upper_bound'] == 12 * n
    output = BASE / 'symbolic-storage-accounting-correction.json'
    assert not output.exists()
    result = {
        'schema': 'razr-symbolic-storage-accounting-correction-v1',
        'source_path': str(Path(__file__).resolve()),
        'source_sha256': sha(__file__),
        'previous_executed_reports_and_sources_preserved': True,
        'correction': 'Old 2*L-n fields count the structural union; separate L/U arrays count 2*L including both diagonals.',
        'symbolic_or_numeric_factorization_executed': False,
        'estimates_do_not_justify_running_the_larger_ND_factors': True,
        'results': results,
    }
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'receipt': str(output), 'sha256': sha(output),
                      'entries': [{k: r[k] for k in ('body', 'separate_L_and_U_array_entries_with_two_diagonals',
                          'separate_float64_int32_CSC_array_storage_bytes')} for r in results]}))


if __name__ == '__main__':
    main()
