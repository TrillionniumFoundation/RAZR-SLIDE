"""Reimport every native STEP and independently reverse every declared stage.
Imports generic material/sweep utilities only; no candidate or scene builder.
"""
from pathlib import Path
import argparse,hashlib,json,importlib.util,platform,sys,time

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--expected-sha256',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if sha(a.receipt)!=a.expected_sha256:raise ValueError('receipt bytes changed')
 source=a.receipt.resolve().parent;data=json.loads(a.receipt.read_text());helper=a.repo/'integration/verify_stow_sweep.py'
 spec=importlib.util.spec_from_file_location('independent_material_reader',helper);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 sys.path.insert(0,str(a.repo/'integration'));import straight_envelope as generic
 inputs={str(a.receipt):sha(a.receipt),str(helper):sha(helper),str(Path(generic.__file__)):sha(generic.__file__)};shapes={};rows=[];start=time.monotonic();comparisons=[]
 for role,item in data['exports'].items():
  p=source/item['path']
  if p.parent!=source or sha(p)!=item['sha256']:raise ValueError('STEP identity/path differs')
  raw=v.cq.importers.importStep(str(p)).vals()
  if len(raw)!=1:raise ValueError('extra roots')
  s=v.single(raw[0]);cert=item['certificate'];box=s.BoundingBox()
  if abs(s.Volume()-cert['signed_volume_mm3'])>1e-7 or any(abs(getattr(box,k)-x)>1e-7 for k,x in cert['bounds_mm'].items()):raise ValueError('STEP certificate changed')
  inputs[str(p)]=sha(p);shapes[role]=s
 if len(shapes)!=64:raise ValueError('complete native export set missing')
 def equals(x,y,label):
  forward=v.material(x.cut(y),allow_empty=True)[1];backward=v.material(y.cut(x),allow_empty=True)[1]
  if max(forward,backward)>1e-7:raise ValueError('reverse envelope disagreement '+label)
  comparisons.append({'label':label,'forward_only_mm3':forward,'reverse_only_mm3':backward})
 for row in data['rows']:
  side=row['side'];get=lambda n:shapes[side+'_'+n];delta=(-1.1 if side=='L' else 1.1,0.,0.);ten=(-10. if side=='L' else 10.,0.,0.)
  pairs=[];negative=[];stages={r['stage']:r for r in row['stages']}
  def common(stage,name,x,y):
   z=v.signed_common(x,y);expected=stages[stage]['checks'][name]['checked_volume_mm3']
   if abs(z-expected)>1e-7 or z>1e-7:raise ValueError(f'actual stage {side} {stage} {name} is not clear: {z}')
   pairs.append({'stage':stage,'part':name,'actual_mm3':z,'producer_mm3':expected})
  parked=get('PAWL').translate(delta);equals(parked,get('PARKED_PAWL'),side+'_parked')
  ins,_=v.reverse_envelope(parked,[0.,0.,10.]);equals(ins,get('PAWL_INSERTION'),side+'_insertion')
  common('1_PAWL_BEFORE_STOPS','ROOT_INNER',ins,get('ROOT_INNER'))
  for i in range(2):
   stop=get(f'STOP_{i}');back,_=generic.envelope(stop.translate(ten),tuple(-x for x in ten));equals(back,get(f'STOP_{i}_SWEEP'),side+f'_stop_{i}')
   stage=f'{2+i}_STOP_{i}_AFTER_PAWL'
   for n in ['ROOT_INNER','PARKED_PAWL']+(['STOP_0'] if i else []):common(stage,n,back,get(n))
   old=v.signed_common(ins,stop)
   if old<=1e-7 or abs(old-row['old_order_insertion_negative'][f'STOP_{i}']['checked_volume_mm3'])>1e-7:raise ValueError('original insertion negative not reproduced')
   negative.append({'stop':i,'old_order_common_mm3':old})
  for n in ['ROOT_INNER','PARKED_PAWL','STOP_0','STOP_1']:
   reverse,_=generic.envelope(get(n).translate(tuple(-x for x in ten)),ten);equals(reverse,get('RELATIVE_'+n),side+'_relative_'+n)
   common('4_OUTER_ROOT_LAST',n,get('ROOT_OUTER_CONNECTED_ALL_FRAGMENTS'),reverse)
  returned,_=v.reverse_envelope(get('PAWL'),delta);equals(returned,get('PAWL_RETURN'),side+'_return')
  for n in stages['5_FINAL_PAWL_RETURN']['checks']:common('5_FINAL_PAWL_RETURN',n,returned,get(n))
  rows.append({'side':side,'pairs':pairs,'old_order_negative_controls':negative});print(side,'PAIRS',len(pairs),'all reverse checked',flush=True)
 static=[]
 for row in data['static_checks']:
  side=row['side'];x,y=row['parts'];actual=v.signed_common(shapes[side+'_'+x],shapes[side+'_'+y])
  if actual>1e-7 or abs(actual-row['checked_common_mm3'])>1e-7:raise ValueError('static pair disagreement')
  static.append({'side':side,'parts':[x,y],'actual_mm3':actual})
 if inputs!={p:sha(p) for p in inputs}:raise ValueError('inputs changed during verification')
 imported=[n for n in sys.modules if n.startswith(('stow_continuous','stow_motion','stow_web','split_root','build_spring'))]
 if imported:raise ValueError('scene builder imported: '+str(imported))
 result={'host':platform.node(),'CadQuery':v.cq.__version__,'verifier_sha256':sha(__file__),'producer_receipt_sha256':a.expected_sha256,
         'inputs_SHA256':inputs,'inputs_unchanged':True,'complete_positive_solid_STEP_files':len(shapes),'reverse_envelope_comparisons':comparisons,
         'rows':rows,'recomputed_stage_pairs':sum(len(r['pairs']) for r in rows),'recomputed_static_pairs':len(static),'static_pairs':static,
         'old_insertion_negative_pairs':4,'builder_imported':False,'same_CAD_kernel_not_cross_engine':True,
         'conservative_cylindrical_carriers_are_not_exact_shape_claims':True,'only_nominal_declared_straight_subassembly_stages':True,
         'fixture_gripping_tolerance_load_and_full_phone_not_qualified':True,'candidate_go':False,'manufacturing_go':False,'elapsed_seconds':time.monotonic()-start}
 with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('PASS',result['recomputed_stage_pairs'],result['recomputed_static_pairs'],flush=True)
if __name__=='__main__':main()
