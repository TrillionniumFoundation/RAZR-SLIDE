"""Build the actual K1 capacity workflow from the reviewed L2a hosted lifecycle."""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import re
import subprocess
import yaml

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
FILES=('run_capacity_v4.py','supervise_capacity_v4.py','capacity_stage_v4.py','full_slide_api_v4.py',
       'envelope_v2.py','correlated_v3.py','test_l2_native.py','frozen_key_factory_adapter.py',
       'K1_BINDING.json','read_capacity_v4.py','export_capacity_v4.py','check_capacity_stage.py','README.md')


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-workflow',type=Path,required=True)
    ap.add_argument('--baseline-repo',type=Path,required=True)
    ap.add_argument('--freeze-validator',type=Path,required=True)
    args=ap.parse_args()
    b=json.loads((HERE/'K1_BINDING.json').read_text())
    assert b['actual_two_clear_witnesses_reviewed'] is True
    assert sha((HERE/'K1_BINDING.json').read_bytes())=='cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be'
    assert b['run_id']==40276423445 and b['head_sha']=='78da3826a1cce029cb36b76555d6be7de2001ba2'
    assert subprocess.check_output(['git','rev-parse',S4+'^{tree}'],cwd=args.baseline_repo,text=True).strip()==TREE
    sources={n:(HERE/n).read_text() for n in FILES}
    expected={n:{'sha256':sha(t.encode()),'bytes':len(t.encode())} for n,t in sources.items()}
    for n,t in sources.items():
        if n.endswith('.py'):ast.parse(t,feature_version=(3,10))
    frozen={'full_slide_api_v4.py':'698a1da718b450dbfaadd62c4f098d1aab6aca950df8e3aa1c3c80e9e5dd9a64',
            'envelope_v2.py':'807f346113d48099f35f79749de6bb5c7baa1d76a9e5c4e468578185554958cc',
            'correlated_v3.py':'2d85084f422f4d3a8a029b9df00abba6545786c4d0c9f1cde7a6b124be1e7ae2',
            'frozen_key_factory_adapter.py':'b112d97a4bb888e17c0a4c4de75abd322c28c89e274ac6f63ef7c734940f70c6',
            'test_l2_native.py':'39301f79b382cd1567711dc6c6e191d8058989e66e13b83718dff2097d891318'}
    for n,h in frozen.items():assert expected[n]['sha256']==h,n
    w=yaml.safe_load(args.base_workflow.read_text())
    w['name']='V4 K1 full-q difficult-pair capacity with unchanged S4 guards'
    w['on']={'push':{'branches':['diagnostic/s4-k1-v4-capacity-20261026']},'workflow_dispatch':None}
    w['concurrency']={'group':'v4-capacity-${{ github.ref }}','cancel-in-progress':False}
    job=w['jobs']['replay'];job.pop('strategy')
    job['name']='V4 actual K1 loader, five factory-law probes and 17 full-q capacity pairs'
    job['env']={'CASE_KIND':'v4','CASE_KEY':'capacity17'}
    old=job['steps'];old[0]['run']=old[0]['run'].replace('razr-s4-l2-replay-20261026','razr-s4-k1-v4-capacity-20261026')
    prefix=old[2]['run'].split('mkdir -p "$HOST_ROOT/l2" "$CASE_DIR/source/l2"\n',1)
    assert len(prefix)==2 and TREE in prefix[0]
    bootstrap=prefix[0]
    # Change named diagnostic metadata only; never replace bare time digits or
    # anything inside an immutable Git SHA. Native budget constants are intact.
    bootstrap=bootstrap.replace("'L2_original_L1_worker_budget_seconds'", "'V4_original_SLIDE_worker_budget_seconds'")
    bootstrap=bootstrap.replace("'finite_native_trial_budget_seconds_unchanged'", "'original_F1_finite_worker_budget_not_used'")
    bootstrap=bootstrap.replace("'original_v4_trial_budget_not_applicable'", "'original_F1_trial_budget_not_applicable'")
    bootstrap=bootstrap.replace("'razr-S4-L2-source-before-v1'", "'razr-S4-V4-source-before-v1'")
    def heredoc(name):
        marker='cat > "$HOST_ROOT/'+name+'" <<\'PY\'\n'
        return bootstrap.split(marker,1)[1].split('\nPY\n',1)[0]+'\n'
    harness={n:sha(heredoc(n).encode()) for n in ('host-cap.py','service-launch.py')}
    bootstrap,count=re.subn(r"assert record\['service_launcher_sha256'\].*", "assert record['service_launcher_sha256']=='"+harness['service-launch.py']+"' and record['hostcap_sha256']=='"+harness['host-cap.py']+"'",bootstrap)
    assert count==1
    block=bootstrap+'mkdir -p "$HOST_ROOT/v4" "$CASE_DIR/source/v4"\n'
    for n,t in sources.items():
        marker='V4_'+re.sub('[^A-Z0-9]','_',n.upper());assert marker not in t and t.endswith('\n')
        block+=f'cat > "$HOST_ROOT/v4/{n}" <<\'{marker}\'\n'+t+marker+'\n'
        block+=f'cp "$HOST_ROOT/v4/{n}" "$CASE_DIR/source/v4/{n}"\n'
    block+='python3 -B - <<\'V4_SOURCE_CHECK\'\nimport hashlib,json,os,pathlib\np=pathlib.Path(os.environ[\'HOST_ROOT\'])/\'v4\'\nexpected='+repr(expected)+'\n'
    block+='for name,row in expected.items():\n data=(p/name).read_bytes();assert len(data)==row[\'bytes\'] and hashlib.sha256(data).hexdigest()==row[\'sha256\']\n'
    block+='(pathlib.Path(os.environ[\'CASE_DIR\'])/\'V4_SOURCE_IDENTITY.json\').write_text(json.dumps(expected,indent=2)+\'\\n\')\nV4_SOURCE_CHECK\n'
    block+='python3 -B "$HOST_ROOT/v4/check_capacity_stage.py"\n'
    old[2]={'name':'Bind immutable S4, exact V4 capacity sources and original lifecycle limits','shell':'bash','run':block}
    downloads=[]
    for pose in ('near','far'):
        row=b['poses'][pose]
        assert row['actual_factory_finite_pose_clear'] is True and row['actual_reader_finite_pose_clear'] is True
        step=copy.deepcopy(old[6]);step['name']='Download actual dual-clear K1 '+pose+' engineering artifact'
        step['with']={'artifact-ids':str(row['artifact_id']),'run-id':str(b['run_id']),
            'repository':'TrillionniumFoundation/RAZR-SLIDE','github-token':'${{ github.token }}','merge-multiple':True,
            'path':'${{ runner.temp }}/razr-s4-k1-v4-capacity-20261026/K1-download/'+pose}
        downloads.append(step)
    verify={'name':'Verify complete K1 engineering members and exact reviewed producer/readback projections',
        'shell':'bash','run':'''set -euo pipefail
python3 -B - <<'V4_K1_VERIFY'
import hashlib,json,os,pathlib,shutil
host=pathlib.Path(os.environ['HOST_ROOT']);case=pathlib.Path(os.environ['CASE_DIR'])
b=json.loads((host/'v4/K1_BINDING.json').read_text());assert b['actual_two_clear_witnesses_reviewed'] is True
observed={}
for pose in ('near','far'):
 src=(host/'K1-download'/pose).resolve();manifest=src/'ENGINEERING_MANIFEST.json';ref=b['poses'][pose]
 assert hashlib.sha256(manifest.read_bytes()).hexdigest()==ref['engineering_manifest_sha256']
 members=json.loads(manifest.read_text())['members'];dest=case/('prerequisite-'+pose);dest.mkdir()
 actual={p.relative_to(src).as_posix() for p in src.rglob('*') if p.is_file()}
 assert actual==set(members)|{'ENGINEERING_MANIFEST.json'}
 for rel,m in members.items():
  p=(src/rel).resolve();assert p.is_relative_to(src) and p.is_file() and not p.is_symlink()
  data=p.read_bytes();assert len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256']
  target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 shutil.copyfile(manifest,dest/'ENGINEERING_MANIFEST.json')
 for kind in ('factory','readback'):
  path=dest/kind/'worker/report.engineering.json';data=path.read_bytes()
  label='factory' if kind=='factory' else 'reader'
  assert hashlib.sha256(data).hexdigest()==ref['actual_'+label+'_projection_sha256']
  w=json.loads(data);assert w['derived_projection_not_raw_original'] is True
  assert w['original']['sha256']==ref['original_'+label+'_report_sha256']
  r=w['engineering_record'];assert r['execution_completed'] is True and r['finite_pose_clear'] is True
  assert len(r['participant_names'])==154 and len(r['pairs'])==11781
  assert not r['evaluation_failures'] and not r['mismatches_to_factory']
 observed[pose]={'artifact_id':ref['artifact_id'],'run_id':b['run_id'],'head_sha':b['head_sha'],
  'engineering_manifest_sha256':ref['engineering_manifest_sha256'],
  'all_scientific_member_hashes_checked':len(members),'exact_reviewed_projection_bytes_verified':True}
(case/'V4_K1_PREREQUISITES_VERIFIED.json').write_text(json.dumps(observed,indent=2)+'\\n')
print(json.dumps(observed))
V4_K1_VERIFY
'''}
    native={'name':'Measure actual K1 full-q capacity through unchanged original owned SLIDE limits','shell':'bash','run':'''set -euo pipefail
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/capacity-runner" \\
 .venv/bin/python -B "$HOST_ROOT/v4/supervise_capacity_v4.py" --output "$CASE_DIR/capacity" \\
 --k1-near "$CASE_DIR/prerequisite-near" --k1-far "$CASE_DIR/prerequisite-far" --binding "$HOST_ROOT/v4/K1_BINDING.json"
'''}
    reader={'name':'Independently rebuild exact source partitions and read signed records and all BREP hashes',
        'if':'always()','shell':'bash','run':'''set -euo pipefail
.venv/bin/python -B "$HOST_ROOT/v4/read_capacity_v4.py" --science "$CASE_DIR/capacity/worker/science" \\
 --output "$CASE_DIR/capacity/worker/science/INDEPENDENT_CAPACITY_RECORD_CHECK.json"
'''}
    export={'name':'Export actual scientific BREP and record allowlist only','if':'always()','shell':'bash','run':'''set -euo pipefail
python3 -B "$HOST_ROOT/v4/export_capacity_v4.py" --case "$CASE_DIR" --sources "$HOST_ROOT/v4" --output "$CASE_DIR/publish"
'''}
    upload=copy.deepcopy(old[-1]);upload['name']='Retain V4 capacity science only; no raw runtime collections'
    upload['with']['name']='S4-V4-capacity17-${{ github.run_id }}-${{ github.run_attempt }}'
    upload['with']['path']='${{ runner.temp }}/razr-s4-k1-v4-capacity-20261026/v4/capacity17/publish'
    upload['with']['include-hidden-files']=False
    job['steps']=[*old[:6],*downloads,verify,native,reader,export,upload]
    for step in job['steps']:
        if 'run' in step:subprocess.run(['bash','-n'],input=step['run'].encode(),check=True)
    wf=HERE/'s4-k1-v4-capacity-hosted.yml';wf.write_text('# Native capacity measurement only. Original geometry/domain/volume and resource gates retained.\n'+yaml.safe_dump(w,sort_keys=False,width=110))
    subprocess.run(['python3','-B',str(args.freeze_validator),'--workflow',str(wf),
        '--baseline-repo',str(args.baseline_repo),'--source-dir',str(HERE),'--label','V4','--out',str(HERE/'V4_STATIC_CHECK.json')],check=True)
    plan={'schema':'razr-V4-capacity-publication-plan-v1','functional_commit':S4,'functional_tree':TREE,
        'branch':'diagnostic/s4-k1-v4-capacity-20261026','actual_K1_binding_sha256':expected['K1_BINDING.json']['sha256'],
        'sources':expected,'workflow_sha256':sha(wf.read_bytes()),'worker_wall_seconds':1800,'worker_RSS_MiB':1536,
        'shared_unreclaimable_GiB':6.8,'startup_disk_MiB':200,'runtime_disk_MiB':100,
        'startup_additional_memory_MiB':1536,'host_job_minutes':40,'host_command_deadline_seconds':2220,
        'priority_physical_pairs':17,'complete_original_pair_slots':11781,'remaining_unmeasured_pairs_after_complete_stage':11764,
        'original_subdivision_parameter':2,'maximum_calls_per_persistent_overlap_pair':36,
        'actual_native_capacity_execution_done':False,'full_product_execution_done':False,
        'no_raw_runtime_exported':True,'candidate_go':False,'manufacturing_go':False}
    (HERE/'V4_PUBLICATION_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    public={**sources,'V4_STATIC_CHECK.json':(HERE/'V4_STATIC_CHECK.json').read_text(),
            'V4_PUBLICATION_PLAN.json':(HERE/'V4_PUBLICATION_PLAN.json').read_text(),
            'build_capacity_workflow.py':Path(__file__).read_text(),
            'validate_workflow_freeze.py':args.freeze_validator.read_text()}
    elements=[{'path':'engineering/engineering-integration-20261026/capacity-V4/'+n,'mode':'100644','type':'blob','content':t} for n,t in public.items()]
    elements.append({'path':'.github/workflows/s4-k1-v4-capacity.yml','mode':'100644','type':'blob','content':wf.read_text()})
    req=HERE/'V4_PUBLIC_TREE_REQUEST.json';req.write_text(json.dumps({'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':elements},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'request_sha256':sha(req.read_bytes()),'request_bytes':req.stat().st_size,'workflow_sha256':plan['workflow_sha256'],'tree_paths':len(elements)}))


if __name__=='__main__':main()
