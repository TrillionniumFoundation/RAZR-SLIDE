"""Independent K3 material and oriented-face checks from frozen scalar contract.

This reader helper never imports the K3 candidate builder. It uses the same
locked CAD kernel and explicitly makes no independent-kernel claim. All false
geometric outcomes and native evaluation exceptions are retained individually.
"""
from __future__ import annotations
import math
from k3_pilot_common import public_failure

TOL=1e-7

def mirrored(side,limits):
 lo,hi=[list(row) for row in limits]
 if side=='L':lo[0],hi[0]=-hi[0],-lo[0]
 return lo,hi

def solid_box(cq,limits):
 lo,hi=limits
 return cq.Solid.makeBox(*(hi[i]-lo[i] for i in range(3)),cq.Vector(*lo))

def face_area(shape):
 faces=shape.Faces()
 if not faces:return 0.
 if not shape.isValid():raise ValueError('invalid native face boolean topology')
 values=[float(f.Area()) for f in faces]
 if not all(math.isfinite(v) and v>=0 for v in values):raise ValueError('invalid native oriented face area')
 return math.fsum(values)

def native_patch(body,cq,axis,plane,u,v,orientation):
 other=[i for i in range(3) if i!=axis];vertices=[]
 for a,b in ((u[0],v[0]),(u[1],v[0]),(u[1],v[1]),(u[0],v[1])):
  xyz=[0.,0.,0.];xyz[axis]=plane;xyz[other[0]]=a;xyz[other[1]]=b;vertices.append(cq.Vector(*xyz))
 rectangle=cq.Face.makeFromWires(cq.Wire.makePolygon(vertices+[vertices[0]]))
 faces=[];records=[]
 for index,face in enumerate(body.Faces()):
  if face.geomType()!='PLANE':continue
  normal=face.normalAt().toTuple();coords=[x.Center().toTuple() for x in face.Vertices()]
  if not coords or abs(normal[axis]-orientation)>1e-9 or any(abs(normal[i])>1e-9 for i in other):continue
  error=max(abs(x[axis]-plane) for x in coords)
  if error>TOL:continue
  cut=face.intersect(rectangle);area=face_area(cut)
  if area>0:
   faces.extend(cut.Faces());records.append({'face_index':index,'outward_normal':list(normal),'actual_clipped_area_mm2':area,'max_plane_error_mm':error})
 shape=cq.Compound.makeCompound(faces)
 return shape,{'area_mm2':face_area(shape),'native_faces':records,'plane_axis':axis,'plane_coordinate_mm':plane,'normal_component':orientation}

def area_identity(a,b):
 lost=face_area(a.cut(b));gained=face_area(b.cut(a))
 return {'a_minus_b_mm2':lost,'b_minus_a_mm2':gained,'passed':max(lost,gained)<=TOL}

