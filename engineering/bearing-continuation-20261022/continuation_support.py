"""Identity and descriptor checks around, not inside, the PR35 numerical model."""
from pathlib import Path
import json
import platform
import sys
import numpy as np
import scipy
from scipy.sparse import hstack
from bearing_checkpoint import file_digest, json_bytes

HERE = Path(__file__).resolve().parent
HEAD = '176df31ceb35bb3737d68030e60ba377665de210'
ORIGINAL = {
    'rigid_bearing_probe.py': '58db7b129df250b4e4a113c7c6d69ae46669766d2eecc8f490045536f095687b',
    'solve_trace_probe.py': 'a5eb8c93eb0fb37cdcb3658ed01b09119dd930729d75e365843887745f9ffb7b',
    'bearing_contact.py': '930a66e177b0c1c778a41c2d6aefd72873316c37059e0e1217e9cf8592f35710',
}
DEPENDENCIES = (
    'integration/contact_exchange.py', 'integration/contact_dual_active.py',
    'integration/contact_patch_audit.py', 'integration/cubic_trace_gap.py',
    'integration/surface_load_functional.py', 'integration/installation_control.py',
    'integration/face_trace_space.py', 'integration/tetra_bubble_refinement.py',
    'integration/rank_fallback.py', 'engineering/consistent-load-20261017/surface_archive.py',
)


def verify_reference_sources():
    result = {}
    for name, expected in ORIGINAL.items():
        path = HERE / 'reference' / name
        if path.is_symlink() or file_digest(path) != expected:
            raise ValueError('pinned PR35 source changed: ' + name)
        result[str(path)] = expected
    return result


def source_binding(ctx):
    files = verify_reference_sources()
    for name in ['continued_rigid_bearing_probe.py', 'bearing_checkpoint.py',
                 'continuation_support.py', 'run_continuation.py', 'source-lock.json']:
        path = HERE / name
        files[str(path)] = file_digest(path)
    for name in DEPENDENCIES:
        path = Path(ctx['ROOT']) / name
        files[str(path)] = file_digest(path)
    # Check the imported numerical modules actually came from these files.
    for name in ['contact_exchange', 'contact_dual_active', 'contact_patch_audit',
                 'cubic_trace_gap', 'surface_load_functional', 'installation_control']:
        module = sys.modules.get(name)
        expected = (Path(ctx['ROOT'])/'integration'/f'{name}.py').resolve()
        if module is None or Path(module.__file__).resolve() != expected:
            raise ValueError('numerical import came from a different source: ' + name)
    for relative in DEPENDENCIES:
        name = Path(relative).stem
        module = sys.modules.get(name)
        if module is not None and Path(module.__file__).resolve() != (Path(ctx['ROOT'])/relative).resolve():
            raise ValueError('dependency import came from a different source: ' + name)
    bearing = sys.modules.get('bearing_contact')
    if bearing is None or file_digest(bearing.__file__) != ORIGINAL['bearing_contact.py']:
        raise ValueError('bearing map is not the pinned PR35 source')
    return {'pr35_head': HEAD, 'file_sha256': files,
            'runtime': {'python': platform.python_version(), 'numpy': np.__version__,
                        'scipy': scipy.__version__, 'byteorder': sys.byteorder,
                        'scikit_fem': getattr(sys.modules.get('skfem'), '__version__', None)}}


def parameters(ctx):
    a = ctx['a']
    return {'max_exchanges': a.max_exchanges, 'maximum_columns': a.max_points + 4,
            'rank_fallback': a.rank_fallback, 'gap_target_mm': ctx['target'],
            'case': ctx['case'], 'external_scale': ctx['external_scale'],
            'surface_load_mode': ctx['load_mode'], 'force_mode': ctx['force_mode'],
            'faces_per_patch': getattr(a, 'faces_per_patch', 2),
            'load_face_cap': getattr(a, 'load_face_cap', 0),
            'installation_control': ctx['control'],
            'selected_trace_faces': ctx['selection'],
            'rigid_modes': ctx['R'].shape[1],
            'QP_tolerance': 2e-10, 'response_restore_probes': 5,
            'model': 'eight free rigid planes, axial-only bolts; original fixed frame'}



def restore_verified(cache, C, H, identity):
    """Keep the original five probes/tolerance; reject undefined arithmetic."""
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            check = cache.restore(C, H, identity, probes=5)
    except (FloatingPointError, OverflowError) as error:
        raise ValueError('non-finite arithmetic while checking cached response') from error
    if not np.isfinite(cache.H).all() or not np.isfinite(check.largest_relative_error):
        raise ValueError('non-finite restored response or verification result')
    return check


