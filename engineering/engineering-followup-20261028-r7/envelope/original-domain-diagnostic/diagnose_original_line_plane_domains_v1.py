"""Bounded original-source diagnosis, independent of all envelope producers.

Reads the recovered R3E producer and native reader and the original R4 proof.
No producer import, native operation, new channel search or gate reclassification.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import gc
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

IDENTITY = [['1', '0', '0', '0'], ['0', '1', '0', '0'], ['0', '0', '1', '0']]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def ident(path):
    p = Path(path).resolve()
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': h.hexdigest()}


def same(a, b):
    return all(a[k] == b[k] for k in ('bytes', 'sha256'))


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def q(x):
    return F(x['exact']) if isinstance(x, dict) else F(x)


def encbox(value):
    return [[str(x) for x in pair] for pair in value]


def load_bound(row, compressed=False, cap=67108864):
    path = Path(row['path'])
    need(same(ident(path), row), 'original identity mismatch: ' + str(path))
    if compressed:
        with gzip.open(path, 'rb') as stream:
            raw = stream.read(cap + 1)
    else:
        need(path.stat().st_size <= cap, 'registered input byte cap exceeded')
        raw = path.read_bytes()
    need(len(raw) <= cap, 'registered decoded byte cap exceeded')
    return json.loads(raw)


def select_originals(row):
    document = load_bound(row)
    need(document['execution_completed'] and len(document['operands']) == 53,
         'complete original executed 53-material inventory required')
    keys = [(r['input']['case_id'], r['input']['material_id']) for r in document['operands']]
    need(len(set(keys)) == 53, 'unique original materials required')
    result = []
    for material_id in (1, 3):
        item = document['operands'][keys.index(('case-028', material_id))]
        boundary = item['boundary']
        need(not boundary['incomplete_inventory'], 'incomplete original material')
        need(boundary['location']['matrix_3x4_exact'] == IDENTITY, 'original material placement differs')
        for name in ('solids', 'shells', 'faces', 'edges', 'vertices'):
            need(len(boundary[name]) == boundary['counts'][name], 'original count differs: ' + name)
            need([x['index'] for x in boundary[name]] == list(range(len(boundary[name]))),
                 'complete ordered original indices required')
        record = {'input': item['input'], 'original_complete_boundary_counts': boundary['counts'],
                  'original_complete_boundary_canonical_sha256': canonical(boundary),
                  'candidate_faces': []}
        if material_id == 3:
            for index in (27, 42):
                face = boundary['faces'][index]
                record['candidate_faces'].append({'face_index': index,
                    'complete_original_face': face,
                    'complete_original_face_canonical_sha256': canonical(face)})
        result.append(record)
    del document
    gc.collect()
    return result


def domains_and_endpoints(face):
    need(face['location']['matrix_3x4_exact'] == IDENTITY, 'identity original face required')
    surface = face['local_surface']
    need(surface['type'] == 'GeomAbs_SurfaceType.GeomAbs_Plane', 'original affine Plane required')
    uv = [tuple(map(q, surface[k])) for k in ('U_interval', 'V_interval')]
    need(all(a <= b for a, b in uv), 'ordered surface intervals required')
    hull = list(uv)
    pieces = []
    need(face['wires'], 'complete original wires required')
    for wi, wire in enumerate(face['wires']):
        need(wire['location']['matrix_3x4_exact'] == IDENTITY and wire['native_IsClosed'],
             'complete identity native-closed wire metadata required')
        need(wire['edge_occurrences'], 'nonempty original wire required')
        for oi, occurrence in enumerate(wire['edge_occurrences']):
            need(occurrence['location']['matrix_3x4_exact'] == IDENTITY and occurrence['edge_index'] is not None,
                 'complete mapped identity occurrence required')
            curve = occurrence['pcurve']
            need(curve['type'].split('.')[-1] == 'GeomAbs_Line', 'this diagnostic admits only the original Lines')
            a, b = q(curve['first_parameter']), q(curve['last_parameter'])
            need(a <= b, 'complete ordered source Line interval required')
            origin, direction = tuple(map(q, curve['origin_exact'])), tuple(map(q, curve['direction_exact']))
            need(len(origin) == len(direction) == 2 and any(direction), 'nonzero exact 2D Line required')
            endpoints = [tuple(origin[k] + direction[k] * t for k in (0, 1)) for t in (a, b)]
            support = [(min(p[k] for p in endpoints), max(p[k] for p in endpoints)) for k in (0, 1)]
            hull = [(min(hull[k][0], support[k][0]), max(hull[k][1], support[k][1])) for k in (0, 1)]
            pieces.append({'wire_index': wire['index'], 'wire_position': wi, 'occurrence_index': oi,
                           'source_edge_index': occurrence['edge_index'],
                           'source_parameter_interval_exact': [str(a), str(b)],
                           'endpoint_coordinates_exact': [[str(x) for x in p] for p in endpoints],
                           'complete_Line_support_box_exact': encbox(support)})
    return uv, hull, pieces


def map_by_corners(surface, uv):
    O, X, Y = [tuple(map(q, surface[k])) for k in ('origin_exact', 'X_exact', 'Y_exact')]
    need(len(O) == len(X) == len(Y) == 3, 'three-dimensional source basis required')
    points = [tuple(O[k] + X[k] * u + Y[k] * v for k in range(3)) for u, v in itertools.product(*uv)]
    return [(min(p[k] for p in points), max(p[k] for p in points)) for k in range(3)], points


def map_by_interval_support(surface, uv):
    O, X, Y = [tuple(map(q, surface[k])) for k in ('origin_exact', 'X_exact', 'Y_exact')]
    result = []
    for k in range(3):
        first = sorted(X[k] * a for a in uv[0])
        second = sorted(Y[k] * a for a in uv[1])
        result.append((O[k] + first[0] + second[0], O[k] + first[1] + second[1]))
    return result


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0,
         'isolated unoptimized Python entry required')
    contract = json.loads(args.contract.read_text())
    need(contract['schema'] == 'razr-r7e-original-Line-plane-domain-diagnostic-contract-v1', 'registered diagnostic schema required')
    need(contract['wall_seconds'] == 60 and contract['address_space_bytes'] == 536870912,
         'diagnostic resource registration differs')
    need(same(ident(__file__), contract['source']), 'registered diagnostic source differs')
    need(not args.output.exists(), 'new diagnostic output directory required')
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('registered 60-second diagnostic limit')))
    signal.alarm(60)
    report = {'schema': 'razr-r7e-original-Line-plane-domain-diagnostic-v1',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'completed': False,
              'native_operations': 0, 'channel_searches': 0, 'producer_imports': 0,
              'missing_V8_artifacts_reconstructed': False, 'new_scientific_pass_claimed': False,
              'full_continuous_G2': False, 'all_blockers_closed': False,
              'source': ident(__file__), 'contract': ident(args.contract), 'rows': []}
    try:
        rows = contract['inputs']
        identities = {name: ident(row['path']) for name, row in rows.items()}
        need(all(same(identities[name], row) for name, row in rows.items()), 'complete original input binding differs')
        basis = load_bound(rows['original_R4_report'])
        expected_inputs = {r['path']: r for r in basis['input_identities']}
        need(same(rows['native_producer'], expected_inputs['native-and-math/producer/worker/report.json']), 'original R4 producer binding differs')
        need(same(rows['native_reader'], expected_inputs['native-and-math/reader/worker/report.json']), 'original R4 reader binding differs')
        frame = next(f for f in basis['frames'] if (f['case_id'], f['frame']) == ('case-028', 1))
        need(same(rows['original_R4_frame_proof'], frame['proof']), 'original R4 proof binding differs')
        selected = select_originals(rows['native_producer'])
        independently_read = select_originals(rows['native_reader'])
        need(selected == independently_read, 'independent original whole-material and full-face readback differs')
        proof = load_bound(rows['original_R4_frame_proof'], compressed=True)
        need((proof['case_id'], proof['frame']) == ('case-028', 1), 'original witness frame differs')
        need(proof['moving_input'] == selected[1]['input'], 'moving original material identity differs')
        D = [tuple(map(F, p)) for p in proof['full_remaining_displacement_box_exact']]
        need(encbox(D) == frame['full_remaining_displacement_box_exact'], 'complete original D differs')
        raw = proof['complete_raw_boundary_slab_cover']['first_complete_boundary_boxes']
        need(len(raw) == sum(selected[1]['original_complete_boundary_counts'][k] for k in ('faces', 'edges', 'vertices')),
             'complete original carrier census differs')
        originals = {c['index']: c for c in raw if c['kind'] == 'face'}
        total_occurrences = 0
        for candidate in selected[1]['candidate_faces']:
            face = candidate['complete_original_face']
            uv, hull, pieces = domains_and_endpoints(face)
            total_occurrences += len(pieces)
            pure, pure_corners = map_by_corners(face['local_surface'], uv)
            complete, full_corners = map_by_corners(face['local_surface'], hull)
            need(complete == map_by_interval_support(face['local_surface'], hull), 'independent exact corner/support formulations differ')
            swept_pure = [(pure[k][0] + D[k][0], pure[k][1] + D[k][1]) for k in range(3)]
            swept_complete = [(complete[k][0] + D[k][0], complete[k][1] + D[k][1]) for k in range(3)]
            inherited = [tuple(map(F, p)) for p in originals[face['index']]['box_exact']]
            differences = [{'axis': k, 'end': j, 'surface_only_minus_original_exact': str(swept_pure[k][j] - inherited[k][j]),
                            'full_hull_minus_original_exact': str(swept_complete[k][j] - inherited[k][j])}
                           for k in range(3) for j in range(2)]
            need(swept_complete == inherited, 'complete original Line/UV hull does not reproduce every inherited box endpoint')
            report['rows'].append({'material_key': ['case-028', 3], 'face_index': face['index'],
                'source_face_canonical_sha256': candidate['complete_original_face_canonical_sha256'],
                'surface_UV_intervals_exact': encbox(uv), 'complete_surface_and_all_Line_hull_exact': encbox(hull),
                'original_occurrences': pieces, 'occurrence_count': len(pieces),
                'surface_only_stationary_box_exact': encbox(pure),
                'complete_hull_stationary_box_exact': encbox(complete),
                'full_hull_corners_exact': [[str(x) for x in p] for p in full_corners],
                'full_original_D_exact': encbox(D), 'inherited_swept_original_box_exact': encbox(inherited),
                'surface_only_forward_matches': swept_pure == inherited,
                'full_hull_forward_matches_all_six_endpoints': True, 'endpoint_differences': differences,
                'native_region_membership_established': False})
        need(total_occurrences == 18 and [r['occurrence_count'] for r in report['rows']] == [14, 4],
             'original two-face 18-Line census differs')
        projection = {'schema': 'razr-r7e-lossless-original-two-Line-plane-projection-v9',
                      'original_native_producer': identities['native_producer'],
                      'original_native_independent_reader': identities['native_reader'],
                      'original_R4_report': identities['original_R4_report'],
                      'original_R4_frame_proof': identities['original_R4_frame_proof'],
                      'records': selected, 'complete_original_D_exact': encbox(D),
                      'original_values_changed': False, 'native_semantics_verified': False,
                      'new_mathematical_qualification': False}
        projection_path = args.output / 'R7E_V9_ORIGINAL_LINE_PLANE_PROJECTION.json'
        projection_path.write_text(json.dumps(projection, indent=2) + '\n')
        after = {name: ident(row['path']) for name, row in rows.items()}
        need(all(same(after[name], identities[name]) for name in rows), 'original input changed during diagnostic')
        report.update(completed=True, complete_original_occurrence_count=total_occurrences,
                      all_original_inputs_unchanged=True, input_identities=identities,
                      native_producer_reader_full_selected_material_records_equal=True,
                      original_carrier_count=len(raw), original_full_D_exact=encbox(D),
                      projection=ident(projection_path))
    except Exception as exc:
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        report.update(elapsed_seconds=time.monotonic() - started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      wall_seconds=60, address_space_bytes=536870912,
                      finished_utc=datetime.now(timezone.utc).isoformat())
        path = args.output / 'R7E_ORIGINAL_LINE_PLANE_DOMAIN_DIAGNOSIS_V1.json'
        path.write_text(json.dumps(report, indent=2) + '\n')
        need(path.stat().st_size <= 1048576, 'diagnostic output exceeds registered finite cap')
    print(json.dumps({'completed': report['completed'], 'elapsed_seconds': report['elapsed_seconds'],
                      'peak_RSS_bytes': report['peak_RSS_bytes'], 'report': ident(path),
                      'failure': report.get('failure')}, separators=(',', ':')))
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
