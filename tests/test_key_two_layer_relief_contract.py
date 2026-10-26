"""Pure contract regressions for the independently selected two-layer KEY cut."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEY = ROOT/'engineering/engineering-integration-20261025/geometry/key'
PROBE = r"""
import copy
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
import read_key_trial as reader
import stow_two_layer_face_relief as v2
import stow_face_relief as v1
case = sys.argv[2]
record = v2.definition()
rejected = False
if case == 'missing_secondary_strip':
    row = next(x for x in record['parts'] if x['part'] == 'R_ROOT_INNER')
    row['cut_boxes'].pop()
elif case == 'cropped_slot_domain':
    record['full_per_side_offset_projection_mm']['dq'][0] = -.02
elif case == 'wrong_KEY_X_motion':
    record['rigid_motion']['KEY'] = '(dx_side,dq_side,0)'
elif case == 'false_strength_or_tolerance':
    record['strength_or_tolerance_qualified'] = True
elif case == 'replaced_material_part':
    record['parts'][0]['part'] = 'L_KEY'
elif case == 'unknown_schema':
    record['schema'] = 'unreviewed-relief'
if case in {'missing_secondary_strip','cropped_slot_domain','wrong_KEY_X_motion',
            'false_strength_or_tolerance','replaced_material_part','unknown_schema'}:
    try:
        reader.validate_relief_definition(record)
    except ValueError:
        rejected = True
    result = {'rejected': rejected}
elif case == 'primary_material_contract_retained':
    original = {r['part']: r['cut_boxes'] for r in v1.definition()['parts']}
    fresh = {r['part']: r['cut_boxes'] for r in record['parts']}
    match = set(original) == set(fresh)
    for name, boxes in original.items():
        match &= all({k:new[k] for k in ('lo_mm','hi_mm')} == old
                     for new, old in zip(fresh[name][:len(boxes)], boxes))
    result = {'same_four_parts_and_primary_cut_coordinates': match,
              'new_box_count': sum(map(len, fresh.values())),
              'old_schema_still_recognized': reader.validate_relief_definition(v1.definition()) is None}
elif case == 'recorded_native_secondary_volume':
    sec = record['secondary_layer']
    h = -record['KEY_full_negative_offset_mm']
    predicted = .16*(h-.02) + 1.152*(h-.055)
    # D4 original STOW full-band native values; distinct from first-relief reader.
    observed = (0.012995443639309764, 0.012995443639308627)
    result = {'maximum_original_native_prediction_error_mm3': max(abs(v-predicted) for v in observed),
              'full_band_local_gap_mm': sec['inferred_nominal_KEY_face_Y_mm']-h-sec['cut_face_Y_mm'],
              'nominal_plane_new_measurement_claimed': sec['new_nominal_plane_measurement_executed'],
              'manufacturing_tolerance_claimed': sec['construction_gap_is_manufacturing_tolerance']}
elif case == 'accept_exact_definition':
    boxes = reader.validate_relief_definition(record)
    result = {'body_count': len(boxes), 'box_count': sum(map(len,boxes.values())),
              'full_slot_vertex_count': len(record['full_per_side_slot_polytope_vertices']),
              'left_right_independent': record['left_and_right_controls_remain_independent'],
              'CAD_imported': any(n == 'cadquery' or n.startswith('OCP') for n in sys.modules)}
else:
    raise ValueError('unknown test case')
print(json.dumps(result))
"""

class TwoLayerKEYReliefContractTests(unittest.TestCase):
    def run_probe(self, case):
        run = subprocess.run([sys.executable, '-B', '-c', PROBE, str(KEY), case],
                             cwd=ROOT, capture_output=True, text=True, timeout=30,
                             env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        return json.loads(run.stdout)

    def test_exact_contract_imports_no_CAD(self):
        value = self.run_probe('accept_exact_definition')
        self.assertEqual((value['body_count'], value['box_count'], value['full_slot_vertex_count']), (4,14,4))
        self.assertTrue(value['left_right_independent'])
        self.assertFalse(value['CAD_imported'])

    def test_omitting_measured_secondary_strip_is_rejected(self):
        self.assertTrue(self.run_probe('missing_secondary_strip')['rejected'])

    def test_cropping_original_slot_domain_is_rejected(self):
        self.assertTrue(self.run_probe('cropped_slot_domain')['rejected'])

    def test_fabricating_KEY_X_motion_is_rejected(self):
        self.assertTrue(self.run_probe('wrong_KEY_X_motion')['rejected'])

    def test_unearned_strength_or_tolerance_claim_is_rejected(self):
        self.assertTrue(self.run_probe('false_strength_or_tolerance')['rejected'])

    def test_cutting_a_different_material_body_is_rejected(self):
        self.assertTrue(self.run_probe('replaced_material_part')['rejected'])

    def test_unreviewed_candidate_schema_is_rejected(self):
        self.assertTrue(self.run_probe('unknown_schema')['rejected'])

    def test_existing_primary_cuts_and_old_schema_remain_supported(self):
        value = self.run_probe('primary_material_contract_retained')
        self.assertTrue(value['same_four_parts_and_primary_cut_coordinates'])
        self.assertEqual(value['new_box_count'], 14)
        self.assertTrue(value['old_schema_still_recognized'])

    def test_two_layer_arithmetic_matches_independent_D4_native_values(self):
        value = self.run_probe('recorded_native_secondary_volume')
        self.assertLess(value['maximum_original_native_prediction_error_mm3'], 1e-14)
        self.assertAlmostEqual(value['full_band_local_gap_mm'], .020, places=12)
        self.assertFalse(value['nominal_plane_new_measurement_claimed'])
        self.assertFalse(value['manufacturing_tolerance_claimed'])

if __name__ == '__main__':
    unittest.main()
