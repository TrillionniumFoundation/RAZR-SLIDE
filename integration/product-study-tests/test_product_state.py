"""Regression tests for the actual cross-entry-point drift found in October 2026."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('sync_current_design', ROOT / 'tools/sync_current_design.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class ProductStateTests(unittest.TestCase):
    def setUp(self):
        self.current, self.manifest = sync.load_inputs(ROOT)
        self.status = json.loads((ROOT / 'status.json').read_text())

    def test_generated_entrypoints_are_current(self):
        for path, expected in sync.expected_files(ROOT).items():
            self.assertEqual(path.read_text(), expected, str(path))

    def test_manifest_growth_never_inflates_completed_run(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['suites'][0]['minimum_tests'] += 7
        manifest['minimum_total_tests'] += 7
        actual = sync.render_status(self.status, self.current, manifest)
        units = actual['current_unit_tests']
        self.assertEqual(units['configured_minimum'], manifest['minimum_total_tests'])
        self.assertEqual(units['completed_runs'], self.current['completed_unit_runs'])
        self.assertTrue(units['configured_count_is_not_a_pass'])

    def test_later_closure_keeps_failed_diagnostic_history(self):
        actual = sync.render_status(self.status, self.current, self.manifest)
        self.assertTrue(actual['current_spatial_contact']['all_eight_cases_closed'])
        self.assertEqual(actual['current_spatial_contact']['remaining_not_run'], [])
        self.assertEqual(actual['current_volume_refinement']['completed_level2_cases'], [4, 5, 6, 7])
        old = actual['current_contact_field_audit']
        self.assertFalse(old['local_contact_nonpenetration_passed'])
        self.assertIn('rejected pre-contact-solve', old['historical_stage_scope'])

    def test_open_draft_cannot_be_marked_as_main(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'design').mkdir()
            (root / 'tools').mkdir()
            current = copy.deepcopy(self.current)
            current['open_research_prs'][0]['in_main'] = True
            (root / 'design/current_product.json').write_text(json.dumps(current))
            (root / 'tools/test_suites.json').write_text(json.dumps(self.manifest))
            with self.assertRaisesRegex(ValueError, 'open research PR'):
                sync.load_inputs(root)

    def test_stale_overview_is_detected_and_repair_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in ['design/current_product.json', 'tools/test_suites.json',
                             sync.OVERVIEW.as_posix(), 'CURRENT_DESIGN.md', 'status.json']:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text((ROOT / relative).read_text())
            readme = root / sync.OVERVIEW
            readme.write_text(readme.read_text().replace('Configured unit validation:', 'Old count:'))
            expected = sync.expected_files(root)
            self.assertNotEqual(readme.read_text(), expected[readme])
            for path, text in expected.items():
                path.write_text(text)
            for path, text in sync.expected_files(root).items():
                self.assertEqual(path.read_text(), text)


if __name__ == '__main__':
    unittest.main()
