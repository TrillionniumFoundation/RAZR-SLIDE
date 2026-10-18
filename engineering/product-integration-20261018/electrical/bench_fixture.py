"""Standalone continuity-coupon clamp, explicitly outside the phone envelope.

The mini boards remain on the bench; insulated static jumpers are hand dressed
outside the clamp. This never promotes the rejected phone stack to a fit result.
"""
import hashlib
import json
import math
from pathlib import Path
import cadquery as cq

OUT=Path(__file__).resolve().parent/'bench-fixture'

def box(lo,hi):return cq.Solid.makeBox(*(b-a for a,b in zip(lo,hi)),cq.Vector(*lo))
def cylinder(x,z0,z1,r):return cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,3,z0))
def hex_prism(x,z0,z1,across_flats):
    radius=across_flats/math.sqrt(3)
    wire=cq.Wire.makePolygon([cq.Vector(x+radius*math.cos(i*math.pi/3),3+radius*math.sin(i*math.pi/3),z0) for i in range(6)],close=True)
    return cq.Solid.extrudeLinear(wire,[],cq.Vector(0,0,z1-z0))

def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    lower=box((-11,0,-3.25),(11,6,-.25))
    upper=box((-11,0,.05),(11,6,3.05))
    parts={'coupon_tail':box((-6,0,-.05),(6,12,.05)),'stiffener':box((-6,0,-.25),(6,12,-.05))}
    for i,x in enumerate((-8,8),1):
        hole=cylinder(x,-5,6,1.1)
        lower=lower.cut(hole).cut(hex_prism(x,-3.251,-1.55,4.15))
        upper=upper.cut(hole)
        nut=hex_prism(x,-3.15,-1.55,4.0).cut(cylinder(x,-3.2,-1.5,.85))
        parts[f'M2_nut_{i}']=nut
        parts[f'M2x8_screw_{i}']=cylinder(x,-4.95,3.05,1).fuse(cylinder(x,3.05,5.05,1.9))
    parts.update(lower_jaw=lower,upper_jaw=upper)
    for name,shape in parts.items():
        if not shape.isValid() or len(shape.Solids())!=1 or shape.Volume()<=0:raise ValueError(name)
        cq.exporters.export(shape,str(OUT/(name+'.step')))
        if name.endswith('jaw'):cq.exporters.export(shape,str(OUT/(name+'.stl')))
    full=cq.Compound.makeCompound(list(parts.values()))
    path=OUT/'bench-clamp-assembly.step';cq.exporters.export(full,str(path))
    reopened=cq.importers.importStep(str(path)).val()
    if len(reopened.Solids())!=8:raise ValueError('assembly STEP solid count changed')
    result={'scope':'standalone bench coupon clamp, no phone installation claim','jaw_dimensions_mm':[22,6,3],'clamp_grip_local_y_mm':[0,6],'exposed_tail_solder_pad_center_local_y_mm':9,'flex_plus_stiffener_gap_mm':.3,'fasteners':'2 x M2x8 nominal screws and 2 x M2 nuts (nominal 4 mm AF, 1.6 mm thick)','captive_nut_pocket_AF_mm':4.15,'clearance_hole_mm':2.2,'model_contains_all_clamp_fasteners':True,'mini_DP_DS_boards_location':'separate on bench, static insulated jumper dressing outside jaw envelope','threads':'nominal shaft/minor-diameter proxies, detailed thread helices not modeled','positive_valid_solids':len(reopened.Solids()),'actual_clamp_force_or_life_measured':False,'phone_installation_go':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'exports':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.suffix in ('.step','.stl')}}
    (OUT/'bench-fixture-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'bench_solids':len(reopened.Solids()),'phone_installation_go':False}))

if __name__=='__main__':generate()
