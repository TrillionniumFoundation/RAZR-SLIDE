"""Export-only V4a freeze; preserve every native and lifecycle command byte."""
from pathlib import Path
import argparse,ast,copy,hashlib,json,re,subprocess
import yaml

HERE=Path(__file__).resolve().parent
S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
TREE='cdd9e2c41216201b6cd04dd610d45fde80499045'
ORIGINAL=('run_capacity_v4.py','supervise_capacity_v4.py','capacity_stage_v4.py','full_slide_api_v4.py',
    'envelope_v2.py','correlated_v3.py','test_l2_native.py','frozen_key_factory_adapter.py',
    'K1_BINDING.json','read_capacity_v4.py','export_capacity_v4.py','check_capacity_stage.py','README.md')
FILES=ORIGINAL+('test_export_capacity_v4a.py',)


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original-v4',type=Path,required=True)
    ap.add_argument('--baseline-repo',type=Path,required=True)
    args=ap.parse_args();old=args.original_v4
    original_request=old/'V4_PUBLIC_TREE_REQUEST.json'
    assert sha(original_request.read_bytes())=='6c1c81efc46a8d78bb545f09c793d33bb7e79c6d4ed3c4fe429fe738e2954e33'
    original_workflow=old/'s4-k1-v4-capacity-hosted.yml'
    assert sha(original_workflow.read_bytes())=='4b85c2b9d4c9f526504837340c9b88c22e19adcb935c1a52c3d03ffffddb6160'
    sources={name:(HERE/name).read_text() for name in FILES}
    expected={name:{'sha256':sha(value.encode()),'bytes':len(value.encode())} for name,value in sources.items()}
    preserved={}
    for name in ORIGINAL:
        if name not in ('export_capacity_v4.py','README.md'):
            assert (old/name).read_bytes()==(HERE/name).read_bytes(),name
            preserved[name]=expected[name]
    for name,value in sources.items():
        if name.endswith('.py'):ast.parse(value,feature_version=(3,10))
    source_analysis={
        'schema':'razr-V4-export-label-source-review-v1',
        'original_commit':'6ff44ea6abe1fef248ccc86396dc0d072e856aef',
        'original_tree':'1a86baa388af839085c3cbc8ac3f2c8771ad55a2',
        'original_workflow_run_id':40279094567,
        'original_request_sha256':sha(original_request.read_bytes()),
        'original_exporter_sha256':sha((old/'export_capacity_v4.py').read_bytes()),
        'source_review_found_label_mismatch':True,
        'real_producer_example':'call-000001-initial-region-0-Common.brep',
        'original_allowlist_accepts_example':False,'corrected_exact_label_allowlist_accepts_example':True,
        'followup_Common_retention_trigger':'nonclear affine frame after strict Common exceeds original sum gate, or caught evaluation failure with an available rejected region',
        'not_every_native_call_creates_followup_Common':True,
        'runtime_export_failure_observed_at_this_freeze':True,
        'actual_first_run_receipt':'V4_FIRST_RUN_EXPORT_FAILURE.json',
        'original_run_was_not_mutated_or_cancelled':True,
        'original_upload_scope':'publish only; partial copies may survive an export assertion; private worker directory is not uploaded',
        'native_or_geometry_result_inferred_from_export_risk':False,
        'native_sources_preserved_byte_for_byte':preserved,
        'native_original_guards_and_limits_changed':False,'raw_runtime_collections_exported':False}
    (HERE/'V4_EXPORT_LABEL_SOURCE_REVIEW.json').write_text(json.dumps(source_analysis,indent=2)+'\n')
    w=yaml.safe_load(original_workflow.read_text());before=copy.deepcopy(w)
    w['name']='V4a exact scientific export labels; unchanged K1 capacity native worker'
    w['on']={'push':{'branches':['diagnostic/s4-k1-v4a-capacity-20261026']},'workflow_dispatch':None}
    w['concurrency']={'group':'v4a-capacity-${{ github.ref }}','cancel-in-progress':False}
    job=w['jobs']['replay'];job['name']='V4a original 17-pair capacity worker with exact retained-Common export'
    prep=job['steps'][2]['run']
    for name in ORIGINAL:
        marker='V4_'+re.sub('[^A-Z0-9]','_',name.upper())
        start='cat > "$HOST_ROOT/v4/'+name+'" <<\''+marker+'\'\n'
        first,sep,rest=prep.partition(start);assert sep,name
        body,sep,last=rest.partition('\n'+marker+'\n');assert sep,name
        assert (body+'\n').encode()==(old/name).read_bytes(),name
        prep=first+start+sources[name]+marker+'\n'+last
    marker='V4A_EXPORT_TEST'
    extra='cat > "$HOST_ROOT/v4/test_export_capacity_v4a.py" <<\''+marker+'\'\n'+sources['test_export_capacity_v4a.py']+marker+'\n'
    check_start="python3 -B - <<'V4_SOURCE_CHECK'\n"
    first,sep,rest=prep.partition(check_start);assert sep
    body,sep,last=rest.partition('\nV4_SOURCE_CHECK\n');assert sep
    lines=body.splitlines();matches=[i for i,line in enumerate(lines) if line.startswith('expected=')]
    assert len(matches)==1
    prior=ast.literal_eval(lines[matches[0]].split('=',1)[1])
    for name,row in prior.items():assert sha((old/name).read_bytes())==row['sha256']
    lines[matches[0]]='expected='+repr(expected)
    prep=first+extra+check_start+'\n'.join(lines)+'\nV4_SOURCE_CHECK\n'+last
    prep+='python3 -B "$HOST_ROOT/v4/test_export_capacity_v4a.py"\n'
    job['steps'][2]['run']=prep
    job['steps'][-1]['with']['name']='S4-V4a-capacity17-${{ github.run_id }}-${{ github.run_attempt }}'
    for i,(a,b) in enumerate(zip(before['jobs']['replay']['steps'],job['steps'])):
        if i not in (2,len(job['steps'])-1):assert a==b,i
    assert job['timeout-minutes']==before['jobs']['replay']['timeout-minutes']==40
    for step in job['steps']:
        if 'run' in step:subprocess.run(['bash','-n'],input=step['run'].encode(),check=True)
    workflow=HERE/'s4-k1-v4a-capacity-hosted.yml'
    workflow.write_text('# V4a changes scientific export only; native sources, commands and original gates retained.\n'+yaml.safe_dump(w,sort_keys=False,width=110))
    subprocess.run(['python3','-B',str(HERE/'validate_workflow_freeze.py'),'--workflow',str(workflow),
        '--baseline-repo',str(args.baseline_repo),'--source-dir',str(HERE),'--label','V4',
        '--out',str(HERE/'V4A_STATIC_CHECK.json')],check=True)
    subprocess.run(['python3','-B',str(HERE/'test_export_capacity_v4a.py')],check=True)
    plan={
        'schema':'razr-V4a-export-only-publication-plan-v1','functional_commit':S4,'functional_tree':TREE,
        'branch':'diagnostic/s4-k1-v4a-capacity-20261026','source_review_record':'V4_EXPORT_LABEL_SOURCE_REVIEW.json',
        'sources':expected,'native_sources_preserved':preserved,'workflow_sha256':sha(workflow.read_bytes()),
        'native_worker_commands_identical_to_V4':True,'all_other_steps_except_source_embedding_and_artifact_name_identical':True,
        'original_worker_wall_seconds':1800,'original_worker_RSS_MiB':1536,'original_shared_unreclaimable_GiB':6.8,
        'original_startup_disk_MiB':200,'original_runtime_disk_MiB':100,'original_startup_additional_memory_MiB':1536,
        'original_priority_pairs':17,'original_pair_slots':11781,'original_volume_gate_mm3':1e-7,
        'export_regression_tests_actually_passed':4,'native_execution_of_this_freeze_done':False,
        'runtime_export_failure_in_first_V4_run_observed':True,'raw_runtime_exported':False,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    (HERE/'V4A_PUBLICATION_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    names=FILES+('V4_EXPORT_LABEL_SOURCE_REVIEW.json','V4_FIRST_RUN_EXPORT_FAILURE.json',
                 'V4_FIRST_RUN_INDEPENDENT_RECORD_CHECK.json','V4A_STATIC_CHECK.json','V4A_PUBLICATION_PLAN.json',
                 'build_v4a_workflow.py','validate_workflow_freeze.py')
    elements=[{'path':'engineering/engineering-integration-20261026/capacity-V4a/'+name,
        'mode':'100644','type':'blob','content':(HERE/name).read_text()} for name in names]
    elements.append({'path':'.github/workflows/s4-k1-v4a-capacity.yml','mode':'100644','type':'blob','content':workflow.read_text()})
    request=HERE/'V4A_PUBLIC_TREE_REQUEST.json'
    request.write_text(json.dumps({'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE',
        'base_tree_sha':TREE,'tree_elements':elements},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'request_sha256':sha(request.read_bytes()),'request_bytes':request.stat().st_size,
        'workflow_sha256':plan['workflow_sha256'],'tree_paths':len(elements),'preserved_source_files':len(preserved)}))


if __name__=='__main__':main()
