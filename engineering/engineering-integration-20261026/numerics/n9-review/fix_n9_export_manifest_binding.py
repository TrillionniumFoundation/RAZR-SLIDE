"""Narrow N9 manifest binding correction; preserve all previous frozen bytes."""
from pathlib import Path
import ast
import datetime
import gzip
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import time
import yaml

ROOT=Path(__file__).resolve().parent
OLD=ROOT/'N9-reconstructed'
OUT=ROOT/'N9-manifest-fixed'
SCI=ROOT/'N8-original-scientific'
REVIEW=ROOT.parent/'factory/review-n9/N9_ORIGINAL_REQUEST_INDEPENDENT_SOURCE_REVIEW.json'
OLD_REQUEST_SHA='b8f4d47bf9173cce528d3db6614756bab15e4b99edd894ee1d2f95253562e4e3'
OLD_EXPORTER_SHA='724840ff06c03c19cd368b37704de7aa5be5fed9f2341600dbaaa587cc0577da'
REVIEW_SHA='e47c26d9e912a82373b76096fe9c2631a9c1d5f66b936b68d7cb9fd7f9c66860'
BEFORE='if p.stat().st_size != 167280 or sha(p) != "f911ecc8f08fe78526af1be49ea2292f94ee49e64789f514359196d7875d01b2":'
AFTER='if p.stat().st_size != 166609 or sha(p) != "aa84d34b26847f308296809ff83002d32535a56a92eb09adcc7e42b571e88ee7":'
N8_ID={'bytes':166609,'sha256':'aa84d34b26847f308296809ff83002d32535a56a92eb09adcc7e42b571e88ee7'}
N7_ID={'bytes':167280,'sha256':'f911ecc8f08fe78526af1be49ea2292f94ee49e64789f514359196d7875d01b2'}
PREFIX='engineering/engineering-integration-20261026/numerics'

def sha(data):return hashlib.sha256(data).hexdigest()
def identity(path):
    b=path.read_bytes();return {'bytes':len(b),'sha256':sha(b)}
def save(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def row(path,repository_path):
    b=path.read_bytes()
    return {'repository_path':repository_path,'local_path':str(path),'bytes':len(b),'sha256':sha(b),'git_blob_sha':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def source_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

started=time.monotonic()
assert OUT.exists() is False,'fresh revision directory required; never overwrite frozen revision'
assert identity(OLD/'N9_TREE_REQUEST.json')=={'bytes':680704,'sha256':OLD_REQUEST_SHA}
assert identity(OLD/'export_n9_engineering.py')=={'bytes':25375,'sha256':OLD_EXPORTER_SHA}
assert identity(REVIEW)=={'bytes':6044,'sha256':REVIEW_SHA}
assert identity(SCI/'EXPORT_MANIFEST.json')==N8_ID
assert identity(SCI/'frozen/EXPORT_MANIFEST.json')==N7_ID
request=json.loads((OLD/'N9_TREE_REQUEST.json').read_text())
assert request['base_tree_sha']=='cdd9e2c41216201b6cd04dd610d45fde80499045'
assert len(request['tree_elements'])==13
OUT.mkdir()
for item in request['tree_elements']:
    path=OLD/Path(item['path']).name
    assert path.read_bytes()==item['content'].encode()
    shutil.copyfile(path,OUT/path.name)

oldexport=(OLD/'export_n9_engineering.py').read_text()
assert oldexport.count(BEFORE)==1 and AFTER not in oldexport
newexport=oldexport.replace(BEFORE,AFTER)
(OUT/'export_n9_engineering.py').write_text(newexport)
newexportsha=sha(newexport.encode())
workflow=(OLD/'s4-panel-n9-hosted.yml').read_text()
assert workflow.count(BEFORE)==1 and workflow.count(OLD_EXPORTER_SHA)==1
newworkflow=workflow.replace(BEFORE,AFTER).replace(OLD_EXPORTER_SHA,newexportsha)
assert newworkflow.replace(AFTER,BEFORE).replace(newexportsha,OLD_EXPORTER_SHA)==workflow
(OUT/'s4-panel-n9-hosted.yml').write_text(newworkflow)
changed=[];source_identities=[]
for item in request['tree_elements']:
    name=Path(item['path']).name
    before=identity(OLD/name);after=identity(OUT/name)
    if before!=after:changed.append(item['path'])
    source_identities.append({'path':item['path'],'before':before,'after':after,'bytes_unchanged':before==after})
    item['content']=(OUT/name).read_text()
assert changed==[PREFIX+'/n9/export_n9_engineering.py','.github/workflows/s4-panel-n9-hosted.yml']
raw=(json.dumps(request,ensure_ascii=False,separators=(',',':'))+'\n').encode()
(OUT/'N9_MANIFEST_FIXED_TREE_REQUEST.json').write_bytes(raw)
(OUT/'N9_MANIFEST_FIXED_TREE_REQUEST.json.gz').write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))

