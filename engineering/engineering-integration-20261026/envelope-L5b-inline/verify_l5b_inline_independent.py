"""Independent offline source/transport review; no native or Git execution."""
from pathlib import Path
import argparse
import ast
import copy
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from contextlib import redirect_stdout
import yaml

REQUEST_SHA = '2d4f311643e9ac73a31dadf6d58b49ebc9c19854b3e4224874aef60b185fd458'
WORKFLOW_SHA = '954e3fe1c0a039f24bc32eeef80e87ecb4225f51010292a482312bc880cd1333'
BASE_WORKFLOW_SHA = 'b355abfd73e34d9096b806ba098c72f88409f3c9aea252059c5aed05fefc4348'
STAGE1_SHA = 'b9773dc610e30196957a71fea34f5daea9884e45a64473119924763a15554e4c'
BINDING_SHA = '7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2'
OLD_BINDING_SHA = 'fa5def368eb9d837ab31d8729d2ff5a5bb080b394392d228429f27375baf2fbf'
PREFIX = 'https://raw.githubusercontent.com/TrillionniumFoundation/RAZR-SLIDE/33386f1d6046aee80b0446b9c21fb7c259c3523a/engineering/engineering-integration-20261026/envelope-L5/'
BINDING_NAME = 'L5_ORIGINAL_SEVEN_BINDING.json'


def identity(raw):
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def frozen(path, digest=None):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size < 1024**2
    raw=path.read_bytes()
    if digest is not None: assert identity(raw)['sha256']==digest
    return raw


def span(text, marker):
    start="<<'"+marker+"'\n"; end='\n'+marker+'\n'
    assert text.count(start)==text.count(end)==1
    a=text.index(start)+len(start);b=text.index(end,a)
    return a,b


