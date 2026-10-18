"""First captured real KKT system: QR versus unchanged NumPy SVD fallback."""
from pathlib import Path
import json,hashlib,time
import numpy as np
import scipy
from scipy.linalg import lstsq
O=Path('/tmp/razr-rank-replay-20261018');inp=O/'capture256/fallback-system.npz';meta=json.loads((O/'capture256/capture.json').read_text());assert hashlib.sha256(inp.read_bytes()).hexdigest()==meta['system_sha256']
z=np.load(inp,allow_pickle=False);A=z['A'];b=z['rhs'];cut=meta['rcond'];results={};solutions={}
for method in ['gelsy','numpy_gelsd']:
 start=time.monotonic()
 if method=='gelsy':x,res,rank,s=lstsq(A,b,cond=cut,lapack_driver='gelsy',check_finite=True)
 else:x,res,rank,s=np.linalg.lstsq(A,b,rcond=cut)
 elapsed=time.monotonic()-start;residual=A@x-b;rr={'seconds':elapsed,'rank':int(rank),'rows':A.shape[0],'columns':A.shape[1],'rcond':cut,'residual_max':float(np.max(abs(residual))),'residual_2norm':float(np.linalg.norm(residual)),'solution_norm':float(np.linalg.norm(x)),'original_residual_limit':meta['solver_tolerance']*10*max(float(np.max(abs(b))),1.)}
 if s is not None:rr['singular_extremes']=[float(s[0]),float(s[-1])];rr['singular_values_below_cutoff']=int(np.sum(s<=cut*s[0]))
 results[method]=rr;solutions[method]=x
 (O/'rank-method-progress.json').write_text(json.dumps(results,indent=2)+'\n');np.savez_compressed(O/(method+'-solution.npz'),x=x)
 print('RANK_METHOD',method,rr,flush=True)
delta=solutions['gelsy']-solutions['numpy_gelsd'];nf=len(z['FF']);E=z['E'];Q=z['Q'];ix=z['FF']
comparison={'same_effective_rank':results['gelsy']['rank']==results['numpy_gelsd']['rank'],'solution_max_difference':float(np.max(abs(delta))),'solution_relative_norm_difference':float(np.linalg.norm(delta)/max(np.linalg.norm(solutions['numpy_gelsd']),1e-300)),'full_A_delta_max':float(np.max(abs(A@delta))),'working_force_energy_of_difference':float(delta[:nf]@Q[np.ix_(ix,ix)]@delta[:nf]),'equality_delta_max':float(np.max(abs(E[:,ix]@delta[:nf]),initial=0.))}
result={'methods':results,'comparison':comparison,'input_sha256':meta['system_sha256'],'captured_context':{k:meta[k] for k in ['shape','iteration','rank_equalities','free_prefix','scale','solver_tolerance']},'numpy':np.__version__,'scipy':scipy.__version__,'no_KKT_or_full_field_pass_inferred':True}
assert all(r['residual_max']<=r['original_residual_limit'] for r in results.values())
assert hashlib.sha256(inp.read_bytes()).hexdigest()==meta['system_sha256']
(O/'rank-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print('COMPARISON',comparison,flush=True)
