"""P2 tetrahedra: exact star-interior refinement and static condensation.

Four children keep every original quadratic face trace; five new scalar
nodes give fifteen interior displacement DOFs per parent. Condensation is
exact for zero interior/body load. This is volume-interior sensitivity,
NOT global h-convergence: parent boundary edges/traces are not refined.
No stabilization, contact pressure, material or support change is implied.
"""
from __future__ import annotations
import numpy as np
EDGES=((0,1),(1,2),(0,2),(0,3),(1,3),(2,3))
VERTICES=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
NODES=np.vstack([VERTICES,[(VERTICES[i]+VERTICES[j])/2 for i,j in EDGES]])
CENTRE=VERTICES.mean(axis=0)
STAR_NODES=np.vstack([NODES,CENTRE,[(v+CENTRE)/2 for v in VERTICES]])
CHILD_VERTICES=np.array([[1,2,3,10],[0,2,3,10],[0,1,3,10],[0,1,2,10]])
CHILD_NODES=[]
for face in CHILD_VERTICES:
    xyz=STAR_NODES[face]
    child=np.vstack([xyz,[(xyz[i]+xyz[j])/2 for i,j in EDGES]])
    indices=[]
    for x in child:
        ix=np.flatnonzero(np.max(abs(STAR_NODES-x),axis=1)<1e-14)
        if len(ix)!=1:raise RuntimeError('ambiguous internal reference node')
        indices.append(int(ix[0]))
    CHILD_NODES.append(indices)
CHILD_NODES=np.array(CHILD_NODES,dtype=int)
CHILD_DOFS=(3*CHILD_NODES[:,:,None]+np.arange(3)).reshape(4,30)
Q_BARY=np.full((4,4),.1381966011250105)
np.fill_diagonal(Q_BARY,.5854101966249685)


def _geometry(vertices):
    raw=np.asarray(vertices)
    if raw.dtype.kind not in 'fiu' or raw.ndim not in (2,3) or raw.shape[-2:]!=(4,3) or not np.isfinite(raw).all():
        raise ValueError('finite real vertices (...,4,3) required')
    v=raw.astype(float,copy=False);singleton=v.ndim==2
    if singleton:v=v[None]
    if not len(v):raise ValueError('empty tetrahedron batch')
    J=(v[:,1:]-v[:,0,None]).transpose(0,2,1)
    scale=np.max(abs(J),axis=(1,2));det=np.linalg.det(J)
    if np.any(scale==0) or np.any(abs(det)<=1e-13*scale**3):
        raise ValueError('degenerate or numerically singular tetrahedron')
    return v,J,det,singleton


def material(E,nu):
    if type(E) not in (int,float) or not np.isfinite(E) or E<=0:
        raise ValueError('positive finite Young modulus required')
    if type(nu) not in (int,float) or not np.isfinite(nu) or not -1<nu<.5:
        raise ValueError('Poisson ratio must be strictly between -1 and .5')
    return E*nu/((1+nu)*(1-2*nu)),E/(2*(1+nu))


def element_stiffness(vertices,E=1.,nu=.3):
    """Small-strain isotropic elasticity, exact degree-two quadrature."""
    v,J,det,single=_geometry(vertices);lam,mu=material(E,nu)
    inv=np.linalg.inv(J)
    bg=np.concatenate([-inv.sum(axis=1)[:,None,:],inv],axis=1)
    grad=np.empty((len(v),4,10,3))
    grad[:,:,:4]=(4*Q_BARY-1)[None,:,:,None]*bg[:,None,:,:]
    for k,(i,j) in enumerate(EDGES,4):
        grad[:,:,k]=4*(Q_BARY[None,:,i,None]*bg[:,None,j,:]+Q_BARY[None,:,j,None]*bg[:,None,i,:])
    k=lam*np.einsum('nqia,nqjb->niajb',grad,grad)
    k+=mu*np.einsum('nqib,nqja->niajb',grad,grad)
    k+=mu*np.einsum('nqik,nqjk,ab->niajb',grad,grad,np.eye(3))
    k=k.reshape(len(v),30,30)*(abs(det)/24)[:,None,None]
    return k[0] if single else k


def star_stiffness(vertices,E=1.,nu=.3,*,return_recovery=False):
    """One star split. Recovery maps retained 30 to new interior 15 DOFs."""
    v,J,det,single=_geometry(vertices);material(E,nu)
    allxyz=v[:,0,None,:]+np.einsum('nij,kj->nki',J,STAR_NODES)
    K=np.zeros((len(v),45,45))
    for nodes,indices in zip(CHILD_VERTICES,CHILD_DOFS):
        local=element_stiffness(allxyz[:,nodes],E,nu)
        K[:,indices[:,None],indices[None,:]]+=local
    A=K[:,:30,:30];B=K[:,30:,:30];D=K[:,30:,30:]
    np.linalg.cholesky(D)
    recovery=-np.linalg.solve(D,B)
    reduced=A+np.einsum('nki,nkj->nij',B,recovery)
    reduced=(reduced+reduced.transpose(0,2,1))/2
    if single:reduced=reduced[0];recovery=recovery[0];K=K[0]
    return (reduced,recovery,K) if return_recovery else reduced


def parent_interpolation():
    """Exact parent P2 embedding; used to verify the nested energy identity."""
    x=STAR_NODES;b=np.column_stack([1-x.sum(axis=1),x])
    shape=np.column_stack([b*(2*b-1),*[4*b[:,i]*b[:,j] for i,j in EDGES]])
    return np.kron(shape,np.eye(3))
