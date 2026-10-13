"""Read-only byte bridge between selected R50 bodies and inherited obstacle proxies."""
from pathlib import Path
import hashlib,json
workspace=Path(__file__).resolve().parents[3]
cache=workspace/'work-cad/r45-safe-cache'
old=cache/'base_R43/parent_R42/parent_R41/baseline_R40/baseline_R38/cad'
new=workspace/'work-cad/r50-checked-replay/baseline/R47/baseline/R46_source/reference'
rows=[]
for a,b in [('R38_A_R37_BYTE_IDENTICAL.brep','R38_A_unchanged.brep'),('R38_B_PROVISIONAL_STATIC_HEADER_CLEARANCE.brep','R38_B_unchanged.brep')]:
 x=(old/a).read_bytes();y=(new/b).read_bytes()
 rows.append({'historical_path':str(old/a),'selected_path':str(new/b),'historical_sha256':hashlib.sha256(x).hexdigest(),'selected_sha256':hashlib.sha256(y).hexdigest(),'byte_identical':x==y})
inputs=[cache/'minimal_source_manifest.json',cache/'r44_rear_bypass.py',Path(__file__).parents[1]/'strict-motion-audit-20261013/cad_motion_audit.py']
r={'pairs':rows,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'historical_proxy_route':'r44_rear_bypass.protected -> r21.r17_assembly(P,s,q,int(q==8.2)) OLED/FPC; r35_parts.inboard_rail/arm_guide L/R transformed with B','world_B_translation_mm':['0','s','q-8.2'],'obstacles_are_vendor_OEM_qualified':False,'manufacturing_go':False}
(Path(__file__).parent/'lineage_receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
raise SystemExit(0 if all(z['byte_identical'] for z in rows) else 1)
