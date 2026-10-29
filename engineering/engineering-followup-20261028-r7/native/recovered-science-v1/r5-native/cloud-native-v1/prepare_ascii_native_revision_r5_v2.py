"""Create new named ASCII-only native workers; preserve all frozen predecessors."""
from pathlib import Path
import ast
import difflib
import hashlib
import json


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCIENCE = ROOT / 'r5-native/trim-core-witness'
FORMAT = 'OCCT_ASCII_BREP_V3'
HEADER = b'DBRep_DrawableShape\n\nCASCADE Topology V3, (c) Open Cascade\n'


def identity(path):
    with Path(path).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': Path(path).stat().st_size, 'sha256': digest}


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Expected one exact predecessor source fragment: ' + old[:90])
    return source.replace(old, new, 1)


def main():
    original_contract = json.loads((SCIENCE / 'R5_NATIVE_TRIM_CORE_PRODUCER_CONTRACT.json').read_text())
    rows = []
    for item in original_contract['bound_records']:
        path = Path(item['path'])
        if path.suffix == '.brep':
            with path.open('rb') as stream:
                observed = stream.read(len(HEADER))
            if observed != HEADER or identity(path) != item['identity']:
                raise ValueError('Frozen original BREP byte/header identity differs')
            rows.append({'path': str(path.relative_to(ROOT)), 'identity': item['identity'],
                         'observed_exact_header_hex': observed.hex(), 'observed_format': FORMAT})
    if len(rows) != 6:
        raise ValueError('Exactly six frozen complete material originals required')
    producer_old = SCIENCE / 'native_trim_core_witness_r5.py'
    producer = SCIENCE / 'native_trim_core_witness_r5_ascii_v2.py'
    reader_old = SCIENCE / 'read_native_trim_core_witness_r5.py'
    reader = SCIENCE / 'read_native_trim_core_witness_r5_ascii_v2.py'
    for p in (producer, reader):
        if p.exists():
            raise ValueError('Do not overwrite a named scientific revision')
    p = producer_old.read_text()
    p = replace_once(p, 'def main():\n', '''def require_ascii_brep_v3(path, declared_format):
    """Classify only the exact registered header; native topology is checked later."""
    need(declared_format == "OCCT_ASCII_BREP_V3", "Unsupported declared BREP serialization")
    expected = b"DBRep_DrawableShape\\n\\nCASCADE Topology V3, (c) Open Cascade\\n"
    with Path(path).open("rb") as stream:
        header = stream.read(len(expected))
    need(header == expected, "Original/new BREP header is not registered ASCII V3")
    return {"declared": declared_format, "header_hex": header.hex(),
            "header_recognition_is_not_native_validity": True}


def main():
''')
    p = replace_once(p, '    need(ident(__file__) == c["worker_identity"], "Producer source changed")',
                        '    need(ident(__file__) == c["worker_identity"], "Producer source changed")\n    need(c["native_brep_serialization"] == "OCCT_ASCII_BREP_V3", "Explicit ASCII BREP contract required")')
    p = replace_once(p, '"schema": "r5-finite-native-trim-core-witness-v1",',
                        '"schema": "r5-finite-native-trim-core-witness-ascii-v2", "native_brep_serialization": c["native_brep_serialization"],')
    p = replace_once(p, '        from OCP.BinTools import BinTools', '        from OCP.BRepTools import BRepTools')
    p = replace_once(p, '        from OCP.BRep import BRep_Tool', '        from OCP.BRep import BRep_Tool, BRep_Builder')
    p = replace_once(p, '            status = BinTools.Write_s(shape.wrapped, str(path))',
                        '            status = BRepTools.Write_s(shape.wrapped, str(path))')
    p = replace_once(p, '            need(status is not False and path.is_file(), "Native BREP export failed")',
                        '            need(status is not False and path.is_file(), "Native ASCII BREP export failed")\n            serialization = require_ascii_brep_v3(path, c["native_brep_serialization"])')
    p = replace_once(p, 'return {"path": str(path.relative_to(a.out)), **ident(path), "native": summary}',
                        'return {"path": str(path.relative_to(a.out)), **ident(path), "native": summary, "serialization": serialization}')
    p = replace_once(p, '''        def read(path):
            native_shape = TopoDS_Shape()
            need(BinTools.Read_s(native_shape, str(path)), "Native BREP read failed")
            return cq.Shape.cast(native_shape)''', '''        def read(path):
            require_ascii_brep_v3(path, c["native_brep_serialization"])
            native_shape = TopoDS_Shape()
            need(BRepTools.Read_s(native_shape, str(path), BRep_Builder()), "Native ASCII BREP read failed")
            need(not native_shape.IsNull(), "Native ASCII BREP reader returned a null shape")
            return cq.Shape.cast(native_shape)''')
    r = reader_old.read_text()
    r = replace_once(r, 'def main():\n', '''def independent_ascii_brep_v3_header(path, declared_format):
    """Separate bounded line parser; success identifies format, never validity."""
    require(declared_format == "OCCT_ASCII_BREP_V3", "Unsupported independent BREP serialization")
    with Path(path).open("rb") as stream:
        first, second, third = stream.readline(128), stream.readline(128), stream.readline(128)
    require((first, second, third) == (b"DBRep_DrawableShape\\n", b"\\n", b"CASCADE Topology V3, (c) Open Cascade\\n"),
            "Independent BREP header is not registered ASCII V3")
    return {"declared": declared_format, "header_hex": (first + second + third).hex(),
            "header_recognition_is_not_native_validity": True}


def main():
''')
    r = replace_once(r, '    pc = json.loads(Path(contract["producer_contract"]["path"]).read_text())',
                        '    pc = json.loads(Path(contract["producer_contract"]["path"]).read_text())\n    require(pc["native_brep_serialization"] == "OCCT_ASCII_BREP_V3", "Explicit independent ASCII contract required")')
    r = replace_once(r, '"schema": "r5-independent-native-trim-core-readback-v1",',
                        '"schema": "r5-independent-native-trim-core-readback-ascii-v2", "native_brep_serialization": pc["native_brep_serialization"],')
    r = replace_once(r, '        from OCP.BinTools import BinTools', '        from OCP.BRepTools import BRepTools')
    r = replace_once(r, '        from OCP.BRep import BRep_Tool', '        from OCP.BRep import BRep_Tool, BRep_Builder')
    r = replace_once(r, '''        def read(path):
            raw = TopoDS_Shape()
            require(BinTools.Read_s(raw, str(path)), "Independent BREP read failed")
            return cq.Shape.cast(raw)''', '''        def read(path):
            independent_ascii_brep_v3_header(path, pc["native_brep_serialization"])
            raw = TopoDS_Shape()
            require(BRepTools.Read_s(raw, str(path), BRep_Builder()), "Independent ASCII BREP read failed")
            require(not raw.IsNull(), "Independent ASCII reader returned a null shape")
            return cq.Shape.cast(raw)''')
    r = replace_once(r, '            status = BinTools.Write_s(shape.wrapped, str(file))',
                        '            status = BRepTools.Write_s(shape.wrapped, str(file))')
    old = '            require(status is not False and file.is_file(), "Independent native output failed")'
    if old not in r:
        raise ValueError('Independent write-success source fragment requires review')
    r = replace_once(r, old, old + '\n            independent_ascii_brep_v3_header(file, pc["native_brep_serialization"])')
    ast.parse(p)
    ast.parse(r)
    if 'BinTools' in p or 'BinTools' in r:
        raise ValueError('Mixed binary/ASCII API remains in revised worker')
    producer.write_text(p)
    reader.write_text(r)
    diffs = {}
    for old, new in ((producer_old, producer), (reader_old, reader)):
        diff = ''.join(difflib.unified_diff(old.read_text().splitlines(True), new.read_text().splitlines(True), fromfile=old.name, tofile=new.name))
        name = new.name + '.diff'
        (HERE / 'serialization-v1' / name).write_text(diff)
        diffs[name] = identity(HERE / 'serialization-v1' / name)
    receipt = {'schema': 'razr-r5-native-explicit-ASCII-BREP-revision-v1', 'native_worker_executed': False,
               'original_six_inputs': rows, 'original_input_bytes_changed': False,
               'old_frozen_sources_preserved': {str(x.relative_to(ROOT)): identity(x) for x in (producer_old, reader_old)},
               'new_sources': {str(x.relative_to(ROOT)): identity(x) for x in (producer, reader)},
               'format_contract': FORMAT, 'actual_native_write_and_read_pair': 'BRepTools.Write_s / BRepTools.Read_s with BRep_Builder',
               'output_format_same_as_all_six_registered_input_originals': True,
               'producer_and_reader_header_parsers_separate': True,
               'null_shape_not_success': True, 'valid_topologically_empty_compound_not_conflated_with_null_shape': True,
               'native_Boolean_operators_patch_construction_and_geometric_thresholds_changed': False,
               'original_64MiB_scientific_and_six_native_resource_limits_changed': False,
               'old_v3_publication_was_static_not_native_execution': True, 'diffs': diffs,
               'official_sources': [
                   'https://raw.githubusercontent.com/CadQuery/cadquery/v2.7.0/cadquery/occ_impl/shapes.py',
                   'https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_1/src/BinTools/BinTools.cxx',
                   'https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_1/src/BinTools/BinTools_ShapeSet.cxx']}
    target = HERE / 'serialization-v1/R5_NATIVE_ASCII_BREP_REVISION_PREPARATION.json'
    if target.exists():
        raise ValueError('New immutable format-revision receipt required')
    target.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'new_sources': receipt['new_sources'], 'original_inputs': len(rows), 'native_execution': False}), flush=True)


if __name__ == '__main__':
    main()
