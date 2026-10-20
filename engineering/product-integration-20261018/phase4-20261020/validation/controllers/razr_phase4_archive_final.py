"""Archive identified completed EP4 experiments; run after every reader exits."""
from pathlib import Path
import datetime, gzip, hashlib, json, subprocess

R=Path('/home/qian-qi/RAZR-SLIDE-product-integration-20261018')
E=Path('/home/qian-qi/.local/share/razr-slide-evidence/product-followup-20261020-phase4')
P=Path('engineering/product-integration-20261018/phase4-20261020')
N='9a8307fe4bd4163b53515698fb12cfc0a8cc27e7'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==N
assert not subprocess.check_output(['git','status','--porcelain'],cwd=R,text=True)
native=[]
readbacks=[]
for prefix in ['predock','open-stow']:
    p=E/(prefix+'-9a8307f')/'native/native-report.json'
    n=read(p); v=read(E/('readback-'+prefix+'-9a8307f')/'report.json')
    assert n['source_commit']==N and n['native_checks_executed'] and n['source_bytes_unchanged']
    assert all(sha(R/k)==h for k,h in n['source_sha256'].items())
    assert v['native_source_commit']==N and v['execution_completed'] and v['declared_readback_checks_passed']
    assert v['all_assembly_parts_have_metric_comparison'] and v['native_report']['sha256']==sha(p)
    assert all(sha(k)==i['sha256'] for k,i in v['retained_input_files'].items())
    native.append(n);readbacks.append(v)
unit=read(E/'unit-9a8307f/report.json')
assert unit['base_commit']==N and unit['tests_run']==137 and unit['passed'] and unit['source_bytes_unchanged']
assert len(unit['suite_results'])==4
assert all(x['passed'] and x['failures']==x['errors']==x['skipped']==0 for x in unit['suite_results'])
small=read(E/'small-native-9a8307f/native-regression/native-regressions.json')
assert small['source_commit']==N and small['source_bytes_unchanged'] and small['native_regressions_passed'] and len(small['cases'])==7
a=read(E/'a-head-relief-9a8307f/report.json')
assert a['local_declared_geometry_checks_passed'] and a['material_accounting']['added_mm3']==0
assert a['head_Common_mm3']['revised']==0 and not a['baseline_EP4_source_or_assemblies_modified']
for label in ['unit','small-native','predock','open-stow','readback-predock','readback-open-stow','a-head-relief']:
    x=read(E/(label+'-execution-9a8307f')/'execution.json')
    assert x['source_commit']==N and x['exit_code']==0 and x['execution_identity_preserved']

items=[]
def archive(source,relative):
    source=Path(source); raw=source.read_bytes();rel=Path(relative)
    compressed=rel.parts[0]!='actions' and (rel.suffix.lower()=='.step' or rel.name in ('report.json','native-report.json') or (rel.suffix=='.json' and len(raw)>65536))
    data=gzip.compress(raw,mtime=0) if compressed else raw
    if compressed:rel=Path(str(rel)+'.gz')
    dest=R/P/rel
    assert not dest.exists(),str(dest)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    assert dest.read_bytes()==data
    if compressed:assert gzip.decompress(data)==raw
    item={'path':(P/rel).as_posix(),'bytes':len(data),'sha256':sha(dest),
          'original_path':str(source),'original_bytes':len(raw),'original_sha256':hashlib.sha256(raw).hexdigest(),'gzip':compressed}
    items.append(item);return item['path']
def tree(source,relative):
    for p in sorted(Path(source).rglob('*')):
        if p.is_file():archive(p,Path(relative)/p.relative_to(source))
for label in ['predock','open-stow']:
    tree(E/(label+'-9a8307f')/'native',Path('native')/label)
    tree(E/('readback-'+label+'-9a8307f'),Path('validation')/('readback-'+label))
tree(E/'unit-9a8307f','validation/unit')
tree(E/'small-native-9a8307f','validation/small-native')
tree(E/'a-head-relief-9a8307f','local-studies/A-head-relief')
for label in ['unit','small-native','predock','open-stow','readback-predock','readback-open-stow','a-head-relief']:
    tree(E/(label+'-execution-9a8307f'),Path('validation/execution')/label)
for name in ['ep4-source-commit.json','baseline.json','source-update.json.gz']:
    archive(E/name,Path('validation')/name)
archive(E/'actions-90b09f5-final/report.json','actions/90b09f5-run39378151409-final.json')
archive(E/'actions-90b09f5-final-execution.json','actions/90b09f5-run39378151409-execution.json')
archive(E/'ep4_a_head_relief.py','local-studies/ep4_a_head_relief.py')

# Additional local studies/readers are explicitly identified by a create-only
# publication manifest, including failed execution records if any.
extra=read(E/'publication-extra-inputs.json')
assert extra['basis_source_commit']==N
for row in extra['files']:
    assert sha(row['source'])==row['sha256'],row
    archive(row['source'],row['relative'])
for row in extra['trees']:
    expected={x['relative']:x['sha256'] for x in row['inventory']}
    actual={p.relative_to(row['source']).as_posix():sha(p) for p in Path(row['source']).rglob('*') if p.is_file()}
    assert expected==actual
    tree(Path(row['source']),row['relative'])

