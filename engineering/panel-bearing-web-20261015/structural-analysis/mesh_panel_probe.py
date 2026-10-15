from pathlib import Path
import argparse,hashlib,json,time
import gmsh
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--size',type=float,default=3.)
a=p.parse_args();m=json.loads(a.manifest.read_text());r=m['exports']['A_BACK_PANEL'];step=a.manifest.parent/r['path'];h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert h(step)==r['sha256'];a.output.mkdir(exist_ok=False)
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',2);gmsh.option.setString('Geometry.OCCTargetUnit','MM');gmsh.model.add('current_panel');gmsh.model.occ.importShapes(str(step));gmsh.model.occ.synchronize()
vols=gmsh.model.getEntities(3);assert len(vols)==1
mass=gmsh.model.occ.getMass(*vols[0]);assert abs(mass-r['volume_mm3'])<1e-6
surfaces=[];support=[];loads={k:[] for k in ('L_front','L_rear','R_front','R_rear')}
for _,tag in gmsh.model.getEntities(2):
 b=gmsh.model.getBoundingBox(2,tag);center=gmsh.model.occ.getCenterOfMass(2,tag);area=gmsh.model.occ.getMass(2,tag)
 rec={'tag':tag,'bounds':b,'center':center,'area':area};surfaces.append(rec)
 if abs(b[2]-.55)<1e-5 and abs(b[5]-.55)<1e-5 and any(np.linalg.norm(np.array(center[:2])-np.array([x,y]))<.02 for x in (-34.8,34.8) for y in (50.,70.)):
  support.append(tag)
 for side,sign in [('L',-1),('R',1)]:
  if abs(b[0]-sign*17.43)>1e-5 or abs(b[3]-sign*17.43)>1e-5:continue
  for label,y0,y1 in [('front',18.30,19.50),('rear',22.35,23.80)]:
   if abs(b[1]-y0)<1e-5 and abs(b[4]-y1)<1e-5 and b[2]>.64:
    loads[side+'_'+label].append(tag)
assert len(support)==4, support
assert all(len(x)==1 for x in loads.values()),loads
print('GEOMETRY',mass,'SUPPORT',support,'LOADS',loads,flush=True)
gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0);gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',32);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
gmsh.option.setNumber('Mesh.MeshSizeMin',.025);gmsh.option.setNumber('Mesh.MeshSizeMax',a.size)
# Distance refinements around actual loads and bearing rings, not altered CAD.
dist=gmsh.model.mesh.field.add('Distance');gmsh.model.mesh.field.setNumbers(dist,'FacesList',support+[x[0] for x in loads.values()]);gmsh.model.mesh.field.setNumber(dist,'Sampling',60)
thr=gmsh.model.mesh.field.add('Threshold');gmsh.model.mesh.field.setNumber(thr,'InField',dist);gmsh.model.mesh.field.setNumber(thr,'SizeMin',a.size/6);gmsh.model.mesh.field.setNumber(thr,'SizeMax',a.size);gmsh.model.mesh.field.setNumber(thr,'DistMin',1.);gmsh.model.mesh.field.setNumber(thr,'DistMax',6.);gmsh.model.mesh.field.setAsBackgroundMesh(thr)
gmsh.option.setNumber('Mesh.Algorithm3D',10);gmsh.model.mesh.generate(3);gmsh.model.mesh.optimize('Netgen')
tags,coords,_=gmsh.model.mesh.getNodes();coords=np.asarray(coords).reshape(-1,3);tags=np.asarray(tags);ordering=np.argsort(tags);tags=tags[ordering];coords=coords[ordering]
getindices=lambda n:np.searchsorted(tags,np.asarray(n))
types,etags,enodes=gmsh.model.mesh.getElements(3);assert list(types)==[4];tets=getindices(enodes[0]).reshape(-1,4)
facets={}
for label,sids in {'support':support,**loads}.items():
 triangles=[]
 for tag in sids:
  tt,_,nn=gmsh.model.mesh.getElements(2,tag);assert list(tt)==[2]
  triangles.extend(getindices(nn[0]).reshape(-1,3))
 facets[label]=np.asarray(triangles)
jac=np.stack([coords[tets[:,i]]-coords[tets[:,0]] for i in (1,2,3)],axis=2);det=np.linalg.det(jac);vol=float(np.abs(det).sum()/6)
assert np.min(np.abs(det))>1e-16
np.savez_compressed(a.output/'mesh.npz',points=coords,tetra=tets,**facets)
gmsh.write(str(a.output/'mesh.msh'));gmsh.finalize()
report={'STEP_sha256':h(step),'manifest_sha256':h(a.manifest),'native_volume_mm3':mass,'mesh_volume_mm3':vol,'volume_relative_error':abs(vol-mass)/mass,'nodes':len(coords),'tetrahedra':len(tets),'size_mm':a.size,'surfaces':surfaces,'load_surfaces':loads,'support_surfaces':support,'mesh_sha256':h(a.output/'mesh.npz'),'first_order_geometric_mapping':True,'solution_order_planned':2,'manufacturing_go':False}
(a.output/'mesh-report.json').write_text(json.dumps(report,indent=2)+'\n');print('MESH_REPORT', {k:report[k] for k in ('nodes','tetrahedra','mesh_volume_mm3','volume_relative_error')},flush=True)
