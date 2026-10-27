"""Build a reviewable immutable-S4 K4 workflow; never publish or run native work.

Input: the byte-verified original K3FULL pyfix workflow at commit 566197a9.
Its infrastructure prefix, S4 byte checks, lock installation and lifecycle are
retained. Only this named finite local-section diagnostic is added externally.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import yaml

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
PREFIX='engineering/engineering-integration-20261027/structure-K4/'
BRANCH='diagnostic/s4-k3-local-sections-k4-20261027'
WORKFLOW='s4-k3-local-sections-k4-hosted.yml'
RUNTIME=('f1_common.py','service-launch.py','host-cap.py','python-downloads.json',
    'k4_local_section_native_api.py','k4_worker.py','supervise_k4.py','prepare_k4_input.py',
    'verify_k4_complete.py','export_k4_engineering.py','K4_LOCAL_SECTION_PILOT_SPEC.json',
    'K4_INPUT_BINDING.json','K4_HOSTED_CAPACITY_CONTRACT.json',
    'key_forward_loop_v1.py','KEY_FORWARD_LOOP_V1_CONTRACT.json',
    'panel_key_travel_stops_v1.py','PANEL_KEY_TRAVEL_STOPS_V1_CONTRACT.json')


def digest(path):
    raw=Path(path).read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def jsonwrite(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def heredoc(target,name,data):
    tag='K4_SOURCE_'+re.sub('[^A-Za-z0-9]','_',name).upper()
    assert tag not in data.splitlines()
    return 'cat > "'+target+'" <<\''+tag+'\'\n'+data+(not data.endswith('\n'))*'\n'+tag+'\n'


def build():
    original=HERE/'original-s4-panel-key-stop-k3full-hosted.yml';raw=original.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='e1d9115c34eddfa9f27756cc792b3f1f8fc72c29'
    old=yaml.safe_load(raw);steps=old['jobs']['full']['steps'];installer=steps[2]['run']
    marker='mkdir -p "$HOST_ROOT/k3full" "$CASE_DIR/source/k3full"\n'
    assert installer.count(marker)==1
    prefix=installer.split(marker)[0]
    for name in ('service-launch.py','host-cap.py'):
        marker_start='cat > "$HOST_ROOT/'+name+'" <<\'PY\'\n'
        body=prefix.split(marker_start,1)[1].split('\nPY\n',1)[0]+'\n'
        assert body.encode()==(HERE/name).read_bytes()
    metadata=prefix.split('cat > "$HOST_ROOT/python-downloads.json" <<\'PYTHON_METADATA\'\n',1)[1].split('\nPYTHON_METADATA\n',1)[0]+'\n'
    (HERE/'python-downloads.json').write_text(metadata)
    native={
        'integration/product_assembly.py':'fc5391d3be98810ada06ca27e65de9a77d2f599c4d1890bb31a4d87ef14791b4',
        'integration/straight_envelope.py':digest(HERE/'original-straight_envelope.py')['sha256'],
        'engineering/engineering-integration-20261025/geometry/execution_identity.py':digest(HERE/'original-execution_identity.py')['sha256'],
        'engineering/engineering-integration-20261025/geometry/slide/owned_process.py':digest(HERE/'original-owned_process.py')['sha256'],
        'pyproject.toml':'910226440f950d17dbe702a2c868d5ae2b679f72f044b14d6d5e2a36fd79279b',
        'uv.lock':'b1387fbbfa74e39474818a8a6235ba7ddf1d97d00629babb1d0e53971141fe6a'}
    bundle={'schema':'razr-K4-frozen-hosted-source-bundle-v1','functional_source_commit':S4,'functional_source_tree':TREE,
        'runtime_sources':{n:digest(HERE/n) for n in RUNTIME},'immutable_S4_helpers':native,
        'original_lifecycle_source_bytes_unchanged':True,'original_finite_guards_unchanged':True}
    jsonwrite(HERE/'K4_FROZEN_SOURCES.json',bundle);bundle_sha=digest(HERE/'K4_FROZEN_SOURCES.json')['sha256']
    install=prefix+'mkdir -p "$HOST_ROOT/k4" "$CASE_DIR/source/k4"\n'
    for name in (*RUNTIME,'K4_FROZEN_SOURCES.json'):
        install+=heredoc('$HOST_ROOT/k4/'+name,name,(HERE/name).read_text())
        install+='cp "$HOST_ROOT/k4/'+name+'" "$CASE_DIR/source/k4/'+name+'"\n'
    install+='python3 -B - <<\'K4_SOURCE_BIND\'\n'
    install+='import hashlib,json,os,pathlib\n'
    install+='host=pathlib.Path(os.environ["HOST_ROOT"]);p=host/"k4";case=pathlib.Path(os.environ["CASE_DIR"])\n'
    install+='assert hashlib.sha256((p/"K4_FROZEN_SOURCES.json").read_bytes()).hexdigest()=='+repr(bundle_sha)+'\n'
    install+='bundle=json.loads((p/"K4_FROZEN_SOURCES.json").read_text())\n'
    install+='for name,ref in bundle["runtime_sources"].items():\n raw=(p/name).read_bytes();assert len(raw)==ref["bytes"] and hashlib.sha256(raw).hexdigest()==ref["sha256"]\n'
    install+='for name in ("service-launch.py","host-cap.py","python-downloads.json"):\n assert (p/name).read_bytes()==(host/name).read_bytes()\n'
    install+='(case/"K4-driver-source.json").write_text(json.dumps(bundle,indent=2)+chr(10))\n'
    install+='(case/"K4-hosted-source-contract.json").write_text(json.dumps({"schema":"razr-K4-hosted-source-contract-v1","functional_source_commit":os.environ["S4"],"frozen_bundle_sha256":'+repr(bundle_sha)+',"native_not_started_by_installation":True,"exact_external_source_bytes_verified":True},indent=2)+chr(10))\n'
    install+='K4_SOURCE_BIND\n'
    source_step={'name':'Bind immutable S4 and exact K4 external sources with original lifecycle guards','shell':'bash','run':install}
    first={'name':'Start bounded hosted deadline and task evidence directory','shell':'bash','run':'''set -euo pipefail
host_root="$RUNNER_TEMP/razr-s4-k3-local-sections-k4-20261027"
case_dir="$host_root/local-sections/K4-twelve-windows"
mkdir -p "$case_dir"
echo "HOST_JOB_START=$(date +%s)" >> "$GITHUB_ENV"
echo "HOST_ROOT=$host_root" >> "$GITHUB_ENV"
echo "CASE_DIR=$case_dir" >> "$GITHUB_ENV"
'''}
    transfer={'name':'Verify the complete original K3FULL archive and retain only three whole STEP inputs','shell':'bash',
        'env':{'GH_READ_TOKEN':'${{ github.token }}'},'run':'''set -euo pipefail
python3 -B "$HOST_ROOT/k4/prepare_k4_input.py" --case "$CASE_DIR"
'''}
    execute='''set -euo pipefail
producer_exit=0
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/producer-runner" .venv/bin/python -B "$HOST_ROOT/k4/supervise_k4.py" --mode producer --output "$CASE_DIR/producer" --inputs "$CASE_DIR/inputs" --sources "$HOST_ROOT/k4/K4_FROZEN_SOURCES.json" --sources-sha256 BUNDLE_SHA || producer_exit=$?
echo "$producer_exit" > "$CASE_DIR/producer-supervisor.exit-code.txt"
reader_exit=not_executed
if test -f "$CASE_DIR/producer/worker/report.json" && test -f "$CASE_DIR/producer/controller.json"; then
  reader_exit=0
  /usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/readback-runner" .venv/bin/python -B "$HOST_ROOT/k4/supervise_k4.py" --mode readback --output "$CASE_DIR/readback" --inputs "$CASE_DIR/inputs" --sources "$HOST_ROOT/k4/K4_FROZEN_SOURCES.json" --sources-sha256 BUNDLE_SHA --producer "$CASE_DIR/producer/worker" || reader_exit=$?
fi
echo "$reader_exit" > "$CASE_DIR/readback-supervisor.exit-code.txt"
python3 -B "$HOST_ROOT/k4/verify_k4_complete.py" --case "$CASE_DIR"
'''.replace('BUNDLE_SHA',bundle_sha)
    execution={'name':'Evaluate twelve whole-body windows and separate complete STEP/BREP readback','shell':'bash','run':execute}
    after=dict(steps[10]);after['name']='Always preserve exact source/environment closure and raw failure identities';after['if']='always()'
    # The fallback exporter is always embedded independently, so a pre-native
    # installation/input failure still produces an explicit engineering package.
    export_run='set -euo pipefail\nmkdir -p "$HOST_ROOT/k4"\n'
    export_run+=heredoc('$HOST_ROOT/k4/export_k4_engineering.py','fallback_export_k4_engineering.py',(HERE/'export_k4_engineering.py').read_text())
    export_run+='python3 -B "$HOST_ROOT/k4/export_k4_engineering.py" --case "$CASE_DIR" --sources "$HOST_ROOT/k4" --output "$HOST_ROOT/engineering-export" --repository "$GITHUB_WORKSPACE"\n'
    exported={'name':'Always preserve engineering originals, failed results and explicitly scoped runtime projections','if':'always()','shell':'bash','run':export_run}
    upload={'name':'Upload only engineering allowlist evidence','if':'always()',
        'uses':'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9',
        'with':{'name':'S4-K4-twelve-local-sections-${{ github.run_id }}-${{ github.run_attempt }}-engineering',
                'path':'${{ runner.temp }}/razr-s4-k3-local-sections-k4-20261027/engineering-export',
                'if-no-files-found':'error','retention-days':14}}
    final={'name':'Require actual local result, complete scientific export and original lifecycle checks','if':'always()','shell':'bash','run':'''set -euo pipefail
python3 -B - <<'K4_FINAL_GATE'
import json,os,pathlib
case=pathlib.Path(os.environ['CASE_DIR']);host=pathlib.Path(os.environ['HOST_ROOT'])
r=json.loads((case/'K4-complete-observation.json').read_text())
assert r['twelve_local_targets_and_two_negative_controls_with_independent_readback_passed'] is True
scope=json.loads((host/'engineering-export/EXPORT_SCOPE.json').read_text())
assert scope['available_allowed_scientific_originals_preserved'] is True and scope['raw_runtime_exported'] is False
for label in ('producer-runner','readback-runner','environment-before-check','environment-after-check'):
 h=json.loads((case/(label+'.namespace')/'SUMMARY.json').read_text())
 assert h['compatibility_verified'] is True and h['cleanup_verified'] is True
 assert h['command_exit_code']==0 and h['normal_command_completed'] is True
for name in ('environment-before.json','environment-after.json'):
 e=json.loads((case/name).read_text());assert e['passed'] is True and e['checked_package_count']==43
assert json.loads((case/'S4-source-after.json').read_text())['all_present_source_bytes_unchanged'] is True
assert all(r[k] is False for k in ('global_minimum_wall_qualified','complete_continuous_motion_proved','physical_allowed_domain_proved','strength_qualified','candidate_go','fixture_fabrication_go','manufacturing_go'))
print(json.dumps({'bounded_K4_local_checks_passed':True,'global_minimum_wall_qualified':False,'full_motion_proved':False,'strength_qualified':False,'candidate_go':False}))
K4_FINAL_GATE
'''}
    job={'name':'K4 twelve frozen local windows and independent native reader','runs-on':'ubuntu-22.04','timeout-minutes':60,
        'strategy':{'fail-fast':False,'max-parallel':1,'matrix':{'pilot':['frozen-twelve-windows']}},'env':{'CASE_KIND':'local-sections','CASE_KEY':'K4-twelve-windows'},
        'steps':[first,steps[1],source_step,steps[3],steps[4],steps[5],transfer,execution,after,exported,upload,final]}
    workflow={'name':'K4 bounded current whole-body local sections and independent readback',
        'on':{'push':{'branches':[BRANCH]},'workflow_dispatch':{}},'permissions':{'contents':'read','actions':'read'},
        'concurrency':{'group':'k4-local-sections-${{ github.ref }}','cancel-in-progress':False},'env':old['env'],'jobs':{'local_sections':job}}
    class Literal(str):pass
    def literal(dumper,data):return dumper.represent_scalar('tag:yaml.org,2002:str',str(data),style='|')
    yaml.SafeDumper.add_representer(Literal,literal)
    for step in workflow['jobs']['local_sections']['steps']:
        if 'run' in step:step['run']=Literal(step['run'])
    (HERE/WORKFLOW).write_text(yaml.safe_dump(workflow,sort_keys=False,width=120))
    assert (HERE/WORKFLOW).stat().st_size<500000,'hosted workflow must stay below the previously observed 500KB limit'
    plan={'schema':'razr-K4-hosted-diagnostic-publication-plan-v1','branch':BRANCH,'base_commit':S4,'base_tree':TREE,
        'workflow_path':'.github/workflows/'+WORKFLOW,'workflow':digest(HERE/WORKFLOW),'source_bundle':digest(HERE/'K4_FROZEN_SOURCES.json'),
        'max_parallel':1,'original_1200s_1536MiB_resource_guards_retained':True,'input_scientific_run_id':40285103942,
        'input_artifact_id':12633972884,'native_execution_already_performed':False,'root_review_and_publication_required':True,
        'main_candidate_go_flags_modified':False,'full_minimum_wall_or_full_15D_evidence_claimed':False}
    jsonwrite(HERE/'K4_PUBLICATION_PLAN.json',plan)
    extras=('build_k4_hosted.py','derive_k4_supervisor.py','verify_k4_prepublication.py','K4_PUBLICATION_PLAN.json',
        'K4_PREPUBLICATION_REVIEW.json','K4_PREPUBLICATION_FAILURE_HISTORY.json','K4_INDEPENDENT_LIMITED_SOURCE_REVIEW.json','K4_SCOPE_AND_EXECUTION.md')
    rows=[]
    for name in (*RUNTIME,'K4_FROZEN_SOURCES.json',*extras):
        if (HERE/name).is_file():rows.append({'path':PREFIX+name,'mode':'100644','type':'blob','content':(HERE/name).read_text()})
    rows.append({'path':'.github/workflows/'+WORKFLOW,'mode':'100644','type':'blob','content':(HERE/WORKFLOW).read_text()})
    jsonwrite(HERE/'K4_PUBLIC_TREE_REQUEST.json',{'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':rows})
    print(json.dumps({'workflow':digest(HERE/WORKFLOW),'request':digest(HERE/'K4_PUBLIC_TREE_REQUEST.json'),'paths':len(rows),'native_execution':False}))


if __name__=='__main__':build()
