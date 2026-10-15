from pathlib import Path
import sys,json,gzip,hashlib,time,traceback
R=Path('/home/qian-qi/RAZR-SLIDE-stow-closure-20261014');sys.path.insert(0,str(R/'integration'))
import stow_motion_slots as s
from straight_envelope import envelope
b=s.b;out=Path('/home/qian-qi/RAZR-SLIDE-stow-closure-evidence-20261014/wide-web-probe');out.mkdir();rows=[]
ref,returned,inserted,_=s.canonical_envelopes('L');old=ref[s.ROOT_NAME];park=ref['PAWL'].translate(b.identity.evec('STOW','L',1.1))
fixed={'STOP_0':ref['STOP_0'],'STOP_1':ref['STOP_1'],'ROOT_INNER':ref['ROOT_INNER'],'PARKED_PAWL':park};sweeps={n:envelope(sh,b.identity.evec('STOW','L',-10.))[0] for n,sh in fixed.items()}
bb=old.BoundingBox();print('ORIGINAL_ROOT_BOUNDS',{'e':[-bb.xmax-34.75,-bb.xmin-34.75],'q':[1.2-bb.ymax,1.2-bb.ymin],'r':[bb.zmin-10,bb.zmax-10]},flush=True)
history=json.loads(gzip.decompress((R/'engineering/workplan-execution-20261014/integration/sequence-native-report.json.gz').read_bytes()))
cutters=[sh for n,sh in ref.items() if n not in (s.ROOT_NAME,'PAWL')]
for row in history['cam_brackets']:
 if row['port']=='STOW' and row['side']=='L':
  cutters.append(ref['KEY'].translate(b.identity.qvec('STOW',row['q_mm'])))
  for i,lift in enumerate(row['actual_cam_collision_free_lifts_mm']):cutters.append(ref['STOP_'+str(i)].translate(b.rvec('STOW',lift-1.14)))
for qmax in (2.75,3.30,4.0,4.85):
 try:
  web=b.world(b.box(.05,.30,1.10,qmax,-9.60,9.35),'STOW','L')
  for cutter in [*cutters,*sweeps.values()]:web=web.cut(cutter).clean()
  leaves=s.volume_leaves(web);core=old.cut(returned).cut(inserted).clean();candidate=core
  for piece in web.Solids():candidate=candidate.fuse(piece)
  candidate=candidate.clean();solids=s.volume_leaves(candidate);p=out/f'qmax-{qmax}.brep';b.cq.exporters.export(candidate,str(p))
  row={'qmax':qmax,'web_components':len(leaves),'root_components':len(solids),'volumes':solids,'candidate_brep':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  if len(solids)==1:
   row['all_relative_checks']={n:b.strict_common(candidate,sh)['checked_volume_mm3'] for n,sh in sweeps.items()}
   row['added_mm3']=sum(s.volume_leaves(candidate.cut(old)));row['removed_mm3']=sum(s.volume_leaves(old.cut(candidate)))
   row['bounds_delta']={k:getattr(candidate.BoundingBox(),k)-getattr(bb,k) for k in ('xmin','xmax','ymin','ymax','zmin','zmax')}
  rows.append(row);print(row,flush=True)
 except Exception as exc:rows.append({'qmax':qmax,'exception':str(exc),'traceback':traceback.format_exc()});print('REJECTED',qmax,str(exc),flush=True)
 (out/'progress.json').write_text(json.dumps({'rows':rows,'manufacturing_go':False},indent=2))
(out/'report.json').write_text(json.dumps({'rows':rows,'only_local_left_sensitivity':True,'manufacturing_go':False},indent=2))
