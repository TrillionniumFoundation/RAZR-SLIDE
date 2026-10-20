"""Compare the extracted law with the frozen PR25 source, without adopting it.

The reference file is supplied explicitly and SHA-pinned; no network or large FE
job is started. Tiny discrete examples test constitutive semantics only.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'integration'))
from slack_spring_contact import solve_tension_contact

REFERENCE_SHA256 = 'c1bdefebf5ab98e1c0173c050459deca4ad49d59ae90f78f5f3b41608b25e195'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pr25-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if digest(args.pr25_source) != REFERENCE_SHA256:
        parser.error('reference is not the pinned PR25 integration/spatial_contact.py')
    spec = importlib.util.spec_from_file_location('pr25_retained_reference', args.pr25_source)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    h = [[2., .3, -.2], [.3, 1.5, .2], [-.2, .2, 1.]]
    cases = [
        ('positive_spring', ([[2.]], np.zeros((1, 0)), [.5], [], [3.], [.4], [])),
        ('released_spring', ([[2.]], np.zeros((1, 0)), [-2.], [], [3.], [.4], [])),
        ('independent_springs', (np.zeros((2, 2)), np.ones((2, 1)), [0., 0.], [3.], [1., 2.], [0., 0.], [])),
        ('contact_stop', ([[2.]], np.zeros((1, 0)), [.6], [], [], [], [.2])),
        ('duplicate_contact', (np.ones((2, 2)), np.zeros((2, 0)), [1., 1.], [], [], [], [0., 0.])),
    ]
    for i, q in enumerate(([.3, -.9, .8], [-2., 1., -.3], [.8, .2, .4])):
        cases.append((f'coupled_{i}', (h, [[1.], [1.], [-1.]], q, [.4], [.5, 2.], [.1, .3], [.1])))
    rows = []
    start = time.monotonic()
    for name, data in cases:
        old, new = reference.solve_reactions(*data), solve_tension_contact(*data)
        assert old['passed'] and new['passed'], (name, old, new)
        # Individual multipliers need not be unique for identical contact rows.
        old_force, new_force = np.array(old['forces']), np.array(new['forces'])
        residual = float(np.max(abs(old_force-new_force)))
        if name == 'duplicate_contact':
            residual = float(abs(old_force.sum()-new_force.sum()))
        assert residual < 1e-9, (name, residual)
        rows.append({'case': name, 'reference_forces': old['forces'], 'adapter_forces': new['forces'],
                     'comparison_error': residual, 'adapter_spring_slacks': new['spring_constitutive_slacks'],
                     'both_discrete_kkt_passed': True})
    rigid_stop = ([[0.]], [[1.]], [0.], [2.], [], [], [.02])
    old = reference.solve_reactions(*rigid_stop)
    assert old['passed']
    try:
        solve_tension_contact(*rigid_stop)
    except ValueError as error:
        unsupported = str(error)
    else:
        raise AssertionError('zero-response limitation changed; review declared scope')
    sources = ['integration/slack_spring_contact.py', 'integration/contact_dual_active.py',
               'integration/rank_fallback.py', str(Path(__file__).relative_to(ROOT))]
    report = {'scope': 'eight_tiny_discrete_constitutive_examples_and_one_explicit_scope_difference',
              'reference_commit': '44a5830f49af73605d5161efff80e6744b0fb468',
              'reference_source_sha256': REFERENCE_SHA256,
              'current_backend_base_commit': 'a1b3cc1e0773446f2e36d0a607edf61211dd9919',
              'source_sha256': {p: digest(ROOT/p) for p in sources}, 'cases': rows,
              'intentional_scope_difference': {'case': 'zero_response_rigid_stop',
                  'pr25_passed': True, 'adapter_rejected': True, 'reason': unsupported},
              'wall_seconds': time.monotonic()-start,
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
              'pr25_full_body_driver_or_results_adopted': False,
              'new_fe_solve': False, 'candidate_go': False,
              'fixture_fabrication_go': False, 'manufacturing_go': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write('\n')
    print(json.dumps({'passed_cases': len(rows), 'intentional_scope_differences': 1,
                      'seconds': report['wall_seconds']}))


if __name__ == '__main__':
    main()
