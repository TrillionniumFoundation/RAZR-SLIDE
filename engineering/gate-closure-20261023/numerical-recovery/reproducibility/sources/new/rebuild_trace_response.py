"""Explicit new selected-face Schur adapter using original mathematical rules.

The same 86 frozen faces, original global DOFs, L2 local energy, constraints,
consistent load archive, ordered 3,885 points and five inverse probes are used.
Only the storage/evaluation of Z=K^-1 A changes: bounded column batches form S
and T, while each full response is evaluated with two genuine complete-K solves.
No skfem module is impersonated and no contact QP is performed by this program.
"""
from pathlib import Path
import argparse
import gc
import gzip
import hashlib
import json
import os
import resource
import sys
import time
import traceback
import numpy as np
from scipy.sparse import csc_matrix, hstack, vstack, load_npz, save_npz
from scipy.sparse.linalg import splu
from scipy.linalg import cho_factor, cho_solve

BASE=Path(__file__).resolve().parent
ROOT=Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'integration'))
sys.path.insert(0,str(ROOT/'engineering/consistent-load-20261017'))
from contact_exchange import ExactResponseCache
from surface_archive import SurfaceArchive
from rebuild_l2_only import sha, save_json, free_bytes


def main(args):
    start=time.monotonic();out=args.output.resolve()
    assert out!=ROOT and ROOT not in out.parents
    out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(int(args.memory_gib*1024**3),)*2)
    state={'schema':'razr-explicit-trace-response-progress-v1','body':args.body,
           'completed':False,'new_QP_executed':False,'historical_checkpoint_restored':False}
    def progress(phase,**extra):
        state.update(phase=phase,seconds=time.monotonic()-start,
                     peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**extra)
        save_json(out/'progress.json',state);print(json.dumps(state),flush=True)
    def guard():
        if time.monotonic()-start>args.seconds-30:raise TimeoutError('bounded trace response time budget')
        if free_bytes(out)<500*1024**2:raise RuntimeError('500MiB disk reserve reached')
    try:
        body=args.body;volume=args.volume.resolve()/body/'level-2'
        seed=args.base_response.resolve();interface=args.interface.resolve()
        report=json.loads((seed/'report.json').read_text())
        assert report['completed'] and report['body']==body
        assert report['ordered_original_seed_columns']==3885
        preflight=json.loads((interface/'report.json').read_text())
        assert preflight['completed'] and preflight['explicit_new_diagnostic_no_skfem_impersonation']
        info=next(r for r in preflight['original_selected_trace_interfaces_rebuilt'] if r['body']==body)
        inputs={str(seed/'report.json'):sha(seed/'report.json'),
                str(interface/'report.json'):sha(interface/'report.json')}
        for name,digest in report['files_sha256'].items():
            assert sha(seed/name)==digest;inputs[str(seed/name)]=digest
        for name,digest in {**report['identity']['inputs_sha256'],**preflight['input_sha256']}.items():
            assert sha(name)==digest;inputs[name]=digest
        for name in ('K.npz','loads.npz','mesh.npz'):
            selected=volume/name
            assert str(selected) in report['identity']['inputs_sha256']
            assert sha(selected)==report['identity']['inputs_sha256'][str(selected)]
        sources={str(Path(__file__)):sha(Path(__file__)),**report['source_sha256'],**preflight['source_sha256']}
        for name,digest in sources.items():assert sha(name)==digest
        for name,digest in info['new_files_sha256'].items():
            path=interface/body/name;assert sha(path)==digest;inputs[str(path)]=digest
        points=json.loads((seed/'points.json').read_text());m=len(points)
        assert m==3885 and sha(seed/'points.json')=='682a157686b06b4d8a1c8f431eab3453b9a43594801df148c03594435c4bf796'
        save_json(out/'points.json',points)
        with np.load(volume/'loads.npz',allow_pickle=False) as values:
            loads={name:values[name] for name in ('D','xyz','C','F','R')}
        with np.load(volume/'mesh.npz',allow_pickle=False) as values:vertices=values['points']
        n=loads['xyz'].shape[1];nb=info['new_trace_dofs'];fixed=loads['D']
        assert (n,nb)==({'panel':(344103,138),'frame':(474726,120)}[body])
        A=load_npz(interface/body/'coupling.npz').tocsc()
        with np.load(interface/body/'local-blocks.npz',allow_pickle=False) as values:B=values['B']
        assert A.shape==(n,nb) and B.shape==(nb,nb)
        chosen=json.loads((interface/body/'selection.json').read_text())
        lookup={tuple(x['vertices']):i for i,x in enumerate(chosen)}
        surface=SurfaceArchive(ROOT/'engineering/consistent-load-20261017/projection-512')
        lc,lcb,lf,lfb=surface.vectors(body,chosen,loads,'consistent')
        inputs.update(surface.hashes)
        baseC=load_npz(seed/'C.npz').tocsc()
        C0=hstack((csc_matrix(lc),baseC[:,4:]),format='csc')
        Cb=np.zeros((nb,m));Cb[:,:4]=lcb
        cf=ROOT/'engineering/contact-field-20261015/common-cell-results.json.gz'
        mf=ROOT/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
        raw=json.loads(gzip.decompress(cf.read_bytes()))
        metas=json.loads(gzip.decompress(mf.read_bytes()))['contact_patches']
        byname={x['patch']:x for x in metas};flat=[(byname[g['patch']],c) for g in raw for c in g['cells']]
        assert len(flat)==5255
        for j,p in enumerate(points[4:],4):
            descriptor,cell=flat[p['cell']]
            assert descriptor['patch']==p['patch'] and descriptor['initial_gap_mm']==p['gap']
            fi=lookup.get(tuple(sorted(cell[body+'_triangle'])))
            if fi is None:continue
            axis=descriptor['normal_axis'];tangent=[i for i in range(3) if i!=axis]
            face=vertices[cell[body+'_triangle']][:,tangent]
            tail=(np.asarray(p['xy'])-face[0])@np.linalg.inv((face[1:]-face[0]).T).T
            bubble=27*tail[0]*tail[1]*(1-tail.sum())
            sign=descriptor['normal_sign']*(1 if body=='panel' else -1)
            Cb[3*fi+axis,j]=sign*bubble
        C=vstack((C0,csc_matrix(Cb)),format='csc');C.sum_duplicates();C.eliminate_zeros();C.sort_indices()
        save_npz(out/'C.npz',C)
        G=np.asarray(C0.T@loads['R']) if body=='panel' else np.zeros((m,6))
        # This comparator is exactly the original explicit unloaded installation.
        # It introduces no measured material, preload, or service-load amplitude.
        external=np.zeros(n+nb);qfree=np.zeros(m);loadG=np.zeros(6)
        del raw,metas,byname,flat,vertices,lookup,surface,loads,lc,lcb,lf,lfb,baseC
        gc.collect();guard()
        assert free_bytes(out)>m*m*8+(n+nb)*5*8+540*1024**2
        K=load_npz(volume/'K.npz').tocsc();free=np.setdiff1d(np.arange(n),fixed)
        Kff=K[free][:,free].tocsc();del K
        Cf=C0[free].tocsc();Af=A[free].tocsc();gc.collect()
        assert np.max(abs(A[fixed].data),initial=0.)<1e-11
        progress('factorization_started',original_vector_dofs=n,new_trace_dofs=nb,
                 ordered_seed_columns=m,input_sha256=inputs,source_sha256=sources)
        t=time.monotonic();factor=splu(Kff,permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True})
        factor_seconds=time.monotonic()-t
        progress('factorization_completed',factor_seconds=factor_seconds,factor_nnz=int(factor.nnz))
        H=np.lib.format.open_memmap(out/'H.partial.npy',mode='w+',dtype=np.float64,shape=(m,m))
        baseH=np.load(seed/'H.npy',mmap_mode='r',allow_pickle=False)
        for lo in range(0,m,128):H[:,lo:lo+128]=baseH[:,lo:lo+128]
        # Original driver recomputes exactly the four changed nodal bolt columns.
        u=factor.solve(Cf[:,:4].toarray(order='F'))
        changed_residual=float(np.max(abs(Kff@u-Cf[:,:4].toarray())))
        assert changed_residual<=1e-7
        columns=np.asarray(Cf.T@u);H[:,:4]=columns;H[:4,:]=columns.T
        H[:4,:4]=(H[:4,:4]+H[:4,:4].T)/2
        del u,columns
        S=B.copy();T=Cb.copy();extension_residual=0.
        for lo in range(0,nb,8):
            hi=min(lo+8,nb);rhs=Af[:,lo:hi].toarray(order='F');X=factor.solve(rhs)
            residual=float(np.max(abs(Kff@X-rhs)))
            extension_residual=max(extension_residual,residual)
            assert residual<1e-8*max(1.,float(np.max(abs(A.data))))
            S[:,lo:hi]-=np.asarray(Af.T@X)
            T[lo:hi,:]-=np.asarray(Cf.T@X).T
            progress('Schur_columns',completed_columns=hi,required_columns=nb,
                     full_K_extension_residual_max=extension_residual)
            guard()
        del rhs,X
        asym=float(np.max(abs(S-S.T)));assert asym<1e-8*max(float(np.max(abs(S))),1e-300)
        S=(S+S.T)/2;sf=cho_factor(S,lower=True)
        eigen_min=float(np.linalg.eigvalsh(S).min());assert eigen_min>0.
        solvedT=cho_solve(sf,T)
        for lo in range(0,m,128):
            hi=min(lo+128,m);H[:,lo:hi]+=T.T@solvedT[:,lo:hi]
        H.flush();del solvedT,baseH;gc.collect()
        fields=[];rhs_hashes=[];residual_checks=[]
        def response(rhs):
            f=np.asarray(rhs[:n]);fb=np.asarray(rhs[n:])
            u0=factor.solve(f[free])
            q=cho_solve(sf,fb-np.asarray(Af.T@u0))
            uf=factor.solve(f[free]-np.asarray(Af@q))
            first=Kff@uf+Af@q-f[free];second=Af.T@uf+B@q-fb
            scale=max(float(np.max(abs(rhs))),1.0)
            error=max(float(np.max(abs(first))),float(np.max(abs(second))))/scale
            assert error<=1e-7
            full=np.zeros(n+nb);full[free]=uf;full[n:]=q
            fields.append(full.copy());rhs_hashes.append(hashlib.sha256(np.asarray(rhs,dtype=np.float64).tobytes()).hexdigest())
            residual_checks.append(error)
            return full
        identity={'space':'original L2 plus exact frozen selected face cubic bubbles',
                  'new_adapter':'sequential batch Schur, two complete K solves per response, no saved dense Z',
                  'body':body,'input_sha256':inputs,'points_sha256':sha(out/'points.json'),
                  'C_sha256':sha(out/'C.npz'),'external_load_scale':0.}
        cache=ExactResponseCache(n+nb,response,identity)
        checked=cache.restore(C,H,identity,probes=5)
        # Store the exact symmetric matrix accepted by the original interface.
        for lo in range(0,m,128):H[:,lo:lo+128]=cache.H[:,lo:lo+128]
        H.flush();H._mmap.close();del H
        os.replace(out/'H.partial.npy',out/'H.npy')
        np.save(out/'five-full-probe-fields.npy',np.stack(fields,axis=1))
        np.savez_compressed(out/'Schur.npz',S=S,B=B,T=T)
        save_npz(out/'coupling.npz',A)
        np.savez_compressed(out/'auxiliary.npz',G=G,qfree=qfree,loadG=loadG,
                            initialgap=np.array([p.get('gap',0.) for p in points]))
        for path,digest in {**inputs,**sources}.items():assert sha(path)==digest
        guard()
        files={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='progress.json'}
        result={'schema':'razr-explicit-full-trace-response-v1','body':body,'completed':True,
                'original_vector_dofs':n,'original_fixed_dofs':len(fixed),'new_trace_dofs':nb,
                'ordered_original_seed_columns':m,'selected_faces':len(chosen),
                'all_selected_trace_coefficients_free':True,'original_fixed_D_unchanged':True,
                'all_original_point_columns_and_order_unchanged':True,
                'original_consistent_nodal_and_bubble_loads_used':True,
                'full_K_extension_residual_max':extension_residual,
                'four_changed_nodal_load_columns_residual_max':changed_residual,
                'Schur_symmetry_absolute_error':asym,'Schur_minimum_eigenvalue':eigen_min,
                'dense_Z_stored':False,'equivalent_response_formula':'q=S^-1(fb-Af.T Kff^-1 f0); u=Kff^-1(f0-Af q)',
                'original_ExactResponseCache_restore':vars(checked),
                'five_full_augmented_residuals':residual_checks,'full_probe_rhs_sha256':rhs_hashes,
                'identity':identity,'input_sha256':inputs,'source_sha256':sources,'files_sha256':files,
                'factor_seconds':factor_seconds,'factor_nnz':int(factor.nnz),
                'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'explicit_new_adapter':True,'original_skfem_driver_executed':False,
                'unchanged_mathematical_criteria':True,'external_load_scale_over_Epanel_mm2':0.,
                'material_E_normalization':1.,'material_nu':.3,
                'new_QP_executed':False,'finite_QP_checkpoint':False,'historical_checkpoint_restored':False,
                'contact_or_mesh_convergence_qualified':False,'physical_or_current_EP5_qualification':False}
        save_json(out/'report.json',result)
        progress('completed',completed=True,original_five_probe_relative_error=checked.largest_relative_error,
                 report_sha256=sha(out/'report.json'))
    except BaseException as error:
        progress('interrupted_or_failed',error_type=type(error).__name__,error=str(error))
        traceback.print_exc();raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--body',choices=['panel','frame'],required=True)
    p.add_argument('--base-response',type=Path,required=True)
    p.add_argument('--volume',type=Path,default=Path('/tmp/razr-fe-20261023/volume-rebuild'))
    p.add_argument('--interface',type=Path,default=Path('/tmp/razr-fe-20261023/trace-interface-preflight'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--memory-gib',type=float,default=4.25)
    p.add_argument('--seconds',type=float,default=600.)
    main(p.parse_args())
