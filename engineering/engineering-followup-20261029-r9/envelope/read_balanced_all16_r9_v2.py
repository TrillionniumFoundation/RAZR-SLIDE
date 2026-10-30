"""Independent reconstruction and proof check for the R9 balanced forests.

Imports the R8 independently written checker, never the producer or geometric
producer helpers. Every retained positive box is included in exact sums.
"""
import argparse
from collections import Counter
import copy
from fractions import Fraction as F
import gc
import gzip
import json
from pathlib import Path
import platform
import resource
import sys
import time
import traceback

R8_READER = Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/independent-review'
sys.path.insert(0, str(R8_READER))
import quadric_checker_r8 as exact
from read_depth24_actual_r8 import identity, need, measure
from read_all16_actual_r8 import read_all_materials, verify_leaf_channels


def verify_observation(observation, B, sources, materials, D, totals):
    # The old R8 quadric checker verifies enclosure correctness even for an
    # unresolved classification. Such a bound is useful diagnostically but
    # cannot support an exterior-channel exclusion. Enforce that distinction
    # here before using the independently written mathematical checker.
    need(type(observation['excluded']) is bool, 'boolean_exclusion_claim')
    for channel in observation['observations']:
        for claim in channel['new_claims']:
            if claim['code'] == 'quadric':
                need(claim['classification'] in ('below_radius', 'above_radius'),
                     'strict_quadric_required_for_exclusion')
    return verify_leaf_channels(observation, B, sources, materials, D, totals)


