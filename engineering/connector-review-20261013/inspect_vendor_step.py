#!/usr/bin/env python3
"""Read-only inspection with FreeCADCmd; never exports or modifies vendor CAD.
Use: QT_QPA_PLATFORM=offscreen freecad.cmd inspect_vendor_step.py
Supplier raw STEP and archive remain at their existing authorized local paths.
"""
import json,hashlib,platform,datetime,sys
from pathlib import Path
import FreeCAD,Part
BASE=Path('/home/qian-qi/Documents/Codex/RAZR_SLIDE_R66/vendor_hirose')
OUT=Path('/home/qian-qi/Documents/Codex/RAZR_SLIDE_WORK_20261013/connector_audit')
OUT.mkdir(parents=True,exist_ok=True)
ROWS=[]
for role,part,path,expected in (
 ('header','BM28B0.6-24DP/2-0.35V(53)','header/BM28-24DP.stp','787382f59954cdb58375d04f67807c54edede419020abaf790023df4714f49d6'),
 ('receptacle','BM28B0.6-24DS/2-0.35V(53)','receptacle/BM28-24DS.stp','4dc2955e5c0e4b4cce461b1d5ffc036542f0f69ebd753af03207186020587bd2')):
 p=BASE/path
 before=hashlib.sha256(p.read_bytes()).hexdigest()
 assert before==expected,(p,before)
 shape=Part.read(str(p)); bb=shape.BoundBox
 row={'role':role,'part':part,'source_path':str(p),'size_bytes':p.stat().st_size,'sha256':before,
      'shape_type':shape.ShapeType,'is_valid':shape.isValid(),'solids_count':len(shape.Solids),
      'shells_count':len(shape.Shells),'faces_count':len(shape.Faces),'volume_mm3':shape.Volume,
      'bbox_xyz_mm':[bb.XMin,bb.XMax,bb.YMin,bb.YMax,bb.ZMin,bb.ZMax],
      'bbox_size_mm':[bb.XLength,bb.YLength,bb.ZLength],
      'each_solid_valid':all(x.isValid() for x in shape.Solids),
      'raw_file_unchanged_after_read':before==hashlib.sha256(p.read_bytes()).hexdigest()}
 ROWS.append(row)
rec={'revision':'20261013 genuine vendor BM28 raw shape inspection only',
 'machine':platform.node(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'FreeCAD_version':FreeCAD.Version(),'python':sys.version,
 'rows':ROWS,'no_vendor_CAD_export_or_modification':True,
 'assembly_alignment_verified':False,'physical_pairing_qualified':False,
 'raw_vendor_CAD_redistribution_permission_received':False,'manufacturing_go':False}
out=OUT/'BM28_raw_step_inspection_qian.json';out.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
print('RECEIPT_JSON_BEGIN',flush=True)
print(json.dumps(rec,ensure_ascii=False,indent=2),flush=True)
print('RECEIPT_JSON_END',flush=True)
sys.exit(0)
