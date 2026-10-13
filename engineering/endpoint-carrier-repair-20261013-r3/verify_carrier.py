"""Independent actual STEP carrier check; never imports the builder."""
import sys,json,hashlib,platform
from pathlib import Path
import cadquery as cq
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
support=HERE/'support'
if support.exists():sys.path.insert(0,str(support))
else:
 sys.path.insert(0,str(HERE.parents[1]/'engineering/r50-topology-repair-20261013/src'))
 sys.path.insert(0,str(HERE.parents[1]/'engineering/strict-motion-audit-20261013'))
from occ_signed_volume import common
from verify_step_payload import full_solid_payload
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for path in sorted((HERE/'cad').glob('*.step')):
 before=sha(path);solids,counts=full_solid_payload(cq.importers.importStep(str(path)).vals());assert len(solids)==3
 carrier=next(s for s in solids if s.BoundingBox().zmin < -1.9)
 ds=next(s for s in solids if abs(s.BoundingBox().zmin+.8)<1e-7)
 dp=next(s for s in solids if abs(s.BoundingBox().zmin-.6)<1e-7)
 v=common(carrier,dp)['checked_volume_mm3'];assert common(ds,carrier)['checked_volume_mm3']<1e-7
 wrong='WRONG_RY180' in path.name
 assert (v>1e-7)==wrong,(path.name,v)
 if 'MISSING_PINS' not in path.name:
  # Reconstruct withdrawal/insertion from actual immutable DP and carrier.
  samples=[]
  for i in range(21):
   dz=2-i*.1;z=.6+dz;value=common(dp.translate((0,0,dz)),carrier)['checked_volume_mm3']
   if wrong and z<2.4-1e-8:assert value>1e-7
   if not wrong:assert value<1e-7
   samples.append({'z_mm':round(z,9),'actual_overlap_mm3':value})
 else:samples=[]
 assert sha(path)==before
 rows.append({'path':path.name,'sha256':before,'full_solid_leaves':3,'shape_types':counts,'final_carrier_overlap_mm3':v,'insertion_samples':samples})
assert len(rows)==3
d={'host':platform.node(),'script_sha256':sha(Path(__file__)),'STEP_rows':rows,'physical_qualification':False,'manufacturing_go':False}
(HERE/'independent_carrier_receipt.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'STEP_files':3,'full_positive_solids':9,'motion_samples':42,'manufacturing_go':False}))
