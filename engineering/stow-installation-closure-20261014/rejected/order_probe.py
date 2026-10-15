from pathlib import Path
import sys,json,time,hashlib,collections
R=Path('/home/qian-qi/RAZR-SLIDE-stow-closure-20261014');sys.path.insert(0,str(R/'integration'))
import stow_motion_slots as s
from OCP.BRepAdaptor import BRepAdaptor_Surface
b=s.b;out=Path('/home/qian-qi/RAZR-SLIDE-stow-closure-evidence-20261014');rows=[];start=time.monotonic()
for side in 'LR':
 p,_=s.scene('STOW',side);park=p['PAWL'].translate(b.identity.evec('STOW',side,1.1));ins,_=s.planar_translation_sweep(park,b.rvec('STOW',10.))
 for n in ['ROOT_INNER',s.ROOT_NAME,'STOP_0','STOP_1']:
  c=b.strict_common(ins,p[n]);print('ORIGINAL_INSERT',side,n,c['checked_volume_mm3'],flush=True)
 print('STOP_GEOMETRY',side,collections.Counter(f.geomType() for f in p['STOP_0'].Faces()),flush=True)
 for f in p['STOP_0'].Faces():
  if f.geomType()=='CYLINDER':
   a=BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Direction();print('CYL_AXIS',a.X(),a.Y(),a.Z(),flush=True)
 for i in range(2):
  fixed={'ROOT_INNER':p['ROOT_INNER'],'PARKED_PAWL':park}
  if i==1:fixed['STOP_0']=p['STOP_0']
  for k in range(41):
   d=10.*k/40;checks=s.check(p[f'STOP_{i}'].translate(b.identity.evec('STOW',side,d)),fixed)
   row={'side':side,'op':'STOP_AFTER_PAWL','i':i,'d':d,'checks':checks,'positive':[(q['part'],q['checked_common_mm3']) for q in checks if q['checked_common_mm3']>b.EPS]};rows.append(row)
  print('STOP_AFTER_PAWL',side,i,[(r['d'],r['positive']) for r in rows if r['side']==side and r['i']==i and r['positive']],flush=True)
 for k in range(41):
  d=10.*k/40;checks=s.check(p[s.ROOT_NAME].translate(b.identity.evec('STOW',side,d)),{'ROOT_INNER':p['ROOT_INNER'],'STOP_0':p['STOP_0'],'STOP_1':p['STOP_1'],'PARKED_PAWL':park})
  row={'side':side,'op':'OUTER_AFTER_PAWL','i':2,'d':d,'checks':checks,'positive':[(q['part'],q['checked_common_mm3']) for q in checks if q['checked_common_mm3']>b.EPS]};rows.append(row)
 print('OUTER_AFTER_PAWL',side,[(r['d'],r['positive']) for r in rows if r['side']==side and r['i']==2 and r['positive']],flush=True)
 (out/'order-probe-progress.json').write_text(json.dumps({'rows':rows,'manufacturing_go':False},indent=2))
(out/'order-probe.json').write_text(json.dumps({'rows':rows,'sampled_only':True,'elapsed_seconds':time.monotonic()-start,'manufacturing_go':False},indent=2));print('DONE',len(rows),flush=True)
