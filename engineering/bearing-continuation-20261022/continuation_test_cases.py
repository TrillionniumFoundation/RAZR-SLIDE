"""Small numerical/checkpoint tests. None is a physical or whole PR35 solve."""
from pathlib import Path
import ast
import copy
import hashlib
import io
import importlib.util
import contextlib
import sys
from types import SimpleNamespace
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.sparse import csc_matrix, coo_matrix, hstack
from contact_exchange import ExactResponseCache
from contact_dual_active import solve_force_qp
from contact_patch_audit import triangle_coefficients, evaluate
from surface_load_functional import shape_values
from bearing_checkpoint import (FILES, digest, file_digest, json_bytes,
                                save_checkpoint, load_checkpoint, validate_payload)
from continuation_support import validate_restored_columns, verify_reference_sources, restore_verified


class BearingContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.n = 10
        self.inverse = np.diag(np.linspace(.75, 1.5, self.n))
        self.identity = {'scope': 'synthetic unit problem, not PR35 FE',
                         'K_inverse_sha256': hashlib.sha256(self.inverse.tobytes()).hexdigest()}
        self.sources = {'source_kind': 'synthetic_test_fixture', 'physical_execution': False}
        self.parameters = {'max_exchanges': 4, 'maximum_columns': 20, 'gap_target_mm': 1e-7}
        self.points = [{'kind': 'bolt', 'index': i} for i in range(4)] + [self.point(0)]
        self.cache = self.new_cache()
        self.cache.append(hstack([self.one_map(p) for p in self.points], format='csc'))
        self.state = {'phase': 'ready_for_qp', 'next_iteration': 0, 'history': [], 'guess': None}

    def tearDown(self):
        self.tmp.cleanup()

    def point(self, cell):
        return {'kind': 'contact', 'cell': cell, 'patch': 'synthetic', 'xy': [float(cell), 0.], 'gap': 0.}

    def one_map(self, point):
        v = np.zeros(self.n)
        if point['kind'] != 'bolt':
            v[point['cell']] = 1.
        return csc_matrix(v[:, None])

    def new_cache(self):
        return ExactResponseCache(self.n, lambda v: self.inverse @ v, self.identity,
                                  response_block=lambda v: self.inverse @ v, response_batch_size=8)

    def save(self, cache=None, points=None, state=None, path=None):
        return save_checkpoint(path or self.root/'checkpoints',
            (cache or self.cache).C, (cache or self.cache).H,
            self.points if points is None else points, self.state if state is None else state,
            identity=self.identity, sources=self.sources, parameters=self.parameters)

    def load(self, receipt, **changes):
        args = dict(expected_manifest_sha256=receipt['manifest_sha256'], expected_identity=self.identity,
                    expected_sources=self.sources, expected_parameters=self.parameters, expected_n_dofs=self.n)
        args.update(changes)
        return load_checkpoint(receipt['path'], **args)

    def rebind_fixture(self, receipt, filename, payload):
        """Simulate a newly trusted but inconsistent bundle to test numerical guards."""
        folder = Path(receipt['path']); (folder/filename).write_bytes(payload)
        manifest = json.loads((folder/'manifest.json').read_text())
        manifest['files'][filename] = {'bytes': len(payload), 'sha256': digest(payload)}
        data = json_bytes(manifest); (folder/'manifest.json').write_bytes(data)
        return {**receipt, 'manifest_sha256': digest(data)}

    def cycle(self, cache, points, history, guess, first, stop=None):
        for iteration in range(first, 3):
            n = len(points); S = cache.H.copy(); S[np.arange(4), np.arange(4)] += 5.
            d = np.r_[np.zeros(4), -np.arange(1, n-3)*.25]
            eq = np.zeros((n, 4)); eq[:4] = np.eye(4); rhs = np.array([.2, .3, .4, .5])
            initial = None if guess is None else np.pad(guess, (0, n-len(guess)))
            q = solve_force_qp(S, d, eq, rhs, initial=initial, tolerance=2e-10, factor_reuse=True)
            self.assertTrue(q['passed'], q)
            forces = np.array(q['forces']); field, applied = cache.reconstruct(np.zeros(self.n), forces)
            history.append({'exchange': iteration, 'body_contacts': n-4, 'bearing_contacts': 0,
                            'body_negative': 1, 'bearing_negative': 0, 'unresolved': 0,
                            'body_bound': -1e-5, 'bearing_bound': 0., 'seconds': 0.})
            if iteration == 2:
                return forces, field, applied, cache.H, points, history
            new = self.point(iteration + 1)
            cache.append(self.one_map(new)); points.append(new); guess = forces.copy()
            if stop == iteration:
                state = {'phase': 'ready_for_qp', 'next_iteration': iteration+1,
                         'history': history, 'guess': guess.tolist()}
                return self.save(cache, points, state)

    def test_real_small_QP_continuous_equals_interrupted_restored_run(self):
        uninterrupted = self.cycle(self.cache, copy.deepcopy(self.points), [], None, 0)
        fresh = self.new_cache(); fresh.append(hstack([self.one_map(p) for p in self.points], format='csc'))
        receipt = self.cycle(fresh, copy.deepcopy(self.points), [], None, 0, stop=0)
        saved = self.load(receipt)
        cells = [{'label': 'synthetic', 'gap': 0.,
                  'vertices': [[-1., -1.], [3., -1.], [0., 3.]]} for _ in range(3)]
        validate_restored_columns(saved, self.points, self.one_map, self.n, [], cells)
        restored = self.new_cache(); check = restored.restore(saved.C, saved.H, saved.identity, probes=5)
        self.assertEqual(check.probes, 5)
        self.assertEqual(check.response_calls, 5)
        resumed = self.cycle(restored, saved.points, saved.state['history'],
                             np.array(saved.state['guess']), saved.state['next_iteration'])
        for a, b in zip(uninterrupted[:4], resumed[:4]):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(uninterrupted[4:], resumed[4:])

    def test_adapter_fresh_and_resumed_zero_load_synthetic_domain(self):
        """Exercise unchanged driver dispatch end-to-end, not a production FE solve."""
        package = Path(__file__).resolve().parent
        repository = Path(sys.modules['contact_exchange'].__file__).resolve().parents[1]
        module_names = ['bearing_contact', '_bearing_adapter_test']
        prior = {name: sys.modules.get(name) for name in module_names}
        try:
            for name, relative in [('bearing_contact', 'reference/bearing_contact.py'),
                                   ('_bearing_adapter_test', 'continued_rigid_bearing_probe.py')]:
                spec = importlib.util.spec_from_file_location(name, package/relative)
                module = importlib.util.module_from_spec(spec); sys.modules[name] = module
                spec.loader.exec_module(module)
            adapter = sys.modules['_bearing_adapter_test']
            surface = self.root/'synthetic-surface'; surface.mkdir()
            triangle = [[-1., -1.], [1., -1.], [0., 1.]]
            for body in ['panel', 'frame']:
                faces = [{'kind': 'C', 'axis': 2, 'direction': [0, 0, -1 if body == 'panel' else 1],
                          'density_target': [0., 0.], 'index': i, 'vertices': [3*i+j for j in range(3)],
                          'dofs': [6*i+j for j in range(6)], 'triangle_xy': triangle, 'polygon': triangle}
                         for i in range(4)]
                (surface/(body+'-faces.json')).write_bytes(json_bytes(faces))
            def context(name):
                output = self.root/name; output.mkdir()
                body = {'N': 24, 'nb': 3, 'lookup': {}, 'K': np.eye(24), 'A': np.zeros((24, 3)),
                        'B': np.eye(3), 'free': np.arange(1, 24), 'D': np.array([0])}
                response = lambda v: np.asarray(v).copy()
                cache = ExactResponseCache(54, response, {'scope': 'synthetic adapter test only'}, response_block=response)
                cache.append(csc_matrix((54, 4), dtype=np.float64))
                audit = lambda u: {'minimum': np.zeros(1), 'minimum_at': np.zeros((1, 2)),
                    'covered_lower_bounds': np.zeros(1), 'negative_cells': np.array([], dtype=int), 'unresolved_cells': []}
                return {'ROOT': repository, 'a': SimpleNamespace(max_exchanges=3, max_points=6500,
                    rank_fallback='svd', faces_per_patch=2, load_face_cap=0), 'out': output,
                    'dump': lambda path, value: Path(path).write_bytes(json_bytes(value)),
                    'target': 1e-7, 'force_mode': True, 'external_scale': 0., 'load_mode': 'consistent',
                    'P': body, 'F': body, 'nP': 27, 'n': 54, 'npanel': 24, 'nframe': 24,
                    'R': np.zeros((54, 0)), 'loadG': np.zeros(0),
                    'points': [{'kind': 'bolt', 'index': i} for i in range(4)], 'hashes': {},
                    'surface': SimpleNamespace(root=surface), 'cache': cache, 'response': response,
                    'one_map': lambda point: csc_matrix((54, 1)),
                    'cells': [{'label': 'synthetic', 'gap': 0., 'vertices': triangle}], 'audit': audit,
                    'external': np.zeros(54), 'Uext': np.zeros(54), 'selection': [], 'case': 6,
                    'control': {'targets': np.zeros(4), 'compliance': np.full(4, 5.)}}
            fresh = context('fresh-synthetic'); resumed = context('resumed-synthetic')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(adapter.run(fresh, checkpoint_root=self.root/'adapter-checkpoints'))
                receipt = json.loads((fresh['out']/'continuation-latest.json').read_text())
                self.assertTrue(adapter.run(resumed, checkpoint_root=self.root/'adapter-checkpoints',
                    resume_checkpoint=receipt['path'], expected_manifest_sha256=receipt['manifest_sha256']))
            init = json.loads((resumed['out']/'bearing-initialization.json').read_text())
            self.assertEqual(init['next_iteration'], 0)
            self.assertEqual(init['exact_body_response_check']['probes'], 5)
            with np.load(fresh['out']/'bearing-full-fields.npz', allow_pickle=False) as a, np.load(resumed['out']/'bearing-full-fields.npz', allow_pickle=False) as b:
                for name in a.files:
                    np.testing.assert_array_equal(a[name], b[name])
            report = json.loads((resumed['out']/'bearing-report.json').read_text())
            for key in ['hardware_or_actual_preload_qualified', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go']:
                self.assertFalse(report[key])
        finally:
            for name, module in prior.items():
                if module is None: sys.modules.pop(name, None)
                else: sys.modules[name] = module

    def test_appended_state_without_a_new_column_is_rejected(self):
        cache = self.new_cache(); cache.append(hstack([self.one_map(p) for p in self.points], format='csc'))
        receipt = self.cycle(cache, copy.deepcopy(self.points), [], None, 0, stop=0)
        saved = self.load(receipt)
        saved.state['history'][0]['body_contacts'] += 1
        saved.state['guess'].append(0.)
        cells = [{'label': 'synthetic', 'gap': 0.,
                  'vertices': [[-1., -1.], [3., -1.], [0., 3.]]} for _ in range(3)]
        with self.assertRaisesRegex(ValueError, 'append-only'):
            validate_restored_columns(saved, self.points, self.one_map, self.n, [], cells)

    def actual_descriptor_fixture(self, kind, xy, polygon=None):
        """Use both original one_map bodies, without executing FE preparation."""
        package = Path(__file__).resolve().parent
        triangle = [[0., 0.], [1., 0.], [0., 1.]]
        polygon = triangle if polygon is None else polygon
        center = np.mean(polygon, axis=0).tolist()
        n, nP = 12, 6
        body = {'N': 6, 'C': np.zeros((6, 4)), 'Cb': np.zeros((0, 4))}
        cell = {'label': 'synthetic', 'gap': 0., 'vertices': polygon,
                'origin': np.zeros(2), 'normal': 1., 'axis': 2,
                'dp': np.arange(6), 'df': np.arange(6),
                'panel_q': triangle_coefficients(triangle, np.eye(6)),
                'frame_q': triangle_coefficients(triangle, np.eye(6)),
                'panel_face': None, 'frame_face': None}
        cells = [cell]
        faces = [{'body': body_name, 'index': i, 'label': 'bearing_'+body_name+'_'+str(i),
                  'triangle_xy': triangle, 'polygon': polygon, 'offset': offset,
                  'dofs': list(range(6)), 'normal_sign': sign, 'trace_index': None}
                 for body_name, offset, sign in [('panel', 0, -1), ('frame', nP, 1)]
                 for i in range(4)]
        def extract(relative, nested, top, environment):
            path = package/relative
            tree = ast.parse(path.read_text(), filename=str(path))
            run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
            nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in top]
            nodes += [node for node in run.body if isinstance(node, ast.FunctionDef) and node.name in nested]
            self.assertEqual(len(nodes), len(nested)+len(top))
            exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), environment)
            return environment['one_map']
        body_map = extract('reference/solve_trace_probe.py', {'one_map', 'bubble'}, {'col'},
            {'np': np, 'csc_matrix': csc_matrix, 'coo_matrix': coo_matrix,
             'evaluate': evaluate, 'P': body, 'F': body, 'n': n, 'nP': nP, 'cells': cells})
        one_map = extract('continued_rigid_bearing_probe.py', {'one_map'}, set(),
            {'np': np, 'csc_matrix': csc_matrix, 'shape_values': shape_values,
             'n': n, 'faces': faces, 'bodies': {'panel': body, 'frame': body},
             'ctx': {'one_map': body_map}})
        original = [{'kind': 'bolt', 'index': i} for i in range(4)]
        points = copy.deepcopy(original)
        points += [{'kind': 'bearing', 'body': face['body'], 'index': face['index'],
                    'face': i, 'patch': face['label'], 'xy': center[:], 'gap': 0.}
                   for i, face in enumerate(faces)]
        points += [{'kind': 'contact', 'cell': 0, 'patch': cell['label'], 'xy': center[:], 'gap': 0.}]
        selected = 4 if kind == 'bearing' else len(points)-1
        points[selected]['xy'] = list(xy)
        C = hstack([one_map(point) for point in points], format='csc')
        saved = SimpleNamespace(points=points, C=C, H=(C.T@C).toarray(), state=copy.deepcopy(self.state))
        # The original defect passed the byte/payload and exact-C checks.
        validate_payload(saved.C, saved.H, saved.points, saved.state, n_dofs=n, parameters=self.parameters)
        return saved, original, one_map, n, faces, cells

    def test_bearing_point_outside_domain_rejected_with_matching_actual_C(self):
        fixture = self.actual_descriptor_fixture('bearing', [2., 2.])
        with self.assertRaisesRegex(ValueError, 'outside frozen bearing polygon'):
            validate_restored_columns(*fixture)

    def test_contact_point_outside_domain_rejected_with_matching_actual_C(self):
        fixture = self.actual_descriptor_fixture('contact', [2., 2.])
        with self.assertRaisesRegex(ValueError, 'outside frozen contact polygon'):
            validate_restored_columns(*fixture)

    def test_bearing_point_in_basis_triangle_but_outside_clipped_face_rejected(self):
        fixture = self.actual_descriptor_fixture('bearing', [.45, .45], [[0., 0.], [.5, 0.], [0., .5]])
        with self.assertRaisesRegex(ValueError, 'outside frozen bearing polygon'):
            validate_restored_columns(*fixture)

    def test_contact_point_in_basis_triangle_but_outside_clipped_cell_rejected(self):
        fixture = self.actual_descriptor_fixture('contact', [.45, .45], [[0., 0.], [.5, 0.], [0., .5]])
        with self.assertRaisesRegex(ValueError, 'outside frozen contact polygon'):
            validate_restored_columns(*fixture)

    def test_bearing_polygon_vertices_edges_and_interior_accepted(self):
        polygon = [[0., 0.], [.5, 0.], [0., .5]]
        for xy in polygon + [[.25, 0.], [.25, .25], [0., .25], [.1, .1]]:
            with self.subTest(xy=xy):
                validate_restored_columns(*self.actual_descriptor_fixture('bearing', xy, polygon))

    def test_contact_polygon_vertices_edges_and_interior_accepted(self):
        polygon = [[0., 0.], [.5, 0.], [0., .5]]
        for xy in polygon + [[.25, 0.], [.25, .25], [0., .25], [.1, .1]]:
            with self.subTest(xy=xy):
                validate_restored_columns(*self.actual_descriptor_fixture('contact', xy, polygon))

    def test_nonfinite_bearing_coordinates_rejected_before_reconstruction(self):
        for invalid in [np.nan, np.inf, -np.inf]:
            fixture = self.actual_descriptor_fixture('bearing', [.2, .2])
            fixture[0].points[4]['xy'][0] = invalid
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'invalid descriptor coordinates'):
                validate_restored_columns(*fixture)

    def test_nonfinite_contact_coordinates_rejected_before_reconstruction(self):
        for invalid in [np.nan, np.inf, -np.inf]:
            fixture = self.actual_descriptor_fixture('contact', [.2, .2])
            fixture[0].points[-1]['xy'][0] = invalid
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'invalid descriptor coordinates'):
                validate_restored_columns(*fixture)

    def test_nonfinite_or_overflowing_frozen_polygon_rejected(self):
        for kind in ['bearing', 'contact']:
            for polygon in [[[0., 0.], [np.inf, 0.], [0., 1.]],
                            [[0., 0.], [np.nan, 0.], [0., 1.]],
                            [[-1e308, -1e308], [1e308, -1e308], [0., 1e308]]]:
                fixture = self.actual_descriptor_fixture(kind, [.2, .2])
                if kind == 'bearing': fixture[4][0]['polygon'] = polygon
                else: fixture[5][0]['vertices'] = polygon
                with self.subTest(kind=kind, polygon=polygon), self.assertRaisesRegex(ValueError, 'finite'):
                    validate_restored_columns(*fixture)

    def test_domain_boundary_preserves_original_roundoff_and_orientation(self):
        for kind in ['bearing', 'contact']:
            for polygon in [[[0., 0.], [1., 0.], [0., 1.]], [[0., 1.], [1., 0.], [0., 0.]]]:
                with self.subTest(kind=kind, polygon=polygon):
                    # Original stationary-point feasibility allows this roundoff only.
                    validate_restored_columns(*self.actual_descriptor_fixture(kind, [-.5e-12, .25], polygon))
                    fixture = self.actual_descriptor_fixture(kind, [-2e-12, .25], polygon)
                    with self.assertRaisesRegex(ValueError, 'outside frozen'):
                        validate_restored_columns(*fixture)

    def test_generation_contains_complete_bound_state(self):
        receipt = self.save(); loaded = self.load(receipt)
        self.assertEqual(set(loaded.manifest['files']), FILES)
        np.testing.assert_array_equal(loaded.C.toarray(), self.cache.C.toarray())
        np.testing.assert_array_equal(loaded.H, self.cache.H)
        self.assertFalse(loaded.manifest['physical_qualification'])
        self.assertFalse(loaded.manifest['whole_surface_contact_pass'])

    def test_atomic_pointer_survives_interruption_before_publish(self):
        receipt = self.save(); latest = self.root/'checkpoints/LATEST.json'; old = latest.read_bytes()
        with patch('bearing_checkpoint.os.replace', side_effect=OSError('synthetic power loss before publish')):
            with self.assertRaises(OSError): self.save()
        self.assertEqual(latest.read_bytes(), old)
        self.load(receipt)
        self.assertEqual(list((self.root/'checkpoints').glob('.incomplete-*')), [])

    def test_failed_serialization_does_not_create_checkpoint_root(self):
        H = self.cache.H.copy(); H[0, 0] = np.inf
        target = self.root/'never-published'
        with self.assertRaises(ValueError):
            save_checkpoint(target, self.cache.C, H, self.points, self.state,
                            identity=self.identity, sources=self.sources, parameters=self.parameters)
        self.assertFalse(target.exists())

    def test_each_truncated_payload_is_rejected(self):
        for name in FILES:
            with self.subTest(name=name):
                receipt = self.save(); path = Path(receipt['path'])/name
                path.write_bytes(path.read_bytes()[:-1])
                with self.assertRaises(ValueError): self.load(receipt)

    def test_missing_payload_rejected(self):
        receipt = self.save(); (Path(receipt['path'])/'points.json').unlink()
        with self.assertRaises(ValueError): self.load(receipt)

    def test_field_016_is_not_a_checkpoint(self):
        path = self.root/'bearing-field-016.npz'; np.savez(path, u=np.zeros(10), forces=np.zeros(5))
        with self.assertRaises(ValueError):
            self.load({'path': str(path), 'manifest_sha256': file_digest(path)})

    def test_source_and_parameter_and_operator_identity_mismatch_rejected(self):
        receipt = self.save()
        changes = [dict(expected_sources={'different_source': True}),
                   dict(expected_parameters={**self.parameters, 'gap_target_mm': 1e-6}),
                   dict(expected_parameters={**self.parameters, 'max_exchanges': 8}),
                   dict(expected_identity={'different_K': True}), dict(expected_n_dofs=self.n+1)]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError): self.load(receipt, **change)

    def test_manifest_edit_rejected_by_caller_held_digest(self):
        receipt = self.save(); path = Path(receipt['path'])/'manifest.json'
        data = json.loads(path.read_text()); data['parameters']['gap_target_mm'] = 1e-6
        path.write_bytes(json_bytes(data))
        with self.assertRaises(ValueError): self.load(receipt)

    def test_nonphysical_checkpoint_cannot_be_relabelled_pass(self):
        receipt = self.save(); path = Path(receipt['path'])/'manifest.json'
        data = json.loads(path.read_text()); data['whole_surface_contact_pass'] = True
        raw = json_bytes(data); path.write_bytes(raw); receipt['manifest_sha256'] = digest(raw)
        with self.assertRaises(ValueError): self.load(receipt)

    def test_changed_H_rehashed_bundle_still_fails_full_operator_probes(self):
        receipt = self.save(); H = self.cache.H.copy(); H[4, 4] *= 1.1
        stream = io.BytesIO(); np.savez_compressed(stream, H=H)
        saved = self.load(self.rebind_fixture(receipt, 'H.npz', stream.getvalue()))
        with self.assertRaises(ValueError): self.new_cache().restore(saved.C, saved.H, saved.identity, probes=5)

    def test_finite_cache_with_overflowing_probe_is_rejected(self):
        H = np.full(self.cache.H.shape, 1e308)
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            restore_verified(self.new_cache(), self.cache.C, H, self.identity)

    def test_changed_C_rehashed_bundle_still_fails_descriptor_maps(self):
        receipt = self.save(); C = self.cache.C.copy(); C.data *= 2.
        stream = io.BytesIO(); np.savez_compressed(stream, data=C.data, indices=C.indices, indptr=C.indptr, shape=np.array(C.shape))
        saved = self.load(self.rebind_fixture(receipt, 'C.npz', stream.getvalue()))
        with self.assertRaises(ValueError):
            validate_restored_columns(saved, self.points, self.one_map, self.n, [], [])

    def test_original_point_order_change_rejected(self):
        receipt = self.save(); points = copy.deepcopy(self.points); points[0], points[1] = points[1], points[0]
        saved = self.load(self.rebind_fixture(receipt, 'points.json', json_bytes(points)))
        with self.assertRaises(ValueError):
            validate_restored_columns(saved, self.points, self.one_map, self.n, [], [])

    def test_unknown_or_incomplete_iteration_state_rejected(self):
        for change in [{'phase': 'field_only'}, {'next_iteration': True}, {'next_iteration': 1},
                       {'guess': [0.]*5}, {'next_iteration': 4}]:
            with self.subTest(change=change):
                with self.assertRaises(ValueError): self.save(state={**self.state, **change})

    def test_shapes_and_nonfinite_arrays_rejected_before_publish(self):
        cases = [(self.cache.C, self.cache.H[:-1]),
                 (self.cache.C[:, :-1].tocsc(), self.cache.H),
                 (self.cache.C, self.cache.H.astype(np.float32))]
        for C, H in cases:
            with self.subTest(shape=(C.shape, H.shape)):
                with self.assertRaises(ValueError):
                    save_checkpoint(self.root/'bad', C, H, self.points, self.state,
                                    identity=self.identity, sources=self.sources, parameters=self.parameters)

    def test_symlinked_member_rejected_even_with_matching_bytes(self):
        receipt = self.save(); path = Path(receipt['path'])/'points.json'
        other = self.root/'other-points.json'; other.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(other)
        with self.assertRaises(ValueError): self.load(receipt)

    def test_original_PR35_snapshots_still_match_pinned_content(self):
        self.assertEqual(len(verify_reference_sources()), 3)

    def test_sparse_index_corruption_rejected(self):
        receipt = self.save(); C = self.cache.C
        stream = io.BytesIO(); np.savez_compressed(stream, data=C.data, indices=C.indices,
            indptr=np.full_like(C.indptr, 100), shape=np.array(C.shape))
        with self.assertRaises(ValueError): self.load(self.rebind_fixture(receipt, 'C.npz', stream.getvalue()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
