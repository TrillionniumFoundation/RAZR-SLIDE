"""Normal-displacement flatness of the accepted prescribed-pressure installation.

Area-integrated affine projection is an audit of the rigid full-contact
hypothesis, not proof that a real deformable screw/nut is incompatible.
Uses library tetrahedral P2 basis and direct barycentric face terms.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
ROOT=Path('/home/qian-qi/RAZR-SLIDE-bearing-contact-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/bearing-contact-20261018')
V=Path('/home/qian-qi/.local/share/razr-slide-evidence/volume-convergence-20261017/volume-v3')
SRC=ROOT/'engineering/installation-control-20261018/install-force'
sys.path.insert(0,str(ROOT/'integration'))
from surface_load_functional import polygon_quadrature
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=json.loads((SRC/'report.json').read_text());assert report['passed']
ind=json.loads((SRC/'independent-report.json').read_text()) if (SRC/'independent-report.json').exists() else json.loads((SRC/'audit-report.json').read_text())
assert ind['passed']
x=np.load(SRC/'full-fields.npz',allow_pickle=False);rows=[];ident={str(SRC/'report.json'):sha(SRC/'report.json'),str(SRC/'full-fields.npz'):sha(SRC/'full-fields.npz')}
for name in ('panel','frame'):
    src=ROOT/f'engineering/consistent-load-20261017/projection-512/{name}-faces.json';faces=[f for f in json.loads(src.read_text()) if f['kind']=='C'];ident[str(src)]=sha(src)
    md=V/name/'level-2/mesh.npz';d=np.load(md,allow_pickle=False);ident[str(md)]=sha(md);mesh=MeshTet(d['points'].T,d['tetra'].T)
    scalar=Basis(mesh,ElementTetP2());vector=Basis(mesh,ElementVector(ElementTetP2()));axis=vector.split_indices()[2]
    chosen=json.loads((SRC/name/'selection.json').read_text());lookup={tuple(z['vertices']):i for i,z in enumerate(chosen)}
    u=x['up' if name=='panel' else 'uf'];b=x['bp' if name=='panel' else 'bf']
    def field(face,xy):
        ti=face['parent_tetrahedron'];tet=mesh.p[:,mesh.t[:,ti]];p=np.zeros((len(xy),3));p[:,:2]=xy;p[:,2]=mesh.p[2,face['vertices'][0]]
        local=np.linalg.solve(tet[:,1:]-tet[:,:1],(p-tet[:,0]).T);shape=np.stack([scalar.elem.lbasis(local,j)[0] for j in range(10)],axis=1)
        val=shape@u[axis[scalar.element_dofs[:,ti]]];fi=lookup.get(tuple(sorted(face['vertices'])))
        if fi is not None:
            bary=np.vstack((1-local.sum(axis=0),local));ix=[j for j,v in enumerate(mesh.t[:,ti]) if v in set(face['vertices'])];val+=27*np.prod(bary[ix],axis=0)*b[3*fi+2]
        return val
    for i in range(4):
        fs=[f for f in faces if f['index']==i];center=np.array(fs[0]['density_target']);gram=np.zeros((3,3));rhs=np.zeros(3);area=0.;samples=[];minimum_density=1e300
        for f in fs:
            xy,w=polygon_quadrature(f['polygon'],order=6);P=np.column_stack((np.ones(len(xy)),xy-center));v=field(f,xy);gram+=P.T@(w[:,None]*P);rhs+=P.T@(w*v);area+=w.sum();samples.append((xy,w,P,v))
            verts=np.array(f['polygon']);den=np.column_stack((np.ones(len(verts)),(verts-np.array(f['density_target']))/np.array(f['density_scale'])))@np.array(f['density_coefficients']);minimum_density=min(minimum_density,float(den.min()))
        a=np.linalg.solve(gram,rhs);error2=0.;worst=0.;count=0
        for xy,w,P,v in samples:
            e=v-P@a;error2+=w@(e*e);worst=max(worst,float(np.max(abs(e))));count+=len(w)
        rows.append({'body':name,'bolt':i,'area_mm2':float(area),'plane_coefficients':a.tolist(),'normal_displacement_best_plane_RMS_mm':float(np.sqrt(error2/area)),'sampled_max_plane_residual_mm':worst,'prescribed_unit_density_min':minimum_density,'quadrature_points':count,'full_positive_pressure_requires_affine_member_surface_if_mating_face_rigid':True})
        print('PRIOR_BEARING_FLATNESS',rows[-1],flush=True)
result={'source_field':'accepted PR34 force installation','input_sha256':ident,'area_integrated_P2_plus_selected_face_terms':True,'uses_library_tetra_basis_not_candidate_map':True,'quadrature_order':6,'results':rows,'positive_pressure_on_entire_domain_not_proof_of_rigid_contact':True,'finite_deformable_head_nut_not_rejected_by_this_rigid_comparator':True,'actual_fastener_displacement_stress_and_pressure_unknown':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for p,h in ident.items():assert sha(p)==h
out=O/'prior-bearing-flatness.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
