"""Freeze ten actual full factories with unchanged finite gates after K3 pilots."""
from __future__ import annotations
import argparse,ast,hashlib,json,re,subprocess
from pathlib import Path
import yaml
from full_stop_states import STATES,EXPECTED_CONTACT_ENDS
from verify_embedded_python import inspect as inspect_embedded_python

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560';TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
FILES=('f1_common.py','frozen_key_factory_adapter.py','actual_stop_prerequisite.py','full_stop_states.py','k3_pilot_common.py',
 'panel_key_travel_stops_v1.py','independent_stop_checks.py','full_factory_stops.py','read_factory_stops.py',
 'supervise_k3full.py','K3FULL_K3_BINDING.json','K3FULL_K1_BINDING.json','PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json',
 'KEY_FORWARD_LOOP_V1_CONTRACT.json','export_k3full_engineering.py','verify_k3full_complete.py')

def sha(b):return hashlib.sha256(b).hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base-workflow',type=Path,required=True);a=ap.parse_args()
 sources={name:(HERE/name).read_text() for name in FILES}
 for n,s in sources.items():
  if n.endswith('.py'):ast.parse(s,filename=n)
 binding=json.loads(sources['K3FULL_K3_BINDING.json']);contract=json.loads(sources['PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'])
 assert binding['actual_two_complete_pilots_reviewed_clear'] is True and binding['run_id']==40281153812
 assert binding['head_sha']=='4497cfb9726d26d2b1452008ac23b6b0ec9b6223'
 assert sha(sources['panel_key_travel_stops_v1.py'].encode())==contract['candidate_source_sha256']==binding['candidate_source_sha256']
 assert sha(sources['PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'].encode())==binding['contract_sha256']
 assert sha(sources['K3FULL_K1_BINDING.json'].encode())==binding['original_K1_binding_sha256']
 assert len(STATES)==10 and sum(v['expected_bodies']*(v['expected_bodies']-1) for v in STATES.values())==237818
 for pose in ('stow_tabs_3','predock'):
  old=binding['poses'][pose];assert old['actual_finite_pilot_clear'] and old['all_early_native_gates_evaluated_and_passed']
  assert not old['evaluated_geometric_gate_rejections'] and not old['native_evaluation_unresolved'] and not old['producer_reader_classification_disagreement']
 w=yaml.safe_load(a.base_workflow.read_text());w['name']='K3FULL ten complete factories and independent full-pair STEP readers'
 w['on']={'push':{'branches':['diagnostic/s4-panel-key-stop-k3full-20261026']},'workflow_dispatch':None}
 w['concurrency']={'group':'k3full-${{ github.ref }}','cancel-in-progress':False}
 job=w['jobs'].pop('pilot');w['jobs']={'full':job}
 job['name']='K3FULL fresh complete factory and every STEP pair: ${{ matrix.pose }}'
 job['strategy']['matrix']={'pose':list(STATES)};assert job['strategy']['max-parallel']==2
 steps=job['steps'];steps[0]['run']=steps[0]['run'].replace('razr-s4-panel-key-stop-k3-20261026','razr-s4-panel-key-stop-k3full-20261026')
 prefix=steps[2]['run'].split('mkdir -p "$HOST_ROOT/k3" "$CASE_DIR/source/k3"\n',1)
 assert len(prefix)==2 and TREE in prefix[0]
 block=prefix[0]+'mkdir -p "$HOST_ROOT/k3full" "$CASE_DIR/source/k3full"\n';expected={}
 for name,s in sources.items():
  marker='K3FULL_SOURCE_'+re.sub('[^A-Z0-9]','_',name.upper());assert marker not in s and s.endswith('\n')
  block+=f'cat > "$HOST_ROOT/k3full/{name}" <<\'{marker}\'\n'+s+marker+'\n'
  block+=f'cp "$HOST_ROOT/k3full/{name}" "$CASE_DIR/source/k3full/{name}"\n'
  expected[name]={'sha256':sha(s.encode()),'bytes':len(s.encode())}
 block+='python3 -B - <<\'K3FULL_SOURCE_BIND\'\nimport hashlib,json,os,pathlib\np=pathlib.Path(os.environ[\'HOST_ROOT\'])/\'k3full\'\nexpected='+repr(expected)+'\n'
 block+='for name,r in expected.items():\n data=(p/name).read_bytes();assert len(data)==r[\'bytes\'] and hashlib.sha256(data).hexdigest()==r[\'sha256\']\n'
 block+='(pathlib.Path(os.environ[\'CASE_DIR\'])/\'K3FULL-driver-source.json\').write_text(json.dumps(expected,indent=2)+\'\\n\')\nK3FULL_SOURCE_BIND\n'
 steps[2]['name']='Bind immutable S4 and exact complete-campaign sources with original lifecycle guards';steps[2]['run']=block
 for step,pose in zip(steps[6:8],('stow_tabs_3','predock')):
  step['name']='Download actual reviewed K3 '+pose+' complete engineering artifact'
  step['with']={'artifact-ids':str(binding['poses'][pose]['artifact_id']),'run-id':str(binding['run_id']),
   'repository':'TrillionniumFoundation/RAZR-SLIDE','github-token':'${{ github.token }}','merge-multiple':True,
   'path':'${{ runner.temp }}/razr-s4-panel-key-stop-k3full-20261026/K3-download/'+pose}
 steps[8]={'name':'Verify both actual clear K3 originals and stricter input-copy capacity preflight','shell':'bash','run':'''set -euo pipefail
python3 -B - <<'K3FULL_PREREQUISITE'
import hashlib,json,os,pathlib,shutil
host=pathlib.Path(os.environ['HOST_ROOT']);case=pathlib.Path(os.environ['CASE_DIR'])
binding=json.loads((host/'k3full/K3FULL_K3_BINDING.json').read_text());assert binding['actual_two_complete_pilots_reviewed_clear'] is True
v=os.statvfs(case);available=v.f_bavail*v.f_frsize
capacity={'ordinary_available_bytes_before_second_copy':available,'additional_input_and_export_reserve_bytes':1536*2**20,'observed_actual_two_input_unpacked_bytes':408408534,'original_native_startup_256MiB_runtime_100MiB_guards_unchanged':True}
(case/'K3FULL-input-capacity.json').write_text(json.dumps(capacity,indent=2)+chr(10))
assert available>=1536*2**20,'extra input/export ordinary disk reserve unavailable; original native gate is not relaxed'
observed={}
for pose in ('stow_tabs_3','predock'):
 src=host/'K3-download'/pose;manifest=src/'ENGINEERING_MANIFEST.json';raw=manifest.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==binding['poses'][pose]['engineering_manifest_sha256']
 m=json.loads(raw);assert m['schema']=='razr-K3-engineering-export-manifest-v1';members=m['members']
 assert {str(p.relative_to(src)) for p in src.rglob('*') if p.is_file()}==set(members)|{'ENGINEERING_MANIFEST.json'}
 dest=case/('prerequisite-'+pose);dest.mkdir()
 for rel,ref in members.items():
  p=(src/rel).resolve();assert p.is_relative_to(src.resolve()) and p.is_file() and not p.is_symlink()
  data=p.read_bytes();assert len(data)==ref['bytes'] and hashlib.sha256(data).hexdigest()==ref['sha256']
  target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 shutil.copyfile(manifest,dest/'ENGINEERING_MANIFEST.json')
 for mode in ('factory','readback'):
  wrapper=json.loads((dest/mode/'worker/report.engineering.json').read_text());assert wrapper['derived_projection_not_raw_original'] is True
  r=wrapper['engineering_record'];assert r['execution_completed'] is True and r['pilot_clear'] is True and r['pilot_preconditions_passed'] is True
  assert len(r['participant_names'])==154 and len(r['pairs'])==153 and not r['evaluation_failures'] and not r['mismatches_to_factory']
  assert wrapper['original']['sha256']==binding['poses'][pose]['original_report_sha256'][mode]
  if mode=='readback':
   assert len(r['independent_early_gate_records'])==18 and all(x['evaluated'] is True and x['passed'] is True for x in r['independent_early_gate_records'].values())
   assert not r['independent_native_evaluation_failures'] and r['producer_reader_precondition_classification_consistent'] is True
 observed[pose]={'manifest_sha256':hashlib.sha256(raw).hexdigest(),'all_engineering_members_verified':len(members),'actual_complete_clear_pilot_verified':True}
(case/'K3FULL-prerequisite-verification.json').write_text(json.dumps(observed,indent=2)+chr(10))
print(json.dumps(observed,sort_keys=True))
K3FULL_PREREQUISITE
'''}
 common_args='--pose "$POSE" --k3-stow "$CASE_DIR/prerequisite-stow_tabs_3" --k3-predock "$CASE_DIR/prerequisite-predock" --binding "$HOST_ROOT/k3full/K3FULL_K3_BINDING.json" --key-binding "$HOST_ROOT/k3full/K3FULL_K1_BINDING.json" --contract "$HOST_ROOT/k3full/PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json" --k1-contract "$HOST_ROOT/k3full/KEY_FORWARD_LOOP_V1_CONTRACT.json"'
 native='set -euo pipefail\nfactory_exit=0\n/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/factory-runner" .venv/bin/python -B "$HOST_ROOT/k3full/supervise_k3full.py" --mode factory --output "$CASE_DIR/factory" '+common_args+' || factory_exit=$?\necho "$factory_exit" > "$CASE_DIR/factory-supervisor.exit-code.txt"\nreader_exit=not_executed\n'
 native+='if python3 -B - <<\'K3FULL_PREVIEW\'\nimport json,os,pathlib\np=pathlib.Path(os.environ[\'CASE_DIR\'])/\'factory/worker/report.json\'\nassert p.is_file() and json.loads(p.read_text()).get(\'complete_preview_exports_retained\') is True\nK3FULL_PREVIEW\nthen\n reader_exit=0\n'
 native+=' /usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/readback-runner" .venv/bin/python -B "$HOST_ROOT/k3full/supervise_k3full.py" --mode readback --output "$CASE_DIR/readback" --report "$CASE_DIR/factory/worker/report.json" '+common_args+' || reader_exit=$?\nfi\necho "$reader_exit" > "$CASE_DIR/readback-supervisor.exit-code.txt"\npython3 -B "$HOST_ROOT/k3full/verify_k3full_complete.py" --case "$CASE_DIR" --pose "$POSE"\n'
 steps[9]={'name':'Fresh complete factory and independent full STEP matrix at the preregistered state','shell':'bash','run':native}
 steps[11]={'name':'Export complete all-pair engineering originals and marked projections only','if':'always()','shell':'bash',
  'run':'set -euo pipefail\nmkdir -p "$CASE_DIR/source/k3full"\ncat > "$CASE_DIR/source/k3full/export_k3full_engineering.py" <<\'K3FULL_ENGINEERING_EXPORT\'\n'+sources['export_k3full_engineering.py']+'K3FULL_ENGINEERING_EXPORT\npython3 -B "$CASE_DIR/source/k3full/export_k3full_engineering.py" --case "$CASE_DIR" --output "$CASE_DIR-engineering-export"\n'}
 steps[12]['name']='Preserve complete scientific originals for the actual finite state'
 steps[12]['with']['name']='S4-K3FULL-${{ matrix.pose }}-${{ github.run_id }}-${{ github.run_attempt }}-engineering'
 steps[12]['with']['path']='${{ runner.temp }}/razr-s4-panel-key-stop-k3full-20261026/factory/${{ matrix.pose }}-engineering-export'
 steps[12]['with']['include-hidden-files']=False
 shells=[]
 for step in steps:
  if 'run' in step:
   c=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True);assert c.returncode==0,(step['name'],c.stderr);shells.append(step['name'])
 workflow='# Ten exact finite factories after actual dual K3 pilot; no continuous or physical qualification.\n'+yaml.safe_dump(w,sort_keys=False,width=110)
 (HERE/'s4-panel-key-stop-k3full-hosted.yml').write_text(workflow)
 embedded=inspect_embedded_python(HERE/'s4-panel-key-stop-k3full-hosted.yml')
 assert embedded['all_embedded_and_generated_Python_AST_passed'],embedded['failures']
 plan={'schema':'razr-K3FULL-ten-factory-preexecution-capacity-plan-v1','functional_source_commit':S4,'source_tree':TREE,
  'branch':'diagnostic/s4-panel-key-stop-k3full-20261026','actual_dual_pilot_run_id':binding['run_id'],'actual_dual_pilot_head_sha':binding['head_sha'],
  'actual_dual_pilot_binding_sha256':sha(sources['K3FULL_K3_BINDING.json'].encode()),'candidate_source_sha256':binding['candidate_source_sha256'],
  'candidate_contract_sha256':binding['contract_sha256'],'sources':expected,'workflow_sha256':sha(workflow.encode()),'workflow_bytes':len(workflow.encode()),
  'states':STATES,'expected_contact_end_by_side':EXPECTED_CONTACT_ENDS,'fresh_factory_plus_reader_pair_evaluations_planned':237818,
  'selected_and_completed_journal_rows_planned':475636,'independent_native_early_gate_rows_planned':156,
  'four_independent_left_right_boundary_factories_included':True,'prior_pair_result_reused_instead_of_fresh_Common':False,
  'worker_wall_seconds':1200,'worker_peak_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,'startup_ordinary_disk_MiB':256,
  'runtime_ordinary_disk_MiB':100,'startup_additional_memory_MiB':2048,'outer_deadline_seconds':3240,'job_timeout_minutes':60,'maximum_parallel_jobs':2,
  'additional_input_export_ordinary_disk_reserve_MiB':1536,'actual_two_pilot_inputs_unpacked_bytes':408408534,
  'actual_K2_factory_seconds_observed_range':[305.471401959,484.620509848],'actual_K2_reader_seconds_observed_range':[233.206273563,369.893422049],
  'actual_K3_pilot_factory_seconds':[128.05840331800027,138.25220973],'actual_K3_pilot_reader_seconds':[67.80708747500012,75.08905887399999],
  'actual_pilot_max_sampled_factory_RSS_bytes':563232768,'actual_pilot_max_sampled_reader_RSS_bytes':543293440,
  'planned_factory_seconds_range':[350,600],'planned_reader_seconds_range':[270,480],'setup_download_export_seconds_range':[90,180],
  'planned_five_two_job_waves_minutes_range':[60,105],'queue_time_included':False,'completion_guaranteed_by_estimate':False,
  'all_embedded_and_generated_Python_AST_passed':True,'Python_heredoc_count':embedded['Python_heredoc_count'],'executable_inline_Python_count':embedded['executable_inline_Python_count'],
  'original_resource_gates_not_relaxed':True,'all_shell_blocks_parse':True,'shell_blocks':shells,'new_native_full_campaign_executed':False,
  'current_S4_or_K1_domain_reduced':False,'full_continuous_motion_proved':False,'physical_allowed_domain_proved':False,'strength_qualified':False,
  'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'raw_runtime_durable_preservation_claimed':False}
 plan_text=json.dumps(plan,indent=2)+'\n';(HERE/'K3FULL_EXECUTION_PLAN.json').write_text(plan_text)
 public={**sources,'verify_embedded_python.py':(HERE/'verify_embedded_python.py').read_text(),'build_k3full_workflow.py':Path(__file__).read_text(),'README.md':(HERE/'README.md').read_text(),'K3FULL_EXECUTION_PLAN.json':plan_text}
 elements=[{'path':'engineering/engineering-next-20261026/panel-key-stop-k3full/'+name,'mode':'100644','type':'blob','content':s} for name,s in public.items()]
 elements.append({'path':'.github/workflows/s4-panel-key-stop-k3full-hosted.yml','mode':'100644','type':'blob','content':workflow})
 (HERE/'K3FULL_PUBLIC_TREE_REQUEST.json').write_text(json.dumps({'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':elements},indent=2)+'\n')
 print(json.dumps({'runtime_sources':len(sources),'public_entries':len(elements),'workflow_bytes':len(workflow.encode()),'workflow_sha256':sha(workflow.encode()),'shell_blocks':len(shells)},sort_keys=True))

if __name__=='__main__':main()
