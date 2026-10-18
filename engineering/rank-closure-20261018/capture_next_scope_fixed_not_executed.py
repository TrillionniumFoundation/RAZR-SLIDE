"""Capture the next actual rank event after replaying six completed fields.
Does not patch a running process, delete a contact, or claim a solved field.
"""
from pathlib import Path
import ast,hashlib,inspect,json,sys
import numpy as np
from scipy.sparse import hstack,save_npz
R=Path('/home/qian-qi/RAZR-SLIDE-rank-pivot-20261018')
B=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-replay-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/rank-followup-20261018')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
identity=json.loads((O/'input-identity.json').read_text())
for p,h in identity.items():assert sha(p)==h
sys.path.insert(0,str(R/'integration'));import rank_fallback as rf
class Captured(BaseException):pass
original=rf.release_dependent_force

def capture(A,Q,E,p,b,x,active,**kw):
    caller=inspect.currentframe().f_back;assert caller.f_code.co_name=='solve_force_qp'
    L=caller.f_locals;arrays={'A':A,'Q':Q,'E':E,'p':p,'b':b,'x':x,'FF':np.asarray(active)}
    for key in ('S','d','G','load','sc','reduced','eqscale','rr'):arrays[key]=np.asarray(L[key])
    target=O/'next-fallback.npz';assert not target.exists();np.savez_compressed(target,**arrays)
    meta={'shape':list(A.shape),'iteration':int(L['iteration']),'total_force_variables':len(x),'working_forces':len(active),
          'rank_equalities':int(L['rank']),'free_prefix':L['free_prefix'],'scale':float(L['scale']),
          'solver_tolerance':L['tolerance'],'capture_only':True,'input_sha256':identity,
          'system_sha256':sha(target),'script_sha256':sha(__file__),
          'all_original_constraints_retained':True,'source_core_unmodified':True}
    (O/'next-fallback.json').write_text(json.dumps(meta,indent=2)+'\n')
    for f,h in identity.items():assert sha(f)==h
    print('ACTUAL_NEXT_RANK_EVENT_CAPTURED',meta['shape'],meta['iteration'],meta['system_sha256'],flush=True)
    raise Captured()
rf.release_dependent_force=capture
source=(R/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text()
marker='    history=[];success=False\n    for iteration in range(a.max_exchanges):'
replay="    replay_rows=[]\n    for origin in [REPLAY_EVIDENCE_ROOT/'pr32-before-fix/p256-t020',REPLAY_EVIDENCE_ROOT/'strict256-v2']:\n        for prior_iteration in range(3):\n            field=origin/f'field-{prior_iteration:03d}.npz';gf=origin/f'gaps-{prior_iteration:03d}.json'\n            prior=np.load(field,allow_pickle=False);prior_gap=json.loads(gf.read_text())\n            assert len(prior['forces'])==len(points)\n            expected=external-np.asarray(cache.C@prior['forces']).ravel()\n            assert np.max(abs(expected-prior['applied']))<1e-12\n            checked=audit(prior['u'])\n            assert np.array_equal(checked['negative_cells'],np.asarray(prior_gap['negative_cells']))\n            assert np.max(abs(checked['minimum']-np.asarray(prior_gap['minimum'])))<1e-12\n            bad=checked['negative_cells']\n            chosen=select_violations([{'patch':cells[i]['label'],'cell':int(i),'minimum':float(checked['minimum'][i]),'minimum_at':checked['minimum_at'][i].tolist()} for i in bad],seen,maximum_new=min(128,a.max_points+4-len(points)))\n            newpoints=[{'kind':'contact','cell':q['cell'],'patch':q['patch'],'xy':q['minimum_at'],'gap':cells[q['cell']]['gap']} for q in chosen]\n            nc=hstack([one_map(q) for q in newpoints],format='csc');cache.append(nc);points.extend(newpoints)\n            for q in newpoints:seen[q['patch']].append(q['xy'])\n            G=np.vstack([G,np.asarray(nc.T@R)]);qfree=np.r_[qfree,np.asarray(nc.T@Uext).ravel()];initialgap=np.r_[initialgap,[q['gap'] for q in newpoints]];old=prior['forces'].copy()\n            replay_rows.append({'source':str(origin),'exchange':prior_iteration,'field_contacts':len(prior['forces'])-4,'next_contacts':len(points)-4,'full_load_and_all_gap_regions_checked':True})\n            print('REPLAY_NEXT',replay_rows[-1],flush=True)\n    dump(out/'replay-identity.json',replay_rows);dump(out/'replayed-points.json',points)\n    history=[];success=False\n    for iteration in range(a.max_exchanges):"
assert source.count(marker)==1;source=source.replace(marker,replay);ast.parse(source)
(O/'executed-capture-driver.py').write_text(source)
sys.argv=[str(R/'engineering/trace-enrichment-20261017/solve_trace_probe.py'),
 '--volume','/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3',
 '--state','/home/qian-qi/.local/share/razr-slide-evidence/nested-contact-20261017/level-2/final-case7-state',
 '--output',str(O/'reconstructed-next'),'--surface-loads',str(R/'engineering/consistent-load-20261017/projection-256'),
 '--surface-load-mode','consistent','--load-face-cap','2','--faces-per-patch','4',
 '--frozen-selection',str(R/'engineering/joint-sensitivity-20261017/frozen-selection.json'),
 '--case','6','--gap-tolerance','2e-8','--rank-fallback','qr_pivot','--max-exchanges','1','--max-points','6500']
try:exec(compile(source,str(O/'executed-capture-driver.py'),'exec'),{'__name__':'__main__','__file__':sys.argv[0],'REPLAY_EVIDENCE_ROOT':B})
except Captured:print('CAPTURE_ONLY_TERMINAL_NOT_A_FIELD_PASS',flush=True)
finally:rf.release_dependent_force=original
