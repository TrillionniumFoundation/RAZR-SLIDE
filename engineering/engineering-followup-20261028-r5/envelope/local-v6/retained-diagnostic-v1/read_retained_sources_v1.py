"""Index original V6 retained observations; do not run geometric search."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction as F
import gc
import gzip
import hashlib
import json
from pathlib import Path
import resource
import signal
import time
import traceback

HERE = Path(__file__).resolve().parent
started = time.monotonic()
plan_path = HERE / 'R5_V6_RETAINED_SOURCE_DIAGNOSTIC_PLAN.json'
plan = json.loads(plan_path.read_text())
limits = plan['budget']
resource.setrlimit(resource.RLIMIT_AS, (limits['address_space_limit_bytes'], limits['address_space_limit_bytes']))
signal.signal(signal.SIGALRM, lambda signum, frame: (_ for _ in ()).throw(TimeoutError('preregistered readback wall limit')))
signal.alarm(limits['wall_seconds'])
decoded_total = 0


def identity(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest}


def read_gzip(path):
    global decoded_total
    parts = []; size = 0
    with gzip.open(path, 'rb') as stream:
        while chunk := stream.read(1048576):
            size += len(chunk); decoded_total += len(chunk)
            assert size <= limits['maximum_decoded_bytes_per_gzip']
            assert decoded_total <= limits['maximum_total_decoded_gzip_bytes']
            parts.append(chunk)
    data = b''.join(parts); del parts
    obj = json.loads(data); del data
    return obj, size


def box_numbers(box):
    return [[float(F(v)) for v in axis] for axis in box]


def face_summary(candidate):
    face = candidate['complete_original_face']
    return {'face_index': candidate['face_index'], 'canonical_sha256': candidate['complete_original_face_canonical_sha256'],
            'primitive': candidate['source_primitive'],
            'surface_radius': face['local_surface'].get('radius'),
            'wires': [{'is_outer': wire['is_outer'], 'orientation': wire.get('orientation'),
                       'occurrence_count': len(wire['edge_occurrences']),
                       'pcurve_types': dict(Counter(occ['pcurve']['type'] for occ in wire['edge_occurrences']))}
                      for wire in face['wires']]}


report = {'schema': 'r5-v6-existing-retained-source-readback-v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
          'completed': False, 'plan': identity(plan_path), 'reader_source': identity(__file__), 'frames': [],
          'actual_geometric_search_executions': 0, 'new_channel_tests': 0, 'new_curve_or_surface_enclosures': 0,
          'native_operations': 0, 'new_mathematical_qualification': False, 'full_continuous_G2': False, 'all_blockers_closed': False}
try:
    for row in plan['input_files']:
        assert identity(row['path']) == row
    report['input_identities'] = plan['input_files']
    full = json.loads(Path(plan['input_files'][0]['path']).read_text())
    projection, projection_size = read_gzip(plan['input_files'][2]['path'])
    records = {(r['input']['case_id'], r['input']['material_id']): r for r in projection['records']}
    report['primitive_source_decoded_bytes'] = projection_size
    for frame in full['frames']:
        if frame['primitive_support_model_conditional_clearance_gate_passed']:
            continue
        path = Path(plan['input_files'][0]['path']).parent / frame['certificate']['path']
        payload, size = read_gzip(path)
        sources = payload['boundary_refinement']['sources']
        reasons = Counter(); volume_by_reason = defaultdict(F)
        blockers = Counter(); cut_kinds = Counter(); candidates = []
        root_splits = []
        for root_index, root in enumerate(payload['roots']):
            nodes = root['tree']['nodes']; splits = sum(n['kind'] == 'split' for n in nodes)
            if splits:
                root_splits.append({'root_index': root_index, 'base_V5_leaf_locator': root['base_V5_leaf_locator'],
                                    'splits': splits, 'maximum_depth_reached': root['tree']['maximum_depth_reached'],
                                    'retained_sum_exact': root['tree']['retained_sum_exact']})
            pending = [(0, root['root_box_exact'], 0)]
            while pending:
                node_index, box, depth = pending.pop(); node = nodes[node_index]
                if node['kind'] == 'split':
                    cut_kinds[node['cut_source']['kind']] += 1
                    axis = node['axis']; cut = node['cut_exact']
                    low = [list(a) for a in box]; high = [list(a) for a in box]
                    low[axis][1] = cut; high[axis][0] = cut
                    pending.extend([(node['children'][0], low, depth + 1), (node['children'][1], high, depth + 1)])
                elif node['kind'] == 'retained':
                    value = F(node['positive_directed_volume_exact']); reason = node['reason']
                    reasons[reason] += 1; volume_by_reason[reason] += value
                    observations = node.get('actual_channel_observation', {}).get('all_registered_channels_unresolved', [])
                    for observation in observations:
                        side = observation['material_side']; piece = sources[side]['pieces'][observation['unresolved_piece_index']]
                        blockers[(side, piece['kind'], piece['index'], piece['replacement'], piece.get('parameter_patch_index'))] += 1
                    candidates.append((value, root_index, node_index, depth, box, node, root['base_V5_leaf_locator']))
        assert sum(volume_by_reason.values(), F(0)) == F(frame['retained_leaf_sum_exact'])
        candidates.sort(key=lambda row: row[0], reverse=True)
        selected = []
        for value, root_index, node_index, depth, box, node, locator in candidates[:limits['maximum_selected_leaves_per_frame']]:
            observed = []
            for obs in node.get('actual_channel_observation', {}).get('all_registered_channels_unresolved', []):
                side = obs['material_side']; source = sources[side]; piece_index = obs['unresolved_piece_index']; piece = source['pieces'][piece_index]
                material = tuple(source['material_key']); faces = {r['face_index']: r for r in records[material]['candidate_faces']}
                candidate = faces.get(piece['index']) if piece['kind'] == 'face' else None
                certificate = source['face_certificates'][piece['face_certificate_index']] if 'face_certificate_index' in piece else None
                observed.append(dict(obs, material_key=list(material), original_kind=piece['kind'], original_index=piece['index'],
                    replacement=piece['replacement'], parameter_patch_index=piece.get('parameter_patch_index'),
                    box_numeric=box_numbers(piece['box_exact']),
                    additional_slabs_numeric=[{'source': s['source'], 'normal': [float(F(v)) for v in s['normal_exact']],
                                               'bounds': [float(F(v)) for v in s['bounds_exact']]} for s in piece['additional_slabs']],
                    original_face=face_summary(candidate) if candidate else None,
                    primitive_certificate_domain={k: v for k, v in (certificate or {}).items() if k in ['complete_source_UV_domain_exact', 'angular_patch_count']},
                    original_certificate_piece_locator={'source_index': side, 'piece_index': piece_index}))
            selected.append({'root_index': root_index, 'base_V5_leaf_locator': locator, 'node_index': node_index,
                             'depth': depth, 'positive_directed_volume_exact': str(value), 'volume_numeric': float(value),
                             'reason': node['reason'], 'box_exact': box, 'box_numeric': box_numbers(box),
                             'recorded_unresolved_channels': observed})
        report['frames'].append({'case_id': frame['case_id'], 'frame': frame['frame'], 'pair': frame['pair'],
            'certificate': identity(path), 'decoded_bytes': size,
            'current_conditional_upper_mm3': frame['primitive_support_model_conditional_upper_mm3'],
            'complete_original_D_exact': frame['original_remaining_displacement_box_exact'],
            'complete_original_D_numeric': box_numbers(frame['original_remaining_displacement_box_exact']),
            'retained_reason_counts': dict(reasons),
            'retained_volume_by_reason_exact': {k: str(v) for k, v in volume_by_reason.items()},
            'retained_volume_by_reason_numeric': {k: float(v) for k, v in volume_by_reason.items()},
            'actual_split_source_counts': dict(cut_kinds), 'roots_with_actual_new_splits': root_splits,
            'recorded_blocker_counts': [{'material_side': k[0], 'kind': k[1], 'index': k[2], 'replacement': k[3], 'patch_index': k[4], 'recorded_channel_count': v}
                                      for k, v in blockers.most_common()],
            'selected_largest_retained_leaves': selected})
        del payload, candidates, sources, selected, nodes
        gc.collect()
    assert len(report['frames']) == 8
    assert all(identity(row['path']) == row for row in plan['input_files'])
    report['all_inputs_unchanged'] = True
    report['completed'] = True
except BaseException as exc:
    report['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
finally:
    signal.alarm(0)
    report['decoded_bytes_total'] = decoded_total
    report['elapsed_seconds'] = time.monotonic() - started
    report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    target = HERE / 'R5_V6_RETAINED_SOURCE_DIAGNOSTIC_ACTUAL.json'
    assert not target.exists()
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'completed': report['completed'], 'failure': report.get('failure'), 'frames': len(report['frames']),
                      'elapsed_seconds': report['elapsed_seconds'], 'peak_RSS_bytes': report['peak_RSS_bytes'],
                      'decoded_bytes_total': decoded_total, 'report': identity(target)}))
