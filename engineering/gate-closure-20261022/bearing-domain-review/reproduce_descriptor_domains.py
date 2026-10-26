#!/usr/bin/env python3
"""Actual adapter/restore domain guards on synthetic 12 DOFs; never original FE/QP."""
import argparse,ast,copy,hashlib,json,sys,types
from pathlib import Path
import numpy as np
from scipy.sparse import csc_matrix,hstack
BASE=Path('/dev/shm/razr-slide-1104895ba7b9')
p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--expect-fixed',action='store_true');args=p.parse_args()
repo=BASE/'repo';stage=args.source_dir.resolve()
sys.path[:0]=[str(stage),str(repo/'integration')]
from continuation_support import validate_restored_columns,restore_verified
from bearing_checkpoint import validate_payload
from contact_exchange import ExactResponseCache
from surface_load_functional import shape_values
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
sources={str(stage/n):sha(stage/n) for n in ['continuation_support.py','continued_rigid_bearing_probe.py','bearing_checkpoint.py']}
sources.update({str(repo/'integration'/n):sha(repo/'integration'/n) for n in ['contact_exchange.py','surface_load_functional.py']})
tree=ast.parse((stage/'continued_rigid_bearing_probe.py').read_text())
one=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='one_map')
cases=[('bearing-outside-triangle',[2.,2.],False,False,False),
       ('bearing-inside-triangle-outside-clipped-face',[.4,.4],False,True,False),
       ('contact-outside-cell',[2.,2.],True,False,False),
       ('bearing-original-corner',[0.,0.],False,False,True),
       ('bearing-original-edge',[.5,.5],False,False,True),
       ('contact-original-corner',[1.,0.],True,False,True),
       ('contact-original-edge',[.5,.5],True,False,True)]
rows=[]
for name,xy,is_contact,clipped,inside in cases:
 faces=[]
 for body,offset in [('panel',0),('frame',6)]:
  for index in range(4):
   faces.append({'body':body,'index':index,'label':body+str(index),'polygon':[[0.,0.],[1.,0.],[0.,1.]],
    'triangle_xy':[[0.,0.],[1.,0.],[0.,1.]],'normal_sign':1.,'offset':offset,'dofs':list(range(6)),'trace_index':None})
 if clipped:faces[0]['polygon']=[[0.,0.],[.5,0.],[0.,.5]]
 cells=[{'label':'contact-cell-0','gap':0.,'vertices':[[0.,0.],[1.,0.],[0.,1.]]}]
 def contact_map(point):
  weights=shape_values(cells[point['cell']]['vertices'],[point['xy']])[0][:6]
  return csc_matrix((weights,(np.arange(6),np.zeros(6,dtype=int))),shape=(12,1))
 namespace={'csc_matrix':csc_matrix,'np':np,'n':12,'ctx':{'one_map':contact_map},'faces':faces,
            'bodies':{'panel':{'N':6},'frame':{'N':6}},'shape_values':shape_values}
 exec(compile(ast.Module(body=[copy.deepcopy(one)],type_ignores=[]),str(stage/'continued_rigid_bearing_probe.py'),'exec'),namespace)
 original=[{'kind':'bolt','index':i} for i in range(4)]
 points=original+[{'kind':'bearing','face':i,'body':f['body'],'index':f['index'],'patch':f['label'],'xy':[.2,.2],'gap':0.} for i,f in enumerate(faces)]
 if is_contact:points.append({'kind':'contact','cell':0,'patch':'contact-cell-0','xy':xy,'gap':0.})
 else:points[4]['xy']=xy
 C=hstack([namespace['one_map'](point) for point in points],format='csc');H=(C.T@C).toarray()
 state={'phase':'ready_for_qp','next_iteration':0,'history':[],'guess':None}
 identity={'scope':'synthetic 12-DOF identity response, not original FE'}
 row={'case':name,'domain_member':inside,'xy':xy,'all_8_original_bearing_domains_present':True}
 try:
  validate_payload(C,H,points,state,n_dofs=12,parameters={'max_exchanges':4,'maximum_columns':20})
  saved=types.SimpleNamespace(points=points,C=C,H=H,state=state)
  validate_restored_columns(saved,original,namespace['one_map'],12,faces,cells)
  cache=ExactResponseCache(12,lambda v:np.asarray(v).copy(),identity,response_block=lambda v:np.asarray(v).copy())
  probe=restore_verified(cache,C,H,identity)
  row.update(accepted=True,response_probes=probe.probes,response_calls=probe.response_calls,
             largest_relative_error=probe.largest_relative_error)
 except ValueError as exc:
  row.update(accepted=False,rejection=str(exc))
 expected=inside if args.expect_fixed else True
 row['expected_acceptance']=expected
 row['expectation_met']=row['accepted']==expected
 if args.expect_fixed and not inside and not row['accepted']:
  row['targeted_domain_reason']=any(word in row['rejection'].lower() for word in ['domain','polygon','outside'])
  row['expectation_met'] &= row['targeted_domain_reason']
 rows.append(row)
after={name:sha(name) for name in sources}
result={'schema':'razr-bearing-independent-domain-controls-v1','scope':'7 synthetic 12-DOF descriptor controls. Actual adapter bearing one_map and actual payload/descriptor/restore functions; synthetic contact interpolation and identity response. No real FE or QP.',
 'source_sha256_before':sources,'source_sha256_after':after,'sources_unchanged':sources==after,
 'expected_mode':'fixed-reject-domain-extrapolation' if args.expect_fixed else 'pre-fix-domain-extrapolation-reproduction',
 'checks':len(rows),'matched_expected':sum(r['expectation_met'] for r in rows),'rows':rows}
args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({'report':str(args.output),'checks':len(rows),'matched_expected':result['matched_expected'],'sources_unchanged':sources==after},indent=2))
for row in rows:print(json.dumps(row))
raise SystemExit(0 if result['matched_expected']==len(rows) and sources==after else 1)
