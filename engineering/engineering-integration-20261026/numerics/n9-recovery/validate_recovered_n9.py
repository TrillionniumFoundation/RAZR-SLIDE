"""Static, pure-control and byte-identity audit of recovered N9; no native solve."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import time
import yaml

ROOT=Path(__file__).resolve().parent
N9=ROOT/'N9-reconstructed'
N8=ROOT/'N8-published-source'
SCI=ROOT/'N8-original-scientific'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ident(path):
    raw=path.read_bytes()
    return {'bytes':len(raw),'sha256':sha(raw)}
def funcs(source):
    return {x.name:ast.dump(x,include_attributes=False) for x in ast.parse(source).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}

started=time.perf_counter()
workflow=yaml.safe_load((N9/'s4-panel-n9-hosted.yml').read_text())
assert workflow['permissions']=={'contents':'read','actions':'read'}
assert workflow['env']['S4']=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
assert workflow['on']['push']['branches']==['diagnostic/panel-coordinate-n9-20261026']
steps=[x for j in workflow['jobs'].values() for x in j['steps']]
assert next(x for x in steps if x['name'].startswith('Checkout'))['with']['ref']==workflow['env']['S4']
runs=[x for x in steps if 'run' in x]
shells=[];embedded=[];inline=[];harness=[]
for step in runs:
    check=subprocess.run(['/bin/bash','-n'],input=step['run'],text=True,capture_output=True)
    assert check.returncode==0,(step['name'],check.stderr)
    shells.append({'step':step['name'],'bash_n_exit_code':check.returncode})
    lines=step['run'].splitlines(keepends=True)
    i=0
    while i<len(lines):
        line=lines[i];match=re.search(r"<<'([^']+)'",line)
        if not match:i+=1;continue
        delimiter=match.group(1);j=i+1
        while j<len(lines) and lines[j].rstrip('\n')!=delimiter:j+=1
        assert j<len(lines),(step['name'],delimiter)
        body=''.join(lines[i+1:j]); raw=body.encode()
        source=re.search(r'cat > "\$HOST_ROOT/([^"/]+)"',line)
        if source:
            name=source.group(1)
            if delimiter.startswith('N9_SOURCE_'):
                assert raw==(N9/name).read_bytes(),name
                embedded.append({'name':name,'bytes':len(raw),'sha256':sha(raw)})
                assert f"printf '{sha(raw)}  %s\\n' \"$HOST_ROOT/{name}\" | sha256sum --check --strict" in step['run']
            elif name in ('host-cap.py','service-launch.py'):
                ast.parse(body)
                harness.append({'name':name,'bytes':len(raw),'sha256':sha(raw)})
        elif re.match(r'python3 -B - ',line):
            ast.parse(body)
            inline.append({'step':step['name'],'delimiter':delimiter,'bytes':len(raw),'sha256':sha(raw)})
        i=j+1
assert (len(shells),len(embedded),len(inline),len(harness))==(12,12,5,2)
assert harness==[{'name':'host-cap.py','bytes':3336,'sha256':'0002ceb40c125b0ee26343a291a2c0011c3ed128f86b7f7959db2454a7974f0b'},{'name':'service-launch.py','bytes':39288,'sha256':'656f11eb363841ff28d10e60587c609b9f69a5b59edbb5931c95f4987a1bc3b3'}]
python_sources=[]
for p in sorted(N9.glob('*.py')):
    ast.parse(p.read_text());python_sources.append({'name':p.name,**ident(p)})
assert len(python_sources)==6
before=funcs((N8/'probe_n8_coordinates.py').read_text());after=funcs((N9/'probe_n9_coordinates.py').read_text())
unchanged=['qpack','exact_product','ordered_row_dot','acceptance_conditions','select_unaffected_anchor','ExactCache','array_sha','residual_record']
for name in unchanged:assert before[name]==after[name],name
helper=SCI/'source/S4/engineering/engineering-integration-20261025/numerics/probe_original_actions.py'
assert ident(helper)['sha256']=='1f8334a1dda34a4101662ccdbd14c2db0bb77b8a3e080b5f5ec74d918955a2c6'
original=funcs(helper.read_text())
for name in ('array_sha','residual_record'):assert original[name]==after[name]
oldworker=(N8/'probe_n8_coordinates.py').read_text();newworker=(N9/'probe_n9_coordinates.py').read_text()
oldexpr='"eligible_for_full_candidate": bool(ratio <= LIMIT and abs(exact_after) <= abs(exact_before))'
newexpr='"eligible_for_full_candidate": bool(ratio <= LIMIT)'
assert oldworker.count(oldexpr)==1 and newworker.count(newexpr)==1
reader=(N9/'readback_n9_coordinates.py').read_text()
assert 'eligible=ratio<=LIMIT' in reader and 'eligible=ratio<=LIMIT and abs(after)<=abs(exact_before)' not in reader
for node in ast.walk(ast.parse(reader)):
    if isinstance(node,ast.ImportFrom):assert node.module!='probe_n9_coordinates'
    if isinstance(node,ast.Import):assert all(x.name!='probe_n9_coordinates' for x in node.names)
contract={}
for node in ast.parse((N9/'n9_contract.py').read_text()).body:
    if isinstance(node,ast.Assign):
        try:value=ast.literal_eval(node.value)
        except (ValueError,TypeError):continue
        for target in node.targets:
            if isinstance(target,ast.Name):contract[target.id]=value
assert contract['FIXED']==(0,1,2,13,14,8)
assert all(contract[k]==v for k,v in {'LIMIT':1e-7,'MAX_FULL':96,'MAX_SCALAR':8192,'MAX_ROW_SUPPORT':256,'MAX_CACHE_ROWS':4096,'MAX_EXACT_TERMS':1000000,'MAX_READER_EXACT_TERMS':2000000,'MAX_FRACTION_BITS':4096,'AS_BYTES':4831838208,'OUTPUT_BYTES':1610612736,'WALL_SECONDS':180,'BASE_FIELD_SHA':'289153703ed68fd9b8161858195865a088325de58b0d66395f16844787c8420a','K_SHA':'80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb','C_SHA':'9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f'}.items())
api=json.loads((N9/'S4_IMMUTABLE_API_IDENTITY_RESET_RECOVERY.json').read_text())['safe_fields']
assert api['sha']==contract['S4'] and api['tree']==contract['S4_TREE']=='cdd9e2c41216201b6cd04dd610d45fde80499045'
frozen=json.loads((N9/'N9_FROZEN_INPUTS.json').read_text());manifest=json.loads((SCI/'EXPORT_MANIFEST.json').read_text())
assert len(frozen['members'])==22 and sum(x['bytes'] for x in frozen['members'].values())==382222748
for name,item in frozen['members'].items():assert item==manifest['exported_files'][name]
recovered=json.loads((N9/'N9_RESET_RECONSTRUCTION_RECEIPT.json').read_text());assert recovered['all_retained_pre_reset_identities_match'] is True
small=json.loads((N9/'N9_RECOVERY_SMALL_CONTRACT_RESULTS.json').read_text())
assert small['tests_run']==9 and small['passed'] is True and small['historical_S4_test_count_modified'] is False
request=json.loads((N9/'N9_TREE_REQUEST.json').read_text())
assert len(request['tree_elements'])==13 and request['base_tree_sha']==contract['S4_TREE']
for item in request['tree_elements']:
    assert item['content'].encode()==(N9/Path(item['path']).name).read_bytes()
    assert item['mode']=='100644' and item['type']=='blob'
uploads=[x for x in steps if x.get('uses','').startswith('actions/upload-artifact@')]
assert len(uploads)==2 and all(x.get('if')=='always()' for x in uploads)
assert all('include-hidden-files' not in x['with'] for x in uploads)
assert {x['with']['path'] for x in uploads}=={'${{ runner.temp }}/razr-s4-panel-n9-dd7def6e/engineering-export','${{ runner.temp }}/razr-s4-panel-n9-dd7def6e/engineering-summary'}
summary=next(x['run'] for x in runs if 'N9_SMALL_SUMMARY' in x['run'])
assert "manifest.get('scientific_preservation_actual',{}).get(key)" in summary
assert 'all_scalar_screens_and_all_full_arrays_are_in_complete_scientific_artifact' not in summary
strategy=json.loads((N9/'N9_STRATEGY.json').read_text())
assert strategy['capacity']['worker_wall_seconds']==180 and strategy['capacity']['reader_wall_seconds']==180
assert strategy['time_basis']['worker_planning_seconds']<180 and strategy['time_basis']['reader_planning_seconds']<180
assert strategy['qualification_and_release']['H_frame_restore_require_true_all_five_pass_first'] is True
result={'schema':'razr-N9-reset-recovery-static-review-v1','completed':True,'review_scope':'new actual byte, AST, bash syntax and existing nine pure stdlib controls after runtime reset; no native solve','old_RAM_or_old_disk_recovered':False,'all_13_published_files_and_raw_request_match_retained_frozen_SHA':True,'S4_identity_confirmed_against_official_commit_tree_API':True,'source_identity_receipt':ident(N9/'S4_IMMUTABLE_API_IDENTITY_RESET_RECOVERY.json'),'actual_N8_scientific_all87_recovery_receipt':ident(ROOT/'N8_RECOVERED_ORIGINAL_SCIENTIFIC_READBACK.json'),'reconstruction_receipt':ident(N9/'N9_RESET_RECONSTRUCTION_RECEIPT.json'),'small_control_receipt':ident(N9/'N9_RECOVERY_SMALL_CONTRACT_RESULTS.json'),'pure_controls_passed':9,'original_S4_historical_test_count_modified':False,'bash_run_steps':shells,'decoded_embedded_source_files':embedded,'decoded_harnesses':harness,'inline_Python_AST':inline,'standalone_Python_AST':python_sources,'unchanged_N8_worker_AST_definitions':unchanged,'original_S4_residual_record_and_array_sha_AST_identical':True,'independent_reader_imports_producer_numerical_code':False,'same_original_K_C_free_fixed_directions_RHS_field_identity_contract':True,'frozen_input_count':22,'frozen_input_bytes':382222748,'numerical_eligibility_change_only':'predicted original target-row float64 gate now permits a complete trial regardless of target-only exact nonincrease; original complete global exact nonincrease, strict violating-row-count decrease and all five native gates remain mandatory','old_N8_rejections_rewritten':False,'original_worker_reader_limits_changed':False,'worker_planning_seconds':strategy['time_basis']['worker_planning_seconds'],'reader_planning_seconds':strategy['time_basis']['reader_planning_seconds'],'planning_not_runtime_or_convergence_guarantee':True,'scientific_upload_scopes':[x['with']['path'] for x in uploads],'summary_completeness_derived_from_actual_manifest':True,'raw_runtime_or_author_email_exported':False,'new_native_executions':0,'H_frame_restore_executed':False,'elapsed_seconds':time.perf_counter()-started}
raw=(json.dumps(result,indent=2)+'\n').encode();(N9/'N9_RECOVERY_STATIC_REVIEW.json').write_bytes(raw)
print(json.dumps({'completed':True,'bytes':len(raw),'sha256':sha(raw),'pure_controls':9,'bash_steps':12,'embedded_sources':12,'inline_python':5,'native':False}))
