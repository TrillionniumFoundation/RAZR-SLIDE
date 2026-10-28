"""Preflight finite operation counts for exact slab union compression."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import time
import traceback


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_module(name, record):
    require(sha(record['path']) == record['sha256'], 'registered source changed')
    spec = importlib.util.spec_from_file_location(name, record['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    contract = json.loads(args.contract.read_text()); require(sha(__file__) == contract['producer_sha256'], 'capacity source differs')
    begin = time.monotonic()
    result = {'schema': 'razr-r4e-exact-union-slab-capacity-preflight-v1', 'execution_completed': False, 'frames': [],
              'CAD_called': False, 'intersection_or_clearance_certified': False, 'full_continuous_G2': False}
    def save():
        result['seconds'] = time.monotonic()-begin; result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    try:
        support = load_module('r4e_frozen_support_capacity', contract['support_source'])
        slab = load_module('r4e_frozen_slab_capacity', contract['slab_source'])
        for row in contract['inputs']:
            require(Path(row['path']).stat().st_size == row['bytes'] and sha(row['path']) == row['sha256'], 'capacity original input differs')
        native = json.loads(Path(contract['native_report']).read_text())
        by = {(r['input']['case_id'], r['input']['material_id']): r for r in native['operands']}
        for path in contract['supplements']:
            supplement = json.loads(Path(path).read_text()); require(supplement['execution_completed'], 'incomplete supplement')
            for item in supplement['records']:
                original = by[item['input']['case_id'], item['input']['material_id']]['boundary']
                require(hashlib.sha256(json.dumps(original, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == item['original_complete_boundary_canonical_sha256'], 'complete original binding')
                for curve in item['complete_pcurves']:
                    target = original['faces'][curve['face_index']]['wires'][curve['wire_index']]['edge_occurrences'][curve['occurrence_index']]
                    require(target['pcurve'] == curve['old_pcurve_record'] and target['edge_index'] == curve['edge_index'], 'pcurve exact occurrence mapping')
                    target['pcurve'] = curve['complete_pcurve_record']
        cache = {}
        for row in native['tiny_base_Common']:
            materials = []
            for material_id in [row['moving_saved_material_id'], row['fixed_original_material_id']]:
                key = row['case_id'], material_id
                if key not in cache:
                    cache[key] = support.CompleteBoundary(by[key])
                materials.append(cache[key])
            displacement = [tuple(map(F, pair)) for pair in row['full_remaining_displacement_box_exact']]
            zero = [(F(0), F(0))]*3
            frame = {'case_id': row['case_id'], 'frame': row['frame'], 'covers': []}
            for kind in ['raw', 'declared-tolerance', 'whole-self-negative-control']:
                if kind == 'whole-self-negative-control':
                    a = slab.material_boundary_boxes(materials[0], zero); b = a
                else:
                    a = slab.material_boundary_boxes(materials[0], displacement, kind == 'declared-tolerance')
                    b = slab.material_boundary_boxes(materials[1], zero, kind == 'declared-tolerance')
                domain = slab.intersection(a['whole'], b['whole'])
                detail = {'kind': kind, 'first_piece_count': len(a['pieces']), 'second_piece_count': len(b['pieces'])}
                if not slab.volume(domain):
                    detail.update(axis_cuts=[0,0,0], fine_positive_counts=[0,0,0], merged_positive_counts=[0,0,0], pair_plus_triple_static_upper=0)
                else:
                    covers = [slab.coverage_axis(a,b,domain,k) for k in range(3)]
                    runs = [slab.merge_unchanged_transverse_boxes(c) for c in covers]
                    fine = [len(c['positive_boxes']) for c in covers]; merged = [len(r) for r in runs]
                    n = sorted(merged); f = sorted(fine)
                    detail.update(axis_cuts=[len(c['cuts_exact']) for c in covers], fine_positive_counts=fine, merged_positive_counts=merged,
                                  uncompressed_pair_plus_triple_static_upper=f[0]*f[1]*(1+f[2]),
                                  pair_plus_triple_static_upper=n[0]*n[1]*(1+n[2]),
                                  entire_fine_cut_planes_retained=True,
                                  merging_only_exact_equal_transverse_intervals_and_contiguous_axis=True)
                frame['covers'].append(detail)
            result['frames'].append(frame); save()
            print(json.dumps(frame), flush=True)
        require(len(result['frames']) == 16, 'complete original16 capacity coverage')
        result['maximum_static_pair_plus_triple_bound_per_cover'] = max(c['pair_plus_triple_static_upper'] for f in result['frames'] for c in f['covers'])
        result['total_static_pair_plus_triple_bound'] = sum(c['pair_plus_triple_static_upper'] for f in result['frames'] for c in f['covers'])
        result['all_sources_and_inputs_unchanged'] = (sha(__file__) == contract['producer_sha256'] and
            all(sha(contract[k]['path']) == contract[k]['sha256'] for k in ('support_source','slab_source')) and
            all(sha(r['path']) == r['sha256'] for r in contract['inputs']))
        require(result['all_sources_and_inputs_unchanged'], 'capacity postflight identity')
        result['execution_completed'] = True
    except Exception as exc:
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    save(); print(json.dumps({k: result.get(k) for k in ('execution_completed','failure','seconds','peak_RSS_bytes','maximum_static_pair_plus_triple_bound_per_cover','total_static_pair_plus_triple_bound')}), flush=True)
    return 0 if result['execution_completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
