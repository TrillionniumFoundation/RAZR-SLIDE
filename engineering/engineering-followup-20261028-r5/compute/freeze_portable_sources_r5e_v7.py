"""Freeze the reviewed V7 source bundle; never execute its geometry."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
R4=ROOT/'razr-current/engineering/engineering-followup-20261027-r4/envelope'
NEW_NAMES=['planar_exterior_refinement_r5e_v7.py','planar_exterior_model_r5e_v7.py',
           'verify_planar_exterior_r5e_v7.py','run_portable_planar_r5e_v7.py',
           'prepare_planar_source_selection_r5e_v7.py','R5E_PLANAR_EXTERIOR_V7_BASIS.md',
           'R5E_V7_BASE_V6_INPUT_BRIDGE.json','R5E_V7_REAL_RETAINED_LEAF.json',
           'R5E_V7_STATIC_SOURCE_CAPACITY.json','R5E_V7_SOURCE_PREPARATION_RECEIPT.json',
           'freeze_portable_sources_r5e_v7.py']


def identity(path):
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':path.name,'bytes':path.stat().st_size,'sha256':sha}


def same(path,row):
    found=identity(path)
    return all(found[k]==row[k] for k in ('bytes','sha256'))


lock_path=HERE/'R5E_PORTABLE_SOURCE_LOCK_V7.json';readiness_path=HERE/'R5E_V7_READINESS.json'
assert not lock_path.exists() and not readiness_path.exists(),'Keep an already frozen source bundle unchanged'
prior=[]
for name in ['R5E_PORTABLE_SOURCE_LOCK.json','R5E_PORTABLE_SOURCE_LOCK_V4.json','R5E_PORTABLE_SOURCE_LOCK_V5.json','R5E_PORTABLE_SOURCE_LOCK_V6.json']:
    old=json.loads((HERE/name).read_text())
    assert all(same(HERE/row['path'],row) for row in old['r5_files'])
    assert all(same(R4/row['path'],row) for row in old['r4_source_files'])
    prior.append({'lock':identity(HERE/name),'r5_members_unchanged':len(old['r5_files']),'r4_members_unchanged':len(old['r4_source_files'])})
old=json.loads((HERE/'R5E_PORTABLE_SOURCE_LOCK_V6.json').read_text())
names=NEW_NAMES+[r['path'] for r in old['r5_files']]+['R5E_PORTABLE_SOURCE_LOCK_V6.json']
assert len(names)==len(set(names))==37
parsed=[]
for name in names:
    path=HERE/name
    assert path.is_file() and not path.is_symlink()
    if path.suffix=='.py':ast.parse(path.read_text(),filename=name);parsed.append(name)
bridge=json.loads((HERE/'R5E_V7_BASE_V6_INPUT_BRIDGE.json').read_text())
selection=json.loads((HERE/'R5E_V7_REAL_RETAINED_LEAF.json').read_text())
capacity=json.loads((HERE/'R5E_V7_STATIC_SOURCE_CAPACITY.json').read_text())
assert len(bridge['files'])==53 and selection['V6_root_index']==76 and selection['V6_node_index']==47
assert capacity['actual_V6_retained_roots']==4943 and capacity['maximum_total_UV_pieces']==4064 and capacity['maximum_new_forest_nodes']==13135
lock={'schema':'razr-r5e-portable-source-lock-v7-planar-exterior-conditioned','source_commit':old['source_commit'],
      'actual_V3_run_id':old['actual_V3_run_id'],'actual_V3_commit':old['actual_V3_commit'],
      'actual_V4_run_id':old['actual_V4_run_id'],'actual_V4_commit':old['actual_V4_commit'],
      'actual_V5_run_id':old['actual_V5_run_id'],'actual_V5_commit':old['actual_V5_commit'],
      'actual_V6_execution_kind':'local_owned_pipeline','actual_V6_pipeline':bridge['actual_pipeline_identity'],
      'actual_V6_source_lock':identity(HERE/'R5E_PORTABLE_SOURCE_LOCK_V6.json'),
      'conditional_planar_exterior_model_only':True,'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
      'native_planar_region_semantics_verified':False,'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
      'original_raw_gate_reclassified':False,'full_continuous_G2':False,'V5_producer_rerun':False,'V6_producer_rerun':False,
      'r5_files':[identity(HERE/name) for name in names],'r4_source_files':old['r4_source_files']}
lock_path.write_text(json.dumps(lock,indent=2)+'\n')
readiness={'schema':'razr-r5e-v7-static-readiness-for-bounded-actual-v6-retained-leaf','created_utc':datetime.now(timezone.utc).isoformat(),
           'source_lock':identity(lock_path),'new_files_to_publish':[identity(HERE/name) for name in NEW_NAMES]+[identity(lock_path)],
           'all_R5_lock_members':len(names),'original_R4_source_members':3,
           'prior_frozen_sources_actually_rehashed':prior,'python_sources_AST_parsed':parsed,
           'formal_V7_worker_executions':0,'V7_mathematical_controls_executed':0,'new_geometric_pass_claimed':False,
           'conditional_planar_exterior_model_only':True,'native_planar_region_semantics_verified':False,
           'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
           'original_raw_gate_reclassified':False,'full_continuous_G2':False,'all_blockers_closed':False,
           'first_actual_V6_retained_leaf':{'case_id':'case-028','frame':1,'V6_root_index':76,'V6_node_index':47,'base_V5_leaf_locator':[28,17]},
           'source_input_counts':{'original_R4_public_inputs':19,'actual_V5_inputs':25,'actual_V6_inputs':53},
           'sequential_stages':['single-planar-exterior-leaf','verify-single','preflight-planar-exterior','all-planar-exterior-frames','verify-all'],
           'original_owned_limits_per_stage':{'wall_seconds':600,'RSS_limit_bytes':805306368,'shared_ceiling_bytes':7301444403,
                 'disk_floor_bytes':104857600,'maximum_output_bytes':41943040,'metadata_margin_bytes':4194304},
           'maximum_combined_worker_wall_seconds_before_overhead':3000,'maximum_total_UV_pieces':4064,
           'maximum_new_forest_nodes':13135,'maximum_new_forest_leaves':9039,
           'larger_work_requires_actual_single_pass_and_independent_pass':True,
           'full_work_requires_actual_all16_capacity_preflight':True,'final_independent_static_readback_still_required':True}
readiness_path.write_text(json.dumps(readiness,indent=2)+'\n')
print(json.dumps({'source_lock':identity(lock_path),'readiness':identity(readiness_path),'R5_files':len(names),'new_files':len(NEW_NAMES),'geometry_executed':False}))
