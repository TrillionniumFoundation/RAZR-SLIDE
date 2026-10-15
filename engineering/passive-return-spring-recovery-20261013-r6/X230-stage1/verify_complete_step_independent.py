#!/usr/bin/env python3
"""Independent complete STEP branches and spring occupancy dimensions; no builder import."""
import json,math,sys,hashlib,platform,time
from pathlib import Path
sys.dont_write_bytecode=True
import cadquery as cq
from OCP.TopAbs import TopAbs_COMPOUND,TopAbs_COMPSOLID,TopAbs_SOLID
from OCP.TopoDS import TopoDS_Iterator
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_whole(p):
 roots=cq.importers.importStep(str(p)).vals();leaves=[];nodes=0
 def visit(s):
  nonlocal nodes
  if not s.isValid():raise ValueError('Invalid complete STEP node')
  kind=s.wrapped.ShapeType()
  if kind==TopAbs_SOLID:
   v=float(s.Volume())
   if not math.isfinite(v) or v<=0:raise ValueError('Nonpositive or nonfinite actual signed Solid volume')
   leaves.append((s,v));return
  if kind not in (TopAbs_COMPOUND,TopAbs_COMPSOLID):raise ValueError('Free non-solid branch in complete payload')
  nodes+=1;it=TopoDS_Iterator(s.wrapped);children=[]
  while it.More():children.append(cq.Shape.cast(it.Value()));it.Next()
  if not children:raise ValueError('Empty free Compound')
  for c in children:visit(c)
 for r in roots:visit(r)
 raw=sum(r.Volume() for r in roots);total=sum(v for s,v in leaves)
 if not leaves or not math.isfinite(raw) or abs(raw-total)>1e-6:raise ValueError('Complete payload sum differs from actual Solid leaf sum')
 return leaves,{'compound_nodes':nodes,'solid_leaves':len(leaves),'raw_whole_signed_volume_mm3':raw,'all_leaf_signed_volume_sum_mm3':total,'every_branch_checked_no_free_topology_filtered':True}
def main():
 start=time.monotonic();paths=sorted((HERE/'cad').glob('*.step'));cases={'CAM_SUPPORTED':(40,1.46),'ABSENT_LOWER_STOP':(38,2.62),'FORCED_UPPER':(38,1.4)}
 assert {p.name for p in paths}=={port+'_'+name+'.step' for port in ('STOW','OPEN') for name in cases}
 before={str(p.relative_to(HERE)):sha(p) for p in [*paths,Path(__file__)]};rows=[]
 for path in paths:
  port=path.stem.split('_')[0];case=path.stem[len(port)+1:];count,length=cases[case];leaves,topo=read_whole(path);assert len(leaves)==count
  cylindrical=[]
  for shape,v in leaves:
   bb=shape.BoundingBox();axes={a:getattr(bb,a+'max')-getattr(bb,a+'min') for a in 'xyz'}
   radial=('x','y') if port=='STOW' else ('x','z');axial='z' if port=='STOW' else 'y'
   if all(abs(axes[a]-.86)<1e-6 for a in radial) and abs(axes[axial]-length)<1e-6:
    expected=math.pi*.43**2*length;assert abs(v-expected)<1e-6;cylindrical.append({'actual_signed_volume_mm3':v,'independent_cylinder_volume_mm3':expected,'actual_extent_mm':axes,'nominal_length_mm':length,'margin_above_inherited_catalog_solid_height_upper_mm':length-1.2537})
  assert len(cylindrical)==4
  rows.append({'path':str(path.relative_to(HERE)),'sha256':sha(path),'whole_payload':topo,'actual_spring_occupancy_envelopes':cylindrical,'four_envelopes_not_four_vendor_helical_models':True})
 after={str(p.relative_to(HERE)):sha(p) for p in [*paths,Path(__file__)]};assert before==after
 result={'host':platform.node(),'python':platform.python_version(),'cadquery':cq.__version__,'input_sha256':before,'inputs_unchanged':True,'rows':rows,'complete_STEP_count':len(rows),'total_valid_positive_solid_leaves':sum(r['whole_payload']['solid_leaves'] for r in rows),'actual_spring_envelope_count':sum(len(r['actual_spring_occupancy_envelopes']) for r in rows),'builder_not_imported':True,'actual_spring_and_capture_force_or_fatigue_qualified':False,'phone_installation_qualified':False,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'independent-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'STEP':len(rows),'positive_solids':result['total_valid_positive_solid_leaves'],'spring_envelopes':result['actual_spring_envelope_count']}),flush=True)
if __name__=='__main__':main()
