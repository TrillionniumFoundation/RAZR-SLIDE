"""Nested internal P2 tetrahedral refinement with exact local condensation.

Each parent tetrahedron is split through its centroid into four children.
Original faces and their P2 trace nodes remain unchanged. Five new scalar
internal nodes add fifteen vector DOFs, eliminated by a Schur complement,
NOT set to zero. This isolates volume enrichment from contact discretization.
It is not uniform h refinement or proof of trace/continuum convergence.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

EDGES=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
REF=np.vstack((np.zeros(3),np.eye(3)))

def p2_nodes(vertices):
    v=np.asarray(vertices)
    return np.concatenate((v,np.stack([(v[...,i,:]+v[...,j,:])/2 for i,j in EDGES],axis=-2)),axis=-2)

_star_vertices=np.vstack((REF,REF.mean(axis=0)))
CHILDREN=np.tile(np.arange(4),(4,1))
for _i in range(4):CHILDREN[_i,_i]=4
STAR_NODES=np.vstack((p2_nodes(REF),REF.mean(axis=0),(REF+REF.mean(axis=0))/2))
CHILD_MAPS=np.array([[np.flatnonzero(np.all(np.isclose(STAR_NODES,q,rtol=0,atol=1e-14),axis=1))[0]
                     for q in p2_nodes(_star_vertices[c])] for c in CHILDREN])
CHILD_VECTOR_MAPS=(3*CHILD_MAPS[:,:,None]+np.arange(3)).reshape(4,30)


def _vertices(vertices):
    a=np.asarray(vertices)
    if a.dtype.kind not in 'fiu' or a.ndim!=3 or a.shape[1:]!=(4,3) or not len(a) or not np.isfinite(a).all():
        raise ValueError('nonempty finite real tetrahedra of shape (N,4,3) required')
    a=a.astype(float,copy=False);jac=np.swapaxes(a[:,1:]-a[:,:1],1,2);det=np.linalg.det(jac)
    size=np.max(abs(jac),axis=(1,2))
    if np.any(abs(det)<=1e-13*size**3):raise ValueError('degenerate or numerically singular tetrahedron')
    return a,jac,abs(det)/6


def _material(E,nu):
    if type(E) not in (int,float) or not np.isfinite(E) or E<=0:raise ValueError('positive finite Young modulus required')
    if type(nu) not in (int,float) or not np.isfinite(nu) or not -1<nu<.5:raise ValueError('Poisson ratio outside (-1,.5)')
    return E*nu/((1+nu)*(1-2*nu)),E/(2*(1+nu))


def p2_stiffness(vertices,E=1.,nu=.3):
    """Exact degree-two quadrature for straight P2 isotropic tetrahedra.

    Shape (N,30,30), xyz for each canonical scalar node. Orientation is not
    assumed from a library. No penalty or artificial stiffness is added.
    """
    v,jac,volume=_vertices(vertices);lam,mu=_material(E,nu);inv=np.linalg.inv(jac)
    grad=np.concatenate((-inv.sum(axis=1)[:,None,:],inv),axis=1)
    a=(5+3*np.sqrt(5))/20;b=(5-np.sqrt(5))/20;bary=np.full((4,4),b);np.fill_diagonal(bary,a)
    gg=np.empty((len(v),4,10,3));gg[:,:,:4]=(4*bary-1)[None,:,:,None]*grad[:,None]
    for k,(i,j) in enumerate(EDGES,4):
        gg[:,:,k]=4*(bary[None,:,i,None]*grad[:,None,j]+bary[None,:,j,None]*grad[:,None,i])
    outer=np.einsum('tqia,tqjb->tiajb',gg,gg)*(.25*volume)[:,None,None,None,None]
    dot=np.einsum('tqia,tqja->tij',gg,gg)*(.25*volume)[:,None,None]
    k=lam*outer+mu*outer.transpose(0,1,4,3,2)
    k+=mu*np.einsum('tij,ab->tiajb',dot,np.eye(3))
    return k.reshape(-1,30,30)


@dataclass
class CondensedElement:
    stiffness: np.ndarray
    internal_extension: np.ndarray
    uncondensed: np.ndarray

    def recover(self,boundary):
        """Recover top-level internal nodes assuming no internal body loading."""
        b=np.asarray(boundary)
        if b.shape!=(len(self.stiffness),30) or b.dtype.kind not in 'fiu' or not np.isfinite(b).all():
            raise ValueError('finite boundary vector of shape (N,30) required')
        return np.concatenate((b,np.einsum('tij,tj->ti',self.internal_extension,b)),axis=1)


def star_condense(vertices,E=1.,nu=.3,*,level=1):
    """Nested interior refinement; 1=4, 2=16 subtetrahedra per original cell.

    Top-level extension recovers its internal nodes. At level>1, child
    interiors must be recovered recursively. All introduced internal DOFs
    are unloaded; nonzero body loads require a separately condensed load.
    """
    if type(level) is not int or not 1<=level<=2:raise ValueError('explicit level 1 or 2 required')
    v,_,_=_vertices(vertices);_material(E,nu)
    allvertices=np.concatenate((v,v.mean(axis=1)[:,None]),axis=1);full=np.zeros((len(v),45,45))
    for c,ids in zip(CHILDREN,CHILD_VECTOR_MAPS):
        child=allvertices[:,c]
        kc=p2_stiffness(child,E,nu) if level==1 else star_condense(child,E,nu,level=level-1).stiffness
        full[:,ids[:,None],ids[None,:]]+=kc
    kbb=full[:,:30,:30];kib=full[:,30:,:30];kii=full[:,30:,30:]
    np.linalg.cholesky(kii)
    extension=-np.linalg.solve(kii,kib);residual=kii@extension+kib;scale=np.max(abs(full),axis=(1,2))
    if np.any(np.max(abs(residual),axis=(1,2))>1e-10*scale):raise ValueError('internal equilibrium residual')
    condensed=kbb+full[:,:30,30:]@extension
    if np.any(np.max(abs(condensed-condensed.transpose(0,2,1)),axis=(1,2))>1e-10*scale):raise ValueError('nonreciprocal condensed element')
    return CondensedElement((condensed+condensed.transpose(0,2,1))/2,extension,full)


def prolong_p2(vertices):
    """Original quadratic field at all 15 star nodes; shape (N,45,30)."""
    v,_,_=_vertices(vertices);bary=np.column_stack((1-STAR_NODES.sum(axis=1),STAR_NODES))
    values=np.column_stack((bary*(2*bary-1),np.stack([4*bary[:,i]*bary[:,j] for i,j in EDGES],axis=1)))
    return np.broadcast_to(np.kron(values,np.eye(3)),(len(v),45,30)).copy()
