"""Read existing proofs to witness spatial overcoverage at zero displacement.

This diagnoses the enclosure algorithm, never proves material penetration.
No native operation or whole-domain geometry recomputation is performed.
"""
import argparse
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def decode(box):
    return [tuple(map(Q, pair)) for pair in box]


def meet(*boxes):
    return [(max(box[k][0] for box in boxes), min(box[k][1] for box in boxes)) for k in range(3)]


def volume(box):
    if any(a >= b for a, b in box):
        return Q(0)
    return (box[0][1]-box[0][0])*(box[1][1]-box[1][0])*(box[2][1]-box[2][0])


def encode(box):
    return [[str(x) for x in pair] for pair in box]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    c = json.loads(args.contract.read_text()); require(sha(__file__) == c['producer_sha256'], 'diagnostic source registration')
    base = Path(c['proof_root']); report_path = base/'report.json'
    require(sha(report_path) == c['producer_report_sha256'], 'completed source certificate identity')
    original = json.loads(report_path.read_text()); require(original['execution_completed'], 'completed certificate source')
    begin = time.monotonic(); result = {'schema': 'razr-r4e-spatial-overcoverage-zero-displacement-diagnostic-v1',
        'execution_completed': False, 'rows': [], 'new_native_operations': 0, 'material_intersection_lower_bound_claimed': False,
        'full_continuous_G2': False, 'original_clearance_threshold_exact': str(Q(1e-7))}
    for row in original['frames']:
        if row['original_clearance_gate_passed']:
            continue
        path = base/row['proof']['path']; require(sha(path) == row['proof']['sha256'], 'complete proof identity')
        with gzip.open(path, 'rt') as stream:
            proof = json.load(stream)
        displacement = decode(proof['full_remaining_displacement_box_exact'])
        cover = proof['complete_raw_boundary_slab_cover']
        boxes = [[decode(p['box_exact']) for p in cover[name]] for name in ('first_complete_boundary_boxes','second_complete_boundary_boxes')]
        # Raw support boxes are interval sums: subtract exactly their original
        # lower/upper displacement endpoints to recover stationary boxes.
        stationary = [[[(b[k][0]-(displacement[k][0] if side == 0 else 0),
                         b[k][1]-(displacement[k][1] if side == 0 else 0)) for k in range(3)] for b in group] for side,group in enumerate(boxes)]
        wholes = [[(min(b[k][0] for b in group),max(b[k][1] for b in group)) for k in range(3)] for group in stationary]
        domain = meet(*wholes); cells = sorted(cover['combined']['positive_cells'], key=lambda r: Q(r['positive_directed_volume_exact']), reverse=True)
        observed = None
        for saved in cells[:c['maximum_existing_cell_candidates_per_frame']]:
            bounds = decode(saved['box_exact']); partitions = []; points = []
            for axis in range(3):
                events = {v for group in stationary for b in group for v in b[axis]} | set(domain[axis])
                a,b = bounds[axis]
                point = next((a+(b-a)/m for m in range(2,len(events)+3) if a+(b-a)/m not in events), None)
                require(point is not None, 'finite source events exhaust interior witness sequence')
                lo = max((v for v in events if v < point), default=point)
                hi = min((v for v in events if v > point), default=point)
                partitions.append((max(lo,a),min(hi,b))); points.append(point)
            sections = []; details = []
            for axis,(lo,hi) in enumerate(partitions):
                active = [[i for i,b in enumerate(group) if b[axis][0] < hi and b[axis][1] > lo] for group in stationary]
                if not all(active):
                    sections = []; break
                hulls = []
                for group,indices in zip(stationary,active):
                    hull = [(min(group[i][k][0] for i in indices),max(group[i][k][1] for i in indices)) for k in range(3)]
                    hull[axis] = lo,hi; hulls.append(hull)
                section = meet(*hulls,domain); sections.append(section)
                details.append({'axis':axis,'zero_displacement_open_partition_exact':[str(lo),str(hi)],
                    'complete_active_original_piece_indices':active,'two_source_section_hulls_exact':[encode(h) for h in hulls],
                    'intersection_section_box_exact':encode(section)})
            if len(sections) == 3:
                carrier_cell = meet(*sections); v = volume(carrier_cell)
                if v > Q(1e-7):
                    observed = {'stationary_enclosure_positive_cell_exact':encode(carrier_cell),
                        'stationary_enclosure_cell_volume_exact':str(v),'stationary_enclosure_cell_volume_mm3':float(v),
                        'selected_existing_cell':saved,'interior_points_exact':list(map(str,points)),
                        'stationary_sections':details,'material_penetration_witness':False}
                    break
        require(observed is not None, 'no retained zero-displacement enclosure witness; do not claim time subdivision insufficiency')
        stationary_whole = []
        for candidate in proof['all_registered_candidate_enclosures']:
            moving = decode(candidate['moving_coordinate_intervals_exact']); fixed = decode(candidate['fixed_coordinate_intervals_exact'])
            for i, normal in enumerate(candidate['basis_rows_exact']):
                shifts = [(Q(n)*a,Q(n)*b) for n,(a,b) in zip(normal,displacement)]
                lower = sum(min(pair) for pair in shifts); upper = sum(max(pair) for pair in shifts)
                moving[i] = moving[i][0]-lower,moving[i][1]-upper
            v = volume(meet(moving,fixed))/abs(Q(candidate['basis_determinant_exact']))
            stationary_whole.append(v)
        least_whole = min(stationary_whole)
        require(least_whole > Q(1e-7), 'stationary whole support unexpectedly passes; time-subdivision claim must be narrower')
        result['rows'].append({'case_id':row['case_id'],'frame':row['frame'],'pair':row['pair'],
            'original_remaining_displacement_box_exact':proof['full_remaining_displacement_box_exact'],
            'V4_raw_upper_exact_mm3':row['conditional_complete_material_intersection_upper_exact_mm3'],
            'stationary_whole_support_minimum_exact_mm3':str(least_whole),'stationary_whole_support_minimum_mm3':float(least_whole),
            'zero_displacement_spatial_cover_witness':observed,
            'only_finer_displacement_partition_with_unchanged_spatial_cover_cannot_qualify_cell_containing_zero':True,
            'complete_trim_and_curved_parameterization_refinement_or_certified_inner_void_reasoning_needed':True,
            'native_material_semantics_and_compiled_error_still_separate':True})
    require(len(result['rows']) == 12, 'all12 remaining coarse spatial enclosures diagnosed')
    result['execution_completed'] = True; result['seconds'] = time.monotonic()-begin
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'execution_completed':True,'remaining12_zero_displacement_spatial_cover_witnesses':len(result['rows']),'seconds':result['seconds']}),flush=True)


if __name__ == '__main__':
    main()
