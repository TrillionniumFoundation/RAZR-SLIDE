from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path.cwd()/'integration'));import verify_endpoint_joint_pawl as q
O=Path('/tmp/razr-endpoint-joint-20261015');meta,new,h=q.v.load(O/'native-v1/manifest.json');prev=q.frozen(h);parent,prior,old,profiles=q.v.parent_native(h);slots={s:q.native_slot(new[s+'_TAB']) for s in 'LR'}
home=q.scene(new,parent,prior,old,profiles,slots,0.,0.,(0.,0.));detach={s+'_'+r for s in 'LR' for r in q.v.INSERT_ROLES}
installed={k:b for k,b in home.items() if k not in detach|{'A_FRAME','B_SHELL'}};rows=[]
for side in 'LR':
 for role,vector in q.v.plan(side):
  result=q.roof_motion_partition(role,home[role],prev[role],vector,installed) if role.endswith('_ROOF') else q.v.motion(role,home[role],vector,installed)
  rows.append(result);installed[role]=home[role];print(role,'checks',len(result['checks']),'failed',len(result['failed']),flush=True)
assert all(q.sha(path)==value for path,value in h.items())
r={'source_sha256':meta['source_sha256'],'reader_sha256':q.sha(Path.cwd()/'integration/verify_endpoint_joint_pawl.py'),'input_sha256':h,'assembly_stages':rows,'passed':not any(x['failed'] for x in rows),'scope':'all fourteen insertion steps only; not a second complete scene run; original full report retained'}
(O/'corrected-assembly.json').write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['passed'] else 1)
