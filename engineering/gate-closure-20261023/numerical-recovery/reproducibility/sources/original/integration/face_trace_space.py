"""Conforming cubic face bubbles added to a nested P2 volume space.

Each scalar face function is 27*lambda_i*lambda_j*lambda_k. It vanishes on
all other faces and all original P2 nodes, but equals one at its face centre.
A single coefficient must be shared by BOTH cells of an interior face.
Only selected faces are enriched: this is not complete P3 or global h refinement.
Original private volume DOFs are eliminated, not fixed. No material is assigned.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from numpy.polynomial.legendre import leggauss
from tetra_bubble_refinement import (EDGES, REF, CHILDREN, CHILD_VECTOR_MAPS,
    _vertices, _material, p2_nodes)

FACES = tuple(tuple(j for j in range(4) if j != i) for i in range(4))

def tetra_rule():
    """Positive Duffy product rule, exact for total degree <=4 on a straight tet."""
    q,w=leggauss(4);q=(q+1)/2;w=w/2
    a,b,c=np.meshgrid(q,q,q,indexing='ij');wa,wb,wc=np.meshgrid(w,w,w,indexing='ij')
    xyz=np.stack((a,(1-a)*b,(1-a)*(1-b)*c),axis=-1).reshape(-1,3)
    weights=(wa*wb*wc*(1-a)**2*(1-b)).ravel()
    return xyz,weights

QUADRATURE, WEIGHTS = tetra_rule()

def barycentric(vertices,points):
    v,jac,_=_vertices(vertices);p=np.asarray(points)
    if p.dtype.kind not in 'fiu' or p.shape[0]!=len(v) or p.ndim!=3 or p.shape[2]!=3 or not np.isfinite(p).all():
        raise ValueError('finite points (N,Q,3) required')
    tail=np.einsum('nij,nqj->nqi',np.linalg.inv(jac),p-v[:,:1,:])
    return np.concatenate((1-tail.sum(axis=2,keepdims=True),tail),axis=2)

def face_values(vertices,points):
    l=barycentric(vertices,points)
    return np.stack([27*np.prod(l[:,:,ix],axis=2) for ix in FACES],axis=2)

def _gradients(vertices,parent):
    v,jac,volume=_vertices(vertices);root,rjac,_=_vertices(parent)
    if root.shape!=v.shape:raise ValueError('one parent per child required')
    inv=np.linalg.inv(jac);g=np.concatenate((-inv.sum(axis=1)[:,None],inv),axis=1)
    l=np.column_stack((1-QUADRATURE.sum(axis=1),QUADRATURE))
    physical=v[:,:1]+np.einsum('nij,qj->nqi',jac,QUADRATURE)
    parent_l=barycentric(root,physical);pinv=np.linalg.inv(rjac)
    pg=np.concatenate((-pinv.sum(axis=1)[:,None],pinv),axis=1)
    gradients=np.empty((len(v),len(QUADRATURE),14,3))
    gradients[:,:,:4]=(4*l-1)[None,:,:,None]*g[:,None]
    for k,(i,j) in enumerate(EDGES,4):
        gradients[:,:,k]=4*(l[None,:,i,None]*g[:,None,j]+l[None,:,j,None]*g[:,None,i])
    for f,(i,j,k) in enumerate(FACES,10):
        gradients[:,:,f]=27*(parent_l[:,:,i,None]*parent_l[:,:,j,None]*pg[:,None,k]
            +parent_l[:,:,j,None]*parent_l[:,:,k,None]*pg[:,None,i]
            +parent_l[:,:,k,None]*parent_l[:,:,i,None]*pg[:,None,j])
    return gradients,6*volume

def trace_element(vertices,E=1.,nu=.3,*,parent=None):
    """Exact polynomial elastic energy on [30 P2,12 parent-face coefficients]."""
    v,_,_=_vertices(vertices);root=v if parent is None else parent
    lam,mu=_material(E,nu);g,det=_gradients(v,root)
    outer=np.einsum('q,nqia,nqjb->niajb',WEIGHTS,g,g)*det[:,None,None,None,None]
    dot=np.einsum('q,nqia,nqja->nij',WEIGHTS,g,g)*det[:,None,None]
    k=lam*outer+mu*outer.transpose(0,1,4,3,2)+mu*np.einsum('nij,ab->niajb',dot,np.eye(3))
    return k.reshape(-1,42,42)

@dataclass
class TraceElement:
    stiffness: np.ndarray
    internal_extension: np.ndarray
    uncondensed: np.ndarray


def trace_condense(vertices,E=1.,nu=.3,*,level=2,parent=None):
    """Retain parent cubic face coefficients and all old exterior P2 variables.

    For level>0, local ordering before elimination is 45 P2 followed by12
    parent-face coefficients. Returned order is30 retained P2 plus12 faces.
    The internal body-load branch is deliberately unsupported.
    """
    if type(level) is not int or level not in (0,1,2):raise ValueError('level must be0,1,2')
    v,_,_=_vertices(vertices);root=v if parent is None else parent;_material(E,nu)
    if level==0:
        k=trace_element(v,E,nu,parent=root)
        return TraceElement(k,np.empty((len(v),0,42)),k)
    verts=np.concatenate((v,v.mean(axis=1)[:,None]),axis=1)
    full=np.zeros((len(v),57,57))
    for child,old_ids in zip(CHILDREN,CHILD_VECTOR_MAPS):
        ids=np.r_[old_ids,np.arange(45,57)]
        kc=trace_condense(verts[:,child],E,nu,level=level-1,parent=root).stiffness
        full[:,ids[:,None],ids[None,:]]+=kc
    keep=np.r_[np.arange(30),np.arange(45,57)];private=np.arange(30,45)
    kii=full[:,private[:,None],private];kib=full[:,private[:,None],keep]
    np.linalg.cholesky(kii);extension=-np.linalg.solve(kii,kib)
    scale=np.max(abs(full),axis=(1,2))
    if np.any(np.max(abs(kii@extension+kib),axis=(1,2))>1e-10*scale):
        raise ValueError('private volume equilibrium failed')
    k=full[:,keep[:,None],keep]+full[:,keep[:,None],private]@extension
    if np.any(np.max(abs(k-k.transpose(0,2,1)),axis=(1,2))>1e-10*scale):
        raise ValueError('nonreciprocal enriched energy')
    return TraceElement((k+k.transpose(0,2,1))/2,extension,full)


def recover_trace(vertices,old,face,*,level=2,parent=None):
    """Recover all private P2 coefficients and integrate the TOTAL enriched field.

    Private values are hierarchical P2 coefficients, not total nodal positions:
    the parent cubic face field must also be evaluated to obtain displacement.
    Returns private coefficients, maximum local residual, twice strain energy.
    """
    v,_,_=_vertices(vertices);root=v if parent is None else parent
    old=np.asarray(old);face=np.asarray(face)
    if old.shape!=(len(v),30) or face.shape!=(len(v),12) or not np.isfinite(old).all() or not np.isfinite(face).all():
        raise ValueError('finite P2 and face arrays required')
    ub=np.c_[old,face];el=trace_condense(v,level=level,parent=root)
    if level==0:
        return np.empty((len(v),0)),0.,np.einsum('ni,nij,nj->n',ub,el.stiffness,ub)
    private=np.einsum('nij,nj->ni',el.internal_extension,ub)
    full=np.c_[old,private,face];res=np.einsum('nij,nj->ni',el.uncondensed,full)[:,30:45]
    largest=float(np.max(abs(res)));result=[private];energy=np.zeros(len(v))
    verts=np.concatenate((v,v.mean(axis=1)[:,None]),axis=1)
    for child,ids in zip(CHILDREN,CHILD_VECTOR_MAPS):
        more,err,en=recover_trace(verts[:,child],full[:,ids],face,level=level-1,parent=root)
        result.append(more);largest=max(largest,err);energy+=en
    return np.concatenate(result,axis=1),largest,energy
