"""L3: complete correlated contact carriers for seventy retained L1 input pairs.

The unchanged S4 product predicates validate every material and Common.
The historical result is retained by hash and never rewritten.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
ROOT = Path(os.environ['GITHUB_WORKSPACE']).resolve()
HERE = Path(__file__).resolve().parent
GEOMETRY = ROOT/'engineering/engineering-integration-20261025/geometry'
sys.path[:0] = [str(GEOMETRY/'slide'),str(GEOMETRY/'seating'),str(GEOMETRY),
               str(ROOT/'integration'),str(ROOT/'tools')]
import owned_process
import execution_identity as identity

FALSE_FLAGS = ('all_11781_pairs_reexecuted','full_continuous_domain_clear',
               'physical_qualification','candidate_go','fixture_fabrication_go',
               'manufacturing_go','original_results_replaced','independent_CAD_kernel')


def require(x, message):
    if not x: raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def resources(out):
    v = dict((k,int(x)) for k,x in (r.split() for r in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines()))
    d = os.statvfs(out)
    return {'available_disk_bytes':d.f_bavail*d.f_frsize,
            'shared_unreclaimable_bytes':v.get('anon',0)+v.get('shmem',0)
             +max(0,v.get('kernel',0)-v.get('slab_reclaimable',0))+v.get('unevictable',0)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs',type=Path,required=True)
    ap.add_argument('--binding',type=Path,required=True)
    ap.add_argument('--shard',choices=('E17','O72'),required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    owned_process.announce_worker_from_environment(Path(__file__).resolve())
    out=args.output.resolve();require(not out.exists() and not out.is_relative_to(ROOT),'fresh external output required')
    out.mkdir(parents=True)
    science=out/'science';science.mkdir()
    started=time.monotonic()
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(InterruptedError('owned supervisor SIGTERM')))
    report={'schema':'razr-L3-correlated-original-L1-input-replay-v1','functional_predicate_source_commit':S4,
            'new_method':'complete_correlated_contact_carriers_v3','shard':args.shard,'execution_completed':False,
            'original_volume_gate_mm3':1e-7,'case_results':[],**{k:False for k in FALSE_FLAGS}}
    own={p.name:sha(p) for p in [Path(__file__),HERE/'correlated_v3.py',args.binding]}
    report['external_source_sha256']=own
    def save():identity.atomic_json(science/'report.json',report)
    def budget():
        r=resources(out)
        require(time.monotonic()-started<=1800,'original 1800 s L1 wall guard')
        require(r['available_disk_bytes']>=100*2**20,'original 100 MiB L1 runtime disk reserve')
        require(r['shared_unreclaimable_bytes']<=6.8*2**30,'original 6.8 GiB L1 shared guard')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1536*2**20,'original 1536 MiB L1 RSS guard')
        return r
    try:
        require(identity.git('rev-parse','HEAD')==S4 and not identity.git('status','--porcelain'),'clean immutable S4 required')
        before=identity.snapshot();executed=identity.record_executed_project_files()
        identity.atomic_json(out/'source-before-private.json',before)
        binding=json.loads(args.binding.read_text());source=args.inputs.resolve()
        shard=binding['shards'][args.shard]
        for name, entry in shard['members'].items():
            path=(source/name).resolve()
            require(path.is_relative_to(source) and path.is_file() and not path.is_symlink(),'unsafe original input')
            require(path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],'original L1 byte identity mismatch')
        import cadquery as cq
        import product_assembly as p
        import correlated_v3 as v3
        profile_path=ROOT/'engineering/thin-mechanism-20261015/native-verification.json.gz'
        profile_hash=sha(profile_path)
        report['native_profile_source']={'path':str(profile_path.relative_to(ROOT)),'sha256':profile_hash,'bytes':profile_path.stat().st_size}
        report['new_method_tests']='each native case includes original BREP/STEP identity, source family checks, correlated carrier Common and a penetrating negative control'
        report.update(original_input_members_verified=len(shard['members']),
                      original_artifact_id=shard['artifact_id'],original_run_id=binding['run_id'],
                      expected_cases=len(shard['cases']))
        def signature(shape):
            solids,vol=p.whole_material(shape)
            return {'is_valid':shape.isValid(),'signed_volume_mm3':vol,
                    'solid_signed_volumes_mm3':[s.Volume() for s in solids],
                    'bounds_mm':list(p.bounds(shape))}
        for case_id in shard['cases']:
            budget();case_dir=source/'run'/case_id
            raw=json.loads((case_dir/'result.json').read_text());target=raw['target'];spec=target['specification']
            entry={'case_id':case_id,'a':target['a'],'b':target['b'],
                   'original_q_interval_exact':target['q_interval_exact'],
                   'original_result_sha256':sha(case_dir/'result.json'),
                   'original_disposition':raw['current_original_aggregate_disposition'],
                   'original_specification':spec,'material_readbacks':[],
                   'exported_scientific_material':[],'method_audit':{}}
            materials=[]
            for role in ('original-moving-input','original-fixed-input'):
                m=next(x for x in raw['material_exports'] if any(y['role']==role for y in x['references']))
                br=case_dir/m['exports']['brep']['path'];st=case_dir/m['exports']['step']['path']
                body=p.single(cq.Shape.importBrep(str(br)))
                reader=cq.importers.importStep(str(st)).vals();require(len(reader)==1,'one whole STEP root required')
                step=p.single(reader[0]);delta=[p.volume(body.cut(step)),p.volume(step.cut(body))]
                require(max(delta)<=1e-7,'original BREP/STEP bidirectional material mismatch')
                entry['material_readbacks'].append({'role':role,'brep_sha256':sha(br),'step_sha256':sha(st),
                    'brep_signature':signature(body),'step_signature':signature(step),
                    'BREP_minus_STEP_mm3':delta[0],'STEP_minus_BREP_mm3':delta[1],
                    'equal_within_original_volume_gate':True})
                materials.append(body)
            def emit(label,body):
                budget();p.whole_material(body)
                path=science/(case_id+'-'+label+'.brep');require(not path.exists(),'fresh scientific body file required')
                before_sig=signature(body);status=body.exportBrep(str(path))
                require(status is True and path.stat().st_size>0 and signature(body)==before_sig,'native BREP export failed or changed material')
                exported={'path':path.name,'bytes':path.stat().st_size,'sha256':sha(path),'signature':before_sig,
                          'native_export_status':str(status)}
                entry['exported_scientific_material'].append(exported)
                return exported
            entry['complete_inputs_BREP']=[emit('input-moving',materials[0]),emit('input-fixed',materials[1])]
            try:
                result=v3.evaluate(*materials,spec,target,emit,ROOT,entry['method_audit'])
                entry['unchanged_original_postguards_passed']=True
                entry['postguard_scope']='original static carrier Common records only; correlated continuous inclusion is separately documented'
            except Exception as exc:
                result={'disposition':'unresolved_evaluation','error':type(exc).__name__+': '+str(exc)}
                entry['unchanged_original_postguards_passed']=False
                entry['postguard_failure']=result['error']
            entry['new_result']=result
            report['case_results'].append({k:entry[k] for k in ['case_id','a','b','original_q_interval_exact',
                'original_disposition','unchanged_original_postguards_passed']})
            report['case_results'][-1]['new_disposition']=result['disposition']
            path=science/(case_id+'.json');identity.atomic_json(path,entry)
            report['case_results'][-1]['result_sha256']=sha(path)
            save()
        after=identity.finish(before,[*executed]);identity.atomic_json(out/'source-after-private.json',after)
        require(after['source_bytes_and_locked_environment_unchanged'],'original predicate or native input bytes changed')
        require(sha(profile_path)==profile_hash,'native profile original changed')
        require(own=={p.name:sha(p) for p in [Path(__file__),HERE/'correlated_v3.py',args.binding]},'external source changed')
        report.update(execution_completed=len(report['case_results'])==len(shard['cases']),
                      original_source_and_locked_environment_unchanged=True,
                      original_predicate_source_sha256={str(Path(k).relative_to(ROOT)):v for k,v in after['executed_source_and_input_sha256'].items()},
                      new_disposition_counts=dict(Counter(x['new_disposition'] for x in report['case_results'])),
                      all_unchanged_original_postguards_passed=all(x['unchanged_original_postguards_passed'] for x in report['case_results']))
    except BaseException as exc:
        report['failure']=type(exc).__name__+': '+str(exc)
    finally:
        report['seconds']=time.monotonic()-started
        report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        save()
    print(json.dumps({k:report.get(k) for k in ['execution_completed','shard','new_disposition_counts','failure','seconds']}),flush=True)
    return 0 if report['execution_completed'] and report.get('all_unchanged_original_postguards_passed') is True else 2


if __name__=='__main__':raise SystemExit(main())
