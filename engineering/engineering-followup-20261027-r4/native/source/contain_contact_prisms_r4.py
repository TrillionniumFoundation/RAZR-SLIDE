"""R4 finite native material bridge for a continuous excluded contact subdomain.

The registered interior boxes are checked against whole current KEY/PAWL.
Native containment and exact source-box motion proofs remain separate claims.
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
    require(identity(__file__) == c['worker_identity'], 'Worker differs')
    require(sys.flags.optimize == 0 and sys.flags.dont_write_bytecode, 'Original interpreter flags required')
    a.out.mkdir(exist_ok=False); (a.out / 'geometry').mkdir()
    start = time.monotonic()
    r = {'schema': 'razr-r4-native-interior-contact-prisms-v1', 'contract_identity': identity(a.contract),
         'worker_identity': identity(__file__), 'inputs': c['inputs'], 'scope': c['scope'],
         'runtime': {n: importlib.metadata.version(n) for n in c['expected_43_package_versions']},
         'parents': {}, 'prisms': [], 'issues': [], 'completed': False}

    def save():
        r['seconds'] = time.monotonic() - start
        r['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        (a.out / 'R4_CONTACT_PRISMS_NATIVE.json').write_text(json.dumps(r, indent=2, allow_nan=False) + '\n')

    try:
        require(r['runtime'] == c['expected_43_package_versions'], 'Original package versions differ')
        for x in c['bound_sources']:
            require(identity(x['path']) == x['identity'], 'Bound source differs')
        for x in c['bound_records']:
            require(identity(x['path']) == x['identity'], 'Bound record differs')
        sys.path.insert(0, str(Path(c['original_export_helper']).parent))
        helper = load(c['original_export_helper'], 'r4_original_R3_native_export_helper')
        native = helper.extension.load_inventory(c['inventory_source']); p = native.p
        parents = {}
        for x in c['inputs']:
            require(identity(x['path']) == x['identity'], 'Original whole input differs')
            roots = native.cq.importers.importStep(x['path']).vals()
            require(len(roots) == 1, 'One whole root required')
            parent = p.single(roots[0]); parents[x['role']] = parent
            r['parents'][x['role']] = helper.export(parent, x['role'] + '_whole', a.out, native, p)
        for spec in c['prisms']:
            parent = parents[spec['parent']]
            box = p.box(*spec['bounds_mm'])
            common = box.intersect(parent); missing = box.cut(parent)
            outside = box.translate((100, 0, 0)); outside_missing = outside.cut(parent)
            row = {'name': spec['name'], 'parent': spec['parent'], 'bounds_mm': spec['bounds_mm'],
                   'source_box': helper.export(box, spec['name'] + '_source', a.out, native, p),
                   'actual_intersection': helper.export(common, spec['name'] + '_intersection', a.out, native, p),
                   'source_minus_whole_parent': helper.export(missing, spec['name'] + '_missing', a.out, native, p),
                   'outside_control': helper.export(outside, spec['name'] + '_outside', a.out, native, p),
                   'outside_control_minus_parent': helper.export(outside_missing, spec['name'] + '_outside_missing', a.out, native, p)}
            volume = p.volume(box); cv = p.volume(common); mv = p.volume(missing); ov = p.volume(outside_missing)
            row['original_Common_upper_bound_pass'] = 0 <= cv <= min(volume, p.volume(parent)) + p.TOL
            row['native_containment_original_gate_pass'] = mv <= p.TOL and abs(cv - volume) <= p.TOL
            row['missing_is_topologically_empty'] = row['source_minus_whole_parent']['guard']['native_topologically_empty']
            row['outside_control_is_rejected'] = ov > p.TOL and abs(ov - volume) <= p.TOL
            row['native_volume_budget_residual_mm3'] = volume - cv - mv
            row['exact_native_set_containment_claimed'] = False
            r['prisms'].append(row); save()
        r['sources_and_inputs_unchanged'] = all(identity(x['path']) == x['identity'] for x in c['inputs'] + c['bound_sources'] + c['bound_records'])
        r['runtime_unchanged'] = {n: importlib.metadata.version(n) for n in c['expected_43_package_versions']} == r['runtime']
        r['all_native_containments_and_negative_controls_pass'] = len(r['prisms']) == 4 and all(
            all(x[k] for k in ('original_Common_upper_bound_pass', 'native_containment_original_gate_pass',
                              'missing_is_topologically_empty', 'outside_control_is_rejected')) for x in r['prisms'])
        r['completed'] = r['sources_and_inputs_unchanged'] and r['runtime_unchanged'] and r['all_native_containments_and_negative_controls_pass']
    except Exception as exc:
        r['issues'].append({'type': type(exc).__name__, 'message': str(exc)})
    save(); print(json.dumps({k: r[k] for k in ('completed', 'seconds', 'peak_RSS_bytes', 'issues')}), flush=True)
    return 0 if r['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
