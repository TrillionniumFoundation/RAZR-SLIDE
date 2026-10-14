from pathlib import Path
import sys,json,hashlib,tarfile,itertools,time
R=Path('/home/qian-qi/RAZR-SLIDE-coverorder-20261014');E=Path('/home/qian-qi/RAZR-SLIDE-coverorder-evidence-20261014');sys.path.insert(0,str(R/'integration'))
import cam_contact_native as n
G=R/'engineering/keycover-geometry-20261014';m=json.loads((G/'geometry-manifest.json').read_text());arc=G/'project-owned-geometry.tar.gz'
assert hashlib.sha256(arc.read_bytes()).hexdigest()==m['archive_sha256'];entries={x['path']:x for x in m['files']};D=E/'native-inputs';D.mkdir()
names=['ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','OLD_COVER','PARKED_PAWL','STOP_0','STOP_1','ROOT_JOIN_SCREW_0_M1x3_NOMINAL','ROOT_JOIN_SCREW_1_M1x3_NOMINAL']
parts={}
with tarfile.open(arc,'r:gz') as t:
 for side in 'LR':
  for name in names:
   rel='installation/'+side+'_'+name+'.step';data=t.extractfile(rel).read();assert hashlib.sha256(data).hexdigest()==entries[rel]['sha256'];p=D/(side+'_'+name+'.step');p.write_bytes(data)
   if side=='L':parts[name]=n.single(n.cq.importers.importStep(str(p)).val())
rows=[]
# Which participants obstruct each of the six natural rectilinear disassembly
# directions? Distances give actual rejection witnesses only, never acceptance.
directions={'e+':(-1,0,0),'e-':(1,0,0),'q+':(0,-1,0),'q-':(0,1,0),'r+':(0,0,1),'r-':(0,0,-1)}
for name in names[:6]:
 for tag,unit in directions.items():
  blockers={};first_error=None
  for d in [.05,.5,2.,6.,12.,20.]:
   moving=parts[name].translate(tuple(v*d for v in unit))
   for other,shape in parts.items():
    if other==name or other.startswith('ROOT_JOIN_SCREW') or other in blockers:continue
    try:vol=n.common(moving,shape)
    except Exception as exc:first_error=str(exc);break
    if vol>1e-7:blockers[other]={'d_mm':d,'common_mm3':vol}
   if first_error:break
  rows.append({'moving':name,'direction':tag,'unit':unit,'blockers':blockers,'error':first_error})
  print(name,tag,'BLOCKERS',list(blockers),'ERROR',first_error,flush=True)
 (E/'order-probe-progress.json').write_text(json.dumps({'rows':rows,'sample_only':True},indent=2))
(E/'order-probe.json').write_text(json.dumps({'rows':rows,'names':names,'sample_distances_mm':[.05,.5,2,6,12,20],'sample_clearance_not_proof':True,'manufacturing_go':False},indent=2))
print('NATIVE_BOUNDS')
for name,shape in parts.items():print(name,n.bounds('L',shape),flush=True)
