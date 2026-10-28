"""Read existing KEY/STOP source and Common records; no native import or operation."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import gc
import gzip
import hashlib
import json
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SCI = ROOT / 'recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027'
OUT = Path(__file__).resolve().parent
CASES = ('case-028', 'case-037', 'case-063', 'case-072')


def identity(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    target = OUT / 'R5_SAVED_KEY_STOP_COMMON_AND_SOURCE_REVIEW.json'
    assert not target.exists(), 'Preserve the prior readback.'
    binding_path = SCI / 'source-and-inputs/R3E_INPUT_BINDING.json'
    binding = json.loads(binding_path.read_text())
    v5_path = ROOT / 'r5-ci-results/run-40645988108/all-trim-model-frames/report.json'
    v5 = json.loads(v5_path.read_text())
    failed = [r for r in v5['frames'] if not r['trim_model_conditional_clearance_gate_passed']]
    assert {(r['case_id'], r['frame']) for r in failed} == {(c, f) for c in CASES for f in (1, 2)}
    inputs = [identity(binding_path), identity(v5_path)]
    source_rows = {}
    feature_rows = {}
    actual_file_checks = []
    expected_reports = {
        'producer': (65374048, 'f1c6bcb76d32f9dead19296ff37a64805eff59a8bcc4f696f99cc5821c370c5d'),
        'reader': (65385052, '83e527ccbc849701f5d99c4e4b4ddbd099370ee52c7f10a1e11923c27b8742ce')}
    for role in ('producer', 'reader'):
        path = SCI / 'native-and-math' / role / 'worker/report.json'
        actual = identity(path)
        assert (actual['bytes'], actual['sha256']) == expected_reports[role]
        inputs.append(actual)
        report = json.loads(path.read_text())
        assert report['execution_completed'] is True and report['whole_domain_native_qualified'] is False
        rows = [r for r in report['tiny_base_Common'] if r['case_id'] in CASES]
        assert len(rows) == 8
        source_rows[role] = rows
        for r in rows:
            assert r['base_Common_direct_signed_mm3'] == 0.0
            assert r['base_Common_valid_complete_material'] is True
            assert r['unchanged_strict_common'] == {'common_mm3': 0.0, 'method': 'native_common', 'axis_gap_lower_mm': 0.0}
            assert r['unchanged_strict_common_failure'] is None
            for key in ('base_Common_export',):
                record = r[key]
                aid = identity(path.parent / record['relative_path'])
                assert all(aid[k] == record[k] for k in ('bytes', 'sha256'))
                actual_file_checks.append(aid)
        features = []
        for operand in report['operands']:
            i = operand['input']
            if i['case_id'] != 'case-028' or i['material_id'] not in (2, 3):
                continue
            indices = [0] if i['material_id'] == 2 else [37, 39, 78]
            for fidx in indices:
                face = operand['boundary']['faces'][fidx]
                features.append({'case_id': 'case-028', 'material_id': i['material_id'], 'input': i,
                                 'face_index': fidx, 'complete_face_canonical_sha256': canonical(face),
                                 'orientation': face['orientation'], 'local_surface': face['local_surface'],
                                 'wires': [{'index': w['index'], 'is_outer': w['is_outer'],
                                            'edge_occurrence_count': len(w['edge_occurrences']),
                                            'pcurve_type_counts': dict(Counter(e['pcurve']['type'] for e in w['edge_occurrences']))}
                                           for w in face['wires']]})
        feature_rows[role] = features
        del report
        gc.collect()
    assert source_rows['producer'] == source_rows['reader']
    assert feature_rows['producer'] == feature_rows['reader']
    cases = []
    for c in binding['cases']:
        if c['case_id'] not in CASES:
            continue
        path = SCI / 'source-and-inputs' / c['result_relative_path']
        original = json.loads(path.read_text())
        assert original['target'] == c['target']
        assert original['native_raw'] == c['old_raw_result']
        assert original['trace']['actual_strict_Common_calls'] == []
        cases.append({'case_id': c['case_id'], 'pair': c['pair'], 'original_target': c['target'],
                      'original_result_identity': identity(path),
                      'original_continuous_attempt_strict_Common_call_count': 0,
                      'original_continuous_attempt_still_unresolved': True})
    frames = []
    for row in source_rows['producer']:
        key = (row['case_id'], row['frame'])
        actual_v5 = next(r for r in failed if (r['case_id'], r['frame']) == key)
        assert actual_v5['original_remaining_displacement_box_exact'] == row['full_remaining_displacement_box_exact']
        for name in ('moving_input', 'fixed_input'):
            m = row[name]
            aid = identity(SCI / 'source-and-inputs' / m['relative_path'])
            assert all(aid[k] == m[k] for k in ('bytes', 'sha256'))
            actual_file_checks.append(aid)
        frames.append({'case_id': key[0], 'frame': key[1], 'original_native_row': row,
                       'producer_reader_rows_exactly_equal': True,
                       'V5_reported_conditional_upper_mm3': actual_v5['trim_model_conditional_upper_mm3'],
                       'V5_conditional_gate_still_failed': True,
                       'saved_start_Common_is_not_full_displacement_or_continuous_qualification': True})
    original_dir = ROOT / 'r4-native/inputs/original-archives'
    manifest_path = original_dir / 'mounted-geometry-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    archive_path = original_dir / 'mounted-native-geometry.tar.gz'
    archive_id = identity(archive_path)
    assert archive_id['sha256'] == manifest['archive_sha256']
    inputs += [identity(manifest_path), archive_id]
    entries = {x['path']: x for x in manifest['files']}
    mounted_sources = []
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in ('L_KEY.step', 'R_KEY.step', 'L_STOP_0.step', 'L_STOP_1.step', 'R_STOP_0.step', 'R_STOP_1.step'):
            raw = archive.extractfile(member).read()
            expected = entries[member]
            assert len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
            surfaces = re.findall(r'#\d+\s*=\s*CYLINDRICAL_SURFACE\([^;]+;', raw.decode('utf-8'), re.S)
            chosen = [s for s in surfaces if s.endswith(',0.16);') or s.endswith(',0.1);')]
            assert chosen
            mounted_sources.append({'archive_member': member, **expected, 'exact_STEP_cylinder_records': chosen,
                                    'source_member_read_back': True, 'new_native_read_or_radius_measurement': False})
    functional = ROOT / 'r4-native/recovered/functional-source/integration'
    source_functions = {
        'cam_coupling.py': ['parent', 'templates', 'phone_scene'],
        'mounted_mechanism.py': ['parent_part', 'mounted', 'build'],
        'thin_mechanism.py': ['original', 'design'],
        'cam_contact_native.py': ['extract_profile']}
    import ast
    source_locators = []
    for name, functions in source_functions.items():
        path = functional / name
        tree = ast.parse(path.read_text())
        nodes = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        source_locators.append({'identity': identity(path),
                                'functions': [{'name': n, 'line': nodes[n].lineno, 'end_line': nodes[n].end_lineno}
                                              for n in functions]})
    thin_path = original_dir / 'thin-native-verification.json.gz'
    thin = json.loads(gzip.decompress(thin_path.read_bytes()))
    inputs.append(identity(thin_path))
    contacts = {s: [{'stop': x['stop'], 'old_native_core_unchanged': x['old_native_core_unchanged'],
                     'profile': x['profile'], 'pin_complete_relative_path_common_mm3': x['pin_complete_relative_path_common_mm3'],
                     'same_kinematic_branch_not_force_proof': x['same_kinematic_branch_not_force_proof']}
                    for x in thin['sides'][s]['contacts']] for s in ('L', 'R')}
    result = {'schema': 'razr-r5-saved-key-stop-Common-and-source-review-v1',
              'recorded_utc': datetime.now(timezone.utc).isoformat(), 'readback_completed': True,
              'new_native_operation': False, 'new_Common_or_topology_call': False,
              'full_continuous_G2': False, 'new_physical_qualification': False,
              'source_identities': inputs, 'actual_small_file_identities_checked': actual_file_checks,
              'cases': cases, 'frames': frames, 'case028_boundary_feature_records': feature_rows['producer'],
              'boundary_features_exactly_equal_in_producer_and_reader': True,
              'mounted_STEP_source_members': mounted_sources, 'functional_source_locations': source_locators,
              'original_thin_profile_records': contacts,
              'construction_chain': [
                  'cam_coupling.parent authenticates mounted manifest/archive/member then imports the existing STEP.',
                  'cam_coupling.templates fuses the original KEY with its yoke extension; it does not construct the 0.16 mm recess.',
                  'cam_coupling.phone_scene translates the inherited STOP using the stored thin contact profile; its 0.1 mm pin is inherited.',
                  'mounted_mechanism transforms inherited thin parts; thin_mechanism preserves the original KEY and cropped contact core while redesigning seats.',
                  'cam_contact_native.extract_profile recognizes the stored transverse pin radius 0.1 and rebuilds a proof carrier; this is not the original design constructor.',
                  'The recovered mounted STEP contains radius 0.16 KEY cylinder records and radius 0.1 STOP cylinder records. The earliest constructor of those surfaces has not been recovered by this focused readback.'],
              'scope': [
                  'All eight existing base Common producer/reader values are zero; no existing positive native Common found in these exact selected start-pose records.',
                  'The L1 continuous attempts themselves reached zero strict Common calls and remain unresolved evaluation failures.',
                  'R3E base Common is diagnostic start-pose evidence only; native semantics and full remaining displacement are not certified by it.',
                  'Neither the 0.016 V5 bound nor a whole-self negative-control volume is actual pair interference.'],
              'reader_source_identity': identity(Path(__file__))}
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'readback_completed': True, 'cases': len(cases), 'frames': len(frames),
                      'all_original_base_Common_values': 0.0, 'new_native_operation': False,
                      'report': identity(target)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
