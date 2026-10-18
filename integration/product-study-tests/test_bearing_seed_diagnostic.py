"""Point coverage is useful only with correct domain identity and bounded scope."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bearing_seed_diagnostic import (bind_retained_domains, contains, coverage,
    distributed_seeds, gap_witnesses, legacy_perimeter_seeds, polygon_geometry,
    projection_bearings, sha256, verify_manifest_file)


def fixture():
    rows = [[], []]
    for body_number, body in enumerate(('panel', 'frame')):
        for bolt in range(4):
            for x, y in ((0, 0), (1, 0), (0, 1), (1, 1)):
                x += 10*bolt
                rows[body_number].append({'body': body, 'kind': 'C', 'index': bolt,
                    'axis': 2, 'direction': [0, 0, -1 if body == 'panel' else 1],
                    'density_target': [10*bolt+1, 1],
                    'polygon': [[x, y], [x+1, y], [x+1, y+1], [x, y+1]],
                    'dofs': [len(rows[body_number])]})
    return rows


class BearingSeedDiagnosticTests(unittest.TestCase):
    def test_budgeted_centroids_preserve_old_points_and_cover_interior(self):
        faces = projection_bearings(*fixture())
        old = legacy_perimeter_seeds(faces)
        new = distributed_seeds(faces, old, 16)
        self.assertEqual(new[:len(old)], old)
        self.assertEqual(len(new)-len(old), 16)
        self.assertEqual(new, distributed_seeds(faces, old, 16))
        self.assertEqual(coverage(faces, old)['faces_with_interior_point'], 0)
        self.assertEqual(coverage(faces, new)['faces_with_interior_point'], 16)
        for point in new:
            self.assertTrue(contains(faces[point['face']]['polygon'], [point['xy']])[0])

    def test_nonconvex_domain_rejected_and_clockwise_domain_supported(self):
        with self.assertRaisesRegex(ValueError, 'convex'):
            polygon_geometry([[0, 0], [2, 0], [1, .2], [2, 2], [0, 2]])
        p = [[0, 0], [0, 1], [1, 1], [1, 0]]
        self.assertTrue(contains(p, [[.5, .5]], interior=True)[0])
        self.assertFalse(contains(p, [[0, .5]], interior=True)[0])

    def test_face_order_and_projection_operator_are_both_bound(self):
        rows = fixture()
        faces = projection_bearings(*rows)
        domains = []
        for f, raw in zip(faces, rows[0]+rows[1]):
            domains.append({**raw, 'bearing': f['bearing'], 'label': f['patch'],
                            'origin': f['center'], 'normal_sign': -1 if f['body'] == 'panel' else 1})
        self.assertEqual(bind_retained_domains(faces, *rows, domains)['bound_faces'], 32)
        swapped = copy.deepcopy(domains)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        with self.assertRaisesRegex(ValueError, 'projection row'):
            bind_retained_domains(faces, *rows, swapped)
        changed = copy.deepcopy(domains)
        changed[0]['dofs'] = [999]
        with self.assertRaisesRegex(ValueError, 'projection row'):
            bind_retained_domains(faces, *rows, changed)

    def test_real_witness_position_and_frozen_negative_indices_are_enforced(self):
        faces = projection_bearings(*fixture())
        audit = {'minimum': [-2e-7-i*1e-9 for i in range(32)],
                 'minimum_at': [f['centroid'] for f in faces],
                 'negative_cells': list(range(32)), 'unresolved_cells': []}
        witnesses = gap_witnesses(faces, audit, 1e-7)
        old = legacy_perimeter_seeds(faces)
        new = distributed_seeds(faces, old, 8, witnesses=witnesses)
        self.assertEqual([p['face'] for p in new[len(old):]], list(range(3, 32, 4)))
        wrong = copy.deepcopy(audit)
        wrong['minimum_at'][0] = [99, 99]
        with self.assertRaisesRegex(ValueError, 'outside'):
            gap_witnesses(faces, wrong, 1e-7)
        with self.assertRaisesRegex(ValueError, 'frozen target'):
            gap_witnesses(faces, audit, 1e-6)

    def test_retained_manifest_rejects_same_name_modified_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'bearing-gaps-016.json'
            path.write_text(json.dumps({'minimum': [0.]}))
            manifest = {'files': [{'path': '/original/'+path.name, 'bytes': path.stat().st_size,
                                    'sha256': sha256(path)}]}
            verify_manifest_file(path, manifest)
            path.write_text(json.dumps({'minimum': [1.]}))
            with self.assertRaisesRegex(ValueError, 'manifest'):
                verify_manifest_file(path, manifest)


if __name__ == '__main__':
    unittest.main()
