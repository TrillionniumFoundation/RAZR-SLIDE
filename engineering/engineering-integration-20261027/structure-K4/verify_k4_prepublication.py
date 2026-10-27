"""Pure K4 transport, embedded-code, guard-preservation and privacy controls.

No CAD imports, geometry reconstruction, FE, numerical solve or Git mutation.
The only large input is an already retained scientific ZIP read without copying.
"""
from __future__ import annotations
import ast
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
import yaml

HERE=Path(__file__).resolve().parent


def ident(path):
    raw=Path(path).read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def function(tree,name):
    return next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)


def dump(node):return ast.dump(node,include_attributes=False)


def heredocs(script):
    lines=script.splitlines();i=0;result=[]
    while i<len(lines):
        line=lines[i];match=re.search(r"<<'([^']+)'",line)
        if not match:i+=1;continue
        end=i+1
        while end<len(lines) and lines[end]!=match.group(1):end+=1
        assert end<len(lines),'unterminated actual generated heredoc'
        result.append((line,'\n'.join(lines[i+1:end])+'\n'));i=end+1
    return result


def main():
    report={'schema':'razr-K4-pure-prepublication-review-v1','checked_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'CAD_native_imports_or_operations':0,'new_network_downloads':0,'Git_mutations':0,'controls':[]}
    def passed(name,**details):report['controls'].append({'name':name,'passed':True,**details})
    py=[]
    for p in sorted(HERE.glob('*.py')):
        ast.parse(p.read_text(),filename=p.name,feature_version=(3,10));py.append(p.name)
    passed('all_sources_Python_3_10_AST',source_count=len(py),source_names=py)
    # Native 3.12-only original helper is not called from system-Python exporter.
    for n in ('prepare_k4_input.py','verify_k4_complete.py','export_k4_engineering.py'):
        assert 'file_digest' not in (HERE/n).read_text()
    passed('system_Python_3_10_hashing_has_no_hashlib_file_digest')
    original=(HERE/'original-supervise_k3full.py').read_text();new=(HERE/'supervise_k4.py').read_text()
    a,b=ast.parse(original),ast.parse(new)
    for name in ('resources','terminate_group'):assert dump(function(a,name))==dump(function(b,name))
    oa,ob=function(a,'observe'),function(b,'observe')
    strict=[n for n in ob.body if isinstance(n,ast.If) and 'additional bounded worker output exceeded' in dump(n)]
    assert len(strict)==1;ob.body.remove(strict[0]);assert dump(oa)==dump(ob)
    assert (HERE/'f1_common.py').read_bytes()==(HERE/'original-f1_common.py').read_bytes()
    for n in ('service-launch.py','host-cap.py'):
        assert (HERE/n).read_bytes()==(HERE/('original-'+n)).read_bytes()
    passed('original_resources_termination_owned_observation_AST_and_complete_common_lifecycle_bytes_preserved',
        supervisor_addition_only_one_stricter_output_stop=True)
    # The actual K4 Boolean entry point has no additional unguarded Boolean path.
    api=ast.parse((HERE/'k4_local_section_native_api.py').read_text())
    calls=[n for n in ast.walk(api) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('cut','intersect','fuse')]
    assert len(calls)==3 and not any(n.func.attr=='fuse' for n in calls)
    for call in calls:
        assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='operation'
            and any(child is call for child in ast.walk(n)) for n in ast.walk(api))
    assert len([n for n in ast.walk(api) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='difference'])==10
    passed('all_native_boolean_calls_route_through_preregistered_operation_counter',distinct_call_sites=len(calls),
        producer_maximum_calls=38,reader_maximum_calls=190)
    # Pure control of the empty-set dispatch only. These are sentinel objects,
    # not CAD shapes or a substitute for any native geometric observation.
    local_api=module(HERE/'k4_local_section_native_api.py','k4_empty_dispatch_pure_control')
    class Sentinel:
        def __init__(self,empty=False,invalid=False):self.empty,self.invalid=empty,invalid
        def isValid(self):return not self.invalid
        def Faces(self):return [] if self.empty else [None]
        def cut(self,other):
            assert not self.empty and not other.empty,'native subtraction dispatched for validated empty operand'
            return ('unchanged_native_dispatch_sentinel',self,other)
    def material(shape,empty=False):
        if shape.invalid:raise ValueError('synthetic invalid topology must remain an error')
        return ([],0.) if shape.empty else ([shape],1.)
    events=[];operations=[]
    owner=SimpleNamespace(p=SimpleNamespace(whole_material=material),check=lambda:None,
        event=lambda *a,**k:events.append((a,k)),operation=lambda label,fn:(operations.append(label),fn())[1])
    empty,positive=Sentinel(True),Sentinel()
    for a,b in ((empty,positive),(positive,empty),(empty,empty)):
        assert local_api.Output.difference(owner,'pure-empty-dispatch',a,b) is a
    assert len(events)==3 and not operations
    result=local_api.Output.difference(owner,'pure-positive-dispatch',positive,positive)
    assert result[0]=='unchanged_native_dispatch_sentinel' and len(operations)==1
    try:local_api.Output.difference(owner,'pure-invalid-dispatch',Sentinel(invalid=True),empty)
    except ValueError:pass
    else:raise AssertionError('unknown invalid material was incorrectly treated as empty')
    assert len(events)==3 and len(operations)==1
    passed('validated_empty_set_identity_dispatch_and_invalid_topology_negative_control',
        sentinel_cases=5,real_CAD_shapes_or_operations=0)
    workflow=HERE/'s4-k3-local-sections-k4-hosted.yml';w=yaml.safe_load(workflow.read_text());job=w['jobs']['local_sections'];embedded=[];bash_count=0
    assert len(w['jobs'])==1 and job['strategy']['max-parallel']==1 and len(job['strategy']['matrix']['pilot'])==1
    assert job['timeout-minutes']==60 and w['permissions']=={'contents':'read','actions':'read'}
    for i,s in enumerate(job['steps']):
        if 'uses' in s:assert re.fullmatch(r'[^@]+@[0-9a-f]{40}',s['uses'])
        if 'run' not in s:continue
        result=subprocess.run(['/bin/bash','-n'],input=s['run'],text=True,capture_output=True)
        assert result.returncode==0,(s['name'],result.stderr);bash_count+=1
        for command,body in heredocs(s['run']):
            if command.lstrip().startswith('cat >'):
                target=re.search(r'"([^\"]+)"',command).group(1);name=Path(target).name
                if name.endswith('.py'):ast.parse(body,filename='actual_workflow:'+name,feature_version=(3,10))
                elif name.endswith('.json'):json.loads(body)
                if name in {p.name for p in HERE.iterdir() if p.is_file()}:
                    assert body.encode()==(HERE/name).read_bytes(),('actual embedded bytes differ',name)
                embedded.append({'kind':'file','name':name,'bytes':len(body.encode()),'sha256':hashlib.sha256(body.encode()).hexdigest()})
            else:
                assert command.lstrip().startswith(('python3 -B -','python -B -'))
                ast.parse(body,filename='actual_workflow:step_'+str(i),feature_version=(3,10))
                embedded.append({'kind':'inline_python','step':i,'sha256':hashlib.sha256(body.encode()).hexdigest()})
        for match in re.finditer(r"\s-c\s+'([^']*)'",s['run']):
            ast.parse(match.group(1),filename='actual_workflow:-c',feature_version=(3,10))
            embedded.append({'kind':'python_c','step':i,'sha256':hashlib.sha256(match.group(1).encode()).hexdigest()})
    assert workflow.stat().st_size<500000
    assert any(s.get('with',{}).get('ref')=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560' for s in job['steps'])
    upload=next(s for s in job['steps'] if s.get('uses','').startswith('actions/upload-artifact@'))
    assert upload['if']=='always()' and 'engineering-export' in upload['with']['path'] and not upload['with'].get('include-hidden-files',False)
    passed('actual_generated_YAML_bash_and_embedded_Python_JSON_and_bytes',bash_steps=bash_count,embedded_records=embedded,workflow=ident(workflow))
    manifest=json.loads((HERE/'K4_FROZEN_SOURCES.json').read_text())
    for n,x in manifest['runtime_sources'].items():assert ident(HERE/n)==x
    passed('frozen_runtime_bundle_actual_byte_identities',runtime_source_count=len(manifest['runtime_sources']))
    # Test the actual new input function against the existing, already verified
    # original ZIP. This reads all bytes and creates no extracted model or ZIP.
    input_module=module(HERE/'prepare_k4_input.py','k4_input_pure_control')
    binding=json.loads((HERE/'K4_INPUT_BINDING.json').read_text());zip_path=HERE.parent/'K3FULL_stow_tabs_3_original.zip'
    observation=input_module.verify_original(zip_path,binding,None)
    assert observation['all_original_manifest_members_SHA_bytes_CRC_verified'] is True
    passed('actual_original_4764_member_ZIP_stream_replay_by_new_input_loader',observation=observation,no_extraction_or_new_download=True)
    bad=json.loads(json.dumps(binding));bad['ZIP']['sha256']='0'*64
    try:input_module.verify_original(zip_path,bad,None)
    except ValueError:pass
    else:raise AssertionError('wrong original ZIP digest accepted')
    passed('wrong_original_ZIP_digest_rejected_before_native')
    # Failure-only synthetic records test the publication boundary; they are not
    # geometric specimens, native results, or a model of the CAD implementation.
    exporter=module(HERE/'export_k4_engineering.py','k4_export_pure_control')
    with tempfile.TemporaryDirectory(prefix='razr-k4-pure-export-') as temp:
        root=Path(temp);case=root/'case';worker=case/'producer/worker';worker.mkdir(parents=True)
        sources=root/'sources';sources.mkdir();repo=root/'repo';repo.mkdir()
        (sources/'export_k4_engineering.py').write_bytes((HERE/'export_k4_engineering.py').read_bytes())
        raw=json.dumps({'schema':'razr-K4-worker-entry-failure-v1','execution_completed':False,
            'local_material_targets_all_matched':False,'evaluation_failures':[{'scope':'synthetic_transport_control_only','exception_type':'ValueError'}]})+'\n'
        (worker/'report.json').write_text(raw)
        private='private transport control at /home/unpublished/control?token=synthetic'
        (case/'native-errors-private.txt').write_text(private)
        assert exporter.export(case,sources,root/'out-good',repo)==0
        assert (root/'out-good/producer/worker/report.json').read_text()==raw
        scope=json.loads((root/'out-good/EXPORT_SCOPE.json').read_text())
        assert scope['raw_runtime_exported'] is False and scope['raw_runtime_durable_preservation_claimed'] is False
        assert scope['omitted_runtime_or_input_file_hashes'][0]['sha256']==hashlib.sha256(private.encode()).hexdigest()
        for p in (root/'out-good').rglob('*'):
            if p.is_file() and '/source/' not in str(p):assert private not in p.read_text()
        passed('original_failure_JSON_preserved_exactly_and_private_runtime_only_hashed')
        (worker/'bad-header.step').write_text("ISO-10303-21; FILE_NAME('/home/unpublished/private');")
        assert exporter.export(case,sources,root/'out-bad',repo)==2
        scope=json.loads((root/'out-bad/EXPORT_SCOPE.json').read_text())
        assert scope['available_allowed_scientific_originals_preserved'] is False and len(scope['scientific_export_problems'])==1
        assert not (root/'out-bad/producer/worker/bad-header.step').exists()
        assert (worker/'bad-header.step').is_file()
        passed('private_geometry_header_rejected_without_modifying_original_or_claiming_full_scientific_preservation')
    request=json.loads((HERE/'K4_PUBLIC_TREE_REQUEST.json').read_text())
    assert request['base_tree_sha']=='cdd9e2c41216201b6cd04dd610d45fde80499045'
    for row in request['tree_elements']:
        p=HERE/Path(row['path']).name
        assert row['mode']=='100644' and row['type']=='blob' and p.read_text()==row['content']
    passed('review_request_embeds_actual_current_file_bytes',path_count=len(request['tree_elements']))
    report.update(passed=True,limits_or_gates_relaxed=False,global_minimum_wall_qualified=False,physical_allowed_domain_proved=False,
        actual_native_results_exist=False,workflow_source=ident(workflow),frozen_source_bundle=ident(HERE/'K4_FROZEN_SOURCES.json'))
    (HERE/'K4_PREPUBLICATION_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'controls':len(report['controls']),'CAD_native_operations':0,'review':ident(HERE/'K4_PREPUBLICATION_REVIEW.json')}))


if __name__=='__main__':main()