def pairs(v):
    return {'pairs':v['pair_count'],'native_Common_calls':v['native_Common_calls'],
        'positive_Common_count':v['positive_Common_count_including_below_tolerance'],
        'evaluation_errors':sum(bool(x.get('evaluation_failed')) for x in v['rows']),
        'context_errors':sum(len(x.get('local_material_context',{}).get('crop_evaluation_errors',[])) for x in v['rows']),
        'failures':[{'a':x['a'],'b':x['b'],'common_mm3':x.get('common_mm3'),'error':x.get('error'),
                    'bounds_mm':x.get('common_material',{}).get('bounds_mm'),
                    'solid_components':x.get('common_material',{}).get('solids'),
                    'context_complete':x.get('artifact_diagnostics_complete')} for x in v['failures']]}
poses=[]
for n in native:
    for q in n['poses']:
        poses.append({'pose':q['pose'],'combined_participants':q['combined_participants'],
            'external_participants':q['external_participants'],'candidate_participants':41,
            'external':pairs(q['external']),'A_to_B':pairs(q['A_to_B_endpoints']),
            'material_to_ends':pairs(q['material_to_all_40_endpoint_parts']),
            'containment':{'parts':len(q['containment']['rows']),'failures':q['containment']['failures'],
                           'evaluation_errors':sum(bool(x.get('evaluation_failed')) for x in q['containment']['rows'])},
            'all_declared_checks_clear':q['all_declared_checks_clear_at_this_finite_pose']})
poses.sort(key=lambda x:['STOW','PREDOCK','OPEN'].index(x['pose']))
summary={'schema':'razr-ep4-readable-native-summary-v1','source_commit':N,
    'source_sha256':native[0]['source_sha256'],'source_bytes_unchanged':True,
    'endpoint_self_checks':{k:pairs(v) for k,v in native[0]['endpoint_self_checks'].items()},
    'endpoint_self_checks_repeated_in_two_executions':True,
    'poses':poses,'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
    'full_cycle_internal_route_accepted':False,'physical_fabrication_executed':False,
    'actual_OLED_COF_or_flex_stack_selected':False,
    'raw_reports':[{ 'path':str(P/'native'/label/'native-report.json.gz'),
                     'uncompressed_sha256':sha(E/(label+'-9a8307f')/'native/native-report.json')}
                   for label in ['predock','open-stow']],
    'independent_readbacks':[{'path':str(P/'validation'/('readback-'+label)/'report.json.gz'),
        'uncompressed_sha256':sha(E/('readback-'+label+'-9a8307f')/'report.json'),
        'all_assembly_parts_have_metric_comparison':v['all_assembly_parts_have_metric_comparison'],
        'passed':v['declared_readback_checks_passed'],'seconds':v['seconds'],
        'scope':'all endpoint/assembly numeric metrics plus positive Common and 2 mm context exports; no full material or label equivalence'}
        for label,v in zip(['predock','open-stow'],readbacks)],
    'A_local_relief':{'report':str(P/'local-studies/A-head-relief/report.json.gz'),
        'checks_passed':a['local_declared_geometry_checks_passed'],'head_Common_mm3':a['head_Common_mm3'],
        'material_accounting':a['material_accounting'],'baseline_EP4_source_or_assemblies_modified':False},
    'stop_reason':'three bounded baseline poses completed and rejected; two local follow-ups retain separate scope; physical inputs are not supplied'}
summary['unique_declared_pairs']=380+sum(q[k]['pairs'] for q in poses for k in ['external','A_to_B','material_to_ends'])
summary['actual_declared_pairs_across_two_executions']=summary['unique_declared_pairs']+380
summary['pair_evaluation_errors']=sum(q['evaluation_errors'] for q in summary['endpoint_self_checks'].values())+sum(q[k]['evaluation_errors'] for q in poses for k in ['external','A_to_B','material_to_ends'])
summary['containment_evaluation_errors']=sum(q['containment']['evaluation_errors'] for q in poses)
summary['all_three_poses_rejected']=all(not q['all_declared_checks_clear'] for q in poses)
assert summary['pair_evaluation_errors']==summary['containment_evaluation_errors']==0
assert summary['all_three_poses_rejected']
write(R/P/'native-summary.json',summary)
write(E/'phase4-archive-receipt.json',{'schema':'razr-phase4-evidence-archive-v1',
    'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_source_commit':N,
    'items':items,'summary_path':str(P/'native-summary.json'),'summary_sha256':sha(R/P/'native-summary.json'),
    'indexed_transferred_files':len(items),'native_source_inputs_unchanged_after_archive':all(sha(R/k)==h for k,h in native[0]['source_sha256'].items())})
print(json.dumps({'source_commit':N,'archived_files':len(items),'archive_bytes':sum(x['bytes'] for x in items),
    'unique_declared_pairs':summary['unique_declared_pairs'],'actual_declared_pairs_across_two_executions':summary['actual_declared_pairs_across_two_executions'],
    'summary_sha256':sha(R/P/'native-summary.json')},indent=2))
