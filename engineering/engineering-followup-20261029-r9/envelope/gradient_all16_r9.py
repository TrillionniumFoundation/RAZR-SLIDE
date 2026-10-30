"""Bounded global exact-volume refinement of every original V5 retained root."""
import argparse
from collections import Counter
from fractions import Fraction as F
import gc
import gzip
import heapq
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

R8 = Path(__file__).resolve().parents[2] / 'engineering-followup-20261029-r8/envelope'
sys.path.insert(0, str(R8))
import run_original_depth24_r8 as common
import source_quadric_r8 as math
from gradient_cut_r9 import choose_cut
import cached_predicates_r9 as cache
common.old_separate=cache.old_separate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (805306368, 805306368))
    signal.signal(signal.SIGALRM, lambda a, b: (_ for _ in ()).throw(TimeoutError('original 600-second wall limit')))
    signal.alarm(600)
    report = {'schema': 'razr-r9-balanced-all16-original-roots', 'execution_completed': False,
              'counts': Counter(), 'frames': [], 'source': common.identity(__file__),
              'common_source': common.identity(common.__file__), 'math_source': common.identity(math.__file__),
              'cut_source': common.identity(Path(__file__).with_name('gradient_cut_r9.py')),
              'cache_source': common.identity(cache.__file__), 'variant':'exact_local_gradient_with_parsing_cache',
              'basis': common.identity(Path(__file__).with_name('GRADIENT_ALL16_BASIS.md')),
              'limits': {'maximum_splits': 4096, 'maximum_depth': 24,
                         'maximum_boundary_box_tests': 12000000, 'wall_seconds': 600,
                         'address_space_limit_bytes': 805306368},
              'scope': {'conditional_source_model_only': True, 'native_error_bound_verified': False,
                        'native_filling_verified': False, 'native_envelope_topology_verified': False,
                        'full_continuous_G2': False, 'all_blockers_closed': False},
              'new_computation_cost_separate_from_prior_runs': True}
    states = []
    queue = []
    splits = 0
    milestones = []
    try:
        base = args.originals/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames'
        original = json.loads((base/'report.json').read_text())
        report['original_report'] = common.identity(base/'report.json')
        TOL = F(original['original_TOL_exact'])
        tiny = F(original['capacity']['tiny_retained_volume_exact'])
        common.need(TOL == F(1e-7), 'original threshold identity')
        report['original_TOL_exact'] = str(TOL)
        report['original_tiny_exact'] = str(tiny)

        def append(state_index, root_index, B, depth):
            s = states[state_index]
            root = s['roots'][root_index]
            nodes = root['nodes']
            index = len(nodes)
            volume = common.volume(B)
            if volume <= tiny:
                obs = {'excluded': False, 'reason': 'original_tiny_positive_volume_retained'}
                report['counts']['tiny_nodes'] += 1
            else:
                obs = common.attempt(B, s['sources'], s['models'], s['D'], report)
                report['counts']['tested_nodes'] += 1
            n = {'id': index, 'depth': depth, 'box_exact': math.encbox(B),
                 'volume_exact': str(volume), 'observation': obs,
                 'kind': 'excluded' if obs['excluded'] else 'retained'}
            nodes.append(n)
            if obs['excluded']:
                s['excluded'] += volume
            else:
                s['retained'] += volume
                if volume > tiny and depth < 24:
                    heapq.heappush(queue, (-volume, state_index, root_index, index, B, depth))
            common.need(report['counts']['pieces'] <= 12000000, 'original 12000000 piece cap')
            return index

        for frame_index, f in enumerate(original['frames']):
            row, cert, models, identities, native = common.load_inputs(args.originals, f['case_id'], f['frame'])
            s = {'row': row, 'sources': cert['boundary_refinement']['sources'], 'models': models,
                 'D': math.box(row['original_remaining_displacement_box_exact']),
                 'inputs': identities, 'roots': [], 'retained': F(0), 'excluded': F(0),
                 'root_total': F(0), 'splits': 0}
            states.append(s)
            for root_index, root in enumerate(cert['roots']):
                B = math.box(root['root_box_exact'])
                v = common.volume(B)
                common.need(v == F(root['root_directed_volume_exact']) and v > 0, 'original positive root identity')
                s['root_total'] += v
                s['roots'].append({'root_index': root_index, 'base_V5_leaf_locator': root['base_V5_leaf_locator'],
                                   'root_box_exact': root['root_box_exact'],
                                   'root_volume_exact': str(v), 'nodes': []})
                append(frame_index, root_index, B, 0)
            print(json.dumps({'loaded': [f['case_id'], f['frame']], 'roots': len(s['roots']),
                              'initial_retained': float(s['retained'])}), flush=True)
            del cert, native
            gc.collect()

        while queue and splits < 4096:
            negative, frame_index, root_index, node_index, B, depth = heapq.heappop(queue)
            s = states[frame_index]
            if s['retained'] <= TOL:
                continue
            n = s['roots'][root_index]['nodes'][node_index]
            common.need(n['kind'] == 'retained', 'unique selected leaf')
            axis, cut, witness = choose_cut(B, n['observation'], s['models'], s['sources'])
            low, high = list(B), list(B)
            low[axis], high[axis] = (B[axis][0], cut), (cut, B[axis][1])
            volume = -negative
            common.need(common.volume(low) == common.volume(high) == volume/2, 'exact equal-volume partition')
            s['retained'] -= volume
            n.update(kind='split', axis=axis, cut_exact=str(cut), cut_witness=witness)
            n['children'] = [append(frame_index, root_index, tuple(low), depth+1),
                             append(frame_index, root_index, tuple(high), depth+1)]
            splits += 1
            s['splits'] += 1
            if splits in (1,2,4,8,16,32,64,128,256,512,1024,2048,4096):
                mark = {'splits': splits, 'frame_retained_display': [float(x['retained']) for x in states],
                        'conditional_passes': sum(x['retained'] <= TOL for x in states),
                        'seconds': time.monotonic()-started, 'piece_tests': report['counts']['pieces']}
                milestones.append(mark)
                print(json.dumps(mark), flush=True)
        report['execution_completed'] = True
    except Exception as exc:
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0)
        for s in states:
            row = s['row']
            prefix = row['case_id']+'-frame-'+str(row['frame'])
            proof = args.output/(prefix+'-balanced-tree.json.gz')
            payload = {'case_id': row['case_id'], 'frame': row['frame'],
                       'D_exact': row['original_remaining_displacement_box_exact'], 'roots': s['roots']}
            with gzip.open(proof, 'wt', encoding='utf-8') as stream:
                json.dump(payload, stream, separators=(',', ':'))
            common.need(s['root_total'] == s['retained'] + s['excluded'], 'complete original root volume conservation')
            report['frames'].append({'case_id': row['case_id'], 'frame': row['frame'],
                                     'original_inputs': s['inputs'], 'source_piece_counts': row['source_piece_counts'],
                                     'root_count': len(s['roots']), 'root_total_exact': str(s['root_total']),
                                     'retained_exact': str(s['retained']), 'retained_display_mm3': float(s['retained']),
                                     'excluded_exact': str(s['excluded']), 'splits': s['splits'],
                                     'maximum_depth': max(n['depth'] for r in s['roots'] for n in r['nodes']),
                                     'conditional_gate_passed': s['retained'] <= F(1e-7),
                                     'original_gate_passed': row['primitive_support_model_conditional_clearance_gate_passed'],
                                     'proof': common.identity(proof)})
        report.update(global_splits=splits, milestones=milestones,
                      conditional_pass_count=sum(f['conditional_gate_passed'] for f in report['frames']),
                      seconds=time.monotonic()-started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'completed': report['execution_completed'], 'passes': report['conditional_pass_count'],
                      'splits': splits, 'seconds': report['seconds'], 'failure': report.get('failure')}), flush=True)
    if not report['execution_completed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
