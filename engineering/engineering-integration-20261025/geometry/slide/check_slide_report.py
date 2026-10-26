"""Read a saved full SLIDE diagnostic using pure arithmetic/source checks only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import verify_slide_native as worker
import slide_evidence as e


def check(path, expected_head):
    e.require(Path(__file__).resolve() == e.HERE/'check_slide_report.py',
              'executed independent reader differs from its explicit source-bound path')
    path = path.resolve()
    raw_sha = worker.sha(path)
    sources = worker.source_identity()
    current = e.postguard.current_identity(e.ROOT, expected_head)
    report = json.loads(path.read_text())
    e.require(report.get('schema') == 'razr-full-nominal-slide-native-diagnostic-v1'
              and report.get('expected_head') == expected_head, 'wrong saved report schema or source HEAD')
    contract = e.contract_from_report(report)
    result = e.complete_result(report, contract, current, sources)
    e.require(worker.sha(path) == raw_sha and worker.source_identity() == sources
              and e.postguard.current_identity(e.ROOT, expected_head) == current,
              'report or current source/runtime changed during independent readback')
    CAD = any(name == 'cadquery' or name == 'OCP' or name.startswith('OCP.') for name in sys.modules)
    e.require(not CAD, 'independent raw reader unexpectedly imported CAD')
    return {'schema': 'razr-saved-slide-diagnostic-independent-check-v1',
            'report': str(path), 'report_sha256': raw_sha, 'expected_head': expected_head,
            'native_geometry_recomputed_by_reader': False, 'CAD_imported': CAD,
            'raw_count_values_and_scope_recomputed': True, 'scratch_source_sha256': sources,
            **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    e.require(not args.output.exists() and not args.output.resolve().is_relative_to(e.ROOT),
              'new independent readback output outside frozen repository required')
    result = check(args.report, args.expected_head)
    worker.atomic_json(args.output, result)
    print(json.dumps({key: result[key] for key in ('complete_native_diagnostic_executed',
                     'whole_declared_slide_external_pair_domain_clear', 'raw_evidence_validation_failure_count',
                     'evaluation_failure_count', 'pending_pair_count')}))
    return 0 if result['complete_native_diagnostic_executed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
