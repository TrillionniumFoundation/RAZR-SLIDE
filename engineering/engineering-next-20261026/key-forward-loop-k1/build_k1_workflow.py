"""Build a reviewable K1 workflow only after actual F1a artifacts are frozen."""
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

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
S4_TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
FILES=('f1_common.py','k1_evidence.py','key_forward_loop_v1.py','full_factory_candidate.py',
       'read_factory_candidate.py','supervise_k1.py','KEY_FORWARD_LOOP_V1_CONTRACT.json',
       'K1_F1A_BINDING.json','export_k1_engineering.py','verify_k1_complete.py')


def digest(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-workflow',type=Path,required=True)
    ap.add_argument('--binding',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=HERE)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    binding=json.loads(args.binding.read_text())
    assert binding['run_id']==40273568199 and binding['head_sha']=='935d6adb5ceeb2995971cb32ba2a5f7694114237'
    assert binding['actual_artifacts_reviewed'] is True and set(binding['poses'])=={'near','far'}
    for pose,r in binding['poses'].items():
        assert type(r['artifact_id']) is int and r['artifact_id']>0
        assert r['artifact_name']==f'S4-F1-{pose}-40273568199-1-engineering'
        assert re.fullmatch('[0-9a-f]{64}',r['engineering_manifest_sha256'])
        assert r['actual_factory_execution_completed'] is True and r['actual_independent_reader_execution_completed'] is True
    binding_text=json.dumps(binding,indent=2)+'\n'
    (out/'K1_F1A_BINDING.json').write_text(binding_text)
    source={name:binding_text if name=='K1_F1A_BINDING.json' else (HERE/name).read_text() for name in FILES}
    for name,text in source.items():
        if name.endswith('.py'):ast.parse(text,filename=name)
    contract=json.loads(source['KEY_FORWARD_LOOP_V1_CONTRACT.json'])
    assert contract['candidate_source_sha256']==digest(source['key_forward_loop_v1.py'].encode())
    base=yaml.safe_load(args.base_workflow.read_text());w=copy.deepcopy(base)
    w['name']='K1 named forward-loop KEY full-factory witnesses and independent material readback'
    w['on']={'push':{'branches':['diagnostic/s4-key-loop-k1-20261026']},'workflow_dispatch':None}
    w['concurrency']={'group':'k1-${{ github.ref }}','cancel-in-progress':False}
    job=w['jobs'].pop('factory');w['jobs']={'candidate':job}
    job['name']='K1 complete candidate factory and independent STEP/material readback: ${{ matrix.pose }}'
    job['strategy']['matrix']={'include':[{'pose':pose,'artifact_id':binding['poses'][pose]['artifact_id']} for pose in ('near','far')]}
    steps=job['steps'];steps[0]['run']=steps[0]['run'].replace('razr-s4-factory-f1-20261026','razr-s4-key-loop-k1-20261026')
    prefix=steps[2]['run'].split('mkdir -p "$HOST_ROOT/f1" "$CASE_DIR/source/f1"\n',1)
    assert len(prefix)==2 and S4_TREE in prefix[0]
    block=prefix[0]+'mkdir -p "$HOST_ROOT/k1" "$CASE_DIR/source/k1"\n'
    expected={}
    for name,content in source.items():
        marker='K1_SOURCE_'+re.sub('[^A-Z0-9]','_',name.upper())
        assert marker not in content and content.endswith('\n')
        block+=f'cat > "$HOST_ROOT/k1/{name}" <<\'{marker}\'\n'+content+marker+'\n'
        block+=f'cp "$HOST_ROOT/k1/{name}" "$CASE_DIR/source/k1/{name}"\n'
        expected[name]={'sha256':digest(content.encode()),'bytes':len(content.encode())}
    block+='python3 -B - <<\'K1_SOURCE_BIND\'\nimport hashlib,json,os,pathlib\n'
    block+='p=pathlib.Path(os.environ[\'HOST_ROOT\'])/\'k1\'\nexpected='+repr(expected)+'\n'
    block+='for name,r in expected.items():\n data=(p/name).read_bytes();assert len(data)==r[\'bytes\'] and hashlib.sha256(data).hexdigest()==r[\'sha256\']\n'
    block+='(pathlib.Path(os.environ[\'CASE_DIR\'])/\'K1-driver-source.json\').write_text(json.dumps(expected,indent=2)+\'\\n\')\nK1_SOURCE_BIND\n'
    steps[2]['name']='Bind immutable S4 and exact isolated K1 sources; retain original hosted lifecycle gates'
    steps[2]['run']=block
    steps[6]['name']='Download exact reviewed F1a engineering artifact for this pose'
    steps[6]['with']={'artifact-ids':'${{ matrix.artifact_id }}','run-id':'40273568199',
        'repository':'TrillionniumFoundation/RAZR-SLIDE','github-token':'${{ github.token }}',
        'merge-multiple':True,'path':'${{ runner.temp }}/razr-s4-key-loop-k1-20261026/F1a-download'}
    steps[7]={'name':'Verify frozen F1a engineering bytes, complete pair journals, L1 material frames and source projections',
        'shell':'bash','run':'''set -euo pipefail
python3 -B - <<'K1_PREREQUISITE'
import hashlib,json,os,pathlib,shutil,sys
host=pathlib.Path(os.environ['HOST_ROOT']);case=pathlib.Path(os.environ['CASE_DIR'])
sys.path.insert(0,str(host/'k1'))
from k1_evidence import prerequisite
src=host/'F1a-download'
reports,receipt=prerequisite(src,host/'k1/K1_F1A_BINDING.json',os.environ['POSE'])
manifest=json.loads((src/'ENGINEERING_MANIFEST.json').read_text())
out=case/'prerequisite';out.mkdir()
for rel in [*manifest['members'],'ENGINEERING_MANIFEST.json']:
 p=(src/rel).resolve();assert p.is_relative_to(src.resolve()) and p.is_file() and not p.is_symlink()
 target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==hashlib.sha256(p.read_bytes()).hexdigest()
(case/'K1-prerequisite-verification.json').write_text(json.dumps(receipt,indent=2)+'\\n')
print(json.dumps(receipt,sort_keys=True))
K1_PREREQUISITE
'''}
    steps[8]={'name':'Rebuild complete S4, apply named U loop, evaluate all pairs and independently read every STEP/material account',
        'shell':'bash','run':'''set -euo pipefail
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/factory-runner" \\
  .venv/bin/python -B "$HOST_ROOT/k1/supervise_k1.py" --mode factory --pose "$POSE" --output "$CASE_DIR/factory" \\
  --f1-evidence "$CASE_DIR/prerequisite" --binding "$HOST_ROOT/k1/K1_F1A_BINDING.json"
/usr/bin/python3 -B "$HOST_ROOT/service-launch.py" "$CASE_DIR/readback-runner" \\
  .venv/bin/python -B "$HOST_ROOT/k1/supervise_k1.py" --mode readback --pose "$POSE" --output "$CASE_DIR/readback" \\
  --report "$CASE_DIR/factory/worker/report.json" --f1-evidence "$CASE_DIR/prerequisite" \\
  --binding "$HOST_ROOT/k1/K1_F1A_BINDING.json" --contract "$HOST_ROOT/k1/KEY_FORWARD_LOOP_V1_CONTRACT.json"
python3 -B "$HOST_ROOT/k1/verify_k1_complete.py" --case "$CASE_DIR" --pose "$POSE"
'''}
    steps[10]={'name':'Export engineering originals and explicitly marked K1 projections; omit raw runtime',
        'if':'always()','shell':'bash','run':'''set -euo pipefail
mkdir -p "$CASE_DIR/source/k1"
cat > "$CASE_DIR/source/k1/export_k1_engineering.py" <<'K1_ENGINEERING_EXPORT'
'''+source['export_k1_engineering.py']+'''K1_ENGINEERING_EXPORT
python3 -B "$CASE_DIR/source/k1/export_k1_engineering.py" --case "$CASE_DIR" --output "$CASE_DIR-engineering-export"
'''}
    steps[-1]['name']='Preserve only K1 engineering evidence and exact F1a prerequisite engineering export'
    steps[-1]['with']['name']='S4-K1-${{ matrix.pose }}-${{ github.run_id }}-${{ github.run_attempt }}-engineering'
    steps[-1]['with']['path']='${{ runner.temp }}/razr-s4-key-loop-k1-20261026/factory/${{ matrix.pose }}-engineering-export'
    steps[-1]['with']['include-hidden-files']=False
    parsed=[]
    for step in steps:
        if 'run' not in step:continue
        result=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
        assert result.returncode==0,(step['name'],result.stderr)
        parsed.append(step['name'])
    workflow='# Isolated named candidate; no S4 source mutation or release.\n'+yaml.safe_dump(w,sort_keys=False,width=110)
    (out/'s4-key-loop-k1-hosted.yml').write_text(workflow)
    plan={'schema':'razr-K1-frozen-execution-plan-v1','functional_source_commit':S4,'source_tree':S4_TREE,
        'prerequisite_run_id':binding['run_id'],'new_branch':'diagnostic/s4-key-loop-k1-20261026',
        'workflow_sha256':digest(workflow.encode()),'workflow_bytes':len(workflow.encode()),'driver_files':expected,
        'pairs_per_factory':11781,'pairs_per_independent_reader':11781,'two_full_factories':True,
        'original_154_body_whole_material_identity_rechecked':True,'independent_material_reconstruction_required':True,
        'worker_wall_seconds':1200,'worker_RSS_MiB':1536,'shared_unreclaimable_GiB':6.8,
        'startup_disk_MiB':256,'runtime_disk_MiB':100,'additional_startup_memory_MiB':2048,
        'unchanged_outer_deadline_seconds':3240,'job_timeout_minutes':60,
        'capacity_basis':'Prior D6 finite factories took 457-479 s. Additional baseline whole STEP comparisons and candidate accounting must fit the unchanged 1200 s finite guard; fit not yet measured.',
        'declared_leg_section_ratio_to_original':.38/1.5,'strength_qualified':False,
        'new_native_execution_completed':False,'all_go_flags':False,'raw_runtime_durable_preservation_claimed':False,
        'source_and_environment_checks_preserved':True,'all_shell_blocks_parse':True,'shell_blocks':parsed}
    (out/'K1_EXECUTION_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    public={**source,'README.md':(HERE/'README.md').read_text(),'K1_EXECUTION_PLAN.json':json.dumps(plan,indent=2)+'\n',
            'test_k1_engineering_export.py':(HERE/'test_k1_engineering_export.py').read_text(),
            'build_k1_workflow.py':Path(__file__).read_text()}
    elements=[{'path':'engineering/engineering-next-20261026/key-forward-loop-k1/'+name,'mode':'100644','type':'blob','content':content}
              for name,content in public.items()]
    elements.append({'path':'.github/workflows/s4-key-loop-k1-hosted.yml','mode':'100644','type':'blob','content':workflow})
    (out/'K1_PUBLIC_TREE_REQUEST.json').write_text(json.dumps({'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE',
        'base_tree_sha':S4_TREE,'tree_elements':elements},indent=2)+'\n')
    print(json.dumps(plan,indent=2))


if __name__=='__main__':main()
