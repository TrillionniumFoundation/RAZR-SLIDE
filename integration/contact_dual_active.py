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
from scipy.linalg import solve, LinAlgWarning, cholesky, solve_triangular
import warnings


def _a(x,dim,name):
    a=np.asarray(x)
    if a.ndim!=dim or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError(name+': finite real non-boolean array required')
    return a.astype(float)


class _WorkingFactor:
    def __init__(self):
        self.indices=None;self.L=None;self.T=None
        self.counts={'refactor':0,'append':0,'delete':0,'fallback':0}
    def _factor(self,Q,indices,p,E):
        ids=tuple(int(i) for i in indices)
        if self.indices==ids and self.L is not None:return
        old=self.indices;L=self.L;T=self.T;built=None;newT=None
        if old is not None and L is not None and len(ids)==len(old)+1 and ids[:-1]==old:
            w=solve_triangular(L,Q[np.asarray(old,dtype=int),ids[-1]],lower=True,check_finite=False)
            diag=float(Q[ids[-1],ids[-1]]-w@w)
            if diag>1e-13*max(abs(Q[ids[-1],ids[-1]]),1e-300):
                root=np.sqrt(diag);built=np.zeros((len(ids),len(ids)));built[:-1,:-1]=L;built[-1,:-1]=w;built[-1,-1]=root
                row=(np.r_[p[ids[-1]],E[:,ids[-1]]]-w@T)/root
                newT=np.vstack([T,row]);self.counts['append']+=1
        elif old is not None and L is not None and len(ids)==len(old)-1:
            k=next((i for i in range(len(ids)) if ids[i]!=old[i]),len(ids))
            if old[:k]+old[k+1:]==ids:
                U=np.array(np.delete(L.T,k,axis=1),order='C');W=T.copy()
                for j in range(k,len(ids)):
                    a,b=U[j,j],U[j+1,j];norm=np.hypot(a,b)
                    if norm==0:raise np.linalg.LinAlgError('singular factor deletion')
                    c,s=a/norm,b/norm;row=U[j,j:].copy();other=U[j+1,j:].copy()
                    U[j,j:]=c*row+s*other;U[j+1,j:]=-s*row+c*other
                    row=W[j].copy();other=W[j+1].copy();W[j]=c*row+s*other;W[j+1]=-s*row+c*other
                built=np.array(U[:-1,:].T,order='F');newT=W[:-1].copy();self.counts['delete']+=1
        if built is None:
            built=cholesky(Q[np.ix_(ids,ids)],lower=True,check_finite=False)
            newT=solve_triangular(built,np.column_stack([p[list(ids)],E[:,list(ids)].T]),lower=True,check_finite=False)
            self.counts['refactor']+=1
        self.indices=ids;self.L=built;self.T=newT
    def solve(self,Q,indices,E,p,b,tolerance,A,rhs):
        try:
            self._factor(Q,indices,p,E);t=self.T[:,0];W=self.T[:,1:]
            if len(b):
                schur=W.T@W
                with warnings.catch_warnings():
                    warnings.simplefilter('error',LinAlgWarning)
                    nu=solve(schur,b-W.T@t,assume_a='sym',check_finite=False)
            else:nu=np.empty(0)
            x=solve_triangular(self.L.T,t+W@nu,lower=False,check_finite=False)
            result=np.r_[x,nu]
            if not np.isfinite(result).all() or np.max(abs(A@result-rhs),initial=0.)>tolerance*10*max(np.max(abs(rhs),initial=0.),1.):
                raise np.linalg.LinAlgError('updated active-system residual')
            return result
        except (np.linalg.LinAlgError,LinAlgWarning,ValueError):
            self.indices=None;self.L=None;self.T=None;self.counts['fallback']+=1
            with warnings.catch_warnings():
                warnings.simplefilter('error',LinAlgWarning)
                return solve(A,rhs,assume_a='gen',check_finite=False)


def solve_force_qp(S,d,G,load,free_prefix=4,initial=None,tolerance=2e-10,max_iterations=5000, factor_reuse=False, rank_fallback='svd'):
    """Min .5*l*S*l-d*l, G.T*l=load, l[free_prefix:]>=0.

    Uses a feasible working-set method. Negative reactions release a contact;
    a negative reduced gradient admits a previously open contact. Numerical
    gauges are not introduced into the elastic energy or equilibrium rows.
    """
    if type(factor_reuse) is not bool:raise ValueError('factor_reuse must be boolean')
    if type(rank_fallback) is not str or rank_fallback not in ('svd','qr'):raise ValueError('rank_fallback must be svd or qr')
    rank_diagnostics=[]
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
    history=[];status='iteration_limit';nu=np.zeros(rank);factor_cache=_WorkingFactor() if factor_reuse else None
    for iteration in range(max_iterations):
        FF=np.array(F,dtype=int);EF=E[:,FF]
        A=np.block([[Q[np.ix_(FF,FF)],-EF.T],[EF,np.zeros((rank,rank))]])
        rr=np.r_[p[FF],b]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',LinAlgWarning);sol=factor_cache.solve(Q,FF,E,p,b,tolerance,A,rr) if factor_reuse else solve(A,rr,assume_a='gen',check_finite=False)
            err=np.max(abs(A@sol-rr),initial=0.)
            if err>tolerance*10*max(np.max(abs(rr),initial=0.),1.):raise np.linalg.LinAlgError('working-set residual')
        except (np.linalg.LinAlgError,LinAlgWarning):
            if rank_fallback=='qr':
                from rank_fallback import solve_rank_fallback
                sol,rank_record=solve_rank_fallback(A,rr,cutoff=1e-13,
                    residual_limit=tolerance*10*max(float(np.max(abs(rr),initial=0.)),1.))
                rank_diagnostics.append({'iteration':iteration,**rank_record})
            else:
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
        members=set(F)
        outside=[i for i in range(free_prefix,m) if i not in members]
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
            'force_space_complementary_energy_not_primal_stiffness':True,'regularization_added':False,'factor_reuse_enabled':factor_reuse,
            'factor_reuse_counts':factor_cache.counts if factor_reuse else {},
            **({'rank_revealing_fallback':True,'rank_fallback_records':rank_diagnostics} if rank_fallback=='qr' else {}),
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
