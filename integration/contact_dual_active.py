"""Convex complementary-energy QP for an exact elastic response oracle.

S is a complementary-energy Hessian of generalized interface forces, NOT a
primal displacement stiffness. The oracle must come from full elastic K
solves or exact condensation. Its compliance is not the previous prescribed
12-port contact approximation. Equality equations preserve rigid equilibrium.
Only contact variables are nonnegative; any tensile-only bolt branch must be
checked by the caller. No diagonal regularization is used.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import linprog
from scipy.linalg import solve, LinAlgWarning
import warnings


def _a(x,dim,name):
    a=np.asarray(x)
    if a.ndim!=dim or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError(name+': finite real non-boolean array required')
    return a.astype(float)


def solve_force_qp(S,d,G,load,free_prefix=4,initial=None,tolerance=2e-10,max_iterations=5000):
    """Min .5*l*S*l-d*l, G.T*l=load, l[free_prefix:]>=0.

    Uses a feasible working-set method. Negative reactions release a contact;
    a negative reduced gradient admits a previously open contact. Numerical
    gauges are not introduced into the elastic energy or equilibrium rows.
    """
    S=_a(S,2,'S');d=_a(d,1,'d');G=_a(G,2,'G');load=_a(load,1,'load');m=len(d)
    if not m or S.shape!=(m,m) or G.shape!=(m,len(load)):raise ValueError('inconsistent dimensions')
    if type(free_prefix) is not int or not 0<=free_prefix<=m:raise ValueError('invalid free prefix')
    if type(tolerance) not in (int,float) or not 0<tolerance<1e-4:raise ValueError('invalid tolerance')
    if type(max_iterations) is not int or max_iterations<1:raise ValueError('invalid iteration cap')
    diag=np.diag(S);mx=np.max(abs(S))
    if (diag<=0).any() or np.max(abs(S-S.T))>1e-9*max(mx,1e-300):raise ValueError('nonpositive or nonreciprocal response')
    Q=(S+S.T)/2;sc=1/np.sqrt(diag);Q=sc[:,None]*Q*sc[None,:]
    if np.linalg.eigvalsh(Q).min()<-1e-8:raise ValueError('negative complementary energy mode')
    scale=max(np.max(abs(sc*d)),np.max(abs(load),initial=0.),1e-15)
    p=sc*d/scale;ER=G.T*sc[None,:];rhs=load/scale
    if len(load):
        U,s,_=np.linalg.svd(ER,full_matrices=True);rank=int(np.sum(s>1e-11*max(s.max(initial=0.),1e-300)))
        unsupported=U[:,rank:].T@rhs
        if np.linalg.norm(unsupported)>tolerance*max(np.linalg.norm(rhs),1.):
            return {'passed':False,'status':'unsupported_rigid_load','missing_rigid_directions':len(load)-rank}
        reduced=U[:,:rank].T;E=reduced@ER;b=reduced@rhs
        eqscale=np.maximum(np.max(abs(E),axis=1),1e-300) if rank else np.empty(0)
        E=E/eqscale[:,None];b=b/eqscale
    else:rank=0;reduced=np.zeros((0,0));eqscale=np.empty(0);E=np.zeros((0,m));b=np.empty(0)
    x=None
    if initial is not None:
        v=_a(initial,1,'initial')
        if v.shape!=(m,):raise ValueError('initial dimension differs')
        v=v/(sc*scale)
        if np.min(v[free_prefix:],initial=0.)>=-tolerance and np.max(abs(E@v-b),initial=0.)<tolerance:x=v.copy()
    if x is None:
        result=linprog(np.r_[np.zeros(free_prefix),np.ones(m-free_prefix)],A_eq=E if rank else None,b_eq=b if rank else None,
                       bounds=[(None,None)]*free_prefix+[(0,None)]*(m-free_prefix),method='highs',
                       options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
        if not result.success:return {'passed':False,'status':'no_feasible_support','lp_status':int(result.status)}
        x=result.x
    F=list(range(free_prefix))+[i for i in range(free_prefix,m) if x[i]>tolerance]
    history=[];status='iteration_limit';nu=np.zeros(rank)
    for iteration in range(max_iterations):
        FF=np.array(F,dtype=int);EF=E[:,FF]
        A=np.block([[Q[np.ix_(FF,FF)],-EF.T],[EF,np.zeros((rank,rank))]])
        rr=np.r_[p[FF],b]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',LinAlgWarning);sol=solve(A,rr,assume_a='gen',check_finite=False)
            err=np.max(abs(A@sol-rr),initial=0.)
            if err>tolerance*10*max(np.max(abs(rr),initial=0.),1.):raise np.linalg.LinAlgError('working-set residual')
        except (np.linalg.LinAlgError,LinAlgWarning):
            sol,_,_,_=np.linalg.lstsq(A,rr,rcond=1e-13)
            if np.max(abs(A@sol-rr),initial=0.)>tolerance*10*max(np.max(abs(rr),initial=0.),1.):
                return {'passed':False,'status':'dependent_working_set','iterations':iteration+1,'history':history}
        trial=np.zeros(m);trial[FF]=sol[:len(F)];nu=sol[len(F):]
        neg=[i for i in F if i>=free_prefix and trial[i]<-tolerance]
        if neg:
            step=min((max(x[i],0.)/(x[i]-trial[i]),i) for i in neg)
            alpha,j=step;x=x+alpha*(trial-x);x[j]=0.;F.remove(j)
            history.append({'iteration':iteration,'release':int(j),'alpha':float(alpha),'free':len(F)});continue
        x=trial;gradient=Q@x-p-E.T@nu
        outside=[i for i in range(free_prefix,m) if i not in F]
        j=min(outside,key=lambda j:gradient[j]) if outside else None
        if j is None or gradient[j]>=-tolerance*max(np.max(abs(p),initial=0.),1.):status='optimal';break
        F.append(j);history.append({'iteration':iteration,'admit':int(j),'free':len(F)})
    lam=x*sc*scale
    rigid=(reduced.T@(nu/eqscale))*scale if rank else np.zeros(len(load))
    grad=S@lam-d-G@rigid
    force_scale=max(np.max(abs(lam),initial=0.),1e-15)
    disp_scale=max(np.max(abs(d),initial=0.),np.max(abs(S@lam),initial=0.),1e-15)
    errors={'equilibrium':float(np.max(abs(G.T@lam-load),initial=0.)),
            'free_stationarity':float(np.max(abs(grad[:free_prefix]),initial=0.)),
            'negative_contact_force':float(max(0.,-np.min(lam[free_prefix:],initial=0.))),
            'negative_reduced_gradient':float(max(0.,-np.min(grad[free_prefix:],initial=0.))),
            'complementarity':float(np.max(abs(lam[free_prefix:]*grad[free_prefix:]),initial=0.))}
    passed=status=='optimal' and errors['equilibrium']<=1e-7*max(np.max(abs(load),initial=0.),force_scale) and errors['negative_contact_force']<=1e-7*force_scale and errors['negative_reduced_gradient']<=1e-7*disp_scale and errors['free_stationarity']<=1e-7*disp_scale and errors['complementarity']<=1e-7*force_scale*disp_scale
    return {'passed':bool(passed),'status':status if passed else 'numerical_'+status,'forces':lam.tolist(),
            'rigid_mode_coordinates':rigid.tolist(),'reduced_gradient':grad.tolist(),'iterations':iteration+1,
            'remaining_unsupported_rigid_directions':int(len(load)-rank),'errors':errors,'history':history,
            'force_space_complementary_energy_not_primal_stiffness':True,'regularization_added':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
