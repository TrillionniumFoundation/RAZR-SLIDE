"""Inspect one immutable K3FULL engineering ZIP in memory, without CAD.

The inspector binds a declared run/head and frozen source plan.  Missing native
reports remain incomplete.  Evaluated geometry rejection, unevaluated gates,
and producer/reader disagreement are separate outcomes.  No workflow exit code
is used as scientific clearance, and no private raw runtime is reconstructed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import itertools
import json
import math
from pathlib import Path, PurePosixPath
import stat
import sys
import urllib.request
import zipfile

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TOL = 1e-7
LIMITS = {'wall_seconds': 1200, 'worker_peak_RSS_MiB': 1536,
          'shared_unreclaimable_GiB': 6.8, 'runtime_disk_reserve_MiB': 100,
          'startup_disk_reserve_MiB': 256, 'startup_additional_memory_MiB': 2048}
FALSE_FLAGS = ('complete_product_motion_proved', 'continuous_backlash_domain_proved',
               'physical_qualification', 'candidate_go', 'fixture_fabrication_go',
               'manufacturing_go', 'G2_pass')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def finite_volume(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def material_equal(values):
    return isinstance(values, dict) and bool(values) and all(
        finite_volume(x) and x <= TOL for x in values.values())


def inspect(data, meta, pose, run_id, head_sha, plan, k3_binding_bytes, k1_binding_bytes):
    """Return small derived records and exact manifests/observation originals."""
    require(pose in plan['states'], 'undeclared finite state')
    require(meta['name'] == f'S4-K3FULL-{pose}-{run_id}-1-engineering', 'artifact name differs')
    require(meta['workflow_run']['id'] == run_id and meta['workflow_run']['head_sha'] == head_sha,
            'official artifact run or source head differs')
    require(len(data) == meta['size_in_bytes'] and 'sha256:' + sha(data) == meta['digest'],
            'official ZIP length or SHA differs')
    spec = dict(plan['states'][pose])
    expected_bodies = spec.pop('expected_bodies')
    expected_q = dict(zip('LR', spec.pop('actual_binary64_q_from_declared_factory_inputs')))
    contacts = plan['expected_contact_end_by_side'][pose]
    expected_gates = 12 + 3 * sum(x is not None for x in contacts.values())
    expected_count = expected_bodies * (expected_bodies - 1) // 2
    k3_binding = json.loads(k3_binding_bytes)
    require(sha(k3_binding_bytes) == plan['actual_dual_pilot_binding_sha256'], 'actual K3 binding differs')
    require(sha(k1_binding_bytes) == k3_binding['original_K1_binding_sha256'], 'actual K1 binding differs')
    reports, wrappers, controllers, results, prerequisites = {}, {}, {}, {}, {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        names = [x.filename for x in infos]
        require(len(names) == len(set(names)), 'duplicate ZIP member')
        require(all(not x.is_dir() and not stat.S_ISLNK(x.external_attr >> 16) for x in infos),
                'nonregular ZIP member')
        require(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
                    and '\\' not in n and str(PurePosixPath(n)) == n for n in names), 'unsafe ZIP path')
        manifest_bytes = z.read('ENGINEERING_MANIFEST.json')
        manifest = json.loads(manifest_bytes)
        require(manifest['schema'] == 'razr-K3FULL-engineering-export-manifest-v1', 'manifest schema differs')
        members = manifest['members']
        require(set(names) == set(members) | {'ENGINEERING_MANIFEST.json'}, 'exact ZIP member set differs')
        for rel, ref in members.items():
            raw = z.read(rel)  # Includes ZIP CRC verification for every original.
            require(len(raw) == ref['bytes'] and sha(raw) == ref['sha256'], 'member SHA or length differs: ' + rel)
        for name, ref in plan['sources'].items():
            require(members.get('source/k3full/' + name) == ref, 'frozen full-campaign source differs: ' + name)
        require(z.read('source/k3full/K3FULL_K3_BINDING.json') == k3_binding_bytes
                and z.read('source/k3full/K3FULL_K1_BINDING.json') == k1_binding_bytes,
                'actual prerequisite binding source bytes differ')
        for old_pose in ('stow_tabs_3', 'predock'):
            prefix = 'prerequisite-' + old_pose + '/'
            rel = prefix + 'ENGINEERING_MANIFEST.json'
            if rel not in members:
                prerequisites[old_pose] = {'original_manifest_present': False,
                                          'complete_original_engineering_members_retained': False}
                continue
            mb = z.read(rel)
            require(sha(mb) == k3_binding['poses'][old_pose]['engineering_manifest_sha256'],
                    'actual prerequisite manifest differs')
            old = json.loads(mb)['members']
            retained = all(members.get(prefix + key) == ref for key, ref in old.items())
            prerequisites[old_pose] = {'original_manifest_present': True, 'engineering_manifest_sha256': sha(mb),
                                      'original_member_count': len(old),
                                      'complete_original_engineering_members_retained': retained}

        def export_present(entry, prefix):
            return all(members.get(prefix + ref['path']) == {k: ref[k] for k in ('sha256', 'bytes')}
                       for ref in entry.get('files', {}).values()) and set(entry.get('files', {})) == {'step', 'brep'}

        for mode in ('factory', 'readback'):
            rel = f'{mode}/worker/report.engineering.json'
            if rel not in members:
                results[mode] = {'report_present': False, 'scientific_complete': False,
                                 'finite_pose_clear_claimed': False, 'pair_count': 0, 'journal_rows': 0}
                continue
            report_bytes = z.read(rel)
            wrapper = json.loads(report_bytes)
            wrappers[mode] = wrapper
            r = wrapper['engineering_record']
            reports[mode] = r
            require(wrapper['derived_projection_not_raw_original'] is True
                    and r['functional_source_commit'] == S4 and r['pose'] == pose
                    and r['candidate_name'] == 'panel_key_travel_stops_v1', 'marked report identity differs')
            require(all(r[k] is False for k in FALSE_FLAGS), 'unqualified domain or release claim')
            require(r.get('pilot_only') is False and r.get('full_finite_campaign_only') is True
                    and r.get('preregistered_state_count') == 10, 'finite campaign scope differs')
            if 'candidate_source_sha256' in r:
                require(r['candidate_source_sha256'] == plan['candidate_source_sha256']
                        and r['candidate_contract_sha256'] == plan['candidate_contract_sha256'],
                        'named material source or contract differs')
            if 'pose_input' in r:
                require(r['pose_input'] == spec, 'actual factory input differs from preregistered state')
            if 'actual_q_by_side_mm' in r:
                require(r['actual_q_by_side_mm'] == expected_q, 'actual independent binary64 q differs')
            participant_names = r.get('participant_names', [])
            inventory_complete = len(participant_names) == len(set(participant_names)) == expected_bodies
            pairs = r.get('pairs', [])
            ordered = list(itertools.combinations(sorted(participant_names), 2))
            pair_inventory_complete = (inventory_complete and len(pairs) == expected_count
                                      and [(x['a'], x['b']) for x in pairs] == ordered)
            if r.get('all_unordered_pairs_present_once') is True:
                require(pair_inventory_complete and r['expected_pair_count'] == r['persisted_pair_count'] == expected_count,
                        'claimed complete pair inventory differs')
            journal_path = f'{mode}/worker/pairs.jsonl'
            journal = [json.loads(line) for line in z.read(journal_path).decode().splitlines()] if journal_path in names else []
            completed = [x['row'] for x in journal if x.get('event') == 'completed']
            selected = [(x['a'], x['b']) for x in journal if x.get('event') == 'selected']
            journal_complete = (pair_inventory_complete and len(journal) == 2 * expected_count
                                and completed == pairs and selected == ordered)
            if r.get('all_unordered_pairs_present_once') is True:
                require(journal_complete, 'complete selected/completed journal differs')
            for row in pairs:
                if row.get('evaluation_failed'):
                    continue
                v = row['common_mm3']
                require(finite_volume(v) and row['rejected'] == (v > TOL), 'original Common predicate differs')
                if v > 0 and not row.get('post_evaluation_failure'):
                    require(export_present(row['positive_Common_export'], f'{mode}/worker/'),
                            'positive Common STEP/BREP original missing')
            ident = r.get('source_identity_projection', {})
            audited = (ident.get('source_commit_before') == ident.get('source_commit_after') == S4
                       and ident.get('worktree_clean_before') is True
                       and ident.get('source_bytes_and_locked_environment_unchanged') is True
                       and ident.get('locked_environment_before_passed') is True
                       and ident.get('locked_environment_after_passed') is True
                       and ident.get('checked_package_count_before') == ident.get('checked_package_count_after') == 43)
            cp = f'{mode}/controller.engineering.json'
            c = json.loads(z.read(cp))['engineering_record'] if cp in names else {}
            controllers[mode] = c
            supervised = (c.get('completed') is True and c.get('worker_exit_code') == 0 and c.get('limits') == LIMITS
                          and all(c.get(k) is True for k in ('owned_child_identity_verified', 'source_bytes_unchanged',
                                                           'locked_environment_unchanged', 'owned_channel_descriptors_closed'))
                          and c.get('result_sha256') == wrapper['original']['sha256'])
            exports = r.get('body_exports', {})
            if mode == 'factory':
                whole_materials_complete = (r.get('actual_complete_factory_called') is True
                    and r.get('complete_preview_exports_retained') is True and len(exports) == expected_bodies
                    and set(exports) == set(participant_names)
                    and all(export_present(entry, 'factory/worker/') for entry in exports.values()))
            else:
                whole_materials_complete = (r.get('native_STEP_readback_executed') is True
                    and r.get('separate_process_from_factory') is True and r.get('independent_CAD_kernel') is False
                    and r.get('independent_material_builder_does_not_import_candidate_source') is True
                    and len(r.get('body_readbacks', {})) == expected_bodies
                    and set(r.get('body_readbacks', {})) == set(participant_names)
                    and all(x['passed'] is True for x in r.get('body_readbacks', {}).values()))
            complete = bool(r.get('execution_completed') is True and audited and supervised and journal_complete
                            and whole_materials_complete and not r.get('evaluation_failures')
                            and not r.get('mismatches_to_factory'))
            results[mode] = {'report_present': True, 'original_report_sha256': wrapper['original']['sha256'],
                'projection_sha256': sha(report_bytes), 'original_status': r.get('status'), 'failure_stage': r.get('failure_stage'),
                'original_failure_type': r.get('original_failure_type'),
                'source_and_43_package_environment_audited': audited, 'owned_original_resource_guards_completed': supervised,
                'whole_material_exports_or_readbacks_complete': whole_materials_complete,
                'scientific_complete': complete, 'finite_pose_clear_claimed': r.get('finite_pose_clear') is True,
                'native_early_conditions_rechecked': r.get('native_early_conditions_rechecked') is True,
                'seconds': r.get('seconds'), 'body_count': len(participant_names), 'pair_count': len(pairs),
                'all_unordered_pairs_present_once': pair_inventory_complete,
                'journal_rows': len(journal), 'complete_original_pair_journal_verified': journal_complete,
                'method_counts': dict(Counter(x.get('method', 'evaluation_failed') for x in pairs)),
                'positive_pairs': r.get('positive_pairs', []), 'pair_evaluation_failures': r.get('evaluation_failures', []),
                'pair_readback_mismatches': r.get('mismatches_to_factory', []), 'actual_q_by_side_mm': r.get('actual_q_by_side_mm')}

        producer, reader = reports.get('factory', {}), reports.get('readback', {})
        gates = reader.get('independent_early_gate_records', {})
        geometry_rejections = {k: v for k, v in gates.items() if v.get('evaluated') is True and v.get('passed') is False}
        unresolved = {k: v for k, v in gates.items() if v.get('evaluated') is not True}
        gate_inventory_complete = len(gates) == expected_gates
        gates_clear = gate_inventory_complete and not geometry_rejections and not unresolved
        if gates:
            require(len(gates) <= expected_gates, 'unexpected independent gate inventory')
            recorded_unresolved = reader.get('independent_native_evaluation_failures', [])
            recorded_rejected = reader.get('independent_geometric_gate_rejections', [])
            require(len(recorded_unresolved) == len(unresolved) and set(recorded_unresolved) == set(unresolved),
                    'unresolved gate list differs')
            require(len(recorded_rejected) == len(geometry_rejections) and set(recorded_rejected) == set(geometry_rejections),
                    'rejected gate list differs')
        if reader.get('execution_completed') is True:
            require(gate_inventory_complete and reader['native_early_conditions_rechecked'] == gates_clear,
                    'completed reader gate inventory or aggregate differs')
        pair_mismatches = []
        if producer and reader:
            require(reader.get('factory_report_sha256') == wrappers['factory']['original']['sha256'],
                    'reader source report binding differs')
            old_pairs = {(x['a'], x['b']): x for x in producer.get('pairs', [])}
            for row in reader.get('pairs', []):
                previous = old_pairs.get((row['a'], row['b']))
                if previous is None or row.get('evaluation_failed') or previous.get('evaluation_failed'):
                    continue
                delta = row['common_mm3'] - previous['common_mm3']
                if abs(delta) > TOL or row['rejected'] != previous['rejected']:
                    pair_mismatches.append({'a': row['a'], 'b': row['b'], 'volume_delta_mm3': delta,
                                            'factory_rejected': previous['rejected'], 'readback_rejected': row['rejected']})
        consistency_known = bool(producer and reader and gate_inventory_complete)
        gate_disagreement = bool(consistency_known and producer.get('native_early_conditions_rechecked', False) != gates_clear)
        rejected_pairs = {mode: [r for r in report.get('pairs', []) if r.get('rejected') is True]
                          for mode, report in reports.items()}
        all_prerequisites = all(x['complete_original_engineering_members_retained'] for x in prerequisites.values())
        complete = all(x.get('scientific_complete') for x in results.values()) and all_prerequisites
        clear = bool(complete and gates_clear and not gate_disagreement and not pair_mismatches
                     and all(x.get('native_early_conditions_rechecked') for x in results.values())
                     and not any(rejected_pairs.values()))
        clearance_claim_disagreement = {mode: row.get('finite_pose_clear_claimed') != clear
                                       for mode, row in results.items() if row.get('report_present')}
        material_records = {mode: {key: report.get(key) for key in (
            'original_panel_to_verified_pilot_material', 'new_panel_to_named_candidate_material',
            'new_panel_to_actual_dual_pilot_material', 'candidate_q0_material_comparisons') if key in report}
                            for mode, report in reports.items()}
        if clear:
            for report in (producer, reader):
                require(material_equal(report['original_panel_to_verified_pilot_material'])
                        and material_equal(report['new_panel_to_actual_dual_pilot_material']),
                        'complete whole panel does not match actual dual pilots')
            require(material_equal(producer['new_panel_to_named_candidate_material']), 'named candidate panel differs')
            require(set(reader['candidate_q0_material_comparisons']) == {'L', 'R'}
                    and all(material_equal(row) for row in reader['candidate_q0_material_comparisons'].values()),
                    'complete whole K1 KEY materials differ')
        observation_bytes = z.read('K3FULL-complete-observation.json') if 'K3FULL-complete-observation.json' in names else None
        observation_consistent = None
        if observation_bytes:
            observation = json.loads(observation_bytes)
            require(observation['schema'] == 'razr-K3FULL-complete-finite-state-observation-v1'
                    and observation['pose'] == pose and observation['declared_pose'] == plan['states'][pose],
                    'original finite observation identity differs')
            observation_consistent = (observation['complete_full_pair_execution'] == complete
                                      and observation['finite_state_clear'] == clear)
        scope_bytes = z.read('EXPORT_SCOPE.json')
        scope = json.loads(scope_bytes)
        require(scope['schema'] == 'razr-K3FULL-engineering-export-scope-v1'
                and scope['raw_producer_reader_reports_modified'] is False
                and scope['all_copied_original_bytes_verified'] is True
                and scope['raw_runtime_durable_preservation_claimed'] is False, 'engineering scope differs')
        require(all(members.get(key) == ref for key, ref in scope['copied_originals'].items()),
                'copied-original accounting differs')
        require(all(set(row) == {'category', 'bytes', 'sha256'} for row in scope['omitted_runtime_file_hashes']),
                'omitted runtime fields expose other data')
        summary = {'schema': 'razr-K3FULL-memory-artifact-scientific-inspection-v1', 'pose': pose,
            'run_id': run_id, 'head_sha': head_sha, 'artifact_id': meta['id'], 'artifact_name': meta['name'],
            'artifact_expires_at': meta['expires_at'], 'official_ZIP_sha256': sha(data), 'official_ZIP_bytes': len(data),
            'engineering_manifest_sha256': sha(manifest_bytes), 'exact_engineering_manifest_entries': len(members),
            'exact_ZIP_regular_file_count': len(names), 'uncompressed_member_bytes_excluding_manifest': sum(x['bytes'] for x in members.values()),
            'official_ZIP_SHA_size_all_CRC_and_member_SHA_verified': True, 'sixteen_frozen_runtime_source_bytes_verified': True,
            'declared_pose': plan['states'][pose], 'expected_pair_count_per_worker': expected_count,
            'expected_contact_ends': contacts, 'expected_independent_gate_count': expected_gates,
            'complete_K3_prerequisites': prerequisites, 'results': results, 'controllers': controllers,
            'independent_early_gate_records': gates, 'evaluated_geometric_gate_rejections': geometry_rejections,
            'native_gate_evaluation_unresolved': unresolved, 'missing_independent_early_gate_inventory': not gate_inventory_complete,
            'producer_reader_gate_classification_disagreement': gate_disagreement,
            'gate_classification_consistency_known': consistency_known, 'independently_recomputed_pair_mismatches': pair_mismatches,
            'original_clearance_claim_disagreements': clearance_claim_disagreement,
            'positive_rejected_pairs': rejected_pairs, 'complete_finite_pair_execution': complete,
            'actual_finite_state_clear': clear, 'original_observation_consistent_with_independent_inspection': observation_consistent,
            'whole_material_comparison_records': material_records,
            'original_complete_panel_material_account': producer.get('candidate_application', {}).get('actual_added_only_panel_account'),
            'original_endpoint_and_overtravel_checks': producer.get('endpoint_and_overtravel_checks'),
            'candidate_source_sha256': plan['candidate_source_sha256'], 'candidate_contract_sha256': plan['candidate_contract_sha256'],
            'local_new_CAD_execution_claimed': False, 'raw_runtime_reconstructed': False,
            'raw_runtime_durable_preservation_claimed': False, 'complete_scientific_ZIP_saved_locally': False,
            'complete_product_motion_proved': False, 'physical_allowed_domain_proved': False,
            'global_minimum_wall_measured': False, 'strength_qualified': False,
            'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
        projection = {key: scope[key] for key in ('schema', 'functional_source_commit', 'raw_producer_reader_reports_modified',
            'all_copied_original_bytes_verified', 'raw_runtime_durable_preservation_claimed', 'raw_runtime_location',
            'local_runtime_verification_results', 'scope')}
        projection.update(derived_projection_not_raw_original=True, original_sha256=sha(scope_bytes), original_bytes=len(scope_bytes),
            root_keys=sorted(scope), copied_original_count=len(scope['copied_originals']),
            derived_projection_count=len(scope['derived_projections']), omitted_runtime_file_count=len(scope['omitted_runtime_file_hashes']),
            copied_originals_exactly_match_manifest=True, omitted_records_have_only_category_size_sha256=True)
        return summary, manifest_bytes, observation_bytes, projection


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--k3-binding', type=Path, required=True)
    ap.add_argument('--k1-binding', type=Path, required=True)
    ap.add_argument('--run-id', type=int, required=True)
    ap.add_argument('--head-sha', required=True)
    args = ap.parse_args()
    request = json.load(sys.stdin)
    meta = request['artifact']
    require(meta['size_in_bytes'] < 128 * 2**20, 'unexpected engineering ZIP size')
    with urllib.request.urlopen(request['file_uri'], timeout=90) as stream:
        data = stream.read(meta['size_in_bytes'] + 1)
    summary, manifest, observation, projection = inspect(data, meta, request['pose'], args.run_id, args.head_sha,
        json.loads(args.plan.read_text()), args.k3_binding.read_bytes(), args.k1_binding.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    prefix = 'K3FULL_' + request['pose']
    (args.output / (prefix + '_ENGINEERING_MANIFEST.json')).write_bytes(manifest)
    (args.output / (prefix + '_INSPECTION.json')).write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    if observation is not None:
        (args.output / (prefix + '_COMPLETE_OBSERVATION.json')).write_bytes(observation)
    (args.output / (prefix + '_EXPORT_SCOPE_PROJECTION.json')).write_text(json.dumps(projection, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: summary[key] for key in ('pose', 'artifact_id', 'official_ZIP_sha256', 'official_ZIP_bytes',
        'engineering_manifest_sha256', 'exact_engineering_manifest_entries', 'exact_ZIP_regular_file_count',
        'complete_finite_pair_execution', 'actual_finite_state_clear', 'evaluated_geometric_gate_rejections',
        'native_gate_evaluation_unresolved', 'producer_reader_gate_classification_disagreement',
        'original_observation_consistent_with_independent_inspection')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
