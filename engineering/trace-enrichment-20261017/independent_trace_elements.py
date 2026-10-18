"""Flat child-mesh stiffness assembly, library P2 gradients, Voigt strain form.

Independent of recursive trace condensation and its Duffy quadrature. The
candidate matrix is only the comparison target. No contact solver is imported.
"""
from pathlib import Path
import argparse,json,sys,hashlib
import numpy as np
from skfem import ElementTetP2
from skfem.quadrature import get_quadrature_tet
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))

REFERENCE=np.array([[0.,0,0],[1.,0,0],[0.,1,0],[0.,0,1]])
EDGES=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
FACES=tuple(tuple(j for j in range(4) if i!=j) for i in range(4))

def nodes(t):return np.vstack((t,[(t[i]+t[j])/2 for i,j in EDGES]))
def expanded(level):
    result=[REFERENCE]
    for _ in range(level):
        more=[]
        for t in result:
            for i in range(4):
                c=t.copy();c[i]=t.mean(axis=0);more.append(c)
        result=more
    return result

def flat_matrix(vertices,level=2):
    children=expanded(level);allnodes=[tuple(x) for x in nodes(REFERENCE)]
    for t in children:
        for x in nodes(t):
            if tuple(x) not in allnodes:allnodes.append(tuple(x))
    count=len(allnodes);allnodes=np.array(allnodes);full=np.zeros((3*count+12,3*count+12))
    q,w=get_quadrature_tet(4);elem=ElementTetP2()
    perm=[int(np.argmin(np.linalg.norm(elem.doflocs-x,axis=1))) for x in nodes(REFERENCE)]
    rootJ=(vertices[1:]-vertices[0]).T;ri=np.linalg.inv(rootJ);rg=np.vstack((-ri.sum(axis=0),ri))
    mu=1/(2*1.3);la=.3/(1.3*.4);D=np.zeros((6,6));D[:3,:3]=la
    np.fill_diagonal(D[:3,:3],la+2*mu);np.fill_diagonal(D[3:,3:],mu)
    for tr in children:
        physical=vertices[0]+tr@rootJ.T;J=(physical[1:]-physical[0]).T
        gradients=np.stack([elem.lbasis(q,k)[1].T@np.linalg.inv(J) for k in perm],axis=1)
        xref=tr[0]+q.T@(tr[1:]-tr[0]);l=np.c_[1-xref.sum(axis=1),xref]
        bg=np.stack([27*(l[:,i,None]*l[:,j,None]*rg[k]+l[:,j,None]*l[:,k,None]*rg[i]+l[:,k,None]*l[:,i,None]*rg[j]) for i,j,k in FACES],axis=1)
        g=np.concatenate((gradients,bg),axis=1);strain=np.zeros((len(w),6,42))
        for node in range(14):
            dx,dy,dz=g[:,node].T;j=3*node
            strain[:,0,j]=dx;strain[:,1,j+1]=dy;strain[:,2,j+2]=dz
            strain[:,3,j]=dy;strain[:,3,j+1]=dx
            strain[:,4,j]=dz;strain[:,4,j+2]=dx
            strain[:,5,j+1]=dz;strain[:,5,j+2]=dy
        local=np.einsum('q,qai,ab,qbj->ij',w*abs(np.linalg.det(J)),strain,D,strain)
        ni=np.array([np.flatnonzero(np.all(allnodes==x,axis=1))[0] for x in nodes(tr)])
        idx=np.r_[(3*ni[:,None]+np.arange(3)).ravel(),np.arange(3*count,3*count+12)]
        full[np.ix_(idx,idx)]+=local
    keep=np.r_[np.arange(30),np.arange(3*count,3*count+12)];private=np.arange(30,3*count)
    out=full[np.ix_(keep,keep)].copy()
    if len(private):out-=full[np.ix_(keep,private)]@np.linalg.solve(full[np.ix_(private,private)],full[np.ix_(private,keep)])
    return out,full,allnodes

def main(a):
    a.output.mkdir(parents=True,exist_ok=False);rows=[];rng=np.random.default_rng(608)
    from face_trace_space import trace_condense
    for i in range(8):
        A=rng.normal(size=(3,3));u,s,v=np.linalg.svd(A);A=u@np.diag([.5,1.,2.])@v
        vertices=REFERENCE@A+rng.normal(size=3)
        for level in (0,1,2):
            independent,_,_=flat_matrix(vertices,level)
            candidate=trace_condense(vertices[None],level=level).stiffness[0]
            err=float(np.max(abs(independent-candidate))/np.max(abs(independent)));assert err<1e-10
            rows.append({'type':'independent_shape','shape':i,'level':level,'relative_matrix_error':err})
    for body in ('panel','frame'):
        path=a.run/body/'local-records.json';records=json.loads(path.read_text())
        for rec in records:
            independent,full,nn=flat_matrix(np.array(rec['vertices']),2);candidate=np.array(rec['extended_stiffness'])
            err=float(np.max(abs(independent-candidate))/np.max(abs(independent)));assert err<1e-8,(body,rec['tet'],err)
            np.savez_compressed(a.output/f'{body}-tet-{rec["tet"]}.npz',stiffness=independent,uncondensed=full,reference_nodes=nn)
            rows.append({'type':'actual_selected_parent','body':body,'tet':rec['tet'],'relative_matrix_error':err})
    r={'passed':True,'checks':rows,'maximum_relative_error':max(x['relative_matrix_error'] for x in rows),
       'independent_rule':'scikit-fem tetrahedron degree4, flat child mesh, Voigt strains, one elimination of all private unknowns',
       'candidate_contact_solver_imported':False,'not_physical_or_mesh_convergence':True,
       'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print('INDEPENDENT_TRACE_ELEMENTS',len(rows),r['maximum_relative_error'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
