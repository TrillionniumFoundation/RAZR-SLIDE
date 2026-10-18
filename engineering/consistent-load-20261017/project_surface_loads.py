"""Reintegrate declared original affine surface loads on geometrically clipped domains.

Original mask-at-quadrature definitions are retained as a comparison, not
silently overwritten. Circular boundaries use an explicitly named inscribed
polygon. This is a normalized research pressure family, not supplier data.
"""
from pathlib import Path
import argparse,json,sys,hashlib
import numpy as np
from skfem import MeshTet,Basis,FacetBasis,ElementTetP2,ElementVector,LinearForm,asm
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'integration'))
from surface_load_functional import clip_triangle,circle_halfplanes,fit_density,integrate_face
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item(),allow_nan=False)+'\n')

def main(a):
    a.output.mkdir(parents=True,exist_ok=False);allrec=[];inputs={};result={}
    for name in ('panel','frame'):
        folder=a.volume/name/'level-2';record=json.loads((folder/'report.json').read_text())
        for f,k in [('mesh.npz','mesh_sha256'),('loads.npz','loads_sha256')]:
            assert sha(folder/f)==record[k];inputs[str(folder/f)]=record[k]
        producer=a.definitions/(name+'-ports.json');ports=json.loads(producer.read_text());inputs[str(producer)]=sha(producer)
        data=np.load(folder/'mesh.npz',allow_pickle=False);mesh=MeshTet(data['points'].T,data['tetra'].T)
        vector=Basis(mesh,ElementVector(ElementTetP2()),intorder=4);scalar=Basis(mesh,ElementTetP2(),intorder=4);axes=vector.split_indices()
        old=dict(np.load(folder/'loads.npz',allow_pickle=False));assert np.array_equal(vector.doflocs,old['xyz'])
        boundary=mesh.boundary_facets();tri=mesh.p.T[mesh.facets[:,boundary].T];lo=tri.min(axis=1);hi=tri.max(axis=1)
        newC=np.zeros((vector.N,4));newF=np.zeros((vector.N,4 if name=='panel' else 0));records=[];faces=[]
        for port in ports:
            label=port['name']
            if not (label.startswith('bolt') or label.startswith('load_')):continue
            direction=np.array(port['normal']);axis=int(np.flatnonzero(direction)[0]);tan=[j for j in range(3) if j!=axis];plane=port['plane']
            target=np.array(port['resultant_center_mm']);center=target[tan]
            ids=boundary[(abs(lo[:,axis]-plane)<1e-7)&(abs(hi[:,axis]-plane)<1e-7)]
            if label.startswith('bolt'):
                index=int(label[4:]);kind='C'
                if name=='panel':normal,offset=circle_halfplanes(center,.9,a.circle_sides)
                else:
                    theta=np.arange(6)*np.pi/3+np.pi/6;normal=np.column_stack((np.cos(theta),np.sin(theta)));offset=normal@center+1.25
            else:
                kind='F';index=['load_L_front','load_L_rear','load_R_front','load_R_rear'].index(label)
                y0,y1=(18.30,19.50) if label.endswith('front') else (22.35,23.80)
                normal=np.array([[1.,0.],[-1.,0.],[0.,-1.]]);offset=np.array([y1,-y0,-.64])
            pieces=[]
            for fi in ids:
                vertices=mesh.facets[:,fi];xy=mesh.p.T[vertices][:,tan];poly=clip_triangle(xy,normal,offset)
                if len(poly)<3:continue
                pieces.append((int(fi),vertices,xy,poly))
            density=fit_density([p[3] for p in pieces],center)
            force=np.zeros(vector.N);bvalues=[];mom=np.zeros(2);total=0.;patchrows=[]
            for fi,vertices,xy,poly in pieces:
                rec=integrate_face(xy,poly,density);w=rec['work_coefficients'];total+=rec['resultant'];mom+=rec['first_moment']
                pnodes=np.vstack((mesh.p.T[vertices],(mesh.p.T[vertices[[0,1]]].mean(axis=0)),(mesh.p.T[vertices[[0,2]]].mean(axis=0)),(mesh.p.T[vertices[[1,2]]].mean(axis=0))))
                ti=int(mesh.f2t[0,fi]);candidate=vector.element_dofs[:,ti];candidate=candidate[candidate%3==axis]
                dofs=np.array([candidate[np.argmin(np.linalg.norm(vector.doflocs[:,candidate].T-q,axis=1))] for q in pnodes])
                assert np.max(abs(vector.doflocs[:,dofs].T-pnodes))<1e-9
                np.add.at(force,dofs,direction[axis]*w[:6]);bvalues.append(w[6])
                row={'body':name,'patch':label,'kind':kind,'index':index,'axis':axis,'direction':direction,'vertices':vertices,
                     'parent_tetrahedron':ti,'triangle_xy':xy,'polygon':poly,'dofs':dofs,'work_coefficients':w,
                     'bubble_load':direction*w[6],'resultant_scalar':rec['resultant'],'first_moment':rec['first_moment'],
                     'geometric_area_mm2':rec['geometric_area'],'density_target':density.target,'density_scale':density.scale,'density_coefficients':density.coefficients}
                patchrows.append(row);faces.append(row)
            nodal=np.stack([force[ix] for ix in axes],axis=1);coords=vector.doflocs[:,axes[0]].T
            resultant=nodal.sum(axis=0);moment=np.cross(coords,nodal).sum(axis=0)
            assert abs(total-1)<1e-10 and np.max(abs(mom-center))<1e-8
            assert np.max(abs(resultant-direction))<1e-10 and np.max(abs(moment-np.cross(target,direction)))<1e-8
            # Independently reproduce the original quadrature-mask branch before
            # comparing it with a geometrically clipped domain.
            fb=FacetBasis(mesh,ElementVector(ElementTetP2()),facets=ids,intorder=6);q=np.asarray(fb.global_coordinates())
            if label.startswith('bolt') and name=='panel':mask=(q[0]-target[0])**2+(q[1]-target[1])**2<=.9**2+1e-10
            elif label.startswith('bolt'):
                mask=np.logical_and.reduce([abs(np.cos(t)*(q[0]-target[0])+np.sin(t)*(q[1]-target[1]))<=1.25+1e-10 for t in np.arange(6)*np.pi/3+np.pi/6])
            else:mask=(q[1]>=y0-1e-9)&(q[1]<=y1+1e-9)&(q[2]>.64)
            V=np.stack([np.ones_like(fb.dx),q[tan[0]]-target[tan[0]],q[tan[1]]-target[tan[1]]]);coef=np.array(port['pressure_affine_coefficients'])
            values=np.einsum('a,aij->ij',coef,V)*mask
            @LinearForm
            def load(v,w):return direction[axis]*v[axis]*values
            reproduced=asm(load,fb);oldcolumn=old[kind][:,index];err=float(np.max(abs(reproduced-oldcolumn)))
            assert err<1e-10,('original load identity did not reproduce',name,label,err)
            if kind=='C':newC[:,index]=force
            else:newF[:,index]=force
            records.append({'patch':label,'kind':kind,'index':index,'pieces':len(pieces),'area_mm2':density.area,
                'minimum_affine_density':density.minimum,'target':target,'density_coefficients_scaled':density.coefficients,
                'resultant':resultant,'moment':moment,'original_mask_load_max_error':err,
                'relative_nodal_load_change':float(np.linalg.norm(force-oldcolumn)/np.linalg.norm(oldcolumn)),
                'summed_face_bubble_work_not_resultant':float(sum(bvalues))})
            print('PROJECTED',name,label,len(pieces),'area',density.area,'old_maxerr',err,'relative_change',records[-1]['relative_nodal_load_change'],flush=True)
        np.savez_compressed(a.output/(name+'.npz'),C=newC,F=newF)
        dump(a.output/(name+'-faces.json'),faces);dump(a.output/(name+'-patches.json'),records);result[name]=records
    dump(a.output/'manifest.json',{'circle_sides':a.circle_sides,'circle_is_inscribed_polygon_not_exact_disk':True,
        'source_sha256':sha(__file__),'core_sha256':sha(R/'integration/surface_load_functional.py'),'input_sha256':inputs,
        'files_sha256':{p.name:sha(p) for p in a.output.iterdir() if p.is_file()},'original_nodal_vectors_reproduced':True,
        'affine_pressure_target_is_frozen_research_definition':True,'physical_load_or_preload_assigned':False,'result':result})
    for p,h in inputs.items():assert sha(p)==h

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--volume',type=Path,required=True);p.add_argument('--definitions',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--circle-sides',type=int,default=256)
    main(p.parse_args())
