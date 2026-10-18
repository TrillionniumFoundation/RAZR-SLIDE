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


def release_dependent_force(A,Q,E,p,b,x,active,*,free_prefix,tolerance,cutoff=1e-13):
    """Propose a feasible, non-increasing null-direction working-set pivot.

    Only a force that reaches zero leaves the WORKING set. Its original
    unilateral constraint stays in the QP and is eligible for re-admission.
    Null actions are verified against the FULL Hessian/equality rows. A
    failed candidate falls back to ordinary rank-revealing least squares.
    """
    from scipy.linalg import qr,solve_triangular
    A=np.asarray(A,dtype=float);Q=np.asarray(Q,dtype=float);E=np.asarray(E,dtype=float)
    p=np.asarray(p,dtype=float);b=np.asarray(b,dtype=float);x=np.asarray(x,dtype=float);F=np.asarray(active,dtype=int)
    n=len(F);failure={'accepted':False,'constraints_removed':False,'regularization_added':False}
    if A.shape!=(n+len(b),n+len(b)) or Q.shape!=(len(x),len(x)) or E.shape!=(len(b),len(x)) or len(p)!=len(x):raise ValueError('incompatible rank-pivot dimensions')
    if type(free_prefix) is not int or not 0<=free_prefix<=len(x) or len(set(F))!=len(F) or np.any(F<0) or np.any(F>=len(x)):raise ValueError('invalid rank-pivot indices')
    if any(not np.isfinite(a).all() for a in (A,Q,E,p,b,x)) or type(tolerance) not in (int,float) or not np.isfinite(tolerance) or tolerance<=0:raise ValueError('invalid rank-pivot inputs')
    limit=tolerance*10*max(float(np.max(abs(b),initial=0.)),1.)
    if np.min(x[free_prefix:],initial=0.)<-tolerance or np.max(abs(E@x-b),initial=0.)>limit:return {**failure,'reason':'initial_not_feasible'}
    _,R,piv=qr(A,mode='economic',pivoting=True,check_finite=False)
    diag=np.abs(np.diag(R));threshold=cutoff*max(float(diag.max(initial=0.)),1e-300)
    deficient=np.flatnonzero(diag<=threshold);rank=int(deficient[0]) if len(deficient) else len(A)
    if rank==len(A):return {**failure,'reason':'no_numerical_null_direction','rank':rank}
    if rank==0:return {**failure,'reason':'zero_rank_system','rank':rank}
    gradient=Q@x-p;proposals=[]
    for column in range(rank,min(len(A),rank+4)):
        v=np.zeros(len(A));v[piv[column]]=1.
        try:v[piv[:rank]]=solve_triangular(R[:rank,:rank],-R[:rank,column],check_finite=False)
        except np.linalg.LinAlgError:continue
        w=v[:n];norm=float(np.max(abs(w),initial=0.))
        if norm<=1e-14:continue
        w=w/norm
        qnull=float(np.max(abs(Q[:,F]@w),initial=0.));enull=float(np.max(abs(E[:,F]@w),initial=0.))
        null_limit=tolerance*10*max(float(np.max(abs(Q),initial=0.)),1.)
        if qnull>null_limit or enull>tolerance*10:continue
        for sign in (1.,-1.):
            direction=sign*w
            choices=[(max(float(x[j]),0.)/-float(direction[k]),k) for k,j in enumerate(F) if j>=free_prefix and direction[k]<-1e-14]
            if not choices:continue
            alpha,k=min(choices);trial=x.copy();trial[F]+=alpha*direction;trial[F[k]]=0.;delta=trial-x
            eqerr=float(np.max(abs(E@trial-b),initial=0.));qchange=float(np.max(abs(Q@delta),initial=0.))
            objchange=float(gradient@delta+.5*delta@(Q@delta))
            allowance=64*np.finfo(float).eps*max(1.,float(np.linalg.norm(gradient)*np.linalg.norm(delta)),float(np.linalg.norm(delta)*np.linalg.norm(Q@delta)))
            if not np.isfinite(trial).all() or np.min(trial[free_prefix:],initial=0.)<-tolerance or eqerr>limit or objchange>allowance:continue
            proposals.append((objchange,int(F[k]),trial,{'accepted':True,'release':int(F[k]),'rank':rank,'dimension':len(A),'null_Q_max':qnull,'null_E_max':enull,'scaled_equality_residual':eqerr,'full_Hessian_action_change':qchange,'objective_change':objchange,'objective_roundoff_allowance':allowance,'step':float(alpha),'constraints_removed':False,'regularization_added':False}))
    if not proposals:return {**failure,'reason':'no_verified_feasible_pivot','rank':rank}
    _,_,trial,record=min(proposals,key=lambda row:(row[0],row[1]));return {**record,'scaled_forces':trial}
