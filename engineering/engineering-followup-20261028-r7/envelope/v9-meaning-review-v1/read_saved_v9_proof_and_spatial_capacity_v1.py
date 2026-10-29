"""Read-only accounting of saved proofs and hypothetical continuation capacity.

No geometric separator, native call, producer, helper, or refinement is run.
"""
import ast
from collections import Counter
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def need(ok,message):
    if not ok:raise ValueError(message)


def identity(path):
    p=Path(path).resolve();data=p.read_bytes()
    return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def load(path,compressed=False):
    data=Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if compressed else data)


def exact_display(value):return {'exact':str(value),'display_only_float64':float(value)}


def gate_ast(path):
    tree=ast.parse(Path(path).read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need' and
           len(n.args)==2 and isinstance(n.args[1],ast.Constant) and
           n.args[1].value=='first actual planar-exterior witness failed the original TOL or lacked actual new planar proof; later work withheld']
    need(len(calls)==1,'unique original first-u gate expected')
    return ast.dump(calls[0].args[0]),ast.unparse(calls[0].args[0])


def main():
    src=ROOT/'r7-envelope/source-v9';actual=ROOT/'r7-envelope/local-v9/attempt-1'
    producer=load(actual/'single-planar-exterior-leaf/report.json');frame=producer['frames'][0]
    paths={'producer_report':actual/'single-planar-exterior-leaf/report.json','checker_report':actual/'verify-single/report.json',
           'actual_certificate':actual/'single-planar-exterior-leaf'/frame['certificate']['path'],
           'actual_controller':actual/'verify-single-supervision/controller.json','actual_pipeline':actual/'pipeline.json',
           'original_V6_certificate':Path(frame['base_V6_certificate']['path']),'original_V6_report':Path(producer['actual_V6_report']['path']),
           'V9_producer_source':src/'planar_exterior_refinement_r7e_v9.py','V9_driver_source':src/'run_portable_planar_r7e_v9.py',
           'original_V7_driver_source':src/'run_portable_planar_r5e_v7.py','original_V6_producer_source':src/'primitive_refinement_r5e_v6.py',
           'saved_prefix_census':ROOT/'r7-envelope/correlation-diagnostic-v1/attempt-1/R7E_V9_SAVED_PREFIX_PLANE_PREIMAGE_DIAGNOSIS_V1.json',
           'actual_wire_meaning':ROOT/'r7-envelope/wire-meaning-diagnostic-v1/attempt-1-v2/R7E_SAVED_V9_WIRE_MEANING_DIAGNOSIS_V2.json'}
    before={k:identity(p) for k,p in paths.items()}
    need(before['V9_producer_source']['sha256']==producer['source_sha256'],'actual producer source binding differs')
    need(all(before['actual_certificate'][k]==frame['certificate'][k] for k in ('bytes','sha256')) and
         all(before['original_V6_certificate'][k]==frame['base_V6_certificate'][k] for k in ('bytes','sha256')),'actual inherited certificate binding differs')
    new=load(paths['actual_certificate'],True);old=load(paths['original_V6_certificate'],True);old_report=load(paths['original_V6_report'])
    checker=load(paths['checker_report']);controller=load(paths['actual_controller']);pipeline=load(paths['actual_pipeline'])
    need(new['frame']=={k:v for k,v in frame.items() if k!='certificate'} and len(new['roots'])==1,'exact single selected leaf scope differs')
    need(producer['execution_completed'] and checker['execution_completed'] and controller['completed'] is False and controller['worker_exit_code']==0,
         'completed worker / failed owned-controller distinction differs')
    root=new['roots'][0];need(root['base_V6_leaf_locator']==[76,47],'selected original root/leaf differs')
    leaves=[n for n in root['tree']['nodes'] if n['kind']=='excluded'];retained=[n for n in root['tree']['nodes'] if n['kind']=='retained']
    codes=Counter();uses=Counter();patterns=Counter();channels=Counter();lengths=Counter();leaf_sum=F(0)
    for node in leaves:
        c=node['certificate'];text=c['complete_piece_separation_codes']
        need(len(text)==c['boundary_piece_count'] and set(text)<=set('01234567') and not c['planar_exterior_certificates'],
             'all saved final leaf proofs must use only unchanged spatial rules')
        need(c['closed_cell_boundary_retained_as_zero_volume_carrier'] is True and c['whole_closed_cell_disjoint_claimed'] is False,
             'open-interior-only scope must remain explicit')
        codes.update(text);uses.update(set(text));patterns[','.join(sorted(set(text)))]+=1
        channels[(c['material_side'],c['axis'],c['end'])]+=1;lengths[len(text)]+=1;leaf_sum+=F(node['positive_directed_volume_exact'])
    need(len(leaves)==82 and not retained and leaf_sum==F(root['root_directed_volume_exact'])==F(root['tree']['excluded_open_sum_exact']) and
         F(root['tree']['retained_sum_exact'])==0,'complete selected source volume accounting differs')
    selected=next(n for n in old['roots'][76]['tree']['nodes'] if n['id']==47)
    need(selected['kind']=='retained' and selected['reason']=='path_depth_limit_retained' and F(selected['positive_directed_volume_exact'])==leaf_sum,
         'exact originally retained V6 leaf differs')
    old_rows=[];reason_counts=Counter();reason_volumes={};old_depths={};negative_signatures=Counter();volume_frequency=Counter()
    for ri,r in enumerate(old['roots']):
        nodes={n['id']:n for n in r['tree']['nodes']};stack=[(0,0)];seen=set()
        while stack:
            ni,depth=stack.pop();need(ni not in seen,'old source node duplicated');seen.add(ni);n=nodes[ni]
            if n['kind']=='split':stack.extend((child,depth+1) for child in n['children'])
            elif n['kind']=='retained':
                value=F(n['positive_directed_volume_exact']);old_depths[(ri,ni)]=depth
                old_rows.append((value,ri,ni,n['reason'],n));reason_counts[n['reason']]+=1
                reason_volumes[n['reason']]=reason_volumes.get(n['reason'],F(0))+value
        need(len(seen)==len(nodes),'old complete source tree census differs')
    old_sum=sum((r[0] for r in old_rows),F(0))
    need(old_sum==F(frame['base_V6_retained_leaf_sum_exact'])==F(frame['base_V6_frame_conditional_upper_exact_mm3']),
         'original full-frame retained bound differs')
    remaining=[r for r in old_rows if (r[1],r[2])!=(76,47)]
    remaining.sort(key=lambda r:(-r[0],r[1],r[2]));tail=old_sum-leaf_sum;original_tol=F(1e-7);snapshots=[];minimum_roots=None;before_cross=None
    for index,row in enumerate(remaining,1):
        before_tail=tail;tail-=row[0]
        if index in (1,5,10,20,30,40,50,60,80,100,200,500,1000):
            snapshots.append({'largest_original_roots_hypothetically_zeroed':index,'remaining_unprocessed_original_tail':exact_display(tail)})
        if minimum_roots is None and tail<=original_tol:
            minimum_roots=index;before_cross=before_tail;tail_at_cross=tail
    need(minimum_roots==2296 and tail==0,'fixed exact retained-root capacity census differs')
    needed=remaining[:minimum_roots]
    for value,ri,ni,reason,node in remaining:
        volume_frequency[value]+=1
        observation=node.get('actual_channel_observation',{})
        failure=observation.get('all_registered_channels_unresolved')
        signature=tuple((f['material_side'],f['axis'],f['end'],f['unresolved_piece_index']) for f in failure) if failure else None
        negative_signatures[signature]+=1
    need(all(len(row[4].get('actual_channel_observation',{}).get('all_registered_channels_unresolved',[]))==12 for row in needed),
         'all potentially critical old roots must retain their actual complete spatial failure observations')
    old_gate,gate_text=gate_ast(paths['original_V7_driver_source']);new_gate,_=gate_ast(paths['V9_driver_source'])
    need(old_gate==new_gate,'the original UV contribution gate was changed')
    census=load(paths['saved_prefix_census']);models={m['model_index']:m['original_face_index'] for s in new['planar_models']['sources'] for m in s['models']}
    need(models[6]==27,'new original face27 model mapping differs')
    face27_count=sum(f['source_kind']=='face' and f['source_index']==27 for n in census['saved_failed_prefix_nodes'] for f in n['failed_channels'])
    candidates=[]
    for n in census['saved_failed_prefix_nodes']:
        hits=[]
        for f in n['failed_channels']:
            if f.get('model_index') in (2,3):
                last=[r for r in f['UV_first_blockers'] if (r['axis'],r['end'])==(1,1) and r['piece_index']==205]
                if last:hits.append(f['model_index'])
        if sorted(hits)==[2,3]:candidates.append(n['node_id'])
    need(len(candidates)==40 and min(candidates)==51 and face27_count==0,'saved-prefix candidate census differs')
    nodes={n['id']:n for n in root['tree']['nodes']};parents={c:(n['id'],i) for n in nodes.values() if n['kind']=='split' for i,c in enumerate(n['children'])}
    path=[];ni=51
    while ni:
        parent,branch=parents[ni];path.append({'parent_node_id':parent,'chosen_child_id':ni,'branch':branch,'split_axis':nodes[parent]['axis'],
            'original_cut_exact':nodes[parent]['cut_exact'],'original_cut_source':nodes[parent]['cut_source']});ni=parent
    path.reverse();need(len(path)==8,'original candidate source depth differs')
    spent=producer['counters'];cap=producer['capacity']
    remaining_caps={'additional_splits':cap['maximum_splits']-spent['splits'],
                    'combined_piece_tests':cap['maximum_boundary_box_tests']-spent['boundary_box_tests'],
                    'combined_support_tests':cap['maximum_support_inequality_tests']-spent['support_inequality_tests']}
    repeated={'additional_old_roots':minimum_roots,'splits_if_each_cost_the_selected_81':spent['splits']*(minimum_roots+1),
              'combined_support_tests_if_each_cost_the_selected_342440':spent['support_inequality_tests']*(minimum_roots+1),
              'pure_spatial_tests_scenario_plus_already_spent_combined':(spent['support_inequality_tests']-spent['UV_support_inequality_tests'])*minimum_roots+spent['support_inequality_tests'],
              'prediction':False,'demonstrates':'the one successful selected-leaf runtime cannot justify the full remaining forest by equal-cost extrapolation'}
    report={'schema':'razr-r7e-saved-v9-proof-and-spatial-continuation-readback-v1','read_only_saved_data_and_source_analysis':True,
        'new_geometric_predicates_executed':0,'new_refinement_nodes_executed':0,'source':identity(__file__),'inputs':before,
        'selected_leaf_result':{'original_V6_locator':[76,47],'original_V6_retention_reason':selected['reason'],'original_V6_depth':old_depths[(76,47)],
            'original_positive_directed_volume':exact_display(leaf_sum),'final_excluded_leaves':82,'final_retained_leaves':0,'final_retained_positive_volume_exact':'0',
            'complete_original_volume_conservation_checked':True,'additional_splits':spent['splits'],'additional_maximum_depth':root['tree']['maximum_depth_reached'],
            'combined_depth_from_original_V6_root':old_depths[(76,47)]+root['tree']['maximum_depth_reached'],
            'complete_spatial_code_character_counts':dict(sorted(codes.items())),'leaves_using_code':dict(sorted(uses.items())),
            'leaf_code_set_distribution':dict(sorted(patterns.items())),'final_material_axis_end_distribution':[{'key':list(k),'count':v} for k,v in sorted(channels.items())],
            'proof_code_lengths':dict(sorted(lengths.items())),'final_saved_planar_u_count':0,
            'intermediate_successful_UV_tests_not_retained_as_final_proofs':spent['successful_planar_exterior_separations'],
            'all_closed_cell_boundaries_and_cut_carriers_retained':True,'native_or_whole_closed_cell_disjointness_proved':False},
        'original_first_u_gate':{'unchanged_from_recovered_V7_AST':True,'predicate_source':gate_text,
            'positive_excluded_volume_condition':True,'single_selected_leaf_original_tolerance_condition':True,'new_UV_final_proof_condition':False,
            'actual_driver_reached_this_gate':False,'actual_earlier_failure':pipeline['failure'],'actual_owned_failure':controller['failure'],
            'interpretation':'u=0 measures the absence of a final saved proof using the new UV rule; it is not evidence of physical interference or positive unresolved volume in the selected leaf.'},
        'full_frame_scope':{'original_frame':['case-028',1],'original_V6_retained_leaf_count':len(old_rows),'remaining_original_leaf_count_after_selected':len(remaining),
            'original_V6_frame_upper_equals_retained_sum':exact_display(old_sum),'arithmetic_remaining_other_original_leaves':exact_display(old_sum-leaf_sum),
            'original_float64_TOL':exact_display(original_tol),'arithmetic_remaining_above_original_TOL':old_sum-leaf_sum>original_tol,
            'selected_phase_zero_is_not_a_full_frame_zero':True,'arithmetic_substitution_is_new_formal_certificate':False,
            'original_reason_counts':dict(reason_counts),'original_reason_volume_sums':{k:exact_display(v) for k,v in reason_volumes.items()},
            'full_V9_frame_run_executed':False,'native_semantics_verified':False,'full_continuous_G2':False},
        'next_finite_candidate':{'saved_failed_prefix_count':81,'face27_first_blocker_rows':face27_count,'model6_failed_planar_attempt_rows':0,
            'selection_rule':'among actual saved prefixes whose two original z-plane UV paths first fail on the last Circle patch63/piece205, select smallest original node id',
            'all_matching_original_node_ids':candidates,'selected_node_id':51,'original_source_depth':8,'complete_original_path':path,
            'selected_model_indices':[2,3],'selected_original_faces':[37,39],'native_or_V10_run_authorized_by_this_readback':False},
        'independent_spatial_continuation_feasibility':{'different_named_experiment_required':True,'can_qualify_V9_or_UV_first_u':False,
            'original_V9_failure_preserved':True,'full_frame_primitive_model_upper_bound_is_distinct_possible_goal':True,
            'unchanged_space_rule_sources':['primitive_refinement_r5e_v6.py:separated,attempt_channel,choose_cut','planar_exterior_refinement_r7e_v9.py:spatial_separator'],
            'already_spent_actual_V9_producer_counters':spent,'remaining_after_preserving_all_already_spent_combined_counters':remaining_caps,
            'original_maximum_additional_depth_per_V6_leaf':24,'existing_selected_suffix_depth':19,'maximum_combined_original_plus_additional_depth':48,
            'minimum_old_roots_that_must_change_even_if_each_becomes_zero':minimum_roots,
            'unprocessed_tail_before_crossing_TOL':exact_display(before_cross),'unprocessed_tail_at_crossing_TOL':exact_display(tail_at_cross),
            'all_critical_old_roots_have_actual_complete_original_spatial_failure':True,
            'minimum_extra_splits_if_unchanged_spatial_roots_remain_failed':minimum_roots,
            'remaining_split_allowance_per_critical_old_root':exact_display(F(remaining_caps['additional_splits'],minimum_roots)),
            'conditional_hypothetical_tail_snapshots':snapshots,'equal_cost_extrapolation_is_not_capacity_justification':repeated,
            'original_owned_V6_observed_runtime_seconds':old_report['seconds'],'original_owned_V6_observed_peak_RSS_bytes':old_report['peak_RSS_bytes'],
            'original_owned_V6_observed_counters':old_report['counters'],'actual_V9_producer_worker_runtime_seconds':producer['seconds'],
            'source_V6_certificate_bytes':before['original_V6_certificate']['bytes'],'actual_V9_certificate_bytes':before['actual_certificate']['bytes'],
            'remaining_old_complete_failure_signature_groups':[{'signature':[list(v) for v in k] if k else None,'count':v} for k,v in sorted(negative_signatures.items(),key=lambda item:(-item[1],str(item[0])))],
            'largest_repeated_original_volume_classes':[{'volume':exact_display(v),'count':c} for v,c in volume_frequency.most_common(8)],
            'full_budget_success_established':False,'next_needed_evidence':'a pre-registered small spatial-only continuation on representative remaining roots, keeping cumulative counters and every unresolved remainder; no full-frame launch follows from this readback alone'},
        'all_inputs_unchanged':all(identity(paths[k])==v for k,v in before.items())}
    need(report['all_inputs_unchanged'],'saved source changed during readback')
    output=OUT/'R7E_V9_PROOF_AND_SPATIAL_CONTINUATION_READBACK_V1.json';need(not output.exists(),'new output required')
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'report':identity(output),'new_geometric_predicates':0,'new_refinement_nodes':0,'all_inputs_unchanged':True}))


if __name__=='__main__':main()
