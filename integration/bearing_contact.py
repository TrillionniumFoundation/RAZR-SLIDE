"""Frictionless rigid head/nut contact mechanics for an axial-only bolt comparator.

Each bearing has a free normal translation and two slopes. All normal contact
forces are nonnegative unknowns. Axial bolts connect opposed bearing reference
planes, not prescribed member-pressure averages. No head/nut bending stiffness,
thread strength, friction, real preload or support qualification is inferred.
"""
from __future__ import annotations
import numpy as np

N_BOLTS=4
N_BEARINGS=8

def real(value,ndim,name):
    a=np.asarray(value)
    if a.ndim!=ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError(name+': finite real array required')
    return a.astype(float,copy=True)

def plane_basis(xy,center):
    x=real(xy,2,'points');c=real(center,1,'center')
    if x.shape[1:]!=(2,) or c.shape!=(2,):raise ValueError('two tangent coordinates required')
    return np.column_stack((np.ones(len(x)),x-c))

def bearing_id(body,bolt):
    if body not in ('panel','frame') or type(bolt) is not int or not 0<=bolt<4:
        raise ValueError('known body and exact bolt index required')
    return bolt+(0 if body=='panel' else 4)

def equilibrium_map(physical_map,points,centers):
    """Append independent head/nut force and moment balance, no fixed planes.

    Rows are four axial bolt forces followed by nonnegative contact forces.
    Ordinary member contacts have kind='contact'; bearing points have explicit
    body/index/xy. Both opposed bearing resultants equal the same bolt force.
    """
    g=real(physical_map,2,'physical map');c=real(centers,2,'centers')
    if c.shape!=(4,2) or g.shape[0]!=len(points) or len(points)<4:
        raise ValueError('inconsistent bearing/force dimensions')
    if any(p.get('kind')!='bolt' or p.get('index')!=i for i,p in enumerate(points[:4])):
        raise ValueError('first four force identities must be ordered bolts')
    if np.max(abs(g[:4]),initial=0.)>1e-14:
        raise ValueError('axial connector must not apply prescribed member pressure')
    extra=np.zeros((len(points),24))
    for i in range(4):extra[i,3*i]=extra[i,3*(i+4)]=-1.
    for j,p in enumerate(points[4:],4):
        if p.get('kind')=='contact':continue
        if p.get('kind')!='bearing':raise ValueError('unknown contact kind')
        bi=bearing_id(p.get('body'),p.get('index'));extra[j,3*bi:3*bi+3]=plane_basis([p['xy']],c[p['index']])[0]
    return np.column_stack((g,extra))

def split_coordinates(values,physical_modes):
    z=real(values,1,'coordinates')
    if type(physical_modes) is not int or physical_modes<0 or z.shape!=(physical_modes+24,):
        raise ValueError('expected physical coordinates plus eight free planes')
    return z[:physical_modes].copy(),z[physical_modes:].reshape(8,3).copy()

def gap(member_displacement,xy,center,plane,body):
    u=real(member_displacement,1,'member displacement');z=real(plane,1,'plane')
    b=plane_basis(xy,center)
    if body not in ('panel','frame') or len(u)!=len(b) or z.shape!=(3,):raise ValueError('invalid bearing gap inputs')
    # Head is below member: gap=u_panel-z_head. Nut is above frame and has
    # physical z=-z_nut, so gap=-u_frame-z_nut. Positive means separation.
    sign=1. if body=='panel' else -1.
    return sign*u-b@z

def axial_adjustment(forces,compliance,planes):
    t=real(forces,1,'bolt forces');c=real(compliance,1,'bolt compliance');z=real(planes,2,'planes')
    if t.shape!=(4,) or c.shape!=(4,) or z.shape!=(8,3) or (c<=0).any() or (t<0).any():
        raise ValueError('four tensile bolt forces, positive compliance and eight planes required')
    return c*t+z[:4,0]+z[4:,0]

def resultants(forces,points,centers):
    t=real(forces,1,'contact forces');c=real(centers,2,'centers')
    if t.shape!=(len(points),) or c.shape!=(4,2):raise ValueError('reaction identity mismatch')
    rows=np.zeros((8,3))
    for j,p in enumerate(points):
        if p.get('kind')=='bearing':
            k=bearing_id(p.get('body'),p.get('index'));rows[k]+=t[j]*plane_basis([p['xy']],c[p['index']])[0]
    return rows


def bearing_coefficients(vertices, values, origin):
    """Bridge load-face edge order 01,02,12 to audit order 01,12,20."""
    from contact_patch_audit import triangle_coefficients
    v=np.asarray(values)
    if v.ndim not in (1,2) or v.shape[0]!=6 or v.dtype.kind not in 'fiu' or not np.isfinite(v).all():
        raise ValueError('six finite projected face values required')
    return triangle_coefficients(vertices,v[[0,1,2,3,5,4]],origin)
