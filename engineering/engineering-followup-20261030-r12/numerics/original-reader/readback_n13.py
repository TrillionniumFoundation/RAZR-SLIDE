"""Independent N13 native/exact reader. Imports no producer numerical code."""
from pathlib import Path
from fractions import Fraction as Q
import argparse,json,hashlib,math,os,resource,struct,time,sys
if sys.flags.optimize:
 raise RuntimeError('optimized_python_disables_required_contract_assertions')
import numpy as np
from scipy.sparse import load_npz
AS=4831838208; LIMIT=1e-7

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ident(p):return {'bytes':p.stat().st_size,'sha256':sha(p)}
def exact_number(d):return Q(int(d['numerator']),int(d['denominator']))
def bits(x):return struct.pack('>d',float(x)).hex()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(AS,AS))
 P=a.input;O=a.run;report=json.loads((O/'N13_REPORT.json').read_text());out={'schema':'razr-N13-independent-original-five-and-exact-readback-v1','completed':False,'producer_numerical_imports':False,'full_response_operator_qualified':False,'H_frame_restore_executed':False}
 def guard():
  if time.monotonic()-start>=180:raise RuntimeError('original_180_second_reader_wall')
 try:
  assert report['all_ten_final_arrays_complete_and_hash_verified'] and not report.get('preservation_failures')
  assert len(report['expected_final_array_files'])==10 and len(set(report['expected_final_array_files']))==10
  for n,v in report['files'].items():assert ident(O/n)==v,n
  for n,v in report['original_input_identities'].items():assert ident(P/n)==v,n
  for n in ['source/probe_n12_coordinates.py','source/n12_contract.py']:
   m=json.loads((P/'EXPORT_MANIFEST.json').read_text());assert ident(P/n)==m['exported_files'][n]
  p=P/'frozen/frozen/frozen/frozen/frozen/probe-N5';v=P/'frozen/frozen/frozen/frozen/frozen/volume/panel/level-2'
  free=np.load(p/'free-original-DOFs.npy');fixed=np.load(p/'fixed-original-DOFs.npy');rhs=np.load(p/'five-probe-rhs.npy');direction=np.load(p/'five-probe-directions.npy');C=load_npz(p/'C.npz');assert np.array_equal(C@direction,rhs);del C,direction;rhs=rhs[free]
  assert tuple(fixed)==(0,1,2,13,14,8) and np.array_equal(free,np.setdiff1d(np.arange(344103),fixed))
  K=load_npz(v/'K.npz').tocsc();A=K[free][:,free].tocsc();del K
  for n,h in report['original_Kff_buffer_hashes'].items():assert hashlib.sha256(getattr(A,n).tobytes()).hexdigest()==h
  R=A.tocsr();base=[np.load(P/x['file']) for x in report['baseline_field_references']]
  for x in report['baseline_field_references']:assert ident(P/x['file'])=={k:x[k] for k in ('bytes','sha256')}
  native_checks=0;exact_equations=0;target_pairs=0;anchor_checks=0;proofs=[];records=[];state=base
  def native(fs):
   nonlocal native_checks
   rs=[];es=[]
   for j,f in enumerate(fs):
    guard();assert f.shape==(344103,) and f.dtype==np.float64 and np.all(f[fixed]==0) and np.isfinite(f).all()
    e=A@f[free]-rhs[:,j];d=max(float(np.abs(rhs[:,j]).max()),1.0);r=float(np.abs(e).max())/d;rs.append((r,int(np.count_nonzero(np.abs(e)/d>LIMIT))));es.append(e);native_checks+=1
   return rs,es
  def ex(i,full):
   nonlocal exact_equations
   lo,hi=R.indptr[i:i+2];z=-Q(float(rhs[i,0]))
   for c,k in zip(R.indices[lo:hi],R.data[lo:hi]):z+=Q(float(k))*Q(float(full[free[c]]))
   exact_equations+=1;return z
  scores,errors=native(state)
  for j,rr in enumerate(report['baseline']):assert scores[j]==(rr['free_dof_residual_infinity_ratio'],rr['over_gate_row_count'])
  for tr,st in zip(report['trials'],report['stages']):
   guard();idx=tr['index'];assert tr['accepted'] and tr['status']=='accepted' and st['status']=='accepted';assert idx==st['stage']
   cols={int(x[0]) for x in tr['specification']};expected=state[0].copy()
   for c,d,s in tr['specification']:
    assert s==1 and d in [-1,1];expected[free[c]]=math.nextafter(float(state[0][free[c]]),-math.inf if d<0 else math.inf)
   field=np.load(O/f'trial-{idx:02}/probe-0-field.npy');assert field.tobytes()==expected.tobytes()
   update=field-state[0]
   for n in ['actual-update.npy','requested-update.npy']:assert np.load(O/f'trial-{idx:02}'/n).tobytes()==update.tobytes()
   changed=set(map(int,np.flatnonzero(update)));assert changed=={int(free[c]) for c in cols}
   affected=set()
   for c in cols:
    lo,hi=A.indptr[c:c+2]
    affected.update(int(i) for i,k in zip(A.indices[lo:hi],A.data[lo:hi]) if k!=0)
   proof=tr['proof'];assert affected=={x['free_row_index'] for x in proof['all_affected_rows']}
   qbefore={};qafter={}
   for row in proof['all_affected_rows']:
    i=row['free_row_index'];assert row['original_row_DOF']==int(free[i]);qbefore[i]=ex(i,state[0]);qafter[i]=ex(i,field)
    assert qbefore[i]==exact_number(row['before']) and qafter[i]==exact_number(row['after'])
   qb=max(abs(x) for x in qbefore.values());qa=max(abs(x) for x in qafter.values())
   assert qb==exact_number(proof['affected_exact_infinity_before']) and qa==exact_number(proof['affected_exact_infinity_after'])
   anchorok=False;an=proof['unaffected_exact_anchor']
   if an is not None:
    i=an['free_row_index'];assert i not in affected and an['original_row_DOF']==int(free[i]);q0=ex(i,state[0]);q1=ex(i,field);assert q0==q1==exact_number(an['signed_exact_residual']);anchorok=abs(q0)>=qa;anchor_checks+=1
   assert qa<=qb or anchorok
   new=[field]+state[1:];ns,ne=native(new);assert ns[0][1]<scores[0][1] and max(x[0] for x in ns)<=max(x[0] for x in scores)
   assert ne[0].tobytes()==np.load(O/f'trial-{idx:02}/probe-0-residual.npy').tobytes()
   for j in range(1,5):assert new[j].tobytes()==base[j].tobytes() and ne[j].tobytes()==errors[j].tobytes() and ns[j][0]<=LIMIT
   pred=errors[0].copy()
   for i,h in tr['all_affected_prediction']:pred[i]=float.fromhex(h)
   assert pred.tobytes()==ne[0].tobytes()
   for row in proof['all_affected_rows']:
    i=row['free_row_index'];assert row['base_native_float64_residual_bits']==bits(errors[0][i]) and row['predicted_float64_residual_bits']==bits(ne[0][i])
   for j,rr in enumerate(tr['probes']):assert ns[j]==(rr['free_dof_residual_infinity_ratio'],rr['over_gate_row_count'])
   # Independent candidate-table reconstruction and cumsum row evaluation.
   if 'pair_specifications_file' in st:
    target=st['target_free_row'];lo,hi=R.indptr[target:target+2];cc=R.indices[lo:hi];coef=R.data[lo:hi];x=state[0][free];options=[]
    for c,k in zip(cc,coef):
     for d in [-1,1]:
      nv=math.nextafter(float(x[c]),-math.inf if d<0 else math.inf);options.append((int(c),d,nv,Q(float(k))*(Q(nv)-Q(float(x[c])))))
    pairs=[]
    for left in range(len(options)):
     for right in range(left+1,len(options)):
      if options[left][0]!=options[right][0]:pairs.append((abs(options[left][3]+options[right][3]),left,right))
    pairs.sort();spec=np.load(O/st['pair_specifications_file']);pres=np.load(O/st['pair_target_residuals_file'])
    expected_spec=np.asarray([[options[i][0],options[i][1],options[j][0],options[j][1]] for _,i,j in pairs],dtype=np.int64)
    assert np.array_equal(spec,expected_spec)
    lookup={int(c):j for j,c in enumerate(cc)}
    for first in range(0,len(spec),1024):
     guard();ss=spec[first:first+1024];values=np.repeat(x[cc][None,:],len(ss),axis=0)
     for r0,row in enumerate(ss):
      for col,di in zip(row[::2],row[1::2]):values[r0,lookup[int(col)]]=math.nextafter(float(x[col]),-math.inf if di<0 else math.inf)
     products=values*coef[None,:];zero=np.zeros((len(ss),1),dtype=np.float64);read=np.cumsum(np.concatenate((zero,products),axis=1),axis=1)[:,-1]-float(rhs[target,0])
     assert read.tobytes()==pres[first:first+1024].tobytes()
    target_pairs+=len(spec)
   proofs.append({'trial':idx,'all_affected_rows':len(affected),'direct_before_after_exact_checked':True,'anchor_checked':an is not None,'global_exact_infinity_nonincrease':True,'original_ratios':[x[0] for x in ns],'bad_rows':[x[1] for x in ns]})
   records.append({'trial':idx,'original_free_coordinates':tr['specification'],'original_DOFs':sorted(changed),'before_bad_rows':scores[0][1],'after_bad_rows':ns[0][1]});state,scores,errors=new,ns,ne
  final=[np.load(O/f'last-accepted/probe-{j}-field.npy') for j in range(5)]
  for j in range(5):assert final[j].tobytes()==state[j].tobytes()
  final_scores,final_errors=native(final)
  for j,e in enumerate(final_errors):assert e.tobytes()==np.load(O/f'last-accepted/probe-{j}-residual.npy').tobytes()
  assert report['completed'] and report['original_five_passed'] and all(r<=LIMIT and n==0 for r,n in final_scores)
  out.update(completed=True,original_five_qualification_verified=True,original_five_ratios=[r for r,n in final_scores],final_over_threshold_row_counts=[n for r,n in final_scores],native_original_float64_gate_evaluations=native_checks,complete_native_candidate_sets_checked=len(proofs),direct_exact_equations_checked=exact_equations,unchanged_exact_anchors_checked=anchor_checks,all_target_pairs_independently_reconstructed_and_accumulated=target_pairs,all_affected_proofs=proofs,actual_updates=records,input_identities=report['original_input_identities'],original_Kff_buffer_hashes=report['original_Kff_buffer_hashes'],producer_report_identity=ident(O/'N13_REPORT.json'),reader_source_identity=ident(Path(__file__)))
 except BaseException as ex:
  out.update(failure_type=type(ex).__name__,failure_message=str(ex));import traceback;traceback.print_exc()
 finally:
  out.update(elapsed_seconds=time.monotonic()-start,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,runtime={'python':sys.version,'numpy':np.__version__,'scipy':__import__('scipy').__version__});a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 print(json.dumps({k:out.get(k) for k in ['completed','original_five_qualification_verified','original_five_ratios','native_original_float64_gate_evaluations','direct_exact_equations_checked','elapsed_seconds','failure_message']}))
 return 0 if out.get('original_five_qualification_verified') else 2
if __name__=='__main__':raise SystemExit(main())
