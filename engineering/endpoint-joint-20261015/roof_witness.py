from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()/'integration'));import verify_endpoint_joint_pawl as q
O=Path('/tmp/razr-endpoint-joint-20261015');_,new,h=q.v.load(O/'native-v1/manifest.json');prev=q.frozen(h);parent,prior,old,profiles=q.v.parent_native(h);slots={s:q.native_slot(new[s+'_TAB']) for s in 'LR'}
home=q.scene(new,parent,prior,old,profiles,slots,0.,0.,(0.,0.));rows=[];proof=[]
for side in 'LR':
 targets={k:home[k] for k in ('A_BACK_PANEL',side+'_PAWL',side+'_SHOULDER_PIN_NOMINAL')}
 for z in (0.,.01,.1,.3,.5,1.,2.,4.,12.):
  values={k:q.v.common(new[side+'_ROOF'].translate((0,0,z)),b) for k,b in targets.items()};rows.append({'side':side,'z':z,'commons':values});print('ACTUAL',rows[-1],flush=True)
 added=new[side+'_ROOF'].cut(prev[side+'_ROOF']);leaves=q.v.w.v.n.whole_material(added)[0]
 reconstructed=prev[side+'_ROOF']
 for body in leaves:reconstructed=reconstructed.fuse(body).clean()
 q.v.w.v.equal(new[side+'_ROOF'],reconstructed)
 for i,body in enumerate([prev[side+'_ROOF'],*leaves]):
  result=q.v.motion(side+'_ROOF_PART_'+str(i),body,(0,0,12.),targets)
  proof.append(result);print('PART',i,'FAILED',result['failed'],flush=True)
(O/'roof-witness.json').write_text(json.dumps({'actual_pose_witnesses':rows,'material_partition_proof':proof,'scope':'finite poses plus exact material partition conservative sweep for the reported obstacles'},indent=2)+'\n')
