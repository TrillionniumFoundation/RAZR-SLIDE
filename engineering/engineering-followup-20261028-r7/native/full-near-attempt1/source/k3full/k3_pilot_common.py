"""K3 preliminary pair subset recording; original finite guards unchanged."""
from __future__ import annotations
import hashlib,json,math,os
from f1_common import require,atomic,export

def public_failure(exc):
 return {'error_type':type(exc).__name__,'original_error_message_sha256':hashlib.sha256(str(exc).encode()).hexdigest()}

def panel_pairs(parts,out,r,p,budget,original=None):
 expected=[('A_BACK_PANEL',x) for x in sorted(parts) if x!='A_BACK_PANEL']
 r.update(pairs=[],positive_pairs=[],evaluation_failures=[],mismatches_to_factory=[],
  expected_pair_count=len(expected),all_unordered_pairs_present_once=False,
  all_panel_pairs_present_once=False,persisted_pair_count=0,finite_pose_clear=False)
 previous={} if original is None else {(x['a'],x['b']):x for x in original['pairs']}
 def save():
  r['resource']=budget.check();r['persisted_pair_count']=len(r['pairs']);atomic(out/'report.json',r)
 with (out/'pairs.jsonl').open('x') as journal:
  for a,b in expected:
   budget.check();journal.write(json.dumps({'event':'selected','a':a,'b':b})+'\n');journal.flush()
   try:
    result=p.strict_common(parts[a],parts[b]);v=result['common_mm3']
    require(type(v) in (int,float) and math.isfinite(v) and v>=0,'invalid signed panel-pair Common')
    row={'a':a,'b':b,**result,'rejected':v>1e-7};r['pairs'].append(row)
    if v>0:
     common=parts[a].intersect(parts[b]);direct=p.volume(common)
     require(abs(v-direct)<=1e-7,'direct panel Common differs')
     row['direct_Common_mm3']=direct
     row['positive_Common_export']=export(common,out/('positive-'+b),p,budget)
     r['positive_pairs'].append(dict(row))
    if original is not None:
     old=previous[(a,b)];consistent=not old.get('evaluation_failed') and abs(v-old['common_mm3'])<=1e-7 and row['rejected']==old['rejected']
     row['factory_classification_and_volume_consistent']=consistent
     row['factory_difference_mm3']=None if old.get('evaluation_failed') else v-old['common_mm3']
     if not consistent:r['mismatches_to_factory'].append({'a':a,'b':b,'factory':old,'readback':dict(row)})
   except Exception as exc:
    failure={'a':a,'b':b,'evaluation_failed':True,**public_failure(exc)}
    if not r['pairs'] or (r['pairs'][-1]['a'],r['pairs'][-1]['b'])!=(a,b):r['pairs'].append(failure)
    else:r['pairs'][-1]['post_evaluation_failure']=failure
    r['evaluation_failures'].append(failure)
   journal.write(json.dumps({'event':'completed','row':r['pairs'][-1]},allow_nan=False)+'\n');journal.flush()
   if len(r['pairs'])%16==0:os.fsync(journal.fileno());save()
  os.fsync(journal.fileno())
 actual=[(x['a'],x['b']) for x in r['pairs']]
 r['all_panel_pairs_present_once']=actual==expected
 r['pilot_panel_pairs_clear']=bool(actual==expected and not r['evaluation_failures'] and not any(x.get('rejected') for x in r['pairs']))
 save()
