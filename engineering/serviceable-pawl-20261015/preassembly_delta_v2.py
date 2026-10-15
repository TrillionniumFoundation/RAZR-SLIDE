"""Affected earlier cartridge stages for the new PAWL socket and widened root.
The controls/panel are installed later. Keeps the original held/parked assembly
boundary condition; this is not fixture force or KEY coupled insertion proof.
"""
from pathlib import Path
import sys,json
R=Path('/home/qian-qi/RAZR-SLIDE-serviceable-control-20261015');O=Path('/tmp/razr-serviceable-control-20261015');sys.path.insert(0,str(R/'integration'))
import verify_serviceable_pawl as v
from verify_thin_mechanism import stage_plan,placement,motion_check
meta,new,h=v.load(O/'native-v2/manifest.json');assert meta['source_sha256']==v.sha(R/'integration/serviceable_pawl.py');parent,prior,old,profiles=v.parent_native(h)
rows=[]
for side in 'LR':
 sign=-1 if side=='L' else 1
 parts={k:old[side+'_'+k] for k in v.w.v.PARTS}
 parts['PAWL']=new[side+'_PAWL'];parts['ROOT_OUTER_CONNECTED_ALL_FRAGMENTS']=new[side+'_ROOT_OUTER']
 parts['PARKED_PAWL']=parts['PAWL'].translate((0,0,1.1))
 parts['JAW_LOWER']=placement(v.w.v.n.box(side,-.8,.8,12.15,12.55,-3.4,-2.9),side).translate((0,6.,0))
 parts['JAW_UPPER']=placement(v.w.v.n.box(side,-.8,.8,12.15,12.55,-2.5,-2.),side).translate((0,6.,0))
 changed={'PARKED_PAWL','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'}
 installed={'JAW_LOWER':parts['JAW_LOWER']}
 for role,vec in stage_plan(side):
  global_vec=(sign*vec[2],-vec[1],sign*vec[0])
  # Check the stated transform against the frozen reader's actual rigid map.
  origin=placement(v.cq.Vertex.makeVertex(0,0,0),side).Center()
  point=placement(v.cq.Vertex.makeVertex(*vec),side).Center()
  assert max(abs(x-y) for x,y in zip(point.sub(origin).toTuple(),global_vec))<1e-7
  affected={k:b for k,b in installed.items() if role in changed or k in changed}
  if affected:
   row=motion_check(side+'_'+role,parts[role],global_vec,affected,relative=role.startswith('ROOT_') and 'SCREW' not in role)
   row['side']=side;row['role']=role;rows.append(row)
   print(side,role,'affected',len(affected),'positive',row['positive_pairs'],flush=True)
  installed[role]=parts[role]
 assert set(installed)-{'JAW_LOWER','JAW_UPPER'}==(v.w.v.PARTS-{'KEY','PAWL'})|{'PARKED_PAWL'}
assert all(v.sha(path)==value for path,value in h.items())
result={'input_sha256':h,'stages':rows,'affected_pair_count':sum(x['pairs'] for x in rows),'passed':not any(x['positive_pairs'] for x in rows),'same_CAD_kernel':True,'candidate_builder_imported':False,'scope':__doc__}
(O/'preassembly-delta-v2.json').write_text(json.dumps(result,indent=2)+'\n');print('PREASSEMBLY_DELTA',result['passed'],result['affected_pair_count'],flush=True)
