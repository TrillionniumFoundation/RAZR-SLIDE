"""Prepare explicit small engineering evidence maps; never include array payloads."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parent
SCI=ROOT/'N8-original-scientific'
N9=ROOT/'N9-reconstructed'
OUT=ROOT/'integration'
OUT.mkdir(exist_ok=True)
PREFIX='engineering/engineering-integration-20261026/numerics'
def ident(p):
    b=p.read_bytes()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def row(p,repo):
    b=p.read_bytes()
    return {'repository_path':repo,'local_path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def load(p):return json.loads(p.read_text())
def public_record_check(p):
    # Original records have already passed the frozen exporter; this extra scan
    # is confined to recorded text and excludes synthetic source test fixtures.
    value=p.read_text()
    assert not re.search(r'(?:/home/|/workspace/|/tmp/|/dev/shm/|/proc/[0-9]|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})',value),p.name

r=load(SCI/'probe-N8/N8_REPORT.json');rd=load(SCI/'N8-independent-readback.json')
m=load(SCI/'EXPORT_MANIFEST.json');p=m['scientific_preservation_actual']
runtime=load(SCI/'EXECUTION_CHECKS.engineering.json')['checks']
sup={name:load(SCI/(name+'-supervisor.engineering.json'))['selected_engineering_fields'] for name in ['probe-N8','readback-N8']}
native_ratios=[item['free_dof_residual_infinity_ratio'] for item in r['final']]
assert native_ratios==rd['final_original_ratios']
assert sum(x<=1e-7 for x in native_ratios)==4
assert r['original_five_passed'] is False and rd['original_five_qualification_verified'] is False
assert all(item['resource_stop_reason'] is None and item['supervisor_source_unchanged'] is True for item in sup.values())
assert all(x['compatibility_verified'] is True and x['cleanup_verified'] is True and not x['forced_cleanup'] and not x['adopted_descendant_cleanup_required'] for x in runtime['execution_harness'])
assert all(runtime[name]['passed'] is True and runtime[name]['checked_package_count']==43 for name in ('environment-before.json','environment-after.json'))
assert all(runtime['functional_source_after'][name] is True for name in ('head_equals_S4','git_status_empty','original_five_sources_unchanged'))
actual={'schema':'razr-N8-actual-result-reset-recovery-appendix-v1','source_run_id':40288924586,'source_head_sha':'0f86820367a4444796d9fe9f72b63d324ee5c3c5','source_artifact_id':12634369890,'source_result':'completed numerical qualification rejection','original_threshold':1e-7,'original_all_five_passed':False,'passed_probe_count':4,'final_original_float64_ratios':native_ratios,'probe0_last_accepted_field_sha256':r['final_sequential_base_field_sha256'],'probe0_final_violation_count':r['final'][0]['over_gate_row_count'],'probe0_final_worst_original_DOF':r['final'][0]['max_residual_original_dof'],'chronological_accepted_trials':r['accepted_trial_indices'],'full_candidates_completed':r['full_candidates_completed'],'scalar_screens_retained':r['scalar_screen_count'],'termination':r['termination'],'history_best_selected':r['select_best_history'],'hosted_independent_reader_completed':rd['completed'],'native_float64_gates_independently_checked':rd['native_float64_gate_evaluations'],'direct_exact_product_terms':rd['direct_exact_product_terms'],'frozen_candidate_references_checked':rd['per_candidate_frozen_references_verified'],'producer_elapsed_seconds':r['elapsed_seconds'],'reader_elapsed_seconds':rd['elapsed_seconds'],'resource_stop_reasons':{name:record['resource_stop_reason'] for name,record in sup.items()},'supervisor_exit_codes':{name:record['exit_code'] for name,record in sup.items()},'actual_source_and_environment_checks_passed':True,'all_recorded_harness_compatibility_and_cleanup_checks_passed':True,'source_manifest_actual_preservation':{key:p[key] for key in ('selected_complete_input_identities_verified','all_22_selected_complete_inputs_identity_verified','complete_candidate_arrays_present','complete_per_candidate_frozen_reference_count','all_started_full_candidates_all5_fields_and_residuals_recoverable','final_complete_array_count','all_ten_final_arrays_present','all_actual_allowlisted_array_bytes_copied_and_hash_verified')},'producer_original_record':ident(SCI/'probe-N8/N8_REPORT.json'),'reader_original_record':ident(SCI/'N8-independent-readback.json'),'all_203_original_scalar_records':ident(SCI/'probe-N8/N8_SCALAR_SCREENS.jsonl'),'original_export_manifest':ident(SCI/'EXPORT_MANIFEST.json'),'new_actual_all87_original_byte_recovery_receipt':ident(ROOT/'N8_RECOVERED_ORIGINAL_SCIENTIFIC_READBACK.json'),'source_ZIP_recovered_locally_and_all87_members_verified_again':True,'new_native_N8_rerun':False,'old_RAM_files_recovered':False,'old_unpublished_CP3_claimed_persistent':False,'long_term_archive_current_evidence':'Original Actions artifact and new local verified complete ZIP exist. New draft archive completion requires its own actual receipt; this appendix does not claim it.','H_frame_restore_executed':False,'new_K3_FE_qualification_inferred':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
save(OUT/'N8_ACTUAL_RESET_RECOVERY_APPENDIX.json',actual)

originals=['EXPORT_MANIFEST.json','probe-N8/N8_REPORT.json','probe-N8/N8_SCALAR_SCREENS.jsonl','N8-independent-readback.json','N8-input-transfer.json','N8-small-contracts.json','probe-N8-supervisor.engineering.json','readback-N8-supervisor.engineering.json','EXECUTION_CHECKS.engineering.json']
entries=[]
for name in originals:
    path=SCI/name;public_record_check(path)
    if name!='EXPORT_MANIFEST.json':assert ident(path)==m['exported_files'][name]
    entries.append(row(path,PREFIX+'/n8-actual/'+name))
for path in [ROOT/'N8_RECOVERED_ORIGINAL_SCIENTIFIC_READBACK.json',OUT/'N8_ACTUAL_RESET_RECOVERY_APPENDIX.json',ROOT/'N8-published-source/IMMUTABLE_N8_SOURCE_RECOVERY.json',ROOT/'N8-published-source/IMMUTABLE_N8_WORKFLOW_RECOVERY.json']:
    public_record_check(path);entries.append(row(path,PREFIX+'/recovery/'+path.name))
source=load(ROOT/'N8-published-source/IMMUTABLE_N8_SOURCE_RECOVERY.json')
reused=[{k:x[k] for k in ('path','source_commit','blobsha','bytes')} for x in source['entries']]
workflow_bytes=(ROOT/'N8-published-source/s4-panel-n8-hosted-summary-scope.yml').read_bytes()
reused.append({'path':'.github/workflows/s4-panel-n8-hosted.yml','source_commit':'0f86820367a4444796d9fe9f72b63d324ee5c3c5','blobsha':hashlib.sha1(b'blob '+str(len(workflow_bytes)).encode()+b'\0'+workflow_bytes).hexdigest(),'bytes':len(workflow_bytes)})
n8map={'schema':'razr-small-engineering-integration-map-v1','scope':'N8 original actual records and new reset recovery evidence; no raw runtime or full-array binary payloads','entries':entries,'reused_git':reused,'original_N8_native_rerun':False,'all87_original_byte_recovery_completed':True}
save(OUT/'N8_ACTUAL_RECOVERY_SAFE_MAP.json',n8map)

note={'schema':'razr-N9-new-recovery-review-attempt-note-v1','first_static_review_attempt':'The new review script asserted literal bracket access for scientific_preservation_actual, while the frozen workflow correctly uses manifest.get. That review-only assertion failed.','correction':'Changed only the new review script assertion to the actual frozen manifest.get expression and reran its checks successfully.','frozen_worker_reader_exporter_workflow_modified':False,'native_numeric_execution':False,'old_newline_bug_claimed':False}
save(OUT/'N9_RECOVERY_REVIEW_ATTEMPT_NOTE.json',note)
unavailable={'schema':'razr-pre-reset-unpublished-receipt-availability-appendix-v1','old_runtime_files_recovered':False,'reconstructed_files':'All 13 N9 publish files, historical scalar control/replay, raw tree request and gzip match retained pre-reset expected hashes. New recovery and validation receipts record actual new work separately.','known_original_receipts_not_recovered_as_bytes':[{'name':'N8 all87 pre-reset byte readback','sha256':'0d11bf289bc0b2559705a8017f4095f15609736813acba498870cca77f6cff8d','replacement_evidence':'N8_RECOVERED_ORIGINAL_SCIENTIFIC_READBACK.json is a new actual full byte verification, not the old receipt.'},{'name':'N9_STATIC_REVIEW.json','bytes':7625,'sha256':'81e24ad0b7939914c9ee73f47991b18ddaa87d0318cb4a819f34c0f8d3feed00','replacement_evidence':'N9_RECOVERY_STATIC_REVIEW.json is new actual validation.'},{'name':'N9_PUBLICATION_MANIFEST.json','bytes':3478,'sha256':'33d14afe7e61b968cf65d6578e6a2153b851643daece50c7e67bb631d2b67a5c','replacement_evidence':'Exact recovered source/request identities plus new maps; publication requires a real new Git commit.'}],'pre_reset_historical_replay_elapsed_value':'The 0.031196242009173147 s value appears only in the historical replay and preregistration reconstructed to their original retained hashes. It is not the new recovery timing.','original_numerical_five_passed':False}
save(OUT/'PRE_RESET_RECEIPT_AVAILABILITY_APPENDIX.json',unavailable)
n9files=[N9/'N9_RESET_RECONSTRUCTION_RECEIPT.json',N9/'N9_RECOVERY_SMALL_CONTRACT_RESULTS.json',N9/'N9_RECOVERY_STATIC_REVIEW.json',N9/'S4_IMMUTABLE_API_IDENTITY_RESET_RECOVERY.json',N9/'N9_N8_LAST_STAGE_REPLAY.json',OUT/'N9_RECOVERY_REVIEW_ATTEMPT_NOTE.json',OUT/'PRE_RESET_RECEIPT_AVAILABILITY_APPENDIX.json']
n9entries=[]
for path in n9files:
    public_record_check(path);n9entries.append(row(path,PREFIX+'/n9-recovery/'+path.name))
for path in [ROOT/'reconstruct_n9_frozen.py',ROOT/'validate_recovered_n9.py',ROOT/'build_numerics_recovery_maps.py',ROOT/'recover_original_n8_science.py']:
    n9entries.append(row(path,PREFIX+'/n9-recovery/'+path.name))
save(OUT/'N9_PREPARATION_RECOVERY_SAFE_MAP.json',{'schema':'razr-small-engineering-integration-map-v1','scope':'N9 exact frozen-byte recovery and new validation; old failed N8 remains original failure','entries':n9entries,'published_N9_sources_are_in_separate_frozen_request':True,'new_native_executions':0,'H_frame_restore_executed':False})
request=load(N9/'N9_TREE_REQUEST.json')
source_rows=[row(N9/Path(x['path']).name,x['path']) for x in request['tree_elements']]
save(OUT/'N9_FROZEN_SOURCE_SAFE_MAP.json',{'schema':'razr-small-engineering-integration-map-v1','scope':'exact pre-reset N9 frozen publication request content, source bytes only','entries':source_rows,'base_tree_sha':request['base_tree_sha'],'request_identity':ident(N9/'N9_TREE_REQUEST.json'),'original_pre_reset_bytes_match':True,'publication_performed_by_this_script':False})
print(json.dumps({'N8_entries':len(entries),'N8_bytes':sum(x['bytes'] for x in entries),'N9_preparation_entries':len(n9entries),'N9_preparation_bytes':sum(x['bytes'] for x in n9entries),'N9_frozen_source_entries':len(source_rows),'maps':{p.name:ident(p) for p in sorted(OUT.glob('*MAP.json'))}}))
