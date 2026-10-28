"""Independent process readback of the R4 current whole KEY/PAWL experiment.

Reads original whole STEP parts and actual saved operand/Common BReps. Rebuilds
the two rigid source poses, checks both material differences, and executes a new
direct Common. No producer Python module or candidate builder is imported.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import resource
import sys
import time


def identity(path):
    p = Path(path)
    return {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); c = json.loads(a.contract.read_text())
    require(identity(__file__) == c['reader_identity'], 'Reader source differs')
    require(sys.flags.optimize == 0 and sys.flags.dont_write_bytecode, 'Unoptimized no-bytecode execution required')
    producer_path = Path(c['producer_report']['path'])
    require(identity(producer_path) == c['producer_report']['identity'], 'Producer report differs')
    producer = json.loads(producer_path.read_text())
    original_contract = Path(c['producer_contract']['path'])
    require(identity(original_contract) == c['producer_contract']['identity'], 'Original contract differs')
    pc = json.loads(original_contract.read_text())
    require(producer['contract_identity'] == identity(original_contract), 'Producer refers to another contract')
    a.out.mkdir(exist_ok=False); (a.out / 'geometry').mkdir()
    start = time.monotonic()
    r = {'schema': 'razr-r4-independent-whole-key-pawl-readback-v1',
         'reader_identity': identity(__file__), 'contract_identity': identity(a.contract),
         'producer_report_identity': identity(producer_path), 'cases': [], 'issues': [],
         'scope': pc['scope'], 'producer_Python_imported': False,
         'separate_process': True, 'independent_CAD_kernel': False,
         'runtime': {n: importlib.metadata.version(n) for n in pc['expected_43_package_versions']},
         'completed': False}

    def persist():
        r['seconds'] = time.monotonic() - start
        r['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        (a.out / 'R4_WHOLE_KEY_PAWL_READBACK.json').write_text(json.dumps(r, indent=2, allow_nan=False) + '\n')

    try:
        require(producer['completed'], 'Producer execution was incomplete')
        require(r['runtime'] == pc['expected_43_package_versions'], 'Original locked package versions differ')
        for row in pc['bound_sources']:
            require(identity(row['path']) == row['identity'], 'Original bound source differs')
        sys.path.insert(0, pc['functional_integration'])
        import product_assembly as p
        import verify_endpoint_joint_pawl as endpoint
        import cadquery as cq
        from OCP.BinTools import BinTools
        from OCP.TopoDS import TopoDS_Shape

        def guard(shape):
            solids, volume = p.whole_material(shape, empty=True)
            require(shape.isValid() and volume >= 0, 'Original material guard failed')
            result = {'valid': True, 'signed_volume_mm3': volume,
                      'counts': {k: len(getattr(shape, k.capitalize())()) for k in ('solids', 'shells', 'faces', 'edges', 'vertices')}}
            if solids:
                result['bounds_mm'] = p.bounds(shape)
            return result

        def read_brep(record):
            f = record['files']['brep']; path = producer_path.parent / f['path']
            require(identity(path) == {k: f[k] for k in ('bytes', 'sha256')}, 'Preserved BRep differs')
            native = TopoDS_Shape()
            require(BinTools.Read_s(native, str(path)), 'Native saved BRep read failed')
            shape = cq.Shape.cast(native); g = guard(shape)
            require(abs(g['signed_volume_mm3'] - record['guard']['signed_volume_mm3']) <= p.TOL, 'Saved signed volume differs')
            require(g['counts'] == record['guard']['counts'], 'Saved topology counts differ')
            return shape, g

        def export(shape, label):
            path = a.out / 'geometry' / (label + '.brep')
            require(BinTools.Write_s(shape.wrapped, str(path)) is not False and path.is_file(), 'Independent BRep write failed')
            return {'guard': guard(shape), 'path': str(path.relative_to(a.out)), **identity(path)}

        def equal_material(left, right, prefix):
            empty = lambda shape: all(len(getattr(shape, k)()) == 0 for k in ('Solids', 'Faces', 'Edges', 'Vertices'))
            if empty(left) and empty(right):
                # The two stored native shapes contain no material topology.
                # Do not execute an undefined empty/empty Boolean or relabel
                # its failure as evidence of equality.
                return {'directed_differences': [], 'both_native_topologically_empty': True,
                        'comparison_method': 'original_guard_and_complete_empty_topology',
                        'original_tolerance_equal': True, 'exact_set_equality_claimed': False}
            differences = [export(left.cut(right), prefix + '_forward'), export(right.cut(left), prefix + '_reverse')]
            return {'directed_differences': differences,
                    'comparison_method': 'two_native_directed_material_cuts',
                    'original_tolerance_equal': all(d['guard']['signed_volume_mm3'] <= p.TOL for d in differences),
                    'exact_set_equality_claimed': False}

        shapes = {}
        for item in pc['inputs']:
            require(identity(item['path']) == item['identity'], 'Original full input differs')
            roots = cq.importers.importStep(item['path']).vals()
            require(len(roots) == 1, 'One full native input root required')
            shapes[item['role']] = p.single(roots[0])
        slots = {s: endpoint.native_slot(shapes[s + '_TAB']) for s in 'LR'}
        r['independent_slot_measurements'] = slots
        r['slots_match_producer'] = all(all(slots[s][k] == producer['slots'][s][k]
                                                for k in ('origin', 'slope', 'halfwidth')) for s in 'LR')
        require(r['slots_match_producer'], 'Independent original TAB slot measurement differs')
        for case in producer['cases']:
            row = {'name': case['name'], 'kind': case['kind'], 'side_results': {}, 'completed': False}
            r['cases'].append(row)
            for side, saved in case['side_results'].items():
                result = {'failure': None}; row['side_results'][side] = result
                try:
                    require(saved['failure'] is None, 'Producer contact operation failed')
                    key, kg = read_brep(saved['KEY']); pawl, pg = read_brep(saved['PAWL'])
                    original_common, cg = read_brep(saved['direct_Common'])
                    pose = saved['pose']; slot = slots[side]
                    z = slot['origin'] + slot['slope'] * pose['tab_mm'] + pose['flank'] * slot['halfwidth']
                    require(z.hex() == saved['computed_pawl_z_translation_hex'], 'Original pose evaluation differs')
                    expected_key = p.single(shapes[side + '_KEY'].translate((0, pose['q_mm'], 0)))
                    expected_pawl = p.single(shapes[side + '_PAWL'].translate((0, 0, z)))
                    prefix = case['name'] + '_' + side
                    result['KEY_source_pose_identity'] = equal_material(expected_key, key, prefix + '_KEY_source')
                    result['PAWL_source_pose_identity'] = equal_material(expected_pawl, pawl, prefix + '_PAWL_source')
                    fresh_common = key.intersect(pawl)
                    result['fresh_direct_Common'] = export(fresh_common, prefix + '_fresh_COMMON')
                    result['Common_material_comparison'] = equal_material(fresh_common, original_common, prefix + '_COMMON_compare')
                    v = result['fresh_direct_Common']['guard']['signed_volume_mm3']
                    require(v <= min(kg['signed_volume_mm3'], pg['signed_volume_mm3']) + p.TOL, 'Original Common upper bound failed')
                    result['Common_volume_matches_producer'] = abs(v - cg['signed_volume_mm3']) <= p.TOL
                    result['original_Common_gate_pass'] = v <= p.TOL
                    result['fresh_original_strict_common'] = p.strict_common(key, pawl)
                    strict_v = result['fresh_original_strict_common']['common_mm3']
                    result['direct_strict_numeric_agreement'] = abs(v - strict_v) <= p.TOL
                    result['direct_strict_gate_classification_agreement'] = (v <= p.TOL) == (strict_v <= p.TOL)
                    result['classification_matches_producer'] = result['original_Common_gate_pass'] == saved['original_Common_gate_pass'] and (strict_v <= p.TOL) == saved['original_strict_common_gate_pass']
                    result['all_checks_passed'] = all(result[k]['original_tolerance_equal'] for k in ('KEY_source_pose_identity', 'PAWL_source_pose_identity', 'Common_material_comparison')) and all(result[k] for k in ('Common_volume_matches_producer', 'classification_matches_producer', 'direct_strict_numeric_agreement', 'direct_strict_gate_classification_agreement'))
                except Exception as exc:
                    result['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
                persist()
            row['completed'] = all(x.get('all_checks_passed') and x['failure'] is None for x in row['side_results'].values())
            row['pair_only_clear'] = row['completed'] and all(x['original_Common_gate_pass'] for x in row['side_results'].values())
            persist()
        r['producer_report_unchanged'] = identity(producer_path) == c['producer_report']['identity']
        r['sources_and_inputs_unchanged'] = all(identity(x['path']) == x['identity'] for x in pc['inputs'] + pc['bound_sources'])
        r['runtime_unchanged'] = {n: importlib.metadata.version(n) for n in pc['expected_43_package_versions']} == r['runtime']
        r['completed'] = all(x['completed'] for x in r['cases']) and all(r[k] for k in ('producer_report_unchanged', 'sources_and_inputs_unchanged', 'runtime_unchanged'))
    except Exception as exc:
        r['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
    persist()
    print(json.dumps({k: r[k] for k in ('completed', 'seconds', 'peak_RSS_bytes', 'issues')}), flush=True)
    return 0 if r['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
