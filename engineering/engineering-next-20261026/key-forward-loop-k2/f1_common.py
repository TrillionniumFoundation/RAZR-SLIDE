"""External F1 finite-pose experiment helpers; never alter S4 geometry or gates."""
from __future__ import annotations
from fractions import Fraction
from pathlib import Path
import hashlib
import itertools
import json
import math
import os
import resource
import signal
import sys
import time

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
ROOT = Path(os.environ['GITHUB_WORKSPACE']).resolve()
GEOMETRY = ROOT/'engineering/engineering-integration-20261025/geometry'
sys.path[:0] = [str(GEOMETRY), str(GEOMETRY/'slide'), str(GEOMETRY/'key'), str(ROOT/'integration'), str(ROOT/'tools')]
import execution_identity as identity
import owned_process

FALSE_FLAGS = ('complete_product_motion_proved', 'continuous_backlash_domain_proved',
               'physical_qualification', 'candidate_go', 'fixture_fabrication_go', 'manufacturing_go', 'G2_pass')
Q = {'near': Fraction(1392875388202497,400000000000000),
     'far': Fraction(3664291796067499,400000000000000)}

def require(value, message):
    if not value: raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def atomic(path, value): identity.atomic_json(path, value)

def signature(body, p):
    solids, volume = p.whole_material(body)
    return {'shape_type': body.ShapeType(), 'is_valid': body.isValid(),
            'signed_volume_mm3': volume, 'solid_count': len(solids),
            'solid_signed_volumes_mm3': [s.Volume() for s in solids], 'bounds_mm': list(p.bounds(body))}

