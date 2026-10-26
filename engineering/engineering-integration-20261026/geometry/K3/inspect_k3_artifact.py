"""Read actual K3 engineering archives without CAD, preserving three failure classes."""
from __future__ import annotations
import argparse,hashlib,io,json,math,stat,sys,urllib.request,zipfile
from pathlib import Path

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
RUN=40281153812
HEAD='4497cfb9726d26d2b1452008ac23b6b0ec9b6223'
TOL=1e-7
LIMITS={'wall_seconds':1200,'worker_peak_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,
 'runtime_disk_reserve_MiB':100,'startup_disk_reserve_MiB':256,'startup_additional_memory_MiB':2048}
FLAGS=('complete_product_motion_proved','continuous_backlash_domain_proved','physical_qualification',
 'candidate_go','fixture_fabrication_go','manufacturing_go','G2_pass',
 'all_unordered_pairs_present_once','finite_pose_clear','full_ten_state_campaign_authorized')

def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,why):
 if not ok:raise ValueError(why)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--k1-binding',type=Path,required=True)
 a=ap.parse_args();request=json.load(sys.stdin);meta=request['artifact'];pose=request['pose']
 plan=json.loads(a.plan.read_text());binding=json.loads(a.k1_binding.read_text())
 require(pose in ('stow_tabs_3','predock') and meta['name']==f'S4-K3-{pose}-{RUN}-1-engineering','actual K3 artifact identity differs')
 if 'workflow_run' in meta:require(meta['workflow_run']['id']==RUN and meta['workflow_run']['head_sha']==HEAD,'official actual K3 run differs')
 require(meta['size_in_bytes']<64*2**20,'unexpected engineering ZIP size')
 with urllib.request.urlopen(request['file_uri'],timeout=90) as stream:data=stream.read(meta['size_in_bytes']+1)
 require(len(data)==meta['size_in_bytes'] and 'sha256:'+sha(data)==meta['digest'],'official ZIP SHA/length differs')
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  infos=z.infolist();names=[x.filename for x in infos]
  require(len(names)==len(set(names)) and all(not x.is_dir() and not stat.S_ISLNK(x.external_attr>>16) for x in infos),'unsafe ZIP entries')
  require(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names),'unsafe ZIP paths')
  mb=z.read('ENGINEERING_MANIFEST.json');manifest=json.loads(mb)
  require(manifest['schema']=='razr-K3-engineering-export-manifest-v1','K3 manifest type differs')
  members=manifest['members'];require(set(names)==set(members)|{'ENGINEERING_MANIFEST.json'},'ZIP exact member set differs')
  for rel,ref in members.items():
   b=z.read(rel);require(len(b)==ref['bytes'] and sha(b)==ref['sha256'],'engineering original SHA differs: '+rel)
  for name,ref in plan['sources'].items():
   rel='source/k3/'+name;require(members.get(rel)==ref,'frozen runtime source differs: '+name)
  require(z.read('source/k3/K3_K1_BINDING.json')==a.k1_binding.read_bytes(),'actual K1 prerequisite binding bytes differ')
  prerequisites={}
  for prior in ('near','far'):
   prefix='prerequisite-'+prior+'/'
   prior_bytes=z.read(prefix+'ENGINEERING_MANIFEST.json')
   require(sha(prior_bytes)==binding['poses'][prior]['engineering_manifest_sha256'],'actual prerequisite manifest differs')
   old=json.loads(prior_bytes)['members']
   require(all(members.get(prefix+rel)==ref for rel,ref in old.items()),'complete actual K1 prerequisite missing or changed')
   prerequisites[prior]={'engineering_manifest_sha256':sha(prior_bytes),'all_prior_engineering_members_retained':len(old)}
  results={};reports={};wrappers={};controllers={}
  for mode in ('factory','readback'):
   rel=f'{mode}/worker/report.engineering.json'
   if rel not in names:
    results[mode]={'report_present':False,'scientific_complete':False,'pilot_clear_claimed':False};continue
   w=json.loads(z.read(rel));wrappers[mode]=w;r=w['engineering_record'];reports[mode]=r
   require(w['derived_projection_not_raw_original'] is True and r['functional_source_commit']==S4
    and r['candidate_name']=='panel_key_travel_stops_v1' and r['pose']==pose,'marked K3 projection identity differs')
   require(all(r[x] is False for x in FLAGS),'pilot improperly grants full-matrix/domain/physical release')
   require(r['candidate_source_sha256']==plan['candidate_source_sha256']
    and r['candidate_contract_sha256']==plan['sources']['PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json']['sha256'],'candidate source/contract differs')
   expected=dict(plan['pilot_states'][pose]);expected.pop('expected_bodies')
   expected.update(flanks=[0.,0.],key_offsets=[0.,0.],crosshead_offsets=[0.,0.],telescope_offsets=None)
   require(r['pose_input']==expected,'actual pilot input differs')
   names_part=r.get('participant_names',[])
   require(len(names_part)==len(set(names_part))==154,'full actual pilot body inventory differs')
   ident=r.get('source_identity_projection',{})
   audited=(ident.get('source_commit_before')==ident.get('source_commit_after')==S4
    and ident.get('worktree_clean_before') is True and ident.get('source_bytes_and_locked_environment_unchanged') is True
    and ident.get('locked_environment_before_passed') is True and ident.get('locked_environment_after_passed') is True
    and ident.get('checked_package_count_before')==ident.get('checked_package_count_after')==43)
   cp=f'{mode}/controller.engineering.json';c=json.loads(z.read(cp))['engineering_record'] if cp in names else {}
   controllers[mode]=c
   supervised=(c.get('completed') is True and c.get('worker_exit_code')==0 and c.get('limits')==LIMITS
    and all(c.get(k) is True for k in ('owned_child_identity_verified','source_bytes_unchanged','locked_environment_unchanged','owned_channel_descriptors_closed'))
    and c.get('result_sha256')==w['original']['sha256'])
   pairs=r.get('pairs',[]);expected_pairs=[('A_BACK_PANEL',n) for n in sorted(names_part) if n!='A_BACK_PANEL']
   if r.get('all_panel_pairs_present_once'):
    require([(x['a'],x['b']) for x in pairs]==expected_pairs and len(pairs)==153,'complete changed-panel subset differs')
    journal=[json.loads(x) for x in z.read(f'{mode}/worker/pairs.jsonl').decode().splitlines()]
    require(len(journal)==306 and [x['row'] for x in journal if x['event']=='completed']==pairs,'panel pair journal differs')
   else:
    require(not pairs and r['pilot_clear'] is False,'uncomputed changed-panel pairs presented as clearance');journal=[]
   for row in pairs:
    if not row.get('evaluation_failed'):
     v=row['common_mm3'];require(type(v) in (float,int) and math.isfinite(v) and v>=0 and row['rejected']==(v>TOL),'invalid original Common predicate')
     if v>0:
      for ref in row['positive_Common_export']['files'].values():
       require(members.get(f'{mode}/worker/'+ref['path'])=={k:ref[k] for k in ('sha256','bytes')},'positive Common original missing')
   if mode=='factory':
    require(r.get('actual_complete_factory_called') is True and r.get('complete_preview_exports_retained') is True
      and len(r['body_exports'])==154,'actual complete factory preview absent')
    for entry in r['body_exports'].values():
     for ref in entry['files'].values():
      require(members.get('factory/worker/'+ref['path'])=={k:ref[k] for k in ('sha256','bytes')},'whole factory material original missing')
   else:
    require(r.get('native_STEP_readback_executed') is True and r.get('separate_process_from_factory') is True
     and r.get('independent_CAD_kernel') is False and r.get('independent_material_builder_does_not_import_candidate_source') is True,'reader independence scope differs')
    require(len(r['body_readbacks'])==154 and all(x['passed'] for x in r['body_readbacks'].values()),'complete STEP readback differs')
    require(set(r['original_panel_to_actual_K1_material'])=={'near','far'}
     and all(0<=v<=TOL for row in r['original_panel_to_actual_K1_material'].values() for v in row.values()),'old whole panel differs from actual K1')
    require(set(r['candidate_q0_material_comparisons'])=={'L','R'}
     and all(0<=v<=TOL for row in r['candidate_q0_material_comparisons'].values() for v in row.values()),'complete actual K1 KEYs differ')
   results[mode]={'report_present':True,'original_report_sha256':w['original']['sha256'],'projection_sha256':sha(z.read(rel)),
    'source_and_43_package_environment_audited':audited,'owned_original_resource_guards_completed':supervised,
    'scientific_complete':r.get('execution_completed') is True and audited and supervised,
    'original_status':r.get('status'),'pilot_clear_claimed':r.get('pilot_clear') is True,
    'pilot_preconditions_passed':r.get('pilot_preconditions_passed') is True,'seconds':r.get('seconds'),
    'changed_panel_pair_count':len(pairs),'journal_rows':len(journal),
    'all_panel_pairs_present_once':r.get('all_panel_pairs_present_once',False),
    'positive_panel_pairs':r.get('positive_pairs',[]),'pair_evaluation_failures':r.get('evaluation_failures',[]),
    'pair_readback_mismatches':r.get('mismatches_to_factory',[]),
    'producer_precondition_failures':r.get('precondition_failures',[])}
  reader=reports.get('readback',{});producer=reports.get('factory',{});gates=reader.get('independent_early_gate_records',{})
  require(not gates or len(gates)==18,'independent early-gate inventory incomplete')
  geometry_rejections={k:v for k,v in gates.items() if v.get('evaluated') is True and v.get('passed') is False}
  unresolved={k:v for k,v in gates.items() if v.get('evaluated') is not True}
  missing_early_gate_inventory=len(gates)!=18
  consistency=reader.get('producer_reader_precondition_classification_consistent')
  disagreement=consistency is False
  if reader:
   require(reader['factory_report_sha256']==wrappers['factory']['original']['sha256'],'reader bound to different producer original')
   require(reader['pilot_preconditions_passed']==all(x['evaluated'] and x['passed'] for x in gates.values()),'reader gate aggregate differs')
   require(consistency==(reader['pilot_preconditions_passed']==producer['pilot_preconditions_passed']),'classification-consistency record differs')
   if producer.get('all_panel_pairs_present_once'):
    old={(x['a'],x['b']):x for x in producer['pairs']}
    for row in reader['pairs']:
     previous=old[(row['a'],row['b'])]
     if not row.get('evaluation_failed') and not previous.get('evaluation_failed'):
      require(abs(row['common_mm3']-previous['common_mm3'])<=TOL and row['rejected']==previous['rejected'],'actual panel-pair readback mismatch')
  pair_rejections={mode:[row for row in result.get('positive_panel_pairs',[]) if row['rejected']] for mode,result in results.items()}
  complete=len(results)==2 and all(x.get('scientific_complete') for x in results.values())
  independently_clear=bool(complete and not missing_early_gate_inventory and not geometry_rejections and not unresolved
   and consistency is True and all(x.get('pilot_clear_claimed') and x.get('pilot_preconditions_passed') and x.get('all_panel_pairs_present_once')
    and not x['pair_evaluation_failures'] and not x['pair_readback_mismatches'] and not pair_rejections[m] for m,x in results.items()))
  if complete:
   require(all(x['pilot_clear_claimed']==independently_clear for x in results.values()) or disagreement,
    'claimed pilot clearance differs from independently classified actual records')
  scope_bytes=z.read('EXPORT_SCOPE.json');scope=json.loads(scope_bytes)
  require(scope['schema']=='razr-K3-engineering-export-scope-v1' and scope['raw_producer_reader_reports_modified'] is False
   and scope['all_copied_original_bytes_verified'] is True and scope['raw_runtime_durable_preservation_claimed'] is False,'unsafe K3 export scope')
  require(all(members.get(k)==v for k,v in scope['copied_originals'].items()),'copied original accounting differs')
  require(all(set(row)=={'category','bytes','sha256'} for row in scope['omitted_runtime_file_hashes']),'omitted runtime field exposure')
  summary={'schema':'razr-K3-memory-artifact-scientific-inspection-v1','pose':pose,'run_id':RUN,'head_sha':HEAD,
   'artifact_id':meta['id'],'artifact_name':meta['name'],'artifact_expires_at':meta['expires_at'],
   'official_ZIP_sha256':sha(data),'official_ZIP_bytes':len(data),'engineering_manifest_sha256':sha(mb),
   'exact_engineering_manifest_entries':len(members),'exact_ZIP_regular_file_count':len(names),
   'official_ZIP_SHA_size_all_CRC_and_member_SHA_verified':True,'fourteen_frozen_runtime_source_bytes_verified':True,
   'complete_K1_prerequisites':prerequisites,'results':results,'controllers':controllers,
   'independent_early_gate_records':gates,'evaluated_geometric_gate_rejections':geometry_rejections,
   'native_evaluation_unresolved':unresolved,'missing_independent_early_gate_inventory':missing_early_gate_inventory,
   'producer_reader_classification_disagreement':disagreement,'classification_consistency_known':type(consistency) is bool,
   'positive_rejected_panel_pairs':pair_rejections,'complete_diagnostic_execution':complete,
   'actual_finite_pilot_clear':independently_clear,'subsequent_ten_state_campaign_allowed_by_this_inspection':False,
   'original_complete_panel_material_account':producer.get('candidate_application',{}).get('actual_added_only_panel_account'),
   'original_preliminary_positive_join_measurements':producer.get('preliminary_actual_join_measurements'),
   'candidate_source_sha256':plan['candidate_source_sha256'],'candidate_contract_sha256':plan['sources']['PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json']['sha256'],
   'local_new_CAD_execution_claimed':False,'raw_runtime_reconstructed':False,'raw_runtime_durable_preservation_claimed':False,
   'complete_scientific_ZIP_saved_locally':False,'complete_product_motion_proved':False,'physical_allowed_domain_proved':False,
   'global_minimum_wall_measured':False,'strength_qualified':False,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
  a.output.mkdir(parents=True,exist_ok=True)
  (a.output/f'K3_{pose}_ENGINEERING_MANIFEST.json').write_bytes(mb)
  (a.output/f'K3_{pose}_INSPECTION.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
  if 'K3-pilot-observation.json' in names:
   (a.output/f'K3_{pose}_PILOT_OBSERVATION.json').write_bytes(z.read('K3-pilot-observation.json'))
  projection={k:scope[k] for k in ('schema','functional_source_commit','raw_producer_reader_reports_modified',
   'all_copied_original_bytes_verified','raw_runtime_durable_preservation_claimed','raw_runtime_location',
   'local_runtime_verification_results','scope')}
  projection.update(derived_projection_not_raw_original=True,original_sha256=sha(scope_bytes),original_bytes=len(scope_bytes),
   root_keys=sorted(scope),copied_original_count=len(scope['copied_originals']),derived_projection_count=len(scope['derived_projections']),
   omitted_runtime_file_count=len(scope['omitted_runtime_file_hashes']),copied_originals_exactly_match_manifest=True,
   omitted_records_have_only_category_size_sha256=True)
  (a.output/f'K3_{pose}_EXPORT_SCOPE_PROJECTION.json').write_text(json.dumps(projection,indent=2)+'\n')
  print(json.dumps({k:summary[k] for k in ('pose','artifact_id','official_ZIP_sha256','official_ZIP_bytes','engineering_manifest_sha256',
   'exact_engineering_manifest_entries','exact_ZIP_regular_file_count','complete_diagnostic_execution','actual_finite_pilot_clear',
   'evaluated_geometric_gate_rejections','native_evaluation_unresolved','producer_reader_classification_disagreement','positive_rejected_panel_pairs')},indent=2),flush=True)

if __name__=='__main__':main()
