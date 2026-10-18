"""Capture the first actual unloaded-assembly working-system fallback.
Original fields, working constraints and numerical tolerances are unmodified.
"""
from pathlib import Path
import ast,hashlib,inspect,json,sys
import numpy as np
ROOT=Path('/home/qian-qi/RAZR-SLIDE-loadcases-20261018')
OUT=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
identity=json.loads((OUT/'assembly-capture-inputs.json').read_text())
for p,h in identity.items():assert sha(p)==h
sys.path.insert(0,str(ROOT/'integration'));import rank_fallback as rf
class Captured(BaseException):pass
original=rf.release_dependent_force
def capture(A,Q,E,p,b,x,active,**kw):
    caller=inspect.currentframe().f_back;assert caller.f_code.co_name=='solve_force_qp';L=caller.f_locals
    arrays={key:np.asarray(L[key]) for key in ['S','d','G','load','Q','E','p','b','x','FF','sc','reduced','eqscale','rr']}
    arrays['A']=A
    f=OUT/'assembly-fallback.npz';assert not f.exists();np.savez_compressed(f,**arrays)
    meta={'capture_only':True,'matrix_shape':list(A.shape),'total_force_variables':len(x),'iteration':L['iteration'],
          'active_indices':list(L['F']),'rank_equalities':L['rank'],'scale':L['scale'],'tolerance':L['tolerance'],
          'source_sha256':identity,'system_sha256':sha(f),'diagnostic_sha256':sha(__file__),
          'actual_model_not_synthetic':True,'no_new_contact_or_stiffness_constraint':True}
    (OUT/'assembly-fallback.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n')
    print('ASSEMBLY_ACTUAL_FALLBACK_CAPTURED',meta['matrix_shape'],meta['iteration'],flush=True)
    raise Captured()
rf.release_dependent_force=capture
source=(ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py').read_text()
marker='    history=[];success=False\n    for iteration in range(a.max_exchanges):'
replay="""    prior=np.load(ASSEMBLY_REPLAY_ROOT/'assembly-reference/field-000.npz',allow_pickle=False)
    prior_gap=json.loads((ASSEMBLY_REPLAY_ROOT/'assembly-reference/gaps-000.json').read_text())
    assert len(prior['forces'])==len(points)
    expected=external-np.asarray(cache.C@prior['forces']).ravel()
    assert np.max(abs(expected-prior['applied']))<1e-12
    checked=audit(prior['u'])
    assert np.array_equal(checked['negative_cells'],np.array(prior_gap['negative_cells']))
    assert np.max(abs(checked['minimum']-np.array(prior_gap['minimum'])))<1e-12
    bad=checked['negative_cells']
    picked=select_violations([{'patch':cells[i]['label'],'cell':int(i),'minimum':float(checked['minimum'][i]),'minimum_at':checked['minimum_at'][i].tolist()} for i in bad],seen,maximum_new=min(128,a.max_points+4-len(points)))
    newpoints=[{'kind':'contact','cell':p['cell'],'patch':p['patch'],'xy':p['minimum_at'],'gap':cells[p['cell']]['gap']} for p in picked]
    nc=hstack([one_map(p) for p in newpoints],format='csc');cache.append(nc);points.extend(newpoints)
    for p in newpoints:seen[p['patch']].append(p['xy'])
    G=np.vstack([G,np.asarray(nc.T@R)]);qfree=np.r_[qfree,np.asarray(nc.T@Uext).ravel()];initialgap=np.r_[initialgap,[p['gap'] for p in newpoints]];old=prior['forces'].copy()
    dump(out/'replayed-points.json',points)
    print('ASSEMBLY_REPLAY_IDENTICAL',len(points)-4,flush=True)
    history=[];success=False
    for iteration in range(a.max_exchanges):"""
assert source.count(marker)==1;source=source.replace(marker,replay);ast.parse(source)
(OUT/'assembly-executed-capture.py').write_text(source)
command=json.loads((OUT/'assembly-reference-command.json').read_text())
args=command[command.index(str(ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py'))+1:]
args[args.index('--output')+1]=str(OUT/'assembly-capture-replay')
sys.argv=[str(ROOT/'engineering/trace-enrichment-20261017/solve_trace_probe.py'),*args]
try:exec(compile(source,str(OUT/'assembly-executed-capture.py'),'exec'),{'__name__':'__main__','__file__':sys.argv[0],'ASSEMBLY_REPLAY_ROOT':OUT})
except Captured:print('CAPTURE_ONLY_COMPLETE_NOT_AN_ASSEMBLY_SOLUTION',flush=True)
finally:rf.release_dependent_force=original
