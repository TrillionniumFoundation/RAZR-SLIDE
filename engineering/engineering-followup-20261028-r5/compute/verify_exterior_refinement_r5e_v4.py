"""Independent reconstruction of V4 exact partition trees and leaf certificates.

The producer/refiner is not imported. The earlier separate certificate checker
is reused only for complete-boundary channel inequalities and blocked records.
"""
import argparse
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import time
import traceback


def need(ok,message):
    if not ok:raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def bound(record,parent=None):
    path=Path(record['path']) if parent is None else parent/record['path']
    need(path.stat().st_size==record['bytes'] and digest(path)==record['sha256'],'input identity differs');return path


def load_checker(contract):
    path=bound(contract['base_verifier_source']);spec=importlib.util.spec_from_file_location('r5e_v4_separate_channel_checker',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def complete_phase(producer,contract,baseline):
    phase=contract['expected_phase'];need(producer['phase']==phase,'actual phase differs')
    expected=[tuple(x) for x in contract['expected_case_frames']]
    actual=[(r['case_id'],r['frame']) for r in producer['frames']]
    original=[(r['case_id'],r['frame']) for r in baseline['frames']]
    need(len(actual)==len(set(actual)) and len(expected)==len(set(expected)),'duplicate frame')
    need(actual==expected,'missing, extra or reordered frame')
    if phase=='all_raw_refined':need(actual==original and len(actual)==16,'all original16 frames required')
    elif phase=='single_retained_cell':need(len(actual)==1 and actual[0] in original,'one original selected frame required')
    else:raise ValueError('unexpected verification phase')


def phase_controls(producer,contract,baseline):
    rows=[]
    for name,changes in [('missing-frame',{'frames':producer['frames'][:-1]}),
                         ('duplicate-frame',{'frames':producer['frames']+[producer['frames'][0]]}),
                         ('incorrect-phase',{'phase':'preflight'})]:
        error=None
        try:complete_phase(dict(producer,**changes),contract,baseline)
        except ValueError as exc:error=str(exc)
        need(error is not None,'bad phase control accepted');rows.append({'name':name,'actual_rejected':True,'reason':error})
    return rows


def root_coverage(frame,certificate,expected_indices):
    need(frame['root_original_cell_indices']==expected_indices and
         [r['original_cell_index'] for r in certificate['roots']]==expected_indices and
         frame['root_count']==len(expected_indices),
         'missing, extra, duplicate or reordered original root cells')


def root_controls(frame,certificate,expected_indices):
    rows=[]
    for name,roots in [('omitted-original-root',certificate['roots'][:-1]),
                       ('duplicate-original-root',certificate['roots']+[certificate['roots'][0]])]:
        error=None
        try:root_coverage(frame,dict(certificate,roots=roots),expected_indices)
        except ValueError as exc:error=str(exc)
        need(error is not None,'bad root coverage accepted');rows.append({'name':name,'actual_rejected':True,'reason':error})
    return rows


def verify_tree(base,tree,root,sources,limits):
    nodes=tree['nodes'];need(nodes and all(type(n['id']) is int and n['id']==i for i,n in enumerate(nodes)),'contiguous explicit tree identities')
    stack=[(0,root,0)];seen=set();kept=Q(0);removed=Q(0);splits=leaves=excluded=checked=0;depth_max=0
    sample=None;split_sample=None;reasons={}
    while stack:
        index,cell,depth=stack.pop();need(index not in seen and 0<=index<len(nodes),'duplicate, cyclic or missing tree node');seen.add(index)
        node=nodes[index];value=base.signed_measure(cell);depth_max=max(depth_max,depth)
        need(depth<=limits['maximum_depth'],'path depth budget exceeded')
        if node['kind']=='split':
            axis=node['axis'];need(type(axis) is int and 0<=axis<3,'split axis')
            point=Q(node['cut_exact']);need(cell[axis][0]<point<cell[axis][1],'split strictly inside parent required')
            w=node['cut_source'];s,i,k,e=w['material_side'],w['piece_index'],w['axis'],w['endpoint']
            need(type(s) is int and 0<=s<len(sources) and type(i) is int and 0<=i<len(sources[s][0]),'cut source piece index')
            need(type(k) is int and k==axis and type(e) is int and e in (0,1),'cut source coordinate')
            need(point==sources[s][0][i][axis][e],'cut is not an original complete boundary endpoint')
            child=node['children'];need(type(child) is list and len(child)==2 and all(type(x) is int and index<x<len(nodes) for x in child) and child[0]!=child[1],'two distinct forward child indices required')
            a=list(cell);b=list(cell);a[axis]=(cell[axis][0],point);b[axis]=(point,cell[axis][1])
            av,bv=base.signed_measure(a),base.signed_measure(b)
            need(av+bv==value and Q(node['parent_positive_directed_volume_exact'])==value,'parent directed volume conservation')
            need(list(map(Q,node['children_positive_directed_volumes_exact']))==[av,bv],'child directed volumes differ')
            need(node['closed_cut_plane_retained_as_zero_volume_carrier'] is True,'closed cut carrier omitted')
            stack.extend([(child[1],b,depth+1),(child[0],a,depth+1)]);splits+=1
            if split_sample is None:split_sample=(index,cell)
        elif node['kind']=='excluded':
            need(Q(node['positive_directed_volume_exact'])==value,'excluded leaf volume differs')
            checked+=base.check_exclusion(node['certificate'],cell,sources);removed+=value;leaves+=1;excluded+=1
            if sample is None:sample=(node['certificate'],cell)
        elif node['kind']=='retained':
            need(Q(node['positive_directed_volume_exact'])==value and node['actual_material_interference_claimed'] is False,'retained full directed volume/scope differs')
            reason=node['reason'];need(reason in ['tiny_exact_volume_retained','global_predicate_budget_retained','path_depth_limit_retained','global_split_limit_retained','no_original_blocking_endpoint_inside_cell'],'unregistered retention reason')
            if reason=='tiny_exact_volume_retained':need(value<=Q(limits['tiny_retained_volume_exact']),'tiny retained leaf threshold differs')
            if reason=='path_depth_limit_retained':need(depth==limits['maximum_depth'],'incorrect path-depth stop')
            if 'actual_channel_observation' in node:
                observation=node['actual_channel_observation']
                need(observation['excluded_open_interior'] is False and observation['actual_material_interference_claimed'] is False,'retained observation overclaims material collision')
                if not observation.get('search_stopped_at_predicate_budget'):base.check_blocked(observation,cell,sources)
            kept+=value;leaves+=1;reasons[reason]=reasons.get(reason,0)+1
        else:raise ValueError('unknown partition tree disposition')
    need(len(seen)==len(nodes),'unreachable or unvisited tree node')
    need(kept+removed==base.signed_measure(root),'root volume not conserved')
    need(kept==Q(tree['retained_sum_exact']) and removed==Q(tree['excluded_open_sum_exact']),'tree sums differ')
    need(leaves==tree['total_leaf_count'] and excluded==tree['excluded_leaf_count'] and leaves-excluded==tree['retained_leaf_count'],'tree leaf counts differ')
    need(reasons==tree['retained_reason_counts'] and depth_max==tree['maximum_depth_reached'],'tree stop/depth metadata differs')
    need(tree['all_closed_cut_planes_and_root_boundaries_retained'] is True,'closed zero-volume carriers omitted')
    need(len(nodes)==2*splits+1 and leaves==splits+1,'full binary partition topology count')
    return {'kept':kept,'removed':removed,'nodes':len(nodes),'splits':splits,'leaves':leaves,'excluded_leaves':excluded,
            'checked_boundary_pieces':checked,'sample_exclusion':sample,'sample_split':split_sample,'depth':depth_max}


def tree_controls(base,tree,root,sources,limits):
    checked=verify_tree(base,tree,root,sources,limits);need(checked['sample_split'] is not None,'actual split required for partition controls')
    selected,parent=checked['sample_split'];answers=[]
    def reject(name,alter):
        copied=json.loads(json.dumps(tree));alter(copied)
        error=None
        try:verify_tree(base,copied,root,sources,limits)
        except (ValueError,IndexError,KeyError,TypeError) as exc:error=str(exc)
        need(error is not None,'corrupt partition accepted: '+name);answers.append({'name':name,'actual_rejected':True,'reason':error})
    reject('omitted-partition-child',lambda t:t['nodes'][selected].update(children=t['nodes'][selected]['children'][:1]))
    reject('duplicated-partition-child',lambda t:t['nodes'][selected].update(children=[t['nodes'][selected]['children'][0]]*2))
    reject('cut-on-parent-boundary',lambda t:t['nodes'][selected].update(cut_exact=str(parent[t['nodes'][selected]['axis']][0])))
    reject('discarded-closed-cut-plane',lambda t:t['nodes'][selected].update(closed_cut_plane_retained_as_zero_volume_carrier=False))
    reject('incorrect-positive-directed-volume',lambda t:t['nodes'][selected].update(parent_positive_directed_volume_exact='0'))
    reject('omitted-pending-leaf-node',lambda t:t['nodes'].pop())
    smallest_leaf=min((n for n in tree['nodes'] if n['kind']!='split'),key=lambda n:Q(n['positive_directed_volume_exact']))
    leaf_index=smallest_leaf['id']
    reject('discarded-smallest-nonzero-leaf-volume',lambda t:t['nodes'][leaf_index].update(positive_directed_volume_exact='0'))
    answers[-1]['actual_original_leaf_kind']=smallest_leaf['kind']
    answers[-1]['actual_original_positive_volume_exact']=smallest_leaf['positive_directed_volume_exact']
    return answers


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();contract=json.loads(args.contract.read_text());need(digest(__file__)==contract['verifier_sha256'],'registered V4 verifier identity')
    base=load_checker(contract);args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report={'schema':'razr-r5e-independent-endpoint-tree-verification-v4','execution_completed':False,'producer_code_imported':False,
            'contract_sha256':digest(args.contract),'verified_producer_report':contract['producer_report'],
            'frames':[],'phase_negative_controls':[],'root_coverage_negative_controls':[],'channel_negative_controls':[],'partition_negative_controls':[],
            'native_Common_called':False,'native_material_semantics_verified':False,'compiled_error_verified':False,'full_continuous_G2':False}
    def save():
        report['seconds']=time.monotonic()-start;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        producer_path=bound(contract['producer_report']);producer=json.loads(producer_path.read_text());need(producer['execution_completed'],'complete actual producer required')
        controller=json.loads(bound(contract['producer_owned_supervision']).read_text())
        need(controller['completed'] and controller['worker_started'] and controller['worker_exit_code']==0 and controller['resource_stop'] is None,'producer owned resource qualification absent')
        need(controller['limits']['registered_math_contract_sha256']==producer['contract_sha256'],'producer actual contract differs')
        need(Path(controller['limits']['worker_output_directory']).resolve()==producer_path.parent.resolve(),'actual producer output binding differs')
        baseline=json.loads(bound(producer['source_report_identity']).read_text());complete_phase(producer,contract,baseline)
        report['phase_negative_controls']=phase_controls(producer,contract,baseline)
        report['expected_phase']=contract['expected_phase'];report['expected_case_frames']=contract['expected_case_frames']
        old_by={(r['case_id'],r['frame']):r for r in baseline['frames']}
        bridge_json=json.loads(bound(contract['public_input_bridge']).read_text());need(producer['public_input_bridge']==contract['public_input_bridge'],'producer/verifier public bridge differs')
        need(bridge_json['source_commit']=='c5f6606924937d716b007cd3ffa8e54df8ecfa5d' and len(bridge_json['files'])==19 and all(r['decoded_json_equal'] and not r['changed_strings'] for r in bridge_json['files']),'unchanged complete public bridge required')
        bridge={r['path']:r for r in bridge_json['files']};need(len(bridge)==19,'duplicate public bridge path')
        selection=json.loads(bound(contract['real_retained_cell_selection']).read_text());limits=producer['capacity']
        need(limits['maximum_splits']==4096 and limits['maximum_depth']==24 and limits['maximum_boundary_box_tests']==12000000 and Q(limits['tiny_retained_volume_exact'])==Q(1e-7)/100000,'registered finite policy differs')
        all_splits=all_nodes=all_leaves=0
        for row in producer['frames']:
            key=(row['case_id'],row['frame']);old=old_by[key];entry=bridge['support-v4/'+old['proof']['path']]
            need(row['original_raw_proof_identity']==old['proof'] and entry['raw_identity']=={k:old['proof'][k] for k in ('bytes','sha256')},'raw source mapping differs')
            need({k:row['source_proof'][k] for k in ('bytes','sha256')}==entry['public_identity'],'actual public source identity differs')
            with gzip.open(bound(row['source_proof']),'rt') as stream:proof=json.load(stream)
            need(hashlib.sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()==entry['public_canonical_json_sha256'],'decoded public source differs')
            need(row['original_remaining_displacement_box_exact']==proof['full_remaining_displacement_box_exact']==old['full_remaining_displacement_box_exact'],'complete original D differs')
            sources=base.reconstructed_sources(proof,stationary=False)
            with gzip.open(bound(row['certificate'],producer_path.parent),'rt') as stream:certificate=json.load(stream)
            old_cells=proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
            expected_indices=[selection['original_raw_cell_index']] if contract['expected_phase']=='single_retained_cell' else list(range(len(old_cells)))
            root_coverage(row,certificate,expected_indices)
            if not report['root_coverage_negative_controls']:report['root_coverage_negative_controls']=root_controls(row,certificate,expected_indices)
            kept=Q(0);removed=Q(0);checked=0;splits=leaves=nodes=0;max_depth=0
            for root_record,index in zip(certificate['roots'],expected_indices):
                old_cell=old_cells[index]
                need(root_record['root_box_exact']==old_cell['box_exact'] and Q(root_record['root_directed_volume_exact'])==Q(old_cell['positive_directed_volume_exact']),'original positive root changed')
                root=base.box(root_record['root_box_exact']);stats=verify_tree(base,root_record['tree'],root,sources,limits)
                kept+=stats['kept'];removed+=stats['removed'];checked+=stats['checked_boundary_pieces'];splits+=stats['splits'];nodes+=stats['nodes'];leaves+=stats['leaves'];max_depth=max(max_depth,stats['depth'])
                if not report['channel_negative_controls'] and stats['sample_exclusion']:
                    sample,cell=stats['sample_exclusion'];report['channel_negative_controls']=base.negative_controls(sample,cell,sources)
                if not report['partition_negative_controls'] and stats['sample_split']:
                    report['partition_negative_controls']=tree_controls(base,root_record['tree'],root,sources,limits)
            need(kept==Q(row['retained_leaf_sum_exact']) and removed==Q(row['excluded_open_leaf_sum_exact']) and kept+removed==Q(row['original_root_sum_exact']),'frame exact directed sums differ')
            need(row['all_closed_cut_planes_and_original_cell_boundaries_retained'] is True,'frame zero-volume carrier lost')
            selected=kept
            if contract['expected_phase']=='all_raw_refined':
                need(kept+removed==Q(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']),'complete original raw sum differs')
                selected=min(kept,Q(old['coarse_whole_support_upper_exact_mm3']))
                need(selected<=Q(old['conditional_complete_material_intersection_upper_exact_mm3']) and old['original_min_volume_plus_TOL_gate_passed'] is True and row['original_min_volume_plus_TOL_gate_passed'] is True,'inherited upper sanity gate differs')
            need(selected==Q(row['selected_conditional_raw_upper_exact_mm3']) and row['original_clearance_gate_passed']==(selected<=Q(1e-7)),'unchanged original gate differs')
            need(splits==row['exact_splits_this_frame'] and leaves==row['total_leaf_count'] and max_depth==row['maximum_depth_reached'],'actual tree metadata differs')
            all_splits+=splits;all_nodes+=nodes;all_leaves+=leaves
            report['frames'].append({'case_id':key[0],'frame':key[1],'original_roots_verified':len(expected_indices),'exact_tree_nodes_verified':nodes,
                                     'exact_splits_verified':splits,'all_retained_and_excluded_leaves_verified':leaves,
                                     'complete_boundary_piece_separations_checked':checked,'retained_upper_exact_mm3':str(selected),
                                     'original_clearance_gate_passed':selected<=Q(1e-7)})
            save()
        need(all_splits==producer['counters']['splits']<=limits['maximum_splits'] and all_nodes==producer['counters']['tree_nodes_visited'],'global actual tree count differs')
        need(producer['counters']['boundary_box_tests']<=limits['maximum_boundary_box_tests'],'actual predicate counter exceeds registered budget')
        need(report['channel_negative_controls'] and report['partition_negative_controls'],'actual geometric and partition controls required')
        report.update(total_tree_nodes_verified=all_nodes,total_splits_verified=all_splits,total_leaves_verified=all_leaves,
                      conditional_clearance_passes=sum(r['original_clearance_gate_passed'] for r in report['frames']))
        need(digest(__file__)==contract['verifier_sha256'] and digest(Path(contract['base_verifier_source']['path']))==contract['base_verifier_source']['sha256'] and
             digest(args.contract)==report['contract_sha256'],'verifier source or contract changed')
        report['execution_completed']=True
    except BaseException as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        save();print(json.dumps({k:report.get(k) for k in ['execution_completed','conditional_clearance_passes','total_tree_nodes_verified','seconds','peak_RSS_bytes','failure']}),flush=True)


if __name__=='__main__':main()
