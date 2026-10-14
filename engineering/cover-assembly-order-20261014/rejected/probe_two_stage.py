from pathlib import Path
import sys,json
R=Path('/home/qian-qi/RAZR-SLIDE-coverorder-20261014');E=Path('/home/qian-qi/RAZR-SLIDE-coverorder-evidence-20261014');sys.path.insert(0,str(R/'integration'));import cam_contact_native as n
D=E/'native-inputs';names=['ROOT_INNER','ROOT_OUTER_CONNECTED_ALL_FRAGMENTS','OLD_COVER','PARKED_PAWL','STOP_0','STOP_1']
p={name:n.single(n.cq.importers.importStep(str(D/('L_'+name+'.step'))).val()) for name in names};rows=[]
# Short normal release distances straddle the native 0.8mm cover thickness.
for root,ex in [('ROOT_INNER',1),('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS',-1)]:
 for drop in [.4,.8,.9,1.0]:
  blockers={};samples=[]
  route=[(0,0,-drop*i/8) for i in range(9)]+[(ex*d,0,-drop) for d in [.05,.25,.5,1.,2.,4.,8.,12.,20.]]
  for move in route:
   body=p[root].translate(move)
   for name,fixed in p.items():
    if name==root or name in blockers:continue
    try:vol=n.common(body,fixed)
    except Exception as exc:blockers[name]={'error':str(exc),'move':move};continue
    if vol>1e-7:blockers[name]={'common_mm3':vol,'move':move}
  row={'moving':root,'release_r_mm':drop,'route':'normal_then_lateral','blockers':blockers};rows.append(row);print(row,flush=True)
 (E/'two-stage-progress.json').write_text(json.dumps({'rows':rows},indent=2))
(E/'two-stage.json').write_text(json.dumps({'rows':rows,'not_continuous_acceptance':True,'manufacturing_go':False},indent=2))
