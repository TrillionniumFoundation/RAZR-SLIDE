#!/usr/bin/env python3
"""Compare all pinned actual STEP report values across Cloud and X230."""
import hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
SKIP={'$.environment.host','$.environment.python'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 local=HERE.parent/'independent/final-independent-export-check.json'
 remote=HERE/'final-independent-export-check.json'
 a,b=json.loads(local.read_text()),json.loads(remote.read_text())
 numbers=identities=0;max_delta=0.;max_path=None;failures=[]
 def visit(x,y,path='$'):
  nonlocal numbers,identities,max_delta,max_path
  if path in SKIP:return
  if isinstance(x,dict) and isinstance(y,dict):
   if set(x)!=set(y):failures.append({'path':path,'reason':'Different object keys'});return
   for k in x:visit(x[k],y[k],path+'.'+k)
  elif isinstance(x,list) and isinstance(y,list):
   if len(x)!=len(y):failures.append({'path':path,'reason':'Different array length'});return
   for i,(u,v) in enumerate(zip(x,y)):visit(u,v,path+'['+str(i)+']')
  elif isinstance(x,(float,int)) and not isinstance(x,bool) and isinstance(y,(float,int)) and not isinstance(y,bool):
   numbers+=1
   if not (math.isfinite(x) and math.isfinite(y)):failures.append({'path':path,'reason':'Nonfinite comparison value'});return
   delta=abs(x-y)
   if delta>max_delta:max_delta,max_path=delta,path
   if delta>1e-7:failures.append({'path':path,'reason':'Actual numeric difference exceeds absolute comparison tolerance','Cloud':x,'X230':y})
  else:
   identities+=1
   if type(x)!=type(y) or x!=y:failures.append({'path':path,'reason':'Different identity or truth value','Cloud':x,'X230':y})
 visit(a,b)
 result={'Cloud_report_sha256':sha(local),'X230_report_sha256':sha(remote),'Cloud_environment':a['environment'],'X230_environment':b['environment'],
  'actual_numeric_values_compared':numbers,'actual_identity_truth_or_null_values_compared':identities,'maximum_absolute_numeric_difference':max_delta,
  'maximum_difference_path':max_path,'absolute_numeric_comparison_tolerance':1e-7,'all_numeric_values_exactly_equal':max_delta==0.,
  'only_skipped_environment_fields':sorted(SKIP),'failures':failures,'passed':not failures,'physical_safety_qualification_is_not_implied_by_two_machine_agreement':True,'manufacturing_go':False}
 (HERE/'Cloud-vs-X230-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
