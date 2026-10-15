#!/usr/bin/env python3
"""Independent FreeCAD STEP parse; only original research exports are loaded."""
from pathlib import Path
import datetime,hashlib,json,platform,sys
import FreeCAD,Part
ROOT=Path('/home/qian-qi/Documents/Codex/RAZR_SLIDE_WORK_20261013/native_endpoint_original_step')
expected={
 'BM28_DP_ORIGINAL_NOMINAL_LANDS_RESEARCH.step':('b0bbb73594cca0d2972f6529cba87ba4d3a49f830f6e9ac3b2bb43d107444125',29),
 'BM28_DS_ORIGINAL_NOMINAL_LANDS_RESEARCH.step':('99315150960ef0e48f2da51c327808d789f1edd7b2477acc16d915a560aef760',29),
 'BM28_STATIC_ENDPOINT_COUPON_RESEARCH_NOT_OEM_FIT.step':('c8cbb181d3a1efc3e36a95830a9218f389494139d01131337740ff9df239a885',10),
}
rows=[]
for name,(h,n) in expected.items():
 p=ROOT/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h
 shape=Part.read(str(p));assert len(shape.Solids)==n
 assert shape.isValid() and all(s.isValid() and s.Volume>0 for s in shape.Solids)
 rows.append(dict(file=name,sha256=h,solid_count=n,all_solids_valid=True,
     all_solid_volumes_positive=True,volume_mm3=shape.Volume,
     exported_model_source='original primitives; no vendor raw shape in exports'))
rec=dict(machine=platform.node(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 FreeCAD_version=FreeCAD.Version(),rows=rows,native_import_checks_passed=True,
 actual_PCBA_or_fixture_built=False,native_KiCad_engine_load_verified=False,
 manufacturing_go=False)
(ROOT/'original_step_native_reimport.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec,indent=2),flush=True)
sys.exit(0)
