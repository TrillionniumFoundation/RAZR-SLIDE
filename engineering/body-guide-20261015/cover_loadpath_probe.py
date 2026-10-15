from pathlib import Path
import sys,json,math,itertools,time
import numpy as np
import cadquery as cq
from scipy.optimize import linprog
R=Path('/home/qian-qi/RAZR-SLIDE-body16-review-20261015');O=Path('/tmp/razr-body-delivery-20261015')
sys.path.insert(0,str(R/'integration'))
import verify_pawl_box_guide as w
import verify_endpoint_joint_pawl as e
_,new,h=w.w.load_new(O/'body16/manifest.json');parent,prior,old,profiles=e.v.parent_native(h)
slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
p=e.scene(new,parent,prior,old,profiles,slots,0.,0.,(0.,0.))
for side in 'LR':
 p[side+'_ROOT_INNER']=new[side+'_ROOT_INNER'];p[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER'];p[side+'_OLD_COVER']=new[side+'_OLD_COVER']
assert len(p)==79
rows=[]
for side in 'LR':
 key=side+'_OLD_COVER';cover=p[key];near=[];contacts=[];c=cover.Center();origin=np.array(c.toTuple());sgn=-1 if side=='L' else 1
 b=cover.BoundingBox();print('COVER',key,'bounds',[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],'COM',list(origin),flush=True)
 for name,body in p.items():
  if name==key:continue
  ab=cover.BoundingBox();bb=body.BoundingBox()
  if any(getattr(ab,k+'min')>getattr(bb,k+'max')+.21 or getattr(bb,k+'min')>getattr(ab,k+'max')+.21 for k in 'xyz'):continue
  d=cover.distance(body)
  if d<=.20+1e-7:near.append({'part':name,'distance_mm':d,'common_mm3':w.v.common(cover,body)})
  if d>1e-6:continue
  for fi,face in enumerate(cover.Faces()):
   if face.geomType()!='PLANE':continue
   normal=np.array(face.normalAt().toTuple());point=np.array(face.Center().toTuple())
   for gi,other in enumerate(body.Faces()):
    if other.geomType()!='PLANE':continue
    n2=np.array(other.normalAt().toTuple());pt2=np.array(other.Center().toTuple())
    if np.dot(normal,n2)>-.999999 or abs(np.dot(normal,pt2-point))>1e-6:continue
    cross=face.intersect(other);area=cross.Area()
    if area<=1e-8:continue
    for patch in cross.Faces():
     if patch.Area()<=1e-8:continue
     samples=[patch.Center().toTuple()]+[v.Center().toTuple() for v in patch.Vertices()]
     contacts.append({'neighbor':name,'cover_face':fi,'other_face':gi,'area_mm2':patch.Area(),'center_mm':patch.Center().toTuple(),'normal_into_cover':list(-normal),'points_mm':samples})
 print('NEAR',side,near,flush=True);print('PLANAR_CONTACTS',side,contacts,flush=True)
 # One-newton basis load is a dimensional diagnostic only, not a design load.
 # Compressively loaded normal rays; no adhesion, screw tension, friction or stiffness.
 columns=[]
 for rec in contacts:
  n=np.array(rec['normal_into_cover'])
  for point in rec['points_mm']:
   columns.append(np.r_[n,np.cross(np.array(point)-origin,n)])
 W=np.array(columns,dtype=float).T if columns else np.empty((6,0))
 loadpoint=np.array([sgn*16.65,20.15,5.5]);force=np.array([float(sgn),0,0]);external=np.r_[force,np.cross(loadpoint-origin,force)]
 if len(columns):
  lp=linprog(np.ones(len(columns)),A_eq=W,b_eq=-external,bounds=[(0,None)]*len(columns),method='highs')
  eq={'external_force_N':list(force),'application_point_mm':list(loadpoint),'external_wrench_N_Nmm':list(external),'normal_ray_count':len(columns),'normal_wrench_rank':int(np.linalg.matrix_rank(W)),'solver_status':int(lp.status),'normal_only_equilibrium_found':bool(lp.success)}
  if lp.success:eq.update({'sum_compressive_ray_coefficients_N':float(sum(lp.x)),'residual_max':float(np.max(np.abs(W@lp.x+external)))})
 else:eq={'normal_ray_count':0,'normal_only_equilibrium_found':False,'solver_status':None}
 print('UNIT_LOAD',side,eq,flush=True)
 displacements=[]
 for axis,sign,dist in [(0,sgn,.005),(0,sgn,.02),(0,sgn,.05),(0,-sgn,.02),(1,1,.02),(1,-1,.02),(2,1,.02),(2,-1,.02)]:
  delta=[0.,0.,0.];delta[axis]=sign*dist;moved=cover.translate(tuple(delta));hits=[]
  for name,body in p.items():
   if name==key:continue
   value=w.v.common(moved,body)
   if value>w.TOL:hits.append({'part':name,'common_mm3':value})
  displacements.append({'delta_xyz_mm':delta,'positive_intersections':hits});print('COVER_SHIFT',side,delta,hits,flush=True)
 rows.append({'side':side,'cover_center_mm':list(origin),'nearby_parts':near,'actual_coplanar_contacts':contacts,'unit_normal_load_diagnostic':eq,'finite_translation_samples':displacements})
assert all(w.v.sha(path)==value for path,value in h.items())
result={'source_commit':'f1acc44d33255bb3e0b6e469531d99a674bd2fca','inputs':h,'rows':rows,'scope':'actual rigid79-part home scene; planar compressive normal contacts only, every other part held fixed; one-newton diagnostic is NOT operating load or rating','no_strength_stiffness_or_preload_qualification':True,'no_friction_or_tension_inferred':True,'finite_translation_samples_not_continuous_paths':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
(O/'cover-loadpath-probe.json').write_text(json.dumps(result,indent=2)+'\n')
