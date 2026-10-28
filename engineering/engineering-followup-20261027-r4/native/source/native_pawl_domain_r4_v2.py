"""R4 whole-current-KEY/original-PAWL contact experiment.

This is a narrow six-original-solid experiment. It is not a complete factory
execution, a continuous native material certificate, or physical qualification.
All original Boolean failures and scalar witness identities are retained.
"""
from pathlib import Path
import argparse
from fractions import Fraction
import hashlib
import importlib.metadata
import importlib.util
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


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    c = json.loads(a.contract.read_text())
    require(identity(__file__) == c['worker_identity'], 'Worker identity differs')
    require(sys.flags.optimize == 0 and sys.flags.dont_write_bytecode, 'Unoptimized no-bytecode execution required')
    a.out.mkdir(exist_ok=False)
    (a.out / 'geometry').mkdir()
    (a.out / 'inventories').mkdir()
    start = time.monotonic()
    report = {'schema': 'razr-r4-whole-key-pawl-contact-domain-v1',
              'worker_identity': identity(__file__), 'contract_identity': identity(a.contract),
              'scope': c['scope'], 'original_Common_threshold_mm3': c['original_Common_threshold_mm3'],
              'inputs': c['inputs'], 'whole_inputs': {}, 'slots': {}, 'cases': [], 'issues': [],
              'runtime': {n: importlib.metadata.version(n) for n in c['expected_43_package_versions']},
              'completed': False}

    def persist():
        report['seconds'] = time.monotonic() - start
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        raw = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
        require(len(raw) <= c['maximum_report_bytes'], 'Registered report size exceeded')
        (a.out / 'R4_WHOLE_KEY_PAWL_NATIVE.json').write_bytes(raw)

    try:
        require(report['runtime'] == c['expected_43_package_versions'], 'An original package version differs')
        for row in c['bound_sources']:
            require(identity(row['path']) == row['identity'], 'Bound source differs: ' + row['path'])
        for row in c['bound_records']:
            require(identity(row['path']) == row['identity'], 'Bound original record differs: ' + row['path'])
        sys.path.insert(0, c['functional_integration'])
        import product_assembly as p
        import verify_endpoint_joint_pawl as endpoint
        extension = module(c['inventory_extension'], 'r4_original_inventory_extension')
        native = extension.load_inventory(c['inventory_source'])
        cq = native.cq

        def guard(shape, empty=True):
            solids, volume = p.whole_material(shape, empty=empty)
            result = {'valid': shape.isValid(), 'signed_volume_mm3': volume,
                      'solid_volumes_mm3': [s.Volume() for s in solids],
                      'counts': {k: len(getattr(shape, k.capitalize())())
                                 for k in ('solids', 'shells', 'faces', 'edges', 'vertices')}}
            require(result['valid'] and volume >= 0, 'Original material guard failed')
            if solids:
                result['bounds_mm'] = p.bounds(shape)
            return result

        def export(shape, label, step=False):
            record = {'guard': guard(shape), 'files': {}}
            path = a.out / 'geometry' / (label + '.brep')
            status = native.BinTools.Write_s(shape.wrapped, str(path))
            require(status is not False and path.is_file(), 'BRep output failed')
            record['files']['brep'] = {'path': str(path.relative_to(a.out)), **identity(path)}
            if step and shape.Faces():
                path = path.with_suffix('.step')
                cq.exporters.export(shape, str(path))
                record['files']['step'] = {'path': str(path.relative_to(a.out)), **identity(path)}
            return record

        original_manifest = json.loads(Path(c['template_manifest']).read_text())
        shapes = {}
        for item in c['inputs']:
            require(identity(item['path']) == item['identity'], 'Input differs: ' + item['role'])
            if item['provenance_kind'] == 'registered_34_template':
                native_row = original_manifest['exports'][item['role']]
                require(native_row['sha256'] == item['identity']['sha256'], 'Original template manifest mismatch')
            else:
                m = item['manifest']
                require(identity(m['path']) == m['identity'], 'Current KEY manifest differs')
                row = json.loads(Path(m['path']).read_text())['members'][m['member']]
                require(row == item['identity'], 'Whole current KEY identity missing from original manifest')
            roots = cq.importers.importStep(item['path']).vals()
            require(len(roots) == 1, 'Exactly one whole input root required')
            shape = p.single(roots[0]); shapes[item['role']] = shape
            inv = extension.inspect(shape, native)
            path = a.out / 'inventories' / (item['role'] + '.json')
            path.write_text(json.dumps(inv, separators=(',', ':'), allow_nan=False) + '\n')
            report['whole_inputs'][item['role']] = {
                'native_guard': guard(shape, empty=False),
                'complete_boundary_inventory': {'path': str(path.relative_to(a.out)), **identity(path)},
                'inventory_complete': inv['r3_complete_curve_inventory']['complete'],
                'geometry': export(shape, 'whole_' + item['role'], step=True)}
            persist()
        for side in 'LR':
            slot = endpoint.native_slot(shapes[side + '_TAB'])
            report['slots'][side] = slot
            report['slots'][side]['source_binary64_parameters'] = {
                k: {'hex': float(slot[k]).hex(), 'exact': str(Fraction(float(slot[k])))}
                for k in ('origin', 'slope', 'halfwidth')}
        persist()
        for case in c['cases']:
            row = {'name': case['name'], 'kind': case['kind'], 'source_binding': case.get('source_binding'),
                   'side_results': {}, 'completed': False}
            report['cases'].append(row)
            for side in 'LR':
                pose = case['by_side'][side]
                q, u, flank = pose['q_mm'], pose['tab_mm'], pose['flank']
                require(0 <= q <= 12 and 0 <= u <= 3 and -1 <= flank <= 1, 'Pose outside source scalar coordinates')
                slot = report['slots'][side]
                z = slot['origin'] + slot['slope'] * u + flank * slot['halfwidth']
                # These are the unchanged exact source evaluation order and
                # current frozen adapter translations, not an alternative law.
                key = p.single(shapes[side + '_KEY'].translate((0, q, 0)))
                pawl = p.single(shapes[side + '_PAWL'].translate((0, 0, z)))
                prefix = case['name'] + '_' + side
                side_row = {'pose': pose, 'computed_pawl_z_translation_mm': z,
                            'computed_pawl_z_translation_hex': z.hex(),
                            'KEY': export(key, prefix + '_KEY'),
                            'PAWL': export(pawl, prefix + '_PAWL'), 'failure': None}
                row['side_results'][side] = side_row
                try:
                    direct = key.intersect(pawl)
                    side_row['direct_Common'] = export(direct, prefix + '_COMMON')
                    value = side_row['direct_Common']['guard']['signed_volume_mm3']
                    require(value <= min(p.volume(key), p.volume(pawl)) + p.TOL, 'Original Common upper bound failed')
                    side_row['original_strict_common'] = p.strict_common(key, pawl)
                    side_row['original_Common_gate_pass'] = value <= p.TOL
                    side_row['original_strict_common_gate_pass'] = side_row['original_strict_common']['common_mm3'] <= p.TOL
                    side_row['direct_and_original_guard_agree'] = abs(value - side_row['original_strict_common']['common_mm3']) <= p.TOL
                    side_row['same_original_tolerance_gate_classification'] = side_row['original_Common_gate_pass'] == side_row['original_strict_common_gate_pass']
                except Exception as exc:
                    side_row['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
                persist()
            row['completed'] = all(r['failure'] is None for r in row['side_results'].values())
            row['pair_only_clear'] = row['completed'] and all(r['original_Common_gate_pass'] and r['original_strict_common_gate_pass'] for r in row['side_results'].values())
            row['whole_factory_feasibility_claimed'] = False
            persist()
        report['local_imported_sources'] = []
        for name, loaded in sorted(sys.modules.items()):
            path = getattr(loaded, '__file__', None)
            if path and Path(path).is_file() and str(Path(path).resolve()).startswith(c['source_root'] + '/') and path.endswith('.py'):
                report['local_imported_sources'].append({'module': name, 'path': str(Path(path).resolve()), 'identity': identity(path)})
        expected = {r['path']: r['identity'] for r in c['bound_sources']}
        for row in report['local_imported_sources']:
            require(expected.get(row['path']) == row['identity'], 'An imported local source was not frozen')
        report['inputs_unchanged'] = all(identity(r['path']) == r['identity'] for r in c['inputs'])
        report['sources_unchanged'] = all(identity(r['path']) == r['identity'] for r in c['bound_sources'])
        report['package_versions_unchanged'] = {n: importlib.metadata.version(n) for n in c['expected_43_package_versions']} == report['runtime']
        report['all_case_operations_completed'] = all(r['completed'] for r in report['cases'])
        report['all_whole_inventories_complete'] = all(r['inventory_complete'] for r in report['whole_inputs'].values())
        report['all_original_Common_guards_consistent'] = all(
            side.get('direct_and_original_guard_agree') and side.get('same_original_tolerance_gate_classification')
            for row in report['cases'] for side in row['side_results'].values())
        report['completed'] = all(report[k] for k in ('inputs_unchanged', 'sources_unchanged', 'package_versions_unchanged',
            'all_case_operations_completed', 'all_whole_inventories_complete', 'all_original_Common_guards_consistent'))
    except Exception as exc:
        report['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
    persist()
    print(json.dumps({k: report[k] for k in ('completed', 'seconds', 'peak_RSS_bytes', 'issues')}), flush=True)
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
