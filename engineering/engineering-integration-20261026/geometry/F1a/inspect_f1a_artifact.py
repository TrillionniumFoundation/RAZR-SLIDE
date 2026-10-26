"""Read a frozen public F1a engineering ZIP in memory; save only small evidence.

Input JSON on stdin supplies an authorized artifact file URI and official API
metadata. The URI is never written to the evidence output or printed.
"""
from __future__ import annotations
import argparse
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
RUN=40273568199
HEAD='935d6adb5ceeb2995971cb32ba2a5f7694114237'


def sha(data):return hashlib.sha256(data).hexdigest()


def require(ok,msg):
    if not ok:raise ValueError(msg)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--source-profile-analysis',type=Path,required=True)
    args=ap.parse_args();request=json.load(sys.stdin);meta=request['artifact'];pose=request['pose']
    require(pose in ('near','far') and meta['name']==f'S4-F1-{pose}-{RUN}-1-engineering','wrong artifact name')
    require(meta['workflow_run']['id']==RUN and meta['workflow_run']['head_sha']==HEAD,'wrong actual workflow identity')
    require(meta.get('expired') is False,'actual artifact expired')
    with urllib.request.urlopen(request['file_uri'],timeout=90) as response:
        data=response.read(meta['size_in_bytes']+1)
    require(len(data)==meta['size_in_bytes'],'official ZIP size differs')
    require(meta.get('digest')=='sha256:'+sha(data),'official ZIP digest differs or absent')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=[x.filename for x in z.infolist() if not x.is_dir()]
        require(len(names)==len(set(names)),'duplicate ZIP members')
        manifest_bytes=z.read('ENGINEERING_MANIFEST.json');manifest=json.loads(manifest_bytes)
        require(set(names)==set(manifest['members'])|{'ENGINEERING_MANIFEST.json'},'complete ZIP/member manifest differs')
        for rel,entry in manifest['members'].items():
            path=Path(rel);require(not path.is_absolute() and '..' not in path.parts,'unsafe member path')
            h=hashlib.sha256();size=0
            with z.open(rel) as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):
                    h.update(chunk);size+=len(chunk)
            require(size==entry['bytes'] and h.hexdigest()==entry['sha256'],'engineering member digest differs')
        proofs={};results={}
        for kind in ('factory','readback'):
            wrapper=json.loads(z.read(kind+'/worker/report.engineering.json'));r=wrapper['engineering_record'];proofs[kind]=(wrapper,r)
            require(wrapper.get('derived_projection_not_raw_original') is True,'report is not marked projection')
            require(r.get('functional_source_commit')==S4 and r.get('pose')==pose and r.get('execution_completed') is True,
                    'actual source, pose or complete execution differs')
            ident=r['source_identity_projection']
            require(ident.get('source_commit_before')==ident.get('source_commit_after')==S4
                    and ident.get('worktree_clean_before') is True
                    and ident.get('source_bytes_and_locked_environment_unchanged') is True
                    and ident.get('locked_environment_before_passed') is True
                    and ident.get('locked_environment_after_passed') is True
                    and ident.get('checked_package_count_before')==ident.get('checked_package_count_after')==43,
                    'actual source and environment qualification incomplete')
            roles=r['participant_names'];pairs=r['pairs']
            require(len(set(roles))==154 and len(pairs)==11781
                    and [(x['a'],x['b']) for x in pairs]==list(itertools.combinations(sorted(roles),2))
                    and r['all_unordered_pairs_present_once'] is True
                    and not r['evaluation_failures'] and not r['mismatches_to_factory'],
                    'actual complete all-pairs evaluation differs')
            require(all(type(x['common_mm3']) in (int,float) and math.isfinite(x['common_mm3']) and x['common_mm3']>=0
                    and x['rejected']==(x['common_mm3']>1e-7) for x in pairs),'original signed Common predicate differs')
            journal=[json.loads(x) for x in z.read(kind+'/worker/pairs.jsonl').decode().splitlines()]
            require(len(journal)==23562 and [x['row'] for x in journal if x['event']=='completed']==pairs
                    and [(x['a'],x['b']) for x in journal if x['event']=='selected']==[(x['a'],x['b']) for x in pairs],
                    'original pair journal differs')
            results[kind]={'projection_sha256':sha(z.read(kind+'/worker/report.engineering.json')),
                'original_report_sha256':wrapper['original']['sha256'],'original_report_bytes':wrapper['original']['bytes'],
                'execution_completed':r['execution_completed'],'finite_pose_clear':r['finite_pose_clear'],
                'pair_count':len(pairs),'journal_rows':len(journal),'seconds':r['seconds'],
                'source_and_43_package_environment_unchanged_observed':True,
                'panel_KEY_direct_Common':r['panel_KEY_direct_Common'],
                'positive_pairs':[{'a':x['a'],'b':x['b'],'common_mm3':x['common_mm3'],'rejected':x['rejected']} for x in r['positive_pairs']]}
        fw,f=proofs['factory'];rw,r=proofs['readback']
        require(f.get('actual_complete_factory_called') is True and f.get('fixed_pair_certificate_reused') is False
                and f.get('geometry_repair_applied') is False,'unmodified complete original factory not observed')
        require(r['factory_report_sha256']==fw['original']['sha256'],'actual reader is not bound to actual producer')
        require(r['native_STEP_readback_executed'] is True and len(r['body_readbacks'])==154
                and all(x['passed'] for x in r['body_readbacks'].values()),'actual complete STEP readback incomplete')
        comparisons=r['L1_whole_endpoint_material_comparisons']
        require(r.get('L1_original_input_members_verified')==104
                and r.get('L1_binding_sha256')=='cc4d09cf54d7b92cadd626051b11ebe7451f369bd0811f6c238717133f4178a2',
                'all original L1 input byte identities are not verified')
        require(len(comparisons)==8 and all(x['passed'] is True for x in comparisons),'actual L1 complete material comparison failed')
        for side in 'LR':
            v=f['panel_KEY_direct_Common'][side]['common_mm3']
            require(v>1e-7,'original panel/KEY rejected witness did not reproduce')
            pair=next(x for x in f['pairs'] if {x['a'],x['b']}=={'A_BACK_PANEL',side+'_KEY'})
            require(abs(v-pair['common_mm3'])<=1e-7,'direct and all-pair Common differ')
        source=json.loads(args.source_profile_analysis.read_text());profile_checks=[]
        fields=('pin_radius','floor_height','floor_corner_q','ramp_slope','pin_q','lower_stop_height','q_max')
        for side in 'LR':
            for index,profile in enumerate(f['native_positive_q_STOP_SPRING_profiles'][side]):
                expected=source['profiles'][side][index]['original_profile_receipt']
                profile_checks.append({'side':side,'stop_index':index,
                    'parameters_match_frozen_source_analysis':all(profile['parameters'][k]==expected[k] for k in fields),
                    'breakpoints_match_frozen_source_analysis':profile['receipt']['breakpoints_q_mm']==expected['breakpoints_q_mm'],
                    'actual_current_q_state':profile['current_q_state'],
                    'actual_STOP_signature':profile['actual_STOP_signature'],
                    'actual_SPRING_envelope_signature':profile['actual_SPRING_envelope_signature']})
        scope=json.loads(z.read('EXPORT_SCOPE.json'))
        require(scope['raw_producer_reader_reports_modified'] is False and scope['raw_runtime_durable_preservation_claimed'] is False,
                'engineering export overclaims raw runtime preservation')
        summary={'schema':'razr-F1a-memory-archive-inspection-v1','pose':pose,'run_id':RUN,'head_sha':HEAD,
            'artifact_id':meta['id'],'artifact_name':meta['name'],'artifact_expires_at':meta.get('expires_at'),
            'official_ZIP_sha256':sha(data),'official_ZIP_bytes':len(data),'official_ZIP_digest_and_size_verified':True,
            'all_ZIP_member_CRC_verified_during_full_reads':True,'all_engineering_member_hashes_verified':len(manifest['members']),
            'engineering_manifest_sha256':sha(manifest_bytes),'results':results,
            'actual_factory_pose_input':f['pose_input'],'actual_L1_whole_endpoint_material_comparisons':comparisons,
            'actual_four_profile_source_analysis_comparisons':profile_checks,
            'complete_STEP_body_count_verified':154,'all_pairs_and_journals_verified_from_actual_full_projections':True,
            'local_new_CAD_execution_claimed':False,'raw_runtime_reports_reconstructed':False,
            'raw_runtime_durable_preservation_claimed':False,'complete_archive_saved_locally':False,
            'requires_durable_archiving_beyond_GitHub_artifact_expiry':True,
            'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/f'F1A_{pose}_ENGINEERING_MANIFEST.json').write_bytes(manifest_bytes)
        (args.output/f'F1A_{pose}_INSPECTION.json').write_text(json.dumps(summary,indent=2)+'\n')
        original_summary=z.read('F1-complete-observation.json')
        (args.output/f'F1A_{pose}_COMPLETE_OBSERVATION.json').write_bytes(original_summary)
        print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
