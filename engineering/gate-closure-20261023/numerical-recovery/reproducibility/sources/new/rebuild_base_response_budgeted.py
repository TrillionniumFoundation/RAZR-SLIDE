"""New full-operator base response for the original ordered PR35 seed maps.

Each invocation processes exactly one complete body.  It keeps the original
constraints and full K, solves all original response columns, and invokes the
original ExactResponseCache.restore five-probe validator.  This is a new linear
response seed, never an accepted finite QP or a restored historical checkpoint.
"""
from pathlib import Path
import argparse
import gc
import gzip
import hashlib
import json
import os
import resource
import shutil
import sys
import time
import traceback
import tempfile
import numpy as np
import scipy
from scipy.sparse import coo_matrix, csc_matrix, hstack, load_npz, save_npz
from scipy.sparse.linalg import splu

ROOT = Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'integration'))
from contact_patch_audit import triangle_coefficients, evaluate
from contact_exchange import ExactResponseCache
from rebuild_l2_only import sha, save_json
from predict_nd_fill import stored_array


def free_bytes(path):
    """Task budget excludes the filesystem blocks reserved for root."""
    status=os.statvfs(path)
    return status.f_bavail*status.f_frsize


def main(args):
    started = time.monotonic()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('output must be outside repository')
    output.mkdir(parents=True, exist_ok=False)
    workroot=Path("/tmp/razr-fe-20261023")
    workroot.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix=args.body+"-response-",dir=workroot))
    memory_limit=int(args.memory_gib*1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    state = {'schema':'razr-new-base-response-progress-v1', 'body':args.body,
             'completed':False, 'historical_checkpoint_restored':False,
             'new_QP_executed':False, 'contact_qualification':False,
             'private_temporary_directory':str(work),'address_space_limit_bytes':memory_limit}
    def progress(phase, **extra):
        state.update(phase=phase, seconds=time.monotonic()-started,
                     peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                     disk_free_bytes=free_bytes(output), **extra)
        save_json(output/'progress.json', state)
        print(json.dumps(state, allow_nan=False), flush=True)
    try:
        folder=args.volume.resolve()/args.body/'level-2'
        report=json.loads((folder/'report.json').read_text())
        assert report['body']==args.body and report['level']==2
        assert report['E_normalization']==1.0 and report['nu']==0.3
        assert report['original_faces_and_surface_P2_traces_unchanged'] is True
        assert report['body_loads_on_added_internal_DOFs'] is False
        inputs={str(folder/'report.json'):sha(folder/'report.json')}
        for filename,key in [('K.npz','K_sha256'),('mesh.npz','mesh_sha256'),('loads.npz','loads_sha256')]:
            path=folder/filename
            inputs[str(path)]=sha(path)
            assert inputs[str(path)]==report[key]
        seedpath=ROOT/'engineering/nested-contact-20261017/level-2/case-6/report.json.gz'
        common=ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz'
        meta=ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
        for path in (seedpath, common, meta):
            inputs[str(path)]=sha(path)
        sources={str(path):sha(path) for path in (
            Path(__file__),BASE/'rebuild_l2_only.py',BASE/'predict_nd_fill.py',BASE/'build_geometric_nd.py',ROOT/'integration/contact_exchange.py',
            ROOT/'integration/contact_patch_audit.py',
            ROOT/'engineering/volume-convergence-20261017/solve_enriched_contact.py')}
        seed=json.loads(gzip.decompress(seedpath.read_bytes()))
        points=seed['contact_points']
        assert seed['case']==6 and seed['volume_level']==2 and len(points)==3885
        assert points[:4]==[{'kind':'bolt','index':i} for i in range(4)]
        save_json(output/'points.json',points)
        m=len(points)
        reserve=500*1024**2
        # H plus the five genuine probe fields, with a 500 MiB disk reserve.
        expected_n={'panel':344103,'frame':474726}[args.body]
        if free_bytes(output)<m*m*8+expected_n*5*8+reserve+32*1024**2:
            raise RuntimeError('insufficient disk for complete response and 500MiB reserve')
        with np.load(folder/'loads.npz',allow_pickle=False) as ld:
            fixed=ld['D'];xyz=ld['xyz'];bolts=ld['C'];rigid=ld['R'];external=ld['F']
        n=xyz.shape[1]
        assert n==expected_n and len(fixed)==({'panel':6,'frame':777}[args.body])
        raw=json.loads(gzip.decompress(common.read_bytes()))
        metas=json.loads(gzip.decompress(meta.read_bytes()))['contact_patches']
        byname={x['patch']:x for x in metas}
        flat=[(byname[group['patch']],cell) for group in raw for cell in group['cells']]
        assert len(flat)==5255
        cells=[]
        for descriptor,cell in flat:
            axis=descriptor['normal_axis'];tan=[i for i in range(3) if i!=axis]
            origin=np.asarray(descriptor['origin_tangent_mm'])
            dofs=np.asarray(cell[args.body+'_P2_dofs'],dtype=int)
            coeff=triangle_coefficients(xyz[tan][:,dofs[:3]].T,np.eye(6),origin)
            cells.append((descriptor,dofs,coeff,origin))
        columns=[]
        for point in points:
            if point['kind']=='bolt':
                columns.append(csc_matrix(bolts[:,point['index'],None]))
                continue
            descriptor,dofs,coeff,origin=cells[point['cell']]
            assert point['patch']==descriptor['patch'] and point['gap']==descriptor['initial_gap_mm']
            sign=descriptor['normal_sign']*(1 if args.body=='panel' else -1)
            weights=sign*evaluate(coeff,np.asarray(point['xy'])[None],origin)[0]
            assert abs(weights.sum()-sign)<2e-9
            columns.append(coo_matrix((weights,(dofs,np.zeros(len(dofs),dtype=int))),shape=(n,1)).tocsc())
        C=hstack(columns,format='csc');C.sum_duplicates();C.eliminate_zeros();C.sort_indices()
        save_npz(output/'C.npz',C)
        # Original global model has panel rigid coordinates only. The frame
        # is held at its original 777 coordinates, with zero global R/F rows.
        if args.body=='panel':
            G=np.asarray(C.T@rigid)
            loadG=rigid.T@external
        else:
            G=np.zeros((m,6))
            loadG=np.zeros((6,4))
            assert external.shape==(n,0)
        del columns,cells,raw,metas,flat,byname,xyz,bolts,rigid
        gc.collect()
        identity={'body':args.body,'space':'original P2 traces with level-2 internal condensation',
                  'constraints':'original D, no substituted support or gauge',
                  'inputs_sha256':inputs,'points_sha256':sha(output/'points.json'),
                  'C_sha256':sha(output/'C.npz')}
        progress('full_force_maps_verified',original_vector_dofs=n,original_fixed_dofs=len(fixed),
                 ordered_seed_columns=m,C_nnz=int(C.nnz),input_sha256=inputs,source_sha256=sources)
        K=load_npz(folder/'K.npz').tocsc()
        assert K.shape==(n,n)
        free=np.setdiff1d(np.arange(n),fixed)
        Kff=K[free][:,free].tocsc()
        del K
        gc.collect()
        # Storage-only change: exact same original Kff bytes and MMD order.
        # File-backed arrays can be reclaimed without retaining another large
        # anonymous K copy alongside SuperLU's factor allocation.
        Kff_path=work/'Kff-exact-working.npz'
        if free_bytes(output)<Kff.data.nbytes+Kff.indices.nbytes+Kff.indptr.nbytes+reserve+160*1024**2:
            raise RuntimeError('insufficient disk for exact mapped Kff and reserve')
        save_npz(Kff_path,Kff,compressed=False)
        derived_Kff_sha256=sha(Kff_path)
        mapped_arrays=[stored_array(Kff_path,key) for key in ('data','indices','indptr')]
        mapped=csc_matrix(tuple(mapped_arrays),shape=Kff.shape,copy=False)
        assert np.array_equal(mapped.data,Kff.data) and np.array_equal(mapped.indices,Kff.indices) and np.array_equal(mapped.indptr,Kff.indptr)
        assert all(np.shares_memory(a,b) for a,b in zip((mapped.data,mapped.indices,mapped.indptr),mapped_arrays))
        mapped.has_sorted_indices=True;mapped.has_canonical_format=True
        del Kff;Kff=mapped;del mapped
        gc.collect()
        Cf=C[free].tocsc()
        progress('complete_K_factorization_started',free_dofs=len(free),Kff_nnz=int(Kff.nnz))
        factor_start=time.monotonic()
        factor=splu(Kff,permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True})
        factor_seconds=time.monotonic()-factor_start
        recorded_factor_nnz=int(factor.nnz)
        progress('complete_K_factorization_finished',factor_seconds=factor_seconds,
                 factor_nnz=int(factor.nnz))
        resumed_columns=0
        resumed_manifest=None
        if args.resume_manifest is not None:
            assert args.resume_sha256 is not None and sha(args.resume_manifest)==args.resume_sha256
            resumed_manifest=json.loads(args.resume_manifest.read_text())
            assert resumed_manifest['schema']=='razr-partial-linear-response-v1'
            assert resumed_manifest['body']==args.body
            assert resumed_manifest['input_sha256']==inputs
            assert resumed_manifest['required_columns']==m and resumed_manifest['original_vector_dofs']==n
            assert resumed_manifest['C_sha256']==sha(output/'C.npz')
            assert resumed_manifest['points_sha256']==sha(output/'points.json')
            for name,digest in {**resumed_manifest['producer_source_sha256'],**resumed_manifest['freeze_source_sha256']}.items():
                assert sha(name)==digest
            for name in ('progress','supervisor_report','C','points','partial_H'):
                assert sha(resumed_manifest[name+'_path'])==resumed_manifest[name+'_sha256']
            resumed_columns=resumed_manifest['completed_columns']
            assert type(resumed_columns) is int and 0<resumed_columns<=m
            shutil.copyfile(resumed_manifest['partial_H_path'],work/'H.partial.npy')
            assert sha(work/'H.partial.npy')==resumed_manifest['partial_H_sha256']
            H=np.load(work/'H.partial.npy',allow_pickle=False,mmap_mode='r+')
            assert H.shape==(m,m) and H.dtype==np.float64
            progress('partial_linear_response_prefix_verified',completed_columns=resumed_columns,
                     resumed_manifest_sha256=args.resume_sha256,required_columns=m)
        else:
            assert args.resume_sha256 is None
            H=np.lib.format.open_memmap(work/'H.partial.npy',mode='w+',dtype=np.float64,shape=(m,m))
        residual_max=float(resumed_manifest.get('linear_solve_residual_max') or 0.0) if resumed_manifest else 0.0
        solve_seconds=0.0
        batch=args.batch
        first_batch_seconds=None
        for lo in range(resumed_columns,m,batch):
            hi=min(lo+batch,m)
            before=time.monotonic()
            rhs=Cf[:,lo:hi].toarray(order='F')
            solution=factor.solve(rhs)
            residual=Kff@solution-rhs
            rel=float(np.max(abs(residual)))/max(float(np.max(abs(rhs))),1.0)
            residual_max=max(residual_max,rel)
            # Same full constrained operator; no approximate/local solve.
            if rel>1e-7:
                raise ValueError('full free-DOF residual exceeds bounded-rebuild tolerance')
            H[:,lo:hi]=np.asarray(Cf.T@solution)
            dt=time.monotonic()-before;solve_seconds+=dt
            if first_batch_seconds is None:
                first_batch_seconds=dt
                predicted=time.monotonic()-started+dt*(m-resumed_columns)/(hi-lo)
                progress('pilot_full_operator_columns_completed',completed_columns=hi,
                         first_batch_seconds=dt,predicted_total_seconds=predicted,
                         linear_solve_residual_max=residual_max)
                if predicted>1200:
                    H.flush()
                    raise RuntimeError('measured remaining-column estimate exceeds 1200-second review time budget')
                if predicted>args.seconds-60:
                    progress('bounded_linear_response_chunks_required',completed_columns=hi,
                             predicted_remaining_completion_seconds=predicted,
                             partial_linear_response_is_not_QP_checkpoint=True)
            if hi%128==0 or hi==m:
                H.flush()
                progress('full_operator_response_columns',completed_columns=hi,total_columns=m,
                         response_solve_seconds=solve_seconds,linear_solve_residual_max=residual_max)
                if time.monotonic()-started>args.seconds-45:
                    raise TimeoutError('explicit response time budget reached before final validation')
                if free_bytes(output)<reserve:
                    raise RuntimeError('500MiB disk reserve reached')
        if resumed_columns<m:
            del solution,rhs,residual
        # Chunked extrema avoid allocating a complete absolute-value copy
        # while the original factor is still resident.
        scale=1e-300
        for lo in range(0,m,128):
            scale=max(scale,float(np.max(abs(H[lo:min(lo+128,m),:]))))
        # Chunked symmetry validation avoids another dense H allocation.
        asym=0.0
        for lo in range(0,m,128):
            hi=min(lo+128,m)
            asym=max(asym,float(np.max(abs(H[lo:hi,:]-H[:,lo:hi].T))))
        if asym>2e-8*scale or float(np.min(np.diag(H))) < -2e-8*scale:
            raise ValueError('full response reciprocity or self-energy failure')
        for lo in range(0,m,128):
            hi=min(lo+128,m)
            for col in range(lo,m,128):
                end=min(col+128,m)
                average=(H[lo:hi,col:end]+H[col:end,lo:hi].T)*0.5
                H[lo:hi,col:end]=average
                H[col:end,lo:hi]=average.T
        H.flush()
        probe_fields=[];probe_rhs_hashes=[];probe_residuals=[]
        def response(rhs):
            u=np.zeros(n)
            u[free]=factor.solve(np.asarray(rhs[free]))
            residual=Kff@u[free]-rhs[free]
            ratio=float(np.max(abs(residual)))/max(float(np.max(abs(rhs[free]))),1.0)
            if ratio>1e-7:
                raise ValueError('five-probe full free-DOF residual exceeded')
            probe_residuals.append(ratio)
            probe_fields.append(u.copy())
            probe_rhs_hashes.append(hashlib.sha256(np.asarray(rhs,dtype=np.float64).tobytes()).hexdigest())
            return u
        # Compute exactly the original deterministic complete-K actions first.
        # Their RHS hashes restrict the later original-interface replay to these
        # genuine fields; no unknown load can be answered by this callback.
        generator=np.random.default_rng(73021)
        directions=[np.ones(m)]+[generator.choice([-1.,1.],m) for _ in range(4)]
        for direction in directions:response(np.asarray(C@direction).ravel())
        qfree=np.zeros((m,4))
        if external.shape[1]:
            assert external.shape[1]==4
            u=factor.solve(np.asarray(external[free],order='F'))
            qfree=np.asarray(Cf.T@u)
            err=float(np.max(abs(Kff@u-external[free])))
            if err>1e-7*max(float(np.max(abs(external))),1.0):
                raise ValueError('external full response residual exceeded')
        del factor
        gc.collect()
        progress('five_full_probe_actions_solved_LU_released',
                 full_probe_residuals=probe_residuals,derived_Kff_sha256=derived_Kff_sha256)
        calls=0
        def replay_solved_action(rhs):
            nonlocal calls
            if calls>=5 or hashlib.sha256(np.asarray(rhs,dtype=np.float64).tobytes()).hexdigest()!=probe_rhs_hashes[calls]:
                raise ValueError('callback accepts only the five genuinely solved complete-K RHS actions')
            value=probe_fields[calls].copy();calls+=1;return value
        cache=ExactResponseCache(n,replay_solved_action,identity)
        checked=cache.restore(C,H,identity,probes=5)
        assert calls==5
        np.save(work/'five-full-probe-fields.npy',np.stack(probe_fields,axis=1))
        del Kff
        gc.collect()
        for array in mapped_arrays:array._mmap.close()
        del mapped_arrays
        assert sha(Kff_path)==derived_Kff_sha256, "derived working Kff changed during execution"
        Kff_path.unlink()
        np.savez(work/'auxiliary.npz',G=G,qfree=qfree,loadG=loadG,
                 initialgap=np.array([point.get('gap',0.0) for point in points]))
        H._mmap.close();del H
        os.replace(work/'H.partial.npy',work/'H.npy')
        for path,digest in {**inputs,**sources}.items():
            assert sha(path)==digest,'input or source changed during computation'
        if free_bytes(output)<reserve:
            raise RuntimeError('500MiB disk reserve not retained')
        for name in ('H.npy','auxiliary.npz','five-full-probe-fields.npy'):
            # Stable finalized data only. /tmp and workspace forbid hardlinks.
            digest=sha(work/name)
            temporary=output/(name+'.writing')
            shutil.copyfile(work/name,temporary)
            assert sha(temporary)==digest
            os.replace(temporary,output/name)
            with (work/name).open('r+b') as f:f.truncate(0)
            (work/name).unlink()
        work.rmdir()
        files={name:sha(output/name) for name in ('H.npy','C.npz','points.json','auxiliary.npz','five-full-probe-fields.npy')}
        result={'schema':'razr-new-full-body-base-response-v1','body':args.body,
                'completed':True,'original_vector_dofs':n,'original_fixed_dofs':len(fixed),
                'full_free_dofs_solved':len(free),'ordered_original_seed_columns':m,
                'identity':identity,'source_sha256':sources,'files_sha256':files,
                'factor_seconds':factor_seconds,'factor_nnz':recorded_factor_nnz,
                'response_solve_seconds':solve_seconds,'linear_solve_residual_max':residual_max,
                'H_reciprocity_absolute_max':asym,'H_reciprocity_relative_max':asym/scale,
                'original_ExactResponseCache_restore':vars(checked),
                'full_probe_rhs_sha256':probe_rhs_hashes,'full_probe_residuals':probe_residuals,
                'seconds':time.monotonic()-started,
                'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},
                'new_base_response_seed':True,'factorization_order':'original MMD_AT_PLUS_A','derived_exact_Kff_working_sha256':derived_Kff_sha256,'Kff_storage':'read-only verified file-backed CSC arrays',
                'disk_budget_uses_nonprivileged_available_blocks':True,
                'derived_Kff_final_sha256_rechecked_before_unlink':True,'restore_callback_scope':'five SHA-bound complete-K actions actually solved immediately before releasing LU; unknown RHS rejected','historical_artifact_restored':False,
                'resumed_partial_columns':resumed_columns,
                'resumed_partial_manifest_sha256':args.resume_sha256,
                'resumed_partial_manifest':resumed_manifest,
                'response_columns_solved_this_invocation':m-resumed_columns,
                'auxiliary_convention':'original panel-only rigid coordinates and panel-only external loads; frame G/qfree/loadG contribution exactly zero',
                'finite_QP_checkpoint':False,'new_QP_executed':False,
                'gauge_reactions_not_a_physical_load_qualification':True,
                'contact_or_mesh_convergence_qualified':False,'hardware_or_EP5_structural_qualification':False}
        save_json(output/'report.json',result)
        progress('completed_new_body_base_response',completed=True,files_sha256=files,
                 original_five_probe_relative_error=checked.largest_relative_error)
    except BaseException as error:
        progress('interrupted_or_failed',completed=False,error_type=type(error).__name__,error=str(error))
        traceback.print_exc()
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body',choices=['panel','frame'],required=True)
    parser.add_argument('--volume',type=Path,default=Path('/tmp/razr-fe-20261023/volume-rebuild'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--memory-gib',type=float,choices=(4.0,4.25,4.5),default=4.25)
    parser.add_argument('--resume-manifest',type=Path)
    parser.add_argument('--resume-sha256')
    parser.add_argument('--batch',type=int,default=8,choices=(1,2,4,8,16))
    main(parser.parse_args())
