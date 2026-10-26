"""Volume-enrichment sensitivity under frozen old traction vectors.

These are NOT newly solved unilateral-contact states. Negative local gaps
remain diagnostic failures. No old point matrix is used with a changed K.
"""
from pathlib import Path
import argparse,json,sys,time,gzip
import numpy as np
from scipy.sparse import load_npz
from scipy.sparse.linalg import splu
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'integration'))
from contact_exchange import sha256
from tetra_bubble_refinement import star_condense,CHILDREN,CHILD_VECTOR_MAPS,p2_stiffness


def strain_energy(vertices,nodal):
    # Direct strain quadrature avoids subtracting large rigid-motion terms
    # in u.T K u. Only evaluation is stabilized; returned displacements and
    # all physical equations are unchanged.
    v=np.asarray(vertices);u=np.asarray(nodal).reshape(len(v),10,3)
    jac=np.swapaxes(v[:,1:]-v[:,:1],1,2);inv=np.linalg.inv(jac);vol=abs(np.linalg.det(jac))/6
    g=np.concatenate((-inv.sum(axis=1)[:,None,:],inv),axis=1)
    a=(5+3*np.sqrt(5))/20;b=(5-np.sqrt(5))/20;l=np.full((4,4),b);np.fill_diagonal(l,a)
    gradient=np.empty((len(v),4,10,3));gradient[:,:,:4]=(4*l-1)[None,:,:,None]*g[:,None]
    edges=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
    for k,(i,j) in enumerate(edges,4):gradient[:,:,k]=4*(l[None,:,i,None]*g[:,None,j]+l[None,:,j,None]*g[:,None,i])
    du=np.einsum('tqia,tib->tqab',gradient,u-u[:,:1]);eps=(du+du.transpose(0,1,3,2))/2
    lam=.3/(1.3*.4);mu=1/2.6
    return vol/4*np.sum(lam*np.trace(eps,axis1=2,axis2=3)**2+2*mu*np.sum(eps*eps,axis=(2,3)),axis=1)


def recovered(vertices,ub,level):
    obj=star_condense(vertices,level=level);u=obj.recover(ub)
    residual=np.einsum('tij,tj->ti',obj.uncondensed,u)
    maximum=float(np.max(abs(residual[:,30:]),initial=0.));inner=[u[:,30:]];energy=np.zeros(len(vertices))
    children=np.concatenate((vertices,vertices.mean(axis=1)[:,None]),axis=1)
    for c,ids in zip(CHILDREN,CHILD_VECTOR_MAPS):
        if level==1:energy+=strain_energy(children[:,c],u[:,ids])
        else:
            sub,res,en=recovered(children[:,c],u[:,ids],level-1);inner.append(sub);maximum=max(maximum,res);energy+=en
    return np.concatenate(inner,axis=1),maximum,energy


def main(a):
    out=a.output;out.mkdir(parents=True,exist_ok=False);src=a.volume/a.body/f'level-{a.level}'
    report=json.loads((src/'report.json').read_text());assert report['level']==a.level and report['K_sha256']==sha256(src/'K.npz')
    ld=np.load(src/'loads.npz',allow_pickle=False);mapping=np.load(a.volume/a.body/'mapping.npz',allow_pickle=False);ids=mapping['element_dofs'];vertices=mapping['vertices']
    K=load_npz(src/'K.npz').tocsc();D=ld['D'];free=np.setdiff1d(np.arange(K.shape[0]),D)
    tic=time.monotonic();factor=splu(K[free][:,free],permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True});print('FACTOR',a.body,a.level,time.monotonic()-tic,flush=True)
    results=[]
    for case in (4,5,6,7):
        origin=ROOT/'engineering/preload-closure-20261017'/f'case-{case}';old=np.load(origin/'full-fields.npz',allow_pickle=False)
        r=json.loads(gzip.decompress((origin/'report.json.gz').read_bytes()));f=old['load_'+a.body];u=np.zeros(len(f));u[free]=factor.solve(f[free])
        if a.body=='panel':u+=ld['R']@np.asarray(r['rigid'])
        res=K@u-f;err=float(np.max(abs(res[free])));assert err<1e-9
        if a.body=='panel':assert np.max(abs(res[D]))<1e-9
        energy=float(u@(K@u));work=float(u@f);assert abs(energy-work)<1e-5*max(abs(work),1e-20)
        internal=np.empty((len(ids),15*((4**a.level-1)//3)));maximum=0.;integrated=0.
        for lo in range(0,len(ids),256):
            hi=min(lo+256,len(ids));rr,re,en=recovered(vertices[lo:hi],u[ids[lo:hi]],a.level);internal[lo:hi]=rr;maximum=max(maximum,re);integrated+=float(en.sum())
        assert maximum<1e-9 and abs(integrated-energy)<1e-5*max(abs(energy),1e-20)
        prior=old['up' if a.body=='panel' else 'uf'];delta=u-prior
        item={'case':case,'body':a.body,'level':a.level,'same_old_traction_not_new_contact_solution':True,'max_displacement_change_mm':float(np.max(abs(delta))),
              'new_fTu':work,'old_fTu':float(f@prior),'relative_fTu_change':work/float(f@prior)-1,'free_residual_max':err,'fixed_or_gauge_reaction_max':float(np.max(abs(res[D]))),
              'recovered_energy_from_direct_finest_strain_quadrature':True,'recovered_internal_dofs':int(internal.size),'internal_residual_max':maximum,'recovered_total_twice_energy':integrated,'energy_work_relative_error':abs(energy-work)/max(abs(work),1e-20),
              'K_sha256':sha256(src/'K.npz'),'old_fields_sha256':sha256(origin/'full-fields.npz'),'source_sha256':sha256(__file__),
              'new_contact_solved':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
        np.savez_compressed(out/f'case-{case}.npz',u=u,load=f,internal=internal)
        (out/f'case-{case}.json').write_text(json.dumps(item,indent=2)+'\n');results.append(item);print('FIXED_LOAD_CASE',a.body,a.level,case,item['relative_fTu_change'],item['max_displacement_change_mm'],flush=True)
    (out/'SUMMARY.json').write_text(json.dumps({'passed_algebraic_reconstruction':True,'new_contact_solution':False,'cases':results},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--volume',type=Path,required=True);p.add_argument('--body',choices=['panel','frame'],required=True);p.add_argument('--level',choices=[1,2],type=int,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
