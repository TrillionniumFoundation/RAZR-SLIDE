"""Resume the unchanged original RAZR contact problem from a pinned checkpoint.

Use explicit prepared input paths, then independently recheck all returned
full fields before any integration claim. Multiple right-hand sides change
only evaluation of the same factored elastic operator. It does not change
CAD, E/nu, load, bolt compliance, gauge, frame support or gap tolerance.
"""
from __future__ import annotations
from pathlib import Path
import argparse, gzip, hashlib, json, sys, time
import numpy as np
from scipy.sparse import csc_matrix, coo_matrix, hstack, vstack, load_npz
from scipy.sparse.linalg import splu

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integration'))
from contact_patch_audit import triangle_coefficients,evaluate
from contact_exchange import ExactResponseCache,QuadraticGapBatch,select_violations,sha256,feasible_force_guess
from contact_dual_active import solve_force_qp

BASE_COMMIT='ab8e32acf4d6dc0510e45838ec03458f4de28363'
GAP_TOLERANCE=1e-7
AUDITOR_SHA='6e6ee08ecf2eac3539edab1f9c18be8cfed8e6dc03f80a3010dc48bc7c612100'


def _json_numpy(value):
    # ndarray.item() is not a conversion for multi-element arrays.
    if isinstance(value,np.ndarray):
        return value.tolist()
    if isinstance(value,np.generic):
        return value.item()
    raise TypeError('unsupported result type: '+type(value).__name__)


def dump(path, value):
    # Output paths are always in a newly created result directory.
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False,
        default=_json_numpy)+'\n')


def column(size, indices, weights):
    return coo_matrix((weights,(indices,np.zeros(len(indices),dtype=int))),shape=(size,1)).tocsc()


def arguments():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=ROOT)
    p.add_argument('--inputs',type=Path,required=True,help='restored elastic/panel and elastic/frame directories')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cases',type=int,nargs='+',default=[4,5,6,7])
    p.add_argument('--new-points',type=int,default=128)
    p.add_argument('--max-points',type=int,default=6000)
    p.add_argument('--max-exchanges',type=int,default=80)
    p.add_argument('--response-batch-size',type=int,default=16)
    p.add_argument('--resume-state',type=Path,help='immutable completed finite-QP checkpoint directory')
    a=p.parse_args()
    if a.repo.resolve() != ROOT.resolve():
        p.error('--repo must be this adapter repository, not another code tree')
    if len(a.cases)!=len(set(a.cases)) or any(i not in range(8) for i in a.cases):
        p.error('unique original case indices 0..7 required')
    if not 1<=a.new_points<=512 or a.max_points<1 or a.max_exchanges<1 or not 1<=a.response_batch_size<=64:
        p.error('invalid explicit resource bound')
    a.repo=a.repo.resolve();a.inputs=a.inputs.resolve();a.output=a.output.resolve()
    if a.output==a.repo or a.repo in a.output.parents or a.output==a.inputs or a.inputs in a.output.parents:
        p.error('use a new directory outside source and input trees')
    a.output.mkdir(parents=True,exist_ok=False)
    return a


