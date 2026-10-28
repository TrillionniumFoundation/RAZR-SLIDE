"""Cross-author streaming audit of original K3 ZIP records; no imports from the producer auditor or CAD."""
from pathlib import Path, PurePosixPath
import collections
import gzip
import hashlib
import json
import math
import resource
import stat
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOL = 1e-7
EXPECTED = {
    'near': {'bytes': 62073711, 'sha256': 'cb4db333a525375928efb59ba4cb4b55afc8d6d3024dd04ebdc438c816b613ff'},
    'far': {'bytes': 62068019, 'sha256': 'e9e68c7accdc32ac261cd9e19ad45218c08f8896c686c874ef77bdacfec32fa0'}}
K1 = '3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578'
K3 = '59946f42f8bff88b0cdb8bcd2ad7f578e22e6f64e65832a6b6087426e282e5a5'

def require(value, reason):
    if not value:
        raise ValueError(reason)

def loads(raw):
    def pairs(items):
        d = {}
        for k, v in items:
            require(k not in d, 'duplicate JSON key:' + k)
            d[k] = v
        return d
    def bad(x):
        raise ValueError('nonfinite JSON:' + x)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)

def stream_id(stream):
    h, n = hashlib.sha256(), 0
    for b in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(b)
        n += len(b)
    return {'bytes': n, 'sha256': h.hexdigest()}

def identity(path):
    with Path(path).open('rb') as stream:
        return stream_id(stream)