class Budget:
    def __init__(self, out): self.out, self.start = Path(out), time.monotonic()
    def check(self):
        stat = os.statvfs(self.out)
        vals = dict(row.split() for row in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
        amount = sum(int(vals.get(k,0)) for k in ('anon','shmem')) + max(0,int(vals.get('kernel',0))-int(vals.get('slab_reclaimable',0))) + int(vals.get('unevictable',0))
        row = {'seconds':time.monotonic()-self.start,'ordinary_available_disk_bytes':stat.f_bavail*stat.f_frsize,
               'finite_worker_shared_unreclaimable_bytes':amount,
               'worker_peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        require(row['seconds'] <= 1200, '1200 s finite worker budget exceeded')
        require(row['ordinary_available_disk_bytes'] >= 100*2**20, '100 MiB runtime disk reserve reached')
        require(amount <= 6.8*2**30, '6.8 GiB finite shared memory guard reached')
        require(row['worker_peak_RSS_bytes'] <= 1536*2**20, '1536 MiB worker RSS guard reached')
        return row

def export(body, stem, p, budget):
    before = signature(body,p); result={'signature_before':before,'files':{}}
    for extension,method in [('brep',body.exportBrep),('step',body.exportStep)]:
        budget.check(); path=Path(str(stem)+'.'+extension)
        require(not path.exists(), 'fresh export path required')
        status=method(str(path));expected=getattr(type(status),'IFSelect_RetDone',None)
        require(status is True if extension=='brep' else expected is not None and status==expected,
                'native serialization did not report success')
        require(path.is_file() and path.stat().st_size>0,'missing material export')
        result['files'][extension]={'path':str(path.relative_to(budget.out)), 'sha256':sha(path),
                                    'bytes':path.stat().st_size,'native_status':str(status)}
    result['signature_after']=signature(body,p)
    result['serialization_preserved_in_memory_signature']=before==result['signature_after']
    require(result['serialization_preserved_in_memory_signature'],'export changed in-memory material signature')
    return result

def compare_material(a,b,p):
    values=[p.volume(a.cut(b)),p.volume(b.cut(a))]
    require(all(type(x) in (float,int) and math.isfinite(x) and x>=0 for x in values), 'invalid directed material difference')
    return {'a_minus_b_mm3':values[0],'b_minus_a_mm3':values[1],
            'equal_within_original_1e_minus_7_mm3':max(values)<=1e-7}

def evaluate_pairs(parts,out,report,p,budget,*,original=None):
    names=sorted(parts);expected=list(itertools.combinations(names,2));report['pairs']=[]
    report['positive_pairs']=[];report['evaluation_failures']=[];report['mismatches_to_factory']=[]
    report['participant_names']=names;report['expected_pair_count']=len(expected)
    def save():
        report['resource']=budget.check();report['persisted_pair_count']=len(report['pairs'])
        atomic(out/'report.json',report)
    old={} if original is None else {(x['a'],x['b']):x for x in original['pairs']}
    with (out/'pairs.jsonl').open('x') as stream:
        for i,(a,b) in enumerate(expected):
            budget.check();stream.write(json.dumps({'event':'selected','a':a,'b':b})+'\n');stream.flush()
            try:
                result=p.strict_common(parts[a],parts[b]);v=result['common_mm3']
                require(type(v) in (float,int) and math.isfinite(v) and v>=0,'invalid pair volume')
                row={'a':a,'b':b,**result,'rejected':v>1e-7}
                report['pairs'].append(row)
                if v>0:
                    report['positive_pairs'].append(row.copy());save()
                    common=parts[a].intersect(parts[b]);direct=p.volume(common)
                    require(direct>=0 and abs(direct-v)<=1e-7, 'direct Common differs from strict result')
                    row['positive_Common_export']=export(common,out/('positive-%04d'%(len(report['positive_pairs']))),p,budget)
                    row['direct_Common_mm3']=direct
                    report['positive_pairs'][-1]=row.copy()
                if original is not None:
                    previous=old[(a,b)]
                    consistent=not previous.get('evaluation_failed') and abs(v-previous['common_mm3'])<=1e-7 and row['rejected']==previous['rejected']
                    row['factory_difference_mm3']=None if previous.get('evaluation_failed') else v-previous['common_mm3']
                    row['factory_classification_and_volume_consistent']=consistent
                    if not consistent:report['mismatches_to_factory'].append({'a':a,'b':b,'factory':previous,'readback':row.copy()})
            except Exception as exc:
                failure={'a':a,'b':b,'evaluation_failed':True,'error':type(exc).__name__+': '+str(exc)}
                if not report['pairs'] or (report['pairs'][-1]['a'],report['pairs'][-1]['b'])!=(a,b): report['pairs'].append(failure)
                else: report['pairs'][-1]['post_evaluation_failure']=failure
                report['evaluation_failures'].append(failure);save()
            stream.write(json.dumps({'event':'completed','row':report['pairs'][-1]},allow_nan=False)+'\n');stream.flush()
            if (i+1)%16==0:os.fsync(stream.fileno())
            if (i+1)%256==0:
                save();print(json.dumps({'pairs':i+1,'expected':len(expected),'seconds':time.monotonic()-budget.start}),flush=True)
        os.fsync(stream.fileno())
    actual=[(r['a'],r['b']) for r in report['pairs']]
    report['all_unordered_pairs_present_once']=len(actual)==len(set(actual))==len(expected) and set(actual)==set(expected)
    report['finite_pose_clear']=bool(report['all_unordered_pairs_present_once'] and not report['evaluation_failures'] and not any(r.get('rejected') for r in report['pairs']))
    save()

def start(source,out,pose):
    owned_process.announce_worker_from_environment(Path(source).resolve())
    out=Path(out).resolve();require(not out.exists() and not out.is_relative_to(ROOT),'fresh output outside source required')
    out.mkdir(parents=True)
    require(identity.git('rev-parse','HEAD')==S4,'immutable S4 checkout required')
    require(not identity.git('status','--porcelain'),'clean functional S4 checkout required')
    report={'schema':'razr-S4-F1-full-factory-witness-20261026-v1','functional_source_commit':S4,
            'pose':pose,'execution_completed':False,'external_source_sha256':{str(Path(x).resolve()):sha(x) for x in (source,__file__)},
            **{x:False for x in FALSE_FLAGS}}
    atomic(out/'report.json',report)
    signal.signal(signal.SIGTERM, lambda s,f: (_ for _ in ()).throw(InterruptedError('owned supervisor SIGTERM')))
    return out,report,Budget(out)
