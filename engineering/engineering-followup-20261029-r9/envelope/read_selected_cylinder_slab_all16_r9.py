"""Independent complete forest, source and conservative-volume verification."""
import argparse
from collections import Counter
import copy
from fractions import Fraction as F
import gc
import gzip
import json
from pathlib import Path
import platform
import resource
import sys
import time
import traceback
import check_selected_cylinder_slab_r9 as checker

R8=Path(__file__).resolve().parents[2]/'engineering-followup-20261029-r8/independent-review'
sys.path.insert(0,str(R8))
from read_all16_actual_r8 import read_all_materials
from read_depth24_actual_r8 import identity,need,measure

LIMITS={'maximum_splits':4096,'maximum_depth':24,'maximum_boundary_box_tests':12000000,
        'wall_seconds':600,'address_space_limit_bytes':805306368}


def verify_root(root,original,sources,materials,D,tiny,counts):
    need(root['base_V5_leaf_locator']==original['base_V5_leaf_locator'],'original_root_locator')
    initial=checker.math.bounds(original['root_box_exact'])
    need(checker.math.bounds(root['root_box_exact'])==initial,'same_original_root_box')
    need(F(root['root_volume_exact'])==measure(initial)==F(original['root_directed_volume_exact']),'same_original_positive_root_volume')
    seen=set();pending=[(0,initial,0)];volume=bound=F(0);splits=maxdepth=0;nodes=root['nodes']
    while pending:
        index,B,depth=pending.pop()
        need(type(index) is int and 0<=index<len(nodes) and index not in seen,'unique_complete_node')
        seen.add(index);node=nodes[index]
        need(node['id']==index,'node_identity')
        need(node['depth']==depth<=24,'original_maximum_depth24')
        need(checker.math.bounds(node['box_exact'])==B,'reconstructed_exact_node_box')
        v=measure(B);need(F(node['box_volume_exact'])==v,'exact_positive_box_volume')
        observation=node['observation']
        if observation['kind']=='original_tiny_positive_volume_retained':
            need(v<=tiny and F(observation['bound_exact'])==v,'unchanged_original_tiny_rule')
            u=v;counts['tiny_nodes']+=1
        else:
            need(observation['kind']!='not_evaluated','completed_run_has_no_unevaluated_node')
            need(v>tiny,'non_tiny_node_evaluated')
            u=checker.verify(observation,B,sources,materials,D,counts);counts['tested_nodes']+=1
        need(F(node['bound_exact'])==u and 0<=u<=v,'bound_matches_independent_proof')
        maxdepth=max(maxdepth,depth)
        if node['kind']=='split':
            axis=node['axis'];cut=F(node['cut_exact']);children=node['children']
            need(type(axis) is int and 0<=axis<3 and B[axis][0]<cut<B[axis][1],'proper_internal_cut')
            need(cut==sum(B[axis])/2,'registered_exact_midpoint')
            need(len(children)==2 and children[0]!=children[1],'two_distinct_children')
            lower,upper=list(B),list(B);lower[axis],upper[axis]=(B[axis][0],cut),(cut,B[axis][1])
            need(measure(lower)==measure(upper)==v/2,'conserved_split_box_volume')
            pending.extend([(children[1],tuple(upper),depth+1),(children[0],tuple(lower),depth+1)]);splits+=1
        else:
            need(node['kind']=='leaf','known_terminal_kind');volume+=v;bound+=u;counts['terminal_leaves']+=1
    need(len(seen)==len(nodes),'all_nodes_reachable')
    need(volume==measure(initial),'complete_root_partition_conservation')
    need(0<=bound<=volume,'conservative_root_volume_accounting')
    return volume,bound,splits,maxdepth


