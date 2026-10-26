"""Execute only source-bound arithmetic regressions and preparation metadata."""
from __future__ import annotations

import argparse
import ast
import io
import json
from pathlib import Path
import resource
import sys
import time
import unittest

import verify_seating_native as adapter
import test_seating_arithmetic as tests
import test_seating_checkpoint as checkpoint_tests
import test_owned_process as owned_process_tests
import test_seating_supervisor_lifecycle as lifecycle_tests


def preserved_v1_and_geometry():
    original = adapter.HERE.parent / 'g2_seating'
    manifest = original / 'prepared-v1/executed-source-manifest.json'
    if adapter.digest(manifest) != '2f677af6163a421da21f3c8b719071c2e5b60a46a36e7f6a21cf991bae4c93b3':
        raise ValueError('original prepared-v1 manifest changed')
    records = json.loads(manifest.read_text())
    for name, record in records.items():
        if adapter.digest(original / name) != record['sha256'] or adapter.digest(record['preserved_source_path']) != record['sha256']:
            raise ValueError('original v1 executed source/current copy changed: ' + name)
    for name in ('seating_domain.py', 'seating_enclosures.py', 'seating-inventory.json', 'test_seating_arithmetic.py'):
        if adapter.digest(adapter.HERE / name) != records[name]['sha256']:
            raise ValueError('v2 changed an original geometric/domain/inventory/arithmetic-test source: ' + name)
    old = ast.parse((original / 'verify_seating_native.py').read_text())
    new = ast.parse((adapter.HERE / 'verify_seating_native.py').read_text())
    old_nodes = {node.name: node for node in old.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    new_nodes = {node.name: node for node in new.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    changed_flow = {'adapter_identity', 'preparation_report', 'run_native', 'main'}
    unchanged = []
    for name in set(old_nodes) - changed_flow:
        if ast.dump(old_nodes[name]) != ast.dump(new_nodes[name]):
            raise ValueError('original geometry/evidence helper changed: ' + name)
        unchanged.append(name)

    def call_name(node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute): return call_name(node.value) + '.' + node.attr
        return ''

    geometry = {'nominal.full_scene', 'domain.rigid_laws', 'verify_factory_rigid_laws',
        'nominal.continuous_pair', 'flexible_rigid_interval', 'enclosure.flex_flex_certificate',
        'p.whole_material', 'p.bounds', 'p.native_inputs', 'CageCache', 'Budget'}
    calls = lambda node: [ast.dump(item) for item in ast.walk(node)
                          if isinstance(item, ast.Call) and call_name(item.func) in geometry]
    if calls(old_nodes['run_native']) != calls(new_nodes['run_native']):
        raise ValueError('the actual native geometry/constraint calls changed')
    return {'original_manifest_sha256': adapter.digest(manifest),
            'original_six_sources_unchanged': {name: record['sha256'] for name, record in records.items()},
            'four_geometry_inventory_and_regression_files_byte_identical': True,
            'unchanged_helper_function_and_class_AST_names': sorted(unchanged),
            'run_native_geometry_call_AST_unchanged': True}


def preserved_r2_and_raw_contract():
    original = adapter.HERE.parent/'g2_seating_v2'
    manifest = original/'prepared-v2-r2/executed-source-manifest.json'
    if adapter.digest(manifest) != '1024dc5aa4e8cc2011b4201ea73f84abe78f6695ed27e5b70e517d6e56af867c':
        raise ValueError('original prepared-v2-r2 manifest changed')
    records = json.loads(manifest.read_text())
    for name, record in records.items():
        if adapter.digest(original/name) != record['sha256'] or adapter.digest(record['preserved_source_path']) != record['sha256']:
            raise ValueError('original r2 source or preserved execution bytes changed: '+name)
    unchanged = ('seating_domain.py', 'seating_enclosures.py', 'seating-inventory.json',
                 'test_seating_arithmetic.py', 'seating_checkpoint.py',
                 'check_seating_checkpoint.py', 'test_seating_checkpoint.py')
    for name in unchanged:
        if adapter.digest(adapter.HERE/name) != records[name]['sha256']:
            raise ValueError('r3 changed an original geometry/raw-checkpoint qualification source: '+name)
    definitions = lambda path: {node.name: ast.dump(node, include_attributes=False)
        for node in ast.parse(path.read_text()).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    old = definitions(original/'verify_seating_native.py')
    new = definitions(adapter.HERE/'verify_seating_native.py')
    if set(old) != set(new) or any(old[name] != new[name] for name in old if name not in ('adapter_identity', 'main')):
        raise ValueError('r3 changed native computation, geometry, budget or raw qualification functions')
    return {'original_r2_manifest_sha256': adapter.digest(manifest),
            'original_r2_ten_sources_and_execution_copies_unchanged': True,
            'unchanged_geometry_raw_reader_and_original_regression_files': list(unchanged),
            'all_original_worker_definition_AST_unchanged_except_source_path_and_early_handshake': True,
            'native_computation_and_Budget_AST_unchanged': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--expected-head', default=adapter.DEFAULT_HEAD)
    args = parser.parse_args(argv)
    output = args.output_directory.resolve()
    if output.exists() or output.is_relative_to(adapter.ROOT.resolve()):
        raise ValueError('new scratch output directory outside the repository required')
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    preserved_before = preserved_v1_and_geometry()
    r2_before = preserved_r2_and_raw_contract()
    before = adapter.arithmetic_repository_identity(args.expected_head)
    own_before = adapter.adapter_identity()
    copies = output / 'executed-source-bytes'; copies.mkdir()
    manifest = {}
    for name, digest in own_before.items():
        source, target = adapter.HERE / name, copies / name
        target.write_bytes(source.read_bytes())
        if adapter.digest(source) != digest or adapter.digest(target) != digest:
            raise ValueError('v3 source changed during archival copy')
        manifest[name] = {'sha256': digest, 'bytes': target.stat().st_size,
                         'original_execution_path': str(source), 'preserved_source_path': str(target)}
    (output / 'executed-source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    environment = adapter.postguard.check_environment.inspect_environment(adapter.ROOT)
    if environment.get('passed') is not True:
        raise ValueError('arithmetic regressions require the existing locked environment')
    stream = io.StringIO()
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(tests),
                               unittest.defaultTestLoader.loadTestsFromModule(checkpoint_tests),
                               unittest.defaultTestLoader.loadTestsFromModule(owned_process_tests),
                               unittest.defaultTestLoader.loadTestsFromModule(lifecycle_tests)])
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (output / 'arithmetic-tests.log').write_text(stream.getvalue())
    after = adapter.arithmetic_repository_identity(args.expected_head)
    own_after = adapter.adapter_identity()
    environment_after = adapter.postguard.check_environment.inspect_environment(adapter.ROOT)
    preserved_after = preserved_v1_and_geometry()
    r2_after = preserved_r2_and_raw_contract()
    cad_imported = any(name == 'cadquery' or name == 'OCP' or name.startswith('OCP.') for name in sys.modules)
    unchanged = (before == after and own_before == own_after and environment == environment_after
                 and preserved_before == preserved_after and r2_before == r2_after)
    record = {'schema': 'razr-seating-source-bound-arithmetic-and-supervision-regressions-v3',
              'expected_head': args.expected_head, 'test_count': result.testsRun,
              'failures': [(str(test), detail) for test, detail in result.failures],
              'errors': [(str(test), detail) for test, detail in result.errors],
              'skipped': [(str(test), reason) for test, reason in result.skipped],
              'passed': result.wasSuccessful() and unchanged and not cad_imported and not result.skipped,
              'adapter_source_sha256_before': own_before, 'adapter_source_sha256_after': own_after,
              'repository_identity_before': before, 'repository_identity_after': after,
              'source_identity_unchanged': unchanged, 'locked_environment': environment,
              'locked_environment_after': environment_after,
              'v1_preservation_and_geometry_before': preserved_before,
              'v1_preservation_and_geometry_after': preserved_after,
              'r2_preservation_and_raw_contract_before': r2_before,
              'r2_preservation_and_raw_contract_after': r2_after,
              'CAD_imported': cad_imported, 'native_checks_executed': False,
              'actual_finite_cell_crosschecks': 4 * sum(len(s['s']) - 1 for s, _ in tests.FiniteMaterialEnclosureTests.pose_sections.values()),
              'actual_taper_polygon_crosschecks': 6 * 2 * 2 * 2,
              'cell_crosschecks_are_regressions_not_substitutes_for_continuous_coverage_proof': True,
              'seconds': time.monotonic() - started, 'peak_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'complete_G2_qualification': False, 'candidate_go': False,
              'fixture_fabrication_go': False, 'manufacturing_go': False}
    (output / 'arithmetic-tests-report.json').write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
    if record['passed']:
        prepared = adapter.preparation_report(args.expected_head)
        (output / 'preparation-report.json').write_text(json.dumps(prepared, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: record[key] for key in ('test_count', 'passed', 'seconds', 'peak_RSS_KiB',
                     'actual_finite_cell_crosschecks', 'actual_taper_polygon_crosschecks', 'CAD_imported')}))
    return 0 if record['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
