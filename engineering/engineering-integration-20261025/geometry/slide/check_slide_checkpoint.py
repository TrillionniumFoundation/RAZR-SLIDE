"""Independently read durable SLIDE evidence without native geometry or resume.

An intact prefix only identifies which pairs started and which raw completions
were recorded. A complete diagnostic additionally requires the full report,
final commit, atomic index, original geometric reader, source and lock checks.
"""
from __future__ import annotations

import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import sys

import slide_checkpoint as checkpoint
import slide_evidence as evidence
import verify_slide_native as worker
import check_slide_report as original_reader


def source_state(expected_head):
    evidence.require(Path(__file__).resolve() == evidence.HERE/'check_slide_checkpoint.py',
                     'executed checkpoint reader differs from its declared source path')
    evidence.require(Path(original_reader.__file__).resolve() == evidence.HERE/'check_slide_report.py',
                     'executed original raw reader differs from its declared source path')
    return (worker.source_identity(), evidence.postguard.current_identity(evidence.ROOT, expected_head))


def expected_context(expected_head, sources, identity, limits, report_filename):
    evidence.require(isinstance(limits, dict), 'source-owned execution limits missing')
    depth = limits.get('maximum_subdivision_depth')
    evidence.require(limits == worker.execution_limits(depth), 'execution limits differ from the original bounds')
    evidence.require(type(report_filename) is str and Path(report_filename).name == report_filename
                     and report_filename not in ('', '.', '..', 'pairs.jsonl', 'checkpoint-index.json'),
                     'same-directory report filename required')
    names = evidence.expected_names()
    rows = [{'a': a, 'b': b} for a, b in itertools.combinations(names, 2)]
    return checkpoint.context_record(expected_head, evidence.recorded_domain(evidence.original_profiles()),
        names, worker.pair_visit_order(rows), sources, identity, limits, report_filename)


def validate_pair_classes(journal):
    for row in journal['pair_starts']:
        evidence.require(row['pair_class'] == evidence.pair_class(row['a'], row['b']),
                         'started pair class differs from the complete material inventory')


def require_stable(expected_head, sources, identity, files):
    evidence.require(all(checkpoint.sha(path) == digest for path, digest in files.items()),
                     'saved evidence bytes changed during independent readback')
    evidence.require(source_state(expected_head) == (sources, identity),
                     'current source or locked runtime changed during independent readback')
    CAD = any(name == 'cadquery' or name == 'OCP' or name.startswith('OCP.') for name in sys.modules)
    evidence.require(not CAD, 'pure checkpoint reader unexpectedly imported CAD')


def inspect_prefix(journal_path, expected_head):
    """Validate a stable source-bound prefix; never qualify or resume it."""
    path = Path(journal_path).resolve()
    evidence.require(path.name == 'pairs.jsonl', 'fixed journal filename required')
    sources, identity = source_state(expected_head)
    first = checkpoint.read_journal(path, allow_truncated_tail=True)
    context = first['context']
    expected = expected_context(expected_head, sources, identity, context.get('execution_limits'),
                                context.get('report_filename'))
    evidence.require(context == expected, 'prefix source/domain/runtime context differs')
    validate_pair_classes(first)
    require_stable(expected_head, sources, identity, {path: first['journal_sha256']})
    rows = [item['raw_evidence'] for item in first['completed_pairs']]
    return {'schema': 'razr-slide-interrupted-prefix-independent-read-r3',
        'journal': str(path), 'journal_sha256': first['journal_sha256'],
        'expected_head': expected_head, 'context_sha256': first['context_sha256'],
        'run_id': first['run_id'], 'last_intact_record_sha256': first['last_record_sha256'],
        'intact_record_count': first['complete_records'],
        'completed_pair_records': first['completed_pair_records'],
        'expected_pair_records': first['expected_pair_records'],
        'completed_raw_pair_indices': [item['raw_pair_index'] for item in first['completed_pairs']],
        'recorded_disposition_counts': dict(Counter(row.get('disposition', 'absent') for row in rows)),
        'recorded_raw_evaluation_error_count': len(evidence.errors_in(rows)),
        'active_pair_start': first['active_pair_start'], 'truncated_tail_bytes': first['truncated_tail_bytes'],
        'construction_snapshot_present': first['construction'] is not None,
        'interruption_record_present': first['interruption'] is not None,
        'postflight_record_present': first['postflight'] is not None,
        'final_commit_record_present': first['final_commit'] is not None,
        'current_source_and_locked_runtime_match_context': True,
        'pair_start_proves_selection_before_evaluation_only': True,
        'raw_pair_geometry_independently_qualified_by_prefix_reader': False,
        'complete_native_diagnostic_executed': False,
        'whole_declared_slide_external_pair_domain_clear': False,
        'resume_certificate': False, 'CAD_imported': False,
        **{key: False for key in evidence.FALSE_FLAGS}}


def check_report(path, expected_head):
    """Require publication closure and then the unchanged original raw reader."""
    path = Path(path).resolve()
    sources, identity = source_state(expected_head)
    raw = checkpoint.parse(path.read_bytes())
    evidence.require(isinstance(raw, dict), 'full saved report must be an object')
    context = expected_context(expected_head, sources, identity, raw.get('execution_limits'), path.name)
    bound = checkpoint.validate_published(path, context)
    journal, report = bound['journal'], bound['report']
    validate_pair_classes(journal)
    # Retain exactly the bytes already bound by the final commit and index;
    # re-baselining a fresh digest here would absorb a post-validation edit.
    before = {Path(key): value for key, value in bound['publication_sha256'].items()}
    result = original_reader.check(path, expected_head)
    evidence.require(result.get('report_sha256') == before[path],
                     'original raw reader consumed report bytes outside the validated publication chain')
    complete = bool(bound['all_expected_pair_records_present']
                    and result.get('complete_native_diagnostic_executed') is True
                    and not report.get('checkpoint_write_failure'))
    clear = complete and result.get('whole_declared_slide_external_pair_domain_clear') is True
    evidence.require(report.get('complete_native_diagnostic_executed') is complete
                     and report.get('whole_declared_slide_external_pair_domain_clear') is clear,
                     'producer completion/clear claim differs from independent publication and raw checks')
    require_stable(expected_head, sources, identity, before)
    return {**result, 'schema': 'razr-slide-journal-and-raw-independent-check-r3',
        'checkpoint_publication_chain_verified': True,
        'original_geometric_and_source_postguard_executed': True,
        'completed_pair_records': journal['completed_pair_records'],
        'expected_pair_records': journal['expected_pair_records'],
        'active_pair_start': journal['active_pair_start'],
        'checkpoint_context_sha256': journal['context_sha256'], 'checkpoint_run_id': journal['run_id'],
        'publication_sha256': {str(key): value for key, value in before.items()},
        'all_expected_pair_records_present': bound['all_expected_pair_records_present'],
        'complete_native_diagnostic_executed': complete,
        'whole_declared_slide_external_pair_domain_clear': clear,
        'resume_certificate': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--report', type=Path)
    inputs.add_argument('--prefix', type=Path)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    evidence.require(not args.output.exists() and not args.output.resolve().is_relative_to(evidence.ROOT),
                     'new independent receipt outside the frozen repository required')
    result = (check_report(args.report, args.expected_head) if args.report is not None
              else inspect_prefix(args.prefix, args.expected_head))
    worker.atomic_json(args.output, result)
    print(json.dumps({key: result[key] for key in ('completed_pair_records', 'expected_pair_records',
                     'complete_native_diagnostic_executed', 'resume_certificate')}))
    return 0 if args.prefix is not None or result['complete_native_diagnostic_executed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
