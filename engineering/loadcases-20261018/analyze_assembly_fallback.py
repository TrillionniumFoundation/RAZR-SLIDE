"""Analyze a captured active system without changing any field or constraint."""
from pathlib import Path
import hashlib,json,time
import numpy as np
from scipy.linalg import cholesky,solve_triangular,lstsq
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
p=O/'assembly-fallback.npz';meta=json.loads((O/'assembly-fallback.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['system_sha256']
z=dict(np.load(p,allow_pickle=False));A=z['A'];rr=z['rr'];F=z['FF'];Q=z['Q'];E=z['E'];b=z['b'];pr=z['p']
EF=E[:,F];sv=np.linalg.svd(EF,compute_uv=False)
r={'input_sha256':meta['system_sha256'],'shape':list(A.shape),'active_forces':len(F),'equalities':len(b),
 'active_equality_singular_values':sv.tolist(),'active_equality_rank_estimate':int(np.sum(sv>1e-11*sv.max(initial=1e-300))),
 'full_field_not_solved_by_this_diagnostic':True,'source_constraints_unchanged':True}
start=time.monotonic()
try:
 L=cholesky(Q[np.ix_(F,F)],lower=True,check_finite=True)
 t=solve_triangular(L,pr[F],lower=True);W=solve_triangular(L,EF.T,lower=True)
 schur=W.T@W;rhs=b-W.T@t
 nu,_,rank,_=lstsq(schur,rhs,cond=1e-13,lapack_driver='gelsy')
 force=solve_triangular(L.T,t+W@nu,lower=False)
 sol=np.r_[force,nu];res=float(np.max(abs(A@sol-rr)))
 r.update(active_force_block_positive_definite=True,schur_eigenvalues=np.linalg.eigvalsh(schur).tolist(),small_schur_rank=int(rank),
          small_solve_seconds=time.monotonic()-start,full_original_residual=res,
          full_original_residual_limit=meta['tolerance']*10*max(float(np.max(abs(rr),initial=0)),1.),
          linear_solution_not_complete_QP=True)
 np.savez_compressed(O/'assembly-small-schur-candidate.npz',solution=sol)
except np.linalg.LinAlgError as exc:r.update(active_force_block_positive_definite=False,reason=str(exc),seconds=time.monotonic()-start)
(O/'assembly-rank-analysis.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
print('ACTUAL_ASSEMBLY_RANK_ANALYSIS',json.dumps(r),flush=True)