# Only standard-library exporter code is imported; no producer/reader numerical
# code, sparse matrix, NPY, or native scientific library is imported or executed.
oldmodule=source_module(OLD/'export_n9_engineering.py','old_n9_exporter_binding_control')
newmodule=source_module(OUT/'export_n9_engineering.py','new_n9_exporter_binding_control')
controls=[]
controlroot=OUT/'manifest-regression';controlroot.mkdir()
def control(name,module,input_path,should_accept,expected_input):
    case=controlroot/name/'case';case.mkdir(parents=True)
    (case/'frozen').mkdir()
    shutil.copyfile(input_path,case/'frozen/EXPORT_MANIFEST.json')
    assert identity(case/'frozen/EXPORT_MANIFEST.json')==expected_input
    output=controlroot/name/'export'
    rec={'name':name,'input_manifest_identity':expected_input,'expected_manifest_gate_acceptance':should_accept,
         'scope':'manifest-only partial-case exporter regression; no mathematical candidate or complete-input qualification',
         'exporter_source_identity':identity(Path(module.__file__)),'native_execution':False}
    try:
        module.export(case,output)
    except ValueError as exc:
        rec.update(actual_manifest_gate_acceptance=False,error_type=type(exc).__name__,failure_message=str(exc))
        assert str(exc)=='original N8 scientific manifest differs'
    else:
        rec['actual_manifest_gate_acceptance']=True
        manifest=json.loads((output/'EXPORT_MANIFEST.json').read_text())
        assert identity(output/'frozen/EXPORT_MANIFEST.json')==expected_input
        assert manifest['copied']['frozen/EXPORT_MANIFEST.json']=={**expected_input,'original_bytes':True}
        actual=manifest['scientific_preservation_actual']
        assert actual['original_source_manifest_identity_verified'] is True
        assert actual['all_22_selected_complete_inputs_identity_verified'] is False
        assert actual['all_started_full_candidates_all5_fields_and_residuals_recoverable'] is False
        rec['export_manifest_identity']=identity(output/'EXPORT_MANIFEST.json')
        rec['incomplete_input_state_truthfully_retained']=True
    assert rec['actual_manifest_gate_acceptance']==should_accept
    rec['expected_control_observed']=True
    controls.append(rec)

control('old_exporter_rejects_actual_N8',oldmodule,SCI/'EXPORT_MANIFEST.json',False,N8_ID)
control('old_exporter_accepts_stale_N7_manifest_only',oldmodule,SCI/'frozen/EXPORT_MANIFEST.json',True,N7_ID)
control('corrected_exporter_accepts_actual_N8',newmodule,SCI/'EXPORT_MANIFEST.json',True,N8_ID)
control('corrected_exporter_rejects_stale_N7',newmodule,SCI/'frozen/EXPORT_MANIFEST.json',False,N7_ID)
corrupt=controlroot/'same_size_modified_N8_manifest.json'
data=(SCI/'EXPORT_MANIFEST.json').read_bytes();assert data.endswith(b'\n')
corrupt.write_bytes(data[:-1]+b' ');assert corrupt.stat().st_size==N8_ID['bytes']
control('corrected_exporter_rejects_same_size_changed_N8',newmodule,corrupt,False,identity(corrupt))
regression={'schema':'razr-N9-export-manifest-binding-regression-v1','completed':True,'actual_original_N8_manifest':N8_ID,'actual_original_N7_manifest':N7_ID,'controls':controls,'all_expected_results_observed':True,'native_executions':0,'large_array_reads':0,'old_request_source_or_actual_scientific_records_modified':False,'old_incorrect_export_binding_reproduced':True}
save(OUT/'N9_MANIFEST_BINDING_REGRESSION.json',regression)

decoded=yaml.safe_load(newworkflow)
runs=[x for job in decoded['jobs'].values() for x in job['steps'] if 'run' in x]
shell_count=0;embedded_count=0;inline_count=0
for step in runs:
    checked=subprocess.run(['/bin/bash','-n'],input=step['run'],text=True,capture_output=True)
    assert checked.returncode==0,(step['name'],checked.stderr)
    shell_count+=1
    lines=step['run'].splitlines(keepends=True);i=0
    while i<len(lines):
        match=re.search(r"<<'([^']+)'",lines[i])
        if not match:i+=1;continue
        delimiter=match.group(1);j=i+1
        while j<len(lines) and lines[j].rstrip('\n')!=delimiter:j+=1
        assert j<len(lines)
        body=''.join(lines[i+1:j]);name=re.search(r'cat > "\$HOST_ROOT/([^"/]+)"',lines[i])
        if delimiter.startswith('N9_SOURCE_'):
            assert name and body.encode()==(OUT/name.group(1)).read_bytes()
            assert f"printf '{sha(body.encode())}  %s\\n' \"$HOST_ROOT/{name.group(1)}\" | sha256sum --check --strict" in step['run']
            embedded_count+=1
        elif lines[i].startswith('python3 -B - '):
            ast.parse(body);inline_count+=1
        i=j+1
assert (shell_count,embedded_count,inline_count)==(12,12,5)
for item in request['tree_elements']:
    name=Path(item['path']).name
    if name.endswith('.py'):ast.parse((OUT/name).read_text())
