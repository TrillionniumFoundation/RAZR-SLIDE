"""Freeze a two-pilot K3 diagnostic workflow, never the ten-state campaign."""
from __future__ import annotations
import argparse,ast,copy,hashlib,json,re,subprocess
from pathlib import Path
import yaml
from k3_pilot_states import PILOTS

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
FILES=('f1_common.py','frozen_key_factory_adapter.py','K3_K1_BINDING.json',
 'KEY_FORWARD_LOOP_V1_CONTRACT.json','PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json',
 'panel_key_travel_stops_v1.py','k3_pilot_states.py','k3_pilot_common.py',
 'independent_stop_checks.py','full_factory_stop_pilot.py','read_stop_pilot.py',
 'supervise_k3.py','verify_k3_pilot.py','export_k3_engineering.py')

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base-workflow',type=Path,required=True)
 a=ap.parse_args();sources={n:(HERE/n).read_text() for n in FILES}
 binding=json.loads(sources['K3_K1_BINDING.json']);assert binding['actual_two_clear_witnesses_reviewed'] is True
 assert binding['run_id']==40276423445 and binding['head_sha']=='78da3826a1cce029cb36b76555d6be7de2001ba2'
 contract=json.loads(sources['PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json'])
 assert sha(sources['panel_key_travel_stops_v1.py'].encode())==contract['candidate_source_sha256']
 assert sha(sources['KEY_FORWARD_LOOP_V1_CONTRACT.json'].encode())==binding['contract_sha256']
 for n,s in sources.items():
  if n.endswith('.py'):ast.parse(s,filename=n)
 w=yaml.safe_load(a.base_workflow.read_text())
 w['name']='K3 additive travel-stop preliminary contact and placement pilots'
 w['on']={'push':{'branches':['diagnostic/s4-panel-key-stop-k3-pilot-20261026']},'workflow_dispatch':None}
 w['concurrency']={'group':'k3-pilot-${{ github.ref }}','cancel-in-progress':False}
 job=w['jobs'].pop('endpoints');w['jobs']={'pilot':job}
 job['name']='K3 preliminary complete factory and independent STEP: ${{ matrix.pose }}'
 job['strategy']['matrix']={'pose':list(PILOTS)}
 steps=job['steps'];steps[0]['run']=steps[0]['run'].replace('razr-s4-key-loop-k2-20261026','razr-s4-panel-key-stop-k3-20261026')
 prefix=steps[2]['run'].split('mkdir -p "$HOST_ROOT/k2" "$CASE_DIR/source/k2"\n',1)
 assert len(prefix)==2 and TREE in prefix[0]
 block=prefix[0]+'mkdir -p "$HOST_ROOT/k3" "$CASE_DIR/source/k3"\n';expected={}
 for name,source in sources.items():
  marker='K3_SOURCE_'+re.sub('[^A-Z0-9]','_',name.upper());assert marker not in source and source.endswith('\n')
  block+=f'cat > "$HOST_ROOT/k3/{name}" <<\'{marker}\'\n'+source+marker+'\n'
  block+=f'cp "$HOST_ROOT/k3/{name}" "$CASE_DIR/source/k3/{name}"\n'
  expected[name]={'sha256':sha(source.encode()),'bytes':len(source.encode())}
 block+='python3 -B - <<\'K3_SOURCE_BIND\'\nimport hashlib,json,os,pathlib\np=pathlib.Path(os.environ[\'HOST_ROOT\'])/\'k3\'\nexpected='+repr(expected)+'\n'
 block+='for name,r in expected.items():\n data=(p/name).read_bytes();assert len(data)==r[\'bytes\'] and hashlib.sha256(data).hexdigest()==r[\'sha256\']\n'
 block+='(pathlib.Path(os.environ[\'CASE_DIR\'])/\'K3-driver-source.json\').write_text(json.dumps(expected,indent=2)+\'\\n\')\nK3_SOURCE_BIND\n'
 steps[2]['name']='Bind immutable S4 and exact K3 pilot sources with original lifecycle guards';steps[2]['run']=block
 for step in steps[6:8]:
  step['with']['path']=step['with']['path'].replace('razr-s4-key-loop-k2-20261026','razr-s4-panel-key-stop-k3-20261026')
 verify=steps[8]['run'].replace('K2','K3').replace('k2/','k3/')
 verify=verify.replace("members=json.loads(manifest.read_text())['members'];dest=case/('prerequisite-'+pose);dest.mkdir()", "members=json.loads(manifest.read_text())['members']\n assert {str(p.relative_to(src)) for p in src.rglob('*') if p.is_file()}==set(members)|{'ENGINEERING_MANIFEST.json'}\n dest=case/('prerequisite-'+pose);dest.mkdir()")
 steps[8]['run']=verify
 native='''set -euo pipefail
factory_exit=0
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/factory-runner" \
 .venv/bin/python -B "$HOST_ROOT/k3/supervise_k3.py" --mode factory --pose "$POSE" --output "$CASE_DIR/factory" \
 --k1-near "$CASE_DIR/prerequisite-near" --k1-far "$CASE_DIR/prerequisite-far" --binding "$HOST_ROOT/k3/K3_K1_BINDING.json" \
 --contract "$HOST_ROOT/k3/PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json" --k1-contract "$HOST_ROOT/k3/KEY_FORWARD_LOOP_V1_CONTRACT.json" || factory_exit=$?
echo "$factory_exit" > "$CASE_DIR/factory-supervisor.exit-code.txt"
reader_exit=not_executed
if python3 -B - <<'K3_PREVIEW_AVAILABLE'
import json,os,pathlib
p=pathlib.Path(os.environ['CASE_DIR'])/'factory/worker/report.json'
assert p.is_file() and json.loads(p.read_text()).get('complete_preview_exports_retained') is True
K3_PREVIEW_AVAILABLE
then
 reader_exit=0
 /usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/readback-runner" \
  .venv/bin/python -B "$HOST_ROOT/k3/supervise_k3.py" --mode readback --pose "$POSE" --output "$CASE_DIR/readback" \
  --report "$CASE_DIR/factory/worker/report.json" --k1-near "$CASE_DIR/prerequisite-near" --k1-far "$CASE_DIR/prerequisite-far" \
  --binding "$HOST_ROOT/k3/K3_K1_BINDING.json" --contract "$HOST_ROOT/k3/PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json" \
  --k1-contract "$HOST_ROOT/k3/KEY_FORWARD_LOOP_V1_CONTRACT.json" || reader_exit=$?
fi
echo "$reader_exit" > "$CASE_DIR/readback-supervisor.exit-code.txt"
python3 -B "$HOST_ROOT/k3/verify_k3_pilot.py" --case "$CASE_DIR" --pose "$POSE"
'''
 steps[9]={'name':'Execute early geometry gates, preserve true rejection, and independently read complete STEP preview','shell':'bash','run':native}
 steps[11]={'name':'Export only original pilot engineering material and marked projections','if':'always()','shell':'bash',
  'run':'set -euo pipefail\nmkdir -p "$CASE_DIR/source/k3"\ncat > "$CASE_DIR/source/k3/export_k3_engineering.py" <<\'K3_ENGINEERING_EXPORT\'\n'+sources['export_k3_engineering.py']+'K3_ENGINEERING_EXPORT\npython3 -B "$CASE_DIR/source/k3/export_k3_engineering.py" --case "$CASE_DIR" --output "$CASE_DIR-engineering-export"\n'}
 steps[12]['name']='Preserve scientific pilot evidence including rejected candidates only'
 steps[12]['with']['name']='S4-K3-${{ matrix.pose }}-${{ github.run_id }}-${{ github.run_attempt }}-engineering'
 steps[12]['with']['path']='${{ runner.temp }}/razr-s4-panel-key-stop-k3-20261026/factory/${{ matrix.pose }}-engineering-export'
 steps[12]['with']['include-hidden-files']=False
 shells=[]
 for step in steps:
  if 'run' in step:
   c=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
   assert c.returncode==0,(step['name'],c.stderr);shells.append(step['name'])
 workflow='# Preliminary two-pose engineering diagnostic; ten-state campaign requires separate actual evidence review.\n'+yaml.safe_dump(w,sort_keys=False,width=110)
 (HERE/'s4-panel-key-stop-k3-pilot-hosted.yml').write_text(workflow)
 plan={'schema':'razr-K3-frozen-two-pilot-execution-plan-v1','functional_source_commit':S4,'source_tree':TREE,
  'new_branch':'diagnostic/s4-panel-key-stop-k3-pilot-20261026','sources':expected,
  'candidate_source_sha256':contract['candidate_source_sha256'],'actual_K1_run_id':binding['run_id'],
  'workflow_sha256':sha(workflow.encode()),'workflow_bytes':len(workflow.encode()),'pilot_states':PILOTS,
  'maximum_panel_pairs_per_worker_after_gates':153,'full_11781_pair_matrix_executed':False,
  'reader_independent_early_gate_count_per_pose':18,'complete_factory_participants_per_pose':154,
  'early_gate_failure_prevents_panel_pair_subset':True,'original_failed_preview_retained_for_independent_reader':True,
  'full_ten_state_campaign_automatically_released':False,
  'worker_wall_seconds':1200,'worker_peak_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,
  'startup_ordinary_disk_MiB':256,'runtime_ordinary_disk_MiB':100,'startup_additional_memory_MiB':2048,
  'outer_deadline_seconds':3240,'job_timeout_minutes':60,'maximum_parallel_jobs':2,
  'capacity_basis':'K2 actual STOW3 full factory 484.620509848 s and independent all-pair reader 369.893422049 s under identical guards. This pilot retains 154 whole exports/imports but evaluates at most 153 changed-panel pairs plus explicit contact/functional/material checks. Native unknown complexity remains subject to the unchanged hard caps.',
  'all_shell_blocks_parse':True,'shell_blocks':shells,'actual_native_K3_executed':False,
  'current_S4_or_K1_domain_reduced':False,'physical_allowed_domain_proved':False,'strength_qualified':False,
  'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'raw_runtime_durable_preservation_claimed':False}
 plan_text=json.dumps(plan,indent=2)+'\n';(HERE/'K3_PILOT_EXECUTION_PLAN.json').write_text(plan_text)
 public={**sources,'README.md':(HERE/'README.md').read_text(),'build_k3_workflow.py':Path(__file__).read_text(),
  'K3_PILOT_EXECUTION_PLAN.json':plan_text}
 for n in ('analyze_k3_source_domain.py','K3_SOURCE_DOMAIN_AND_EXECUTION_PLAN.json'):
  public[n]=(HERE/n).read_text()
 elements=[{'path':'engineering/engineering-next-20261026/panel-key-stop-k3/'+name,'mode':'100644','type':'blob','content':content} for name,content in public.items()]
 elements.append({'path':'.github/workflows/s4-panel-key-stop-k3-pilot-hosted.yml','mode':'100644','type':'blob','content':workflow})
 request={'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':elements}
 (HERE/'K3_PUBLIC_TREE_REQUEST.json').write_text(json.dumps(request,indent=2)+'\n')
 print(json.dumps({'source_count':len(sources),'public_entries':len(elements),'workflow_sha256':plan['workflow_sha256'],'workflow_bytes':len(workflow.encode()),'shell_blocks':len(shells)},sort_keys=True))

if __name__=='__main__':main()
