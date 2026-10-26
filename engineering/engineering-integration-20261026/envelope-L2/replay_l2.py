"""New V2 method replay of every retained L1 E17/O72 original input pair.

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
    report={'schema':'razr-L2-original-L1-input-replay-v2','functional_predicate_source_commit':S4,
            'new_method':'all_boundary_carriers_v2','shard':args.shard,'execution_completed':False,
            'original_volume_gate_mm3':1e-7,'case_results':[],**{k:False for k in FALSE_FLAGS}}
    own={p.name:sha(p) for p in [Path(__file__),HERE/'envelope_v2.py',HERE/'test_l2_native.py',args.binding]}
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
        import envelope_v2 as v2
        import test_l2_native
        import validate_product_nominal_report as original_postguard
        report['new_method_native_controls']=test_l2_native.execute()
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
                   'original_specification':spec,'material_readbacks':[]}
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
            def retain_carrier(carrier,fixed,detail):
                budget()
                name=case_id+'-'+detail['frame']+'-region-'+str(detail['region_index'])
                path=science/(name+'.brep')
                require(not path.exists(),'new raw carrier path required')
                status=carrier.exportBrep(str(path));require(status is True and path.stat().st_size>0,'carrier BREP export failed')
                record={**detail,'carrier':{'path':path.name,'bytes':path.stat().st_size,'sha256':sha(path),
                    'signature':signature(carrier),'native_export_status':str(status)}}
                try:
                    common=carrier.intersect(fixed)
                    cp=science/(name+'-Common.brep')
                    status=common.exportBrep(str(cp));require(status is True and cp.stat().st_size>0,'Common BREP export failed')
                    cs={'shape_type':common.ShapeType(),'is_valid':common.isValid(),
                        'signed_volume_mm3':float(common.Volume()),'solid_signed_volumes_mm3':[s.Volume() for s in common.Solids()]}
                    record['recomputed_native_Common']={'path':cp.name,'bytes':cp.stat().st_size,'sha256':sha(cp),
                        'signature':cs,'native_export_status':str(status),
                        'is_a_new_followup_Common_operation_not_the_saved_failed_object':True}
                    if 'strict_common' in detail:
                        require(abs(cs['signed_volume_mm3']-detail['strict_common']['common_mm3'])<=1e-7,'retained Common differs from checked Common')
                except Exception as exc:
                    record['followup_Common_failure']=type(exc).__name__+': '+str(exc)
                entry.setdefault('material_retention',[]).append(record)
                if 'strict_common' in detail:
                    require('followup_Common_failure' not in record,'retained checked Common failed consistency')
                budget()
                return record
            result=v2.continuous_pair(*materials,spec['coefficients'],
                domain=tuple(tuple(x) for x in spec['parameter_intervals']),evidence_callback=retain_carrier)
            entry['new_result']=result
            try:
                original_postguard.validate_frame(result)
                entry['unchanged_original_postguard_passed']=True
            except Exception as exc:
                entry['unchanged_original_postguard_passed']=False
                entry['postguard_failure']=type(exc).__name__+': '+str(exc)
            report['case_results'].append({k:entry[k] for k in ['case_id','a','b','original_q_interval_exact',
                'original_disposition','unchanged_original_postguard_passed']})
            report['case_results'][-1]['new_disposition']=result['disposition']
            path=science/(case_id+'.json');identity.atomic_json(path,entry)
            report['case_results'][-1]['result_sha256']=sha(path)
            save()
        after=identity.finish(before,[*executed]);identity.atomic_json(out/'source-after-private.json',after)
        require(after['source_bytes_and_locked_environment_unchanged'],'original predicate or native input bytes changed')
        require(own=={p.name:sha(p) for p in [Path(__file__),HERE/'envelope_v2.py',HERE/'test_l2_native.py',args.binding]},'external source changed')
        report.update(execution_completed=len(report['case_results'])==len(shard['cases']),
                      original_source_and_locked_environment_unchanged=True,
                      original_predicate_source_sha256={str(Path(k).relative_to(ROOT)):v for k,v in after['executed_source_and_input_sha256'].items()},
                      new_disposition_counts=dict(Counter(x['new_disposition'] for x in report['case_results'])),
                      all_unchanged_original_postguards_passed=all(x['unchanged_original_postguard_passed'] for x in report['case_results']))
    except BaseException as exc:
        report['failure']=type(exc).__name__+': '+str(exc)
    finally:
        report['seconds']=time.monotonic()-started
        report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        save()
    print(json.dumps({k:report.get(k) for k in ['execution_completed','shard','new_disposition_counts','failure','seconds']}),flush=True)
    return 0 if report['execution_completed'] and report.get('all_unchanged_original_postguards_passed') is True else 2


if __name__=='__main__':raise SystemExit(main())
