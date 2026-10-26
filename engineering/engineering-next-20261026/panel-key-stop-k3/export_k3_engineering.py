"""Export an explicit engineering evidence allowlist without altering raw results.

The original runtime remains on the ephemeral runner. Omitted runtime bytes are
hashed locally; this exporter does not claim their durable preservation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

S4 = 'dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
OLD_ROOT = '/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();case=args.case.resolve();out=args.output.resolve()
    root=Path(os.environ['GITHUB_WORKSPACE']).resolve()
    if not case.is_dir() or out.exists() or out.is_relative_to(case):
        raise ValueError('existing raw case and fresh separate export required')
    out.mkdir(parents=True);copied={};projected={};checks={};known_originals=set()

    def normal(value):
        if isinstance(value,str):
            for prefix in (str(root)+'/',OLD_ROOT):
                value=value.replace(prefix,'repository/')
            if re.search(r'(?:/home/|/tmp/|/workspace/|oai-library:|library-file:|libfile_|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})',value):
                raise ValueError('non-engineering locator in projected evidence')
            return value
        if isinstance(value,list):return [normal(x) for x in value]
        if isinstance(value,dict):return {normal(k):normal(v) for k,v in value.items()}
        return value

    def write(rel,value):
        p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(normal(value),indent=2,allow_nan=False)+'\n')

    def source_ref(p):
        return {'sha256':sha(p),'bytes':p.stat().st_size}

    def copy(p,rel=None):
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(case):
            raise ValueError('nonregular or escaping engineering input')
        rel=rel or str(p.relative_to(case));dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dst)
        if sha(p)!=sha(dst):raise ValueError('copied engineering evidence changed')
        copied[rel]=source_ref(p);known_originals.add(p)

    def project(p,rel,data,omitted):
        ref=source_ref(p)
        write(rel,{'schema':'razr-K3-public-engineering-projection-v1',
                   'derived_projection_not_raw_original':True,
                   'original':ref,'original_relative_role':str(p.relative_to(case)),
                   'excluded_runtime_fields':omitted,'engineering_record':data})
        projected[rel]={'original':ref,'excluded_fields':omitted};known_originals.add(p)

    # Exact source files were frozen and checked by the workflow; only these
    # directories contain reviewed source bytes. No logs or arbitrary JSON.
    source=case/'source'
    permitted_static={'host-cap.py','service-launch.py','python-downloads.json','f1/export_f1_engineering.py'}
    k3_names={'f1_common.py','frozen_key_factory_adapter.py','k3_pilot_states.py','k3_pilot_common.py',
              'panel_key_travel_stops_v1.py','independent_stop_checks.py','full_factory_stop_pilot.py',
              'read_stop_pilot.py','supervise_k3.py','K3_K1_BINDING.json','PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json',
              'KEY_FORWARD_LOOP_V1_CONTRACT.json','export_k3_engineering.py','verify_k3_pilot.py'}
    k1_names={'f1_common.py','k1_evidence.py','key_forward_loop_v1.py','KEY_FORWARD_LOOP_V1_CONTRACT.json',
              'full_factory_candidate.py','read_factory_candidate.py','supervise_k1.py','K1_F1A_BINDING.json',
              'export_k1_engineering.py','verify_k1_complete.py'}
    f1_names={'f1_common.py','full_factory_witness.py','read_factory_witness.py',
              'supervise_f1.py','F1_L1_BINDING.json','export_f1_engineering.py'}
    old_names={'integration/probe_key_endpoint_extension.py','tools/key_endpoint_resume.py',
               'run_key_endpoint_trials.py','tests/test_key_endpoint_extension.py','tests/test_key_endpoint_resume.py'}
    s4_before=case/'S4-source-before.json'
    delta={}
    if s4_before.is_file():
        sr=json.loads(s4_before.read_text());delta=sr.get('thirteen_changed_source_sha256',{})
        checks['S4_all_present_tracked_bytes_match_HEAD']=sr.get('all_present_tracked_bytes_match_HEAD')
        project(s4_before,'S4-source-before.engineering.json',{
            k:sr[k] for k in ('schema','source_commit','source_tree','present_source_sha256',
                'all_present_tracked_bytes_match_HEAD','full_checkout_claimed','thirteen_changed_source_sha256') if k in sr},
            sorted(set(sr)-{'schema','source_commit','source_tree','present_source_sha256',
                'all_present_tracked_bytes_match_HEAD','full_checkout_claimed','thirteen_changed_source_sha256'}))
    for p in sorted(source.rglob('*')) if source.is_dir() else []:
        if not p.is_file():continue
        rel=str(p.relative_to(source));allow=rel in permitted_static
        if rel.startswith('k3/'):allow=rel[3:] in k3_names
        elif rel.startswith('k1/'):allow=rel[3:] in k1_names
        elif rel.startswith('f1/'):allow=rel[3:] in f1_names
        elif rel.startswith('original-v4/'):allow=rel[12:] in old_names
        elif rel.startswith('S4-delta/'):
            key=rel[9:];allow=key in delta and sha(p)==delta[key]
        if allow:copy(p)

    geometry_keys={'schema','functional_source_commit','pose','execution_completed','pose_input','status',
       'actual_complete_factory_called','native_scene_metadata','participant_count','nominal_inventory',
       'fixed_pair_certificate_reused','whole_motion_claimed','geometry_repair_applied',
       'native_positive_q_STOP_SPRING_profiles','body_exports','panel_KEY_direct_Common','pairs','positive_pairs',
       'evaluation_failures','mismatches_to_factory','participant_names','expected_pair_count','resource',
       'persisted_pair_count','all_unordered_pairs_present_once','finite_pose_clear','seconds',
       'factory_report_sha256','native_STEP_readback_executed','separate_process_from_factory',
       'independent_CAD_kernel','body_readbacks','L1_binding_sha256','L1_original_input_members_verified',
       'L1_whole_endpoint_material_comparisons','complete_product_motion_proved','continuous_backlash_domain_proved',
       'physical_qualification','candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass'}
    geometry_keys.update({'candidate_name','F1a_prerequisite','original_S4_scene_metadata','candidate_inventory','failure_stage',
       'original_baseline_material_comparisons','baseline_panel_KEY_direct_Common','candidate_application',
       'candidate_material_exports','candidate_contract_sha256','independent_material_builder_does_not_import_candidate_source',
       'candidate_material_readbacks','material_reconstruction'})
    geometry_keys.update({'K1_prerequisite','finite_nominal_endpoint_only','remaining_unproved_domains','candidate_q0_material_comparisons'})
    geometry_keys.update({'pilot_only','pilot_clear','pilot_preconditions_passed','full_ten_state_campaign_authorized',
        'precondition_failures','preliminary_actual_join_measurements','preliminary_candidate_panel_signature',
        'complete_preview_exports_retained','design_contract','candidate_source_sha256','original_K1_inventory',
        'all_nonpanel_participants_retained_unchanged','preview_to_named_candidate_material','endpoint_and_overtravel_checks',
        'all_panel_pairs_present_once','pilot_panel_pairs_clear','panel_pairs_not_evaluated_reason',
        'independent_early_gate_records','independent_native_evaluation_failures','producer_reader_precondition_classification_consistent',
        'original_panel_to_actual_K1_material'})
    controller_keys={'schema','mode','worker_started','completed','owned_child_identity_verified',
       'procfs_visible_PID_used_for_signals','limits','resource_observations','resource_start_refused',
       'worker_exit_code','owned_channel_descriptors_closed','result_sha256','reported_execution_completed',
       'finite_trial_clear','pilot_clear','source_bytes_unchanged','elapsed_seconds','locked_environment_unchanged','capacity_or_wall_stop'}
    for name in ('factory','readback'):
        folder=case/name/'worker';rp=folder/'report.json'
        if rp.is_file():
            r=json.loads(rp.read_text());d={k:r[k] for k in geometry_keys if k in r}
            if 'failure' in r:
                d['original_failure_type']=r['failure'].split(':',1)[0]
                d['original_failure_message_sha256']=hashlib.sha256(r['failure'].encode()).hexdigest()
            if 'original_precondition_failure' in r:
                d['original_precondition_error_type']=r['original_precondition_failure'].split(':',1)[0]
                d['original_precondition_error_sha256']=hashlib.sha256(r['original_precondition_failure'].encode()).hexdigest()
            before=r.get('identity_before',{});after=r.get('identity_after',{})
            d['source_identity_projection']={
               'source_commit_before':before.get('repository_head_at_start'),
               'source_commit_after':after.get('repository_head_at_finish'),
               'worktree_clean_before':before.get('worktree_status_at_start')=='',
               'native_input_roles':before.get('native_input_roles'),
               'available_source_sha256':before.get('available_source_sha256'),
               'executed_source_and_input_sha256':after.get('executed_source_and_input_sha256'),
               'changed_or_late_sources':after.get('changed_or_late_sources'),
               'source_bytes_and_locked_environment_unchanged':after.get('source_bytes_and_locked_environment_unchanged'),
               'locked_environment_before_passed':before.get('environment',{}).get('passed'),
               'locked_environment_after_passed':after.get('environment_after',{}).get('passed'),
               'checked_package_count_before':before.get('environment',{}).get('checked_package_count'),
               'checked_package_count_after':after.get('environment_after',{}).get('checked_package_count')}
            checks[name+'_execution_completed']=r.get('execution_completed')
            checks[name+'_source_environment_unchanged']=after.get('source_bytes_and_locked_environment_unchanged')
            project(rp,f'{name}/worker/report.engineering.json',d,sorted(set(r)-geometry_keys))
            for p in sorted(folder.rglob('*')):
                if p.is_file() and (p.suffix in ('.step','.brep') or p.name=='pairs.jsonl'):copy(p)
        cp=case/name/'controller.json'
        if cp.is_file():
            c=json.loads(cp.read_text());project(cp,f'{name}/controller.engineering.json',
                {k:c[k] for k in controller_keys if k in c},sorted(set(c)-controller_keys))

    # The complete prerequisite is already a frozen engineering-only export.
    # Every member is verified against the independently frozen manifest first.
    for pose in ('near','far'):
        prior=case/('prerequisite-'+pose)
        if not prior.is_dir():continue
        manifest=prior/'ENGINEERING_MANIFEST.json'
        binding_path=case/'source/k3/K3_K1_BINDING.json';driver_ref=case/'K3-driver-source.json'
        if manifest.is_file() and binding_path.is_file() and driver_ref.is_file():
            expected_binding=json.loads(driver_ref.read_text())['K3_K1_BINDING.json']
            if sha(binding_path)!=expected_binding['sha256'] or binding_path.stat().st_size!=expected_binding['bytes']:
                raise ValueError('K1 prerequisite binding changed before export')
            binding=json.loads(binding_path.read_text());entry=binding['poses'][pose]
            if sha(manifest)!=entry['engineering_manifest_sha256']:
                raise ValueError('K1 prerequisite manifest differs before export')
            members=json.loads(manifest.read_text())['members'];missing=0
            for rel,ref in members.items():
                p=prior/rel
                if not p.is_file():missing+=1;continue
                if not p.resolve().is_relative_to(prior.resolve()) or p.is_symlink():
                    raise ValueError('unsafe K1 engineering member')
                if sha(p)!=ref['sha256'] or p.stat().st_size!=ref['bytes']:
                    raise ValueError('K1 engineering member changed before export')
                copy(p)
            copy(manifest);checks[pose+'_prerequisite_original_manifest_verified']=True
            checks[pose+'_prerequisite_missing_manifest_members']=missing
        else:checks[pose+'_prerequisite_export_incomplete']=True

    # L1 inputs have exact original geometry; result projections keep every
    # geometric outcome and material record. Runtime traceback capture stays raw.
    l1=case/'original-L1-inputs'
    for p in sorted(l1.rglob('*')) if l1.is_dir() else []:
        if p.is_file() and p.suffix in ('.step','.brep'):copy(p)
        elif p.is_file() and p.name=='result.json':
            r=json.loads(p.read_text());omit={'trace','started_monotonic'}
            project(p,str(p.relative_to(case)).replace('result.json','result.engineering.json'),
                    {k:v for k,v in r.items() if k not in omit},sorted(omit))

    for name in ('K3-pilot-observation.json','K3-prerequisite-verification.json','K3-driver-source.json'):
        p=case/name
        if p.is_file():
            normal(json.loads(p.read_text()));copy(p)
    # Numeric observer results are admitted; environment and /proc contents are not.
    for label in ('factory-runner','readback-runner','environment-before-check','environment-after-check'):
        p=case/(label+'.namespace')/'SUMMARY.json'
        if p.is_file():
            r=json.loads(p.read_text());m=r.get('manager_result',{})
            data={k:r[k] for k in ('compatibility_verified','cleanup_verified','command_exit_code') if k in r}
            data['manager']={k:m[k] for k in ('cleanup_verified','forced_cleanup','adopted_descendant_cleanup_required','normal_command_completed','host_cap_exit_code') if k in m}
            checks[label+'_cleanup_verified']=r.get('cleanup_verified')
            project(p,f'lifecycle/{label}.engineering.json',data,sorted(set(r)-set(data)))
    for name in ('environment-before.json','environment-after.json'):
        p=case/name
        if p.is_file():
            r=json.loads(p.read_text());checks[name+'_passed']=r.get('passed')
            allowed={'schema','passed','python_version','checked_packages','checked_package_count','pyproject_sha256','uv_lock_sha256','installation_artifact_provenance_verified'}
            project(p,name.replace('.json','.engineering.json'),{k:r[k] for k in allowed if k in r},sorted(set(r)-allowed))
    omitted=[]
    for p in sorted(case.rglob('*')):
        if not p.is_file() or p in known_originals:continue
        if p.is_symlink():raise ValueError('raw evidence symlink rejected')
        rel=str(p.relative_to(case))
        category='runtime_interface_capture' if '/raw/' in rel else 'runtime_log' if p.suffix in ('.log','.stdout','.stderr','.txt','.jsonl') else 'runtime_receipt'
        omitted.append({'category':category,**source_ref(p)})
    write('EXPORT_SCOPE.json',{'schema':'razr-K3-engineering-export-scope-v1','functional_source_commit':S4,
          'raw_producer_reader_reports_modified':False,'all_copied_original_bytes_verified':True,
          'raw_runtime_durable_preservation_claimed':False,'raw_runtime_location':'ephemeral runner only',
          'copied_originals':copied,'derived_projections':projected,'omitted_runtime_file_hashes':omitted,
          'local_runtime_verification_results':checks,
          'scope':'Explicit source, geometric models, every pair/journal and geometric result; runtime interfaces and caller environment omitted.'})
    members={str(p.relative_to(out)):source_ref(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write('ENGINEERING_MANIFEST.json',{'schema':'razr-K3-engineering-export-manifest-v1','members':members})
    print(json.dumps({'export_completed':True,'original_files_copied':len(copied),
        'derived_reports':len(projected),'runtime_files_omitted':len(omitted),'native_claims':checks},sort_keys=True))

if __name__=='__main__':main()
