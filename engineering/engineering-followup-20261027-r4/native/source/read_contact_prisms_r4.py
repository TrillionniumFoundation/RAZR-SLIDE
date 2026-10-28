"""Independent R4 readback of four whole-parent contact interior boxes.

No R4 producer code is imported. Reads every saved BRep and STEP and repeats
containment and the intended outside-material countercontrols independently.
"""
from pathlib import Path
import argparse
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


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); c = json.loads(a.contract.read_text())
    require(identity(__file__) == c['worker_identity'], 'Reader differs')
    require(sys.flags.optimize == 0 and sys.flags.dont_write_bytecode, 'Original interpreter flags required')
    for x in (c['producer_report'], c['producer_contract']):
        require(identity(x['path']) == x['identity'], 'Producer record differs')
    producer_path = Path(c['producer_report']['path']); producer = json.loads(producer_path.read_text())
    pc = json.loads(Path(c['producer_contract']['path']).read_text())
    require(producer['completed'] and producer['contract_identity'] == c['producer_contract']['identity'], 'Producer binding incomplete')
    a.out.mkdir(exist_ok=False); (a.out / 'geometry').mkdir()
    start = time.monotonic()
    r = {'schema': 'razr-r4-independent-contact-prism-readback-v1', 'worker_identity': identity(__file__),
         'contract_identity': identity(a.contract), 'producer_identity': identity(producer_path),
         'scope': pc['scope'], 'separate_process': True, 'independent_CAD_kernel': False,
         'R4_producer_imported': False, 'saved_readbacks': [], 'prisms': [], 'issues': [], 'completed': False,
         'runtime': {n: importlib.metadata.version(n) for n in pc['expected_43_package_versions']}}

    def save():
        r['seconds'] = time.monotonic() - start
        r['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        (a.out / 'R4_CONTACT_PRISMS_READBACK.json').write_text(json.dumps(r, indent=2, allow_nan=False) + '\n')

    try:
        require(r['runtime'] == pc['expected_43_package_versions'], 'Original package version differs')
        for x in pc['bound_sources'] + pc['bound_records']:
            require(identity(x['path']) == x['identity'], 'Original source/record differs')
        helper = load(pc['original_reader_helper'], 'r4_independent_R3_reader_helpers')
        native = helper.load_module(pc['inventory_source']); p = native.p
        parents = {}
        for x in pc['inputs']:
            require(identity(x['path']) == x['identity'], 'Original whole input differs')
            parents[x['role']] = p.single(helper.load_shape(Path(x['path']), native))
        saved = {}

        def visit(value):
            if isinstance(value, dict):
                if 'files' in value and 'guard' in value:
                    for f in value['files'].values():
                        path = producer_path.parent / f['path']
                        require(identity(path) == {k: f[k] for k in ('bytes', 'sha256')}, 'Saved geometry differs')
                        shape = helper.load_shape(path, native); g = helper.shape_gate(shape, native)
                        same = g['counts'] == value['guard']['counts'] and abs(g['signed_volume_mm3'] - value['guard']['signed_volume_mm3']) <= p.TOL
                        require(same, 'Independent saved geometry signature differs')
                        saved[f['path']] = shape
                        r['saved_readbacks'].append({'path': f['path'], 'guard': g, 'signature_matches': same})
                for v in value.values(): visit(v)
            elif isinstance(value, list):
                for v in value: visit(v)
        visit(producer)
        for spec, old in zip(pc['prisms'], producer['prisms'], strict=True):
            require(spec['name'] == old['name'], 'Prism order differs')
            parent = parents[spec['parent']]; source = p.box(*spec['bounds_mm'])
            common = source.intersect(parent); missing = source.cut(parent)
            saved_source = saved[old['source_box']['files']['brep']['path']]
            saved_common = saved[old['actual_intersection']['files']['brep']['path']]
            outside = source.translate((100, 0, 0)); control = outside.cut(parent)
            checks = {'source_minus_saved': source.cut(saved_source), 'saved_minus_source': saved_source.cut(source),
                      'common_minus_saved': common.cut(saved_common), 'saved_minus_common': saved_common.cut(common),
                      'source_minus_parent': missing}
            row = {'name': spec['name'], 'directed_differences': {name: helper.save_shape(shape, spec['name'] + '_' + name, a.out, native) for name, shape in checks.items()},
                   'fresh_common': helper.save_shape(common, spec['name'] + '_fresh_common', a.out, native),
                   'outside_missing': helper.save_shape(control, spec['name'] + '_outside_missing', a.out, native)}
            row['all_native_differences_empty'] = all(x['guard']['native_topologically_empty'] for x in row['directed_differences'].values())
            row['native_containment_original_gate_pass'] = p.volume(missing) <= p.TOL and abs(p.volume(common) - p.volume(source)) <= p.TOL
            row['outside_control_rejected'] = p.volume(control) > p.TOL and abs(p.volume(control) - p.volume(source)) <= p.TOL
            row['passed'] = row['all_native_differences_empty'] and row['native_containment_original_gate_pass'] and row['outside_control_rejected']
            r['prisms'].append(row); save()
        r['sources_and_inputs_unchanged'] = all(identity(x['path']) == x['identity'] for x in pc['inputs'] + pc['bound_sources'] + pc['bound_records'])
        r['runtime_unchanged'] = {n: importlib.metadata.version(n) for n in pc['expected_43_package_versions']} == r['runtime']
        r['completed'] = len(r['prisms']) == 4 and all(x['passed'] for x in r['prisms']) and r['sources_and_inputs_unchanged'] and r['runtime_unchanged']
    except Exception as exc:
        r['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
    save(); print(json.dumps({k: r[k] for k in ('completed', 'seconds', 'peak_RSS_bytes', 'issues')}), flush=True)
    return 0 if r['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
