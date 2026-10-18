"""Identity-checked continuation of archived exchange fields on the existing driver.

This is an executed research wrapper, not a resumed OS process. No old failed
field is accepted as equilibrium; full original constraints and gap checks run.
"""
from pathlib import Path
import sys,argparse,hashlib,ast,json,time
import numpy as np
P=argparse.ArgumentParser(add_help=False);P.add_argument('--replay-source',type=Path,required=True);P.add_argument('--warm-qp',type=Path)
args,rest=P.parse_known_args()
ROOT=Path('/home/qian-qi/RAZR-SLIDE-rank-pivot-20261018');OUT=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018/current')
expected={'p256-t020':'6bdb9a643db534cec9ac35102a2f40efd15e7c519dee1eb5e6da0b1e1df3229a','p512-t020':'ae80412ee7c0b094da5a146285103530e4169c3beea7e081880322a09fbb64c0'}
assert hashlib.sha256((args.replay_source/'field-002.npz').read_bytes()).hexdigest()==expected[args.replay_source.name]
sys.path.insert(0,str(ROOT/'integration'));import rank_fallback as rf
real=rf.release_dependent_force;log=[]
def observe(*a,**k):
 t=time.monotonic();r=real(*a,**k);z={key:val for key,val in r.items() if key!='scaled_forces'};log.append({'seconds':time.monotonic()-t,**z})
 print('RANK_PIVOT',len(log),z,flush=True);return r
rf.release_dependent_force=observe
source=(ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text()
replacement="    replay_hashes={};replayed=[]\n    reference=Path(REPLAY_SOURCE)\n    for prior_iteration in range(3):\n        field=reference/f'field-{prior_iteration:03d}.npz';gapfile=reference/f'gaps-{prior_iteration:03d}.json'\n        prior=np.load(field,allow_pickle=False);prior_gap=json.loads(gapfile.read_text())\n        replay_hashes[str(field)]=sha256(field);replay_hashes[str(gapfile)]=sha256(gapfile)\n        assert len(prior['forces'])==len(points)\n        # Exact identity of the force maps must reconstruct the retained full load.\n        expected=external-np.asarray(cache.C@prior['forces']).ravel()\n        assert np.max(abs(expected-prior['applied']))<1e-12\n        # Independently re-evaluate all regions before recovering new constraints.\n        checked=audit(prior['u'])\n        assert np.array_equal(checked['negative_cells'],np.array(prior_gap['negative_cells']))\n        assert np.max(abs(checked['minimum']-np.array(prior_gap['minimum'])))<1e-12\n        bad=checked['negative_cells']\n        chosen=select_violations([{'patch':cells[i]['label'],'cell':int(i),'minimum':float(checked['minimum'][i]),'minimum_at':checked['minimum_at'][i].tolist()} for i in bad],seen,maximum_new=min(128,a.max_points+4-len(points)))\n        newpoints=[{'kind':'contact','cell':p['cell'],'patch':p['patch'],'xy':p['minimum_at'],'gap':cells[p['cell']]['gap']} for p in chosen]\n        nc=hstack([one_map(p) for p in newpoints],format='csc');cache.append(nc);points.extend(newpoints)\n        for p in newpoints:seen[p['patch']].append(p['xy'])\n        G=np.vstack([G,np.asarray(nc.T@R)]);qfree=np.r_[qfree,np.asarray(nc.T@Uext).ravel()];initialgap=np.r_[initialgap,[p['gap'] for p in newpoints]];old=prior['forces'].copy()\n        replayed.append({'prior_exchange':prior_iteration,'field_contacts':len(prior['forces'])-4,'added_points':len(newpoints),'rebuilt_contacts':len(points)-4,'full_load_identity_checked':True,'all_gap_regions_rechecked':True})\n        print('REPLAYED_EXCHANGE',replayed[-1],flush=True)\n    hashes.update(replay_hashes)\n    dump(out/'reconstructed-checkpoint.json',{'sources':replay_hashes,'replayed':replayed,'all_new_responses_recomputed_with_complete_augmented_energy':True,'previous_fields_only_optimizer_initial_guesses':True})\n    dump(out/'reconstructed-points.json',points)\n    save_npz(out/'reconstructed-C.npz',cache.C)\n    np.savez_compressed(out/'reconstructed-response.npz',H=cache.H)\n    hashes[WRAPPER_PATH]=sha256(WRAPPER_PATH)\n    if WARM_QP_PATH is not None:\n        warm=json.loads(Path(WARM_QP_PATH).read_text());assert warm['passed']\n        saved=np.load(CAPTURED_QP_PATH,allow_pickle=False)\n        assert sha256(CAPTURED_QP_PATH)==warm['captured_source_sha256']\n        ss=cache.H.copy();ss[np.arange(4),np.arange(4)]+=5.\n        dd=qfree-initialgap;dd[:4]+=5.*2e-4\n        assert np.array_equal(ss,saved['S']) and np.array_equal(dd,saved['d']) and np.array_equal(G,saved['G']) and np.array_equal(loadG,saved['load'])\n        old=np.array(warm['forces']);assert len(old)==len(points)\n        hashes[WARM_QP_PATH]=sha256(WARM_QP_PATH);hashes[CAPTURED_QP_PATH]=sha256(CAPTURED_QP_PATH)\n        dump(out/'warm-qp-identity.json',{'full_S_d_G_load_byte_arrays_equal':True,'initial_only_full_KKT_resolve_required':True,'warm_source':WARM_QP_PATH})\n    history=[];success=False\n    for iteration in range(a.max_exchanges):"
marker='    history=[];success=False\n    for iteration in range(a.max_exchanges):'
assert source.count(marker)==1;source=source.replace(marker,replacement)
ast.parse(source)
record=OUT/(args.replay_source.name+'-executed-replay-driver-v2.py');record.write_text(source)
sys.argv=[str(ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py'),*rest]
ns={'__name__':'__main__','__file__':sys.argv[0],'REPLAY_SOURCE':str(args.replay_source),'WARM_QP_PATH':str(args.warm_qp) if args.warm_qp else None,'CAPTURED_QP_PATH':str(OUT/'capture256/fallback-system.npz'),'WRAPPER_PATH':str(Path(__file__).resolve())}
exec(compile(source,str(record),'exec'),ns)