def verify_root(root, original, sources, materials, D, tiny, totals):
    need(root['base_V5_leaf_locator'] == original['base_V5_leaf_locator'], 'original_V5_locator')
    initial = exact.bounds(original['root_box_exact'])
    need(exact.bounds(root['root_box_exact']) == initial, 'same_complete_original_root')
    need(F(root['root_volume_exact']) == measure(initial) == F(original['root_directed_volume_exact']), 'original_root_directed_volume')
    nodes = root['nodes']
    visited = set()
    retained = excluded = F(0)
    splits = maxdepth = 0
    pending = [(0, initial, 0)]
    while pending:
        index, B, depth = pending.pop()
        need(type(index) is int and 0 <= index < len(nodes) and index not in visited, 'unique_complete_child_node')
        visited.add(index)
        n = nodes[index]
        need(n['id'] == index, 'node_identity')
        need(n['depth'] == depth <= 24, 'original_depth24_limit')
        need(exact.bounds(n['box_exact']) == B, 'reconstructed_child_box')
        volume = measure(B)
        need(F(n['volume_exact']) == volume, 'positive_directed_node_volume')
        maxdepth = max(maxdepth, depth)
        observation = n['observation']
        if 'reason' in observation:
            need(observation == {'excluded': False, 'reason': 'original_tiny_positive_volume_retained'}, 'only_original_tiny_skip')
            need(volume <= tiny, 'unchanged_tiny_threshold')
            totals['tiny_nodes'] += 1
            is_excluded = False
        else:
            need(volume > tiny, 'non_tiny_node_tested')
            totals['tested_nodes'] += 1
            is_excluded = verify_observation(observation, B, sources, materials, D, totals)
        if n['kind'] == 'split':
            need(not is_excluded and volume > tiny and depth < 24, 'only_unresolved_splittable_node')
            axis, cut = n['axis'], F(n['cut_exact'])
            need(type(axis) is int and 0 <= axis < 3, 'cut_axis')
            need(B[axis][0] < cut < B[axis][1] and cut == sum(B[axis])/2, 'exact_internal_midpoint')
            children = n['children']
            need(len(children) == 2 and children[0] != children[1], 'two_distinct_children')
            lower, upper = list(B), list(B)
            lower[axis], upper[axis] = (B[axis][0], cut), (cut, B[axis][1])
            need(measure(lower) == measure(upper) == volume/2, 'exact_partition_volume')
            pending.extend([(children[1], tuple(upper), depth+1), (children[0], tuple(lower), depth+1)])
            splits += 1
        else:
            need(n['kind'] == ('excluded' if is_excluded else 'retained'), 'terminal_claim_kind')
            totals['terminal_leaves'] += 1
            if is_excluded:
                excluded += volume
                totals['excluded_leaves'] += 1
            else:
                retained += volume
                totals['retained_leaves'] += 1
    need(len(visited) == len(nodes), 'all_nodes_reachable')
    need(retained+excluded == measure(initial), 'whole_root_volume_conservation')
    return retained, excluded, splits, maxdepth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--producer-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = {'schema': 'razr-r9-balanced-all16-independent-readback-v2', 'completed': False, 'frames': [],
              'source': identity(__file__), 'independent_source_checker': identity(exact.__file__),
              'independent_channel_checker': identity(R8_READER/'read_all16_actual_r8.py'),
              'producer_report': identity(args.producer_report), 'python_version': platform.python_version(),
              'producer_or_primitive_helper_imported': False,
              'scope': {'conditional_source_model_only': True, 'native_error_bound_verified': False,
                        'native_filling_verified': False, 'native_envelope_topology_verified': False,
                        'full_continuous_G2': False, 'all_blockers_closed': False}}
    try:
        report = json.loads(args.producer_report.read_text())
        need(report['execution_completed'] and report['schema'] == 'razr-r9-balanced-all16-original-roots', 'complete_actual_all16_producer')
        for k in ('source', 'common_source', 'math_source', 'cut_source', 'basis'):
            need(identity(report[k]['path']) == report[k], 'recorded_execution_source_identity:'+k)
        expected_limits={'maximum_splits':4096,'maximum_depth':24,'maximum_boundary_box_tests':12000000,'wall_seconds':600,'address_space_limit_bytes':805306368}
        need(report['limits']==expected_limits,'exact_original_execution_limits')
        need(0 <= report['seconds'] <= 600,'complete_recorded_cost_including_proof_serialization')
        if 'cache_source' in report:
            need(identity(report['cache_source']['path']) == report['cache_source'], 'recorded_exact_parsing_cache_identity')
        base = args.originals/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames'
        original = json.loads((base/'report.json').read_text())
        need(identity(base/'report.json') == report['original_report'], 'original_report_identity')
        threshold = F(original['original_TOL_exact'])
        tiny = F(original['capacity']['tiny_retained_volume_exact'])
        need(threshold == F(report['original_TOL_exact']) == F(1e-7), 'unmodified_original_float64_gate')
        need(tiny == F(report['original_tiny_exact']), 'unmodified_original_tiny_rule')
        need(len(report['frames']) == len(original['frames']) == 16, 'all16_frame_count')
        need([(x['case_id'],x['frame']) for x in report['frames']] == [(x['case_id'],x['frame']) for x in original['frames']], 'complete_original_frame_order')
        required = set()
        for row in original['frames']:
            with gzip.open(base/Path(row['certificate']['path']).name, 'rt') as stream:
                cert = json.load(stream)
            required.update(tuple(s['material_key']) for s in cert['boundary_refinement']['sources'])
        materials, native_ids = read_all_materials(args.originals, required)
        result['original_native_inventories'] = native_ids
        result['whole_native_material_records'] = len(materials)
        totals = Counter()
        total_splits = 0
        selected_control = None
        selected_success = None
        selected_quadric = None
        for frame, original_frame in zip(report['frames'], original['frames']):
            cp = base/Path(original_frame['certificate']['path']).name
            cid = identity(cp)
            need(all(cid[k] == original_frame['certificate'][k] for k in ('bytes','sha256')), 'full_original_certificate_identity')
            with gzip.open(cp, 'rt') as stream:
                cert = json.load(stream)
            need(cert['frame'] == {k:v for k,v in original_frame.items() if k!='certificate'}, 'certificate_original_frame_header')
            sources = cert['boundary_refinement']['sources']
            need(frame['source_piece_counts'] == [len(s['pieces']) for s in sources], 'all_boundary_source_pieces')
            proof_path = args.producer_report.parent/Path(frame['proof']['path']).name
            pid = identity(proof_path)
            need(all(pid[k] == frame['proof'][k] for k in ('bytes','sha256')), 'actual_proof_identity')
            with gzip.open(proof_path, 'rt') as stream:
                proof = json.load(stream)
            need((proof['case_id'],proof['frame']) == (frame['case_id'],frame['frame']), 'proof_frame_identity')
            D = exact.bounds(original_frame['original_remaining_displacement_box_exact'])
            need(exact.bounds(proof['D_exact']) == D, 'complete_original_displacement')
            need(len(proof['roots']) == len(cert['roots']) == frame['root_count'], 'all_original_roots_preserved')
            retained = excluded = root_total = F(0)
            frame_splits = maxdepth = 0
            frame_totals = Counter()
            for index, (root, original_root) in enumerate(zip(proof['roots'], cert['roots'])):
                need(root['root_index'] == index, 'original_root_order')
                a,b,c,d = verify_root(root, original_root, sources, materials, D, tiny, frame_totals)
                retained += a
                excluded += b
                root_total += F(original_root['root_directed_volume_exact'])
                frame_splits += c
                maxdepth = max(maxdepth, d)
                if selected_control is None and c:
                    selected_control = (copy.deepcopy(root), original_root, sources, D)
                if selected_success is None:
                    for node in root['nodes']:
                        if node['kind']=='excluded':
                            selected_success = (copy.deepcopy(node), sources, D)
                            break
                if selected_quadric is None:
                    for node in root['nodes']:
                        if (node['kind']=='excluded' and
                            any(claim['code']=='quadric' for claim in node['observation']['observations'][-1]['new_claims'])):
                            selected_quadric = (copy.deepcopy(node), sources, D)
                            break
            need(retained+excluded == root_total, 'complete_frame_positive_volume_conservation')
            need(F(frame['retained_exact']) == retained and F(frame['excluded_exact']) == excluded and F(frame['root_total_exact']) == root_total, 'frame_exact_sums')
            need(frame['splits'] == frame_splits and frame['maximum_depth'] == maxdepth <= 24, 'frame_split_depth_accounting')
            need(frame['conditional_gate_passed'] == (retained <= threshold), 'frame_original_gate')
            total_splits += frame_splits
            totals.update(frame_totals)
            checked = {'case_id': frame['case_id'], 'frame': frame['frame'], 'verified': True,
                       'root_count': len(proof['roots']), 'counts': frame_totals, 'splits': frame_splits,
                       'maximum_depth': maxdepth, 'retained_exact': str(retained),
                       'retained_display_mm3': float(retained), 'conditional_gate_passed': retained <= threshold,
                       'root_total_exact': str(root_total), 'excluded_exact': str(excluded), 'proof': pid}
            result['frames'].append(checked)
            print(json.dumps({'verified_frame': [frame['case_id'],frame['frame']], 'splits': frame_splits,
                              'retained': float(retained), 'pass': retained <= threshold}), flush=True)
            del proof, cert
            gc.collect()
        need(total_splits == report['global_splits'] <= 4096, 'global_original_split_budget')
        need(totals['channels'] == report['counts']['channels'], 'actual_channel_accounting')
        need(totals['piece_proofs'] + totals['failed_channel_prefixes'] == report['counts']['pieces'] <= 12000000, 'actual_piece_accounting_and_cap')
        for k in ('tiny_nodes','tested_nodes'):
            need(totals[k] == report['counts'][k], 'actual_node_count:'+k)
        for k in ('quadric','plane','line','empty_closed_intersection'):
            need(totals['new_'+k] == report['counts'].get('new_'+k,0), 'actual_source_claim_count:'+k)
        controls = []
        root, original_root, sources, D = selected_control
        def check_mutation(name, change, expected):
            mutated = copy.deepcopy(root)
            change(mutated)
            actual = None
            try:
                verify_root(mutated, original_root, sources, materials, D, tiny, Counter())
            except ValueError as exc:
                actual = str(exc)
            need(actual == expected, 'mutation_specific_rejection:'+name)
            controls.append({'name':name,'expected_rejection':expected,'actual_rejection':actual,'passed':True})
        check_mutation('alter_original_root',lambda r:r['root_box_exact'][0].__setitem__(0,str(F(r['root_box_exact'][0][0])-1)),'same_complete_original_root')
        check_mutation('alter_directed_volume',lambda r:r.__setitem__('root_volume_exact','0'),'original_root_directed_volume')
        check_mutation('alter_inherited_depth',lambda r:r['nodes'][0].__setitem__('depth',25),'original_depth24_limit')
        check_mutation('duplicate_child',lambda r:r['nodes'][0].__setitem__('children',[1,1]),'two_distinct_children')
        check_mutation('false_midpoint',lambda r:r['nodes'][0].__setitem__('cut_exact',str(F(r['nodes'][0]['cut_exact'])+F(1,1000))),'exact_internal_midpoint')
        check_mutation('discard_positive_root_as_tiny',lambda r:r['nodes'][0].__setitem__('observation',{'excluded':False,'reason':'original_tiny_positive_volume_retained'}),'unchanged_tiny_threshold')
        node, sources, D = selected_success
        mutated = copy.deepcopy(node['observation'])
        last = mutated['observations'][-1]
        removed_index = len(last['codes'])-1
        last['codes'] = last['codes'][:-1]
        last['new_claims'] = [claim for claim in last['new_claims'] if claim['piece_index'] != removed_index]
        failure = None
        try:
            verify_observation(mutated, exact.bounds(node['box_exact']), sources, materials, D, Counter())
        except ValueError as exc:
            failure = str(exc)
        need(failure == 'complete_whole_channel_coverage','missing_piece_specific_rejection')
        controls.append({'name':'remove_successful_boundary_piece','actual_rejection':failure,'expected_rejection':'complete_whole_channel_coverage','passed':True})
        node, sources, D = selected_quadric
        mutated = copy.deepcopy(node['observation'])
        claim = next(c for c in mutated['observations'][-1]['new_claims'] if c['code']=='quadric')
        claim['lower_exact'] = '0'
        claim['upper_exact'] = str(F(claim['upper_exact'])+F(claim['radius_squared_exact'])+1)
        claim['classification'] = 'unresolved'
        # This altered enclosure remains a valid bound, but cannot exclude
        # the cylindrical surface. Preserve the observed old acceptance to
        # distinguish this real semantic gap from a malformed-certificate test.
        old_accepts = verify_leaf_channels(mutated, exact.bounds(node['box_exact']), sources, materials, D, Counter())
        need(old_accepts is True, 'old_reader_actual_non_strict_acceptance_reproduced')
        failure = None
        try:
            verify_observation(mutated, exact.bounds(node['box_exact']), sources, materials, D, Counter())
        except ValueError as exc:
            failure = str(exc)
        need(failure == 'strict_quadric_required_for_exclusion', 'unresolved_quadric_specific_rejection')
        controls.append({'name':'use_unresolved_quadric_for_exclusion','actual_rejection':failure,
                         'expected_rejection':'strict_quadric_required_for_exclusion','passed':True,
                         'old_R8_channel_reader_accepts_altered_bound_as_exclusion':old_accepts,
                         'altered_bound_still_mathematically_conservative':True})
        passes = sum(f['conditional_gate_passed'] for f in result['frames'])
        need(passes == report['conditional_pass_count'], 'complete_pass_count')
        result.update(completed=True, totals=totals, global_splits=total_splits,
                      conditional_pass_count=passes, actual_mutation_controls=controls,
                      analytic_controls=exact.analytic_controls())
    except Exception as exc:
        result['failure'] = {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    result['seconds'] = time.monotonic()-start
    result['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'completed':result['completed'],'passes':result.get('conditional_pass_count'),
                      'seconds':result['seconds'],'failure':result.get('failure')}),flush=True)
    if not result['completed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
