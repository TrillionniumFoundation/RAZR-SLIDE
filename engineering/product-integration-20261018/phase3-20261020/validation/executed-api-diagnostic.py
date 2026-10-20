from pathlib import Path
import json,sys,datetime,hashlib
R=Path('/home/qian-qi/RAZR-SLIDE-product-integration-20261018')
E=Path('/home/qian-qi/.local/share/razr-slide-evidence/product-followup-20261020')
sys.path.insert(0,str(R/'integration'))
import product_assembly as p
import product_routing_ep3 as ep
import product_interfaces as interfaces
import product_fpc as f
import numpy as np
A=p.box((0.,0.,0.),(10.,10.,10.));B=p.box((10.,0.,0.),(20.,10.,10.))
inside=p.box((1.,1.,1.),(2.,2.,2.))
empty=inside.cut(A)
checks={'empty_after_first_cut':{'shape_type':empty.ShapeType(),'valid':empty.isValid(),'volume_mm3':p.volume(empty),'solid_count':len(empty.Solids())}}
try: empty.cut(B);checks['old_second_cut_error']=None
except Exception as x: checks['old_second_cut_error']={'type':type(x).__name__,'message':str(x)}
cases={'inside_A':(inside,0.),'inside_B':(p.box((11.,1.,1.),(12.,2.,2.)),0.),
 'spans_touching_A_B':(p.box((9.,1.,1.),(11.,2.,2.)),0.),
 'partly_outside':(p.box((19.,1.,1.),(21.,2.,2.)),1.),
 'fully_outside':(p.box((21.,1.,1.),(22.,2.,2.)),1.)}
rows=[]
for name,(body,expected) in cases.items():
 residual=body;steps=0
 for domain in [A,B]:
  if p.volume(residual)==0.: break
  residual=residual.cut(domain);steps+=1
 actual=p.volume(residual)
 rows.append({'case':name,'expected_outside_mm3':expected,'actual_outside_mm3':actual,'native_cuts_executed':steps,'passed':abs(actual-expected)<1e-9})
assert all(r['passed'] for r in rows)
cfg=ep.candidate_interface_config(interfaces.load_config(),ep.load_config())
sections,route=f.route_pose(cfg,79.75,0.)
y0=94.25;y1=51.+route['straight_A_mm']
checks['original_witness_y1_type']=type(y1).__name__
try:p.box((-6.,y0,1.4),(6.,y1,1.5));checks['original_witness_rejected']=False
except ValueError as x:checks['original_witness_rejected']=str(x)
w=p.box((-6.,float(y0),1.4),(6.,float(y1),1.5))
checks['explicit_float_witness_volume_mm3']=p.volume(w)
assert abs(p.volume(w)-35.0312505261)<1e-8
report={'schema':'razr-ep3-native-api-diagnostic-v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_commit':'bdb1bc19fce49692fd49cd508031bfc456e15208','checks':checks,'guard_cases':rows,
 'scope':'small actual native diagnosis of empty sequential cut and NumPy scalar boundary; production source has not yet changed',
 'candidate_geometry_changed':False,'candidate_go':False,'manufacturing_go':False}
(E/'ep3-native-api-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
