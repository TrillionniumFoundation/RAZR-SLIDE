"""Fresh L2-only elastic assembly from exact original research mesh/load data.

This is a new, explicitly identified reconstruction, not restoration of an old K
or a contact/QP checkpoint. Uses only the existing locked NumPy/SciPy primitives.
"""
from pathlib import Path
import argparse
import errno
import shutil
import gc
import hashlib
import json
import os
import resource
import sys
import time
import traceback
import numpy as np
import scipy
from scipy.sparse import coo_matrix, save_npz
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT/'integration')]
from tools.check_environment import inspect_environment
from tetra_bubble_refinement import p2_nodes, star_condense

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def save_json(path, data):
    temporary = path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
    os.replace(temporary, path)

def free_bytes(path):
    s = os.statvfs(path)
    return s.f_bavail*s.f_frsize

def main(args):
    start = time.monotonic()
    out = args.output.resolve()
    if out == ROOT or ROOT in out.parents:
        raise ValueError('output must be outside repository')
    out.mkdir(parents=True, exist_ok=False)
    # Conservative virtual-memory ceiling also bounds resident allocations.
    environment = inspect_environment(ROOT)
    if not environment['passed']:
        raise RuntimeError('locked environment mismatch: ' + '; '.join(environment['errors']))
    memory_limit = int(args.memory_gib*1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    original = args.inputs.resolve()/args.body
    expected = {
        'panel/mesh.npz': '310152fc64af21451cc5ea4be683a73075109ed7e6ec588a6e8bcacf4979ac34',
        'panel/loads.npz': '811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6',
        'frame/mesh.npz': 'fc0eeecf966eda3bf242b0abd90f5603132f47d5235fcf81ea7238c1faf33132',
        'frame/loads.npz': 'eb2b180696785a77b71412506760df974fbf54c800090e36f027f2aaf70135a3',
    }
    input_hashes = {str(original/name):sha(original/name) for name in ('mesh.npz','loads.npz')}
    for name in ('mesh.npz','loads.npz'):
        assert input_hashes[str(original/name)] == expected[args.body+'/'+name]
    source_hashes = {str(p):sha(p) for p in (Path(__file__), ROOT/'integration/tetra_bubble_refinement.py', ROOT/'tools/check_environment.py', ROOT/'pyproject.toml', ROOT/'uv.lock')}
    state = {'schema':'razr-fresh-l2-assembly-progress-v1', 'body':args.body,
             'input_sha256':input_hashes, 'source_sha256':source_hashes,
             'original_artifact_restored':False, 'completed':False,
             'full_inverse_solved':False, 'contact_solved':False,
             'environment': environment, 'numerical_primitive_unchanged': True,
             'historical_producer': 'engineering/gate-closure-20261023/numerical-recovery/reproducibility/sources/new/rebuild_l2_only.py'}
    def progress(phase, **extra):
        state.update(phase=phase, elapsed_seconds=time.monotonic()-start,
                     peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                     disk_free_bytes=free_bytes(out), **extra)
        save_json(out/'progress.json', state)
        print(json.dumps(state), flush=True)
    try:
        mesh = np.load(original/'mesh.npz', allow_pickle=False)
        loads = np.load(original/'loads.npz', allow_pickle=False)
        points, tetra, xyz = mesh['points'], mesh['tetra'], loads['xyz']
        vertices = points[tetra]
        count, ndof = len(tetra), xyz.shape[1]
        expected_count = {'panel':(57620,344103),'frame':(79628,474726)}
        assert (count,ndof) == expected_count[args.body]
        assert np.array_equal(xyz[:,::3],xyz[:,1::3]) and np.array_equal(xyz[:,1::3],xyz[:,2::3])
        for c in range(3):
            assert np.array_equal(loads['axis'+str(c)],np.arange(c,ndof,3))
        scalar = xyz[:,::3].T.copy()
        assert len(np.unique(scalar,axis=0)) == len(scalar)
        tree = cKDTree(scalar)
        separation = float(tree.query(scalar,k=2)[0][:,1].min())
        assert separation > 1e-9
        ids = np.empty((count,30), dtype=np.int32)
        coordinate_error = 0.0
        for lo in range(0,count,2048):
            hi=min(lo+2048,count)
            distance,index=tree.query(p2_nodes(vertices[lo:hi]).reshape(-1,3))
            coordinate_error=max(coordinate_error,float(distance.max()))
            assert distance.max()<1e-11
            ids[lo:hi]=(3*index.reshape(-1,10,1)+np.arange(3)).reshape(-1,30)
        assert np.array_equal(np.unique(ids),np.arange(ndof))
        del tree,scalar
        gc.collect()
        expected_K_bytes={'panel':285134212,'frame':394529020}[args.body]
        partial_bytes=count*30*30*8+128 if args.element_storage == 'mmap' else 0
        reserve=500*1024**2
        if free_bytes(out) < partial_bytes+expected_K_bytes+reserve:
            raise RuntimeError('insufficient disk for partial elements, finalized K and 500MiB reserve')
        progress('mapping_verified',original_tetrahedra=count,original_vector_dofs=ndof,
                 coordinate_mapping_error_mm=coordinate_error,minimum_scalar_dof_separation_mm=separation,
                 original_mesh_and_load_bytes_exact=True,material_E=1.0,material_nu=0.3,volume_level=2)
        partial=out/'partial-elements.npy'
        values=(np.lib.format.open_memmap(partial,mode='w+',dtype=np.float64,shape=(count,30,30))
                if args.element_storage == 'mmap' else np.empty((count,30,30), dtype=np.float64))
        state['element_storage'] = args.element_storage
        probe=np.random.default_rng(20261023).normal(size=(ndof,5))
        element_energies=np.zeros(5)
        assembly_start=time.monotonic()
        for lo in range(0,count,256):
            hi=min(lo+256,count)
            block=star_condense(vertices[lo:hi],E=1.0,nu=0.3,level=2).stiffness
            assert np.isfinite(block).all()
            values[lo:hi]=block
            u=probe[ids[lo:hi]]
            element_energies+=np.einsum('tij,tip,tjp->p',block,u,u,optimize=True)
            if lo%4096==0 or hi==count:
                if args.element_storage == 'mmap':
                    values.flush()
                if free_bytes(out)<reserve:
                    raise RuntimeError('500MiB disk reserve reached')
                progress('partial_element_assembly',assembled_elements=hi,total_elements=count)
        assembly_seconds=time.monotonic()-assembly_start
        if args.element_storage == 'mmap':
            values.flush()
        progress('sparse_conversion_started',assembled_elements=count,element_assembly_seconds=assembly_seconds)
        row=np.repeat(ids,30,axis=1).ravel()
        col=np.tile(ids,(1,30)).ravel()
        K=coo_matrix((values.reshape(-1),(row,col)),shape=(ndof,ndof)).tocsc()
        K.sum_duplicates();K.sort_indices()
        del row,col,block,u
        if args.element_storage == 'mmap':
            values._mmap.close()
        del values
        gc.collect()
        assert np.isfinite(K.data).all()
        delta=K-K.T
        asym=float(np.max(abs(delta.data),initial=0.0))
        scale=float(np.max(abs(K.data)))
        assert asym < 1e-11*max(scale,1.0)
        del delta
        matrix_energies=np.einsum('ij,ij->j',probe,K@probe)
        energy_error=float(np.max(abs(matrix_energies-element_energies)/abs(element_energies)))
        assert energy_error<1e-11
        rigid=loads['R']
        rigid_residual=float(np.max(abs(K@rigid),initial=0.0))
        assert rigid_residual<1e-9
        progress('global_assembly_verified',K_nnz=int(K.nnz),K_symmetry_absolute_max=asym,
                 five_global_assembly_energy_probes_relative_error=energy_error,
                 six_rigid_modes_action_absolute_max=rigid_residual)
        level=out/'level-2';level.mkdir()
        temporary=level/'K.partial.npz'
        save_npz(temporary,K,compressed=False)
        if free_bytes(out)<reserve:
            raise RuntimeError('500MiB reserve not retained after K serialization')
        final=level/'K.npz';os.replace(temporary,final)
        np.savez_compressed(out/'mapping.npz',element_dofs=ids,vertices=vertices)
        for name in ('mesh.npz','loads.npz'):
            # A new pathname to the immutable same bytes; no full duplicate.
            try:
                os.link(original/name,level/name)
            except OSError as exc:
                if exc.errno not in (errno.EXDEV, errno.EPERM):
                    raise
                shutil.copyfile(original/name, level/name)
            assert sha(level/name) == input_hashes[str(original/name)]
        for path,expected_sha in {**input_hashes,**source_hashes}.items():
            assert sha(path)==expected_sha, 'input/source changed during assembly'
        report={'schema':'razr-fresh-L2-reconstruction-v1','body':args.body,'level':2,
                'original_tetrahedra':count,'subtetrahedra':16*count,'dofs':ndof,'condensed_dofs':ndof,
                'full_uncondensed_dofs':ndof+75*count,'E_normalization':1.0,'nu':0.3,
                'body_loads_on_added_internal_DOFs':False,'original_faces_and_surface_P2_traces_unchanged':True,
                'K_sha256':sha(final),'loads_sha256':input_hashes[str(original/'loads.npz')],
                'mesh_sha256':input_hashes[str(original/'mesh.npz')],'mapping_sha256':sha(out/'mapping.npz'),
                'K_bytes':final.stat().st_size,'K_nnz':int(K.nnz),'K_symmetry_absolute_max':asym,
                'global_directional_energy_probes':5,'global_energy_relative_error_max':energy_error,
                'rigid_modes_checked':6,'rigid_mode_action_max':rigid_residual,
                'coordinate_mapping_max_error_mm':coordinate_error,'minimum_scalar_DOF_separation_mm':separation,
                'input_sha256':input_hashes,'source_sha256':source_hashes,
                'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},
                'element_assembly_seconds':assembly_seconds,'seconds':time.monotonic()-start,
                'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'new_rebuild_identity':True,'original_historical_artifact_restored':False,
                'full_inverse_operator_probes_executed':False,'new_QP_executed':False,
                'contact_or_mesh_convergence_qualified':False,'candidate_go':False,
                'fixture_fabrication_go':False,'manufacturing_go':False}
        save_json(level/'report.json',report)
        if args.element_storage == 'mmap':
            partial.unlink()
        progress('completed_new_L2_matrix',completed=True,K_sha256=report['K_sha256'],K_bytes=report['K_bytes'])
    except BaseException as error:
        progress('interrupted_or_failed',completed=False,error_type=type(error).__name__,error=str(error))
        traceback.print_exc()
        raise

# This portable successor changes path, environment and storage handling only.
# Assembly formulas, normalized material, DOF mapping and acceptance thresholds
# are unchanged from the preserved reconstruction producer.
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body',choices=['panel','frame'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--inputs',type=Path,required=True, help='Directory containing exact panel/ and frame/ mesh.npz and loads.npz')
    parser.add_argument('--memory-gib',type=float,choices=(3.0,3.5,4.0),default=3.0)
    parser.add_argument('--element-storage', choices=('mmap', 'memory'), default='mmap',
                        help='Storage only; identical float64 element blocks and COO assembly order')
    main(parser.parse_args())
