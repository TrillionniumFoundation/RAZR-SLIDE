#!/usr/bin/env python3
"""Read A-head-relief or KEY-study STEP artifacts without importing a generator.

Only the frozen EP3 reader helpers are imported. Every exported positive solid
is compared injectively by native bounds and volume; this does not establish
full material/topology equality, STEP-label identity, or a new Boolean subset
proof. Native local acceptance is recorded separately from file readback.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import traceback

HELPER = 'engineering/product-integration-20261018/phase3-20261020/read_ep3_step_independent.py'
HELPER_SHA = '14b2aa3362aba950a39244b0130021b72231fa2866e15d96e2f34a6dac6798c5'
RELIEF_SCRIPT_SHA = '04ba12fd1c3d58acdcfd8de039a8e7cca72dec29762834ffb6105deb6ffddcda'
KEY_SCRIPT_SHA = '6c6b1fb9b5affd36a6d3d5848ff2dd20c0856409ad599019eabd64653eedaa90'
BASELINE_MODULE_SHA = 'f8286416e8d4f835b5a280f3c76e7dd69aaebda25ac2217f40f33e19e92251b8'
BASELINE_CONFIG_SHA = '7504d0714a6a61bf8742d2ab2f69dff245aa32dec449a34158c784803fe4240d'
INPUT_SCHEMA = 'razr-ep4-A-head-local-relief-v1'
KEY_INPUT_SCHEMA = 'razr-key-endcap-local-native-v1'
TOLERANCE = {'bounds_mm': 1e-6, 'absolute_volume_mm3': 1e-6, 'relative_volume': 1e-9}
PART_NAMES = set(['tail', 'stiffener', 'outer_stiffener_jaw', 'inner_carrier_jaw',
    'mini_DP_PCB', 'mini_DS_PCB', 'mated_BM28_reservation', 'static_26wire_transfer_reservation'] +
    [f'M2_clamp_{role}_{i}' for role in ('screw', 'head') for i in (1, 2)] +
    [f'M1_board_{role}_{i}' for role in ('shaft', 'head') for i in (1, 2, 3, 4)])
GENERATOR_MODULES = {'product_assembly', 'product_fpc', 'product_routing_ep3',
    'product_routing_ep4', 'product_split_assembly', 'oled_storage', 'cam_coupling',
    'key_endcap_local_study', 'ep4_a_head_relief'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_identity(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def volume_agrees(first, second):
    require(all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in (first, second)),
            'invalid nonnegative volume')
    error = abs(first-second)
    limit = max(TOLERANCE['absolute_volume_mm3'], TOLERANCE['relative_volume']*max(first, second))
    return {'absolute_volume_error_mm3': error, 'applied_volume_tolerance_mm3': limit,
            'within_tolerance': error <= limit}


def read_export(reader, metadata, expected, artifact_root, tracked):
    """Read all components of one export; expected may contain one or many parts."""
    name = metadata['file']
    require(isinstance(name, str) and not Path(name).is_absolute() and
            '..' not in Path(name).parts and name.lower().endswith('.step'),
            'export must be a contained relative STEP path')
    path = (artifact_root/name).resolve()
    require(artifact_root in path.parents and path.is_file(), 'missing or escaped STEP export: '+name)
    identity = file_identity(path)
    tracked[str(path)] = identity
    require(identity['sha256'] == metadata['sha256'], 'STEP SHA differs from native report: '+name)
    require(metadata['positive_valid_solids'] == len(expected), 'recorded solid inventory differs: '+name)
    require(len(metadata['solids']) == len(expected), 'per-solid export metrics incomplete: '+name)
    shape, solids, record = reader.read_file(path, len(expected))
    matching = reader.match_recorded_metrics(expected, record['flat_solids'], TOLERANCE)
    unnamed = {str(i): metric for i, metric in enumerate(metadata['solids'])}
    export_matching = reader.match_recorded_metrics(unnamed, record['flat_solids'], TOLERANCE)
    aggregate = {'bounds_mm': record['bounds_mm'], 'volume_mm3': record['sum_of_flat_solid_volumes_mm3']}
    aggregate_match = reader.agreement(metadata, aggregate, TOLERANCE)
    after = file_identity(path)
    unchanged = identity == after
    passed = bool(record['flat_solid_count_matches'] and record['all_flat_solids_valid_positive'] and
        matching['recorded_objects_all_matched_injectively'] and not matching['unassigned_observed_indices'] and
        export_matching['recorded_objects_all_matched_injectively'] and not export_matching['unassigned_observed_indices'] and
        aggregate_match is not None and unchanged)
    record.update(native_report_sha256=metadata['sha256'], before_read=identity, after_read=after,
        bytes_unchanged_during_this_read=unchanged, named_or_declared_component_matching=matching,
        export_component_matching=export_matching, aggregate_metric_comparison=aggregate_match,
        all_declared_file_checks_passed=passed)
    return shape, solids, record


def read_key_manifest(manifest, root, artifact_root, reader, report, tracked, track, check):
    """Consume every recorded KEY export, including evidence of rejected checks."""
    require(manifest.get('native_checks_executed') is True, 'KEY native report is incomplete')
    commit = manifest.get('source_commit', '')
    require(re.fullmatch(r'[a-f0-9]{40}', commit) is not None, 'missing KEY native source commit')
    report['native_source_commit'] = commit
    report['basis_native_source_commit'] = commit
    report['recorded_generator_runtime'] = manifest['runtime']
    report['native_local_geometry_checks_passed'] = manifest['all_declared_local_checks_passed']
    report['native_declared_failures_preserved_not_recomputed'] = manifest['declared_failures']
    report['native_source_bytes_unchanged_claim'] = manifest['source_bytes_unchanged']
    report['native_loaded_sources_without_pre_execution_snapshot'] = manifest[
        'loaded_sources_without_pre_execution_snapshot']
    report['native_check_count_observed_not_recomputed'] = len(manifest['checks'])
    report['native_scope'] = manifest['scope']
    report['native_release_flags'] = {key: manifest[key] for key in (
        'candidate_go', 'fixture_fabrication_go', 'manufacturing_go',
        'whole_scene_clearance_accepted', 'full_phone_motion_accepted')}
    sources = manifest['source_sha256']
    require(isinstance(sources, dict) and sources, 'empty KEY native source inventory')
    require(any(Path(path).name == 'key_endcap_local_study.py' and digest == KEY_SCRIPT_SHA
                for path, digest in sources.items()), 'unreviewed KEY study script identity')
    report['basis_source_inputs'] = {}
    for absolute, digest in sources.items():
        require(isinstance(absolute, str) and Path(absolute).is_absolute(), 'KEY source reference is not absolute')
        require(re.fullmatch(r'[a-f0-9]{64}', digest) is not None, 'invalid KEY native source SHA')
        path = Path(absolute).resolve()
        require(path.is_file(), 'KEY recorded source input is unavailable: '+absolute)
        identity = track(path)
        require(identity['sha256'] == digest, 'KEY executed source bytes differ: '+absolute)
        report['basis_source_inputs'][absolute] = identity
    module = (root/'integration/product_routing_ep4.py').resolve()
    require(sources.get(str(module)) == BASELINE_MODULE_SHA, 'KEY native EP4 module identity differs')
    artifacts = manifest['artifacts']
    require(isinstance(artifacts, dict) and artifacts, 'empty KEY native artifact inventory')
    report['native_artifact_count'] = len(artifacts)
    report['empty_artifacts_without_STEP'] = {}
    exported_paths = set()
    for name, metadata in artifacts.items():
        require(isinstance(name, str) and name and isinstance(metadata, dict), 'invalid KEY artifact entry')
        if metadata.get('empty') is True:
            require(metadata.get('solids') == [] and metadata.get('volume_mm3') == 0. and
                    metadata.get('bounds_mm') is None and metadata.get('file') is None and
                    metadata.get('sha256') is None, 'inconsistent recorded empty KEY artifact: '+name)
            report['empty_artifacts_without_STEP'][name] = {
                'recorded_native_metrics': metadata,
                'reason_not_read': 'Native empty artifact has no exported STEP; emptiness not recomputed.'}
            continue
        require(metadata.get('empty') is False, 'missing explicit KEY artifact emptiness: '+name)
        require(metadata['file'] not in exported_paths, 'duplicate KEY artifact file reference: '+metadata['file'])
        exported_paths.add(metadata['file'])
        expected = {str(i): metric for i, metric in enumerate(metadata['solids'])}
        require(expected, 'nonempty KEY artifact has no positive-material components: '+name)
        _, _, record = read_export(reader, metadata, expected, artifact_root, tracked)
        declared_valid = metadata.get('valid') is True and all(
            metric.get('valid') is True for metric in metadata['solids'])
        record['native_validity_flags_all_true'] = declared_valid
        report['files'][name] = record
        check(record['all_declared_file_checks_passed'] and declared_valid,
              'KEY STEP component/count/metric/hash/validity check failed: '+name)
    require(exported_paths, 'KEY report has no nonempty exported artifacts')
    report['all_nonempty_artifacts_read'] = len(report['files']) == len(exported_paths)
    report['empty_native_artifacts_not_independently_recomputed'] = True
    report['native_geometric_acceptance_is_not_a_readback_precondition'] = True


def execute(manifest_path, root, output, relief_script=None, mode='auto'):
    root, output = Path(root).resolve(), Path(output).resolve()
    manifest_path = Path(manifest_path).resolve()
    artifact_root = manifest_path.parent
    require(not output.exists() and output != root and root not in output.parents,
            'use a new output directory outside repository source')
    output.mkdir(parents=True)
    started = time.monotonic()
    report = {'schema': 'razr-ep4-local-independent-step-readback-v1',
        'started_UTC': dt.datetime.now(dt.timezone.utc).isoformat(), 'argv': sys.argv,
        'reader_process': {'PID': os.getpid(), 'PPID': os.getppid(),
            'python_executable': sys.executable, 'entrypoint': str(Path(__file__).resolve())},
        'input_manifest': str(manifest_path), 'artifact_root': str(artifact_root),
        'native_source_commit': None, 'basis_native_source_commit': None, 'files': {}, 'execution_completed': False,
        'declared_readback_checks_passed': False,
        'tolerance': TOLERANCE, 'tolerance_is_not_manufacturing_tolerance': True,
        'full_material_or_topology_equivalence_proved': False,
        'STEP_label_identity_proved': False, 'Boolean_subset_recomputed_by_reader': False,
        'native_collision_matrix_recomputed_by_reader': False,
        'strength_retention_or_manufacturing_qualified': False,
        'whole_phone_candidate_accepted': False, 'candidate_go': False,
        'fixture_fabrication_go': False, 'manufacturing_go': False}
    tracked = {}; failures = []

    def track(path):
        identity = file_identity(path)
        tracked[identity['path']] = identity
        return identity

    def check(condition, message):
        if not condition:
            failures.append(message)

    try:
        report['reader_source'] = track(__file__)
        report['native_report'] = track(manifest_path)
        helper_path = root/HELPER
        report['helper_source'] = track(helper_path)
        require(report['helper_source']['sha256'] == HELPER_SHA, 'frozen reader helper differs')
        require(not GENERATOR_MODULES.intersection(sys.modules), 'generator already imported into reader process')
        spec = importlib.util.spec_from_file_location('ep4_A_relief_independent_helpers', helper_path)
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        report['runtime'] = reader.versions()
        report['reader_observed_repository_head'] = reader.git_head(root)
        manifest = json.loads(manifest_path.read_text())
        inferred_mode = {INPUT_SCHEMA: 'a-relief', KEY_INPUT_SCHEMA: 'key'}.get(manifest.get('schema'))
        require(inferred_mode is not None, 'unrecognized local native report schema')
        require(mode in ('auto', inferred_mode), 'requested mode differs from native report schema')
        report['study_mode'] = inferred_mode
        if inferred_mode == 'key':
            read_key_manifest(manifest, root, artifact_root, reader, report, tracked, track, check)
        else:
            require(manifest.get('schema') == INPUT_SCHEMA, 'wrong local-relief report schema')
            require(manifest.get('basis_source_bytes_unchanged') is True, 'native source-byte check incomplete')
            require(re.fullmatch(r'[a-f0-9]{40}', manifest.get('basis_native_source_commit', '')) is not None,
                    'missing native basis commit')
            report['basis_native_source_commit'] = manifest['basis_native_source_commit']
            report['native_source_commit'] = manifest['basis_native_source_commit']
            report['coordinate_frame'] = manifest['coordinate_frame']
            report['native_local_geometry_checks_passed'] = manifest['local_declared_geometry_checks_passed']
            report['recorded_generator_runtime'] = manifest['runtime']
            report['native_subset_claim'] = manifest['new_external_intersections_precluded_by_material_subset_only']
            require(manifest['script']['sha256'] == RELIEF_SCRIPT_SHA, 'unreviewed relief script identity')
            script_path = Path(relief_script or manifest['script']['path']).resolve()
            report['relief_script_source'] = track(script_path)
            require(report['relief_script_source']['sha256'] == manifest['script']['sha256'], 'relief script bytes differ')
            sources = manifest['basis_source_sha256']
            require(sources.get('integration/product_routing_ep4.py') == BASELINE_MODULE_SHA,
                    'native report does not use the frozen EP4 module')
            require(sources.get('design/product_routing_ep4.json') == BASELINE_CONFIG_SHA,
                    'native report does not use the frozen EP4 configuration')
            report['basis_source_inputs'] = {}
            for relative, digest in sources.items():
                require(isinstance(relative, str) and not Path(relative).is_absolute(), 'absolute repository source reference')
                require(re.fullmatch(r'[a-f0-9]{64}', digest) is not None, 'invalid native source SHA')
                path = (root/relative).resolve()
                require(root in path.parents and path.is_file(), 'missing or escaped source input: '+relative)
                identity = track(path)
                require(identity['sha256'] == digest, 'executed source bytes differ: '+relative)
                report['basis_source_inputs'][relative] = identity
            artifacts = manifest['artifacts']
            require(set(artifacts) == {'complete_endpoint', 'removed_material', 'explicit_head_clearance_tool'},
                    'local-relief artifact inventory differs')
            endpoint = artifacts['complete_endpoint']
            require(set(endpoint['parts']) == PART_NAMES and len(endpoint['parts']) == 20,
                    'complete A endpoint must retain the named 20 source participants')
            for name in ('complete_endpoint', 'removed_material', 'explicit_head_clearance_tool'):
                metadata = artifacts[name]
                expected = endpoint['parts'] if name == 'complete_endpoint' else {
                    str(i): metric for i, metric in enumerate(metadata['solids'])}
                require(expected, 'empty positive-material export: '+name)
                _, _, record = read_export(reader, metadata, expected, artifact_root, tracked)
                report['files'][name] = record
                check(record['all_declared_file_checks_passed'], 'STEP component/count/metric/hash check failed: '+name)
            require(len(artifacts['explicit_head_clearance_tool']['solids']) == 1, 'one cylindrical relief tool required')
            relief = manifest['relief']
            require(relief['center_XY_mm'] == [0., -15.] and relief['radius_mm'] == 1.95 and
                    relief['Z_mm'] == [.85, 1.65] and relief['bearing_plane_Z_mm'] == .85,
                    'declared relief parameters differ from this reviewed local study')
            radius = relief['radius_mm']; cx, cy = relief['center_XY_mm']; z0, z1 = relief['Z_mm']
            theoretical_tool = {'bounds_mm': [cx-radius,cx+radius,cy-radius,cy+radius,z0,z1],
                                'volume_mm3': math.pi*radius*radius*(z1-z0)}
            observed_tool = report['files']['explicit_head_clearance_tool']
            tool_comparison = reader.agreement(theoretical_tool, {
                'bounds_mm': observed_tool['bounds_mm'],
                'volume_mm3': observed_tool['sum_of_flat_solid_volumes_mm3']}, TOLERANCE)
            report['declared_cylinder_dimensions_comparison'] = {
                'independent_expected_metrics': theoretical_tool, 'comparison': tool_comparison}
            check(tool_comparison is not None, 'STEP tool disagrees with independent declared cylinder dimensions')
            accounting = manifest['material_accounting']
            for key in ('original_mm3','removed_mm3','added_mm3','new_mm3'):
                volume_agrees(accounting[key], accounting[key])
            comparisons = {
                'removed_STEP_to_report': volume_agrees(
                    report['files']['removed_material']['sum_of_flat_solid_volumes_mm3'], accounting['removed_mm3']),
                'new_carrier_metric_to_report': volume_agrees(endpoint['parts']['inner_carrier_jaw']['volume_mm3'], accounting['new_mm3']),
                'reported_material_accounting_balance': volume_agrees(
                    accounting['original_mm3']-accounting['removed_mm3']+accounting['added_mm3'], accounting['new_mm3'])}
            report['material_accounting_comparison'] = {'reported_native_accounting': accounting,
                'comparisons': comparisons, 'original_carrier_STEP_not_supplied': True,
                'original_minus_new_or_new_minus_original_not_recomputed': True}
            for key, value in comparisons.items():
                check(value['within_tolerance'], 'material accounting mismatch: '+key)
            check(not report['native_subset_claim'] or accounting['added_mm3'] == 0.,
                  'native strict-subset claim has positive reported added material')
            pairs = manifest['self_pairs']
            require(pairs['pair_count'] == len(pairs['rows']) == 190, 'native A self-pair inventory incomplete')
            report['native_self_pairs_observed_not_recomputed'] = {
                'pair_count': pairs['pair_count'], 'failures': len(pairs['failures']),
                'no_Common_above_tolerance_or_evaluation_error': pairs['no_Common_above_tolerance_or_evaluation_error']}
        report['execution_completed'] = True
    except Exception as exc:
        failures.append(type(exc).__name__+': '+str(exc))
        report['exception_traceback'] = traceback.format_exc()
    after = {}; changed = []
    for name, before in tracked.items():
        try:
            observed = file_identity(name)
            after[name] = observed
            if observed != before:
                changed.append(name)
        except Exception as exc:
            after[name] = {'error_type': type(exc).__name__, 'error': str(exc)}
            changed.append(name)
    imported = sorted(GENERATOR_MODULES.intersection(sys.modules))
    check(not imported, 'geometry generator module imported during independent readback')
    check(not changed, 'input bytes changed during independent readback')
    report.update(retained_input_files=tracked, input_files_before=tracked, input_files_after=after, changed_during_readback=changed,
        geometry_generator_modules_imported=imported, failures=failures,
        declared_readback_checks_passed=bool(report['execution_completed'] and not failures),
        finished_UTC=dt.datetime.now(dt.timezone.utc).isoformat(), seconds=time.monotonic()-started)
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--repository-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('auto', 'a-relief', 'key'), default='auto')
    parser.add_argument('--relief-script', type=Path,
        help='Optional relocated copy of the exact recorded relief script; SHA must match')
    args = parser.parse_args()
    result = execute(args.manifest, args.repository_root, args.output, args.relief_script, args.mode)
    print(json.dumps({key: result[key] for key in ('native_source_commit', 'execution_completed',
        'declared_readback_checks_passed', 'seconds', 'failures')}, indent=2))
    return 0 if result['declared_readback_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
