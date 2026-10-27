"""K4 engineering allowlist export; original records remain byte-identical.

Private process/environment interfaces and raw exception messages stay on the
ephemeral runner. Their byte identities and numeric local verification results
are retained without publishing raw paths or claiming durable raw preservation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

MAX_OUTPUT=384*2**20
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
PRIVATE=re.compile(r'(?:/(?:home|tmp|workspace|proc|sys|dev/shm)/|file://|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[?&](?:sig|signature|token)=)',re.I)
SOURCE_NAMES=('f1_common.py','service-launch.py','host-cap.py','python-downloads.json',
    'k4_local_section_native_api.py','k4_worker.py','supervise_k4.py','prepare_k4_input.py',
    'verify_k4_complete.py','export_k4_engineering.py','K4_LOCAL_SECTION_PILOT_SPEC.json',
    'K4_INPUT_BINDING.json','K4_HOSTED_CAPACITY_CONTRACT.json','K4_FROZEN_SOURCES.json',
    'key_forward_loop_v1.py','KEY_FORWARD_LOOP_V1_CONTRACT.json',
    'panel_key_travel_stops_v1.py','PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def ref(path):return {'sha256':sha(path),'bytes':Path(path).stat().st_size}


def safe(value):
    if isinstance(value,str):
        if PRIVATE.search(value):raise ValueError('private runtime locator or identity in engineering data')
    elif isinstance(value,dict):
        for k,v in value.items():safe(k);safe(v)
    elif isinstance(value,(list,tuple)):
        for v in value:safe(v)


def export(case,sources,out,repository):
    case=case.resolve();sources=sources.resolve();out=out.resolve();repository=repository.resolve()
    if out.exists() or out.is_relative_to(case):raise ValueError('fresh separate engineering directory required')
    out.mkdir(parents=True);known=set();copied=[];projections=[];problems=[];written=0
    def write(rel,data):
        nonlocal written
        p=out/rel
        if p.exists() or not p.resolve().is_relative_to(out):raise ValueError('new safe export path required')
        raw=data if isinstance(data,bytes) else (json.dumps(data,indent=2,allow_nan=False)+'\n').encode()
        if written+len(raw)>MAX_OUTPUT:raise ValueError('registered engineering export byte bound reached')
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);written+=len(raw)
        return p
    def copy(p,rel,kind):
        nonlocal written
        if p.is_symlink() or not p.is_file():raise ValueError('regular original required')
        if written+p.stat().st_size>MAX_OUTPUT:raise ValueError('registered engineering export byte bound reached')
        target=out/rel
        if target.exists() or not target.resolve().is_relative_to(out):raise ValueError('fresh safe export destination required')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        before,after=ref(p),ref(target)
        if before!=after:raise ValueError('original scientific bytes changed while copying')
        written+=before['bytes'];known.add(p)
        copied.append({'exported_path':rel,'category':kind,**before,'original_bytes_unchanged':True})
    def project(p,rel,value,category):
        safe(value);original=ref(p)
        wrapped={'schema':'razr-K4-engineering-derived-projection-v1','derived_projection_not_raw_original':True,
            'original':original,'source_category':category,'engineering_record':value}
        write(rel,wrapped);known.add(p);projections.append({'exported_path':rel,'source_category':category,'original':original})
    def admit_json(p,rel,kind,jsonl=False):
        try:
            if jsonl:
                for line in p.read_text().splitlines():safe(json.loads(line))
            else:safe(json.loads(p.read_text()))
            copy(p,rel,kind)
        except (ValueError,UnicodeError,json.JSONDecodeError):
            problems.append({'category':kind,**ref(p),'reason':'scientific_record_not_exported_due_to_invalid_or_private_data'})
    bundle_path=sources/'K4_FROZEN_SOURCES.json'
    bundle=json.loads(bundle_path.read_text()) if bundle_path.is_file() else None
    for name in SOURCE_NAMES:
        p=sources/name
        if p.is_file():
            if bundle and name in bundle['runtime_sources'] and ref(p)!=bundle['runtime_sources'][name]:
                problems.append({'category':'frozen_source',**ref(p),'reason':'source_bytes_differ_from_frozen_bundle'});continue
            copy(p,'source/K4/'+name,'reviewed_frozen_source')
    if bundle:
        for rel,expected in bundle['immutable_S4_helpers'].items():
            p=repository/rel
            if p.is_file() and not p.is_symlink() and sha(p)==expected:copy(p,'source/immutable-S4/'+rel,'immutable_S4_actual_helper_source')
            else:problems.append({'category':'immutable_S4_helper','repository_path':rel,'reason':'absent_or_source_SHA_mismatch'})
    inputs=case/'inputs'
    if inputs.is_dir():
        for name in ('K3FULL_ENGINEERING_MANIFEST.json','K3FULL-complete-observation.json','K4-input-verification.json'):
            p=inputs/name
            if p.is_file():admit_json(p,'inputs/'+name,'original_input_identity_or_verification')
        for name in ('A_BACK_PANEL.step','L_KEY.step','R_KEY.step'):
            p=inputs/'whole_STEP'/name
            if p.is_file():copy(p,'inputs/whole_STEP/'+name,'complete_original_current_whole_STEP')
    for name in ('K4-input-acquisition.json','K4-complete-observation.json','K4-driver-source.json','K4-hosted-source-contract.json'):
        p=case/name
        if p.is_file():admit_json(p,name,'local_engineering_observation')
    checks={}
    for mode in ('producer','readback'):
        worker=case/mode/'worker'
        if worker.is_dir():
            for p in sorted(worker.iterdir()):
                if p.is_file() and not p.is_symlink() and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:brep|step)',p.name):
                    # STEP headers may carry author/runtime names. Preserve a
                    # rejected original by identity rather than modify its bytes.
                    header=p.open('rb').read(8192).decode('utf-8',errors='replace')
                    if PRIVATE.search(header):problems.append({'category':'native_geometry',**ref(p),'reason':'private_header_in_native_original'});continue
                    copy(p,mode+'/worker/'+p.name,'complete_native_geometry_including_failed_or_partial_result')
                elif p.name in ('report.json','journal.jsonl') and p.is_file():admit_json(p,mode+'/worker/'+p.name,'original_native_report_or_full_operation_journal',p.suffix=='.jsonl')
        cp=case/mode/'controller.json'
        if cp.is_file():
            c=json.loads(cp.read_text());keys=('schema','mode','started_utc','finished_utc','worker_started','completed',
                'worker_exit_code','reported_execution_completed','local_material_targets_all_matched','all_probes_evaluated',
                'owned_child_identity_verified','owned_channel_descriptors_closed','procfs_visible_PID_used_for_signals',
                'source_bytes_unchanged','locked_environment_unchanged','limits','additional_output_limits',
                'resource_start_refused','capacity_or_wall_stop','elapsed_seconds','result_sha256','resource_observations')
            value={k:c[k] for k in keys if k in c}
            if 'failure' in c:
                raw=c['failure'].encode();value['private_failure']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            checks[mode+'_controller_completed']=c.get('completed') is True
            project(cp,mode+'/controller.engineering.json',value,'owned_controller_numeric_outcome')
        rp=case/mode/'worker-runtime.json'
        if rp.is_file():
            r=json.loads(rp.read_text());a=r.get('identity_after',{});b=r.get('identity_before',{});executed={}
            for raw,digest in a.get('executed_source_and_input_sha256',{}).items():
                path=Path(raw)
                if path.is_relative_to(repository):executed[str(path.relative_to(repository))]=digest
            value={'mode':mode,'worker_source_sha256':r.get('worker_source_sha256'),'API_source_sha256':r.get('API_source_sha256'),
                'handshake_returned_after_parent_verification':r.get('handshake_returned_after_parent_verification'),
                'separate_from_producer_process_verified':r.get('separate_from_producer_process_verified'),
                'source_bytes_and_locked_environment_unchanged':a.get('source_bytes_and_locked_environment_unchanged'),
                'source_checkout_still_clean':r.get('source_checkout_still_clean'),'input_bytes_unchanged':r.get('input_bytes_unchanged'),
                'own_process_identity_unchanged':r.get('own_process_identity_unchanged'),'resource_after':r.get('resource_after'),
                'repository_head_at_start':b.get('repository_head_at_start'),'repository_head_at_finish':a.get('repository_head_at_finish'),
                'executed_immutable_repository_source_sha256':executed,'elapsed_seconds':r.get('elapsed_seconds')}
            for label,env in [('before',b.get('environment',{})),('after',a.get('environment_after',{}))]:
                allowed=('schema','passed','python_version','checked_packages','checked_package_count','pyproject_sha256','uv_lock_sha256','installation_artifact_provenance_verified')
                value['locked_environment_'+label]={k:env[k] for k in allowed if k in env}
            project(rp,mode+'/source_identity.engineering.json',value,'actual_source_environment_process_local_verification')
    for label in ('producer-runner','readback-runner','environment-before-check','environment-after-check'):
        p=case/(label+'.namespace')/'SUMMARY.json'
        if p.is_file():
            r=json.loads(p.read_text());m=r.get('manager_result',{})
            value={k:r[k] for k in ('compatibility_verified','cleanup_verified','command_exit_code') if k in r}
            value['manager']={k:m[k] for k in ('cleanup_verified','forced_cleanup','adopted_descendant_cleanup_required','normal_command_completed','host_cap_exit_code') if k in m}
            checks[label+'_cleanup_verified']=r.get('cleanup_verified')
            project(p,'lifecycle/'+label+'.engineering.json',value,'original_lifecycle_local_verification')
    for name in ('environment-before.json','environment-after.json'):
        p=case/name
        if p.is_file():
            r=json.loads(p.read_text());keys=('schema','passed','python_version','checked_packages','checked_package_count','pyproject_sha256','uv_lock_sha256','installation_artifact_provenance_verified')
            checks[name+'_passed']=r.get('passed') is True
            project(p,name.replace('.json','.engineering.json'),{k:r[k] for k in keys if k in r},'locked_environment_local_verification')
    for name in ('S4-source-before.json','S4-source-after.json','source-after.json'):
        p=case/name
        if p.is_file():
            r=json.loads(p.read_text());value={k:r[k] for k in ('source_commit','source_tree','all_present_tracked_bytes_match_HEAD','all_present_source_bytes_unchanged','original_five_sources_unchanged') if k in r}
            if 'head' in r:value['head_is_expected_immutable_S4']=r['head'].get('exit_code')==0 and r['head'].get('stdout','').strip()==S4
            if 'status' in r:value['worktree_is_clean']=r['status'].get('exit_code')==0 and not r['status'].get('stdout','').strip()
            project(p,name.replace('.json','.engineering.json'),value,'immutable_source_byte_verification')
    omitted=[]
    for p in sorted(case.rglob('*')):
        if not p.is_file() or p in known:continue
        if p.is_symlink():raise ValueError('raw evidence symlink prohibited')
        rel=str(p.relative_to(case))
        category='frozen_scientific_input_archive_not_republished' if p.name=='original-K3FULL-stow3.zip' else 'private_runtime_interface_capture' if '/raw/' in rel else 'private_runtime_exception' if 'error' in p.name else 'private_runtime_or_partial_record'
        omitted.append({'ordinal':len(omitted),'category':category,**ref(p)})
    scope={'schema':'razr-K4-engineering-export-scope-v1','functional_source_commit':S4,
        'raw_producer_reader_reports_modified':False,'all_copied_original_bytes_verified':True,
        'raw_runtime_exported':False,'raw_runtime_durable_preservation_claimed':False,'raw_runtime_location':'ephemeral runner only',
        'copied_originals':copied,'derived_projections':projections,'omitted_runtime_or_input_file_hashes':omitted,
        'local_runtime_verification_results':checks,'scientific_export_problems':problems,
        'available_allowed_scientific_originals_preserved':not problems,
        'global_minimum_wall_qualified':False,'complete_continuous_motion_proved':False,'physical_allowed_domain_proved':False,
        'strength_qualified':False,'candidate_go':False,'scope':'Bounded local K4 sections and independent readback; original errors and unresolved outcomes remain evidence.'}
    safe(scope);write('EXPORT_SCOPE.json',scope)
    members={str(p.relative_to(out)):ref(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write('ENGINEERING_MANIFEST.json',{'schema':'razr-K4-engineering-export-manifest-v1','members':members})
    print(json.dumps({'export_completed':True,'scientific_export_problems':len(problems),'engineering_bytes':written,'members':len(members),'raw_runtime_exported':False}))
    return 0 if not problems else 2


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',type=Path,required=True);ap.add_argument('--sources',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--repository',type=Path,required=True);a=ap.parse_args()
    return export(a.case,a.sources,a.output,a.repository)


if __name__=='__main__':raise SystemExit(main())
