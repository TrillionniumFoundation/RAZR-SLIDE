"""Consistent affine traction functionals on explicitly clipped planar triangles.

Positive degree-four-exact quadrature integrates P2 and cubic face work. The
input polygon is the declared domain: a circle represented by an inscribed
polygon is NOT silently treated as the exact circle. These routines assign no
physical pressure, preload or allowable force. Generalized bubble loads are
not extra physical resultant forces. No contact or stiffness is changed here.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from numpy.polynomial.legendre import leggauss


def real(a, ndim, name):
    a=np.asarray(a)
    if a.ndim!=ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError(name+': finite nonboolean real array required')
    return a.astype(float,copy=False)


def cross2(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def triangle(a):
    a=real(a,2,'triangle')
    if a.shape!=(3,2):raise ValueError('three planar vertices required')
    d=a[1:]-a[0];scale=np.max(abs(d))
    if scale==0 or abs(cross2(*d))<=1e-13*scale*scale:
        raise ValueError('degenerate triangle')
    return a


def clip_triangle(vertices, normals, offsets):
    """Sutherland-Hodgman clipping by n dot x <= d; retains real cut edges."""
    p=triangle(vertices).copy();n=real(normals,2,'clip normals');b=real(offsets,1,'clip offsets')
    if n.shape!=(len(b),2) or np.any(np.linalg.norm(n,axis=1)==0):
        raise ValueError('invalid halfplanes')
    for normal,bound in zip(n,b):
        if len(p)<3:return np.empty((0,2))
        value=p@normal-bound;out=[]
        for j,q in enumerate(p):
            previous=p[j-1];va=value[j-1];vb=value[j]
            if (va<=0)!=(vb<=0):out.append(previous+(q-previous)*(va/(va-vb)))
            if vb<=0:out.append(q)
        if not out:return np.empty((0,2))
        p=np.asarray(out);scale=max(float(np.max(np.ptp(p,axis=0))),1e-300)
        # Remove only repeated consecutive vertices generated at existing edges.
        keep=np.linalg.norm(p-np.roll(p,1,axis=0),axis=1)>64*np.finfo(float).eps*scale
        p=p[keep]
    if len(p)<3:return np.empty((0,2))
    if sum(cross2(p[i]-p[0],p[i+1]-p[0]) for i in range(1,len(p)-1))<0:p=p[::-1]
    return p


def circle_halfplanes(center,radius,sides):
    center=real(center,1,'circle center')
    if center.shape!=(2,) or type(radius) not in (int,float) or not np.isfinite(radius) or radius<=0:
        raise ValueError('positive circle radius required')
    if type(sides) is not int or sides<8 or sides>4096:raise ValueError('explicit 8..4096 polygon sides required')
    angle=(2*np.arange(sides)+1)*np.pi/sides;n=np.column_stack((np.cos(angle),np.sin(angle)))
    return n,n@center+radius*np.cos(np.pi/sides)


def polygon_quadrature(polygon, *, order=4):
    """Positive Duffy rule, no quadrature-point mask; straight convex domain."""
    p=real(polygon,2,'polygon')
    if p.shape[1:]!=(2,) or len(p)<3:raise ValueError('nonempty convex polygon required')
    if type(order) is not int or not 3<=order<=12:raise ValueError('quadrature order 3..12 required')
    e=np.roll(p,-1,axis=0)-p;turn=cross2(e,np.roll(e,-1,axis=0))
    if np.any(turn < -1e-12*max(float(np.max(abs(e)))**2,1e-300)):
        raise ValueError('CCW convex polygon required')
    q,w=leggauss(order);q=(q+1)/2;w=w/2
    a,b=np.meshgrid(q,q,indexing='ij');wa,wb=np.meshgrid(w,w,indexing='ij')
    uv=np.column_stack((a.ravel(),((1-a)*b).ravel()));weight=(wa*wb*(1-a)).ravel()
    X=[];W=[]
    for i in range(1,len(p)-1):
        d=np.stack((p[i]-p[0],p[i+1]-p[0]));det=float(cross2(*d))
        if det<0:raise ValueError('inverted polygon fan')
        if det==0:continue
        X.append(p[0]+uv@d);W.append(weight*det)
    if not W:raise ValueError('zero-area polygon')
    return np.concatenate(X),np.concatenate(W)


def shape_values(vertices,points):
    t=triangle(vertices);p=real(points,2,'evaluation points')
    if p.shape[1:]!=(2,):raise ValueError('planar points required')
    v=(p-t[0])@np.linalg.inv((t[1:]-t[0]).T).T
    l=np.column_stack((1-v.sum(axis=1),v))
    return np.column_stack((l*(2*l-1),4*l[:,0]*l[:,1],4*l[:,0]*l[:,2],4*l[:,1]*l[:,2],27*np.prod(l,axis=1)))


@dataclass(frozen=True)
class AffineDensity:
    target: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    area: float
    minimum: float

    def values(self,points):
        x=real(points,2,'density points')
        if x.shape[1:]!=(2,):raise ValueError('density points must be planar')
        return np.column_stack((np.ones(len(x)),(x-self.target)/self.scale))@self.coefficients


def fit_density(polygons,target):
    """Unit total and specified first moment; reject a tensile affine fit.

    This finite affine family is a declared research shape, not a measured or
    uniquely reconstructed pressure distribution. Positivity is checked at all
    vertices, which bound affine functions on these convex polygons.
    """
    target=real(target,1,'target')
    if target.shape!=(2,) or not len(polygons):raise ValueError('planar target and nonempty domain required')
    vertices=np.concatenate([real(p,2,'domain') for p in polygons]);scale=np.max(abs(vertices-target),axis=0)
    if np.any(scale<=1e-14):raise ValueError('singular pressure domain')
    gram=np.zeros((3,3));area=0.
    for p in polygons:
        x,w=polygon_quadrature(p);v=np.column_stack((np.ones(len(x)),(x-target)/scale))
        gram+=v.T@(w[:,None]*v);area+=float(w.sum())
    if area<=0:raise ValueError('empty pressure domain')
    coeff=np.linalg.solve(gram,np.array([1.,0.,0.]));at_vertices=np.column_stack((np.ones(len(vertices)),(vertices-target)/scale))@coeff
    minimum=float(at_vertices.min())
    if minimum< -1e-12/max(area,1e-300):raise ValueError('prescribed affine pressure has tensile region')
    return AffineDensity(target.copy(),scale,coeff,area,minimum)


def integrate_face(vertices,polygon,density):
    """Seven scalar work coefficients [3vertices,3edges,1face bubble]."""
    t=triangle(vertices);p=real(polygon,2,'domain');x,w=polygon_quadrature(p)
    # Reject outside polygons instead of integrating extrapolated basis values.
    tail=(p-t[0])@np.linalg.inv((t[1:]-t[0]).T).T
    bary=np.column_stack((1-tail.sum(axis=1),tail))
    if bary.min() < -1e-9:raise ValueError('integration domain outside parent triangle')
    if not isinstance(density,AffineDensity):raise ValueError('explicit affine density required')
    d=density.values(x);basis=shape_values(t,x);weighted=w*d
    return {'work_coefficients':basis.T@weighted,'resultant':float(weighted.sum()),
            'first_moment':x.T@weighted,'geometric_area':float(w.sum()),
            'bubble_coefficient_is_not_physical_resultant':True,
            'real_material_preload_or_pressure_assigned':False}
