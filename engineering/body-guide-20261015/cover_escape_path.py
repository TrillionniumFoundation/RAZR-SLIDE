from pathlib import Path
import sys,json
R=Path('/home/qian-qi/RAZR-SLIDE-body16-review-20261015');O=Path('/tmp/razr-body-delivery-20261015');sys.path.insert(0,str(R/'integration'))
import verify_pawl_box_guide as w
import verify_endpoint_joint_pawl as e
_,new,h=w.w.load_new(O/'body16/manifest.json');parent,prior,old,profiles=e.v.parent_native(h)
slots={s:e.native_slot(new[s+'_TAB']) for s in 'LR'}
p=e.scene(new,parent,prior,old,profiles,slots,0.,0.,(0.,0.))
for side in 'LR':
 p[side+'_ROOT_INNER']=new[side+'_ROOT_INNER'];p[side+'_ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER'];p[side+'_OLD_COVER']=new[side+'_OLD_COVER']
rows=[]
for side in 'LR':
 key=side+'_OLD_COVER';move=((-1 if side=='L' else 1)*.05,0.,0.)
 row=e.v.motion(key,p[key],move,{k:b for k,b in p.items() if k!=key});rows.append(row)
 print('FULL_OUTWARD_COVER_PATH',side,'checks',len(row['checks']),'failed',row['failed'],flush=True)
for key in p:
 if key.startswith('CARTRIDGE_'):
  b=p[key].BoundingBox();print('EXISTING_MOUNT',key,[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],flush=True)
for side in 'LR':
 for name in ('ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'):
  b=p[side+'_'+name].BoundingBox();print('ROOT',side,name,[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],flush=True)
assert all(w.v.sha(f)==v for f,v in h.items())
r={'functional_commit':'f1acc44d33255bb3e0b6e469531d99a674bd2fca','input_sha256':h,'paths':rows,'all_paths_clear':not any(row['failed'] for row in rows),'scope':'two complete rigid outward0.05mm cover paths versus all other78 scene parts, home only; exposes geometric holding gap, not physical detached-cover or failure-load prediction','does_not_model_friction_adhesion_or_preload':True,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
(O/'cover-escape-path.json').write_text(json.dumps(r,indent=2)+'\n')
