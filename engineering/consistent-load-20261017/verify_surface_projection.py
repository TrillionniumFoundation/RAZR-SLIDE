"""Independent geometric intersections, library quadrature and tetrahedral work.

No candidate clipping, quadrature or shape-function module is imported.
Shapely intersections and scikit-fem quadrature/P2 shapes rebuild each load.
The declared polygonal domain and affine pressure family are not physical data.
"""
from pathlib import Path
import argparse,sys,json,hashlib
import numpy as np
from shapely.geometry import Polygon,box
from skfem import MeshTet,Basis,ElementTetP2,ElementVector
from skfem.quadrature import get_quadrature_tri
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item(),allow_nan=False)+'\n')
p=argparse.ArgumentParser();p.add_argument('--projection',type=Path,required=True);p.add_argument('--volume',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
manifest=json.loads((a.projection/'manifest.json').read_text());inputs={str(a.projection/'manifest.json'):sha(a.projection/'manifest.json')}
for f,h in manifest['files_sha256'].items():assert sha(a.projection/f)==h;inputs[str(a.projection/f)]=h
Q,W=get_quadrature_tri(8);rows=[]
for name in ('panel','frame'):
    folder=a.volume/name/'level-2';d=np.load(folder/'mesh.npz',allow_pickle=False);mesh=MeshTet(d['points'].T,d['tetra'].T)
    scalar=Basis(mesh,ElementTetP2());vector=Basis(mesh,ElementVector(ElementTetP2()));axes=vector.split_indices()
    records=json.loads((a.projection/(name+'-faces.json')).read_text());given=dict(np.load(a.projection/(name+'.npz'),allow_pickle=False))
    patchmeta=json.loads((a.projection/(name+'-patches.json')).read_text());faces={tuple(sorted(f)):i for i,f in enumerate(mesh.facets.T)}
    C=np.zeros_like(given['C']);F=np.zeros_like(given['F']);bubble=[]
    for meta in patchmeta:
        pp=[r for r in records if r['patch']==meta['patch']];assert pp
        axis=pp[0]['axis'];tan=[i for i in range(3) if i!=axis];normal=np.asarray(pp[0]['direction']);plane=float(meta['target'][axis]);target=np.array(meta['target'])[tan]
        if meta['kind']=='C' and name=='panel':
            angle=np.arange(manifest['circle_sides'])*2*np.pi/manifest['circle_sides'];domain=Polygon(target+np.column_stack((np.cos(angle),np.sin(angle)))*.9)
        elif meta['kind']=='C':
            angle=np.arange(6)*np.pi/3;domain=Polygon(target+np.column_stack((np.cos(angle),np.sin(angle)))*(1.25/np.cos(np.pi/6)))
        else:
            y0,y1=(18.30,19.50) if meta['patch'].endswith('front') else (22.35,23.80)
            domain=box(y0,.64,y1,float(mesh.p[2].max()+1.))
        boundary=mesh.boundary_facets();verts=mesh.p.T[mesh.facets[:,boundary].T]
        ids=boundary[np.max(abs(verts[:,:,axis]-plane),axis=1)<1e-7];domains={}
        for fi in ids:
            key=tuple(sorted(mesh.facets[:,fi]));tri=mesh.p.T[list(key)][:,tan];poly=Polygon(tri).intersection(domain)
            if not poly.is_empty and poly.area>1e-14:domains[key]=poly
        oldkeys={tuple(sorted(r['vertices'])) for r in pp};assert set(domains)==oldkeys,('missing declared face',name,meta['patch'],len(domains),len(oldkeys))
        polys={tuple(sorted(r['vertices'])):r for r in pp};maxarea=0.;samples=[];gram=np.zeros((3,3))
        scale=np.asarray(pp[0]['density_scale']);coef=np.asarray(pp[0]['density_coefficients'])
        for key,poly in domains.items():
            rec=polys[key];maxarea=max(maxarea,poly.symmetric_difference(Polygon(rec['polygon'])).area);assert maxarea<1e-10
            xy=np.asarray(poly.exterior.coords[:-1]);fi=faces[key];ti=int(mesh.f2t[0,fi]);tet=mesh.p.T[mesh.t[:,ti]];iv=np.linalg.inv((tet[1:]-tet[0]).T)
            for j in range(1,len(xy)-1):
                edge=np.stack((xy[j]-xy[0],xy[j+1]-xy[0]));det=abs(np.linalg.det(edge));q=xy[0]+Q.T@edge;w=W*det
                if det==0:continue
                V=np.column_stack((np.ones(len(q)),(q-target)/scale));gram+=V.T@(w[:,None]*V)
                xyz=np.zeros((len(q),3));xyz[:,tan]=q;xyz[:,axis]=plane;local=(xyz-tet[0])@iv.T
                ph=np.array([scalar.elem.lbasis(local.T,k)[0] for k in range(10)]).T
                bary=np.column_stack((1-local.sum(axis=1),local));localface=[i for i,v in enumerate(mesh.t[:,ti]) if v in key]
                bub=27*np.prod(bary[:,localface],axis=1);idx=axes[axis][scalar.element_dofs[:,ti]]
                samples.append((key,idx,w,V,ph,bub))
        fitted=np.linalg.solve(gram,[1.,0.,0.]);assert np.max(abs(fitted-coef))<1e-10*max(np.max(abs(coef)),1.)
        force=np.zeros(vector.N);bubbles={key:0. for key in domains}
        for key,idx,w,V,ph,bub in samples:
            weighted=w*(V@fitted);np.add.at(force,idx,normal[axis]*(ph.T@weighted));bubbles[key]+=float(weighted@bub)
        want=given[meta['kind']][:,meta['index']];err=float(np.max(abs(force-want)));assert err<1e-11
        for key,bv in bubbles.items():
            desired=np.asarray(polys[key]['bubble_load']);val=normal*bv;assert np.max(abs(val-desired))<1e-11
            bubble.append({'kind':meta['kind'],'index':meta['index'],'vertices':list(key),'bubble_load':val})
        if meta['kind']=='C':C[:,meta['index']]=force
        else:F[:,meta['index']]=force
        rows.append({'body':name,'patch':meta['patch'],'independent_shape_domain_max_symmetric_difference_mm2':maxarea,
                     'vector_max_error':err,'complete_intersection_faces':len(domains),'recomputed_affine_fit':True})
        print('INDEPENDENT_PROJECT',name,meta['patch'],'faces',len(domains),'error',err,flush=True)
    np.savez_compressed(a.output/(name+'.npz'),C=C,F=F);dump(a.output/(name+'-bubble-loads.json'),bubble)
for f,h in inputs.items():assert sha(f)==h
assert 'surface_load_functional' not in sys.modules and 'surface_archive' not in sys.modules
dump(a.output/'report.json',{'passed':True,'patches':rows,'input_sha256':inputs,'source_sha256':sha(__file__),
      'candidate_integration_not_imported':True,'higher_quadrature_and_independent_geometric_intersection':True,
      'files_sha256':{f.name:sha(f) for f in a.output.iterdir() if f.is_file()},'physical_pressure_preload_assigned':False})
