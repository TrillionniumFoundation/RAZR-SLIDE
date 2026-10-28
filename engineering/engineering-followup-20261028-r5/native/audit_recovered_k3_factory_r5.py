"""Stream-verify original K3 factory archives; no CAD imports or native rerun.

Every member is read to EOF (ZIP CRC) and hashed against the original manifest.
Historical full matrices and journals are checked as recorded evidence. This
does not turn the historical projection into its omitted raw runtime report.
"""
from pathlib import Path, PurePosixPath
import argparse
from collections import Counter
import gzip
import hashlib
import itertools
import json
import math
import os
import resource
import stat
import time
import traceback
import zipfile

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
K1_SOURCE = '3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578'
K3_SOURCE = '59946f42f8bff88b0cdb8bcd2ad7f578e22e6f64e65832a6b6087426e282e5a5'
K3_CONTRACT = '0f3ec4af155a2e92650f49ada7042e6d1fc1f8ad94cb43f6716a77985ecc5b84'
TOL = 1e-7


def need(ok, message):
    if not ok:
        raise ValueError(message)


def file_identity(path):
    with Path(path).open('rb') as stream:
        return {'bytes': Path(path).stat().st_size,
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def byte_identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            need(k not in result, 'Duplicate JSON key: ' + k)
            result[k] = v
        return result
    def bad(value):
        raise ValueError('Non-finite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


def guard_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def audit_matrix(archive, relative, wrapper, observed, journal_output):
    r = wrapper['engineering_record']
    need(wrapper['derived_projection_not_raw_original'] is True, 'Projection scope missing')
    names = r['participant_names']
    expected = list(itertools.combinations(sorted(names), 2))
    rows = r['pairs']
    need(len(names) == len(set(names)) and len(names) in (154, 161), 'Full participant roster differs')
    need([(x['a'], x['b']) for x in rows] == expected, 'Full unordered matrix is incomplete or reordered')
    need(r['all_unordered_pairs_present_once'] is True and r['execution_completed'] is True,
         'Historical complete matrix not recorded')
    need(not r['evaluation_failures'] and not r.get('mismatches_to_factory'), 'Historical evaluation or consistency failure')
    need(r['functional_source_commit'] == S4, 'Original functional source differs')
    rejected = []
    for i, row in enumerate(rows):
        v = row['common_mm3']
        need(guard_number(v) and row['rejected'] == (v > TOL), 'Invalid original volume or threshold classification')
        need(row['method'] in ('positive_axis_gap', 'native_common'), 'Unknown original Common method')
        need(not row.get('evaluation_failed') and not row.get('post_evaluation_failure'), 'Original pair evaluation failed')
        if row['method'] == 'positive_axis_gap':
            need(v == 0 and row['axis_gap_lower_mm'] > 0, 'Broad phase record is inconsistent')
        if row['rejected']:
            rejected.append({'a': row['a'], 'b': row['b'], 'common_mm3': v})
    need(r['finite_pose_clear'] == (not rejected), 'Historical finite classification differs from full matrix')
    for flag in ('G2_pass', 'complete_product_motion_proved', 'continuous_backlash_domain_proved',
                 'physical_qualification', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go'):
        need(r.get(flag) is False, 'A finite record improperly claims ' + flag)
    journal = str(PurePosixPath(relative).parent / 'pairs.jsonl')
    need(journal in observed, 'Original matrix journal absent')
    count = 0
    with archive.open(journal) as stream:
        for line in stream:
            value = strict_json(line)
            i, event = divmod(count, 2)
            need(i < len(rows), 'Extra journal row')
            if event == 0:
                need(value == {'event': 'selected', 'a': rows[i]['a'], 'b': rows[i]['b']}, 'Journal selected event differs')
            else:
                need(value == {'event': 'completed', 'row': rows[i]}, 'Journal completed row differs')
            count += 1
    need(count == 2 * len(rows), 'Journal missing selected/completed event')
    for side in 'LR':
        direct = r['panel_KEY_direct_Common'][side]
        pair = next(x for x in rows if (x['a'], x['b']) == ('A_BACK_PANEL', side + '_KEY'))
        need(guard_number(direct['common_mm3']) and abs(direct['common_mm3'] - pair['common_mm3']) <= TOL,
             'Direct panel/KEY volume differs from matrix')
        need(direct['rejected'] == pair['rejected'], 'Direct panel/KEY classification differs')
        need(abs(direct['strict_common']['common_mm3'] - direct['common_mm3']) <= TOL,
             'Direct Common differs from original strict Common')
    ident = r['source_identity_projection']
    need(ident['source_commit_before'] == ident['source_commit_after'] == S4,
         'Historical source identity projection differs')
    need(ident['worktree_clean_before'] is True and ident['source_bytes_and_locked_environment_unchanged'] is True,
         'Historical source mutation or unclosed source audit')
    need(ident['locked_environment_before_passed'] is True and ident['locked_environment_after_passed'] is True and
         ident['checked_package_count_before'] == ident['checked_package_count_after'] == 43,
         'Historical 43-version result projection differs')
    journal_output.write(json.dumps({'report_member': relative, 'report_identity': observed[relative],
        'historical_original_report_identity': wrapper['original'], 'pairs': rows}, separators=(',', ':'),
        allow_nan=False).encode() + b'\n')
    return {'report_member': relative, 'projection_identity': observed[relative],
            'historical_original_report_identity': wrapper['original'],
            'omitted_runtime_fields': wrapper['excluded_runtime_fields'],
            'participant_count': len(names), 'pair_count': len(rows),
            'journal_rows': count, 'method_counts': dict(Counter(x['method'] for x in rows)),
            'finite_pose_clear_recorded_and_matrix_consistent': not rejected,
            'retained_rejected_pairs': rejected, 'panel_KEY_direct_Common': r['panel_KEY_direct_Common'],
            'historical_source_and_43_version_projection_consistent': True,
            'historical_runtime_requalified': False}


def run(a):
    c = strict_json(a.contract.read_bytes())
    need(file_identity(__file__) == c['worker_identity'], 'Audit worker identity differs')
    need(c['original_tolerance_mm3'] == TOL, 'Original threshold changed')
    need(file_identity(c['source_acceptance']['path']) == c['source_acceptance']['identity'], 'Acceptance source differs')
    acceptance = strict_json(Path(c['source_acceptance']['path']).read_bytes())
    expected = next(x for x in acceptance['rows'] if x['pose'] == a.pose)
    ref = expected['scientific_artifact']
    a.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {'schema': 'razr-r5-recovered-current-k3-factory-audit-v1', 'pose': a.pose,
        'worker_identity': file_identity(__file__), 'contract_identity': file_identity(a.contract),
        'completed': False, 'issues': [], 'historical_run_id': 40285103942,
        'historical_diagnostic_commit': acceptance['diagnostic_commit'],
        'functional_source_commit': S4, 'new_native_execution': False,
        'historical_runtime_requalified': False, 'original_raw_runtime_reports_reconstructed': False,
        'full_continuous_domain_proved': False, 'physical_qualification': False,
        'candidate_go': False, 'G2_pass': False, 'source_acceptance': c['source_acceptance'],
        'archive_expected': {'bytes': ref['zip_bytes'], 'sha256': ref['zip_sha256']},
        'verified_member_count': 0, 'verified_member_bytes': 0, 'matrices': []}
    def persist():
        report['seconds'] = time.monotonic() - started
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        (a.out / 'R5_K3_ARCHIVE_AUDIT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    def check_resource():
        need(time.monotonic() - started < c['readonly_audit_wall_seconds'], 'Readonly audit wall bound exceeded')
        need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 < c['readonly_audit_RSS_bytes'],
             'Readonly audit memory bound exceeded')
    try:
        actual = file_identity(a.archive)
        report['archive_actual'] = actual
        need(actual == report['archive_expected'], 'Original whole ZIP identity differs')
        with zipfile.ZipFile(a.archive) as z:
            entries = z.infolist()
            need(len(entries) == len({x.filename for x in entries}), 'Duplicate ZIP member')
            for x in entries:
                p = PurePosixPath(x.filename)
                need(not p.is_absolute() and '..' not in p.parts and not x.is_dir() and
                     not stat.S_ISLNK(x.external_attr >> 16), 'Unsafe ZIP member')
                need(x.file_size <= c['maximum_single_member_bytes'], 'Oversize uncompressed member')
            raw = z.read('ENGINEERING_MANIFEST.json')
            need(hashlib.sha256(raw).hexdigest() == ref['manifest_sha256'], 'Original manifest identity differs')
            manifest = strict_json(raw)['members']
            need(len(manifest) == ref['manifest_entries'], 'Original member count differs')
            need(set(z.namelist()) == set(manifest) | {'ENGINEERING_MANIFEST.json'}, 'Original member set differs')
            observed = {}
            for i, (name, want) in enumerate(sorted(manifest.items())):
                check_resource()
                h = hashlib.sha256(); size = 0
                with z.open(name) as stream:
                    for block in iter(lambda: stream.read(1048576), b''):
                        h.update(block); size += len(block)
                got = {'bytes': size, 'sha256': h.hexdigest()}
                need(got == want, 'Original member identity differs: ' + name)
                observed[name] = got
                report['verified_member_count'] += 1
                report['verified_member_bytes'] += size
                if (i + 1) % 512 == 0:
                    persist()
            report['all_manifest_members_SHA_size_and_ZIP_CRC_verified'] = True
            for name, want in c['original_candidate_source_identities'].items():
                need(observed['source/k3full/' + name] == want, 'Frozen K1/K3 source or contract differs')
            sources = {}
            for name in ('factory', 'readback'):
                path = name + '/worker/report.engineering.json'
                sources[name] = strict_json(z.read(path))
            f, r = [sources[n]['engineering_record'] for n in ('factory', 'readback')]
            for n, body in [('factory', f), ('readback', r)]:
                expected_mode = expected['producer' if n == 'factory' else 'independent_STEP_reader']
                need(observed[n+'/worker/report.engineering.json']['sha256'] == expected_mode['projection_sha256'],
                     'Current K3 report differs from known source record')
                need(sources[n]['original']['sha256'] == expected_mode['original_report_sha256'], 'Historical raw report SHA differs')
                need(body['pose'] == a.pose and body['candidate_name'] == 'panel_key_travel_stops_v1' and
                     body['candidate_source_sha256'] == K3_SOURCE and body['candidate_contract_sha256'] == K3_CONTRACT,
                     'Current K3 candidate or pose differs')
                need(body['actual_q_by_side_mm'] == expected['actual_q_by_side_mm'], 'KEY q coordinate differs')
                need(body['pose_input']['slide'] == expected['declared_pose']['slide'], 'Slide coordinate differs')
                need(body['native_early_conditions_rechecked'] is True, 'Early conditions not rechecked')
            need(r['factory_report_sha256'] == sources['factory']['original']['sha256'], 'Independent reader bound to different raw producer')
            names = f['participant_names']
            need(len(names) == 154 and set(f['body_exports']) == set(r['body_readbacks']) == set(names),
                 'Current whole-body export/readback inventory incomplete')
            body_refs = {}
            for name in names:
                row = f['body_exports'][name]
                need(row['signature_before'] == row['signature_after'] and row['serialization_preserved_in_memory_signature'] is True,
                     'Serialization changed whole body signature')
                for ext in ('step', 'brep'):
                    b = row['files'][ext]; member = 'factory/worker/' + b['path']
                    need(observed[member] == {k: b[k] for k in ('bytes', 'sha256')}, 'Whole participant export not bound to original bytes')
                read = r['body_readbacks'][name]
                need(read['passed'] is True and read['STEP'] == row['files']['step'], 'Original STEP reader mismatch')
                body_refs[name] = {'factory_exports': row['files'], 'reader_record': read}
            need(r['native_STEP_readback_executed'] is True and r['separate_process_from_factory'] is True and
                 r['independent_CAD_kernel'] is False and r['independent_material_builder_does_not_import_candidate_source'] is True,
                 'Original independent reader scope differs')
            gates = r['independent_early_gate_records']
            need(len(gates) == 12 and all(x['evaluated'] is True and x['passed'] is True for x in gates.values()),
                 'Not all 12 independent middle-pose gates passed')
            need(not r['independent_native_evaluation_failures'] and not r['independent_geometric_gate_rejections'],
                 'Independent early gate failure')
            comparisons = []
            for first, second in zip(f['pairs'], r['pairs']):
                need((first['a'], first['b']) == (second['a'], second['b']), 'Producer and reader matrix order differs')
                dv = second['common_mm3'] - first['common_mm3']
                need(abs(dv) <= TOL and first['rejected'] == second['rejected'], 'Producer and reader volume or classification differs')
                comparisons.append({'a': first['a'], 'b': first['b'], 'factory_Common_mm3': first['common_mm3'],
                                    'reader_Common_mm3': second['common_mm3'], 'difference_mm3': dv,
                                    'threshold_classification_equal': first['rejected'] == second['rejected']})
            with (a.out / 'all-historical-matrices.jsonl.gz').open('wb') as stream:
                with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as rows_out:
                    for path in sorted(n for n in manifest if n.endswith('/worker/report.engineering.json')):
                        check_resource()
                        wrapper = strict_json(z.read(path))
                        if wrapper['engineering_record'].get('all_unordered_pairs_present_once') is True:
                            report['matrices'].append(audit_matrix(z, path, wrapper, observed, rows_out))
            material = {'source': 'original full material comparisons and original separate STEP reader',
                        'new_geometry_evaluated': False,
                        'whole_panel_material_account': f['candidate_application']['actual_added_only_panel_account'],
                        'factory_original_panel_to_verified_pilot': f['original_panel_to_verified_pilot_material'],
                        'factory_new_panel_to_named_candidate': f['new_panel_to_named_candidate_material'],
                        'factory_new_panel_to_dual_pilot': f['new_panel_to_actual_dual_pilot_material'],
                        'reader_new_panel_to_dual_pilot': r['new_panel_to_actual_dual_pilot_material'],
                        'reader_whole_KEY_q0_comparisons': r['candidate_q0_material_comparisons'],
                        'actual_positive_panel_joins': f['candidate_application']['actual_positive_joins'],
                        'original_cover_functional_faces': f['candidate_application']['original_cover_functional_face_material_preserved'],
                        'independent_material_gates': gates,
                        'K3_prerequisite': f['K3_prerequisite'],
                        'current_whole_material_bytes': {k: body_refs[k] for k in ('A_BACK_PANEL','L_KEY','R_KEY')}}
            outdata = {'all_154_body_readbacks': body_refs, 'all_11781_pair_readback_comparisons': comparisons,
                       'material_identity_bridge': material}
            with (a.out/'current-pose-complete-readback.json.gz').open('wb') as stream:
                with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as gz:
                    gz.write(json.dumps(outdata, separators=(',', ':'), allow_nan=False).encode()+b'\n')
            report['material_identity_bridge'] = material
            report['current_pose_summary'] = {'slide_mm': f['pose_input']['slide'], 'KEY_q_mm_by_side': f['actual_q_by_side_mm'],
                'body_count': 154, 'current_pose_pair_rows_factory_plus_reader': len(f['pairs'])+len(r['pairs']),
                'current_pose_journal_rows': 4*len(f['pairs']), 'independent_early_gates': len(gates),
                'all_pair_readbacks_consistent': True, 'finite_pose_clear': f['finite_pose_clear'] and r['finite_pose_clear'],
                'panel_KEY_direct_Common': {n: sources[n]['engineering_record']['panel_KEY_direct_Common'] for n in sources}}
            report['whole_ZIP_unchanged_after_audit'] = file_identity(a.archive) == actual
            need(report['whole_ZIP_unchanged_after_audit'], 'Archive changed during audit')
            for name in ('all-historical-matrices.jsonl.gz','current-pose-complete-readback.json.gz'):
                report.setdefault('audit_outputs', {})[name] = file_identity(a.out/name)
            report['completed'] = True
    except BaseException as exc:
        report['issues'].append({'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
    persist()
    print(json.dumps({k: report[k] for k in ('pose','completed','verified_member_count','verified_member_bytes','seconds','peak_RSS_bytes','issues')}))
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--pose', choices=('near','far'), required=True)
    raise SystemExit(run(ap.parse_args()))