def run(args):
    root=args.envelope_root
    folder=root/'l5b-inline'; base=root/'source/L5A'
    raw=frozen(folder/'L5B_INLINE_PUBLIC_TREE_REQUEST.json',REQUEST_SHA)
    request=json.loads(raw);assert len(request['tree_elements'])==12
    stage_raw=frozen(root/'l5b-binding/L5B_BINDING_PUBLIC_TREE_REQUEST.json',STAGE1_SHA)
    stage=json.loads(stage_raw)
    assert request['base_tree_sha']==stage['base_tree_sha']=='c03bdbd891ba22902ab070ca9ab4c5ccfe39909f'
    entries={x['path']:x for x in request['tree_elements']};assert len(entries)==12
    assert all(entries[x['path']]==x for x in stage['tree_elements']) and len(stage['tree_elements'])==5
    binding=frozen(root/'l5b-binding'/BINDING_NAME,BINDING_SHA);assert len(binding)==39348
    old_raw=frozen(base/'.github/workflows/s4-k1-l5-cylindrical.yml',BASE_WORKFLOW_SHA)
    workflow=frozen(folder/'s4-k1-l5b-inline-cylindrical-hosted.yml',WORKFLOW_SHA)
    assert len(old_raw)==148236 and len(workflow)==247450 and len(workflow)<500000
    assert entries['.github/workflows/s4-k1-l5-cylindrical.yml']['content'].encode()==workflow
    old,new=yaml.safe_load(old_raw),yaml.safe_load(workflow)
    restored=copy.deepcopy(new)
    for key in ('name','on','concurrency'):restored[key]=copy.deepcopy(old[key])
    assert set(new['jobs'])=={'original','current'}
    installers=[];footers=[];always=[]
    for job in ('original','current'):
        before=old['jobs'][job]['steps'][2]['run'];after=new['jobs'][job]['steps'][2]['run']
        a,b=span(before,'L5A_PINNED_PUBLIC_SOURCE');c,d=span(after,'L5A_PINNED_PUBLIC_SOURCE')
        assert before[:a]==after[:c]
        assert before[b:].replace(OLD_BINDING_SHA,BINDING_SHA).replace('25013','39348')==after[d:]
        assert "timeout --signal=TERM --kill-after=5s 90s python3 -B - <<'L5A_PINNED_PUBLIC_SOURCE'" in after
        installers.append(after[c:d]);f,g=span(after,'L5_SOURCE_CHECK');footers.append(after[f:g])
        restored['jobs'][job]['steps'][2]=copy.deepcopy(old['jobs'][job]['steps'][2])
        for step in new['jobs'][job]['steps']:
            if step.get('if')=='always()':always.append({'job':job,'step':step['name']})
    assert restored==old and installers[0]==installers[1] and footers[0]==footers[1]
    assert new['jobs']['current']['needs']=='original'
    assert all(j['timeout-minutes']==40 for j in new['jobs'].values())
    assert len(always)==8
    installer=installers[0];footer=footers[0]
    assert frozen(folder/'l5b_inline_source_install.py')==installer.encode()+b'\n'
    tree=ast.parse(installer,feature_version=(3,10))
    assignments={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    expression=assignments['binding_raw']
    assert isinstance(expression,ast.Call) and expression.func.attr=='encode'
    assert ast.literal_eval(expression.func.value).encode(ast.literal_eval(expression.args[0]))==binding
    expected=ast.literal_eval(assignments['expected']);assert len(expected)==20 and BINDING_NAME not in expected
    assert ast.literal_eval(assignments['prefix'])==PREFIX
    transport=json.loads(frozen(base/'engineering/engineering-integration-20261026/envelope-L5a/L5A_SOURCE_TRANSPORT_BINDING.json'))
    old_expected={x['name']:{'sha256':x['sha256'],'bytes':x['bytes']} for x in transport['source_files']}
    del old_expected[BINDING_NAME];assert expected==old_expected
    source_base=base/'engineering/engineering-integration-20261026/envelope-L5'
    fixtures={name:frozen(source_base/name,row['sha256']) for name,row in expected.items()}
    assert all(len(fixtures[name])==row['bytes'] for name,row in expected.items())
    assert sum(map(len,fixtures.values()))==193306
    assert sum(name.endswith('.py') for name in fixtures)==17
    all_expected=dict(expected);all_expected[BINDING_NAME]=identity(binding)
    shell_count=python_count=0
    for job in new['jobs'].values():
        for step in job['steps']:
            if 'run' not in step:continue
            command=step['run']
            checked=subprocess.run(['/bin/bash','-n'],input=command.encode(),capture_output=True,check=False)
            assert checked.returncode==0 and not checked.stderr
            shell_count+=1;lines=command.splitlines()
            for i,line in enumerate(lines):
                match=re.search(r"\bpython(?:3)?(?: -B)? - <<'([A-Za-z0-9_]+)'$",line)
                if match:
                    j=next(j for j in range(i+1,len(lines)) if lines[j]==match.group(1))
                    ast.parse('\n'.join(lines[i+1:j])+'\n',feature_version=(3,10));python_count+=1
    assert (shell_count,python_count)==(19,11)
    mapping=json.loads(frozen(folder/'L5B_INLINE_SAFE_INTEGRATION_MAPPING.json'))
    for item in mapping['entries']:
        bb=frozen(Path(item['local_path']),item['sha256'])
        assert len(bb)==item['bytes'] and bb==entries[item['repository_path']]['content'].encode()
    transport_record=json.loads(frozen(folder/'L5B_INLINE_TRANSPORT_READBACK.json','00428452eb907ecce5056fbda707eb476ae04dc05d471f9e2376116005358a09'))
    assert transport_record['installer_sha256']==identity(installer.encode())['sha256']
    assert transport_record['installer_bytes']==len(installer.encode())==45147
    assert transport_record['standalone_installer_sha256']==identity(installer.encode()+b'\n')['sha256']
    assert {x['name']:{'bytes':x['bytes'],'sha256':x['sha256']} for x in transport_record['installed_files']}==all_expected
    args.output.parent.mkdir(parents=True,exist_ok=True)
    old_opener=urllib.request.build_opener;old_env={key:os.environ.get(key) for key in ('HOST_ROOT','CASE_DIR')}
    controls=[]
    try:
        with tempfile.TemporaryDirectory(prefix='l5b-offline-independent-',dir=args.output.parent) as temporary:
            for label in ('exact_local_fixtures','damaged_inline_binding','damaged_public_source'):
                host=Path(temporary)/label/'host';case=Path(temporary)/label/'case'
                (host/'l5').mkdir(parents=True);(case/'source/l5').mkdir(parents=True)
                os.environ['HOST_ROOT']=str(host);os.environ['CASE_DIR']=str(case)
                calls=[]
                class Response:
                    status=200
                    def __init__(self,url):self.url=url
                    def __enter__(self):return self
                    def __exit__(self,*unused):return False
                    def geturl(self):return self.url
                    def read(self,n):
                        name=self.url.removeprefix(PREFIX);bb=fixtures[name]
                        if label=='damaged_public_source':bb=bytes([bb[0]^1])+bb[1:]
                        assert n==expected[name]['bytes']+1
                        return bb[:n]
                class OfflineOpener:
                    def open(self,request,timeout):
                        assert request.full_url.startswith(PREFIX) and timeout==15
                        assert set(dict(request.header_items()))=={'User-agent'}
                        calls.append(request.full_url.removeprefix(PREFIX))
                        return Response(request.full_url)
                urllib.request.build_opener=lambda *unused:OfflineOpener()
                code=ast.parse(installer)
                if label=='damaged_inline_binding':
                    node=next(n for n in code.body if isinstance(n,ast.Assign) and n.targets[0].id=='binding_raw')
                    node.value.func.value.value='['+node.value.func.value.value[1:]
                observation={'control':label,'network_requests':0,'native_source_imports_or_execution':False}
                try:
                    with redirect_stdout(io.StringIO()) as log:
                        exec(compile(ast.fix_missing_locations(code),'<offline source installer>','exec'),{})
                    assert label=='exact_local_fixtures'
                    assert calls==list(expected)
                    for name,wanted in all_expected.items():
                        x=(host/'l5'/name).read_bytes();y=(case/'source/l5'/name).read_bytes()
                        assert x==y and identity(x)==wanted
                    with redirect_stdout(io.StringIO()):exec(compile(footer,'<original source footer>','exec'),{})
                    assert json.loads((case/'L5_SOURCE_IDENTITY.json').read_text())==all_expected
                    observation.update(accepted=True,fixture_responses=len(calls),both_copies_verified=42,original_21_footer_passed=True)
                except ValueError as error:
                    expected_gate='inline_complete_target_binding_bytes_differ' if label=='damaged_inline_binding' else 'published_source_bytes_differ'
                    assert label!='exact_local_fixtures' and str(error)==expected_gate
                    assert len(calls)==(0 if label=='damaged_inline_binding' else 1)
                    assert {p.name for p in (host/'l5').iterdir()}==(set() if label=='damaged_inline_binding' else {BINDING_NAME})
                    observation.update(accepted=False,failure_gate=str(error),fixture_responses=len(calls),corrupt_source_not_installed=True)
                controls.append(observation)
    finally:
        urllib.request.build_opener=old_opener
        for key,value in old_env.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    result={'schema':'razr-L5b-inline-independent-offline-review-v1',
        'reviewed_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'review_source_sha256':identity(Path(__file__).read_bytes())['sha256'],
        'request_identity':identity(raw),'workflow_identity':identity(workflow),
        'base_workflow_identity':identity(old_raw),'preserved_stage1_request_identity':identity(stage_raw),
        'request_paths':12,'preserved_stage1_entries_byte_identical':5,
        'all_12_request_entries_match_local_frozen_mapping':True,
        'workflow_under_500000_bytes':True,'public_source_commit':'33386f1d6046aee80b0446b9c21fb7c259c3523a',
        'inline_binding_identity':identity(binding),'native_source_files_byte_unchanged':17,
        'other_public_source_files_byte_unchanged':3,'all_20_source_SHA_and_size_pairs':expected,
        'all_other_workflow_steps_and_job_fields_equal_original_L5a':True,
        'current_needs_original_unchanged':True,'failure_preserving_always_steps_unchanged':always,
        'original_native_resource_source_ownership_clearance_and_reader_guards_unchanged':True,
        'source_install_process_seconds':90,'source_install_termination_grace_seconds':5,
        'source_socket_timeout_seconds':15,'host_deadline_seconds':2220,'job_timeout_minutes':40,
        'worker_wall_seconds':1800,'worker_peak_RSS_MiB':1536,
        'actual_independent_bash_blocks_parsed':shell_count,'actual_independent_Python_3_10_inline_blocks_parsed':python_count,
        'both_jobs_exact_installer_and_footer_identical':True,
        'standalone_extra_final_newline_is_explicitly_bound':True,
        'actual_offline_source_copy_and_original_footer_controls':controls,
        'original_L5_L5a_failures_and_interrupted_publication_history_preserved':True,
        'depends_on_unconfirmed_stage1_commit':False,'blocking_findings_in_reviewed_scope':[],
        'new_network_requests':0,'native_CAD_solver_or_L1_replay_executed':False,
        'native_or_geometry_clear_claimed':False,'Git_write_or_workflow_start':False,
        'publication_or_run_confirmed_by_this_review':False}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'review_identity':identity(args.output.read_bytes()),'blocking_findings':0,'offline_controls':3,'native_executed':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--envelope-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
