"""Bounded, read-only FE feasibility probe on exact recovered original meshes.

No complete stiffness matrix, inverse, contact solve, or restart cache is built.
All output is outside the repository; only existing locked NumPy/SciPy is used.
"""
from pathlib import Path
import gc
import hashlib
import importlib.util
import json
import resource
import sys
import time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree

BASE = Path(__file__).resolve().parent
ROOT = Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'integration'))
from tetra_bubble_refinement import p2_nodes, p2_stiffness, star_condense

path = ROOT/'engineering/volume-convergence-20261017/frozen_load_response.py'
spec = importlib.util.spec_from_file_location('frozen_load_response_bounded', path)
energy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(energy)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

results = []
started = time.monotonic()
for body in ('panel', 'frame'):
    begin = time.monotonic()
    folder = BASE/'frozen-original'/body
    mesh = np.load(folder/'mesh.npz', allow_pickle=False)
    loads = np.load(folder/'loads.npz', allow_pickle=False)
    points, tetra, xyz = mesh['points'], mesh['tetra'], loads['xyz']
    ndof = xyz.shape[1]
    assert ndof % 3 == 0 and np.array_equal(xyz[:, 0::3], xyz[:, 1::3]) and np.array_equal(xyz[:, 1::3], xyz[:, 2::3])
    for component in range(3):
        assert np.array_equal(loads['axis'+str(component)], np.arange(component, ndof, 3))
    scalar = xyz[:, 0::3].T.copy()
    assert len(np.unique(scalar, axis=0)) == len(scalar), 'ambiguous duplicate original scalar DOF coordinates'
    tree = cKDTree(scalar)
    vertex_coords = points[tetra]
    ids = np.empty((len(tetra), 10), dtype=np.int32)
    maximum = 0.0
    bitwise = True
    for lo in range(0, len(tetra), 2048):
        hi = min(lo+2048, len(tetra))
        wanted = p2_nodes(vertex_coords[lo:hi])
        distance, found = tree.query(wanted.reshape(-1, 3), k=1)
        maximum = max(maximum, float(distance.max()))
        bitwise = bitwise and np.array_equal(scalar[found], wanted.reshape(-1, 3))
        assert distance.max() < 1e-11
        ids[lo:hi] = found.reshape(-1, 10)
    assert len(np.unique(ids)) == len(scalar), 'original retained DOF not mapped'
    mapping_seconds = time.monotonic()-begin
    # Count exact structural nonzero positions without constructing elastic K.
    row = np.repeat(ids, 10, axis=1).ravel()
    col = np.tile(ids, (1, 10)).ravel()
    structure = coo_matrix((np.ones(len(row), dtype=bool), (row, col)), shape=(len(scalar), len(scalar))).tocsr()
    scalar_nnz = int(structure.nnz)
    vector_structural_nnz = 9*scalar_nnz
    csc_bytes = vector_structural_nnz*(8+4)+4*(ndof+1)
    del structure, row, col, tree
    gc.collect()
    chosen = np.unique(np.linspace(0, len(tetra)-1, 64, dtype=int))
    v = vertex_coords[chosen]
    rng = np.random.default_rng(20261023)
    random_boundary = rng.normal(size=(5, len(v), 30))
    level_reports, previous = [], None
    for level in (0, 1, 2):
        tic = time.monotonic()
        stiffness = p2_stiffness(v) if level == 0 else star_condense(v, level=level).stiffness
        assembly_seconds = time.monotonic()-tic
        directional = np.einsum('pti,tij,ptj->pt', random_boundary, stiffness, random_boundary)
        assert np.all(directional > 0)
        symmetry = float(np.max(abs(stiffness-stiffness.transpose(0, 2, 1))))
        direct_error, internal_residual = 0.0, 0.0
        for u, expected in zip(random_boundary, directional):
            if level == 0:
                integrated = energy.strain_energy(v, u)
            else:
                _, residual, integrated = energy.recovered(v, u, level)
                internal_residual = max(internal_residual, residual)
            direct_error = max(direct_error, float(np.max(abs(integrated-expected)/np.maximum(abs(expected), 1e-30))))
        assert direct_error < 1e-9
        nested_increase = None if previous is None else float(np.max((directional-previous)/np.maximum(abs(previous), 1e-30)))
        assert nested_increase is None or nested_increase < 1e-9
        previous = directional
        level_reports.append({'level':level, 'sample_elements':len(v), 'five_directional_energy_probes':True,
                              'assembly_seconds':assembly_seconds, 'linear_full_element_count_extrapolation_seconds':assembly_seconds*len(tetra)/len(v),
                              'symmetry_absolute_max':symmetry, 'direct_strain_energy_relative_error_max':direct_error,
                              'internal_equilibrium_residual_absolute_max':internal_residual,
                              'relative_energy_increase_from_previous_level_max':nested_increase})
    result = {'body':body, 'original_tetrahedra':len(tetra), 'original_vector_dofs':ndof,
              'original_scalar_dofs':len(scalar), 'all_original_dofs_mapped':True,
              'coordinate_mapping_max_error_mm':maximum, 'bitwise_exact_coordinate_mapping':bitwise,
              'mapping_seconds':mapping_seconds, 'vector_structural_nnz':vector_structural_nnz,
              'estimated_uncompressed_float64_int32_CSC_K_bytes':csc_bytes,
              'original_assembler_COO_triplets_bytes_before_CSC':len(tetra)*30*30*24,
              'levels':level_reports, 'elapsed_seconds':time.monotonic()-begin,
              'mesh_sha256':digest(folder/'mesh.npz'), 'loads_sha256':digest(folder/'loads.npz')}
    results.append(result)
    print(json.dumps({'body':body, 'mapping_exact':bitwise, 'K_estimated_bytes':csc_bytes, 'seconds':result['elapsed_seconds']}), flush=True)
    del mesh, loads, xyz, scalar, ids, vertex_coords
    gc.collect()

report = {'schema':'razr-original-mesh-bounded-fe-feasibility-v1', 'bodies':results,
          'elapsed_seconds':time.monotonic()-started, 'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'runtime':{'python':sys.version, 'numpy':np.__version__, 'scipy':__import__('scipy').__version__},
          'source_sha256':{str(p):digest(p) for p in [Path(__file__), ROOT/'integration/tetra_bubble_refinement.py', path]},
          'research_material':{'E_normalization':1.0, 'nu':0.3},
          'full_FE_assembled':False, 'full_inverse_operator_probes_executed':False, 'new_QP_executed':False,
          'checkpoint_created':False, 'source_or_repo_files_written':False, 'hardware_or_EP5_structural_qualification':False,
          'extrapolation_limits':'Element assembly only. Excludes sparse matrix conversion, full factorization, trace extension, contact responses, QP, exchange and independent full-field audit.'}
(BASE/'real-mesh-bounded-probe.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
print(json.dumps({'report':str(BASE/'real-mesh-bounded-probe.json'), 'elapsed_seconds':report['elapsed_seconds'], 'peak_rss_kib':report['peak_rss_kib']}), flush=True)
