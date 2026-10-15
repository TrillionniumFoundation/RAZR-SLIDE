from pathlib import Path
import sys,json,math
R=Path('/home/qian-qi/RAZR-SLIDE-pawl-actuation-20261015');O=Path('/tmp/razr-pawl-actuation-20261015')
sys.path.insert(0,str(R/'integration'))
import verify_pawl_actuator as w
meta,p,h=w.load_new(O/'native-v2/manifest.json');prior,old,profiles=w.prior_native(h)
key_half=(w.v.G-w.v.R)*(math.hypot(1,w.v.K)+math.sqrt(2));pawl_half=(w.GR-w.PR)*math.hypot(1,w.M)
rows=[]
for q in (0.,key_half):
 for z in (0.,pawl_half,1.1-pawl_half,1.1):
  for side in 'LR':
   key=prior[side+'_KEY_YOKE'].translate((0,q+.3,0))
   pawl=p[side+'_PAWL'].translate((0,0,z))
   value=w.v.common(key,pawl)
   rows.append({'side':side,'initial_KEY_offset_mm':q,'PAWL_lift_mm':z,'attempted_KEY_withdrawal_mm':.3,'KEY_PAWL_native_common_mm3':value})
   print('RETAIN',rows[-1],flush=True)
assert all(w.sha(path)==value for path,value in h.items())
(O/'retention-probe.json').write_text(json.dumps({'input_sha256':h,'rows':rows,'scope':'isolated actual KEY/PAWL retention probe; no load, full motion, negative KEY play or automatic relock qualification'},indent=2)+'\n')
