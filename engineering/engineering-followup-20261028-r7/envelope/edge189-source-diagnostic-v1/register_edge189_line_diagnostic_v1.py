"""Freeze only source, original input identities and a bounded contract.

This registration performs no geometric support/channel calculation and imports
neither producer nor independent reader code. It must precede actual approval.
"""
import argparse
import ast
import copy
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path


def need(value,message):
    if not value:raise ValueError(message)


def identity(path):
    path=Path(path).resolve();digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def same(a,b):return all(a[k]==b[k] for k in ('bytes','sha256'))


def write_new(path,value):
    need(not path.exists(),'registration cannot overwrite a prior artifact: '+str(path))
    path.write_text(json.dumps(value,indent=2)+'\n')
    return identity(path)


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--independent-checker',type=Path,required=True)
    parser.add_argument('--independent-evidence-root',type=Path,required=True)
    args=parser.parse_args()
    here=Path(__file__).resolve().parent;workspace=here.parents[1]
    prior=workspace/'r7-envelope/spatial-pilot-v1'
    prior_contract_path=prior/'R7E_ONE_SPLIT_SPATIAL_COST_PROBE_CONTRACT_V1.json'
    prior_contract=json.loads(prior_contract_path.read_text())
    source=here/'diagnose_edge189_line_support_r7e_v1.py'
    source_text=source.read_text();source_tree=ast.parse(source_text)
    source_functions={n.name:n for n in source_tree.body if isinstance(n,ast.FunctionDef)}
    need(args.independent_checker.resolve().is_relative_to(args.independent_evidence_root.resolve()),
         'independent checker must reside inside the independently authored evidence package')
    independent_text=args.independent_checker.read_text();independent_tree=ast.parse(independent_text)
    need(any(isinstance(n,ast.FunctionDef) and n.name=='verify_claim' for n in independent_tree.body),
         'independent source must define the registered verify_claim interface')
    for node in ast.walk(independent_tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=([node.module] if isinstance(node,ast.ImportFrom) else [v.name for v in node.names])
            need(all(n and n.split('.')[0] in {'copy','fractions','hashlib','itertools','json','typing'} for n in names),
                 'independent checker imports must be its explicitly reviewed standard-library set')
    inputs=copy.deepcopy(prior_contract['inputs'])
    metadata=json.loads((here/'SOURCE_METADATA_READBACK_V1.json').read_text())
    inputs.update({
        'registration_source':identity(__file__),
        'independent_checker_cross_author_static_review':identity(here/'INDEPENDENT_CHECKER_STATIC_REVIEW_V1.json'),
        'original_resource_supervisor_source':identity(workspace/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/r4/supervise_owned_pure_math_r4e_v2.py'),
        'actual_cost_probe_contract':identity(prior_contract_path),
        'actual_cost_probe_report':identity(prior/'attempt-1/R7E_ONE_SPLIT_ORIGINAL_SPATIAL_COST_PROBE_V1.json'),
        'actual_cost_probe_source':identity(prior/'probe_original_spatial_one_split_r7e_v1.py'),
        'source_metadata_readback':identity(here/'SOURCE_METADATA_READBACK_V1.json'),
        'native_original_producer':metadata['inputs']['native_producer'],
        'native_original_reader':metadata['inputs']['native_independent_reader'],
        'original_material_BREP':identity(workspace/'r7-recovery/r3e/source-and-inputs/inputs/case-028/material-003.brep'),
        'original_native_extractor':identity(workspace/'r7-recovery/r3e/source-and-inputs/extract_originals_r3e.py'),
        'original_native_boundary_inventory':identity(workspace/'r7-recovery/r3e/source-and-inputs/source-original/boundary_inventory_l8.py')
    })
    need(same(inputs['actual_cost_probe_report'],metadata['trigger_actual_cost_probe']),
         'actual edge source trigger must retain exact report bytes')
    need(same(inputs['original_material_BREP'],metadata['selected_original_record']['input']),
         'original material bytes must match its native record')
    independent_files=[]
    for path in sorted(args.independent_evidence_root.resolve().rglob('*')):
        if path.is_file():
            need(not path.is_symlink() and path.suffix not in ('.pyc','.pyo'),'independent source package contains an unregistered generated or linked file')
            rel=path.relative_to(args.independent_evidence_root.resolve()).as_posix()
            row=identity(path);independent_files.append({'relative_path':rel,**row})
            if path.resolve()!=args.independent_checker.resolve():inputs['independent_authority/'+rel]=row
    need(len(independent_files)>=12,'complete independent source/official authority package required')
    mapping=[]
    wanted={'need','separated','require','decode','encode','volume','channel_for','add','scale','project'}
    for row in prior_contract['original_function_bindings']:
        if row['original_function'] not in wanted:continue
        row=copy.deepcopy(row);path=Path(inputs[row['original_source_input']]['path']);text=path.read_text()
        tree={n.name:n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        original=tree[row['original_function']];copied=source_functions[row['copied_function']]
        need(ast.dump(original)==ast.dump(copied),'original spatial or helper AST differs before registration')
        need(ast.get_source_segment(text,original)==ast.get_source_segment(source_text,copied),
             'complete original copied function source bytes differ before registration')
        row['actual_function_bytes_equal']=True;mapping.append(row)
    path=Path(inputs['original_resource_supervisor_source']['path']);text=path.read_text()
    original=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='resources')
    copied=source_functions['resources']
    need(ast.dump(original)==ast.dump(copied) and ast.get_source_segment(text,original)==ast.get_source_segment(source_text,copied),
         'the original shared-unreclaimable resource formula/source must remain byte-exact')
    digest=hashlib.sha256(ast.dump(original).encode()).hexdigest()
    mapping.append({'original_source_input':'original_resource_supervisor_source','original_source':inputs['original_resource_supervisor_source'],
        'original_function':'resources','copied_function':'resources','original_AST_sha256':digest,'copied_AST_sha256':digest,
        'original_function_bytes_sha256':hashlib.sha256(ast.get_source_segment(text,original).encode()).hexdigest(),
        'actual_function_bytes_equal':True})
    need(len(mapping)==11 and {v['original_function'] for v in mapping}==wanted|{'resources'},
         'eleven exact original function mappings required')
    mapping_row=write_new(here/'ORIGINAL_METHOD_FUNCTION_MAPPING_V1.json',{
        'schema':'razr-r7e-edge189-original-function-mapping-v1','actual_geometry_executed':False,
        'complete_original_function_count':11,'bindings':mapping,
        'producer_or_primitive_helper_imports':0,'source':identity(source)})
    archive=copy.deepcopy(prior_contract['original_V6_archive_files'])
    bound_inputs=dict(inputs);bound_inputs.update({'V6_archive/'+k:v for k,v in archive.items()})
    for row in bound_inputs.values():need(same(identity(row['path']),row),'pre-registration complete original input hash differs')
    capacity={
        'schema':'razr-r7e-edge189-static-capacity-v1','actual_geometry_executed':False,
        'source_model':'one original complete Line plus original full D; one saved low child and one fixed original channel',
        'prior_actual_additional_stage_debit':{'splits':82,'piece_like_tests':174854,'support_like_tests':366314},
        'maximum_new_splits':0,'maximum_single_piece_comparisons':3,'maximum_fixed_whole_channel_attempts':1,
        'maximum_complete_material_piece_count':523,'all_original_material_piece_counts_preserved':[523,179],
        'maximum_new_producer_piece_tests':526,'maximum_new_producer_support_tests':4208,
        'maximum_independent_separator_calls':553,'maximum_independent_claim_calls':6,
        'maximum_new_validation_vertices':864,'maximum_new_validation_comparisons':50000,
        'source_validation_static_upper_debit_ledger':{
            'six_independent_calls_at_6144_each':36864,
            'six_original_edge_canonical_serializations_at_1553_bytes_each':9318,
            'six_independent_source_binding_check_upper_charges_at_64_each':384,
            'three_producer_formula_upper_charges_at_128_each':384,
            'saved_original_path_24_times16_plus_low_child64':448,
            'original_separator_wrapper_guard_upper_charges':553,
            'total_upper_debit':47951,'registered_upper_cap':50000,
            'source_serialization_bytes_are_labeled_separately_and_also_extra_overcharged':True,
            'total_is_not_a_literal_comparison_count':True},
        'maximum_conservative_additional_stage_debit':{'splits':82,'piece_like_tests':174854+526+553+864,
            'support_like_tests':366314+4208+553+50000},
        'minimum_remaining_conservative_additional_stage_budget':{'splits':4014,
            'piece_like_tests':12000000-(174854+526+553+864),'support_like_tests':12000000-(366314+4208+553+50000)},
        'wall_seconds':60,'address_space_bytes':536870912,'maximum_decoded_input_bytes':67108864,'maximum_output_bytes':4194304,
        'original_native_reports_read_sequentially':True,'source_inputs_bound_before_auxiliary_registration':len(bound_inputs),
        'source_input_bytes_before_auxiliary_registration':sum(v['bytes'] for v in bound_inputs.values()),
        'largest_original_input_bytes':max(v['bytes'] for v in bound_inputs.values()),
        'previous_actual_capacity_evidence':[
            {'input':inputs['actual_original_domain_attempt2'],'elapsed_seconds':1.3438780260003114,'peak_RSS_bytes':241602560,
             'relevance':'actual sequential readback of both full original native reports with exact source analysis'},
            {'input':inputs['actual_cost_probe_report'],'elapsed_seconds':0.7930038741000015,'peak_RSS_bytes':174010368,
             'relevance':'actual larger original-spatial fixed-target work, including low child739piece tests'}
        ],
        'finite_algorithmic_basis':[
            'No new split, no native operations, no Taylor patches, no new full-frame forest.',
            'At most6 independent affine vertex enumerations; each has16 exact and128 hypothetical-tube vertices.',
            'At most3 local piece calls and one523piece original-order fixed channel; eachpiece at most8 support inequalities.',
            'Independent source dimensions and loops are finite; all source validation including controls is conservatively debited.',
            'Output retains only one source edge/carrier, bounded corner records, five mutated claims and one fixed prefix; original whole forest remains hash-bound input.'
        ],
        'native_or_original_depth24_or_V9_first_u_qualification_claimed':False,
        'strict_source_box_identity_required_before_fixed_whole_channel':True,
        'hypothetical_tube_containment_in_original_B_is_a_reported_boolean_not_assumed':True,
        'independent_authority_files':independent_files
    }
    # Time/RSS values are copied from actual reports, not recomputed predictions.
    actual_probe=json.loads(Path(inputs['actual_cost_probe_report']['path']).read_text())
    capacity['previous_actual_capacity_evidence'][1]['elapsed_seconds']=actual_probe['elapsed_seconds']
    capacity_row=write_new(here/'STATIC_CAPACITY_V1.json',capacity)
    target=here/'attempt-1';contract_path=here/'R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_CONTRACT_V1.json'
    contract={'schema':'razr-r7e-edge189-line-support-diagnostic-contract-v1','registered_utc':datetime.now(timezone.utc).isoformat(),
        'source':identity(source),'basis':identity(here/'BASIS_V1.md'),'static_capacity':capacity_row,
        'source_function_mapping':mapping_row,'checker_interface':identity(here/'INDEPENDENT_CHECKER_INTERFACE_V1.json'),
        'independent_line_checker':identity(args.independent_checker),'original_function_bindings':mapping,
        'inputs':inputs,'original_V6_archive_files':archive,'original_capacity':prior_contract['original_capacity'],
        'wall_seconds':60,'address_space_bytes':536870912,'maximum_decoded_input_bytes':67108864,'maximum_output_bytes':4194304,
        'maximum_new_splits':0,'maximum_single_piece_comparisons':3,'maximum_fixed_whole_channel_attempts':1,
        'maximum_independent_claim_calls':6,'maximum_new_validation_vertices':864,'maximum_new_validation_comparisons':50000,
        'maximum_new_producer_piece_tests':526,'maximum_new_producer_support_tests':4208,'maximum_independent_separator_calls':553,
        'disk_floor_bytes':104857600,'metadata_margin_bytes':4194304,'shared_ceiling_bytes':7301444403,
        'shared_resource_formula':'anon + shmem + max(kernel - slab_reclaimable, 0) + unevictable',
        'memory_current_used_as_gate':False,'fixed_original_source_locator':[78,375],'fixed_source_child_index':0,
        'fixed_channel':{'material_side':0,'axis':1,'end':0},'fixed_piece_index':332,'fixed_edge_index':189,
        'fixed_normal_exact':['1','2','0'],'cumulative_source_depth':25,'original_V6_depth_gate_passed':False,
        'qualification_claimed':False,'V9_first_u_qualification_claimed':False,'native_BREP_error_bound_certified':False,
        'same_source_channel_carrier_order_required':True,'same_full_original_D_required':True,
        'original_AABB_must_be_preserved':True,'strict_six_endpoint_source_box_equality_required':True,
        'whole_hypothetical_tube_contained_in_B_intersection_is_not_assumed':True,
        'new_full_frame_execution_authorized':False,
        'argv':['python3','-I','-S','-B',str(source),'--contract',str(contract_path),'--output',str(target)]}
    all_rows=dict(bound_inputs)
    all_rows.update({k:contract[k] for k in ('source','basis','static_capacity','source_function_mapping','checker_interface','independent_line_checker')})
    contract['registered_input_and_artifact_count']=len(all_rows)
    contract['registered_input_and_artifact_bytes']=sum(v['bytes'] for v in all_rows.values())
    contract_row=write_new(contract_path,contract)
    draft=here/'drafts/diagnose_edge189_line_support_before_phase_fix_v1.py.txt'
    diff=''.join(difflib.unified_diff(draft.read_text().splitlines(True),source_text.splitlines(True),fromfile=draft.name,tofile=source.name))
    diff_path=here/'drafts/PRE_REGISTRATION_NEGATIVE_PHASE_AND_SCOPE_REFINEMENT.diff'
    need(not diff_path.exists(),'prior unexecuted draft diff must not be overwritten');diff_path.write_text(diff)
    write_new(here/'SOURCE_REGISTRATION_RECEIPT_V1.json',{
        'schema':'razr-r7e-edge189-source-registration-receipt-v1','registered_utc':datetime.now(timezone.utc).isoformat(),
        'actual_support_or_channel_execution_started':False,'original_inputs_and_artifacts_all_hashed':True,
        'contract':contract_row,'source':identity(source),'independent_checker':identity(args.independent_checker),
        'source_function_mapping':mapping_row,'static_capacity':capacity_row,
        'registered_input_and_artifact_count':len(all_rows),'registered_input_and_artifact_bytes':sum(v['bytes'] for v in all_rows.values()),
        'unexecuted_draft':identity(draft),'unexecuted_draft_refinement_diff':identity(diff_path),
        'root_independent_review_still_required_before_actual':True})
    print(json.dumps({'source':identity(source),'contract':contract_row,'registered_input_and_artifact_count':len(all_rows),
                      'registered_input_and_artifact_bytes':sum(v['bytes'] for v in all_rows.values()),'actual_geometry_executed':False}))


if __name__=='__main__':main()
