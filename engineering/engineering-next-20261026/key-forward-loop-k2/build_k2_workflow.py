"""Freeze K2 only after actual dual-clear K1 engineering artifacts are reviewed."""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml
from k2_endpoints import ENDPOINTS

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
FILES=('f1_common.py','frozen_key_factory_adapter.py','k2_endpoints.py','full_factory_endpoint.py',
       'read_factory_endpoint.py','supervise_k2.py','K2_K1_BINDING.json','export_k2_engineering.py','verify_k2_complete.py')


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base-workflow',type=Path,required=True)
    ap.add_argument('--binding',type=Path,required=True);ap.add_argument('--output',type=Path,default=HERE)
    args=ap.parse_args();out=args.output;b=json.loads(args.binding.read_text())
    assert b['run_id']==40276423445 and b['head_sha']=='78da3826a1cce029cb36b76555d6be7de2001ba2'
    assert b['actual_two_clear_witnesses_reviewed'] is True and set(b['poses'])=={'near','far'}
    assert b['candidate_source_sha256']=='3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578'
    assert b['contract_sha256']=='17e1532ed82eff1298e9525456d6953df56437082ef2918f3d04839cff200455'
    for pose,r in b['poses'].items():
        assert type(r['artifact_id']) is int and r['artifact_id']>0
        assert r['artifact_name']==f'S4-K1-{pose}-{b["run_id"]}-1-engineering'
        assert re.fullmatch('[0-9a-f]{64}',r['engineering_manifest_sha256'])
        assert r['actual_factory_execution_completed'] is True and r['actual_reader_execution_completed'] is True
        assert r['actual_factory_finite_pose_clear'] is True and r['actual_reader_finite_pose_clear'] is True
    out.mkdir(parents=True,exist_ok=True);bt=json.dumps(b,indent=2)+'\n';(out/'K2_K1_BINDING.json').write_text(bt)
    sources={name:bt if name=='K2_K1_BINDING.json' else (HERE/name).read_text() for name in FILES}
    for name,text in sources.items():
        if name.endswith('.py'):ast.parse(text,filename=name)
    base=yaml.safe_load(args.base_workflow.read_text());w=copy.deepcopy(base)
    w['name']='K2 complete finite endpoint factories after dual-clear K1'
    w['on']={'push':{'branches':['diagnostic/s4-key-loop-k2-endpoints-20261026']},'workflow_dispatch':None}
    w['concurrency']={'group':'k2-${{ github.ref }}','cancel-in-progress':False}
    job=w['jobs'].pop('factory');w['jobs']={'endpoints':job}
    job['name']='K2 actual full endpoint factory and independent STEP: ${{ matrix.pose }}'
    job['strategy']['matrix']={'pose':list(ENDPOINTS)}
    steps=job['steps'];steps[0]['run']=steps[0]['run'].replace('razr-s4-factory-f1-20261026','razr-s4-key-loop-k2-20261026')
    prefix=steps[2]['run'].split('mkdir -p "$HOST_ROOT/f1" "$CASE_DIR/source/f1"\n',1)
    assert len(prefix)==2 and TREE in prefix[0]
    block=prefix[0]+'mkdir -p "$HOST_ROOT/k2" "$CASE_DIR/source/k2"\n';expected={}
    for name,content in sources.items():
        marker='K2_SOURCE_'+re.sub('[^A-Z0-9]','_',name.upper());assert marker not in content and content.endswith('\n')
        block+=f'cat > "$HOST_ROOT/k2/{name}" <<\'{marker}\'\n'+content+marker+'\n'
        block+=f'cp "$HOST_ROOT/k2/{name}" "$CASE_DIR/source/k2/{name}"\n'
        expected[name]={'sha256':sha(content.encode()),'bytes':len(content.encode())}
    block+='python3 -B - <<\'K2_SOURCE_BIND\'\nimport hashlib,json,os,pathlib\np=pathlib.Path(os.environ[\'HOST_ROOT\'])/\'k2\'\nexpected='+repr(expected)+'\n'
    block+='for name,r in expected.items():\n data=(p/name).read_bytes();assert len(data)==r[\'bytes\'] and hashlib.sha256(data).hexdigest()==r[\'sha256\']\n'
    block+='(pathlib.Path(os.environ[\'CASE_DIR\'])/\'K2-driver-source.json\').write_text(json.dumps(expected,indent=2)+\'\\n\')\nK2_SOURCE_BIND\n'
    steps[2]['name']='Bind immutable S4, exact endpoint sources and original hosted lifecycle gates';steps[2]['run']=block
    downloads=[]
    for pose in ('near','far'):
        d=copy.deepcopy(steps[6]);d['name']='Download actual reviewed K1 '+pose+' engineering artifact'
        d['with']={'artifact-ids':str(b['poses'][pose]['artifact_id']),'run-id':str(b['run_id']),
            'repository':'TrillionniumFoundation/RAZR-SLIDE','github-token':'${{ github.token }}','merge-multiple':True,
            'path':'${{ runner.temp }}/razr-s4-key-loop-k2-20261026/K1-download/'+pose}
        downloads.append(d)
    verify={'name':'Verify both exact K1 engineering manifests and actual dual-clear report prerequisites',
        'shell':'bash','run':'''set -euo pipefail
python3 -B - <<'K2_PREREQUISITE'
import hashlib,json,os,pathlib,shutil
host=pathlib.Path(os.environ['HOST_ROOT']);case=pathlib.Path(os.environ['CASE_DIR'])
binding=json.loads((host/'k2/K2_K1_BINDING.json').read_text());assert binding['actual_two_clear_witnesses_reviewed'] is True
observed={}
for pose in ('near','far'):
 src=host/'K1-download'/pose;manifest=src/'ENGINEERING_MANIFEST.json'
 assert hashlib.sha256(manifest.read_bytes()).hexdigest()==binding['poses'][pose]['engineering_manifest_sha256']
 members=json.loads(manifest.read_text())['members'];dest=case/('prerequisite-'+pose);dest.mkdir()
 for rel,ref in members.items():
  p=(src/rel).resolve();assert p.is_relative_to(src.resolve()) and p.is_file() and not p.is_symlink()
  data=p.read_bytes();assert len(data)==ref['bytes'] and hashlib.sha256(data).hexdigest()==ref['sha256']
  target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 shutil.copyfile(manifest,dest/'ENGINEERING_MANIFEST.json')
 for kind in ('factory','readback'):
  wrapper=json.loads((dest/kind/'worker/report.engineering.json').read_text());assert wrapper['derived_projection_not_raw_original'] is True
  r=wrapper['engineering_record'];assert r['execution_completed'] is True and r['finite_pose_clear'] is True
  assert len(r['participant_names'])==154 and len(r['pairs'])==11781 and not r['evaluation_failures'] and not r['mismatches_to_factory']
 observed[pose]={'manifest_sha256':binding['poses'][pose]['engineering_manifest_sha256'],'all_engineering_members_verified':len(members),'both_original_complete_clear_reports_observed':True}
(case/'K2-prerequisite-verification.json').write_text(json.dumps(observed,indent=2)+'\\n')
print(json.dumps(observed,sort_keys=True))
K2_PREREQUISITE
'''}
    native={'name':'Build complete actual endpoint and independently read every STEP and all pairs',
        'shell':'bash','run':'''set -euo pipefail
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/factory-runner" \\
  .venv/bin/python -B "$HOST_ROOT/k2/supervise_k2.py" --mode factory --pose "$POSE" --output "$CASE_DIR/factory" \\
  --k1-near "$CASE_DIR/prerequisite-near" --k1-far "$CASE_DIR/prerequisite-far" --binding "$HOST_ROOT/k2/K2_K1_BINDING.json"
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/readback-runner" \\
  .venv/bin/python -B "$HOST_ROOT/k2/supervise_k2.py" --mode readback --pose "$POSE" --output "$CASE_DIR/readback" \\
  --report "$CASE_DIR/factory/worker/report.json" --k1-near "$CASE_DIR/prerequisite-near" \\
  --k1-far "$CASE_DIR/prerequisite-far" --binding "$HOST_ROOT/k2/K2_K1_BINDING.json"
python3 -B "$HOST_ROOT/k2/verify_k2_complete.py" --case "$CASE_DIR" --pose "$POSE"
'''}
    exporter={'name':'Export endpoint engineering originals and marked projections only','if':'always()',
        'shell':'bash','run':'''set -euo pipefail
mkdir -p "$CASE_DIR/source/k2"
cat > "$CASE_DIR/source/k2/export_k2_engineering.py" <<'K2_ENGINEERING_EXPORT'
'''+sources['export_k2_engineering.py']+'''K2_ENGINEERING_EXPORT
python3 -B "$CASE_DIR/source/k2/export_k2_engineering.py" --case "$CASE_DIR" --output "$CASE_DIR-engineering-export"
'''}
    upload=copy.deepcopy(steps[-1]);upload['name']='Preserve only complete endpoint engineering evidence and frozen K1 engineering prerequisites'
    upload['with']['name']='S4-K2-${{ matrix.pose }}-${{ github.run_id }}-${{ github.run_attempt }}-engineering'
    upload['with']['path']='${{ runner.temp }}/razr-s4-key-loop-k2-20261026/factory/${{ matrix.pose }}-engineering-export'
    upload['with']['include-hidden-files']=False
    job['steps']=[*steps[:6],*downloads,verify,native,steps[9],exporter,upload]
    checked=[]
    for step in job['steps']:
        if 'run' in step:
            r=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
            assert r.returncode==0,(step['name'],r.stderr);checked.append(step['name'])
    workflow='# Four actual endpoint states only; no full-domain or physical release.\n'+yaml.safe_dump(w,sort_keys=False,width=110)
    (out/'s4-key-loop-k2-endpoints-hosted.yml').write_text(workflow)
    plan={'schema':'razr-K2-actual-prerequisite-execution-plan-v1','functional_source_commit':S4,
        'actual_K1_run_id':b['run_id'],'actual_K1_head_sha':b['head_sha'],
        'new_branch':'diagnostic/s4-key-loop-k2-endpoints-20261026','source_tree':TREE,
        'workflow_sha256':sha(workflow.encode()),'workflow_bytes':len(workflow.encode()),'sources':expected,
        'finite_endpoints':ENDPOINTS,'all_factory_plus_reader_pair_evaluations_planned':96446,
        'worker_wall_seconds':1200,'worker_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,
        'startup_disk_MiB':256,'runtime_disk_MiB':100,'additional_startup_memory_MiB':2048,
        'outer_deadline_seconds':3240,'job_timeout_minutes':60,'maximum_parallel_jobs':2,
        'capacity_basis':'F1a actual factories 486.55/490.65 s and readers 363.60/369.57 s; K2 replaces costly baseline reconstruction comparisons by eight verified KEY imports while keeping 154/161 full endpoint inventories. Actual runtime remains subject to unchanged original finite guards.',
        'actual_K1_measured_worker_seconds':{pose:{k:b['poses'][pose].get(k) for k in ('actual_factory_seconds','actual_reader_seconds')} for pose in ('near','far')},
        'all_shell_blocks_parse':True,'shell_blocks':checked,'new_native_K2_executed':False,
        'complete_motion_proved':False,'physical_allowed_domain_proved':False,'strength_qualified':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,'raw_runtime_durable_preservation_claimed':False}
    plan_text=json.dumps(plan,indent=2)+'\n';(out/'K2_EXECUTION_PLAN.json').write_text(plan_text)
    public={**sources,'build_k2_workflow.py':Path(__file__).read_text(),'README.md':(HERE/'README.md').read_text(),'K2_EXECUTION_PLAN.json':plan_text}
    elements=[{'path':'engineering/engineering-next-20261026/key-forward-loop-k2/'+name,'mode':'100644','type':'blob','content':text} for name,text in public.items()]
    elements.append({'path':'.github/workflows/s4-key-loop-k2-endpoints-hosted.yml','mode':'100644','type':'blob','content':workflow})
    (out/'K2_PUBLIC_TREE_REQUEST.json').write_text(json.dumps({'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':TREE,'tree_elements':elements},indent=2)+'\n')
    print(json.dumps(plan,indent=2))


if __name__=='__main__':main()
