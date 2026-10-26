"""Inspect actual finite endpoint engineering ZIPs in memory, retaining failures.

Only byte-safe small observations are saved. No CAD is executed locally, no raw
runtime is reconstructed, and incomplete reports remain incomplete.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import sys
import urllib.request
import zipfile

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
RUN=40277813145
HEAD='c1fa9e7271e0ff7a7146c03b702994b3dae842d4'
ENDPOINTS={'stow_tabs_0':154,'stow_tabs_3':154,'predock':154,'open_installed':161}
TOL=1e-7


def sha(data):return hashlib.sha256(data).hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def source_ok(r):
    d=r.get('source_identity_projection',{})
    return (d.get('source_commit_before')==d.get('source_commit_after')==S4
        and all(d.get(k) is True for k in ('worktree_clean_before','source_bytes_and_locked_environment_unchanged',
            'locked_environment_before_passed','locked_environment_after_passed'))
        and d.get('checked_package_count_before')==d.get('checked_package_count_after')==43)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--k1-binding',type=Path,required=True);args=ap.parse_args()
    request=json.load(sys.stdin);meta=request['artifact'];pose=request['pose'];expected=ENDPOINTS[pose]
    binding=json.loads(args.k1_binding.read_text());pair_count=expected*(expected-1)//2
    require(meta['name']==f'S4-K2-{pose}-{RUN}-1-engineering' and meta['workflow_run']['id']==RUN
            and meta['workflow_run']['head_sha']==HEAD,'actual K2 workflow identity differs')
    require(meta.get('expired') is False and meta['size_in_bytes']<128*2**20,'expired or oversized byte archive')
    with urllib.request.urlopen(request['file_uri'],timeout=90) as stream:data=stream.read(meta['size_in_bytes']+1)
    require(len(data)==meta['size_in_bytes'] and meta['digest']=='sha256:'+sha(data),'official ZIP size/digest differs')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        require(len(names)==len(set(names)) and not any(x.is_dir() for x in infos),'duplicate or non-file ZIP member')
        for item in infos:
            path=Path(item.filename)
            require(not path.is_absolute() and '..' not in path.parts and (item.external_attr>>16)&0o170000!=0o120000,
                    'unsafe ZIP member')
        mb=z.read('ENGINEERING_MANIFEST.json');manifest=json.loads(mb)
        require(manifest['schema']=='razr-K2-engineering-export-manifest-v1','wrong engineering manifest schema')
        require(set(names)==set(manifest['members'])|{'ENGINEERING_MANIFEST.json'},'ZIP/manifest inventory differs')
        for rel,ref in manifest['members'].items():
            h=hashlib.sha256();count=0
            with z.open(rel) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block);count+=len(block)
            require(count==ref['bytes'] and h.hexdigest()==ref['sha256'],'engineering member SHA/size differs')
        prerequisites={}
        for prior_pose in ('near','far'):
            prefix='prerequisite-'+prior_pose+'/';name=prefix+'ENGINEERING_MANIFEST.json'
            if name not in names:
                prerequisites[prior_pose]={'complete_frozen_engineering_archive_present':False};continue
            pm=z.read(name);members=json.loads(pm)['members']
            require(sha(pm)==binding['poses'][prior_pose]['engineering_manifest_sha256'],'K1 manifest identity differs')
            require(all(manifest['members'].get(prefix+k)==v for k,v in members.items()),'K1 prerequisite bytes differ')
            prerequisites[prior_pose]={'complete_frozen_engineering_archive_present':True,
                'manifest_sha256':sha(pm),'verified_member_count':len(members)}
        reports={};results={};controllers={}
        for kind in ('factory','readback'):
            name=kind+'/worker/report.engineering.json'
            if name not in names:
                results[kind]={'report_present':False,'execution_completed':False,'scientific_complete_verified':False,
                    'finite_pose_clear':False};continue
            report_bytes=z.read(name);wrapper=json.loads(report_bytes);r=wrapper['engineering_record'];reports[kind]=(wrapper,r)
            require(wrapper['derived_projection_not_raw_original'] is True,'explicit report projection required')
            require(r['functional_source_commit']==S4 and r['pose']==pose,'report source/pose differs')
            cname=kind+'/controller.engineering.json';c={}
            if cname in names:
                cw=json.loads(z.read(cname));require(cw['derived_projection_not_raw_original'] is True,'controller projection required')
                c=cw['engineering_record']
                if c.get('result_sha256') is not None:require(c['result_sha256']==wrapper['original']['sha256'],'controller result SHA differs')
                controllers[kind]={k:v for k,v in c.items() if k in ('completed','worker_exit_code','limits','elapsed_seconds',
                    'source_bytes_unchanged','locked_environment_unchanged','owned_channel_descriptors_closed',
                    'capacity_or_wall_stop','resource_start_refused')}
            roles=r.get('participant_names',[]);pairs=r.get('pairs',[])
            inventory_ok=(len(set(roles))==expected and len(pairs)==pair_count
                and [(x['a'],x['b']) for x in pairs]==list(itertools.combinations(sorted(roles),2)))
            numeric_ok=all(type(x.get('common_mm3')) in (int,float) and math.isfinite(x['common_mm3'])
                and x['common_mm3']>=0 and x['rejected']==(x['common_mm3']>TOL) for x in pairs)
            positive=[x for x in pairs if x.get('common_mm3',0)>0];journal=[]
            jname=kind+'/worker/pairs.jsonl'
            if jname in names:journal=[json.loads(x) for x in z.read(jname).decode().splitlines()]
            journal_ok=(len(journal)==2*pair_count and [x['row'] for x in journal if x['event']=='completed']==pairs
                and [(x['a'],x['b']) for x in journal if x['event']=='selected']==[(x['a'],x['b']) for x in pairs])
            owned_ok=(c.get('completed') is True and c.get('worker_exit_code')==0
                and all(c.get(k) is True for k in ('owned_child_identity_verified','source_bytes_unchanged',
                    'locked_environment_unchanged','owned_channel_descriptors_closed')))
            if c.get('limits'):
                require(c['limits']['wall_seconds']==1200 and c['limits']['worker_peak_RSS_MiB']==1536
                        and c['limits']['shared_unreclaimable_GiB']==6.8,'original native limits changed')
            complete=(r.get('execution_completed') is True and inventory_ok and numeric_ok and journal_ok and owned_ok
                and source_ok(r) and r.get('all_unordered_pairs_present_once') is True
                and not r.get('evaluation_failures') and not r.get('mismatches_to_factory'))
            if r.get('execution_completed') is True:
                require(complete,'report claims completion without complete supporting original records')
                require(r['finite_pose_clear']==(not any(x['rejected'] for x in pairs)),'finite-clear claim differs')
                # Reader comparison fields are added after positive_pairs snapshot,
                # so compare the physical pair identity/value/classification only.
                proj=lambda values:[{k:x[k] for k in ('a','b','common_mm3','rejected')} for x in values]
                require(proj(r['positive_pairs'])==proj(positive),'positive-pair physical records differ')
            require(all(r.get(k) is False for k in ('complete_product_motion_proved','continuous_backlash_domain_proved',
                'physical_qualification','candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass')),
                'endpoint evidence improperly promoted')
            results[kind]={'report_present':True,'projection_sha256':sha(report_bytes),
                'original_report_sha256':wrapper['original']['sha256'],'original_report_bytes':wrapper['original']['bytes'],
                'execution_completed':r.get('execution_completed',False),'scientific_complete_verified':complete,
                'finite_pose_clear':bool(complete and r.get('finite_pose_clear')),'status':r.get('status'),
                'failure_stage':r.get('failure_stage'),'original_failure_type':r.get('original_failure_type'),
                'original_failure_message_sha256':r.get('original_failure_message_sha256'),
                'pair_count':len(pairs),'expected_pair_count':pair_count,'journal_rows':len(journal),
                'seconds':r.get('seconds'),'source_and_43_package_environment_unchanged_observed':source_ok(r),
                'panel_KEY_direct_Common':r.get('panel_KEY_direct_Common'),
                'positive_pairs':[{k:x[k] for k in ('a','b','common_mm3','rejected')} for x in positive],
                'evaluation_failures':r.get('evaluation_failures',[]),'mismatches_to_factory':r.get('mismatches_to_factory',[]),
                'method_counts':dict(Counter(x.get('method','evaluation_failure') for x in pairs))}
        readback_checks={};factory_checks={};pose_input=None
        if 'factory' in reports:
            fw,f=reports['factory'];pose_input=f.get('pose_input')
            factory_checks={'actual_complete_factory_called':f.get('actual_complete_factory_called',False),
                'actual_K1_prerequisite':f.get('K1_prerequisite'),
                'actual_named_KEY_factory_comparisons':f.get('native_scene_metadata',{}).get('named_KEY_candidate')}
            if results['factory']['scientific_complete_verified']:
                require(f['actual_complete_factory_called'] is True and f['fixed_pair_certificate_reused'] is False
                        and f['geometry_repair_applied'] is True and f['participant_count']==expected,
                        'actual complete candidate endpoint factory absent')
        if 'readback' in reports:
            rw,r=reports['readback']
            if results['readback']['scientific_complete_verified']:
                require('factory' in reports and r['factory_report_sha256']==reports['factory'][0]['original']['sha256'],
                        'reader bound to a different producer')
                require(r['native_STEP_readback_executed'] is True and r['separate_process_from_factory'] is True
                        and r['independent_CAD_kernel'] is False and len(r['body_readbacks'])==expected
                        and all(x['passed'] for x in r['body_readbacks'].values()),'complete STEP readback not supported')
                require(set(r['candidate_q0_material_comparisons'])=={'L','R'}
                        and all(0<=v<=TOL for d in r['candidate_q0_material_comparisons'].values() for v in d.values()),
                        'candidate KEYs differ from actual K1 whole material')
            readback_checks={'actual_complete_STEP_readback_count':len(r.get('body_readbacks',{})),
                'candidate_q0_material_comparisons':r.get('candidate_q0_material_comparisons'),
                'actual_K1_prerequisite':r.get('K1_prerequisite')}
        scope_bytes=z.read('EXPORT_SCOPE.json');scope=json.loads(scope_bytes)
        require(scope['schema']=='razr-K2-engineering-export-scope-v1' and scope['functional_source_commit']==S4
                and scope['raw_producer_reader_reports_modified'] is False and scope['all_copied_original_bytes_verified'] is True
                and scope['raw_runtime_durable_preservation_claimed'] is False,'engineering export scope differs')
        require(all(manifest['members'].get(k)==v for k,v in scope['copied_originals'].items()),'copied original bytes differ')
        require(all(set(x)=={'bytes','category','sha256'} for x in scope['omitted_runtime_file_hashes']),
                'omitted runtime record includes content or locator')
        finite_clear=all(results[k]['finite_pose_clear'] for k in ('factory','readback'))
        summary={'schema':'razr-K2-memory-archive-inspection-v1','pose':pose,'run_id':RUN,'head_sha':HEAD,
            'artifact_id':meta['id'],'artifact_name':meta['name'],'artifact_expires_at':meta['expires_at'],
            'official_ZIP_sha256':sha(data),'official_ZIP_bytes':len(data),'official_ZIP_digest_and_size_verified':True,
            'all_ZIP_member_CRC_verified_during_full_reads':True,'all_engineering_member_hashes_verified':len(manifest['members']),
            'engineering_manifest_sha256':sha(mb),'actual_pose_input':pose_input,'prerequisites':prerequisites,
            'results':results,'controllers':controllers,'factory_checks':factory_checks,'readback_checks':readback_checks,
            'expected_participant_count':expected,'expected_pair_count_per_worker':pair_count,
            'finite_endpoint_complete':all(results[k]['scientific_complete_verified'] for k in ('factory','readback')),
            'finite_endpoint_clear':finite_clear,'actual_export_scope_sha256':sha(scope_bytes),
            'local_new_CAD_execution_claimed':False,'raw_runtime_reports_reconstructed':False,
            'raw_runtime_durable_preservation_claimed':False,'complete_archive_saved_locally':False,
            'requires_durable_archiving_beyond_GitHub_artifact_expiry':True,'complete_product_motion_proved':False,
            'physical_allowed_domain_proved':False,'strength_qualified':False,'candidate_go':False,
            'fixture_fabrication_go':False,'manufacturing_go':False}
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/f'K2_{pose}_ENGINEERING_MANIFEST.json').write_bytes(mb)
        (args.output/f'K2_{pose}_INSPECTION.json').write_text(json.dumps(summary,indent=2)+'\n')
        oname='K2-complete-observation.json'
        if oname in names:
            ob=z.read(oname);(args.output/f'K2_{pose}_COMPLETE_OBSERVATION.json').write_bytes(ob)
        scope_projection={k:scope[k] for k in ('schema','functional_source_commit','raw_producer_reader_reports_modified',
            'all_copied_original_bytes_verified','raw_runtime_durable_preservation_claimed','raw_runtime_location',
            'local_runtime_verification_results','scope')}
        scope_projection.update(derived_projection_not_raw_original=True,original_sha256=sha(scope_bytes),
            original_bytes=len(scope_bytes),root_keys=sorted(scope),copied_original_count=len(scope['copied_originals']),
            derived_projection_count=len(scope['derived_projections']),omitted_runtime_file_count=len(scope['omitted_runtime_file_hashes']),
            copied_originals_exactly_match_manifest=True,omitted_records_have_only_category_size_sha256=True)
        (args.output/f'K2_{pose}_EXPORT_SCOPE_PROJECTION.json').write_text(json.dumps(scope_projection,indent=2)+'\n')
        print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
