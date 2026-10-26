"""Verify actual K1 engineering ZIP bytes in memory; save only small evidence.

The authorized temporary file URI is supplied on stdin, is never persisted and
is never included in output. Full original geometric records stay in the ZIP.
This inspector does not rerun CAD and does not turn execution into clearance.
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
RUN=40276423445
HEAD='78da3826a1cce029cb36b76555d6be7de2001ba2'
CANDIDATE_SHA='3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578'
CONTRACT_SHA='17e1532ed82eff1298e9525456d6953df56437082ef2918f3d04839cff200455'
TOL=1e-7


def sha(data):return hashlib.sha256(data).hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--f1a-binding',type=Path,required=True)
    args=ap.parse_args();request=json.load(sys.stdin);meta=request['artifact'];pose=request['pose']
    binding=json.loads(args.f1a_binding.read_text());prior=binding['poses'][pose]
    require(pose in ('near','far') and meta['name']==f'S4-K1-{pose}-{RUN}-1-engineering','wrong artifact name')
    require(meta['workflow_run']['id']==RUN and meta['workflow_run']['head_sha']==HEAD,'wrong run/source identity')
    require(meta.get('expired') is False and meta['size_in_bytes']<128*2**20,'expired or oversized byte archive')
    with urllib.request.urlopen(request['file_uri'],timeout=90) as response:
        data=response.read(meta['size_in_bytes']+1)
    require(len(data)==meta['size_in_bytes'] and meta['digest']=='sha256:'+sha(data),'official ZIP size/digest differs')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        require(len(names)==len(set(names)) and not any(x.is_dir() for x in infos),'duplicate or non-file ZIP member')
        for item in infos:
            path=Path(item.filename)
            require(not path.is_absolute() and '..' not in path.parts and (item.external_attr>>16)&0o170000!=0o120000,
                    'unsafe ZIP member')
        mb=z.read('ENGINEERING_MANIFEST.json');manifest=json.loads(mb)
        require(manifest['schema']=='razr-K1-engineering-export-manifest-v1','wrong engineering manifest schema')
        require(set(names)==set(manifest['members'])|{'ENGINEERING_MANIFEST.json'},'ZIP/member inventory differs')
        for rel,ref in manifest['members'].items():
            h=hashlib.sha256();count=0
            with z.open(rel) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block);count+=len(block)
            require(count==ref['bytes'] and h.hexdigest()==ref['sha256'],'engineering member SHA/size differs')
        pm=z.read('prerequisite/ENGINEERING_MANIFEST.json')
        require(sha(pm)==prior['engineering_manifest_sha256'],'actual F1a prerequisite manifest differs')
        prior_members=json.loads(pm)['members']
        require(all(manifest['members'].get('prerequisite/'+k)==v for k,v in prior_members.items()),
                'actual complete F1a prerequisite members differ')
        require(sha(z.read('source/k1/key_forward_loop_v1.py'))==CANDIDATE_SHA
                and sha(z.read('source/k1/KEY_FORWARD_LOOP_V1_CONTRACT.json'))==CONTRACT_SHA,
                'named candidate source or independent contract differs')
        results={};reports={};controllers={}
        for kind in ('factory','readback'):
            report_bytes=z.read(kind+'/worker/report.engineering.json');wrapper=json.loads(report_bytes)
            r=wrapper['engineering_record'];reports[kind]=(wrapper,r)
            require(wrapper['derived_projection_not_raw_original'] is True,'report not explicitly marked projection')
            require(r['functional_source_commit']==S4 and r['pose']==pose and r['candidate_name']=='key_forward_loop_v1',
                    'wrong report source, pose or candidate')
            cwrapper=json.loads(z.read(kind+'/controller.engineering.json'));c=cwrapper['engineering_record']
            require(cwrapper['derived_projection_not_raw_original'] is True,'controller not explicitly marked projection')
            require(c['completed'] is True and c['worker_exit_code']==0
                    and c['result_sha256']==wrapper['original']['sha256'],'controller completion or result identity differs')
            require(all(c[k] is True for k in ('owned_child_identity_verified','source_bytes_unchanged',
                    'locked_environment_unchanged','owned_channel_descriptors_closed')),'owned lifecycle/source checks incomplete')
            require(c['limits']['wall_seconds']==1200 and c['limits']['worker_peak_RSS_MiB']==1536
                    and c['limits']['shared_unreclaimable_GiB']==6.8,'original native limits changed')
            ident=r['source_identity_projection']
            require(ident['source_commit_before']==ident['source_commit_after']==S4
                    and ident['worktree_clean_before'] is True and ident['source_bytes_and_locked_environment_unchanged'] is True
                    and ident['locked_environment_before_passed'] is True and ident['locked_environment_after_passed'] is True
                    and ident['checked_package_count_before']==ident['checked_package_count_after']==43,
                    'actual source/environment checks incomplete')
            require(r['execution_completed'] is True and not r['evaluation_failures'] and not r['mismatches_to_factory'],
                    'actual complete evaluation absent or mismatched')
            roles=r['participant_names'];pairs=r['pairs'];expected=list(itertools.combinations(sorted(roles),2))
            require(len(set(roles))==154 and len(pairs)==len(expected)==11781
                    and [(x['a'],x['b']) for x in pairs]==expected
                    and r['all_unordered_pairs_present_once'] is True and r['persisted_pair_count']==11781,
                    'complete original pair inventory differs')
            require(all(type(x['common_mm3']) in (int,float) and math.isfinite(x['common_mm3']) and x['common_mm3']>=0
                    and x['rejected']==(x['common_mm3']>TOL) for x in pairs),'original signed volume/predicate differs')
            positive=[x for x in pairs if x['common_mm3']>0]
            require(r['positive_pairs']==positive,'positive-pair projection differs from complete pairs')
            observed_clear=not any(x['rejected'] for x in pairs)
            require(r['finite_pose_clear']==observed_clear,'finite clear claim differs from actual pair results')
            journal=[json.loads(x) for x in z.read(kind+'/worker/pairs.jsonl').decode().splitlines()]
            require(len(journal)==23562 and [(x['a'],x['b']) for x in journal if x['event']=='selected']==expected
                    and [x['row'] for x in journal if x['event']=='completed']==pairs,'actual full pair journal differs')
            require(all(r[k] is False for k in ('complete_product_motion_proved','continuous_backlash_domain_proved',
                    'physical_qualification','candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass')),
                    'finite experiment improperly promoted')
            for side in 'LR':
                direct=r['panel_KEY_direct_Common'][side]['common_mm3']
                row=next(x for x in pairs if {x['a'],x['b']}=={'A_BACK_PANEL',side+'_KEY'})
                require(abs(direct-row['common_mm3'])<=TOL,'direct panel/KEY and complete-pair result differ')
            results[kind]={'projection_sha256':sha(report_bytes),'original_report_sha256':wrapper['original']['sha256'],
                'original_report_bytes':wrapper['original']['bytes'],'execution_completed':True,
                'finite_pose_clear':observed_clear,'pair_count':len(pairs),'journal_rows':len(journal),
                'seconds':r['seconds'],'source_and_43_package_environment_unchanged_observed':True,
                'panel_KEY_direct_Common':r['panel_KEY_direct_Common'],
                'positive_pairs':[{'a':x['a'],'b':x['b'],'common_mm3':x['common_mm3'],'rejected':x['rejected']} for x in positive],
                'method_counts':dict(Counter(x['method'] for x in pairs))}
            controllers[kind]={k:c[k] for k in ('completed','worker_exit_code','limits','elapsed_seconds',
                'source_bytes_unchanged','locked_environment_unchanged','owned_channel_descriptors_closed')}
        fw,f=reports['factory'];rw,r=reports['readback']
        require(r['factory_report_sha256']==fw['original']['sha256'],'reader bound to another producer')
        require(f['actual_complete_factory_called'] is True and f['geometry_repair_applied'] is True
                and f['fixed_pair_certificate_reused'] is False,'complete original factory/candidate application absent')
        require(len(f['original_baseline_material_comparisons'])==154
                and all(x['equal_within_original_1e_minus_7_mm3'] for x in f['original_baseline_material_comparisons'].values()),
                'fresh complete factory not materially equal to F1a')
        require(f['candidate_application']['source_sha256']==CANDIDATE_SHA and r['candidate_contract_sha256']==CONTRACT_SHA,
                'actual producer/reader named source identities differ')
        require(r['native_STEP_readback_executed'] is True and r['separate_process_from_factory'] is True
                and r['independent_CAD_kernel'] is False and r['independent_material_builder_does_not_import_candidate_source'] is True,
                'independent process/builder scope differs')
        require(len(r['body_readbacks'])==154 and all(x['passed'] for x in r['body_readbacks'].values())
                and set(r['material_reconstruction'])=={'L_KEY','R_KEY'}
                and all(x['passed'] for x in r['material_reconstruction'].values()),'complete independent STEP/material audit failed')
        for side in 'LR':
            before=f['baseline_panel_KEY_direct_Common'][side]
            require(before['common_mm3']>TOL and abs(before['difference_from_original_F1a_mm3'])<=TOL,
                    'original actual collision did not reproduce before repair')
            account=r['material_reconstruction'][side+'_KEY']['independent_account']
            require(abs(account['removed_mm3']-.594)<=TOL,'actual removed material differs')
            require(all(abs(account[k])<=TOL for k in ('signed_material_balance_error_mm3','retained_original_material_loss_mm3',
                    'unintended_loss_outside_declared_cutter_mm3','material_restored_inside_clearance_cut_mm3')),
                    'actual material conservation/retention failed')
        scope_bytes=z.read('EXPORT_SCOPE.json');scope=json.loads(scope_bytes)
        require(scope['schema']=='razr-K1-engineering-export-scope-v1' and scope['functional_source_commit']==S4
                and scope['raw_producer_reader_reports_modified'] is False and scope['all_copied_original_bytes_verified'] is True
                and scope['raw_runtime_durable_preservation_claimed'] is False,'engineering export scope differs')
        require(all(manifest['members'].get(k)==v for k,v in scope['copied_originals'].items()),'original byte preservation differs')
        require(all(set(x)=={'bytes','category','sha256'} for x in scope['omitted_runtime_file_hashes']),
                'omitted runtime record contains more than category/size/hash')
        observation_bytes=z.read('K1-complete-observation.json');observation=json.loads(observation_bytes)
        finite_clear=all(x['finite_pose_clear'] for x in results.values())
        require(observation['finite_witness_clear']==finite_clear,'original complete observation misstates finite result')
        summary={'schema':'razr-K1-memory-archive-inspection-v1','pose':pose,'run_id':RUN,'head_sha':HEAD,
            'artifact_id':meta['id'],'artifact_name':meta['name'],'artifact_expires_at':meta['expires_at'],
            'official_ZIP_sha256':sha(data),'official_ZIP_bytes':len(data),'official_ZIP_digest_and_size_verified':True,
            'all_ZIP_member_CRC_verified_during_full_reads':True,'all_engineering_member_hashes_verified':len(manifest['members']),
            'engineering_manifest_sha256':sha(mb),'actual_full_F1a_prerequisite_manifest_sha256':sha(pm),
            'actual_full_F1a_prerequisite_member_count':len(prior_members),'candidate_source_sha256':CANDIDATE_SHA,
            'contract_sha256':CONTRACT_SHA,'actual_factory_pose_input':f['pose_input'],
            'results':results,'controllers':controllers,'all_154_whole_baseline_material_comparisons_passed':True,
            'baseline_panel_KEY_direct_Common':f['baseline_panel_KEY_direct_Common'],
            'producer_material_accounts':f['candidate_application']['material_accounts'],
            'independent_material_reconstruction':r['material_reconstruction'],
            'complete_STEP_body_count_verified':154,'all_pairs_and_journals_verified_from_actual_full_projections':True,
            'finite_witness_clear':finite_clear,'actual_export_scope_sha256':sha(scope_bytes),
            'local_new_CAD_execution_claimed':False,'raw_runtime_reports_reconstructed':False,
            'raw_runtime_durable_preservation_claimed':False,'complete_archive_saved_locally':False,
            'requires_durable_archiving_beyond_GitHub_artifact_expiry':True,
            'complete_product_motion_proved':False,'physical_allowed_domain_proved':False,'strength_qualified':False,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
        scope_projection={k:scope[k] for k in ('schema','functional_source_commit','raw_producer_reader_reports_modified',
            'all_copied_original_bytes_verified','raw_runtime_durable_preservation_claimed','raw_runtime_location',
            'local_runtime_verification_results','scope')}
        scope_projection.update(derived_projection_not_raw_original=True,original_sha256=sha(scope_bytes),
            original_bytes=len(scope_bytes),root_keys=sorted(scope),copied_original_count=len(scope['copied_originals']),
            derived_projection_count=len(scope['derived_projections']),omitted_runtime_file_count=len(scope['omitted_runtime_file_hashes']),
            omitted_category_counts=dict(Counter(x['category'] for x in scope['omitted_runtime_file_hashes'])),
            copied_originals_exactly_match_manifest=True,omitted_records_have_only_category_size_sha256=True)
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/f'K1_{pose}_ENGINEERING_MANIFEST.json').write_bytes(mb)
        (args.output/f'K1_{pose}_COMPLETE_OBSERVATION.json').write_bytes(observation_bytes)
        (args.output/f'K1_{pose}_INSPECTION.json').write_text(json.dumps(summary,indent=2)+'\n')
        (args.output/f'K1_{pose}_EXPORT_SCOPE_PROJECTION.json').write_text(json.dumps(scope_projection,indent=2)+'\n')
        print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
