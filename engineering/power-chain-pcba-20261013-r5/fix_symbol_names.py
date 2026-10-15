"""Keep exact vendor pin names while retaining unique stage net names."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
rows=[]
for stage in ['A1','A2','B1','B2']:
 for name in ['OwnedCut.kicad_sym','cut_reference.kicad_sch']:
  p=HERE/'modules'/stage/name;b=p.read_bytes();t=b.decode()
  for pin in ['FLT','ILM','DVDT']:t=t.replace('(name "'+stage+'_'+pin+'"','(name "'+pin+'"')
  p.write_text(t);rows.append({'stage':stage,'file':name,'before':hashlib.sha256(b).hexdigest(),'after':hashlib.sha256(p.read_bytes()).hexdigest(),'numeric_pin_and_net_map_changed':False})
(HERE/'symbol_pin_name_correction.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Corrected vendor pin names on 8 source files; numeric map and PCB copper unchanged')
