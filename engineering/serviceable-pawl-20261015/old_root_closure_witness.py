from pathlib import Path
import sys,json
sys.path.insert(0,'integration')
import verify_serviceable_pawl as v
O=Path('/tmp/razr-serviceable-control-20261015')
_,n,h=v.load(O/'native-v1/manifest.json');rows=[]
for side in 'LR':
 root=n[side+'_ROOT_OUTER'];pawl=n[side+'_PAWL'].translate((0,0,1.1))
 for z in (0.,.1,.25,.5,1.,1.5,2.,2.5,3.):
  value=v.common(root.translate((0,0,z)),pawl)
  rows.append({'side':side,'root_Z_above_final_mm':z,'PAWL_outward_mm':1.1,'actual_common_mm3':value})
  print(rows[-1],flush=True)
(O/'old-root-closure-witness.json').write_text(json.dumps({'input_sha256':h,'rows':rows,'source':'native-v1; complete actual bodies, not swept carrier only'},indent=2)+'\n')
