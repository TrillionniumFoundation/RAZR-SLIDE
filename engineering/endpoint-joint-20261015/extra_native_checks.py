from pathlib import Path
import sys,json,math,shutil,tempfile
R=Path('/home/qian-qi/RAZR-SLIDE-endpoint-joint-20261015');O=Path('/tmp/razr-endpoint-joint-20261015')
sys.path.insert(0,str(R/'integration'));import verify_endpoint_joint_pawl as q
mp=O/'native-v1/manifest.json';meta,new,h=q.v.load(mp);prev=q.frozen(h);parent,prior,old,profiles=q.v.parent_native(h)
slots={s:q.native_slot(new[s+'_TAB']) for s in 'LR'};keyhalf=(q.v.w.v.G-q.v.w.v.R)*(math.hypot(1,q.v.w.v.K)+math.sqrt(2))
changed={'A_BACK_PANEL'}|{s+'_'+k for s in 'LR' for k in ('PAWL','SHOULDER_PIN_NOMINAL','TAB','ROOF')}
rows=[];distances=[]
for u in (0.,3.):
 for flanks in ((-1,1),(1,-1)):
  p=q.scene(new,parent,prior,old,profiles,slots,0.,0.,(u,u),flanks,keyhalf)
  pairs=q.v.w.pairs(p,changed);bad=[x for x in pairs if x['common_mm3']>q.TOL]
  rows.append({'tab_mm':u,'left_right_flanks':flanks,'positive_KEY_play_mm':keyhalf,'pair_count':len(pairs),'positive_pairs':bad});print('MIXED',rows[-1],flush=True)
for side in 'LR':
 for u in (0.,3.):
  for flank in (-1,1):
   spec=slots[side];z=spec['origin']+spec['slope']*u+flank*spec['halfwidth'];pawl=new[side+'_PAWL'].translate((0,0,z))
   for name,root in [('INNER',old[side+'_ROOT_INNER']),('OUTER',new[side+'_ROOT_OUTER'])]:
    value=pawl.distance(root);hit=q.v.common(pawl,root)
    distances.append({'side':side,'tab':u,'flank':flank,'root':name,'PAWL_shift_mm':z,'minimum_native_distance_mm':value,'common_mm3':hit})
print('DISTANCES',json.dumps(distances),flush=True)
neg=[]
for case in ('missing_part','changed_bytes','nonfinite_volume','symlink'):
 with tempfile.TemporaryDirectory(prefix='endpoint-reader-negative-',dir=O) as td:
  folder=Path(td);data=json.loads(mp.read_text())
  for f in mp.parent.glob('*.step'):shutil.copyfile(f,folder/f.name)
  if case=='missing_part':data['exports'].pop('R_TAB')
  if case=='changed_bytes':
   f=folder/'R_TAB.step';f.write_bytes(f.read_bytes()+b'\nCHANGED\n')
  if case=='nonfinite_volume':data['exports']['R_TAB']['volume_mm3']=float('nan')
  if case=='symlink':
   f=folder/'R_TAB.step';f.unlink();f.symlink_to(mp.parent/'R_TAB.step')
  p=folder/'manifest.json';p.write_text(json.dumps(data))
  try:q.v.load(p)
  except (ValueError,OSError) as err:neg.append({'case':case,'rejected':True,'error':str(err)})
  else:raise RuntimeError('invalid native input accepted')
assert all(q.sha(f)==x for f,x in h.items())
r={'input_sha256':h,'reader_sha256':q.sha(R/'integration/verify_endpoint_joint_pawl.py'),'mixed_side_slot_probes':rows,'minimum_root_distances':distances,'negative_controls':neg,'mixed_side_probes_clear':not any(x['positive_pairs'] for x in rows),'scope':'additional local sampled mixed axial slot branches and native distances; no process/lateral/thermal/force guarantees; not counted as unit tests'}
(O/'extra-native-checks.json').write_text(json.dumps(r,indent=2)+'\n');print('EXTRA_COMPLETE',r['mixed_side_probes_clear'],len(neg),flush=True)
