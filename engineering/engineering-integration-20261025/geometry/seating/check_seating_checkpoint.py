"""Pure saved-evidence reader: a JSONL prefix never grants a complete domain."""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
import sys

import seating_checkpoint as checkpoint
import seating_domain as domain
import verify_seating_native as worker

require = checkpoint.require
FALSE_SCOPE_FLAGS = ('whole_declared_seating_domain_clear', 'canonical_execution_checks_passed',
                     'complete_G2_qualification', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go')
SCENE_FALSE_FLAGS = ('physical_holding_and_force_qualified', 'OPEN_thread_retention_load_qualified',
                     'loose_OPEN_accessories_have_onboard_storage', 'complete_functional_phone',
                     'candidate_go', 'manufacturing_go', 'fixture_fabrication_go',
                     'whole_phone_installation_order_verified', 'joining_tool_access_with_whole_housing_verified',
                     'physical_joint_retention_qualified', 'physical_prototype_exists')


def scalar_equal(value, expected):
    return worker.postguard.finite(value) and value == expected


def vector_equal(value, expected):
    return (isinstance(value, list) and len(value) == len(expected)
            and all(scalar_equal(actual, wanted) for actual, wanted in zip(value, expected)))


def controls_valid(controls):
    require(isinstance(controls, dict) and set(controls) == {'seconds', 'minimum_available_disk_mib',
            'maximum_rss_mib', 'maximum_pair_calls', 'maximum_subdivision_depth'}, 'missing execution limits')
    require(worker.postguard.finite(controls['seconds']) and 0 < controls['seconds'] <= 1800,
            'worker wall-time budget exceeds the original bound')
    require(type(controls['minimum_available_disk_mib']) is int and controls['minimum_available_disk_mib'] >= 300,
            'worker disk reserve was reduced')
    for key, maximum in (('maximum_rss_mib', 1536), ('maximum_pair_calls', 20000)):
        require(type(controls[key]) is int and 0 < controls[key] <= maximum, 'worker resource bound increased')
    require(type(controls['maximum_subdivision_depth']) is int and 0 <= controls['maximum_subdivision_depth'] <= 3,
            'subdivision budget differs from the original controller')


def context_for(current, sources, controls):
    controls_valid(controls)
    return checkpoint.context_record(current['repository_head'], domain.domain_record(),
        worker.expected_inventory(), sources, current, controls)


def recursive_pending(value):
    if isinstance(value, dict):
        count = int(value.get('disposition') in ('not_evaluated', 'unresolved_budget', 'unresolved_evaluation'))
        return count + sum(recursive_pending(item) for item in value.values() if isinstance(item, (dict, list)))
    if isinstance(value, list):
        return sum(recursive_pending(item) for item in value)
    return 0


def construction_valid(report, laws):
    require(report.get('construction_completed') is True and report.get('native_checks_executed') is True,
            'whole-material construction was not completed')
    probes = report.get('construction_probes')
    require(isinstance(probes, list) and len(probes) == 3, 'three original rigid-law construction checks required')
    for row, descent in zip(probes, (F('2.6'), F('4.1'), F('8.2'))):
        vertices = domain.joints_at(descent)
        allocations = {'L': list(map(float, vertices[0])), 'R': list(map(float, vertices[-1]))}
        actual = row.get('joints_by_side_mm')
        require(scalar_equal(row.get('descent_mm'), float(descent))
                and isinstance(actual, dict) and set(actual) == {'L', 'R'}
                and all(vector_equal(actual[side], allocations[side]) for side in 'LR')
                and vector_equal(row.get('flanks'), [-.4, .65])
                and type(row.get('rigid_materials_checked')) is int and row['rigid_materials_checked'] == len(laws),
                'construction check differs from the original source-owned states')
        difference = row.get('maximum_bidirectional_material_difference_mm3')
        require(worker.postguard.finite(difference) and 0 <= difference <= worker.TOL
                and row.get('complete_factory_reconstructed_including_both_flexible_bodies') is True
                and row.get('samples_do_not_establish_continuous_law') is True,
                'construction evidence has an invalid material difference or scope')
    metadata = report.get('native_scene_metadata')
    require(isinstance(metadata, dict) and all(type(metadata.get(key)) is int and metadata[key] == expected
            for key, expected in (('combined_participants', 154), ('mechanical_participants', 108),
                                  ('candidate_participants', 41))),
            'complete native material metadata differs')
    scene = metadata.get('scene', {})
    require(isinstance(scene, dict) and scene.get('factory') == 'integration/product_split_assembly.py:split_scene'
            and scene.get('parent_factory') == 'integration/product_assembly.py:product_scene'
            and all(scalar_equal(scene.get(key), expected) for key, expected in
                    (('slide_mm', 79.75), ('descent_mm', 0.), ('left_tab_mm', 3.), ('right_tab_mm', 3.)))
            and type(scene.get('installed_mechanical_parts')) is int and scene['installed_mechanical_parts'] == 108
            and type(scene.get('expected_scene_participants')) is int and scene['expected_scene_participants'] == 108
            and scene.get('OPEN_hold_screws_installed') is False
            and scene.get('OPEN_display_support_insert_installed') is False,
            'actual base must be the released-tab SEATING scene, not an unreleased control pose')
    require(all(vector_equal(scene.get(key), [0., 0.]) for key in
                ('slot_flanks', 'KEY_offsets_mm', 'crosshead_offsets_mm'))
            and vector_equal(scene.get('B_translation_mm'), [0., 79.75, 8.2]),
            'base flank/KEY/crosshead/B controls differ from the exact source-owned reference')
    # native_scene computes q = cam.K * slide + KEY offset; the source-bound
    # slide 79.75 and zero offsets select q=12 without inventing a q metadata key.
    joints = scene.get('telescope_offsets_by_side_mm')
    require(isinstance(joints, dict) and set(joints) == {'L', 'R'}
            and all(vector_equal(joints[side], [float(domain.REFERENCE_JOINT)] * 3) for side in 'LR')
            and scene.get('telescope_allocation') == 'explicit admissible joint allocation',
            'base telescope controls differ from the actual explicit equal reference allocation')
    for key in SCENE_FALSE_FLAGS:
        require(scene.get(key) is False, 'factory metadata overclaims physical/product scope: ' + key)


def factory_payload_valid(scene, current):
    """Preserve the original canonical reader's complete payload contract."""
    declared = scene.get('source_inputs')
    require(isinstance(declared, dict) and declared and type(scene.get('archive')) is str,
            'factory payload identity absent')
    declared = {**declared, scene['archive']: scene.get('archive_sha256')}
    payloads = {name for name in current['head_bound_source_sha256']
                if name.startswith('engineering/') and not name.endswith('.py')}
    require(set(declared) == payloads, 'factory payload inventory is incomplete or changed')
    require(not scene.get('external_verified_source_inputs'), 'external factory overlay cannot pass the source guard')
    for name, digest in declared.items():
        require(type(name) is str and name in current['head_bound_source_sha256']
                and current['head_bound_source_sha256'][name] == digest, 'factory payload differs from HEAD: ' + str(name))


def complete_result(report, publication, current, sources):
    require(report.get('schema') == 'razr-complete-seating-native-diagnostic-v2'
            and report.get('expected_head') == current['repository_head'], 'saved report schema or HEAD differs')
    require(report.get('identity_before') == report.get('identity_after') == current,
            'actual before/after source/input/runtime differs from the current exact identity')
    require(report.get('adapter_source_sha256_before') == report.get('adapter_source_sha256_after') == sources,
            'scratch source identity differs')
    require(checkpoint.normalized(report.get('domain')) == checkpoint.normalized(domain.domain_record()),
            'complete shared-descent domain differs')
    require(all(report.get(key) is False for key in FALSE_SCOPE_FLAGS), 'saved report overclaims native or physical scope')
    names = worker.expected_inventory()
    require(report.get('complete_participant_names') == names and report.get('participant_count') == 154,
            'complete 154-part inventory differs')
    half = report.get('native_slot_halfwidth_mm')
    require(isinstance(half, dict) and set(half) == {'L', 'R'}, 'original native slot measurements missing')
    laws = domain.rigid_laws(names, half, names)
    require(report.get('rigid_Z_laws') == {name: law.record() for name, law in sorted(laws.items())},
            'source-owned rigid Z laws differ')
    construction_valid(report, laws)
    factory_payload_valid(report['native_scene_metadata']['scene'], current)
    worker.enclosure.ep5.validate_factory_input_coverage(report['native_scene_metadata']['scene'],
                                                        current['executed_source_sha256'])
    rows = report.get('pairs')
    require(isinstance(rows, list), 'original raw pairs missing')
    pending = recursive_pending(rows)
    failed = any(key in report for key in ('execution_failure', 'resource_stop',
        'post_execution_identity_failure', 'checkpoint_write_failure', 'checkpoint_unavailable_or_failed'))
    derived = worker.check_complete_result(names, rows, current, current, sources, sources,
        True, failed or bool(pending) or not publication['all_expected_pair_records_present'], laws)
    require(report.get('pair_count') == report.get('expected_pair_count') == len(rows)
            and report.get('counts') == dict(Counter(row['disposition'] for row in rows)), 'raw pair count summary differs')
    for key in ('all_unordered_pairs_present_once', 'source_bytes_unchanged', 'evaluation_failure_count',
                'raw_evidence_validation_failure_count', 'complete_native_diagnostic_executed',
                'whole_declared_seating_external_pair_domain_clear'):
        require(report.get(key) == derived[key], 'reported final proof flag/count differs from raw evidence: ' + key)
    return {**derived, 'checkpoint_publication_chain_verified': True,
            'raw_checkpoint_pair_records': publication['journal']['completed_pair_records'],
            'recursive_pending_or_evaluation_node_count': pending,
            'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}


def inspect_prefix(path, expected_head):
    sources = worker.adapter_identity()
    current = worker.postguard.current_identity(worker.ROOT, expected_head)
    before_sha = checkpoint.sha(path)
    initial = checkpoint.read_journal(path)
    expected = context_for(current, sources, initial['context'].get('execution_limits'))
    parsed = checkpoint.read_journal(path, expected_context=expected)
    require(checkpoint.sha(path) == before_sha and worker.adapter_identity() == sources
            and worker.postguard.current_identity(worker.ROOT, expected_head) == current,
            'journal/current identity changed during stable partial readback')
    return {'schema': 'razr-seating-partial-checkpoint-inspection-v2', 'journal': str(path),
            'journal_sha256': before_sha, 'run_id': parsed['run_id'], 'context_sha256': parsed['context_sha256'],
            'complete_records': parsed['complete_records'], 'completed_pair_records': parsed['completed_pair_records'],
            'expected_pair_records': parsed['expected_pair_records'], 'truncated_tail_bytes': parsed['truncated_tail_bytes'],
            'construction_preserved': parsed['construction'] is not None,
            'interruption_preserved': parsed['interruption'] is not None,
            'postflight_preserved': parsed['postflight'] is not None,
            'final_commit_present': parsed['final_commit'] is not None,
            'complete_native_diagnostic_executed': False, 'whole_declared_seating_external_pair_domain_clear': False,
            'whole_declared_seating_domain_clear': False, 'complete_G2_qualification': False,
            'geometry_recomputed': False, 'partial_checkpoint_is_never_complete_qualification': True}


def check_report(path, expected_head):
    path = Path(path).resolve()
    require(Path(__file__).resolve() == worker.HERE / 'check_seating_checkpoint.py', 'reader executable path differs')
    sources = worker.adapter_identity()
    current = worker.postguard.current_identity(worker.ROOT, expected_head)
    before_sha = checkpoint.sha(path)
    raw = checkpoint.parse(path.read_bytes())
    expected = context_for(current, sources, raw.get('execution_limits'))
    publication = checkpoint.validate_published(path, expected_context=expected)
    result = complete_result(publication['report'], publication, current, sources)
    require(checkpoint.sha(path) == before_sha and worker.adapter_identity() == sources
            and worker.postguard.current_identity(worker.ROOT, expected_head) == current,
            'report/current identity changed during independent saved readback')
    require(not any(name == 'cadquery' or name == 'OCP' or name.startswith('OCP.') for name in sys.modules),
            'saved readback unexpectedly imported CAD')
    return {'schema': 'razr-seating-v2-saved-complete-report-check', 'report': str(path),
            'report_sha256': before_sha, 'expected_head': expected_head,
            'journal_sha256': publication['journal']['journal_sha256'],
            'scratch_source_sha256': sources, 'geometry_recomputed': False, 'CAD_imported': False, **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--report', type=Path)
    source.add_argument('--journal', type=Path)
    parser.add_argument('--expected-head', default=worker.DEFAULT_HEAD)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    require(not args.output.exists() and not args.output.resolve().is_relative_to(worker.ROOT),
            'new readback result outside the frozen repository required')
    result = check_report(args.report, args.expected_head) if args.report else inspect_prefix(args.journal, args.expected_head)
    checkpoint.atomic_bytes(args.output, json.dumps(result, indent=2, allow_nan=False).encode() + b'\n')
    print(json.dumps({key: result.get(key) for key in ('schema', 'completed_pair_records',
        'raw_checkpoint_pair_records', 'complete_native_diagnostic_executed',
        'whole_declared_seating_external_pair_domain_clear')}))
    return 0 if result.get('complete_native_diagnostic_executed') else 2


if __name__ == '__main__':
    raise SystemExit(main())
