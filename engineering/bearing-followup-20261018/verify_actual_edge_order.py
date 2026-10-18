"""Replay the edge-order defect on a retained rejected full original-model field.
No new contact field is qualified by this interpolation-only check.
"""
from pathlib import Path
import json,sys,hashlib
import numpy as np
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
R=Path('/home/qian-qi/RAZR-SLIDE-bearing-orderfix-20261018');O=Path('/home/qian-qi/.local/share/razr-slide-evidence/bearing-contact-20261018');V=Path('/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3')
sys.path.insert(0,str(R/'integration'))
from bearing_contact import bearing_coefficients
from contact_patch_audit import triangle_coefficients,evaluate
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=O/'rigid-install-v2';f=src/'bearing-field-000.npz';d=np.load(f,allow_pickle=False);u=d['u'];regions=json.loads((src/'bearing-domains.json').read_text())
ident={str(f):sha(f),str(src/'bearing-domains.json'):sha(src/'bearing-domains.json')};summary=[]
for name in ['panel','frame']:
 p=V/name/'level-2/mesh.npz';md=np.load(p,allow_pickle=False);ident[str(p)]=sha(p);mesh=MeshTet(md['points'].T,md['tetra'].T);sc=Basis(mesh,ElementTetP2());ve=Basis(mesh,ElementVector(ElementTetP2()));axis=ve.split_indices()[2]
 for i,row in enumerate(regions):
  if row['body']!=name:continue
  tri=np.array(row['triangle_xy']);poly=np.array(row['polygon']);xy=np.vstack((poly,poly.mean(axis=0)));plane=mesh.p[2,row['vertices'][0]];xyz=np.column_stack((xy,np.full(len(xy),plane)));ti=row['parent_tetrahedron'];tet=mesh.p[:,mesh.t[:,ti]];local=np.linalg.solve(tet[:,1:]-tet[:,:1],(xyz-tet[:,0]).T)
  N=np.column_stack([sc.elem.lbasis(local,j)[0] for j in range(10)]);nodal=u[row['offset']+axis[sc.element_dofs[:,ti]]];reference=N@nodal;vals=u[row['offset']+np.array(row['dofs'])]
  new=evaluate(bearing_coefficients(tri,vals,row['origin']),xy,row['origin']);old=evaluate(triangle_coefficients(tri,vals,row['origin']),xy,row['origin'])
  newerr=float(np.max(abs(new-reference)));olderr=float(np.max(abs(old-reference)));assert newerr<1e-12
  summary.append({'body':name,'face':i,'points':len(xy),'new_library_error':newerr,'old_unconverted_error':olderr,'old_order_defect_reproduced':olderr>1e-10})
assert len(summary)==1196 and any(z['old_order_defect_reproduced'] for z in summary)
result={'passed':True,'source_field_is_rejected_not_equilibrium_qualification':True,'domain_faces':1196,'points':sum(x['points'] for x in summary),'max_corrected_error':max(x['new_library_error'] for x in summary),'max_wrong_order_error':max(x['old_unconverted_error'] for x in summary),'wrong_order_faces_above_1e10':sum(x['old_order_defect_reproduced'] for x in summary),'records':summary,'input_sha256':ident,'source_sha256':sha(__file__),'candidate_gap_formula_compared_against_library_tetra_P2':True,'cubic_term_unchanged_not_part_of_this_comparison':True,'field_pass_not_claimed':True}
for p,h in ident.items():assert sha(p)==h
(O/'actual-edge-order-check.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['records','input_sha256']})
