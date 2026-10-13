#!/usr/bin/env python3
"""Independently inspect complete split-root STEP payloads. No builder import."""
from pathlib import Path
import sys,json,math,platform,time,hashlib
sys.dont_write_bytecode=True
import cadquery as cq
from OCP.TopAbs import TopAbs_COMPOUND,TopAbs_COMPSOLID,TopAbs_SOLID
from OCP.TopoDS import TopoDS_Iterator
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def payload(path):
 roots=cq.importers.importStep(str(path)).vals();leaves=[];compounds=0
 def visit(sh):
  nonlocal compounds
  if not sh.isValid():raise ValueError('Invalid complete topology node')
  kind=sh.wrapped.ShapeType()
  if kind==TopAbs_SOLID:
   vol=float(sh.Volume())
   if not math.isfinite(vol) or vol<=0:raise ValueError('Nonpositive signed Solid')
   leaves.append((sh,vol));return
  if kind not in (TopAbs_COMPOUND,TopAbs_COMPSOLID):raise ValueError('Free surface/wire/edge/vertex is not silently discarded')
  it=TopoDS_Iterator(sh.wrapped);children=[];compounds+=1
  while it.More():children.append(cq.Shape.cast(it.Value()));it.Next()
  if not children:raise ValueError('Empty free Compound')
  for child in children:visit(child)
 for root in roots:visit(root)
 raw=sum(root.Volume() for root in roots);total=sum(v for s,v in leaves)
 if not leaves or not math.isfinite(raw) or abs(raw-total)>1e-6:raise ValueError('Whole topology signed-volume sum mismatch')
 return leaves,{'compound_nodes':compounds,'valid_positive_solid_leaves':len(leaves),'whole_signed_volume_mm3':raw,'all_leaf_sum_mm3':total,'no_free_topology_filtered':True}
def main():
 start=time.monotonic();paths=sorted((HERE/'cad').glob('*.step'));assert {p.name for p in paths}=={'STOW_ROOT_SPLIT_ASSEMBLED.step','OPEN_ROOT_SPLIT_ASSEMBLED.step'}
 before={str(p.relative_to(HERE)):sha(p) for p in [*paths,Path(__file__)]};rows=[]
 for path in paths:
  port=path.name.split('_')[0];leaves,topo=payload(path);assert len(leaves)==46;spring=[];screws=[]
  for sh,v in leaves:
   bb=sh.BoundingBox();axes={a:getattr(bb,a+'max')-getattr(bb,a+'min') for a in 'xyz'};radial=('x','y') if port=='STOW' else ('x','z');axial='z' if port=='STOW' else 'y'
   if all(abs(axes[a]-.86)<1e-6 for a in radial) and abs(axes[axial]-1.46)<1e-6:
    expected=math.pi*.43**2*1.46;assert abs(v-expected)<1e-6;spring.append({'signed_volume_mm3':v,'independent_cylinder_mm3':expected,'actual_extents_mm':axes,'nominal_installed_length_mm':1.46,'conditional_margin_above_catalog_solid_upper_mm':1.46-1.2537})
   if abs(v-(math.pi*.5**2*3.+math.pi*.9**2*.45))<1e-6:screws.append({'signed_volume_mm3':v,'nominal_M1x3_plus_1p8x0p45_head_envelope':True,'actual_extents_mm':axes,'thread_form_preload_and_strength_qualified':False})
  assert len(spring)==4 and len(screws)==8
  rows.append({'path':str(path.relative_to(HERE)),'sha256':sha(path),'whole_payload':topo,'actual_four_spring_occupancy_envelopes':spring,'actual_eight_new_nominal_M1x3_envelopes':screws,'all_signed_solid_volumes_mm3':[v for s,v in leaves]})
 assert before=={str(p.relative_to(HERE)):sha(p) for p in [*paths,Path(__file__)]}
 report={'host':platform.node(),'python':platform.python_version(),'cadquery':cq.__version__,'source_sha256':sha(__file__),'inputs_unchanged':True,'input_SHA256':before,'rows':rows,'complete_STEP_count':2,'valid_positive_solid_count':92,'actual_spring_occupancy_envelope_count':8,'new_M1x3_nominal_screw_envelope_count':16,'builder_not_imported':True,'full_branch_topology_recursion_performed':True,'vendor_native_helical_spring_STEP_used':False,'physical_mechanical_OLED_electrical_qualification':False,'fixture_fabrication_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 (HERE/'independent-split-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'STEP':2,'valid_positive_solids':92,'spring_envelopes':8,'new_screw_envelopes':16}),flush=True)
if __name__=='__main__':main()
