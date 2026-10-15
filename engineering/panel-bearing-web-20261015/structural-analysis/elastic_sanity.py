from pathlib import Path
import json,time
import numpy as np
from scipy.sparse.linalg import spsolve
from skfem import MeshTet,Basis,FacetBasis,ElementVector,ElementTetP1,ElementTetP2,LinearForm,asm,condense,solve
from skfem.models.elasticity import linear_elasticity,lame_parameters
O=Path('/tmp/razr-panel-elastic-20261015');rows=[]
for degree in (1,2):
 for E,nu in ((1.,.3),(7.,.3),(1.,.2),(1.,.4)):
  mesh=MeshTet.init_tensor(np.linspace(0,2,4),np.linspace(0,1,3),np.linspace(0,1,3));el=ElementVector(ElementTetP1() if degree==1 else ElementTetP2());b=Basis(mesh,el,intorder=4);ind=b.split_indices();L,mu=lame_parameters(E,nu);K=asm(linear_elasticity(L,mu),b)
  D=[]
  for axis in range(3):D.extend(ind[axis][np.isclose(b.doflocs[axis,ind[axis]],0.)])
  D=np.asarray(D,dtype=int)
  @LinearForm
  def load(v,w):return v[0]
  f=asm(load,FacetBasis(mesh,el,facets=mesh.facets_satisfying(lambda x:np.isclose(x[0],2.)),intorder=4));u=solve(*condense(K,f,D=D))
  exact=np.zeros(b.N)
  for axis in range(3):exact[ind[axis]]=b.doflocs[axis,ind[axis]]*((1. if axis==0 else -nu)/E)
  error=float(np.max(np.abs(u-exact)));energy=float(u@(K@u)/2);expected_energy=1./E
  assert error<1e-9 and abs(energy-expected_energy)<1e-9
  trans=np.ones(b.N);rot=np.zeros(b.N);rot[ind[0]]=-b.doflocs[1,ind[0]];rot[ind[1]]=b.doflocs[0,ind[1]]
  rigid=max(abs(float(trans@(K@trans))),abs(float(rot@(K@rot))));assert rigid<1e-9
  row={'degree':degree,'E_normalization':E,'nu':nu,'exact_uniaxial_max_error':error,'strain_energy':energy,'expected_energy':expected_energy,'rigid_energy_abs':rigid};rows.append(row);print('PATCH',row,flush=True)
(O/'elastic-sanity.json').write_text(json.dumps({'cases':rows,'passed':True,'scope':'analytic homogeneous uniaxial/rigid patch and scaling checks; not production structure'},indent=2)+'\n')
