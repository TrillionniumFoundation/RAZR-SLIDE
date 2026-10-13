#!/usr/bin/env python3
"""FreeCAD read-only inspection of source-machine-only Hirose models.

Native geometry is never saved/exported. Spring contacts in the as-published
CAD are not proof of real deformed-contact force, continuity or durability.
"""
from pathlib import Path
import datetime,hashlib,json,platform,sys
import FreeCAD,Part

BASE=Path('/home/qian-qi/Documents/Codex/RAZR_SLIDE_R66/vendor_hirose')
OUT=BASE/'native_docs_20261013'
shapes={};hashes={}
for role,relative,expected in (
 ('DP','header/BM28-24DP.stp','787382f59954cdb58375d04f67807c54edede419020abaf790023df4714f49d6'),
 ('DS','receptacle/BM28-24DS.stp','4dc2955e5c0e4b4cce461b1d5ffc036542f0f69ebd753af03207186020587bd2')):
 p=BASE/relative;h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==expected
 shapes[role]=Part.read(str(p));hashes[role]=h
 assert shapes[role].isValid() and len(shapes[role].Solids)==1
rows=[]
for axis in ('X','Y'):
 dp=shapes['DP'].copy()
 dp.rotate(FreeCAD.Vector(0,0,0),FreeCAD.Vector(1,0,0) if axis=='X' else FreeCAD.Vector(0,1,0),180)
 dp.translate(FreeCAD.Vector(0,0,.6))
 common=dp.common(shapes['DS']);bb=dp.BoundBox
 rows.append(dict(DP_upper_mounting_plane_rotation=axis+'180',DP_mounting_plane_z_mm=.6,
    DP_bbox_xyz_mm=[bb.XMin,bb.XMax,bb.YMin,bb.YMax,bb.ZMin,bb.ZMax],
    DP_valid=dp.isValid(),DS_valid=shapes['DS'].isValid(),
    native_shape_common_volume_mm3=common.Volume,native_common_valid=common.isValid(),
    actual_mating_alignment_qualified=False,
    overlap_interpretation='Published rigid CAD of spring contacts: common volume is not electrical/mechanical qualification'))
after={role:hashlib.sha256((BASE/relative).read_bytes()).hexdigest() for role,relative in
    [('DP','header/BM28-24DP.stp'),('DS','receptacle/BM28-24DS.stp')]}
assert hashes==after
rec=dict(machine=platform.node(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    FreeCAD_version=FreeCAD.Version(),raw_hashes_before=hashes,raw_hashes_after=after,rows=rows,
    vendor_raw_CAD_ever_exported=False,mechanical_keying_verified=False,
    native_pin1_or_net_assignment_available=False,manufacturing_go=False)
(OUT/'native_pair_orientation_readonly.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec,indent=2),flush=True)
sys.exit(0)
