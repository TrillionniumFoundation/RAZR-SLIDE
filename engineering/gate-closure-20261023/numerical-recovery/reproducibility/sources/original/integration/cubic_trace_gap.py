"""Bounded Bernstein subdivision of a polynomial cubic on convex planar cells.

No P2 interpolation is used to certify a P3 trace. Bernstein convex-hull
bounds cover triangle interiors, not only nodes. The result has explicit
roundoff allowances, but is NOT directed-rounding interval arithmetic or a
continuum error certificate. Exhausted subdivisions return unresolved/failed.
"""
from __future__ import annotations
from math import factorial
import numpy as np
from contact_patch_audit import convex_vertices

INDICES=tuple((i,j,3-i-j) for i in range(3,-1,-1) for j in range(3-i,-1,-1))
LATTICE=np.array(INDICES,dtype=float)/3
VERTEX_IDS=[INDICES.index(t) for t in ((3,0,0),(0,3,0),(0,0,3))]
MULTI=np.array([factorial(3)/(factorial(i)*factorial(j)*factorial(k)) for i,j,k in INDICES])

def bernstein_values(bary):
    a=np.asarray(bary)
    if a.ndim!=2 or a.shape[1]!=3 or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError('finite barycentric points (N,3) required')
    return np.prod(a[:,None,:]**np.array(INDICES)[None,:,:],axis=2)*MULTI

SAMPLES=bernstein_values(LATTICE)
INVERSE=np.linalg.inv(SAMPLES)
CENTRE=bernstein_values(np.ones((1,3))/3)[0]
CHILDREN=np.array([[[1,0,0],[.5,.5,0],[.5,0,.5]],
                  [[.5,.5,0],[0,1,0],[0,.5,.5]],
                  [[.5,0,.5],[0,.5,.5],[0,0,1]],
                  [[.5,.5,0],[0,.5,.5],[.5,0,.5]]],dtype=float)

def _blossom_matrix(corners):
    rows=[]
    for alpha in INDICES:
        table={idx:np.eye(10)[j] for j,idx in enumerate(INDICES)};degree=3
        for corner,multiplicity in zip(corners,alpha):
            for _ in range(multiplicity):
                nxt={}
                for i in range(degree):
                    for j in range(degree-i):
                        idx=(i,j,degree-1-i-j);value=np.zeros(10)
                        for axis in range(3):
                            up=list(idx);up[axis]+=1;value+=corner[axis]*table[tuple(up)]
                        nxt[idx]=value
                table=nxt;degree-=1
        rows.append(table[(0,0,0)])
    return np.array(rows)

SUBDIVISION=np.stack([_blossom_matrix(c) for c in CHILDREN])

def coefficients_from_samples(values):
    a=np.asarray(values)
    if a.shape!=(10,) or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError('ten finite cubic lattice values required')
    c=INVERSE@a
    if not np.isfinite(c).all():raise ValueError('nonfinite cubic coefficients')
    residual=float(np.max(abs(SAMPLES@c-a)))
    guard=2048*np.finfo(float).eps*max(float(np.max(abs(c))),float(np.max(abs(a))),1e-300)+residual
    return c,guard


def audit_polygon(polygon,evaluate,*,gap_tolerance=1e-7,max_depth=16,max_triangles=65536):
    """Check ALL fan triangles; return a violation witness or a covered lower bound.

    ``evaluate`` must be one fixed polynomial of degree <=3 on this polygon.
    It is checked at three additional points but this does not prove that an
    arbitrary callback is cubic. Callers must establish its finite-element form.
    """
    if not callable(evaluate):raise ValueError('polynomial evaluator required')
    if type(gap_tolerance) not in (int,float) or not np.isfinite(gap_tolerance) or gap_tolerance<=0:
        raise ValueError('positive finite gap tolerance required')
    if type(max_depth) is not int or not 0<=max_depth<=24 or type(max_triangles) is not int or max_triangles<1:
        raise ValueError('invalid finite subdivision budget')
    polygon=convex_vertices(polygon)
    stack=[];guardmax=0.;minimum=np.inf;at=None;processed=0;certified=0;lower=np.inf
    for k in range(1,len(polygon)-1):
        triangle=polygon[[0,k,k+1]]
        e1=triangle[1]-triangle[0];e2=triangle[2]-triangle[0]
        area=abs(e1[0]*e2[1]-e1[1]*e2[0])
        if area<=1e-28:continue
        values=np.asarray(evaluate(LATTICE@triangle));c,guard=coefficients_from_samples(values)
        extra=np.array([[.2,.3,.5],[.17,.71,.12],[.41,.08,.51]])
        observed=np.asarray(evaluate(extra@triangle))
        if observed.shape!=(3,) or not np.isfinite(observed).all() or np.max(abs(observed-bernstein_values(extra)@c))>max(guard*8,1e-15):
            raise ValueError('evaluator incompatible with one cubic polynomial')
        stack.append((triangle,c,guard,0));guardmax=max(guardmax,guard)
    if not stack:raise ValueError('nonempty polygon area required')
    while stack:
        triangle,c,guard,depth=stack.pop();processed+=1
        if processed>max_triangles:
            return {'passed':False,'status':'budget_exhausted','minimum_witness':float(minimum),
                    'minimum_at':None if at is None else at.tolist(),'subtriangles':processed,'unresolved':len(stack)+1}
        witnesses=np.r_[c[VERTEX_IDS],CENTRE@c]
        where=np.vstack([triangle,triangle.mean(axis=0)])
        j=int(np.argmin(witnesses))
        if witnesses[j]<minimum:minimum=float(witnesses[j]);at=where[j].copy()
        bound=float(np.min(c)-guard)
        if minimum < -gap_tolerance:
            direct=float(np.asarray(evaluate(at[None,:]))[0])
            if direct < -gap_tolerance:
                return {'passed':False,'status':'negative_witness','minimum_witness':direct,
                        'minimum_at':at.tolist(),'subtriangles':processed,'roundoff_guard_max':guardmax,
                        'strict_zero_or_interval_certificate':False}
        if bound>=-gap_tolerance:
            lower=min(lower,bound);certified+=1;continue
        if depth==max_depth:
            return {'passed':False,'status':'depth_exhausted','minimum_witness':float(minimum),
                    'minimum_at':at.tolist(),'unresolved_lower_bound':bound,'subtriangles':processed,
                    'strict_zero_or_interval_certificate':False}
        childcoeff=np.einsum('kij,j->ki',SUBDIVISION,c)
        childguard=guard+64*np.finfo(float).eps*max(float(np.max(abs(c))),1e-300)
        guardmax=max(guardmax,childguard)
        for child,cc in zip(CHILDREN,childcoeff):
            stack.append((child@triangle,cc,childguard,depth+1))
    return {'passed':True,'status':'all_subtriangles_bounded','covered_lower_bound':lower,
            'minimum_witness':float(minimum),'minimum_at':at.tolist(),'subtriangles':processed,
            'certified_leaf_count':certified,'roundoff_guard_max':guardmax,
            'strict_zero_or_interval_certificate':False}
