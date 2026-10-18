from pathlib import Path
import sys,json,time,hashlib
import numpy as np
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-schur-20261018');O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
sys.path.insert(0,str(R/'integration'));from contact_dual_active import solve_force_qp
p=O/'assembly-fallback.npz';meta=json.loads((O/'assembly-fallback.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['system_sha256'];z=dict(np.load(p,allow_pickle=False))
initial=z['x']*z['sc']*meta['scale'];start=time.monotonic()
print('CAPTURED_ASSEMBLY_QP_START',len(z['d']),flush=True)
r=solve_force_qp(z['S'],z['d'],z['G'],z['load'],initial=initial,factor_reuse=True,rank_fallback='qr_pivot')
r['seconds']=time.monotonic()-start;r['captured_system_sha256']=meta['system_sha256'];r['source_commit']='26539a79b953bdd0b6978551f13c3361f13853b6'
(O/'assembly-captured-qp-result.json').write_text(json.dumps(r,indent=2)+'\n')
assert r['passed'],r['status']
lam=np.array(r['forces']);rigid=np.array(r['rigid_mode_coordinates']);gradient=z['S']@lam-z['d']-z['G']@rigid
fs=max(abs(lam).max(),1e-15);ds=max(abs(z['d']).max(),abs(z['S']@lam).max(),1e-15)
checks={'equilibrium':float(np.max(abs(z['G'].T@lam-z['load']))),'stationarity_bolts':float(np.max(abs(gradient[:4]))),'min_force_contact':float(lam[4:].min()),'min_gradient_contact':float(gradient[4:].min()),'complementarity':float(np.max(abs(lam[4:]*gradient[4:])))}
assert checks['equilibrium']<=1e-7*max(np.max(abs(z['load'])),fs)
assert checks['stationarity_bolts']<=1e-7*ds and checks['min_force_contact']>=-1e-7*fs and checks['min_gradient_contact']>=-1e-7*ds and checks['complementarity']<=1e-7*fs*ds
(O/'assembly-captured-independent-kkt.json').write_text(json.dumps({'passed':True,'checks':checks,'same_original_KKT_limits':True,'not_a_fullfield_pass':True},indent=2)+'\n')
print('CAPTURED_ASSEMBLY_QP_PASSED',r['iterations'],r['seconds'],r['factor_reuse_counts'],checks,flush=True)