assert identity(OLD/'N9_TREE_REQUEST.json')=={'bytes':680704,'sha256':OLD_REQUEST_SHA}
assert identity(OLD/'export_n9_engineering.py')=={'bytes':25375,'sha256':OLD_EXPORTER_SHA}
assert identity(REVIEW)=={'bytes':6044,'sha256':REVIEW_SHA}
receipt={'schema':'razr-N9-export-manifest-binding-correction-v1','completed':True,
 'recorded_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'corrected_local_request_not_published_or_executed',
 'blocking_finding':'N9_EXPORT_FROZEN_MANIFEST_STILL_N7',
 'independent_original_failed_review':identity(REVIEW),
 'old_request_preserved':identity(OLD/'N9_TREE_REQUEST.json'),
 'old_exporter_preserved':identity(OLD/'export_n9_engineering.py'),
 'prior_static_review_limitation':'Syntax, embedded byte identity, pure numerical controls and scalar eligibility checks did not exercise the actual input-manifest gate. Its earlier validation does not remove this later semantic block.',
 'old_binding':N7_ID,'correct_binding':N8_ID,
 'exact_source_expression_before':BEFORE,'exact_source_expression_after':AFTER,
 'changed_repository_paths':changed,'all_source_identities':source_identities,
 'new_request_identity':identity(OUT/'N9_MANIFEST_FIXED_TREE_REQUEST.json'),
 'new_gzip_request_identity':identity(OUT/'N9_MANIFEST_FIXED_TREE_REQUEST.json.gz'),
 'actual_regression_receipt':identity(OUT/'N9_MANIFEST_BINDING_REGRESSION.json'),
 'workflow_change_only_exporter_literal_binding_and_corresponding_embedded_source_hash':True,
 'worker_reader_strategy_contract_tests_or_original_acceptance_changed':False,
 'all_11_other_published_files_byte_identical':True,
 'original_180s_AS_shared_memory_output_and_finite_limits_unchanged':True,
 'bash_syntax_steps_checked':shell_count,'embedded_source_files_byte_checked':embedded_count,'inline_Python_AST_checked':inline_count,
 'native_execution':False,'large_array_read':False,'Git_write_or_Actions_start':False,
 'original_numerical_five_passed':False,'H_frame_restore_executed':False,
 'elapsed_seconds':time.monotonic()-started}
save(OUT/'N9_MANIFEST_BINDING_CORRECTION_RECEIPT.json',receipt)
source_map={'schema':'razr-small-engineering-integration-map-v1',
 'scope':'Corrected unpublished N9 source revision. Prior b8f4d47b request and 724840ff exporter remain historical rejected publication candidates.',
 'entries':[row(OUT/Path(item['path']).name,item['path']) for item in request['tree_elements']],
 'base_tree_sha':request['base_tree_sha'],'request_identity':identity(OUT/'N9_MANIFEST_FIXED_TREE_REQUEST.json'),
 'supersedes_old_publication_request_sha256':OLD_REQUEST_SHA,'old_request_deleted_or_rewritten':False,
 'publication_performed':False,'native_execution':False}
save(OUT/'N9_MANIFEST_FIXED_SOURCE_SAFE_MAP.json',source_map)
evidence=[row(OUT/name,PREFIX+'/n9-review/'+name) for name in ['N9_MANIFEST_BINDING_REGRESSION.json','N9_MANIFEST_BINDING_CORRECTION_RECEIPT.json']]
evidence.append(row(Path(__file__),PREFIX+'/n9-review/'+Path(__file__).name))
evidence.append(row(REVIEW,PREFIX+'/n9-review/'+REVIEW.name))
for name in ['old_exporter_accepts_stale_N7_manifest_only','corrected_exporter_accepts_actual_N8']:
    evidence.append(row(controlroot/name/'export/EXPORT_MANIFEST.json',PREFIX+'/n9-review/manifest-regression/'+name+'/EXPORT_MANIFEST.json'))
save(OUT/'N9_MANIFEST_CORRECTION_EVIDENCE_SAFE_MAP.json',{'schema':'razr-small-engineering-integration-map-v1','entries':evidence,'scope':'Actual old binding failure, corrected binding controls and narrow source correction; no native numerical execution'})
print(json.dumps({'completed':True,'new_request':identity(OUT/'N9_MANIFEST_FIXED_TREE_REQUEST.json'),'new_exporter':identity(OUT/'export_n9_engineering.py'),'new_workflow':identity(OUT/'s4-panel-n9-hosted.yml'),'regression':identity(OUT/'N9_MANIFEST_BINDING_REGRESSION.json'),'correction_receipt':identity(OUT/'N9_MANIFEST_BINDING_CORRECTION_RECEIPT.json'),'source_map':identity(OUT/'N9_MANIFEST_FIXED_SOURCE_SAFE_MAP.json'),'evidence_map':identity(OUT/'N9_MANIFEST_CORRECTION_EVIDENCE_SAFE_MAP.json'),'native':False}))
