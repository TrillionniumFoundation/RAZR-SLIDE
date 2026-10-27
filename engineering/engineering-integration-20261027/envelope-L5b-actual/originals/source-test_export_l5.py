"""Small IO/name/projection regressions, explicitly not CAD test results."""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import export_l5 as export
from l5_science_contract import scientific_filename

ROOT=None


def producer_fixture():
    manifest=ROOT/'engineering/cam-coupling-20261015/geometry-v5-manifest.json'
    archive=manifest.parent/json.loads(manifest.read_text())['archive']
    return {'construction':{'current_candidate_factory_metadata':{'research_relief':{'KEY_source':{
        'original_complete_KEY_source':{'archive':str(archive),'archive_sha256':export.ARCHIVE_SHA},
        'actual_geometry_value':1e-8}}}},'test_only_not_native_geometry_result':True}


class ExportTests(unittest.TestCase):
    def test_exact_emitted_names(self):
        names=['original-case-011-layer-0-Common.brep','current-case-018-layer-0-bridge.brep',
            'current-case-011-layer-1-endpoint-0-difference.brep','current-case-011-whole-source-omission.brep',
            'control-reversed-capsule-bridge.brep','control-tiny-capsule-short-disk.brep',
            'control-zero-source-disk.brep','control-original-extrusion-original-face.step',
            'control-original-extrusion-v2-region-4095.brep']
        for n in names:self.assertTrue(scientific_filename(n),n)
        for n in ('../report.json','control-private-secret.brep','current-case-999-layer-0.brep','native.log'):
            self.assertFalse(scientific_filename(n),n)

    def test_precise_single_field_projection(self):
        source=producer_fixture();untouched=copy.deepcopy(source)
        value,changes=export.project_producer(source,ROOT)
        self.assertEqual(source,untouched);self.assertEqual(len(changes),1)
        self.assertEqual(value['construction']['current_candidate_factory_metadata']['research_relief']['KEY_source']['actual_geometry_value'],1e-8)
        self.assertEqual(changes[0]['archive_content_sha256'],export.ARCHIVE_SHA)
        export.no_runtime(value)
        changed=producer_fixture();changed['unexpected_runtime']='hidden /tmp/private-location'
        with self.assertRaises(ValueError):export.project_producer(changed,ROOT)
        changed=producer_fixture();changed['construction']['current_candidate_factory_metadata']['research_relief']['KEY_source']['original_complete_KEY_source']['archive']='/tmp/unreviewed-other-archive'
        with self.assertRaises(ValueError):export.project_producer(changed,ROOT)

    def test_failure_preserves_all_other_science_and_manifest(self):
        with tempfile.TemporaryDirectory(prefix='l5-export-regression-') as td:
            base=Path(td);science=base/'case/l5/worker/science';science.mkdir(parents=True)
            sources=base/'sources';sources.mkdir();out=base/'published'
            (science/'report.json').write_text(json.dumps(producer_fixture()))
            for name in ('original-case-011-layer-0-Common.brep','current-case-018-fixed-input.brep'):
                (science/name).write_bytes(b'Synthetic fixture bytes; not a CAD BREP.\n')
            (science/'PRIVATE_RUNTIME.log').write_text('never export this fixture')
            (science/'current-case-011.json').write_text(json.dumps({'location':'/tmp/unreviewed-fixture'}))
            (science/'linked-secret').symlink_to(science/'PRIVATE_RUNTIME.log')
            code=export.execute(base/'case',sources,out,ROOT);self.assertEqual(code,2)
            manifest=json.loads((out/'MANIFEST.json').read_text())
            self.assertEqual(set(manifest),{p.name for p in out.iterdir()}-{'MANIFEST.json'})
            self.assertIn('report.engineering.json',manifest);self.assertNotIn('report.json',manifest)
            for name,row in manifest.items():
                data=(out/name).read_bytes();self.assertEqual(len(data),row['bytes']);self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
            scope=json.loads((out/'EXPORT_SCOPE.json').read_text());self.assertEqual(len(scope['rejected_items']),3)
            self.assertNotIn('PRIVATE_RUNTIME',json.dumps(scope));self.assertNotIn('unreviewed-fixture',json.dumps(scope))
            self.assertIn('original-case-011-layer-0-Common.brep',manifest)
            self.assertIn('current-case-018-fixed-input.brep',manifest)
            projection=json.loads((out/'report.engineering.json').read_text())
            self.assertEqual(projection['original']['sha256'],hashlib.sha256((science/'report.json').read_bytes()).hexdigest())
            self.assertTrue(projection['derived_projection_not_raw_original'])

    def test_worker_and_export_source_inventories_equal(self):
        node=ast.parse((Path(__file__).resolve().parent/'run_l5.py').read_text())
        assigned=next(x.value for x in node.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in x.targets))
        self.assertEqual(tuple(ast.literal_eval(assigned)),export.SOURCE_NAMES)
        for n in export.SOURCE_NAMES:self.assertTrue((Path(__file__).resolve().parent/n).is_file(),n)

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):export.no_runtime({'bad':float('nan')})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True)
    args,remaining=parser.parse_known_args();ROOT=args.source_root.resolve();unittest.main(argv=['test_export_l5.py',*remaining])
