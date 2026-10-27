"""Freeze separate L5 jobs from the reviewed V4a hosted/S4 lifecycle."""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import re
import subprocess
import tempfile
import yaml

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
BASE_SHA='5c3a92e2b3448fffd8c243f5f13bb629ba9d62ab3f2e44b6bfc26b703e4d1629'
FILES=('run_l5.py','supervise_l5.py','cylindrical_sweep_l5.py','exact_xy_support_l5.py',
 'test_l5_native.py','check_l5_plan.py','l5_science_contract.py','read_l5_native.py','read_l5_records.py',
 'export_l5.py','test_export_l5.py','capacity_stage_v4.py','full_slide_api_v4.py','envelope_v2.py',
 'correlated_v3.py','test_l2_native.py','frozen_key_factory_adapter.py','K1_BINDING.json','L5_ORIGINAL_SEVEN_BINDING.json',
 'README.md','L5_METHOD_AND_CAPACITY_PLAN.md')


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base-workflow',type=Path,required=True)
    ap.add_argument('--baseline-repo',type=Path,required=True);args=ap.parse_args()
    base=args.base_workflow.read_bytes();assert sha(base)==BASE_SHA
    assert subprocess.check_output(['git','rev-parse',S4+'^{tree}'],cwd=args.baseline_repo,text=True).strip()==TREE
    source={n:(HERE/n).read_text() for n in FILES};expected={n:{'sha256':sha(v.encode()),'bytes':len(v.encode())} for n,v in source.items()}
    for n,v in source.items():
        if n.endswith('.py'):ast.parse(v,feature_version=(3,10))
    frozen={'envelope_v2.py':'807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc',
        'correlated_v3.py':'2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2',
        'full_slide_api_v4.py':'698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64',
        'test_l2_native.py':'39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318',
        'frozen_key_factory_adapter.py':'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6',
        'K1_BINDING.json':'cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be'}
    for n,v in frozen.items():assert expected[n]['sha256']==v,n
    old=yaml.safe_load(base);old_steps=old['jobs']['replay']['steps'];workflow=copy.deepcopy(old)
    workflow['name']='L5 source-bound complete axial-section sweeps on original and current K1 seven pairs'
    workflow['on']={'push':{'branches':['diagnostic/s4-k1-l5-cylindrical-20261026']},'workflow_dispatch':None}
    workflow['concurrency']={'group':'l5-whole-sections-${{ github.ref }}','cancel-in-progress':False}
    prefix=old_steps[2]['run'].split('mkdir -p "$HOST_ROOT/v4" "$CASE_DIR/source/v4"\n',1)
    assert len(prefix)==2;bootstrap=prefix[0]
    bootstrap=bootstrap.replace("'razr-S4-V4-source-before-v1'","'razr-S4-L5-source-before-v1'")
    bootstrap=bootstrap.replace("'V4_original_SLIDE_worker_budget_seconds'","'L5_original_SLIDE_worker_budget_seconds'")
    def harness_bytes(name):
        marker='cat > "$HOST_ROOT/'+name+'" <<\'PY\'\n'
        return (bootstrap.split(marker,1)[1].split('\nPY\n',1)[0]+'\n').encode()
    harness={name:sha(harness_bytes(name)) for name in ('host-cap.py','service-launch.py')}
    bootstrap,count=re.subn(r"assert record\['service_launcher_sha256'\].*",
        "assert record['service_launcher_sha256']=='"+harness['service-launch.py']+"' and record['hostcap_sha256']=='"+harness['host-cap.py']+"'",bootstrap)
    assert count==1
    block=bootstrap+'mkdir -p "$HOST_ROOT/l5" "$CASE_DIR/source/l5"\n'
    for n,value in source.items():
        marker='L5_'+re.sub('[^A-Z0-9]','_',n.upper());assert marker not in value and value.endswith('\n')
        block+=f'cat > "$HOST_ROOT/l5/{n}" <<\'{marker}\'\n'+value+marker+'\n'
        block+=f'cp "$HOST_ROOT/l5/{n}" "$CASE_DIR/source/l5/{n}"\n'
    block+='python3 -B - <<\'L5_SOURCE_CHECK\'\nimport hashlib,json,os,pathlib\np=pathlib.Path(os.environ[\'HOST_ROOT\'])/\'l5\'\nexpected='+repr(expected)+'\n'
    block+='for name,row in expected.items():\n data=(p/name).read_bytes();assert len(data)==row[\'bytes\'] and hashlib.sha256(data).hexdigest()==row[\'sha256\']\n'
    block+='(pathlib.Path(os.environ[\'CASE_DIR\'])/\'L5_SOURCE_IDENTITY.json\').write_text(json.dumps(expected,indent=2)+\'\\n\')\nL5_SOURCE_CHECK\n'
    block+='python3 -B "$HOST_ROOT/l5/check_l5_plan.py" --source-root "$GITHUB_WORKSPACE" --output "$CASE_DIR/L5_SOURCE_PLAN_RECHECK.json"\n'
    block+='python3 -B "$HOST_ROOT/l5/test_export_l5.py" --source-root "$GITHUB_WORKSPACE"\n'
    prereqs=copy.deepcopy(old_steps[:6])
    prereqs[0]['run']=prereqs[0]['run'].replace('razr-s4-k1-v4-capacity-20261026','razr-s4-k1-l5-cylindrical-20261026')
    prereqs[2]={'name':'Bind immutable S4 and exact L5 source, original budget, pure support and export controls','shell':'bash','run':block}
    download={'name':'Download exact original L1 E17 inputs for seven whole-material cases and saved EXTRUSION',
        'uses':'actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093','with':{
        'artifact-ids':'12605676028','run-id':'40210275856','repository':'TrillionniumFoundation/RAZR-SLIDE',
        'github-token':'${{ github.token }}','merge-multiple':True,
        'path':'${{ runner.temp }}/razr-s4-k1-l5-cylindrical-20261026/original-L1-download'}}
    verify={'name':'Verify exact original scientific members without exporting runtime collections','shell':'bash','run':'''set -euo pipefail
python3 -B - <<'L5_INPUT_VERIFY'
import hashlib,json,os,pathlib
host=pathlib.Path(os.environ['HOST_ROOT']);case=pathlib.Path(os.environ['CASE_DIR']);src=(host/'original-L1-download').resolve()
b=json.loads((host/'l5/L5_ORIGINAL_SEVEN_BINDING.json').read_text());members={}
for row in b['original_cases']:
 m=row['original_result'];members[m['path']]=m
 for item in row['inputs']:
  for m in item['exports'].values():members[m['path']]=m
for item in b['original_EXTRUSION_direct_control']['original_saved_materials']:
 for m in item['exports'].values():members[m['path']]=m
for name,row in members.items():
 p=(src/name).resolve();assert p.is_relative_to(src) and p.is_file() and not p.is_symlink()
 raw=p.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
receipt={'schema':'razr-L5-original-scientific-input-byte-check-v1','original_run_id':b['original_L1_run_id'],
 'original_artifact_id':b['original_E17_artifact_id'],'verified_member_count':len(members),
 'original_whole_cases':7,'original_saved_EXTRUSION_members':4,'verified':True,'raw_runtime_exported':False}
(case/'L5_INPUT_VERIFIED.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
L5_INPUT_VERIFY
'''}
    # The original heredoc is a Python string; make its intended newline literal explicit.
    verify['run']=verify['run'].replace("+'\n')","+'\\n')")
    k1steps=[]
    for step in old_steps:
        if step.get('name','').startswith('Download actual dual-clear K1'):
            step=copy.deepcopy(step);step['with']['path']=step['with']['path'].replace('razr-s4-k1-v4-capacity-20261026','razr-s4-k1-l5-cylindrical-20261026');k1steps.append(step)
        if step.get('name','').startswith('Verify complete K1 engineering'):
            step=copy.deepcopy(step);step['run']=step['run'].replace("host/'v4/K1_BINDING.json'","host/'l5/K1_BINDING.json'").replace('V4_K1_PREREQUISITES_VERIFIED.json','L5_K1_PREREQUISITES_VERIFIED.json')
            k1steps.append(step)
    assert len(k1steps)==3
    jobs={}
    for scope in ('original','current'):
        job=copy.deepcopy(old['jobs']['replay']);job['name']='L5 '+scope+' seven whole-q pairs and separate native readback'
        job['env']={'CASE_KIND':'l5','CASE_KEY':scope};job['steps']=copy.deepcopy(prereqs)+[copy.deepcopy(download),copy.deepcopy(verify)]
        if scope=='current':job['needs']='original';job['steps'].extend(copy.deepcopy(k1steps))
        command='''set -euo pipefail
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/l5-runner" \\
 .venv/bin/python -B "$HOST_ROOT/l5/supervise_l5.py" --output "$CASE_DIR/l5" \\
 --mode producer --scope "$CASE_KEY" --inputs "$HOST_ROOT/original-L1-download"'''
        if scope=='current':command+=' \\\n --k1-near "$CASE_DIR/prerequisite-near" --k1-far "$CASE_DIR/prerequisite-far"'
        command+='\n'
        job['steps'].append({'name':'Run '+scope+' seven actual source-bound whole axial-section sweeps','shell':'bash','run':command})
        job['steps'].append({'name':'Separate owned native BREP STEP readback and complete-pair Common recomputation','if':'always()','shell':'bash','run':'''set -euo pipefail
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/native-reader-runner" \\
 .venv/bin/python -B "$HOST_ROOT/l5/supervise_l5.py" --output "$CASE_DIR/native-reader" \\
 --mode reader --scope "$CASE_KEY" --inputs "$HOST_ROOT/original-L1-download" --producer "$CASE_DIR/l5/worker/science"
'''})
        job['steps'].append({'name':'Independently check exact source layers complete q and every scientific file hash without CAD','if':'always()','shell':'bash','run':'''set -euo pipefail
.venv/bin/python -B "$HOST_ROOT/l5/read_l5_records.py" --science "$CASE_DIR/l5/worker/science" \\
 --native-reader "$CASE_DIR/native-reader/worker/science/NATIVE_READBACK.json" --output "$CASE_DIR/l5/worker/science/INDEPENDENT_RECORD_CHECK.json"
'''})
        job['steps'].append({'name':'Export reviewed science and exact archive-locator projection with failure-preserving manifest','if':'always()','shell':'bash','run':'''set -euo pipefail
python3 -B "$HOST_ROOT/l5/export_l5.py" --case "$CASE_DIR" --sources "$HOST_ROOT/l5" --output "$CASE_DIR/publish" --source-root "$GITHUB_WORKSPACE"
'''})
        upload=copy.deepcopy(old_steps[-1]);upload['name']='Retain L5 '+scope+' scientific originals only'
        upload['with']['name']='S4-L5-'+scope+'-${{ github.run_id }}-${{ github.run_attempt }}'
        upload['with']['path']='${{ runner.temp }}/razr-s4-k1-l5-cylindrical-20261026/l5/'+scope+'/publish'
        job['steps'].append(upload);jobs[scope]=job
    workflow['jobs']=jobs
    wf=HERE/'s4-k1-l5-cylindrical-hosted.yml';wf.write_text('# New diagnostic only; original S4 defaults and resource/volume gates unchanged.\n'+yaml.safe_dump(workflow,sort_keys=False,width=110))
    checks={}
    with tempfile.TemporaryDirectory(prefix='l5-freeze-check-') as td:
        directory=Path(td)
        for name,job in jobs.items():
            projected=copy.deepcopy(workflow);projected['jobs']={'replay':job};path=directory/(name+'.yml')
            path.write_text(yaml.safe_dump(projected,sort_keys=False,width=110));result=directory/(name+'.json')
            subprocess.run(['python3','-B',str(HERE/'validate_workflow_freeze_l5.py'),'--workflow',str(path),
                '--source-dir',str(HERE),'--baseline-repo',str(args.baseline_repo),'--label','L5','--out',str(result)],check=True)
            value=json.loads(result.read_text());value['validated_single_job_projection_sha256']=value.pop('workflow_sha256');checks[name]=value
    static={'schema':'razr-L5-two-job-static-freeze-v1','workflow_sha256':sha(wf.read_bytes()),'checks':checks,
        'original_precedes_current_job':jobs['current']['needs']=='original','native_executed':False,
        'both_native_workers_retain_original_limits':True,'source_or_workflow_changed_in_functional_S4':False}
    (HERE/'L5_STATIC_CHECK.json').write_text(json.dumps(static,indent=2)+'\n')
    plan={'schema':'razr-L5-publication-plan-v1','functional_commit':S4,'functional_tree':TREE,
        'branch':'diagnostic/s4-k1-l5-cylindrical-20261026','sources':expected,'workflow_sha256':sha(wf.read_bytes()),
        'original_cases':7,'current_K1_cases':7,'distinct_physical_pairs':7,'source_layers_per_stage':12,
        'primary_carrier_Common_per_stage':12,'negative_control_Common_per_stage':12,
        'separate_native_reader_recomputes_all_carrier_and_negative_Common':True,
        'worker_wall_seconds':1800,'worker_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,
        'startup_disk_MiB':200,'runtime_disk_MiB':100,'startup_additional_memory_MiB':1536,
        'science_output_cap_bytes':128*2**20,'host_job_minutes':40,'host_command_deadline_seconds':2220,
        'whole_pair_volume_gate_mm3':1e-7,'actual_native_execution_done':False,'full11781_execution_done':False,
        'native_set_or_Boolean_interval_certificate':False,'raw_runtime_exported':False,
        'candidate_go':False,'manufacturing_go':False}
    (HERE/'L5_PUBLICATION_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    public={**source}
    for name in ('check_l5_plan.py','L5_PURE_SOURCE_PLAN_CHECK.json','L5_STATIC_CHECK.json','L5_PUBLICATION_PLAN.json',
                 'build_l5_workflow.py','validate_workflow_freeze_l5.py'):
        public[name]=(HERE/name).read_text()
    elements=[{'path':'engineering/engineering-integration-20261026/envelope-L5/'+name,'mode':'100644','type':'blob','content':value} for name,value in public.items()]
    elements.append({'path':'.github/workflows/s4-k1-l5-cylindrical.yml','mode':'100644','type':'blob','content':wf.read_text()})
    req=HERE/'L5_PUBLIC_TREE_REQUEST.json';req.write_text(json.dumps({'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':elements},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'request_sha256':sha(req.read_bytes()),'request_bytes':req.stat().st_size,'tree_entries':len(elements),'workflow_sha256':sha(wf.read_bytes())}))

if __name__=='__main__':main()
