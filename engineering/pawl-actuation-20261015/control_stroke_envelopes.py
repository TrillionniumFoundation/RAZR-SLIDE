from pathlib import Path
import sys,json
R=Path('/home/qian-qi/RAZR-SLIDE-pawl-actuation-20261015');O=Path('/tmp/razr-pawl-actuation-20261015')
sys.path.insert(0,str(R/'integration'))
import verify_pawl_actuator as w
from translation_regions import regions,checks
meta,p,h=w.load_new(O/'native-v2/manifest.json');prior,old,profiles=w.prior_native(h)
rows=[]
for side in 'LR':
 tests=[('PIN_relative_TAB',p[side+'_PIN'],(0,-3.,1.1),p[side+'_TAB']),
        ('PAWL_to_outer_root',p[side+'_PAWL'],(0,0,1.1),p[side+'_ROOT_OUTER']),
        ('PAWL_to_inner_root',p[side+'_PAWL'],(0,0,1.1),old[side+'_ROOT_INNER']),
        ('PIN_to_fixed_guide',p[side+'_PIN'],(0,0,1.1),p[side+'_GUIDE']),
        ('TAB_to_panel_with_guides',p[side+'_TAB'],(0,3.,0),p['A_BACK_PANEL'])]
 for name,body,move,fixed in tests:
  envelope,desc=regions(body,move);result=checks(envelope,fixed)
  rows.append({'side':side,'pair':name,'move_mm':move,'enclosure':desc,'result':result})
  print(side,name,'REGIONS',len(envelope),'CLEAR',result['all_regions_clear'],flush=True)
assert all(w.sha(f)==v for f,v in h.items())
result={'input_sha256':h,'rows':rows,'passed':all(x['result']['all_regions_clear'] for x in rows),'scope':'complete nominal straight control-motion enclosures only; not all phone parts, backlash reachable set, friction, force or assembly qualification','candidate_builder_imported':False,'same_CAD_kernel':True}
(O/'control-stroke-envelopes.json').write_text(json.dumps(result,indent=2)+'\n')
print('CONTINUOUS_CONTROL_RESULT',result['passed'],flush=True)
