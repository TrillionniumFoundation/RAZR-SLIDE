#!/usr/bin/env python3
"""Read complete EP4 assemblies, all recorded bodies, and located Common exports.

The process imports the frozen independent EP3 reader's geometric comparison
helpers, never the assembly or routing generators. Numerical round trips do not
establish full material equality, tolerance capability, or a collision-free path.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import traceback

HELPER = 'engineering/product-integration-20261018/phase3-20261020/read_ep3_step_independent.py'
HELPER_SHA = '14b2aa3362aba950a39244b0130021b72231fa2866e15d96e2f34a6dac6798c5'
SCHEMA = 'razr-ep4-bounded-native-v1'
EXPECTED = {'PREDOCK': (113, 154), 'OPEN': (120, 161), 'STOW': (113, 154)}
TOLERANCE = {'bounds_mm': 1e-6, 'absolute_volume_mm3': 1e-6, 'relative_volume': 1e-9}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(manifest_path, root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    manifest_path = Path(manifest_path).resolve()
    artifact_root = manifest_path.parent
    require(not output.exists() and output != root and root not in output.parents,
            'use a new directory outside repository source')
    output.mkdir(parents=True)
    helper_path = root / HELPER
    require(sha(helper_path) == HELPER_SHA, 'frozen independent reader helper changed')
    spec = importlib.util.spec_from_file_location('ep4_independent_metric_helpers', helper_path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    clock = time.monotonic()
    report = {'schema': 'razr-ep4-independent-step-readback-v1', 'started_utc': started,
        'command_line': sys.argv, 'reader_source': reader.file_identity(__file__),
        'helper_source': reader.file_identity(helper_path), 'runtime': reader.versions(),
        'native_report': reader.file_identity(manifest_path), 'native_source_commit': None,
        'independent_process_from_generator': True, 'geometry_generator_modules_imported': False,
        'tolerance': TOLERANCE, 'tolerance_is_not_manufacturing_tolerance': True,
        'endpoint_files': {}, 'poses': {}, 'located_common_files': [], 'outside_files': [],
        'all_assembly_parts_have_metric_comparison': False,
        'execution_completed': False, 'declared_readback_checks_passed': False,
        'full_source_material_equivalence_proved': False, 'STEP_label_identity_proved': False,
        'continuous_interference_clearance_proved': False,
        'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False}
    tracked = {str(p): reader.file_identity(p) for p in (manifest_path, helper_path, Path(__file__).resolve())}
    failures = []
    def check(value, message):
        if not value:
            failures.append(message)
    try:
        manifest = json.loads(manifest_path.read_text())
        require(manifest.get('schema') == SCHEMA, 'wrong EP4 native manifest')
        require(manifest.get('native_checks_executed') is True and manifest.get('source_bytes_unchanged') is True,
                'native execution/source check incomplete')
        require(re.fullmatch(r'[a-f0-9]{40}', manifest.get('source_commit', '')) is not None, 'missing source commit')
        report['native_source_commit'] = manifest['source_commit']
        report['reader_observed_repository_head'] = reader.git_head(root)
        sources = {}
        for rel, expected in manifest['source_sha256'].items():
            path = (root / rel).resolve()
            require(not Path(rel).is_absolute() and root in path.parents, 'escaped source input')
            identity = reader.file_identity(path)
            sources[rel] = {**identity, 'native_sha256': expected, 'matches_native': identity['sha256'] == expected}
            require(identity['sha256'] == expected, 'source differs from executed native input: ' + rel)
            tracked[str(path)] = identity
        report['generator_source_inputs'] = sources
        original_root = Path(manifest['endpoint_self_checks']['A']['artifact_paths_relative_to']).parent
        require(Path(manifest['endpoint_self_checks']['B']['artifact_paths_relative_to']).parent == original_root,
                'inconsistent original export roots')
        report['original_artifact_root'] = str(original_root)
        report['read_artifact_root'] = str(artifact_root)

        def local_path(relative, base=artifact_root):
            require(isinstance(relative, str) and not Path(relative).is_absolute(), 'export reference must be relative')
            path = (base / relative).resolve()
            require(path.is_relative_to(artifact_root) and path.is_file(), 'missing or escaped STEP export: ' + relative)
            return path

        def pair_directory(pair_report):
            recorded = Path(pair_report['artifact_paths_relative_to'])
            require(recorded.is_relative_to(original_root), 'pair directory outside recorded export root')
            mapped = (artifact_root / recorded.relative_to(original_root)).resolve()
            require(mapped.is_relative_to(artifact_root), 'escaped pair directory')
            return mapped

        def read_shape(metadata, expected, base=artifact_root, key='file'):
            path = local_path(metadata[key], base)
            require(sha(path) == metadata['sha256'], 'STEP bytes differ: ' + str(path))
            shape, solids, record = reader.read_file(path, len(expected))
            tracked[str(path)] = record['file_identity']
            matching = reader.match_recorded_metrics(expected, record['flat_solids'], TOLERANCE)
            record['metric_comparison'] = matching
            ok = (record['flat_solid_count_matches'] and record['all_flat_solids_valid_positive'] and
                  matching['recorded_objects_all_matched_injectively'] and not matching['unassigned_observed_indices'])
            record['declared_file_checks_passed'] = ok
            check(ok, 'STEP count/validity/complete metric comparison failed: ' + str(path))
            return shape, solids, record

        local_endpoints = {}
        for end in ('A', 'B'):
            metadata = manifest['endpoint_exports'][end]
            require(len(metadata['parts']) == 20, 'endpoint metric inventory incomplete')
            _, solids, record = read_shape(metadata, metadata['parts'])
            local_endpoints[end] = solids
            report['endpoint_files'][end] = record

        labels = manifest['selected_poses']
        require(labels and len(set(labels)) == len(labels) and set(labels) <= set(EXPECTED), 'invalid selected poses')
        require([p['pose'] for p in manifest['poses']] == labels, 'pose list differs from selection')
        pair_sets = [(end+' local self', manifest['endpoint_self_checks'][end], 190) for end in ('A', 'B')]
        for pose in manifest['poses']:
            label = pose['pose']; external, total = EXPECTED[label]
            require(pose['external_participants'] == external and pose['combined_participants'] == total and
                    pose['candidate_participants'] == 41 and len(pose['parts']) == total,
                    'full common-scene inventory differs: ' + label)
            require(pose['all_assembly_source_parts_have_native_bounds_and_volume'] is True,
                    'external per-object source baseline missing')
            _, _, record = read_shape(pose['complete_assembly_STEP'], pose['parts'])
            transformed = {}
            for end in ('A', 'B'):
                location = reader.endpoint_location(pose['route'], end)
                metrics = [reader.native_metrics(solid.moved(location), i)
                           for i, solid in enumerate(local_endpoints[end])]
                expected = {end+'_'+name: pose['parts'][end+'_'+name]
                            for name in manifest['endpoint_exports'][end]['parts']}
                match = reader.match_recorded_metrics(expected, metrics, TOLERANCE)
                check(match['recorded_objects_all_matched_injectively'] and not match['unassigned_observed_indices'],
                      label + ' endpoint rigid-placement comparison failed: ' + end)
                transformed[end] = match
            report['poses'][label] = {'assembly': record, 'endpoint_rigid_placements': transformed,
                'all_source_objects_compared': total, 'external_source_objects_compared': external,
                'candidate_source_objects_compared': 41}
            pair_sets.extend([(label+' external', pose['external'], 41*external),
                              (label+' A to B', pose['A_to_B_endpoints'], 400),
                              (label+' material to endpoints', pose['material_to_all_40_endpoint_parts'], 40)])
            for item in pose['containment']['rows']:
                if item.get('outside_material'):
                    metadata = item['outside_material']
                    expected = {str(i): m for i, m in enumerate(metadata['solids'])}
                    _, _, readback = read_shape(metadata, expected, artifact_root/label/'outside-domain')
                    report['outside_files'].append({'pose': label, 'part': item['part'], 'readback': readback})

        pair_summary = []
        for label, pairs, count in pair_sets:
            require(pairs['pair_count'] == len(pairs['rows']) == count, 'native pair inventory differs: ' + label)
            base = pair_directory(pairs)
            positive = 0
            for row in pairs['rows']:
                if row.get('evaluation_failed'):
                    check(False, label + ': native pair evaluation failed: ' + row['a'] + '/' + row['b'])
                if row.get('common_mm3', 0.) <= 0.:
                    continue
                positive += 1
                require(row.get('common_material') and row.get('common_artifact_directory'), 'positive Common lacks export')
                name = row['common_artifact_directory']
                require(Path(name).name == name, 'Common folder must be a basename')
                folder = base/name
                metadata = row['common_material']
                expected = {str(i): m for i, m in enumerate(metadata['solids'])}
                _, _, common_record = read_shape(metadata, expected, folder)
                common_error = abs(common_record['sum_of_flat_solid_volumes_mm3'] - row['common_mm3'])
                check(common_error <= max(TOLERANCE['absolute_volume_mm3'],
                                         TOLERANCE['relative_volume']*row['common_mm3']), 'Common row volume mismatch')
                context = row['local_material_context']
                require(context['margin_each_face_mm'] == 2., 'unexpected neighborhood margin')
                require(len(context['ROI_bounds_mm']) == 6, 'missing Common neighborhood bounds')
                bounds = metadata['bounds_mm']
                expected_roi = [v-2. if i%2 == 0 else v+2. for i, v in enumerate(bounds)]
                check(max(abs(a-b) for a,b in zip(expected_roi, context['ROI_bounds_mm'])) < 1e-10,
                      'neighborhood does not span the declared Common + 2 mm')
                crops = {}
                for part in context['parts']:
                    check(not part.get('crop_evaluation_failed'), 'native context crop evaluation failed')
                    check(part['actual_local_wall_thickness_mm'] is None and part['thickness_inferred_from_bounds'] is False,
                          'local wall thickness was inferred without measurement')
                    require(part.get('crop_positive_solids', 0) == len(part.get('crop_solids', [])),
                            'context crop metrics incomplete')
                    for i, metric in enumerate(part.get('crop_solids', [])):
                        crops[part['part']+'/'+str(i)] = metric
                require(crops and context['neighborhood_STEP'], 'positive Common lacks finite neighborhood')
                _, _, neighborhood_record = read_shape(context['neighborhood_STEP'], crops, folder)
                report['located_common_files'].append({'pair_scope': label, 'a': row['a'], 'b': row['b'],
                    'coordinate_frame': row['coordinate_frame'], 'common_volume_row_error_mm3': common_error,
                    'common': common_record, 'neighborhood': neighborhood_record,
                    'local_wall_thickness_proved': False})
            pair_summary.append({'scope': label, 'declared_pairs': count, 'positive_Common_exports_read': positive})
        report['pair_scope_coverage'] = pair_summary
        report['all_assembly_parts_have_metric_comparison'] = all(
            row['assembly']['declared_file_checks_passed'] for row in report['poses'].values())
        report['execution_completed'] = True
    except Exception as exc:
        failures.append(type(exc).__name__ + ': ' + str(exc))
        report['exception_traceback'] = traceback.format_exc()
    changed = []
    for name, identity in tracked.items():
        if not Path(name).is_file() or sha(name) != identity['sha256']:
            changed.append(name)
    check(not changed, 'retained input file changed during independent readback')
    report['retained_input_files'] = tracked
    report['changed_during_readback'] = changed
    report['failures'] = failures
    report['declared_readback_checks_passed'] = bool(report['execution_completed'] and not failures)
    report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report['seconds'] = time.monotonic()-clock
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--repository-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = execute(args.manifest, args.repository_root, args.output)
    print(json.dumps({k:result[k] for k in ('native_source_commit', 'execution_completed',
        'declared_readback_checks_passed', 'all_assembly_parts_have_metric_comparison', 'seconds', 'failures')}, indent=2))
    raise SystemExit(0 if result['declared_readback_checks_passed'] else 1)
