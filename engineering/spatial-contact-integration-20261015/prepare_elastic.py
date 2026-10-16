from pathlib import Path
import argparse,json,hashlib,time,subprocess,sys,os
import numpy as np
from scipy.sparse import save_npz
from skfem import MeshTet,Basis,ElementVector,ElementTetP2,asm
from skfem.models.elasticity import linear_elasticity,lame_parameters
BASE=Path('/tmp/razr-support-coupling-20261015');OUT=Path('/tmp/razr-spatial-integration-20261015/elastic')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--body',choices=['panel','frame'],required=True);a=p.parse_args();b=a.body
out=OUT/b;out.mkdir(parents=True,exist_ok=False)
r=json.loads((BASE/(b+'-final3/report.json')).read_text());mf=BASE/('input/mesh.npz' if b=='panel' else 'frame-mesh3/mesh.npz');fp=BASE/(b+'-final3/fields.npz')
assert sha(mf)==r['mesh_sha256'] and sha(fp)==r['fields_sha256']
d=np.load(mf,allow_pickle=False);m=MeshTet(d['points'].T,d['tetra'].T);basis=Basis(m,ElementVector(ElementTetP2()),intorder=4)
f=np.load(fp,allow_pickle=False);xyz=f['dof_xyz'];assert np.array_equal(xyz,basis.doflocs) and basis.N==r['dofs']
D=f['D'];R=f['rigid_modes'];C=f['port_forces'][:,:4];F=f['external_forces']
np.savez(out/'loads.npz',D=D,R=R,C=C,F=F,xyz=xyz,axis0=f['axis0'],axis1=f['axis1'],axis2=f['axis2'])
t=time.monotonic();L,mu=lame_parameters(1.,.3);K=asm(linear_elasticity(L,mu),basis).tocsc();print('ASSEMBLED',b,basis.N,K.nnz,time.monotonic()-t,flush=True)
save_npz(out/'K.npz',K,compressed=False)
report={'body':b,'mesh_path':str(mf),'mesh_sha256':sha(mf),'fields_path':str(fp),'fields_sha256':sha(fp),'K_sha256':sha(out/'K.npz'),'loads_sha256':sha(out/'loads.npz'),'dofs':int(basis.N),'tetrahedra':int(m.nelements),'E_normalization':1.,'nu_assumption':.3,'boundary':r['boundary'],'source_sha256':sha(__file__),'no_contact_penalty_or_artificial_stiffness':True}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('READY',b,flush=True)