def main():
    p=argparse.ArgumentParser();p.add_argument('--originals',type=Path,required=True);p.add_argument('--producer-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    result={'schema':'razr-r9-cylinder-slab-all16-independent-readback','completed':False,'frames':[],
            'source':identity(__file__),'independent_checker':identity(checker.__file__),
            'producer_report':identity(args.producer_report),'python_version':platform.python_version(),
            'producer_or_geometric_helper_imported':False,
            'scope':{'conditional_source_model_only':True,'native_error_bound_verified':False,
                     'native_filling_verified':False,'native_envelope_topology_verified':False,
                     'full_continuous_G2':False,'all_blockers_closed':False}}
    try:
        report=json.loads(args.producer_report.read_text())
        need(report['schema']=='razr-r9-cylinder-slab-all16-original-roots' and report['execution_completed'] and report['computation_completed'],'complete_all16_run')
        need(report['limits']==LIMITS,'exact_original_limits')
        need(report['recorded_budget_passed'] and 0<=report['seconds']<=600,'recorded_complete_cost_within_original_time')
        for k in ('source','geometry_source','math_source','common_source','cut_source','atomic_source','cache_source','proof_basis','capacity_basis','recovery_source','family_source','input_cache_source'):
            need(identity(report[k]['path'])==report[k],'actual_execution_source_identity:'+k)
        base=args.originals/'r7-recovery/v7/r5-local-v7/input-snapshot-v1/base-v6/all-primitive-support-frames'
        original=json.loads((base/'report.json').read_text());need(identity(base/'report.json')==report['original_report'],'original_report_identity')
        threshold=F(original['original_TOL_exact']);tiny=F(original['capacity']['tiny_retained_volume_exact'])
        need(threshold==F(report['original_TOL_exact'])==F(1e-7),'exact_original_float64_gate')
        need(tiny==F(report['original_tiny_exact']),'exact_original_tiny_rule')
        need(len(report['frames'])==len(original['frames'])==16,'complete_sixteen_frame_count')
        need([(r['case_id'],r['frame']) for r in report['frames']]==[(r['case_id'],r['frame']) for r in original['frames']],'original_frame_order')
        required=set()
        for row in original['frames']:
            with gzip.open(base/Path(row['certificate']['path']).name,'rt') as f:certificate=json.load(f)
            required.update(tuple(s['material_key']) for s in certificate['boundary_refinement']['sources'])
        materials,native_ids=read_all_materials(args.originals,required)
        result['original_native_inventories']=native_ids;result['whole_native_material_records']=len(materials)
        totals=Counter();total_splits=0;actual_control=None
        for frame,prior in zip(report['frames'],original['frames']):
            cp=base/Path(prior['certificate']['path']).name;cid=identity(cp)
            need(all(cid[k]==prior['certificate'][k] for k in ('bytes','sha256')),'complete_original_certificate_identity')
            with gzip.open(cp,'rt') as f:certificate=json.load(f)
            need(certificate['frame']=={k:v for k,v in prior.items() if k!='certificate'},'original_certificate_frame_header')
            sources=certificate['boundary_refinement']['sources']
            need(frame['source_piece_counts']==[len(s['pieces']) for s in sources],'full_boundary_piece_count')
            path=args.producer_report.parent/Path(frame['proof']['path']).name;pid=identity(path)
            need(all(pid[k]==frame['proof'][k] for k in ('bytes','sha256')),'complete_actual_proof_bytes')
            with gzip.open(path,'rt') as f:proof=json.load(f)
            need((proof['case_id'],proof['frame'])==(frame['case_id'],frame['frame']),'proof_frame_identity')
            D=checker.math.bounds(prior['original_remaining_displacement_box_exact'])
            need(checker.math.bounds(proof['D_exact'])==D,'whole_original_displacement_box')
            need(len(proof['roots'])==len(certificate['roots'])==frame['root_count'],'all_original_roots')
            volume=bound=F(0);frame_splits=maxdepth=0;counts=Counter()
            for index,(root,prior_root) in enumerate(zip(proof['roots'],certificate['roots'])):
                need(root['root_index']==index,'unique_original_root_order')
                v,u,n,d=verify_root(root,prior_root,sources,materials,D,tiny,counts)
                volume+=v;bound+=u;frame_splits+=n;maxdepth=max(maxdepth,d)
                if actual_control is None:
                    node=next((x for x in root['nodes'] if x['observation']['kind']=='cylinder_slab_upper_bound'),None)
                    if node is not None:actual_control=(copy.deepcopy(node),sources,D)
            need(F(frame['root_box_volume_exact'])==volume and F(frame['intersection_upper_bound_exact'])==bound,'all_positive_volumes_and_upper_bounds')
            need(F(frame['conservative_removed_volume_lower_bound_exact'])==volume-bound,'removed_volume_is_lower_bound')
            need(frame['splits']==frame_splits and frame['maximum_depth']==maxdepth<=24,'frame_split_depth_count')
            need(frame['conditional_gate_passed']==(bound<=threshold),'original_volume_gate')
            totals.update(counts);total_splits+=frame_splits
            checked={'case_id':frame['case_id'],'frame':frame['frame'],'verified':True,'root_count':len(proof['roots']),
                     'counts':counts,'root_box_volume_exact':str(volume),'intersection_upper_bound_exact':str(bound),
                     'intersection_upper_bound_display_mm3':float(bound),'splits':frame_splits,'maximum_depth':maxdepth,
                     'conditional_gate_passed':bound<=threshold,'proof':pid}
            result['frames'].append(checked)
            print(json.dumps({'verified':[frame['case_id'],frame['frame']],'bound':float(bound),'pass':bound<=threshold,'splits':frame_splits}),flush=True)
            del proof,certificate;gc.collect()
        need(total_splits==report['global_splits']<=4096,'original_global_split_budget')
        need(totals['pieces']==report['counts']['pieces']<=12000000,'complete_piece_budget_accounting')
        for k in ('channels','tiny_nodes','tested_nodes'):
            need(totals[k]==report['counts'].get(k,0),'complete_actual_count:'+k)
        for k in ('quadric','plane','line','empty_closed_intersection'):
            need(totals['new_'+k]==report['counts'].get('new_'+k,0),'complete_new_claim_count:'+k)
        node,sources,D=actual_control;B=checker.math.bounds(node['box_exact']);original_proof=node['observation']
        mutations=[('remove_required_projection',lambda x:x['slab']['piece_projections'].pop(),'all_unresolved_piece_projections'),
                   ('collapse_support_root',lambda x:x['combination'].__setitem__('support_sqrt_upper_exact','0'),'outward_support_square_root'),
                   ('alias_two_materials',lambda x:x.__setitem__('slab_channel',x['cylinder_channel']),'two_distinct_materials')]
        controls=[]
        for name,mutate,expected in mutations:
            altered=copy.deepcopy(original_proof);mutate(altered);failure=None
            try:checker.verify(altered,B,sources,materials,D,Counter())
            except ValueError as e:failure=str(e)
            need(failure==expected,'specific_actual_mutation_rejection:'+name)
            controls.append({'name':name,'expected_rejection':expected,'actual_rejection':failure,'passed':True})
        passes=sum(f['conditional_gate_passed'] for f in result['frames'])
        need(passes==report['conditional_pass_count'],'complete_conditional_pass_count')
        result.update(completed=True,conditional_pass_count=passes,global_splits=total_splits,totals=totals,actual_mutation_controls=controls)
    except Exception as exc:
        result['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    result.update(seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'completed':result['completed'],'passes':result.get('conditional_pass_count'),'seconds':result['seconds'],'failure':result.get('failure')}),flush=True)
    if not result['completed']:raise SystemExit(1)


if __name__=='__main__':main()
