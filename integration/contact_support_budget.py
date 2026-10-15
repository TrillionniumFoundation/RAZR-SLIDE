"""Couple finite elastic response ports with axial springs and unilateral stops.

This is a reduced, prescribed-pressure contact model, not a resolved local
contact mesh or hardware qualification. H is the two bodies' relative port
compliance; G maps explicitly free rigid modes. Contact gaps are not erased.
Bolts remain on a tension-positive linear spring branch with supplied preload.
No stiffness, preload, material or service force default is provided.
"""
from itertools import combinations
import math
import numpy as np


def array(value,shape,name):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.dtype.kind=='b':
        raise ValueError(name+': real, non-boolean array required')
    out=np.asarray(value,dtype=float)
    if out.shape!=shape or not np.isfinite(out).all():
        raise ValueError(name+': finite array with shape '+str(shape)+' required')
    return out


def solve_support(H,G,free_displacement,rigid_resultant,bolt_compliance,
                  bolt_preload,contact_gaps,*,relative_tolerance=2e-8):
    """Solve all small active contact sets without fixing otherwise free modes.

    q=q_free-H*lambda+G*r. First b forces obey lambda=P0+q/compliance;
    remaining forces are compressive only and q<=gap. G.T*lambda equals
    the external rigid-mode resultant. Compliance and preload are per bolt,
    not a rule that divides applied load equally. Inactive rigid modes retain
    their nonuniqueness; the reported representative is a minimum-norm gauge.
    """
    if type(relative_tolerance) not in (int,float) or not math.isfinite(relative_tolerance) or not 0<relative_tolerance<1e-3:
        raise ValueError('invalid numerical tolerance')
    raw=np.asarray(H)
    if raw.ndim!=2 or raw.shape[0]!=raw.shape[1] or raw.shape[0]==0:
        raise ValueError('square nonempty relative compliance required')
    m=raw.shape[0];H=array(H,(m,m),'H')
    rawG=np.asarray(G)
    if rawG.ndim!=2 or rawG.shape[0]!=m:raise ValueError('rigid map shape differs')
    nr=rawG.shape[1];G=array(G,(m,nr),'G')
    q0=array(free_displacement,(m,),'free displacement');load=array(rigid_resultant,(nr,),'rigid resultant')
    bc=np.asarray(bolt_compliance)
    if bc.ndim!=1:raise ValueError('one compliance per bolt required')
    nb=len(bc);nc=m-nb
    if nc<0 or nc>12:raise ValueError('bounded solver supports at most twelve contact ports')
    bc=array(bc,(nb,),'bolt compliance');pre=array(bolt_preload,(nb,),'bolt preload');gaps=array(contact_gaps,(nc,),'contact gaps')
    if (bc<=0).any() or (pre<0).any() or (gaps<0).any():raise ValueError('positive spring compliance and nonnegative preload/gaps required')
    scale=max(float(np.max(abs(H))),float(np.max(bc)) if nb else 0.)
    if scale<1e-20:scale=1.  # Numerical scale only; does not add physical stiffness.
    if np.max(abs(H-H.T))>relative_tolerance*scale:raise ValueError('nonreciprocal compliance')
    H=(H+H.T)/2
    if np.linalg.eigvalsh(H).min() < -relative_tolerance*scale:raise ValueError('negative elastic compliance mode')
    S=H.copy();S[np.arange(nb),np.arange(nb)]+=bc
    d=q0.copy();d[:nb]+=bc*pre;d[nb:]-=gaps
    force_scale=max(float(np.max(abs(load))) if nr else 0.,float(np.max(pre)) if nb else 0.,float(np.max(abs(d)))/scale,1e-12)
    displacement_scale=scale*force_scale
    candidates=[];checks=0
    for count in range(nc+1):
        for active in combinations(range(nc),count):
            selected=np.array(list(range(nb))+[nb+i for i in active],dtype=int);n=len(selected);checks+=1
            SS=S[np.ix_(selected,selected)]/scale;GG=G[selected]
            A=np.block([[SS,-GG],[GG.T,np.zeros((nr,nr))]])
            rhs=np.r_[d[selected]/displacement_scale,load/force_scale]
            if A.size:
                solution,_,rank,_=np.linalg.lstsq(A,rhs,rcond=1e-13)
                error=np.max(abs(A@solution-rhs)) if len(rhs) else 0.
            else:solution=np.empty(0);rank=0;error=0.
            if error>relative_tolerance*max(1.,np.max(abs(rhs)) if len(rhs) else 0.):continue
            lam=np.zeros(m);lam[selected]=solution[:n]*force_scale;r=solution[n:]*displacement_scale
            q=q0-H@lam+G@r;remaining=gaps-q[nb:]
            force_error=relative_tolerance*force_scale;position_error=relative_tolerance*max(displacement_scale,np.max(abs(gaps)) if nc else 0.,1e-12)
            if (lam < -force_error).any() or (remaining < -position_error).any():continue
            if nb and np.max(abs(lam[:nb]-pre-q[:nb]/bc))>force_error*10:continue
            if active and np.max(abs(remaining[list(active)]))>position_error:continue
            eq=G.T@lam-load
            if nr and np.max(abs(eq))>force_error*10:continue
            energy=.5*lam@S@lam-d@lam
            candidates.append((float(energy),lam,r,q,remaining,tuple(active),int(n+nr-rank)))
    base={'scope':'prescribed finite pressure ports, tension-positive axial springs and unilateral normal gaps',
          'contact_sets_examined':checks,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
          'local_contact_pressure_and_pointwise_nonpenetration_not_solved':True,
          'no_material_or_preload_or_load_sharing_assigned':True}
    if not candidates:return {**base,'status':'no_admissible_reduced_equilibrium','passed':False}
    _,lam,r,q,left,active,nullity=min(candidates,key=lambda x:x[0])
    rankG=np.linalg.matrix_rank(G,tol=relative_tolerance*max(1.,float(np.max(abs(G))) if G.size else 0.)) if nr else 0
    return {**base,'status':'conditional_reduced_equilibrium','passed':True,'forces':lam.tolist(),
            'bolt_forces':lam[:nb].tolist(),'contact_forces':lam[nb:].tolist(),
            'relative_port_displacements':q.tolist(),'remaining_contact_gaps':left.tolist(),
            'rigid_mode_coordinates':r.tolist(),'active_contact_indices':list(active),
            'equilibrium_residual':(G.T@lam-load).tolist(),'unrestrained_global_rigid_modes':int(nr-rankG),
            'selected_active_system_nullity':nullity,'minimum_norm_rigid_representative_not_unique_fixture':nullity>0,
            'maximum_complementarity_product':float(np.max(abs(lam[nb:]*left))) if nc else 0.}