def main(a):
    e=a.repo/'engineering/spatial-contact-integration-20261015'
    delivery=json.loads((e/'DELIVERY_VERIFICATION.json').read_text())
    expected_inputs=delivery['full_response_checkpoint']
    response_file=e/'bounded-exact-response.npz';point_file=e/'bounded-contact-points.json'
    resumed=None
    if a.resume_state is None:
        assert sha256(response_file)==expected_inputs['exact-response-system.npz']['sha256']
        assert sha256(point_file)==expected_inputs['contact-point-locations.json']['sha256']
    else:
        state=a.resume_state.resolve()
        if state==a.output or a.output in state.parents or state in a.output.parents:
            raise ValueError('resume state and new output must not overlap')
        resumed=json.loads((state/'manifest.json').read_text())
        assert resumed['gap_tolerance_mm']==GAP_TOLERANCE
        assert 0<=resumed['case']<8 and resumed['state_is_finite_QP_not_gap_qualification']
        for path,want in resumed['input_sha256'].items():
            assert sha256(Path(path))==want,('changed checkpoint dependency',path)
        response_file=state/'response.npz';point_file=state/'points.json'
        assert sha256(response_file)==resumed['response_sha256']
        assert sha256(point_file)==resumed['points_sha256']

    assert sha256(a.repo/'integration/contact_patch_audit.py')==AUDITOR_SHA
    hashes={str(response_file):sha256(response_file),str(point_file):sha256(point_file)}
    if resumed is not None:
        path=a.resume_state.resolve()/'manifest.json';hashes[str(path)]=sha256(path)
    for name,want in {
        'assembly_inputs.json':'7b7ebf0f48556f2feca175a35b882a9a48337de2bb5f54b1ba7a740f85e8ce6b',
        'roof_joint_load_inputs.json':'09f7b392b00a59ca1fdb5fa97ad10e6b4d5361ae0f440afb8dd4e9ee225a2640',
        'frame_thread_actual_inputs.json':'4dcb50162bd25a7507a3afb4ba7e0f7aa33b8c233c0a366e68b8adec51a13609',
    }.items():
        path=a.repo/'integration'/name;assert sha256(path)==want;hashes[str(path)]=want
    bodies={}
    for name in ('panel','frame'):
        folder=a.inputs/name
        registered=json.loads((e/(name+'-elastic-input.json')).read_text())
        for filename,key in [('K.npz','K_sha256'),('loads.npz','loads_sha256'),('mesh.npz','mesh_sha256')]:
            path=folder/filename;assert sha256(path)==registered[key],('input differs',path)
            hashes[str(path)]=registered[key]
        K=load_npz(folder/'K.npz').tocsc();ld=np.load(folder/'loads.npz',allow_pickle=False)
        data={k:ld[k] for k in ld.files};fixed=data['D'];free=np.setdiff1d(np.arange(K.shape[0]),fixed)
        assert K.shape==(registered['dofs'],)*2
        before=time.monotonic();factor=splu(K[free][:,free],permc_spec='MMD_AT_PLUS_A',
            diag_pivot_thresh=0.,options={'SymmetricMode':True})
        bodies[name]={'K':K,'data':data,'free':free,'D':fixed,'factor':factor}
        print('FACTOR',name,K.shape,time.monotonic()-before,flush=True)
    P,F=bodies['panel'],bodies['frame'];npanel=P['K'].shape[0];nframe=F['K'].shape[0];n=npanel+nframe
    def response(rhs):
        # SuperLU accepts one or several RHS columns with identical factors.
        u=np.zeros_like(rhs, dtype=float)
        u[P['free']]=P['factor'].solve(np.asfortranarray(rhs[P['free']]))
        u[npanel+F['free']]=F['factor'].solve(np.asfortranarray(rhs[npanel+F['free']]))
        return u
    cf=a.repo/'engineering/contact-field-20261015/common-cell-results.json.gz'
    mf=a.repo/'engineering/contact-field-20261015/coupled-field-audit.json.gz'
    raw=json.loads(gzip.decompress(cf.read_bytes()))
    metas=json.loads(gzip.decompress(mf.read_bytes()))['contact_patches']
    # Bind the exact common domains in the cache identity, not just in the report.
    hashes[str(cf)]=sha256(cf);hashes[str(mf)]=sha256(mf)
    cache=ExactResponseCache(n,response,{'base':BASE_COMMIT,'input_sha256':hashes},
                             response_block=response,response_batch_size=a.response_batch_size)
    byname={m['patch']:m for m in metas};cells=[]
    for group in raw:
        m=byname[group['patch']];axis=m['normal_axis'];tan=[i for i in range(3) if i!=axis]
        origin=np.array(m['origin_tangent_mm'])
        for x in group['cells']:
            dp=np.array(x['panel_P2_dofs'],dtype=int);df=np.array(x['frame_P2_dofs'],dtype=int)
            cp=triangle_coefficients(P['data']['xyz'][tan][:,dp[:3]].T,np.eye(6),origin)
            cq=triangle_coefficients(F['data']['xyz'][tan][:,df[:3]].T,np.eye(6),origin)
            cells.append({'label':m['patch'],'origin':origin,'vertices':x['polygon'],'dp':dp,'df':df,
                          'tp':cp,'tf':cq,'normal':m['normal_sign'],'gap':m['initial_gap_mm']})
    assert len(cells)==5255
    batch=QuadraticGapBatch([c['vertices'] for c in cells],[c['origin'] for c in cells])
    tp=np.stack([c['tp'] for c in cells]);tf=np.stack([c['tf'] for c in cells])
    dp=np.stack([c['dp'] for c in cells]);df=np.stack([c['df'] for c in cells])
    normal=np.array([c['normal'] for c in cells]);gap0=np.array([c['gap'] for c in cells])
    points=json.loads(point_file.read_text());checkpoint=np.load(response_file,allow_pickle=False)
    assert len(points)==checkpoint['H'].shape[0] and len(points)<a.max_points+4
    def point_column(p):
        if p['kind']=='bolt':
            i=p['index'];assert i in range(4)
            return vstack([csc_matrix(P['data']['C'][:,i,None]),csc_matrix(F['data']['C'][:,i,None])],format='csc')
        c=cells[p['cell']];assert p['patch']==c['label'] and p['gap']==c['gap']
        xy=np.asarray(p['xy']);sign=c['normal']
        wp=evaluate(c['tp'],xy[None,:],c['origin'])[0]*sign
        wf=-evaluate(c['tf'],xy[None,:],c['origin'])[0]*sign
        assert abs(wp.sum()-sign)<2e-9 and abs(wf.sum()+sign)<2e-9
        return column(n,np.r_[c['dp'],npanel+c['df']],np.r_[wp,wf])
    C=hstack([point_column(p) for p in points],format='csc')
    check=cache.restore(C,checkpoint['H'],cache.identity,probes=5)
    # Recompute low-dimensional maps from the unchanged full force maps. Never
    # infer them from the checkpoint without checking their physical identity.
    Uext=np.stack([response(np.r_[P['data']['F'][:,j],np.zeros(nframe)]) for j in range(4)],axis=1)
    R=np.vstack([P['data']['R'],np.zeros((nframe,6))])
    G=np.asarray(cache.C.T@R);qfree=np.asarray(cache.C.T@Uext)
    initialgap=np.array([p.get('gap',0.) for p in points])
    loadG=P['data']['R'].T@P['data']['F']
    np.testing.assert_allclose(G,checkpoint['G'],rtol=1e-8,atol=2e-8)
    np.testing.assert_allclose(qfree,checkpoint['qfree'],rtol=2e-7,atol=1e-8)
    np.testing.assert_array_equal(initialgap,checkpoint['initialgap'])
    np.testing.assert_allclose(loadG,checkpoint['loadG'],rtol=1e-10,atol=1e-10)
    print('CHECKPOINT_RESTORED',len(points)-4,check,flush=True)
    dump(a.output/'checkpoint-validation.json',{'probes':check.probes,'relative_error':check.largest_relative_error,
         'input_sha256':hashes,'full_fields_recomputed_per_old_point':False})
    if resumed is None:
        seed=json.loads((e/'case-4/report.json').read_text())
        seed_points=seed['contact_points']
        assert len(seed_points)<=len(points) and all(x==y for x,y in zip(seed_points,points))
        oldlam=np.asarray(seed['forces']);oldlam=np.pad(oldlam,(0,len(points)-len(oldlam)))
    else:
        oldlam=np.asarray(checkpoint['forces'])
        assert oldlam.shape==(len(points),) and np.isfinite(oldlam).all()

    seen={m['patch']:[] for m in metas}
    for p in points[4:]:seen[p['patch']].append(p['xy'])
    case_summaries=[]
    for case in a.cases:
        out=a.output/f'case-{case}';out.mkdir();j=case%4;force=1e-5;pre=0. if case<4 else 2e-4
        history=[];success=False;returned=None
        # Transfer only a feasible optimization GUESS, never a copied result.
        if oldlam is not None:
            oldlam=np.pad(oldlam,(0,len(points)-len(oldlam)))
            warm=feasible_force_guess(G,loadG[:,j]*force,oldlam)
            oldlam=warm.pop('forces')
            dump(out/'warm-start.json',warm)

        for exchange in range(a.max_exchanges):
            m=len(points);S=cache.H.copy();S[np.arange(4),np.arange(4)]+=5.
            d=qfree[:,j]*force-initialgap;d[:4]+=5.*pre
            if oldlam is not None:oldlam=np.pad(oldlam,(0,m-len(oldlam)))
            tic=time.monotonic();q=solve_force_qp(S,d,G,loadG[:,j]*force,initial=oldlam,tolerance=2e-10,factor_reuse=True)
            if not q['passed']:
                dump(out/'failure-qp.json',q);break
            lam=np.array(q['forces']);rigid=np.array(q['rigid_mode_coordinates'])
            u,applied=cache.reconstruct(np.r_[P['data']['F'][:,j]*force,np.zeros(nframe)],lam,
                                        rigid_displacement=R@rigid)
            up,uf=u[:npanel],u[npanel:]
            coefficients=-normal[:,None]*(np.einsum('ijk,ik->ij',tp,up[dp])-np.einsum('ijk,ik->ij',tf,uf[df]))
            coefficients[:,0]+=gap0
            audit=batch.extrema(coefficients);bad=np.flatnonzero(audit['minimum'] < -GAP_TOLERANCE)
            row={'exchange':exchange,'point_constraints':m-4,'negative_cells':len(bad),
                 'minimum_gap_mm':float(audit['minimum'].min()),'qp_iterations':q['iterations'],
                 'seconds':time.monotonic()-tic,'retained_response_storage_bytes':cache.storage_bytes()}
            history.append(row);dump(out/'progress.json',history);print('EXCHANGE',case,row,flush=True)
            returned=(lam,rigid,u,applied,q,audit,points.copy())
            snap=out/f'checkpoint-{exchange:03d}';snap.mkdir()
            np.savez_compressed(snap/'response.npz',H=cache.H,G=G,qfree=qfree,
                                initialgap=initialgap,loadG=loadG,forces=lam,rigid=rigid)
            dump(snap/'points.json',points)
            dump(snap/'manifest.json',{'case':case,'exchange':exchange,'input_sha256':hashes,
                'source_sha256':sha256(Path(__file__)),'response_sha256':sha256(snap/'response.npz'),
                'points_sha256':sha256(snap/'points.json'),'state_is_finite_QP_not_gap_qualification':True,
                'minimum_gap_mm':float(audit['minimum'].min()),'gap_tolerance_mm':GAP_TOLERANCE})

            if not len(bad):success=True;break
            if len(points)>=a.max_points+4:break
            candidates=[{'patch':cells[i]['label'],'cell':int(i),'minimum':float(audit['minimum'][i]),
                         'minimum_at':audit['minimum_at'][i].tolist()} for i in bad]
            chosen=select_violations(candidates,seen,maximum_new=min(a.new_points,a.max_points+4-len(points)))
            if not chosen:
                dump(out/'no-new-witness.json',{'passed':False,'negative_cells':len(bad)});break
            newpts=[{'kind':'contact','patch':x['patch'],'cell':x['cell'],'xy':x['minimum_at'],
                     'gap':cells[x['cell']]['gap'],'reason':'bounded-balanced-negative-quadratic-extremum'} for x in chosen]
            newC=hstack([point_column(p) for p in newpts],format='csc')
            cache.append(newC)
            points.extend(newpts)
            for p in newpts:seen[p['patch']].append(p['xy'])
            G=np.vstack([G,np.asarray(newC.T@R)]);qfree=np.vstack([qfree,np.asarray(newC.T@Uext)])
            initialgap=np.r_[initialgap,[p['gap'] for p in newpts]];oldlam=lam
        if returned is None:
            case_summaries.append({'case':case,'passed':False,'reason':'no accepted finite QP field'});break
        lam,rigid,u,applied,q,audit,usedpoints=returned;m=len(lam)
        physical={};balance=[]
        for name,offset in [('panel',0),('frame',npanel)]:
            b=bodies[name];nn=b['K'].shape[0];uu=u[offset:offset+nn];ff=applied[offset:offset+nn]
            res=b['K']@uu-ff;resfree=float(np.max(abs(res[b['free']])));reaction=float(np.max(abs(res[b['D']])))
            en=float(.5*uu@(b['K']@uu));work=float(.5*uu@ff);err=abs(en-work)/max(abs(en),abs(work),1e-20)
            assert resfree<1e-9 and (name!='panel' or reaction<1e-9) and err<1e-5
            ext=ff.copy()
            if name=='frame':ext[b['D']]+=res[b['D']]
            axes=[b['data']['axis'+str(i)] for i in range(3)]
            xyz=b['data']['xyz'][:,axes[0]].T;nodal=np.stack([ext[ix] for ix in axes],axis=1)
            balance.append(np.r_[nodal.sum(axis=0),np.cross(xyz,nodal).sum(axis=0)])
            physical[name]={'free_residual_max':resfree,'gauge_or_fixture_reaction_max':reaction,'energy_work_relative_error':err}
        assert np.max(abs(np.sum(balance,axis=0)))<1e-8
        pointgaps=np.array([p['gap'] for p in usedpoints[4:]])-np.asarray(cache.C[:,:m].T@u).ravel()[4:]
        complementarity=float(np.max(abs(lam[4:]*pointgaps)))
        assert pointgaps.min()>-GAP_TOLERANCE and complementarity<1e-11
        branch=bool(lam[:4].min()>=-1e-10)
        report={'case':case,'load_index':j,'force_over_Epanel_mm2':force,'spring_initial_over_Epanel_mm2':pre,
                'spring_compliance_times_Epanel_per_mm':5.,'Epanel_over_Eframe':1.,'nu':.3,
                'contact_points':usedpoints,'forces':lam.tolist(),'rigid':rigid.tolist(),'qp':q,'history':history,
                'audited_cells':5255,'minimum_gap_mm':float(audit['minimum'].min()),
                'all_original_cells_nonpenetrating':success,'bolt_tension_branch_valid':branch,
                'full_field_checks':physical,'input_sha256':hashes,'source_sha256':sha256(Path(__file__)),
                'minimum_enforced_point_gap':float(pointgaps.min()),'contact_complementarity_max':complementarity,
                'whole_field_reconstructed_by_one_exact_response':True,
                'independent_tetra_verifier_rerun':False,'FE_mesh_convergence':False,'point_contact_convergence':False,
                'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'passed':success and branch}
        dump(out/'report.json',report)
        np.savez_compressed(out/'full-fields.npz',up=u[:npanel],uf=u[npanel:],load_panel=applied[:npanel],
                            load_frame=applied[npanel:],lambda_forces=lam,rigid=rigid)
        dump(out/'gap-extrema.json',{k:v for k,v in audit.items()})
        case_summaries.append({k:report[k] for k in ['case','passed','minimum_gap_mm','audited_cells']})
        oldlam=lam.copy()
        # A failed case is saved explicitly; subsequent work is not called done.
        if not report['passed']:break
    np.savez_compressed(a.output/'exact-response-system.npz',H=cache.H,G=G,qfree=qfree,initialgap=initialgap,loadG=loadG)
    dump(a.output/'contact-point-locations.json',points)
    for p,h in hashes.items():assert sha256(Path(p))==h
    dump(a.output/'SUMMARY.json',{'requested_cases':a.cases,'cases':case_summaries,
        'all_requested_passed':len(case_summaries)==len(a.cases) and all(x['passed'] for x in case_summaries),
        'independent_full_model_validation_still_required':True,'input_sha256':hashes,
        'gap_tolerance_mm':GAP_TOLERANCE,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False})
    return all(x['passed'] for x in case_summaries) and len(case_summaries)==len(a.cases)

if __name__=='__main__':
    raise SystemExit(0 if main(arguments()) else 1)
