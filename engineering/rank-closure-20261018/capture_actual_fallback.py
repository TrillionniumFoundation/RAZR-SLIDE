"""Capture actual first least-squares fallback after identity-checked exchange replay.
No linear solver replacement or full physical pass is performed by this diagnostic.
"""
from pathlib import Path
import sys,json,hashlib,inspect,ast,time
import numpy as np
from scipy.sparse import save_npz
R=Path('/home/qian-qi/RAZR-SLIDE-rank-replay-20261018')
O=Path('/tmp/razr-rank-replay-20261018/capture256');O.mkdir(exist_ok=False)
sys.path.insert(0,str(R/'integration'))
import contact_dual_active as core
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'integration/contact_dual_active.py')=='33e37725f5d3937c8e0559116a2fc76f8c27316d4a4d347fa741951e028dc98e'
assert sha('/tmp/razr-joint-sensitivity-fast-20261017/p256-t020/field-002.npz')=='6bdb9a643db534cec9ac35102a2f40efd15e7c519dee1eb5e6da0b1e1df3229a'
original_lstsq=core.np.linalg.lstsq
class Captured(BaseException):pass
def capture(a,b,rcond=None):
    caller=inspect.currentframe().f_back
    if caller.f_code.co_name!='solve_force_qp':return original_lstsq(a,b,rcond=rcond)
    L=caller.f_locals;arrays={'A':a,'rhs':b}
    for k in ('S','d','G','load','Q','p','E','b','x','FF','sc','reduced','eqscale'):
        if k in L:arrays[k]=np.asarray(L[k])
    np.savez_compressed(O/'fallback-system.npz',**arrays)
    record={'capture_only':True,'shape':list(a.shape),'rcond':rcond,'iteration':L.get('iteration'),
        'free_prefix':L.get('free_prefix'),'rank_equalities':L.get('rank'),'scale':L.get('scale'),
        'solver_tolerance':L.get('tolerance'),'working_set':list(L['F']),
        'source_core_sha256':sha(R/'integration/contact_dual_active.py'),
        'diagnostic_sha256':sha(__file__),'system_sha256':sha(O/'fallback-system.npz'),
        'no_candidate_linear_solution_computed':True}
    (O/'capture.json').write_text(json.dumps(record,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else v,allow_nan=False)+'\n')
    print('ACTUAL_FALLBACK_CAPTURED',record['shape'],record['iteration'],record['system_sha256'],flush=True)
    raise Captured()
core.np.linalg.lstsq=capture
source=(R/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text()

marker='    history=[];success=False\n    for iteration in range(a.max_exchanges):'
replacement="    replay_hashes={};replayed=[]\n    reference=Path('/tmp/razr-joint-sensitivity-fast-20261017/p256-t020')\n    for prior_iteration in range(3):\n        field=reference/f'field-{prior_iteration:03d}.npz';gapfile=reference/f'gaps-{prior_iteration:03d}.json'\n        prior=np.load(field,allow_pickle=False);prior_gap=json.loads(gapfile.read_text())\n        replay_hashes[str(field)]=sha256(field);replay_hashes[str(gapfile)]=sha256(gapfile)\n        assert len(prior['forces'])==len(points)\n        # Exact identity of the force maps must reconstruct the retained full load.\n        expected=external-np.asarray(cache.C@prior['forces']).ravel()\n        assert np.max(abs(expected-prior['applied']))<1e-12\n        # Independently re-evaluate all regions before recovering new constraints.\n        checked=audit(prior['u'])\n        assert np.array_equal(checked['negative_cells'],np.array(prior_gap['negative_cells']))\n        assert np.max(abs(checked['minimum']-np.array(prior_gap['minimum'])))<1e-12\n        bad=checked['negative_cells']\n        chosen=select_violations([{'patch':cells[i]['label'],'cell':int(i),'minimum':float(checked['minimum'][i]),'minimum_at':checked['minimum_at'][i].tolist()} for i in bad],seen,maximum_new=min(128,a.max_points+4-len(points)))\n        newpoints=[{'kind':'contact','cell':p['cell'],'patch':p['patch'],'xy':p['minimum_at'],'gap':cells[p['cell']]['gap']} for p in chosen]\n        nc=hstack([one_map(p) for p in newpoints],format='csc');cache.append(nc);points.extend(newpoints)\n        for p in newpoints:seen[p['patch']].append(p['xy'])\n        G=np.vstack([G,np.asarray(nc.T@R)]);qfree=np.r_[qfree,np.asarray(nc.T@Uext).ravel()];initialgap=np.r_[initialgap,[p['gap'] for p in newpoints]];old=prior['forces'].copy()\n        replayed.append({'prior_exchange':prior_iteration,'field_contacts':len(prior['forces'])-4,'added_points':len(newpoints),'rebuilt_contacts':len(points)-4,'full_load_identity_checked':True,'all_gap_regions_rechecked':True})\n        print('REPLAYED_EXCHANGE',replayed[-1],flush=True)\n    hashes.update(replay_hashes)\n    dump(out/'reconstructed-checkpoint.json',{'sources':replay_hashes,'replayed':replayed,'all_new_responses_recomputed_with_complete_augmented_energy':True,'previous_fields_only_optimizer_initial_guesses':True})\n    dump(out/'reconstructed-points.json',points)\n    save_npz(out/'reconstructed-C.npz',cache.C)\n    np.savez_compressed(out/'reconstructed-response.npz',H=cache.H)\n    history=[];success=False\n    for iteration in range(a.max_exchanges):"
assert source.count(marker)==1
source=source.replace(marker,replacement)
(O/'actual-replay-driver.py').write_text(source);ast.parse(source)
ns={'__name__':'__main__','__file__':str(R/'engineering/trace-enrichment-20261017/solve_trace_probe.py')}
try:exec(compile(source,str(O/'actual-replay-driver.py'),'exec'),ns)
except Captured:print('CAPTURE_COMPLETE_NO_FIELD_PASS',flush=True)
finally:core.np.linalg.lstsq=original_lstsq