def all_checks(parts,original_panel,keys,design,q_by_side,p,cq,budget,emit):
 """Evaluate every early gate independently, retaining false measurements."""
 rows={};material={};panel=parts['A_BACK_PANEL'];boxes={}
 def evaluate(label,fn):
  budget.check()
  try:
   row=fn();row['evaluated']=True
  except Exception as exc:row={'evaluated':False,'passed':False,**public_failure(exc)}
  rows[label]=row;emit(rows);return row
 def material_identity(a,b):
  av=p.volume(a.cut(b));bv=p.volume(b.cut(a));return {'a_minus_b_mm3':av,'b_minus_a_mm3':bv,'passed':max(av,bv)<=TOL}
 rebuilt=original_panel
 for side in 'LR':
  for role,limits in design['additive_boxes_R_mm'].items():
   name=side+'_'+role;body=solid_box(cq,mirrored(side,limits));boxes[name]=body;material[name]=body
   rebuilt=rebuilt.fuse(body).clean()
 evaluate('whole_panel_reconstruction',lambda:material_identity(rebuilt,panel))
 def panel_account():
  old=p.volume(original_panel);new=p.volume(panel);removed=p.volume(original_panel.cut(panel));added=p.volume(panel.cut(original_panel))
  balance=old+added-new;solids,_=p.whole_material(panel)
  return {'old_mm3':old,'new_mm3':new,'removed_mm3':removed,'added_mm3':added,'signed_balance_error_mm3':balance,
   'solid_count':len(solids),'valid_topology':panel.isValid(),'passed':removed<=TOL and abs(balance)<=TOL and len(solids)==1 and panel.isValid()}
 evaluate('panel_addition_only_and_connected',panel_account)
 for side in 'LR':
  front=solid_box(cq,mirrored(side,design['original_front_post_R_mm']))
  def front_check(front=front):
   lost=p.volume(front.cut(original_panel));return {'original_front_post_outside_old_panel_mm3':lost,'passed':lost<=TOL}
  evaluate(side+'_complete_original_front_post',front_check)
  for role,limits in design['additive_boxes_R_mm'].items():
   body=boxes[side+'_'+role]
   def join_check(body=body,role=role,front=front,limits=limits):
    overlap=p.volume(body.intersect(original_panel));added=p.volume(body.cut(original_panel))
    row={'join_to_original_panel_mm3':overlap,'new_component_outside_original_panel_mm3':added,'passed':overlap>TOL and added>TOL}
    if role=='upper_toe':
     actual=p.volume(body.intersect(front));expected=(limits[1][0]-limits[0][0])*(18.5-18.3)*(limits[1][2]-limits[0][2])
     row.update(join_to_front_post_mm3=actual,declared_front_post_join_mm3=expected)
     row['passed']=row['passed'] and abs(actual-expected)<=TOL
    return row
   evaluate(side+'_'+role+'_positive_join',join_check)
  sign=-1 if side=='L' else 1
  for role,y in design['unmodified_existing_cover_patch_Y_mm'].items():
   def functional(y=y,sign=sign):
    args=(cq,0,sign*17.43,y,design['unmodified_existing_cover_patch_Z_search_mm'],-sign)
    before,br=native_patch(original_panel,*args);after,ar=native_patch(panel,*args)
    equality=area_identity(before,after)
    return {'original_native_patch':br,'candidate_native_patch':ar,'directed_area_difference':equality,
     'passed':br['area_mm2']>TOL and ar['area_mm2']>TOL and equality['passed']}
   evaluate(side+'_'+role+'_original_functional_face',functional)
  q=q_by_side[side]
  if not 0<=q<=12:raise ValueError('reader cannot extend actual source factory q')
  for end,at,normal in (('lower',0.,1.),('upper',12.,-1.)):
   if abs(q-at)>TOL:continue
   lo,hi=mirrored(side,[[17.48,0.,4.02],[18.38,1.,4.38]])
   plane=design['declared_stop_contact_planes_Y_mm'][end]
   def contact(side=side,lo=lo,hi=hi,plane=plane,normal=normal):
    a,ar=native_patch(panel,cq,1,plane,[lo[0],hi[0]],[lo[2],hi[2]],normal)
    b,br=native_patch(parts[side+'_KEY'],cq,1,plane,[lo[0],hi[0]],[lo[2],hi[2]],-normal)
    equal=area_identity(a,b);area=face_area(a.intersect(b));expected=design['declared_contact_patch_area_mm2']
    actual=p.strict_common(parts[side+'_KEY'],panel)
    return {'panel_patch':ar,'KEY_patch':br,'actual_contact_area_mm2':area,'expected_contact_area_mm2':expected,
     'directed_area_difference':equal,'whole_KEY_panel_at_contact_Common':actual,
     'passed':equal['passed'] and abs(area-expected)<=TOL and actual['common_mm3']<=TOL}
   evaluate(side+'_'+end+'_endpoint_contact',contact)
   for delta in design['negative_control_overtravel_mm']:
    outside=at+(-delta if end=='lower' else delta);inside=at+(delta if end=='lower' else -delta)
    name=side+'_'+end+'_'+str(delta).replace('.','p')
    outside_key=p.single(keys.candidate_q0[side].translate((0.,outside,0.)))
    inside_key=p.single(keys.candidate_q0[side].translate((0.,inside,0.)))
    material[name+'_overtravel_KEY']=outside_key;material[name+'_inward_KEY']=inside_key
    def control(outside_key=outside_key,inside_key=inside_key,outside=outside,inside=inside,delta=delta,name=name):
     rejected=p.strict_common(outside_key,panel);free=p.strict_common(inside_key,panel)
     expected=design['declared_contact_patch_area_mm2']*delta
     common=outside_key.intersect(panel);direct=p.volume(common)
     if direct>0:material[name+'_overtravel_Common']=common
     return {'q_outside_source_profile_mm':outside,'q_inward_mm':inside,'delta_mm':delta,
      'whole_KEY_overtravel_Common':rejected,'whole_KEY_inward_Common':free,'direct_Common_mm3':direct,
      'expected_crossbar_overlap_mm3':expected,'complete_factory_outside_source_profile_called':False,
      'passed':rejected['common_mm3']>TOL and rejected['common_mm3']>=expected-TOL and free['common_mm3']<=TOL and abs(direct-rejected['common_mm3'])<=TOL}
    evaluate(name+'_whole_KEY_negative_and_release_controls',control)
 return rows,material
