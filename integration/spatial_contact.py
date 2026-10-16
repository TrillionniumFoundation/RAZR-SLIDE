"""Finite-dimensional unilateral contact by an equality-constrained convex dual.

Each contact row is a particular spatial evaluation, NOT a patch mean. The
caller must audit gaps between points and enrich the discretization if needed.
Multipliers are discrete normal reactions, not a resolved continuum pressure
or stress field. Four/other tensile-only springs may slack; no artificial
rigid support, penalty stiffness, material or service-load default is added.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import linprog


def real_array(x, shape, name):
    raw=np.asarray(x)
    if raw.dtype.kind not in 'fiu' or raw.dtype.kind=='b':
        raise ValueError(name+': finite real nonboolean values required')
    a=np.asarray(x,dtype=float)
    if a.shape!=shape or not np.isfinite(a).all():
        raise ValueError(name+': invalid dimensions or nonfinite values')
    return a


def solve_reactions(H,G,free_displacement,rigid_resultant,bolt_compliance,
                    spring_initial_force,contact_gaps,*,warm_start=None,
                    tolerance=1e-10,max_iterations=4000):
    """Solve min(.5*l*S*l-d*l), G.T*l=load, l>=0 using a working set.

    q=q_free-H*l+G*r. For a positive spring force l=P0+q/c; a
    zero-force spring has q+c*P0<=0. Contacts have l>=0,g-q>=0,
    l*(g-q)=0. The frame/panel pressure and displacement operators must be
    energy-conjugate. Missing rigid modes remain explicit and may reject load.
    H can be semidefinite, but numerical solve failure is never a pass.
    """
    if type(max_iterations) is not int or max_iterations<1:
        raise ValueError('positive integer iteration bound required')
    if type(tolerance) not in (int,float) or not np.isfinite(tolerance) or not 0<tolerance<1e-4:
        raise ValueError('invalid numerical tolerance')
    raw=np.asarray(H)
    if raw.ndim!=2 or raw.shape[0]!=raw.shape[1] or len(raw)==0:
        raise ValueError('nonempty square compliance required')
    m=len(raw);H=real_array(H,(m,m),'H');gg=np.asarray(G)
    if gg.ndim!=2 or gg.shape[0]!=m:raise ValueError('rigid map shape')
    nr=gg.shape[1];G=real_array(G,(m,nr),'G')
    q0=real_array(free_displacement,(m,),'free_displacement')
    load=real_array(rigid_resultant,(nr,),'rigid_resultant')
    bc=np.asarray(bolt_compliance)
    if bc.ndim!=1 or len(bc)>m:raise ValueError('one compliance per spring')
    nb=len(bc);bc=real_array(bc,(nb,),'bolt_compliance')
    pre=real_array(spring_initial_force,(nb,),'spring_initial_force')
    gaps=real_array(contact_gaps,(m-nb,),'contact_gaps')
    if (bc<=0).any() or (pre<0).any() or (gaps<0).any():
        raise ValueError('positive spring compliance; nonnegative initial force/gaps')
    scale=max(float(np.max(np.abs(H))),float(np.max(bc)) if nb else 0.)
    if scale<1e-20:scale=1.  # Numerical normalization only; H remains zero.
    if np.max(abs(H-H.T))>1e-8*scale:raise ValueError('nonreciprocal compliance')
    H=(H+H.T)/2
    if np.linalg.eigvalsh(H).min() < -1e-9*scale:raise ValueError('negative compliance energy')
    S=H.copy();S[np.arange(nb),np.arange(nb)]+=bc
    d=q0.copy();d[:nb]+=bc*pre;d[nb:]-=gaps
    force_scale=max(float(np.max(abs(load))) if nr else 0.,float(np.max(pre)) if nb else 0.,float(np.max(abs(q0)))/scale,1e-15)
    position_scale=scale*force_scale
    Sn=S/scale;dn=d/position_scale
    if nr:
        _,sing,Vh=np.linalg.svd(G,full_matrices=True)
        rank=int(np.sum(sing>1e-11*max(sing[0] if len(sing) else 0.,1e-30)))
        Q=Vh[:rank].T;B=G@Q;target=Q.T@load/force_scale
        null_load=load-Q@(Q.T@load)
    else:rank=0;Q=np.zeros((0,0));B=G.copy();target=load;null_load=load
    base={'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
          'discrete_point_reactions_not_continuum_contact_pressure':True,
          'unrestrained_rigid_modes':int(nr-rank),'iterations':0}
    if nr and np.max(abs(null_load))>1e-9*force_scale:
        return {**base,'passed':False,'status':'unsupported_rigid_load'}
    x=None
    if warm_start is not None:
        w=real_array(warm_start,(m,),'warm_start')/force_scale
        if w.min()>=-tolerance and (not rank or np.max(abs(B.T@w-target))<1e-8):x=np.maximum(w,0)
    if x is None:
        feasible=linprog(np.ones(m),A_eq=B.T if rank else None,b_eq=target if rank else None,
                         bounds=(0,None),method='highs')
        if not feasible.success:return {**base,'passed':False,'status':'no_nonnegative_force_balance'}
        x=feasible.x
    active=set(np.flatnonzero(x>1e-13));active.update(range(nb))
    history=[];rred=np.zeros(rank)
    for it in range(max_iterations):
        ix=np.array(sorted(active),dtype=int);n=len(ix)
        M=np.block([[Sn[np.ix_(ix,ix)],-B[ix]],[B[ix].T,np.zeros((rank,rank))]])
        rhs=np.r_[dn[ix],target]
        sol,_,_,_=np.linalg.lstsq(M,rhs,rcond=1e-13) if M.size else (np.empty(0),None,None,None)
        err=float(np.max(abs(M@sol-rhs))) if len(rhs) else 0.
        if err>1e-7*max(float(np.max(abs(rhs))) if len(rhs) else 0.,1.):
            return {**base,'passed':False,'status':'working_set_numerical_residual','iterations':it,'residual':err}
        goal=np.zeros(m);goal[ix]=sol[:n];rred=sol[n:]
        bad=[i for i in ix if goal[i]<-tolerance]
        if bad:
            fractions=[(x[i]/(x[i]-goal[i]),int(i)) for i in bad if x[i]-goal[i]>0]
            if not fractions:return {**base,'passed':False,'status':'invalid_feasible_direction','iterations':it}
            alpha,block=min(fractions);alpha=max(0.,min(1.,alpha));x+=alpha*(goal-x);x[block]=0.;active.remove(block)
            history.append(('drop',block));continue
        x=np.maximum(goal,0.);w=Sn@x-dn-B@rred
        inactive=np.array(sorted(set(range(m))-active),dtype=int)
        if len(inactive) and float(w[inactive].min()) < -tolerance:
            add=int(inactive[np.argmin(w[inactive])]);active.add(add);history.append(('add',add));continue
        lam=x*force_scale;r=Q@rred*position_scale
        q=q0-H@lam+G@r;remaining=gaps-q[nb:]
        dual=S@lam-d-G@r;eq=G.T@lam-load
        error_scale=max(position_scale,1e-15)
        feasible_gap=float(np.min(dual))>=-max(2e-9*error_scale,1e-13)
        complementarity=float(np.max(abs(lam*dual)))
        passed=bool(feasible_gap and (not nr or np.max(abs(eq))<=1e-8*force_scale)
                    and complementarity<=1e-8*force_scale*error_scale)
        return {**base,'passed':passed,'status':'discrete_equilibrium' if passed else 'final_KKT_failed',
                'iterations':it+1,'forces':lam.tolist(),'bolt_forces':lam[:nb].tolist(),
                'contact_forces':lam[nb:].tolist(),'rigid_coordinates':r.tolist(),
                'relative_displacements':q.tolist(),'remaining_contact_gaps':remaining.tolist(),
                'spring_constitutive_slacks':dual[:nb].tolist(),'slack_springs':[int(i) for i in range(nb) if lam[i]<=1e-12*force_scale],
                'equilibrium_residual':eq.tolist(),'dual_slack_minimum':float(np.min(dual)),
                'complementarity_maximum':complementarity,
                'working_set_changes':len(history),'force_scale':force_scale,'position_scale':position_scale,
                'between_point_gap_audit_required':True}
    return {**base,'passed':False,'status':'iteration_limit','iterations':max_iterations}
