"""Extrema of a quadratic FE gap on common planar triangle polygons.

This audits a supplied small-displacement field. It does not solve contact,
assign physical loads, or turn a sampled/average condition into full contact
qualification. Extrema are analytic candidates evaluated in floating point,
not certified interval-arithmetic error bounds.
"""
from __future__ import annotations
import numpy as np


def finite_array(value, shape, name):
    a = np.asarray(value)
    if a.dtype.kind not in 'fiu' or a.shape != shape or not np.isfinite(a).all():
        raise ValueError(name + ': finite real array with shape ' + str(shape) + ' required')
    return a.astype(float)


def linear_product(a, b):
    """Coefficients ordered as 1, x, y, x*x, x*y, y*y."""
    a = finite_array(a, (3,), 'first affine polynomial')
    b = finite_array(b, (3,), 'second affine polynomial')
    return np.array([a[0]*b[0], a[0]*b[1]+a[1]*b[0], a[0]*b[2]+a[2]*b[0],
                     a[1]*b[1], a[1]*b[2]+a[2]*b[1], a[2]*b[2]])


def triangle_coefficients(vertices, values, origin=(0., 0.)):
    """Interpolate six P2 nodes: v0,v1,v2,mid01,mid12,mid20.

    Coefficients are in coordinates relative to the supplied common origin.
    Values may be shape (6,) or (6, number_of_fields).
    """
    xy = finite_array(vertices, (3, 2), 'triangle')
    o = finite_array(origin, (2,), 'origin')
    v = np.asarray(values)
    if v.ndim not in (1, 2) or v.shape[0] != 6 or v.dtype.kind not in 'fiu' or not np.isfinite(v).all():
        raise ValueError('six finite nodal values per field required')
    edges = xy[1:] - xy[0]
    area2 = np.linalg.det(edges)
    scale = np.max(abs(edges))
    if scale == 0 or abs(area2) <= 1e-13 * scale**2:
        raise ValueError('degenerate or numerically singular triangle')
    bary = np.linalg.inv(np.column_stack([np.ones(3), xy-o])).T
    shapes = []
    for li in bary:
        q = 2*linear_product(li, li); q[:3] -= li; shapes.append(q)
    for i,j in ((0,1),(1,2),(2,0)):
        shapes.append(4*linear_product(bary[i],bary[j]))
    out = np.array(shapes).T @ v.astype(float)
    if not np.isfinite(out).all(): raise ValueError('nonfinite polynomial reconstruction')
    return out


def evaluate(coefficients, points, origin=(0., 0.)):
    c = np.asarray(coefficients); p = np.asarray(points)
    if c.ndim not in (1,2) or c.shape[0] != 6 or c.dtype.kind not in 'fiu' or not np.isfinite(c).all():
        raise ValueError('six finite coefficients required')
    if p.ndim != 2 or p.shape[1] != 2 or p.dtype.kind not in 'fiu' or not np.isfinite(p).all():
        raise ValueError('finite two-dimensional points required')
    o = finite_array(origin, (2,), 'origin'); x,y=(p-o).T
    return np.column_stack([np.ones(len(p)),x,y,x*x,x*y,y*y]) @ c


def convex_vertices(vertices):
    v = np.asarray(vertices)
    if v.ndim != 2 or v.shape[1] != 2 or len(v)<3 or v.dtype.kind not in 'fiu' or not np.isfinite(v).all():
        raise ValueError('finite convex polygon vertices required')
    v=v.astype(float)
    if np.array_equal(v[0],v[-1]):v=v[:-1]
    if len(v)<3:raise ValueError('empty polygon')
    e=np.roll(v,-1,axis=0)-v; scale=np.max(abs(e))
    if scale==0 or (np.linalg.norm(e,axis=1)==0).any():raise ValueError('repeated polygon vertex')
    area2=np.sum((v[:,0]-v[0,0])*(np.roll(v,-1,axis=0)[:,1]-v[0,1])-(v[:,1]-v[0,1])*(np.roll(v,-1,axis=0)[:,0]-v[0,0]))
    if abs(area2)<=1e-14*scale**2:raise ValueError('degenerate polygon')
    if area2<0:v=v[::-1];e=np.roll(v,-1,axis=0)-v
    for a,edge in zip(v,e):
        d=v-a;cross=edge[0]*d[:,1]-edge[1]*d[:,0]
        if cross.min() < -1e-11*scale**2:raise ValueError('polygon must be convex and ordered')
    return v


def extrema(coefficients, vertices, origin=(0.,0.)):
    """All vertex, edge-stationary and feasible interior-stationary candidates."""
    c=finite_array(coefficients,(6,),'quadratic');o=finite_array(origin,(2,),'origin')
    v=convex_vertices(vertices);loc=v-o;points=list(loc);kinds=['vertex']*len(loc)
    A=np.array([[c[3],.5*c[4]],[.5*c[4],c[5]]]);b=c[1:3]
    for p,q in zip(loc,np.roll(loc,-1,axis=0)):
        d=q-p;aa=float(d@A@d);bb=float((2*A@p+b)@d)
        if aa!=0:
            t=-bb/(2*aa)
            if 0<t<1:points.append(p+t*d);kinds.append('edge_stationary')
    ev=np.linalg.eigvalsh(A)
    if min(abs(ev)) > 1e-13*max(max(abs(ev)),1e-300):
        s=np.linalg.solve(2*A,-b);edges=np.roll(loc,-1,axis=0)-loc
        cross=edges[:,0]*(s-loc)[:,1]-edges[:,1]*(s-loc)[:,0]
        if cross.min()>=-1e-12*max(np.max(abs(edges))**2,1e-300):
            points.append(s);kinds.append('interior_stationary')
    coords=np.array(points)+o;vals=evaluate(c,coords,o);lo=int(vals.argmin());hi=int(vals.argmax())
    return {'minimum':float(vals[lo]),'maximum':float(vals[hi]),
            'minimum_at':coords[lo].tolist(),'maximum_at':coords[hi].tolist(),
            'minimum_kind':kinds[lo],'maximum_kind':kinds[hi],
            'candidate_count':len(points),'floating_point_not_interval_certificate':True}


def gap_status(minimum, maximum, *, tolerance_mm, compressive_force=0., force_tolerance=0.):
    """Never declare physical acceptance from this numerical contact audit."""
    vals=finite_array([minimum,maximum,tolerance_mm,compressive_force,force_tolerance],(5,),'gap status')
    lo,hi,tol,force,ftol=vals
    if lo>hi or min(tol,force,ftol)<0:raise ValueError('invalid gap range/tolerance/force')
    penetration=lo < -tol
    loaded_opening=force>ftol and hi>tol
    return {'nonpenetration_satisfied':not penetration,
            'loaded_patch_zero_gap_satisfied':not loaded_opening,
            'resolved_contact_compatible_on_audited_domain':not(penetration or loaded_opening),
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
