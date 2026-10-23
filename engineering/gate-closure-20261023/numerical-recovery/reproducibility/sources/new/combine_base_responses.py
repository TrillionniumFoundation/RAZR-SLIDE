"""Combine complete body responses and verify the five original full-K probes.

The original global elastic operator is block diagonal in panel/frame. Each
body has freshly solved all 3,885 force columns and the same five full probe
loads. We recheck those full fields against K, assemble C.T U, and replay ONLY
the five SHA-bound solved actions through the original restore interface.
This bounded replay callback is not advertised as a general elastic solver.
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
import numpy as np
import scipy
from scipy.sparse import load_npz, save_npz, vstack

BASE=Path(__file__).resolve().parent
ROOT=Path('/workspace/scratch/95cd2986fdf2/RAZR-SLIDE')
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import ExactResponseCache
from rebuild_l2_only import sha, save_json, free_bytes


def array_sha(value):
    return hashlib.sha256(np.asarray(value,dtype=np.float64).tobytes()).hexdigest()


def main(args):
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    out=args.output.resolve()
    if out==ROOT or ROOT in out.parents:
        raise ValueError('use a new output directory outside the repository')
    out.mkdir(parents=True,exist_ok=False)
    if free_bytes(out)<450*1024**2+500*1024**2:
        raise RuntimeError('insufficient disk for complete combined response with reserve')
    m=3885
    rng=np.random.default_rng(73021)
    directions=np.column_stack([np.ones(m)]+[rng.choice([-1.,1.],m) for _ in range(4)])
    reports={};matrices={};fields={};auxiliary={};hashes={};probe_details=[]
    input_hashes={};source_hashes={str(Path(__file__)):sha(Path(__file__)),
                                str(ROOT/'integration/contact_exchange.py'):sha(ROOT/'integration/contact_exchange.py')}
    for body,folder,n in [('panel',args.panel.resolve(),344103),('frame',args.frame.resolve(),474726)]:
        report=json.loads((folder/'report.json').read_text())
        assert report['completed'] is True and report['body']==body
        assert report['ordered_original_seed_columns']==m and report['original_vector_dofs']==n
        assert report['original_ExactResponseCache_restore']['probes']==5
        assert report['finite_QP_checkpoint'] is False and report['new_QP_executed'] is False
        hashes[str(folder/'report.json')]=sha(folder/'report.json')
        for name,digest in report['files_sha256'].items():
            assert sha(folder/name)==digest
            hashes[str(folder/name)]=digest
        for name,digest in report['identity']['inputs_sha256'].items():
            assert sha(name)==digest
            input_hashes[name]=digest
        for name,digest in report['source_sha256'].items():
            assert sha(name)==digest
            source_hashes[name]=digest
        assert report['files_sha256']['points.json']=='682a157686b06b4d8a1c8f431eab3453b9a43594801df148c03594435c4bf796'
        C=load_npz(folder/'C.npz').tocsc()
        H=np.load(folder/'H.npy',mmap_mode='r',allow_pickle=False)
        U=np.load(folder/'five-full-probe-fields.npy',mmap_mode='r',allow_pickle=False)
        assert C.shape==(n,m) and H.shape==(m,m) and U.shape==(n,5)
        rhs=np.asarray(C@directions)
        for index in range(5):
            assert array_sha(rhs[:,index])==report['full_probe_rhs_sha256'][index]
        volume=args.volume.resolve()/body/'level-2'
        for name in ('K.npz','loads.npz'):
            selected=volume/name
            assert str(selected) in report['identity']['inputs_sha256']
            assert sha(selected)==report['identity']['inputs_sha256'][str(selected)]
        with np.load(volume/'loads.npz',allow_pickle=False) as loads:
            fixed=loads['D']
        K=load_npz(volume/'K.npz')
        free=np.setdiff1d(np.arange(n),fixed)
        residual=K@U-rhs
        ratio=float(np.max(abs(residual[free])))/max(float(np.max(abs(rhs[free]))),1.0)
        assert ratio<1e-7 and np.max(abs(U[fixed]),initial=0.0)==0.0
        measured=np.asarray(C.T@U)
        saved=np.asarray(H@directions)
        ratios=[]
        for index in range(5):
            denominator=max(float(np.max(abs(measured[:,index]))),float(np.max(abs(saved[:,index]))),1e-300)
            error=float(np.max(abs(measured[:,index]-saved[:,index])))/denominator
            assert error<=2e-7
            ratios.append(error)
        probe_details.append({'body':body,'full_vector_dofs':n,'complete_free_dofs_checked':len(free),
                              'full_K_residual_relative_max':ratio,
                              'fixed_coordinate_response_exactly_zero':True,
                              'five_H_action_relative_errors':ratios,
                              'fixed_reactions_are_algebraic_probe_reactions_not_contact_equilibrium':True})
        del K,residual,rhs,free,measured,saved
        gc.collect()
        matrices[body]=(C,H);fields[body]=U;reports[body]=report
        with np.load(folder/'auxiliary.npz',allow_pickle=False) as a:
            auxiliary[body]={key:a[key] for key in a.files}
    P,F=auxiliary['panel'],auxiliary['frame']
    assert np.array_equal(P['initialgap'],F['initialgap'])
    for key in ('G','qfree','loadG'):
        assert np.count_nonzero(F[key])==0,'original frame global rigid/external contribution must be zero'
    C=vstack((matrices['panel'][0],matrices['frame'][0]),format='csc')
    H=np.lib.format.open_memmap(out/'H-combining.npy',mode='w+',dtype=np.float64,shape=(m,m))
    for lo in range(0,m,128):
        hi=min(lo+128,m)
        H[:,lo:hi]=matrices['panel'][1][:,lo:hi]+matrices['frame'][1][:,lo:hi]
    H.flush()
    global_U=np.vstack((fields['panel'],fields['frame']))
    assert global_U.shape==(818829,5)
    measured=np.asarray(C.T@global_U);predicted=np.asarray(H@directions)
    combined_errors=[]
    for index in range(5):
        denominator=max(float(np.max(abs(measured[:,index]))),float(np.max(abs(predicted[:,index]))),1e-300)
        error=float(np.max(abs(measured[:,index]-predicted[:,index])))/denominator
        assert error<=2e-7
        combined_errors.append(error)
    # Require exact original full RHS identities, then return only the freshly
    # solved complete fields. Unknown/changed actions are rejected, never filled
    # by a reduced or synthetic model. This avoids keeping both LU factors live.
    calls=0
    def replay_exact_solved_probe(rhs):
        nonlocal calls
        if calls>=5 or rhs.shape!=(818829,):
            raise ValueError('callback is restricted to five archived full-K probe actions')
        if (array_sha(rhs[:344103])!=reports['panel']['full_probe_rhs_sha256'][calls]
                or array_sha(rhs[344103:])!=reports['frame']['full_probe_rhs_sha256'][calls]):
            raise ValueError('requested RHS differs from the genuinely solved full probe')
        value=np.array(global_U[:,calls],copy=True)
        calls+=1
        return value
    identity={'space':'new L2-only full panel/frame elastic model with unchanged original traces and constraints',
              'input_sha256':input_hashes,'body_response_artifacts_sha256':hashes,
              'ordered_points_sha256':reports['panel']['files_sha256']['points.json']}
    cache=ExactResponseCache(818829,replay_exact_solved_probe,identity)
    checked=cache.restore(C,H,identity,probes=5)
    assert calls==5
    save_npz(out/'C.npz',C)
    np.savez_compressed(out/'response.npz',H=cache.H,G=P['G'],qfree=P['qfree'],
                        initialgap=P['initialgap'],loadG=P['loadG'])
    np.savez_compressed(out/'five-full-operator-probes.npz',directions=directions,
                        full_response=global_U,measured_C_transpose_U=measured)
    shutil.copyfile(args.panel/'points.json',out/'points.json')
    H._mmap.close();del H
    temporary=out/'H-combining.npy'
    with temporary.open('r+b') as f:f.truncate(0)
    temporary.unlink()
    for name,digest in {**hashes,**input_hashes,**source_hashes}.items():
        assert sha(name)==digest
    manifest={'schema':'razr-new-PR35-linear-base-response-seed-v1',
              'volume_level':2,'input_sha256':input_hashes,'source_sha256':source_hashes,
              'response_sha256':sha(out/'response.npz'),'points_sha256':sha(out/'points.json'),
              'C_sha256':sha(out/'C.npz'),'full_probe_archive_sha256':sha(out/'five-full-operator-probes.npz'),
              'original_ordered_point_columns':m,'complete_vector_dofs':818829,
              'new_linear_response_seed':True,'finite_QP_checkpoint':False,
              'historical_response_restored':False,'new_QP_executed':False,
              'whole_surface_contact_pass':False,'physical_qualification':False}
    save_json(out/'manifest.json',manifest)
    result={'schema':'razr-combined-full-operator-response-verification-v1','completed':True,
            'all_3885_columns_recomputed_with_complete_new_K':True,
            'body_probes_rechecked_against_full_K':probe_details,
            'five_combined_C_transpose_U_vs_Hv_relative_errors':combined_errors,
            'original_ExactResponseCache_restore':vars(checked),
            'probe_callback_scope':'exactly five SHA-bound archived fresh full-operator solve actions; unknown RHS rejected',
            'not_only_boolean_body_pass_combination':True,
            'input_sha256':input_hashes,'body_response_artifact_sha256':hashes,
            'source_sha256':source_hashes,'manifest_sha256':sha(out/'manifest.json'),
            'seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},
            'linear_seed_usable_by_original_outer_trace_driver':True,
            'unchanged_outer_driver_still_requires_skfem':True,
            'accepted_finite_QP_checkpoint':False,'new_QP_executed':False,
            'contact_or_mesh_convergence_qualified':False,'hardware_or_current_EP5_structural_qualification':False}
    save_json(out/'verification.json',result)
    print(json.dumps({'completed':True,'output':str(out),'original_five_probe_check':vars(checked),
                      'manifest_sha256':result['manifest_sha256']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel',type=Path,required=True)
    parser.add_argument('--frame',type=Path,required=True)
    parser.add_argument('--volume',type=Path,default=Path('/tmp/razr-fe-20261023/volume-rebuild'))
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
