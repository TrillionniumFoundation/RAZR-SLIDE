"""Physical three-pin orientation carrier for the frozen routed coupons."""
import hashlib,json,sys
from pathlib import Path
import cadquery as cq
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(REPO/'engineering/r50-topology-repair-20261013/src'))
from occ_signed_volume import common,validated_solid_volume
sys.path.insert(0,str(REPO/'engineering/strict-motion-audit-20261013'))
from verify_step_payload import full_solid_payload
SRC=REPO/'engineering/endpoint-pcba-design-20261013-r2'
FILES=['endpoint_DP.kicad_pcb','endpoint_DS.kicad_pcb','mating_site_map.json','native_pcba_receipt.json']
def hashes():return {f:hashlib.sha256((SRC/f).read_bytes()).hexdigest() for f in FILES}
def box(x0,x1,y0,y1,z0,z1):return cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,cq.Vector(x0,y0,z0))
def cylinder(x,y,r,z0,z1):return cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,y,z0))
def volume(a,b):return common(a,b)['checked_volume_mm3']
def board(holes,z0,z1):
 s=box(-20,20,-18,18,z0,z1)
 for x,y in holes:s=s.cut(cylinder(x,y,1,z0-.1,z1+.1))
 s=s.clean();validated_solid_volume(s);return s
def run():
 before=hashes();native=json.loads((SRC/'native_pcba_receipt.json').read_text());coords={}
 for b in native['boards']:
  assert b['native_DRC']=={'DRC violations':0,'unconnected pads':0,'Footprint errors':0}
  coords[b['board']]=[(h['xy'][0]-100,h['xy'][1]-100) for h in b['holes']]
 assert sorted(coords['DS'])==[(-15,-12),(-12,12),(15,-12)]
 assert sorted((x,-y) for x,y in coords['DP'])==sorted(coords['DS'])
 # Pins are connected to a recessed base. Four corner supports contact only
 # the DS board underside. No connector/FPC is rigidly located by its body.
 carrier=box(-23,23,-21,21,-2,-1.1)
 for x,y in coords['DS']:carrier=carrier.fuse(cylinder(x,y,.9,-2,2.4))
 for x in (-19,17):
  for y in (-17,15):carrier=carrier.fuse(box(x,x+2,y,y+2,-1.1,-.8))
 carrier=carrier.clean();validated_solid_volume(carrier)
 ds=board(coords['DS'],-.8,0);assert volume(carrier,ds)<1e-7
 rows=[]
 correct_holes=[(x,-y) for x,y in coords['DP']]
 wrong_holes=[(-x,y) for x,y in coords['DP']]
 for name,hs in [('Rx180_correct',correct_holes),('Ry180_wrong',wrong_holes)]:
  for i in range(21):
   z=2.6-i*.1;dp=board(hs,z,z+.8);v=volume(dp,carrier)
   assert volume(dp,ds)<1e-7
   if name=='Rx180_correct':assert v<1e-7,(name,z,v)
   if name=='Ry180_wrong' and z<2.4-1e-8:assert v>1e-7,(name,z,v)
   rows.append({'orientation':name,'DP_mount_plane_z_mm':round(z,9),'carrier_overlap_mm3':v})
 # Bounded lateral manufacturing-sensitivity screen: conservative .1mm
 # radial gap. Clearance is tested geometrically, never called GDT release.
 for dx,dy in [(0,0),(.05,0),(-.05,0),(0,.05),(0,-.05),(.05,.05),(-.05,-.05)]:
  dp=board(correct_holes,.6,1.4).translate((dx,dy,0));v=volume(dp,carrier);assert v<1e-7
  rows.append({'orientation':'correct_lateral_perturbation','dx_mm':dx,'dy_mm':dy,'carrier_overlap_mm3':v})
 # Loss of all locating pins remains a real unsafe orientation counterexample.
 missing=box(-23,23,-21,21,-2,-1.1)
 wrong=board(wrong_holes,.6,1.4);assert volume(wrong,missing)<1e-7
 out=HERE/'cad';out.mkdir(exist_ok=True)
 scenes={'CORRECT_RX180': [carrier,ds,board(correct_holes,.6,1.4)],
         'REJECTED_WRONG_RY180': [carrier,ds,wrong],
         'REJECTED_MISSING_PINS_WRONG_ESCAPE':[missing,ds,wrong]}
 exports=[]
 for name,solids in scenes.items():
  path=out/(name+'.step');cq.exporters.export(cq.Compound.makeCompound(solids),str(path));leaves,counts=full_solid_payload(cq.importers.importStep(str(path)).vals());assert len(leaves)==len(solids)
  for s in leaves:validated_solid_volume(s)
  exports.append({'path':str(path.relative_to(HERE)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'solids':len(solids)})
 assert hashes()==before
 result={'source_hashes_before':before,'source_hashes_after':hashes(),'actual_native_PCB_holes_used':coords,'rows':rows,'exports':exports,'board_thickness_hypothesis_mm':.8,'pin_diameter_hypothesis_mm':1.8,'mounting_plane_gap_mm':.6,'physical_continuity':False,'fastener_and_material_qualified':False,'coupon_fabrication_go':False,'manufacturing_go':False}
 (HERE/'carrier_receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'samples':len(rows),'STEPs':len(exports),'manufacturing_go':False}))
if __name__=='__main__':run()
