"""Residual-checked rank-revealing QR for a failed active linear system.

The full matrix and RHS are unchanged. QR and SVD have different numerical
rank estimators at the same cutoff; agreement is to be checked on actual
systems and complete QP/KKT results, never inferred from this helper alone.
No diagonal regularization or constraint removal is performed.
"""
from __future__ import annotations
import numpy as np
from scipy.linalg import lstsq as scipy_lstsq

def solve_rank_fallback(matrix,rhs,*,residual_limit,cutoff=1e-13):
    A=np.asarray(matrix);b=np.asarray(rhs)
    if A.ndim!=2 or b.ndim!=1 or A.shape[0]!=len(b) or not min(A.shape):
        raise ValueError('nonempty matrix and compatible vector required')
    if A.dtype.kind not in 'fiu' or b.dtype.kind not in 'fiu' or not np.isfinite(A).all() or not np.isfinite(b).all():
        raise ValueError('finite real non-boolean data required')
    for name,value in [('residual_limit',residual_limit),('cutoff',cutoff)]:
        if type(value) not in (int,float) or not np.isfinite(value) or value<=0:
            raise ValueError(name+' must be positive and finite')
    if cutoff>=1:raise ValueError('cutoff must be below one')
    A=A.astype(float,copy=False);b=b.astype(float,copy=False);rejected=None
    try:
        x,_,rank,_=scipy_lstsq(A,b,cond=cutoff,lapack_driver='gelsy',check_finite=True)
        residual=float(np.max(np.abs(A@x-b)))
        if not np.isfinite(x).all() or not np.isfinite(residual) or residual>residual_limit:
            raise np.linalg.LinAlgError('QR did not satisfy original full residual')
        driver='gelsy'
    except (np.linalg.LinAlgError,ValueError) as exc:
        rejected=str(exc)
        x,_,rank,_=np.linalg.lstsq(A,b,rcond=cutoff)
        residual=float(np.max(np.abs(A@x-b)));driver='numpy_gelsd'
        if not np.isfinite(x).all() or not np.isfinite(residual):
            raise np.linalg.LinAlgError('nonfinite least-squares fallback')
    return x,{'driver':driver,'rank':int(rank),'rows':A.shape[0],'columns':A.shape[1],
              'cutoff':float(cutoff),'residual_max':residual,'residual_limit':float(residual_limit),
              'residual_passed':bool(residual<=residual_limit),'qr_rejection':rejected,
              'regularization_added':False,'constraints_removed':False}
