"""Exact exterior-channel refinement of registered complete R4 boundary covers.

This is a conditional exact-real proof transformation, not native CAD execution.
No native Common or old zero-Common value is an acceptance premise.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_bound(record):
    path = Path(record['path'])
    require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], 'bound input identity differs: '+str(path))
    return path


def decode(box):
    result = [tuple(map(F, interval)) for interval in box]
    require(len(result) == 3 and all(len(i) == 2 and i[0] <= i[1] for i in result), 'ordered finite 3D box required')
    return result


def encode(box):
    return [[str(v) for v in interval] for interval in box]


def volume(box):
    if any(lo >= hi for lo, hi in box):
        return F(0)
    value = F(1)
    for lo, hi in box:
        value *= hi-lo
    return value


def separation(piece, channel):
    # Codes 2*k and 2*k+1 mean closed piece lies below/above open channel.
    # Zero-thickness boundary pieces are not removed.
    for axis in range(3):
        if piece[axis][1] <= channel[axis][0]:
            return 2*axis
        if piece[axis][0] >= channel[axis][1]:
            return 2*axis+1
    return None


def channel_for(cell, whole, axis, end):
    result = list(cell)
    # Exactly 1 mm beyond the complete support box, with no floating operation.
    if end == 0:
        result[axis] = (min(whole[axis][0]-1, cell[axis][0]-1), cell[axis][1])
    else:
        result[axis] = (cell[axis][0], max(whole[axis][1]+1, cell[axis][1]+1))
    require(all(lo < hi for lo, hi in result), 'open channel must be positive and connected')
    return result


def try_exterior(cell, sources, counters):
    failures = []
    for side, source in enumerate(sources):
        for axis in range(3):
            for end in (0, 1):
                channel = channel_for(cell, source['whole'], axis, end)
                codes = []
                blocker = None
                counters['channels_tested'] += 1
                for index, piece in enumerate(source['pieces']):
                    counters['boundary_box_tests'] += 1
                    code = separation(piece, channel)
                    if code is None:
                        blocker = index
                        break
                    codes.append(str(code))
                if blocker is None:
                    require(len(codes) == len(source['pieces']), 'complete boundary coverage needed')
                    return {'excluded_open_interior': True, 'material_side': side,
                            'axis': axis, 'end': end, 'open_channel_exact': encode(channel),
                            'complete_piece_separation_codes': ''.join(codes),
                            'boundary_piece_count': len(codes),
                            'closed_cell_boundary_retained_as_zero_volume_carrier': True,
                            'whole_closed_cell_disjoint_claimed': False}
                failures.append({'material_side': side, 'axis': axis, 'end': end,
                                 'blocking_piece_index': blocker})
    return {'excluded_open_interior': False, 'all_registered_channels_blocked': failures,
            'actual_material_interference_claimed': False}


def source_records(proof, stationary=False):
    cover = proof['complete_raw_boundary_slab_cover']
    displacement = decode(proof['full_remaining_displacement_box_exact'])
    sources = []
    for side, name in enumerate(('first_complete_boundary_boxes', 'second_complete_boundary_boxes')):
        records = cover[name]
        require(records, 'complete material boundary boxes required')
        pieces = []
        for item in records:
            box = decode(item['box_exact'])
            if stationary and side == 0:
                box = [(box[k][0]-displacement[k][0], box[k][1]-displacement[k][1]) for k in range(3)]
            require(all(lo <= hi for lo, hi in box), 'invalid recovered stationary box')
            pieces.append(box)
        whole = [(min(box[k][0] for box in pieces), max(box[k][1] for box in pieces)) for k in range(3)]
        declared = decode(cover['first_whole_support_box_exact' if side == 0 else 'second_whole_support_box_exact'])
        if stationary and side == 0:
            declared = [(declared[k][0]-displacement[k][0], declared[k][1]-displacement[k][1]) for k in range(3)]
        require(whole == declared, 'complete boundary hull differs from bound support')
        sources.append({'pieces': pieces, 'whole': whole,
                        'identities': [{'kind': p['kind'], 'index': p['index']} for p in records]})
    return sources


def controlled_examples():
    def cube(lo, hi):
        ranges = [(F(lo), F(hi))]*3
        boxes = []
        for axis in range(3):
            for end in (0, 1):
                box = list(ranges); box[axis] = (ranges[axis][end],)*2; boxes.append(box)
        return {'pieces': boxes, 'whole': ranges}
    unit = cube(0, 1)
    counter = {'channels_tested': 0, 'boundary_box_tests': 0}
    examples = []
    for name, box, expected in [
        ('genuine-closed-cube-interior-retained', [(F(1,4), F(3,4))]*3, False),
        ('exterior-with-closed-contact-face-open-interior-only', [(F(1), F(2)), (F(1,4), F(3,4)), (F(1,4), F(3,4))], True),
        ('nonzero-2pow-51-interior-strip-retained', [(F(1)-F(1,2**51), F(1)+F(1,2**51)), (F(1,4), F(3,4)), (F(1,4), F(3,4))], False),
    ]:
        result = try_exterior(box, [unit], counter)
        require(result['excluded_open_interior'] == expected, 'control failed: '+name)
        examples.append({'name': name, 'cell_exact': encode(box), 'expected_exclusion': expected, 'actual': result, 'passed': True})
    # A point-like boundary within an open channel must block it even though
    # its intersection volume is zero.
    point = [(F(1,2), F(1,2))]*3
    require(separation(point, [(F(0),F(1))]*3) is None, 'degenerate boundary point silently dropped')
    examples.append({'name': 'zero-volume-boundary-point-still-blocks', 'passed': True})
    require(separation([(F(0),F(1))]*3, [(F(1),F(2)), (F(0),F(1)), (F(0),F(1))]) == 0,
            'closed point contact lies outside open channel')
    examples.append({'name': 'touching-channel-edge-is-not-open-channel-intersection', 'passed': True})
    return examples


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    require(sha(__file__) == contract['producer_sha256'], 'registered producer identity differs')
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = {'schema': 'razr-r5e-exterior-channel-v2-bound-prerequisites', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'contract_sha256': sha(args.contract), 'execution_completed': False, 'phase': contract['phase'],
              'native_Common_called_or_used_as_premise': False, 'new_native_operations': 0,
              'native_material_boundary_semantics_verified': False, 'compiled_curve_transform_error_verified': False,
              'full_continuous_G2': False, 'all_blockers_closed': False, 'original_TOL_exact': str(F(1e-7)),
              'controls': [], 'frames': [], 'counters': {'channels_tested': 0, 'boundary_box_tests': 0}}
    def save():
        result['seconds'] = time.monotonic()-start
        result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    try:
        report_path = read_bound(contract['r4_report'])
        original = json.loads(report_path.read_text())
        require(original['execution_completed'] and len(original['frames']) == 16, 'completed original16 source required')
        result['source_report_identity'] = contract['r4_report']
        result['source_independent_verification_identity'] = contract['r4_independent_report']
        independent = json.loads(read_bound(contract['r4_independent_report']).read_text())
        require(independent['execution_completed'], 'completed original independent reader required')
        # New full stages require completed owned supervision of their actual
        # scientific prerequisites. A source report alone is insufficient.
        for prerequisite in contract.get('completed_prerequisites', []):
            actual = json.loads(read_bound(prerequisite['report']).read_text())
            controller = json.loads(read_bound(prerequisite['supervisor']).read_text())
            require(actual['execution_completed'] and actual['phase'] == prerequisite['phase'], 'incomplete scientific prerequisite')
            require(controller['completed'] and controller['worker_started'] and controller['worker_exit_code'] == 0 and controller['resource_stop'] is None,
                    'prerequisite was not completed under owned original resource gates')
            require(controller['limits']['registered_math_contract_sha256'] == actual['contract_sha256'], 'prerequisite supervisor/report contract differs')
            require(Path(controller['limits']['worker_output_directory']).resolve() == Path(prerequisite['report']['path']).resolve().parent,
                    'prerequisite supervisor output binding differs')
        expected = [] if contract['phase'] == 'single_stationary_witness' else ['single_stationary_witness'] if contract['phase'] == 'preflight' else ['single_stationary_witness', 'preflight']
        require([p['phase'] for p in contract.get('completed_prerequisites', [])] == expected, 'registered prerequisite sequence required')
        result['controls'] = controlled_examples()
        frames = original['frames']
        if contract['phase'] == 'single_stationary_witness':
            diagnosis = json.loads(read_bound(contract['r4_stationary_diagnostic']).read_text())
            chosen = next(x for x in diagnosis['rows'] if x['case_id'] == contract['case_id'] and x['frame'] == contract['frame'])
            frames = [next(x for x in frames if (x['case_id'], x['frame']) == (chosen['case_id'], chosen['frame']))]
        static_tests = 0; total_cells = 0; total_proof_bytes = 0
        for row in frames:
            proof_record = dict(row['proof'], path=str(report_path.parent/row['proof']['path']))
            proof_path = read_bound(proof_record)
            with gzip.open(proof_path, 'rt') as stream:
                proof = json.load(stream)
            require((proof['case_id'], proof['frame']) == (row['case_id'], row['frame']), 'case/frame proof mapping differs')
            require(proof['full_remaining_displacement_box_exact'] == row['full_remaining_displacement_box_exact'], 'full original displacement changed')
            sources = source_records(proof, stationary=contract['phase']=='single_stationary_witness')
            old_cells = proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
            require(len(old_cells) == row['boundary_slab_positive_cell_count'], 'raw cell count differs')
            total_proof_bytes += proof_record['bytes']
            count = 1 if contract['phase'] == 'single_stationary_witness' else len(old_cells)
            frame_static = count*6*sum(len(s['pieces']) for s in sources)
            static_tests += frame_static; total_cells += count
            record = {'case_id': row['case_id'], 'frame': row['frame'], 'pair': row['pair'], 'source_proof': proof_record,
                      'original_remaining_displacement_box_exact': proof['full_remaining_displacement_box_exact'],
                      'source_piece_counts': [len(s['pieces']) for s in sources], 'candidate_cell_count': count,
                      'static_boundary_box_test_upper': frame_static}
            if contract['phase'] == 'preflight':
                record['mathematical_exclusion_attempted'] = False
            else:
                cells = ([{'box_exact': chosen['zero_displacement_spatial_cover_witness']['stationary_enclosure_positive_cell_exact'],
                           'positive_directed_volume_exact': chosen['zero_displacement_spatial_cover_witness']['stationary_enclosure_cell_volume_exact']}]
                         if contract['phase'] == 'single_stationary_witness' else old_cells)
                kept = F(0); removed = F(0); details = []
                for index, cell in enumerate(cells):
                    box = decode(cell['box_exact']); value = volume(box)
                    require(value == F(cell['positive_directed_volume_exact']) > 0, 'positive directed cell volume differs')
                    certificate = try_exterior(box, sources, result['counters'])
                    details.append({'cell_index': index, 'box_exact': cell['box_exact'],
                                    'positive_directed_volume_exact': str(value), **certificate})
                    if certificate['excluded_open_interior']: removed += value
                    else: kept += value
                record.update(original_disjoint_cell_sum_exact=str(kept+removed), removed_open_cell_sum_exact=str(removed),
                              retained_cell_sum_exact=str(kept), retained_cell_sum_mm3=float(kept),
                              excluded_cell_count=sum(d['excluded_open_interior'] for d in details),
                              retained_cell_count=sum(not d['excluded_open_interior'] for d in details),
                              all_cell_boundaries_retained_as_zero_volume_carriers=True,
                              conditional_raw_clearance_gate_passed=kept <= F(1e-7),
                              source_proof_boundary_semantics_remains_a_premise=True,
                              positive_cell_topology_unchanged=True)
                if contract['phase'] == 'all_raw':
                    require(kept+removed == F(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']), 'original disjoint sum differs')
                    # A minimum with an already proven coarse support upper is
                    # legitimate, and the original clearance threshold stays.
                    selected = min(kept, F(row['coarse_whole_support_upper_exact_mm3']))
                    record['selected_conditional_raw_upper_exact_mm3'] = str(selected)
                    record['selected_conditional_raw_upper_mm3'] = float(selected)
                    record['conditional_raw_clearance_gate_passed'] = selected <= F(1e-7)
                    require(selected <= F(row['conditional_complete_material_intersection_upper_exact_mm3']), 'new selected upper grew beyond original bound')
                    require(row['original_min_volume_plus_TOL_gate_passed'] is True, 'original upper sanity gate not established')
                    record['original_min_volume_plus_TOL_gate_passed'] = True
                    record['upper_sanity_gate_proof'] = 'New bound no greater than the unchanged original bound that passed this gate.'
                dest = args.output/(row['case_id']+'-frame-'+str(row['frame'])+'-channels.json.gz')
                payload = {'schema': 'razr-r5e-exterior-channel-cell-certificate-v1', 'frame': record, 'cells': details}
                with dest.open('wb') as raw:
                    with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as stream:
                        stream.write((json.dumps(payload, separators=(',',':'))+'\n').encode())
                record['certificate'] = {'path': dest.name, 'bytes': dest.stat().st_size, 'sha256': sha(dest)}
            result['frames'].append(record); save()
            require(result['seconds'] <= contract['capacity']['wall_seconds'], 'registered time budget exceeded')
            require(result['peak_RSS_bytes'] <= contract['capacity']['RSS_limit_bytes'], 'registered memory budget exceeded')
            del proof, sources
        result.update(total_candidate_cells=total_cells, static_boundary_box_test_upper=static_tests,
                      static_coordinate_comparison_upper=3*static_tests, total_original_compressed_proof_bytes=total_proof_bytes)
        require(total_cells <= contract['capacity']['maximum_candidate_cells'], 'registered finite cell capacity exceeded')
        require(static_tests <= contract['capacity']['maximum_static_boundary_box_tests'], 'registered finite predicate capacity exceeded')
        result['conditional_clearance_passes'] = sum(r.get('conditional_raw_clearance_gate_passed', False) for r in result['frames'])
        result['source_and_contract_unchanged'] = sha(__file__) == contract['producer_sha256'] and sha(args.contract) == result['contract_sha256']
        require(result['source_and_contract_unchanged'], 'registered source changed during run')
        result['execution_completed'] = True
    except BaseException as exc:
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        raise
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat(); save()
        print(json.dumps({k: result.get(k) for k in ('phase','execution_completed','total_candidate_cells','conditional_clearance_passes','seconds','peak_RSS_bytes','failure')}), flush=True)


if __name__ == '__main__':
    main()