def seen_from_points(points):
    seen = {}
    for p in points[4:]:
        seen.setdefault(p['patch'], []).append(p['xy'])
    return seen


def require_point_in_frozen_polygon(xy, polygon, kind):
    """Use the original quadratic audit's planar feasibility roundoff rule.

    This checks the clipped domain, not merely the underlying basis triangle.
    The 1e-12 * max(edge_scale**2, 1e-300) cross-product tolerance is the
    existing contact_exchange.QuadraticGapBatch / contact_patch_audit.extrema
    rule. It is unrelated to the gap acceptance target or point deduplication.
    """
    # Keep source-only preflight independent of the numerical module search path.
    from contact_patch_audit import convex_vertices
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            vertices = convex_vertices(polygon)
            edges = np.roll(vertices, -1, axis=0) - vertices
            difference = np.asarray(xy, dtype=float) - vertices
            cross = edges[:, 0]*difference[:, 1] - edges[:, 1]*difference[:, 0]
            tolerance = 1e-12 * max(np.max(abs(edges))**2, 1e-300)
    except (FloatingPointError, OverflowError) as error:
        raise ValueError('non-finite frozen polygon arithmetic') from error
    if not np.isfinite(cross).all() or not np.isfinite(tolerance):
        raise ValueError('non-finite frozen polygon feasibility')
    if np.any(cross < -tolerance):
        raise ValueError('descriptor coordinates outside frozen ' + kind + ' polygon')


def validate_restored_columns(saved, original_points, one_map, n_dofs, faces, cells):
    """Independently reconstruct every C column from the same frozen descriptors."""
    if json_bytes(saved.points[:len(original_points)]) != json_bytes(original_points):
        raise ValueError('original body-contact prefix/order changed')
    for p in saved.points[len(original_points):]:
        if p.get('kind') == 'bearing':
            index = p.get('face')
            if type(index) is not int or not 0 <= index < len(faces):
                raise ValueError('invalid bearing face identity')
            face = faces[index]
            polygon = face.get('polygon')
            if type(p.get('index')) is not int or any(p.get(k) != face[k] for k in ('body', 'index')) or p.get('patch') != face['label'] or p.get('gap') != 0.:
                raise ValueError('bearing descriptor differs from frozen domain')
        elif p.get('kind') == 'contact':
            index = p.get('cell')
            if type(index) is not int or not 0 <= index < len(cells):
                raise ValueError('invalid contact cell identity')
            cell = cells[index]
            polygon = cell.get('vertices')
            if p.get('patch') != cell['label'] or p.get('gap') != cell['gap']:
                raise ValueError('contact descriptor differs from frozen cell')
        else:
            raise ValueError('unexpected appended descriptor kind')
        gap = p.get('gap')
        if isinstance(gap, bool) or not isinstance(gap, (int, float)) or not np.isfinite(gap):
            raise ValueError('invalid descriptor gap')
        xy = p.get('xy')
        if not isinstance(xy, list) or len(xy) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in xy) or not np.isfinite(xy).all():
            raise ValueError('invalid descriptor coordinates')
        require_point_in_frozen_polygon(xy, polygon, p['kind'])
    if faces:
        present = {(p.get('body'), p.get('index')) for p in saved.points[4:] if p.get('kind') == 'bearing'}
        if present != {(body, i) for body in ('panel', 'frame') for i in range(4)}:
            raise ValueError('checkpoint omitted an original bearing domain')
    expected = hstack([one_map(p) for p in saved.points], format='csc')
    if expected.shape != (n_dofs, len(saved.points)) or (expected != saved.C).nnz:
        raise ValueError('C columns/order differ from current descriptor maps')
    history = saved.state['history']
    for i, row in enumerate(history):
        for key in ['body_contacts', 'bearing_contacts', 'body_negative', 'bearing_negative', 'unresolved']:
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError('invalid prior exchange count')
        if row['unresolved'] or not (row['body_negative'] or row['bearing_negative']):
            raise ValueError('checkpoint claims continuation after an original stopping condition')
        for key in ['body_bound', 'bearing_bound', 'seconds']:
            if isinstance(row.get(key), bool) or not isinstance(row.get(key), (int, float)) or not np.isfinite(row[key]):
                raise ValueError('invalid prior exchange bound/timing')
    if history:
        expected_guess = 4 + history[-1]['body_contacts'] + history[-1]['bearing_contacts']
        if len(saved.state['guess']) != expected_guess:
            raise ValueError('warm forces do not match the last evaluated columns')
        counts = [4 + row['body_contacts'] + row['bearing_contacts'] for row in history] + [len(saved.points)]
        if any(not 1 <= b-a <= 128 for a, b in zip(counts, counts[1:])):
            raise ValueError('continuation does not match the original append-only exchange boundary')
