"""Actual stdlib format-dispatch controls, not CAD or topology qualification."""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.abc
import importlib.util
import json
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
SCIENCE = ROOT / 'r5-native/trim-core-witness'
FORBIDDEN = {'cadquery', 'OCP', 'vtk', 'vtkmodules', 'numpy', 'scipy', 'shapely', 'casadi', 'nlopt'}


def identity(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise ValueError('Fresh serialization control output required')
    out.mkdir(parents=True)
    blocked = []
    class NoNative(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in FORBIDDEN:
                blocked.append(fullname)
                raise RuntimeError('Native/numeric import prohibited during stdlib format controls')
    sys.meta_path.insert(0, NoNative())
    start = time.monotonic()
    contract = json.loads((SCIENCE / 'R5_NATIVE_TRIM_CORE_PRODUCER_CONTRACT.json').read_text())
    originals = [row for row in contract['bound_records'] if row['path'].endswith('.brep')]
    report = {'schema': 'razr-r5-ASCII-BREP-dispatch-actual-stdlib-controls-v1', 'completed': False,
              'native_execution': False, 'native_topology_validity_claimed': False,
              'header_recognition_never_substitutes_for_native_Read_status_or_nonNull_check': True,
              'controls': [], 'source_comparisons': [], 'blocked_native_import_attempts': blocked}
    header = b'DBRep_DrawableShape\n\nCASCADE Topology V3, (c) Open Cascade\n'
    fixtures = {
        'empty': b'',
        'truncated_header': b'DBRep_DrawableShape\n\nCASCADE Topology',
        'binary_format': b'\nOpen CASCADE Topology V4 (c) Open Cascade\n\x00\x01\x02',
        'other_ASCII_version': header.replace(b'Topology V3', b'Topology V2'),
        'unknown_prefix': b'UNKNOWN\n' + header,
        'embedded_valid_header': b'\x00\xff' + header,
        'wrong_line_endings': header.replace(b'\n', b'\r\n'),
    }
    for name, data in fixtures.items():
        (out / (name + '.brep')).write_bytes(data)
    pairs = [('native_trim_core_witness_r5.py', 'native_trim_core_witness_r5_ascii_v2.py', 'require_ascii_brep_v3'),
             ('read_native_trim_core_witness_r5.py', 'read_native_trim_core_witness_r5_ascii_v2.py', 'independent_ascii_brep_v3_header')]
    geometry_calls = {'intersect', 'cut', 'translate', 'trim', 'whole_material', 'BRepBuilderAPI_MakeFace', 'Volume', 'Area'}
    for old_name, name, function in pairs:
        path = SCIENCE / name
        before = identity(path)
        spec = importlib.util.spec_from_file_location(name.removesuffix('.py'), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        check = getattr(module, function)
        for item in originals:
            result = check(Path(item['path']), 'OCCT_ASCII_BREP_V3')
            if result['header_hex'] != header.hex() or not result['header_recognition_is_not_native_validity'] or identity(item['path']) != item['identity']:
                raise AssertionError('Original header/input identity not preserved')
            report['controls'].append({'source': name, 'case': str(Path(item['path']).relative_to(ROOT)),
                                       'expected': 'exact_ASCII_V3_format_only', 'observed': result, 'passed': True})
        for case in fixtures:
            try:
                check(out / (case + '.brep'), 'OCCT_ASCII_BREP_V3')
            except ValueError as exc:
                report['controls'].append({'source': name, 'case': case, 'expected': 'reject_before_native_API',
                                           'exception': {'type': type(exc).__name__, 'message': str(exc)}, 'passed': True})
            else:
                raise AssertionError('Nonmatching input format unexpectedly admitted: ' + case)
        try:
            check(out / 'never-created-path', 'OCCT_BINARY_BREP')
        except ValueError as exc:
            report['controls'].append({'source': name, 'case': 'unsupported_declared_format_before_file_access',
                                       'expected': 'reject_before_file_or_native_API',
                                       'exception': {'type': type(exc).__name__, 'message': str(exc)}, 'passed': True})
        else:
            raise AssertionError('Unsupported declared format accepted')
        old_tree, tree = ast.parse((SCIENCE / old_name).read_text()), ast.parse(path.read_text())
        def calls(t):
            result = []
            for node in ast.walk(t):
                if isinstance(node, ast.Call):
                    name_ = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ''
                    if name_ in geometry_calls:
                        result.append(ast.dump(node, include_attributes=False))
            return sorted(result)
        comparison = {'source': name, 'source_identity': before, 'predecessor_identity': identity(SCIENCE / old_name),
                      'all_geometry_operator_call_ASTs_equal': calls(old_tree) == calls(tree),
                      'geometry_operator_call_count': len(calls(tree)),
                      'BRepTools_Read_calls': 0, 'BRepTools_Write_calls': 0,
                      'BinTools_calls': 0, 'native_read_status_asserted': False, 'native_null_read_rejected': False}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                owner = node.func.value.id
                if owner == 'BRepTools' and node.func.attr == 'Read_s': comparison['BRepTools_Read_calls'] += 1
                if owner == 'BRepTools' and node.func.attr == 'Write_s': comparison['BRepTools_Write_calls'] += 1
                if owner == 'BinTools': comparison['BinTools_calls'] += 1
            if isinstance(node, ast.FunctionDef) and node.name == 'read':
                for call in ast.walk(node):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in ('need', 'require') and call.args:
                        expr = call.args[0]
                        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute) and expr.func.attr == 'Read_s':
                            comparison['native_read_status_asserted'] = True
                        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not) and isinstance(expr.operand, ast.Call) and isinstance(expr.operand.func, ast.Attribute) and expr.operand.func.attr == 'IsNull':
                            comparison['native_null_read_rejected'] = True
        if not (comparison['all_geometry_operator_call_ASTs_equal'] and comparison['BRepTools_Read_calls'] == comparison['BRepTools_Write_calls'] == 1 and comparison['BinTools_calls'] == 0 and comparison['native_read_status_asserted'] and comparison['native_null_read_rejected']):
            raise AssertionError('Serialization revision changed geometric operators or omitted read/write/null gates')
        if identity(path) != before:
            raise AssertionError('New named source changed during actual control execution')
        report['source_comparisons'].append(comparison)
    report['native_numeric_modules_loaded'] = sorted(n for n in sys.modules if n.split('.')[0] in FORBIDDEN)
    report['completed'] = len(report['controls']) == 28 and not blocked and not report['native_numeric_modules_loaded']
    report['seconds'] = time.monotonic() - start
    report['control_source_identity'] = identity(__file__)
    (out / 'R5_ASCII_BREP_DISPATCH_CONTROLS_ACTUAL.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'completed': report['completed'], 'controls': len(report['controls']), 'seconds': report['seconds'], 'native_execution': False}), flush=True)
    return 0 if report['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
