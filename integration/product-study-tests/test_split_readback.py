"""Omitted STEP states and inconsistent manifests must never report a pass."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('split_reader', ROOT/'integration/verify_product_split_assembly.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class SplitReadbackBoundaryTests(unittest.TestCase):
    def test_empty_or_missing_pose_is_rejected_before_any_step_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for poses in ({}, {'STOW': {}}):
                (root/'manifest.json').write_text(json.dumps({'schema':'razr-common-split-assembly-v1','poses':poses}))
                with self.assertRaisesRegex(ValueError, 'all three'):
                    reader.verify(root, root/'result.json')
                self.assertFalse((root/'result.json').exists())

    def test_empty_participant_set_or_wrong_count_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for pose, error in [({'parts': {}}, 'complete participant'),
                                ({'parts': {'part': {}}, 'total_participants': 2,
                                  'combined': {'expected_solids': 1}}, 'counts disagree'),
                                ({'parts': {'part': {'volume_mm3': 1., 'bounds_mm': [0., 1.]}},
                                  'total_participants': 1, 'combined': {'expected_solids': 1}}, 'geometry signature'),
                                ({'parts': {'part': {'volume_mm3': 1., 'bounds_mm': [0., 1., 0., 1., 0., float('nan')]}},
                                  'total_participants': 1, 'combined': {'expected_solids': 1}}, 'geometry signature')]:
                (root/'manifest.json').write_text(json.dumps({'schema':'razr-common-split-assembly-v1',
                    'poses': {name: pose for name in ('STOW','PREDOCK','OPEN')}}))
                with self.assertRaisesRegex(ValueError, error):
                    reader.verify(root, root/'result.json')
                self.assertFalse((root/'result.json').exists())


if __name__ == '__main__':
    unittest.main()
