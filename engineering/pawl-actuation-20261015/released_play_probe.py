from pathlib import Path
import sys,json,math
R=Path('/home/qian-qi/RAZR-SLIDE-pawl-actuation-20261015');O=Path('/tmp/razr-pawl-actuation-20261015');sys.path.insert(0,str(R/'integration'))
import verify_pawl_actuator as w
_,p,h=w.load_new(O/'native-v2/manifest.json');prior,old,profiles=w.prior_native(h)
half=(w.GR-w.PR)*math.hypot(1,w.M);rows=[]
for s,d in ((.1,0.),(2.,0.),(5.,0.),(40.,0.),(79.75,0.),(79.75,8.2)):
 parts=w.scene(p,prior,old,profiles,s,d,(3.,3.),actuator_flank=-half)
 result=w.pairs(parts,{'L_PAWL','R_PAWL','L_TAB','R_TAB'});bad=[x for x in result if x['common_mm3']>w.TOL]
 rows.append({'slide_mm':s,'descent_mm':d,'tab_mm':3.,'PAWL_outward_mm':1.1-half,'positive_pairs':bad,'pair_count':len(result)})
 print('MINIMUM_RELEASE',s,d,'BAD',bad,flush=True)
assert all(w.sha(f)==v for f,v in h.items())
(O/'released-play-probe.json').write_text(json.dumps({'input_sha256':h,'rows':rows,'all_checked_released_flank_states_clear':not any(x['positive_pairs'] for x in rows),'scope':'six sampled whole-scene changed-part checks on minimum slot-permitted PAWL release; no full continuous sweep or forces'},indent=2)+'\n')
