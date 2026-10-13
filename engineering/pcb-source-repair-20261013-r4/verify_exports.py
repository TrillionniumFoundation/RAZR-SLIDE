"""Independently inspect native manufacturing-format exports, without builder import."""
from pathlib import Path
import sys,csv,hashlib,json,math
sys.dont_write_bytecode=True
import cadquery as cq
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'strict-motion-audit-20261013'))
from verify_step_payload import full_solid_payload
p=ROOT/'native_main/v2/exports/cut_reference_board_ONLY.step'
before=hashlib.sha256(p.read_bytes()).hexdigest()
leaves,counts=full_solid_payload(cq.importers.importStep(str(p)).vals())
assert len(leaves)==1
v=leaves[0].Volume();expected=29*24*1.6-8*math.pi*.4**2*1.6
assert abs(v-expected)<1e-7
box=leaves[0].BoundingBox();assert [box.xlen,box.ylen,box.zlen]==[29.,24.,1.6]
assert before==hashlib.sha256(p.read_bytes()).hexdigest()
exports=ROOT/'native_main/v2/exports'
gerbers=[q for q in exports.glob('*') if q.suffix in ['.gtl','.gbl','.gtp','.gto','.gts','.gbs','.gm1']]
assert len(gerbers)==7
pos=list(csv.DictReader((exports/'cut_reference_placement.csv').open()))
assert len(pos)==7 and {x['Ref'] for x in pos}=={'U1','R1','R2','R3','C1','C2','C3'}
d={'STEP_SHA256':before,'full_root_shape_types':counts,'positive_solid_leaves':1,
 'bbox_mm':[box.xlen,box.ylen,box.zlen],'volume_mm3':v,
 'expected_nominal_board_with_8_0p8mm_PAD_holes_mm3':expected,
 'STEP_board_only':True,'component_models_absent':True,
 'native7_STEP_does_not_subtract_7_via_holes':True,'STEP_assembly_qualification':False,
 'native_Gerber_layers':len(gerbers),'native_SMD_placement_rows':len(pos),
 'all_export_SHA256':{str(q.relative_to(exports)):hashlib.sha256(q.read_bytes()).hexdigest() for q in exports.rglob('*') if q.is_file()},
 'source_before_after_unchanged':True,'manufacturing_go':False,
 'verifier_SHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(ROOT/'export_independent_receipt.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:d[k] for k in ['positive_solid_leaves','bbox_mm','volume_mm3','native_Gerber_layers','native_SMD_placement_rows','manufacturing_go']}))
