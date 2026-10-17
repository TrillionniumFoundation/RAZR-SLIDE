"""Independent flat-mesh versus PR28 recursive condensation comparison.

Both use isotropic P2 straight tetrahedral elasticity. Independent node
ordering and explicit 4/16-cell assembly avoid reusing PR28's Schur recursion.
Not an original phone solve, stress result or global h-convergence claim.
"""
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
import pr28_tetra_bubble_refinement as candidate
sys.path.insert(0,str(Path(__file__).resolve().parent/'candidate/integration'))
import tetra_star_refinement as reference

def flat(level):
    cells=[reference.VERTICES]
    for _ in range(level):
        new=[]
        for v in cells:
            for opposite in range(4):
                ids=[i for i in range(4) if i!=opposite]
                new.append(np.vstack([v[ids],v.mean(axis=0)]))
        cells=new
    nodes=list(reference.NODES.copy());maps=[]
    for v in cells:
        row=[]
        for x in np.vstack([v,[(v[i]+v[j])/2 for i,j in reference.EDGES]]):
            found=[i for i,q in enumerate(nodes) if np.max(abs(q-x))<1e-14]
            if found:row.append(found[0])
            else:row.append(len(nodes));nodes.append(x)
        maps.append(np.array(row))
    return np.array(nodes),np.array(maps),(3*np.array(maps)[:,:,None]+np.arange(3)).reshape(len(cells),30)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    rows=[];rng=np.random.default_rng(172023)
    perm=[]
    for q in candidate.p2_nodes(candidate.REF):
        perm.append(int(np.argmin(np.max(abs(reference.NODES-q),axis=1))))
    perm=(3*np.array(perm)[:,None]+np.arange(3)).ravel()
    grids={i:flat(i) for i in (1,2)}
    t0=time.monotonic()
    for test in range(64):
        left,_=np.linalg.qr(rng.normal(size=(3,3)));right,_=np.linalg.qr(rng.normal(size=(3,3)))
        J=left@np.diag(np.exp(rng.uniform(-2,2,3)))@right
        origin=rng.normal(size=3)*5;v=origin+reference.VERTICES@J.T
        E=float(np.exp(rng.uniform(-2,2)));nu=float(rng.uniform(-.2,.45));coarse=reference.element_stiffness(v,E,nu)
        last=coarse
        for level,(nodes,maps,dofs) in grids.items():
            xyz=origin+nodes@J.T;n=len(nodes)*3;K=np.zeros((n,n))
            for m,ix in zip(maps,dofs):K[np.ix_(ix,ix)]+=reference.element_stiffness(xyz[m[:4]],E,nu)
            extension=-np.linalg.solve(K[30:,30:],K[30:,:30]);exact=K[:30,:30]+K[:30,30:]@extension
            computed=candidate.star_condense(v[None],E,nu,level=level).stiffness[0]
            denom=max(float(abs(exact).max()),1e-30)
            error=float(abs(computed-exact[np.ix_(perm,perm)]).max())/denom
            u=rng.normal(size=30);z=np.r_[u,extension@u];residual=float(abs((K@z)[30:]).max())/max(float(abs(K).max())*float(abs(z).max()),1e-30)
            nested_min=float(np.linalg.eigvalsh((last-exact+(last-exact).T)/2).min())/denom
            assert error<5e-10 and residual<5e-11 and nested_min>-5e-10
            rows.append({'shape':test,'level':level,'child_tetrahedra':4**level,'all_local_dofs':n,'condensed_matrix_relative_error':error,'recovery_residual_scaled':residual,'minimum_nested_energy_drop_scaled':nested_min});last=exact
    result={'reference_source_sha256':hashlib.sha256(Path(reference.__file__).read_bytes()).hexdigest(),'candidate_source_sha256':hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest(),'candidate_git_blob':'71e6fe616ad1b3cd69869ce02e431d50727b0942','candidate_PR_head':'3214eca909ab944843d0d73275100f80c5fbfccb','cases':rows,'matrix_comparisons':len(rows),'all_passed':True,'seconds':time.monotonic()-t0,'max_matrix_relative_error':max(x['condensed_matrix_relative_error'] for x in rows),'max_recovery_residual_scaled':max(x['recovery_residual_scaled'] for x in rows),'actual_original_volume_fields_tested':False,'global_h_or_contact_convergence':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
if __name__=='__main__':main()
