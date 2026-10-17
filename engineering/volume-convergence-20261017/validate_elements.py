"""Independent scikit-fem integration of coarse and explicitly refined cells."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from skfem import MeshTet,Basis,ElementTetP2,ElementVector,asm
from skfem.models.elasticity import linear_elasticity,lame_parameters
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
import tetra_bubble_refinement as t
from contact_exchange import sha256

def explicit(v,level):
    vertices=v.copy();cells=np.array([[0,1,2,3]])
    for _ in range(level):
        centers=vertices[cells].mean(axis=1);new=[]
        for i,cell in enumerate(cells):
            for j in range(4):
                row=cell.copy();row[j]=len(vertices)+i;new.append(row)
        vertices=np.vstack((vertices,centers));cells=np.asarray(new)
    m=MeshTet(vertices.T,cells.T,sort_t=False);b=Basis(m,ElementVector(ElementTetP2()),intorder=4)
    K=asm(linear_elasticity(*lame_parameters(1.,.3)),b).toarray();axes=b.split_indices();xyz=b.doflocs[:,axes[0]].T
    canonical=t.p2_nodes(v);sn=np.array([np.argmin(np.linalg.norm(xyz-x,axis=1)) for x in canonical]);assert np.max(abs(xyz[sn]-canonical))<1e-12
    ext=np.stack([a[sn] for a in axes],axis=1).ravel();inside=np.setdiff1d(np.arange(b.N),ext)
    S=K[np.ix_(ext,ext)]
    if len(inside):S=S-K[np.ix_(ext,inside)]@np.linalg.solve(K[np.ix_(inside,inside)],K[np.ix_(inside,ext)])
    return S,len(cells),b.N

def main(output):
    output=Path(output);assert not output.exists();rows=[];rng=np.random.default_rng(2741)
    for j in range(12):
        v=t.REF@np.array([[1+.1*j,.2,.1],[.2,1.,.15],[.1,.2,.8]])+rng.normal(size=3)
        for level in (0,1,2):
            reference,cells,dofs=explicit(v,level)
            candidate=t.p2_stiffness(v[None])[0] if not level else t.star_condense(v[None],level=level).stiffness[0]
            error=float(np.max(abs(candidate-reference)));scale=float(np.max(abs(reference)));assert error<1e-10*scale
            rows.append({'shape':j,'level':level,'explicit_tetrahedra':cells,'full_DOFs':int(dofs),'maximum_stiffness_error':error,'relative_error':error/scale})
    output.write_text(json.dumps({'passed':True,'checks':rows,'source_sha256':sha256(__file__),'candidate_sha256':sha256(ROOT/'integration/tetra_bubble_refinement.py'),'library_assembled_full_stiffness_then_eliminated_internals':True,'no_phone_mesh_convergence_claim':True},indent=2)+'\n')
    print('INDEPENDENT_FULL_REFINEMENT_CHECKS',len(rows),'MAX_ERROR',max(x['maximum_stiffness_error'] for x in rows),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);main(p.parse_args().output)