def byte_id(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def number(x):
    return type(x) in (int, float) and math.isfinite(x)

def main():
    started = time.monotonic()
    plan_path = HERE / 'R5_INDEPENDENT_REVIEW_PLAN.json'
    plan = loads(plan_path.read_bytes())
    report = {'schema': 'razr-r5-independent-native-archive-review-v1',
        'review_source_identity': identity(__file__), 'plan_identity': identity(plan_path),
        'completed': False, 'issues': [], 'archives': [], 'new_native_CAD_execution': False,
        'producer_auditor_code_imported': False, 'historical_runtime_requalified': False,
        'omitted_original_raw_runtime_reports_reconstructed': False, 'strict_continuous_G2_proved': False,
        'physical_qualification_granted': False, 'candidate_material_changed': False}
    record_groups = collections.defaultdict(list)
    frozen_paths = [ROOT / 'r5-native/R5_K3_ARCHIVE_AUDIT_CONTRACT_V2.json',
        ROOT / 'r5-native/audit_recovered_k3_factory_r5_v2.py',
        ROOT / 'r5-native/historical-source/K3FULL_RECOVERED_TEN_STATE_ACCEPTANCE.json']
    for pose in EXPECTED:
        frozen_paths.extend([ROOT / ('r5-native/archive-audit-' + pose + '-v2') / n for n in
            ('R5_K3_ARCHIVE_AUDIT.json', 'all-historical-matrices.jsonl.gz', 'current-pose-complete-readback.json.gz')])
    before = {str(p.relative_to(ROOT)): identity(p) for p in frozen_paths}
    contract = loads(frozen_paths[0].read_bytes())
    acceptance = loads(frozen_paths[2].read_bytes())
    def guard():
        require(time.monotonic() - started < plan['readonly_review_wall_budget_seconds'], 'review wall budget')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 < plan['readonly_review_peak_RSS_budget_bytes'], 'review RSS budget')
    try:
        for pose, expected_zip in EXPECTED.items():
            guard()
            arcpath = ROOT / 'r5-recovered-originals' / ('K3FULL-' + pose + '-original-40285103942.zip')
            actual_zip = identity(arcpath)
            require(actual_zip == expected_zip, 'whole original ZIP identity:' + pose)
            original_acceptance = next(x for x in acceptance['rows'] if x['pose'] == pose)
            source_arc = original_acceptance['scientific_artifact']
            require(expected_zip == {'bytes': source_arc['zip_bytes'], 'sha256': source_arc['zip_sha256']}, 'acceptance identity:' + pose)
            audir = ROOT / ('r5-native/archive-audit-' + pose + '-v2')
            derived_audit = loads((audir / 'R5_K3_ARCHIVE_AUDIT.json').read_bytes())
            require(derived_audit['completed'] is True and not derived_audit['issues'], 'producer audit did not complete:' + pose)
            for key in ('new_native_execution', 'historical_runtime_requalified', 'original_raw_runtime_reports_reconstructed',
                        'full_continuous_domain_proved', 'physical_qualification', 'candidate_go', 'G2_pass'):
                require(derived_audit[key] is False, 'overclaimed audit scope:' + key)
            with zipfile.ZipFile(arcpath) as z:
                infos = z.infolist()
                require(len(infos) == len({x.filename for x in infos}), 'duplicate member names')
                for info in infos:
                    name = PurePosixPath(info.filename)
                    require(not name.is_absolute() and '..' not in name.parts and not info.is_dir()
                        and not stat.S_ISLNK(info.external_attr >> 16), 'unsafe archive member')
                    require(info.file_size <= plan['maximum_single_uncompressed_member_bytes'], 'unbounded member')
                raw_manifest = z.read('ENGINEERING_MANIFEST.json')
                require(byte_id(raw_manifest)['sha256'] == source_arc['manifest_sha256'], 'original manifest SHA')
                manifest = loads(raw_manifest)['members']
                require(len(manifest) == 4715 == source_arc['manifest_entries'], 'manifest count')
                require(set(z.namelist()) == set(manifest) | {'ENGINEERING_MANIFEST.json'}, 'exact manifest coverage')
                observed = {}
                for path, desired in manifest.items():
                    guard()
                    with z.open(path) as f:
                        observed[path] = stream_id(f)
                    require(observed[path] == desired, 'member SHA/size:' + path)
                    require(z.getinfo(path).file_size == desired['bytes'], 'central directory size:' + path)
                require(sum(x['bytes'] for x in observed.values()) == derived_audit['verified_member_bytes'], 'total uncompressed bytes')
                require(derived_audit['verified_member_count'] == 4715, 'audit member count')
                for name, expected in contract['original_candidate_source_identities'].items():
                    require(observed['source/k3full/' + name] == expected, 'source identity:' + name)
                k1_sources = [n for n, x in observed.items() if x['sha256'] == K1]
                require(len(k1_sources) == 4, 'K1 actual source copies')
                require(observed['source/k3full/panel_key_travel_stops_v1.py']['sha256'] == K3, 'K3 actual source')
                current_bindings = []
                for material in contract['current_R3_R4_whole_material_originals']:
                    local = identity(material['path'])
                    require(local == material['identity'], 'current original whole material changed')
                    matches = sorted(k for k, x in observed.items() if x == local)
                    require(matches, 'current original absent from archive')
                    prior = next(x for x in derived_audit['current_R3_R4_complete_original_material_byte_binding'] if x['role'] == material['role'])
                    require(matches == prior['byte_identical_original_ZIP_members'], 'material binding projection differs')
                    current_bindings.append({'role': material['role'], 'identity': local, 'archive_members': matches})
                source_reports = {}
                matrix_records = []
                derived_records = {x['report_member']: x for x in derived_audit['matrices']}
                with gzip.open(audir / 'all-historical-matrices.jsonl.gz', 'rb') as gz:
                    projected_matrices = {x['report_member']: x for x in map(loads, gz)}
                matrix_files = []
                for path in sorted(x for x in manifest if x.endswith('/worker/report.engineering.json')):
                    guard()
                    wrapper = loads(z.read(path))
                    doc = wrapper['engineering_record']
                    if doc.get('all_unordered_pairs_present_once') is not True:
                        continue
                    matrix_files.append(path)
                    require(wrapper['derived_projection_not_raw_original'] is True, 'not a declared projection')
                    require(set(wrapper['excluded_runtime_fields']) == {'external_source_sha256', 'identity_after', 'identity_before'}, 'runtime omission scope')
                    names = doc['participant_names']
                    require(len(names) == 154 == len(set(names)), 'not a unique 154 participant roster')
                    rows = doc['pairs']
                    require(len(rows) == len(names) * (len(names) - 1) // 2 == 11781, 'pair cardinality')
                    seen, previous, failures, methods = set(), None, [], collections.Counter()
                    for row in rows:
                        pair = (row['a'], row['b'])
                        require(pair[0] in names and pair[1] in names and pair[0] < pair[1], 'invalid unordered pair')
                        require(pair not in seen and (previous is None or previous < pair), 'duplicate or unordered pair list')
                        seen.add(pair)
                        previous = pair
                        value = row['common_mm3']
                        require(number(value) and value >= 0 and row['rejected'] == (value > TOL), 'Common threshold')
                        require(not row.get('evaluation_failed') and not row.get('post_evaluation_failure'), 'pair evaluation failure')
                        methods[row['method']] += 1
                        require(row['method'] in ('positive_axis_gap', 'native_common'), 'unknown Boolean method')
                        if row['method'] == 'positive_axis_gap':
                            require(value == 0 and number(row['axis_gap_lower_mm']) and row['axis_gap_lower_mm'] > 0, 'gap method')
                        if row['rejected']:
                            failures.append({'a': pair[0], 'b': pair[1], 'common_mm3': value})
                    require(doc['finite_pose_clear'] == (not failures) and doc['execution_completed'] is True, 'matrix completion/classification')
                    require(not doc['evaluation_failures'] and not doc.get('mismatches_to_factory'), 'recorded evaluation mismatch')
                    for key in ('G2_pass', 'complete_product_motion_proved', 'continuous_backlash_domain_proved',
                                'physical_qualification', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go'):
                        require(doc[key] is False, 'finite matrix overclaims ' + key)
                    jpath = str(PurePosixPath(path).parent / 'pairs.jsonl')
                    lines = 0
                    with z.open(jpath) as stream:
                        for row in rows:
                            selected = stream.readline()
                            completed = stream.readline()
                            require(selected and completed, 'missing pair journal event')
                            require(loads(selected) == {'event': 'selected', 'a': row['a'], 'b': row['b']}, 'selected journal event differs')
                            require(loads(completed) == {'event': 'completed', 'row': row}, 'completed journal event differs')
                            lines += 2
                        require(not stream.read(1), 'extra journal event')
                    require(lines == 23562, 'journal row count')
                    direct_values = {}
                    for side in ('L', 'R'):
                        direct = doc['panel_KEY_direct_Common'][side]
                        value_fields = set(direct) & {'common_mm3', 'direct_Common_mm3'}
                        require(len(value_fields) == 1, 'direct Common schema ambiguity')
                        value = direct[next(iter(value_fields))]
                        matrix_pair = next(x for x in rows if x['a'] == 'A_BACK_PANEL' and x['b'] == side + '_KEY')
                        require(abs(value - matrix_pair['common_mm3']) <= TOL and (value > TOL) == matrix_pair['rejected'], 'direct/matrix discrepancy')
                        require(direct['strict_common']['method'] == 'native_common' and abs(direct['strict_common']['common_mm3'] - value) <= TOL, 'strict Common discrepancy')
                        direct_values[side] = value
                    original_id = wrapper['original']['sha256']
                    group = 'K3_CURRENT' if doc.get('candidate_name') == 'panel_key_travel_stops_v1' else (
                        'K1_PREREQUISITE' if doc.get('candidate_name') == 'key_forward_loop_v1' else 'F1_UNREPAIRED_PREREQUISITE')
                    require(group != 'F1_UNREPAIRED_PREREQUISITE' or 'F1-full-factory-witness' in doc['schema'], 'unclassified prerequisite')
                    info = {'member': path, 'projection_identity': observed[path], 'original_report_sha256': original_id,
                        'class': group, 'pose': doc.get('pose'), 'participants': 154, 'pairs': len(rows),
                        'journal_events': lines, 'methods': dict(methods), 'finite_pose_clear': not failures,
                        'rejected_pairs': failures, 'direct_panel_KEY_mm3': direct_values}
                    record_groups[original_id].append({'archive': pose, 'member': path, 'class': group,
                        'projection_sha256': observed[path]['sha256'], 'finite_pose_clear': not failures})
                    matrix_records.append(info)
                    d = derived_records[path]
                    require(d['projection_identity'] == observed[path] and d['pair_count'] == len(rows)
                            and d['journal_rows'] == lines and d['method_counts'] == dict(methods)
                            and d['retained_rejected_pairs'] == failures, 'auditor matrix summary differs')
                    pm = projected_matrices[path]
                    require(pm['pairs'] == rows and pm['historical_original_report_identity'] == wrapper['original']
                            and pm['report_identity'] == observed[path], 'saved auditor full matrix differs')
                    if path in ('factory/worker/report.engineering.json', 'readback/worker/report.engineering.json'):
                        source_reports[path.split('/')[0]] = wrapper
                require(len(matrix_files) == 18 and set(matrix_files) == set(derived_records) == set(projected_matrices), 'full matrix source/projection set')
                del projected_matrices
                fw, rw = source_reports['factory'], source_reports['readback']
                f, r = fw['engineering_record'], rw['engineering_record']
                require(r['factory_report_sha256'] == fw['original']['sha256'], 'reader binds other producer')
                require(r['native_STEP_readback_executed'] is True and r['separate_process_from_factory'] is True
                    and r['independent_CAD_kernel'] is False and r['independent_material_builder_does_not_import_candidate_source'] is True,
                    'historical reader scope')
                for row in (f, r):
                    require(row['candidate_name'] == 'panel_key_travel_stops_v1' and row['candidate_source_sha256'] == K3, 'current candidate source')
                    require(row['pose'] == pose and row['pose_input']['slide'] == original_acceptance['declared_pose']['slide']
                        and row['actual_q_by_side_mm'] == original_acceptance['actual_q_by_side_mm'], 'slide/q identity')
                bodies = f['body_exports']
                require(set(bodies) == set(r['body_readbacks']) == set(f['participant_names']) == set(f['original_K1_inventory']), '154 body inventory mismatch')
                max_dv, max_db = 0., 0.
                for name, body in bodies.items():
                    before_sig, after_sig = body['signature_before'], body['signature_after']
                    require(before_sig == after_sig and body['serialization_preserved_in_memory_signature'] is True, 'serialization body changed')
                    require(before_sig['is_valid'] is True and before_sig['signed_volume_mm3'] > 0, 'invalid or nonpositive whole body')
                    for ext in ('step', 'brep'):
                        ex = body['files'][ext]
                        require(observed['factory/worker/' + ex['path']] == {k: ex[k] for k in ('bytes', 'sha256')}, 'export bytes differ')
                    rb = r['body_readbacks'][name]
                    require(rb['STEP'] == body['files']['step'] and rb['passed'] is True, 'STEP record binding')
                    sig = rb['signature']
                    dv = sig['signed_volume_mm3'] - before_sig['signed_volume_mm3']
                    db = [a - b for a, b in zip(sig['bounds_mm'], before_sig['bounds_mm'])]
                    require(rb['volume_delta_mm3'] == dv and rb['bounds_delta_mm'] == db, 'readback difference arithmetic')
                    require(abs(dv) <= TOL and all(abs(v) <= TOL for v in db) and sig['is_valid'] is True, 'whole STEP readback bound')
                    max_dv, max_db = max(max_dv, abs(dv)), max(max_db, max(abs(v) for v in db))
                    if name != 'A_BACK_PANEL':
                        old = f['original_K1_inventory'][name]
                        require(old['volume_mm3'] == before_sig['signed_volume_mm3'] and old['bounds_mm'] == before_sig['bounds_mm']
                            and old['solid_count'] == before_sig['solid_count'], 'nonpanel inventory changed')
                current_saved = loads(gzip.decompress((audir / 'current-pose-complete-readback.json.gz').read_bytes()))
                require(set(current_saved['all_154_body_readbacks']) == set(bodies), 'auditor saved roster')
                max_pair_delta = 0.
                for fr, rr, saved in zip(f['pairs'], r['pairs'], current_saved['all_11781_pair_readback_comparisons']):
                    require((fr['a'], fr['b']) == (rr['a'], rr['b']) == (saved['a'], saved['b']), 'paired row alignment')
                    dv = rr['common_mm3'] - fr['common_mm3']
                    require(abs(dv) <= TOL and fr['rejected'] == rr['rejected'], 'producer/readback Common mismatch')
                    require(saved['factory_Common_mm3'] == fr['common_mm3'] and saved['reader_Common_mm3'] == rr['common_mm3']
                        and saved['difference_mm3'] == dv and saved['threshold_classification_equal'] is True, 'auditor saved pair arithmetic')
                    max_pair_delta = max(max_pair_delta, abs(dv))
                require(len(current_saved['all_11781_pair_readback_comparisons']) == 11781, 'saved comparison length')
                for name in bodies:
                    saved = current_saved['all_154_body_readbacks'][name]
                    require(saved['factory_exports'] == bodies[name]['files'] and saved['reader_record'] == r['body_readbacks'][name], 'auditor saved body record')
                gates = r['independent_early_gate_records']
                require(len(gates) == 12 and all(x['evaluated'] is True and x['passed'] is True for x in gates.values()), '12 historical independent early gates')
                material = derived_audit['material_identity_bridge']
                require(current_saved['material_identity_bridge'] == material, 'saved material bridge differs')
                require(material['whole_panel_material_account'] == f['candidate_application']['actual_added_only_panel_account']
                        and material['independent_material_gates'] == gates, 'bridge account or gates differs')
                account = material['whole_panel_material_account']
                require(account['removed_mm3'] == 0.0 and abs(account['added_mm3'] - 4.62456) <= TOL
                    and abs(account['new_mm3'] - account['original_mm3'] - account['added_mm3']) <= TOL, 'panel material balance')
                for key, original in [('factory_original_panel_to_verified_pilot', f['original_panel_to_verified_pilot_material']),
                    ('factory_new_panel_to_named_candidate', f['new_panel_to_named_candidate_material']),
                    ('factory_new_panel_to_dual_pilot', f['new_panel_to_actual_dual_pilot_material']),
                    ('reader_new_panel_to_dual_pilot', r['new_panel_to_actual_dual_pilot_material'])]:
                    require(material[key] == original and all(number(v) and 0 <= v <= TOL for v in original.values()), 'panel material identity:' + key)
                require(material['reader_whole_KEY_q0_comparisons'] == r['candidate_q0_material_comparisons'], 'KEY q0 comparison mapping')
                for side in ('L', 'R'):
                    require(all(number(v) and 0 <= v <= TOL for v in r['candidate_q0_material_comparisons'][side].values()), 'KEY q0 identity')
                kmeta = f['native_scene_metadata']['named_KEY_candidate']
                require(kmeta['candidate_name'] == 'key_forward_loop_v1' and kmeta['candidate_source_sha256'] == K1, 'nested K1 source bridge')
                scope = loads(z.read('EXPORT_SCOPE.json'))
                require(scope['raw_runtime_durable_preservation_claimed'] is False and scope['raw_producer_reader_reports_modified'] is False, 'archive runtime scope')
                for path, wrapper in [('factory/worker/report.engineering.json', fw), ('readback/worker/report.engineering.json', rw)]:
                    projection = scope['derived_projections'][path]
                    require(projection['original'] == wrapper['original'] and projection['excluded_fields'] == wrapper['excluded_runtime_fields'], 'original/export projection scope')
                for filename, expected in derived_audit['audit_outputs'].items():
                    require(identity(audir / filename) == expected, 'frozen output identity')
                require(identity(arcpath) == actual_zip, 'original ZIP changed during independent read')
                report['archives'].append({'pose': pose, 'archive_identity': actual_zip,
                    'manifest_identity': byte_id(raw_manifest), 'all_manifest_members_independently_hashed': len(observed),
                    'all_member_CRC_read_to_EOF': True, 'uncompressed_member_bytes': sum(x['bytes'] for x in observed.values()),
                    'source_members_bound': len(contract['original_candidate_source_identities']), 'actual_K1_source_copies': k1_sources,
                    'current_material_byte_bindings': current_bindings, 'matrix_records': matrix_records,
                    'current_pose': {'slide_mm': f['pose_input']['slide'], 'KEY_q_mm_by_side': f['actual_q_by_side_mm'],
                        'all_154_STEP_and_BREP_bytes_bound': True, 'all_153_nonpanel_inventory_entries_unchanged': True,
                        'maximum_STEP_volume_delta_mm3': max_dv, 'maximum_STEP_bounds_delta_mm': max_db,
                        'all_11781_pair_comparisons_read': True, 'maximum_Common_delta_mm3': max_pair_delta,
                        'panel_KEY_direct_Common_factory_and_reader_zero_both_sides': all(
                            doc['panel_KEY_direct_Common'][s]['common_mm3'] == 0 for doc in (f,r) for s in ('L','R')),
                        'twelve_historical_independent_early_gates_recorded_pass': True,
                        'whole_panel_account': account},
                    'original_runtime_reports_available': False, 'new_native_execution': False})
        groups = []
        for sha, entries in sorted(record_groups.items()):
            require(len({x['projection_sha256'] for x in entries}) == 1, 'same original report projected inconsistently')
            groups.append({'original_report_sha256': sha, 'occurrences': len(entries), 'entries': entries})
        report['duplicate_record_classification'] = {'original_report_identity_groups': groups,
            'matrix_copies_read': sum(len(a['matrix_records']) for a in report['archives']),
            'unique_original_reports': len(groups),
            'unique_by_class': dict(collections.Counter(x['entries'][0]['class'] for x in groups)),
            'F1_failures_are_retained_historical_prerequisites_not_current_K3_failures': True,
            'duplicates_not_counted_as_independent_new_executions': True}
        after = {str(p.relative_to(ROOT)): identity(p) for p in frozen_paths}
        require(before == after, 'frozen audit inputs changed during review')
        report['frozen_input_identities'] = before
        report['completed'] = True
    except Exception as e:
        report['issues'].append({'type': type(e).__name__, 'message': str(e), 'traceback': traceback.format_exc()})
    report['seconds'] = time.monotonic() - started
    report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    output = HERE / 'R5_INDEPENDENT_NATIVE_ARCHIVE_REVIEW.json'
    with output.open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: report[k] for k in ('completed', 'seconds', 'peak_RSS_bytes', 'issues')}))
    return 0 if report['completed'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
