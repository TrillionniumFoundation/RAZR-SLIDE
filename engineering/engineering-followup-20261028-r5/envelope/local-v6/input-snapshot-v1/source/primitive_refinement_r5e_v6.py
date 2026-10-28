"""Bounded new primitive-support refinement of immutable actual V5 leaves.

No V5 producer is rerun. Every old exclusion and every positive retained
remainder remains traceable. Native membership and original strict gates stay
open; only the explicit source model can receive a new conditional bound.
"""
import argparse
from datetime import datetime,timezone
from fractions import Fraction as F
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


def identity(path):
    path=Path(path)
    with path.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h}


def content_equal(a,b):return all(a[k]==b[k] for k in ('bytes','sha256'))


def bound(record):
    path=Path(record['path']);need(content_equal(identity(path),record),'bound file differs: '+str(path));return path


def module(record,name):
    path=bound(record);spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def require_scope(record):
    need(record['conditional_primitive_support_model_only'] is True and record['conditional_trim_model_only'] is True and
         record['native_primitive_semantics_verified'] is False and record['native_trim_class_membership_verified'] is False and
         record['inner_wire_hole_semantics_verified_for_native'] is False and record['original_raw_gate_reclassified'] is False and
         record['full_continuous_G2'] is False,'conditional model/native scope differs')


def archived_inputs(contract):
    root=Path(contract['base_V5_root']).resolve();bridge=json.loads(bound(contract['base_V5_input_bridge']).read_text())
    need(bridge['actual_run_id']==40645988108 and bridge['actual_request_commit']=='2ce252f25d340b056bfd350bdde8c743f915c9a4' and
         bridge['original_reports_or_certificates_edited'] is False and bridge['path_mapping_only'] is True,'actual V5 archive mapping scope differs')
    by={r['path']:r for r in bridge['files']};need(len(by)==len(bridge['files'])==25,'complete actual V5 input mapping required')
    actual={}
    for name,record in by.items():
        path=(root/name).resolve();need(path.is_relative_to(root),'archived input path escapes root')
        actual[name]=identity(path);need(content_equal(actual[name],record),'actual V5 archived bytes differ')
    for field,name in [('base_V5_actual_report','all-trim-model-frames/report.json'),
                       ('base_V5_actual_independent_report','verify-all/report.json'),
                       ('base_V5_actual_owned_supervision','all-trim-model-frames-supervision/controller.json'),
                       ('base_V5_actual_independent_owned_supervision','verify-all-supervision/controller.json')]:
        need(contract[field]==actual[name],'declared actual V5 report/receipt binding differs: '+field)
    def load(name):return json.loads(Path(actual[name]['path']).read_text())
    report=load('all-trim-model-frames/report.json');verified=load('verify-all/report.json');pipeline=load('pipeline.json')
    need(report['execution_completed'] and verified['execution_completed'] and pipeline['completed'],'prior actual V5 stages incomplete')
    need(report['trim_model_conditional_clearance_passes']==verified['trim_model_conditional_clearance_passes']==8,'actual V5 conditional count changed')
    need(pipeline['environment']['github_sha']==bridge['actual_request_commit'] and
         pipeline['source_lock_identity']['sha256']=='d05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211','prior actual V5 source anchor differs')
    lock=json.loads(bound(contract['base_V5_source_lock']).read_text())
    need(content_equal(contract['base_V5_source_lock'],pipeline['source_lock_identity']),'prior actual V5 source lock bytes differ')
    sources={r['path']:r for r in lock['r5_files']}
    for phase,label,filename,source_name in [('all_trim_model_frames','all-trim-model-frames','all-trim-model-frames/report.json','exterior_trim_r5e_v5.py'),
                                           ('verify_all','verify-all','verify-all/report.json','verify_exterior_trim_r5e_v5.py')]:
        stage=next(r for r in pipeline['stages'] if r['phase']==phase);controller=load(label+'-supervision/controller.json');item=load(filename)
        need(stage['completed'] and content_equal(stage['report'],actual[filename]),'prior actual report identity differs')
        need(controller['completed'] and controller['worker_started'] and controller['worker_exit_code']==0 and controller['resource_stop'] is None,
             'prior actual owned process did not qualify')
        need(controller['limits']['registered_math_contract_sha256']==item['contract_sha256'] and
             controller['limits']['worker']['sha256']==sources[source_name]['sha256'],'prior actual source/contract receipt differs')
        need(Path(controller['limits']['worker_output_directory'])==Path(stage['report']['path']).parent,'prior actual output binding differs')
    need(content_equal(verified['verified_producer_report'],actual['all-trim-model-frames/report.json']) and
         verified['expected_phase']=='all_trim_model_frames','prior verifier checked another actual experiment')
    need(report['native_trim_class_membership_verified'] is False and report['original_raw_gate_reclassified'] is False and
         verified['native_trim_class_membership_verified'] is False and verified['original_raw_gate_reclassified'] is False,'prior scope was changed')
    return actual,report,verified,pipeline


def retained_leaves(base,certificate):
    result=[];kept=F(0);removed=F(0)
    for root in certificate['roots']:
        nodes=root['tree']['nodes'];pending=[(0,base.decode(root['root_box_exact']))];seen=set();leaf_boxes={};total=F(0)
        while pending:
            index,cell=pending.pop();need(index not in seen and 0<=index<len(nodes),'invalid actual V5 tree traversal')
            seen.add(index);node=nodes[index];need(node['id']==index,'actual V5 node identity differs');value=base.volume(cell)
            need(value>0,'actual V5 positive cell required')
            if node['kind']=='split':
                axis=node['axis'];cut=F(node['cut_exact']);need(cell[axis][0]<cut<cell[axis][1],'actual V5 cut not internal')
                low=list(cell);high=list(cell);low[axis]=(cell[axis][0],cut);high[axis]=(cut,cell[axis][1])
                children=node['children'];need(len(children)==2 and children[0]!=children[1],'actual V5 full binary cut required')
                pending.extend([(children[1],high),(children[0],low)])
            else:
                need(node['kind'] in ['excluded','retained'] and F(node['positive_directed_volume_exact'])==value,'actual V5 leaf identity/volume differs')
                total+=value
                if node['kind']=='retained':leaf_boxes[index]=cell;kept+=value
                else:removed+=value
        need(len(seen)==len(nodes) and total==base.volume(base.decode(root['root_box_exact'])),'actual V5 tree incomplete or nonconservative')
        for index in sorted(leaf_boxes):
            result.append({'locator':[root['original_cell_index'],index],'box':leaf_boxes[index],
                           'actual_V5_leaf_record':nodes[index],'root_directed_volume_exact':nodes[index]['positive_directed_volume_exact']})
    return result,kept,removed


def separated(model,piece,channel,counters,limits):
    if counters['boundary_box_tests']>=limits['maximum_boundary_box_tests']:return 'budget'
    counters['boundary_box_tests']+=1
    for axis in range(3):
        for end in (0,1):
            if counters['support_inequality_tests']>=limits['maximum_support_inequality_tests']:return 'budget'
            counters['support_inequality_tests']+=1
            holds=piece['box'][axis][1]<=channel[axis][0] if end==0 else piece['box'][axis][0]>=channel[axis][1]
            if holds:return str(2*axis+end)
    need(len(piece['additional_slabs'])<=1,'at most one registered nonaxis slab per piece')
    for normal,interval in piece['additional_slabs']:
        need(any(normal),'nonzero registered slab normal required');target=model.project(normal,channel)
        for end in (0,1):
            if counters['support_inequality_tests']>=limits['maximum_support_inequality_tests']:return 'budget'
            counters['support_inequality_tests']+=1
            if (interval[1]<=target[0] if end==0 else interval[0]>=target[1]):
                counters['successful_nonaxis_separations']+=1;return str(6+end)
    return None


def attempt_channel(base,model,cell,sources,counters,limits):
    failures=[]
    for side,source in enumerate(sources):
        for axis in range(3):
            for end in (0,1):
                channel=base.channel_for(cell,source['whole'],axis,end);codes=[];blocker=None;counters['channels_tested']+=1
                for index,piece in enumerate(source['pieces']):
                    code=separated(model,piece,channel,counters,limits)
                    if code=='budget':
                        return {'excluded_open_interior':False,'search_stopped_at_predicate_budget':True,
                                'completed_unresolved_channels':failures,'actual_material_interference_claimed':False}
                    if code is None:blocker=index;break
                    codes.append(code)
                if blocker is None:
                    need(len(codes)==len(source['pieces']),'complete primitive support separation required')
                    return {'excluded_open_interior':True,'material_side':side,'axis':axis,'end':end,
                            'open_channel_exact':base.encode(channel),'complete_piece_separation_codes':''.join(codes),
                            'boundary_piece_count':len(codes),'closed_cell_boundary_retained_as_zero_volume_carrier':True,
                            'whole_closed_cell_disjoint_claimed':False,'nonaxis_separation_code_count':sum(c in '67' for c in codes)}
                failures.append({'material_side':side,'axis':axis,'end':end,'unresolved_piece_index':blocker})
    return {'excluded_open_interior':False,'all_registered_channels_unresolved':failures,'actual_material_interference_claimed':False}


def choose_cut(cell,sources,observation):
    candidates={};slabs=[]
    for unresolved in observation['all_registered_channels_unresolved']:
        side,index=unresolved['material_side'],unresolved['unresolved_piece_index'];piece=sources[side]['pieces'][index]
        for axis in range(3):
            lo,hi=cell[axis]
            for end,cut in enumerate(piece['box'][axis]):
                if lo<cut<hi:candidates.setdefault((axis,cut),{'kind':'model_boundary_endpoint','material_side':side,'piece_index':index,'axis':axis,'endpoint':end})
        for normal,unused in piece['additional_slabs']:
            slabs.append((piece.get('slab_source')=='exact_cylinder_patch_radial_support',side,index,normal))
    if candidates:
        def score(key):
            axis,cut=key;lo,hi=cell[axis];return min(cut-lo,hi-cut)/(hi-lo),axis,cut
        axis,cut=min(candidates,key=score);return axis,cut,candidates[(axis,cut)]
    if any(s[0] for s in slabs):slabs=[s for s in slabs if s[0]];rule='largest_registered_radial_slab_variation'
    elif slabs:rule='largest_registered_slab_variation'
    else:rule='longest_cell_interval'
    if slabs:
        values=[max(abs(n[axis])*(cell[axis][1]-cell[axis][0]) for unused,s,i,n in slabs) for axis in range(3)]
        axis=max(range(3),key=lambda k:(values[k],-k))
    else:axis=max(range(3),key=lambda k:(cell[k][1]-cell[k][0],-k))
    return axis,(cell[axis][0]+cell[axis][1])/2,{'kind':'registered_midpoint','axis':axis,'selection_rule':rule}


def refine(base,model,root,sources,counters,limits):
    nodes=[None];pending=[(0,root,0)];kept=F(0);removed=F(0);max_depth=0;reasons={};excluded=retained=0
    while pending:
        index,cell,depth=pending.pop();value=base.volume(cell);need(value>0,'positive source leaf required')
        counters['tree_nodes_visited']+=1;max_depth=max(max_depth,depth);reason=None;observation=None
        if value<=F(limits['tiny_retained_volume_exact']):reason='tiny_exact_volume_retained'
        elif counters['boundary_box_tests']>=limits['maximum_boundary_box_tests'] or counters['support_inequality_tests']>=limits['maximum_support_inequality_tests']:
            reason='global_predicate_budget_retained'
        else:
            observation=attempt_channel(base,model,cell,sources,counters,limits)
            if observation['excluded_open_interior']:
                nodes[index]={'id':index,'kind':'excluded','positive_directed_volume_exact':str(value),'certificate':observation}
                removed+=value;excluded+=1;continue
            if observation.get('search_stopped_at_predicate_budget'):reason='global_predicate_budget_retained'
            elif depth>=limits['maximum_depth']:reason='path_depth_limit_retained'
            elif counters['splits']>=limits['maximum_splits']:reason='global_split_limit_retained'
            else:
                axis,cut,witness=choose_cut(cell,sources,observation)
                need(cell[axis][0]<cut<cell[axis][1],'registered split must be strictly internal')
                low=list(cell);high=list(cell);low[axis]=(cell[axis][0],cut);high[axis]=(cut,cell[axis][1])
                a,b=base.volume(low),base.volume(high);need(a>0 and b>0 and a+b==value,'exact new leaf partition failed')
                left,right=len(nodes),len(nodes)+1;nodes.extend([None,None]);counters['splits']+=1
                nodes[index]={'id':index,'kind':'split','axis':axis,'cut_exact':str(cut),'cut_source':witness,'children':[left,right],
                              'parent_positive_directed_volume_exact':str(value),'children_positive_directed_volumes_exact':[str(a),str(b)],
                              'closed_cut_plane_retained_as_zero_volume_carrier':True,'actual_channel_observation':observation}
                children=[(left,low,depth+1),(right,high,depth+1)]
                pending.extend([children[1],children[0]] if a>=b else children);continue
        need(reason is not None,'retained leaf needs actual stop reason')
        leaf={'id':index,'kind':'retained','reason':reason,'positive_directed_volume_exact':str(value),'actual_material_interference_claimed':False}
        if observation is not None:leaf['actual_channel_observation']=observation
        nodes[index]=leaf;kept+=value;retained+=1;reasons[reason]=reasons.get(reason,0)+1
    need(all(n is not None for n in nodes) and kept+removed==base.volume(root),'new complete forest/volume conservation failed')
    return {'nodes':nodes,'retained_sum_exact':str(kept),'excluded_open_sum_exact':str(removed),
            'total_leaf_count':excluded+retained,'excluded_leaf_count':excluded,'retained_leaf_count':retained,
            'retained_reason_counts':reasons,'maximum_depth_reached':max_depth,
            'all_closed_cut_planes_and_root_boundaries_retained':True}


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();contract=json.loads(args.contract.read_text())
    need(identity(__file__)['sha256']==contract['producer_sha256'],'registered V6 producer source differs')
    base=module(contract['base_channel_source'],'r5e_v6_frozen_channel_helpers')
    model=module(contract['primitive_model_source'],'r5e_v6_primitive_support_helpers')
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();limits=contract['capacity']
    report={'schema':'razr-r5e-primitive-support-refinement-v6','phase':contract['phase'],
        'started_utc':datetime.now(timezone.utc).isoformat(),'execution_completed':False,'contract_sha256':identity(args.contract)['sha256'],
        'frames':[],'capacity':limits,'counters':{'channels_tested':0,'boundary_box_tests':0,'support_inequality_tests':0,
            'successful_nonaxis_separations':0,'splits':0,'tree_nodes_visited':0},
        'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
        'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
        'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,
        'native_Common_called':False,'compiled_error_bound_verified':False,'full_continuous_G2':False,'all_blockers_closed':False,
        'V5_producer_rerun':False,'actual_V5_conditional_passes_preserved':8,'original_V3_raw_passes_unchanged':4,
        'primitive_source_bundle':contract['primitive_source_bundle'],'primitive_model_source':contract['primitive_model_source'],
        'base_V5_input_bridge':contract['base_V5_input_bridge'],'real_retained_leaf_selection':contract['real_retained_leaf_selection'],
        'source_report_identity':contract['r4_report'],'public_input_bridge':contract['public_input_bridge'],
        'original_TOL_exact':str(F(1e-7)),'no_positive_thin_leaf_discarded':True}
    def save():
        report['seconds']=time.monotonic()-started;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        require_scope(contract)
        fixed={'wall_seconds':600,'RSS_limit_bytes':805306368,'maximum_splits':4096,'maximum_depth':24,
               'maximum_boundary_box_tests':12000000,'maximum_support_inequality_tests':12000000,
               'maximum_boundary_pieces_per_material':4096,'cylinder_angular_patch_count':64,
               'Taylor_term_count':24,'centre_grid_denominator':65536}
        need(all(limits[k]==v for k,v in fixed.items()) and F(limits['tiny_retained_volume_exact'])==F(1e-7)/100000,
             'registered original/new finite algorithm limits differ')
        phase=contract['phase'];need(phase in ['single_primitive_support_leaf','preflight_primitive_support','all_primitive_support_frames'],'registered V6 producer phase required')
        selection=json.loads(bound(contract['real_retained_leaf_selection']).read_text());chosen=(selection['case_id'],selection['frame'])
        chosen_locator=[selection['original_R4_root_index'],selection['actual_V5_leaf_node_index']]
        need(selection['actual_V5_run_id']==40645988108 and
             selection['actual_V5_request_commit']=='2ce252f25d340b056bfd350bdde8c743f915c9a4' and
             selection['new_geometric_pass_claimed'] is False and selection['original_source_values_changed'] is False,
             'actual retained-leaf selection source/scope differs')
        need(chosen==('case-028',1) and chosen_locator==[8,13],'preregistered actual first witness differs')
        if phase=='single_primitive_support_leaf':
            need((contract['case_id'],contract['frame'])==chosen,'single contract case/frame differs from actual selection')
        expected=[] if phase=='single_primitive_support_leaf' else ['single_primitive_support_leaf'] if phase=='preflight_primitive_support' else ['single_primitive_support_leaf','preflight_primitive_support']
        need([p['phase'] for p in contract['completed_prerequisites']]==expected,'actual prerequisite phase chain differs')
        for prerequisite in contract['completed_prerequisites']:
            old=json.loads(bound(prerequisite['report']).read_text());owned=json.loads(bound(prerequisite['supervisor']).read_text())
            require_scope(old)
            need(old['execution_completed'] and old['phase']==prerequisite['phase'] and owned['completed'] and owned['worker_started'] and
                 owned['worker_exit_code']==0 and owned['resource_stop'] is None,'actual prerequisite owned execution incomplete')
            need(owned['limits']['registered_math_contract_sha256']==old['contract_sha256'] and
                 owned['limits']['worker']['sha256']==contract['producer_sha256'] and
                 Path(owned['limits']['worker_output_directory']).resolve()==Path(prerequisite['report']['path']).resolve().parent,
                 'actual prerequisite source/contract/output differs')
            for key in ['primitive_source_bundle','primitive_model_source','base_V5_input_bridge','source_report_identity','public_input_bridge','real_retained_leaf_selection']:
                wanted=contract['r4_report'] if key=='source_report_identity' else contract[key]
                need(old[key]==wanted,'actual prerequisite source binding differs: '+key)
            if prerequisite['phase']=='single_primitive_support_leaf':
                need(old['primitive_support_model_conditional_clearance_passes']==1 and len(old['frames'])==1,
                     'actual single primitive-model gate did not pass')
                frame=old['frames'][0]
                need((frame['case_id'],frame['frame'])==chosen and frame['root_base_V5_leaf_locators']==[chosen_locator] and
                     F(frame['newly_excluded_open_leaf_sum_exact'])>0 and frame['applied_cylinder_face_count']>0,
                     'actual registered cylinder witness was not demonstrated')
            else:
                need(old['all_frame_capacity_observations_completed'] and len(old['frames'])==16 and
                     old['total_actual_V5_retained_roots']==1537 and old['complete_phase_maximum_tree_nodes']==9729 and
                     old['maximum_complete_piece_count_per_material']<=4096 and old['maximum_additional_slabs_per_piece']<=1,
                     'actual all16 primitive capacity preflight differs')
                need(contract['actual_capacity_basis']==prerequisite['report'],'actual capacity basis identity differs')
        if phase!='single_primitive_support_leaf':
            binding=contract['independent_single_verification'];verified=json.loads(bound(binding['report']).read_text());owned=json.loads(bound(binding['supervisor']).read_text())
            require_scope(verified)
            need(verified['execution_completed'] and verified['expected_phase']=='single_primitive_support_leaf' and
                 verified['expected_case_frames']==[list(chosen)] and verified['primitive_support_model_conditional_clearance_passes']==1,
                 'actual independent registered single-leaf pass required')
            need(verified['verified_producer_report']==contract['completed_prerequisites'][0]['report'] and
                 verified['primitive_source_bundle']==contract['primitive_source_bundle'],'independent prerequisite checked different source/producer')
            need(owned['completed'] and owned['worker_started'] and owned['worker_exit_code']==0 and owned['resource_stop'] is None and
                 owned['limits']['registered_math_contract_sha256']==verified['contract_sha256'] and
                 owned['limits']['worker']['sha256']==contract['single_verifier_source']['sha256'],
                 'independent prerequisite original owned/source gate failed')
            bound(contract['single_verifier_source'])
            need(Path(owned['limits']['worker_output_directory']).resolve()==Path(binding['report']['path']).resolve().parent,'independent prerequisite output differs')
            report['actual_independent_single_verification']=binding
        archive,prior,prior_verified,pipeline=archived_inputs(contract)
        report['actual_base_V5_report']=archive['all-trim-model-frames/report.json'];report['actual_base_V5_independent_report']=archive['verify-all/report.json']
        need(content_equal(selection['actual_V5_report'],report['actual_base_V5_report']),'selected actual source report differs')
        baseline=json.loads(bound(contract['r4_report']).read_text());need(baseline['execution_completed'],'original R4 report incomplete')
        need(content_equal(prior['source_report_identity'],contract['r4_report']),'prior V5 underlying original R4 report differs')
        need([(f['case_id'],f['frame']) for f in prior['frames']]==[(f['case_id'],f['frame']) for f in baseline['frames']] and len(prior['frames'])==16,
             'original full16 frame coverage differs')
        old_by={(f['case_id'],f['frame']):f for f in baseline['frames']}
        with gzip.open(bound(contract['primitive_source_bundle']),'rt') as stream:projection=json.load(stream)
        with gzip.open(bound(contract['V5_trim_source_bundle']),'rt') as stream:old_projection=json.load(stream)
        need(content_equal(contract['V5_trim_source_bundle'],prior['trim_source_bundle']),
             'unchanged actual V5 original material projection differs')
        need(projection['schema']=='razr-r5e-original-primitive-source-projection-v6' and
             projection['actual_V5_run_id']==40645988108 and projection['new_native_operations']==0 and
             projection['new_mathematical_qualification'] is False and projection['original_pcurve_values_changed'] is False and
             projection['native_primitive_semantics_verified'] is False,'original primitive source scope differs')
        need(content_equal(projection['actual_V5_report_identity'],report['actual_base_V5_report']) and
             content_equal(projection['original_public_R4_report_identity'],contract['r4_report']),'primitive projection base source identity differs')
        need(dict(projection['original_native_inventory_identity'],path=projection['original_native_inventory_relative_path']) in baseline['input_identities'],
             'primitive projection original native inventory is not R4-bound')
        need(len(projection['records'])==32 and len({(r['input']['case_id'],r['input']['material_id']) for r in projection['records']})==32,'complete unique material source projection required')
        old_records={(r['input']['case_id'],r['input']['material_id']):r for r in old_projection['records']}
        census={'GeomAbs_Plane':0,'GeomAbs_Cylinder':0}
        for record in projection['records']:
            key=(record['input']['case_id'],record['input']['material_id'])
            need(key in old_records and all(record[k]==old_records[key][k] for k in
                 ['input','original_complete_boundary_counts','original_complete_boundary_canonical_sha256']) and
                 record['full_original_face_records_unchanged'] is True,
                 'original whole-material identity/inventory differs from actual V5')
            need(len({f['face_index'] for f in record['candidate_faces']})==len(record['candidate_faces']),
                 'duplicate registered original primitive face')
            for face in record['candidate_faces']:
                primitive=face['source_primitive'];need(primitive in census and
                    face['complete_original_face']['local_surface']['type']=='GeomAbs_SurfaceType.'+primitive,
                    'registered original primitive class differs')
                census[primitive]+=1
        need(census=={'GeomAbs_Plane':48,'GeomAbs_Cylinder':16},'registered complete original primitive census differs')
        report['registered_source_primitive_census']=census
        bindings={(f['case_id'],f['frame']):f for f in projection['frame_bindings']}
        need(list(bindings)==[(f['case_id'],f['frame']) for f in prior['frames']],'primitive source full16 frame order differs')
        frames=prior['frames'] if phase!='single_primitive_support_leaf' else [next(f for f in prior['frames'] if (f['case_id'],f['frame'])==chosen)]
        total_roots=planes=cylinders=fallbacks=max_pieces=max_characters=max_slabs=0
        for prior_frame in frames:
            key=(prior_frame['case_id'],prior_frame['frame']);old=old_by[key];binding=bindings[key]
            name='all-trim-model-frames/'+prior_frame['certificate']['path']
            need(content_equal(prior_frame['certificate'],archive[name]) and binding['actual_V5_certificate']==dict(archive[name],path=name),
                 'primitive projection actual certificate identity differs')
            with gzip.open(Path(archive[name]['path']),'rt') as stream:prior_certificate=json.load(stream)
            need(prior_certificate['frame']=={k:v for k,v in prior_frame.items() if k!='certificate'},'actual V5 immutable certificate header differs')
            leaves,old_kept,old_removed=retained_leaves(base,prior_certificate)
            need([r['locator'] for r in leaves]==binding['actual_V5_retained_leaf_locators'] and
                 old_kept==F(prior_frame['retained_leaf_sum_exact']) and old_removed==F(prior_frame['excluded_open_leaf_sum_exact']),
                 'complete actual V5 forest or exact retained/excluded sums differ')
            need(prior_frame['original_remaining_displacement_box_exact']==binding['original_full_D']==old['full_remaining_displacement_box_exact'],
                 'complete original displacement domain differs')
            if phase=='single_primitive_support_leaf':
                leaves=[r for r in leaves if r['locator']==chosen_locator];need(len(leaves)==1,'exact selected actual retained leaf required')
                need(base.encode(leaves[0]['box'])==selection['leaf_box_exact'] and leaves[0]['actual_V5_leaf_record']==selection['actual_V5_leaf_record'] and
                     leaves[0]['root_directed_volume_exact']==selection['positive_directed_volume_exact'] and
                     content_equal(selection['actual_V5_certificate'],archive[name]),'actual selected V5 leaf/identity changed')
                need(selection['original_full_D']==prior_frame['original_remaining_displacement_box_exact'] and
                     selection['pair']==prior_frame['pair'] and
                     selection['actual_V5_original_root_record']==next(r for r in prior_certificate['roots'] if r['original_cell_index']==chosen_locator[0]),
                     'selected original whole root/pair/full displacement differs')
            sources,boundary=model.build_boundary(prior_certificate['boundary_refinement'],prior_frame,projection,limits)
            planes+=boundary['applied_plane_count'];cylinders+=boundary['applied_cylinder_count'];fallbacks+=boundary['retained_original_faces_after_rejection']
            total_roots+=len(leaves);max_pieces=max(max_pieces,*(len(s['pieces']) for s in sources))
            for source in sources:
                for piece in source['pieces']:
                    max_slabs=max(max_slabs,len(piece['additional_slabs']))
                    values=[v for part in piece['box'] for v in part]
                    for normal,interval in piece['additional_slabs']:values.extend(normal);values.extend(interval)
                    max_characters=max(max_characters,*(len(str(v)) for v in values))
            frame={'case_id':key[0],'frame':key[1],'pair':prior_frame['pair'],'original_raw_proof_identity':old['proof'],
                   'original_remaining_displacement_box_exact':prior_frame['original_remaining_displacement_box_exact'],
                   'base_V5_certificate':archive[name],'base_V5_frame_conditional_upper_exact_mm3':prior_frame['trim_model_conditional_upper_exact_mm3'],
                   'base_V5_retained_leaf_sum_exact':str(old_kept),'base_V5_excluded_open_leaf_sum_exact':str(old_removed),
                   'root_base_V5_leaf_locators':[r['locator'] for r in leaves],'root_count':len(leaves),
                   'source_piece_counts':[len(s['pieces']) for s in sources],'primitive_source_bundle':contract['primitive_source_bundle'],
                   'applied_plane_face_count':boundary['applied_plane_count'],'applied_cylinder_face_count':boundary['applied_cylinder_count'],
                   'retained_original_face_count_after_rejection':boundary['retained_original_faces_after_rejection'],
                   'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
                   'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
                   'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,'full_continuous_G2':False}
            if phase=='preflight_primitive_support':
                frame['new_clearance_result_claimed']=False
                frame['face_statuses']=[{'material_key':s['material_key'],'faces':[{'face_index':f['face_index'],'applied':f['applied'],
                    'primitive':f.get('primitive'),'reason':f.get('retained_original_face_reason'),
                    'angular_patch_count':f.get('angular_patch_count',0)} for f in s['face_certificates']]} for s in boundary['sources']]
            else:
                roots=[];kept=F(0);removed=F(0);leaf_count=depth=0;before=dict(report['counters'])
                for leaf in leaves:
                    tree=refine(base,model,leaf['box'],sources,report['counters'],limits)
                    roots.append({'base_V5_leaf_locator':leaf['locator'],'root_box_exact':base.encode(leaf['box']),
                                  'root_directed_volume_exact':leaf['root_directed_volume_exact'],'tree':tree})
                    kept+=F(tree['retained_sum_exact']);removed+=F(tree['excluded_open_sum_exact']);leaf_count+=tree['total_leaf_count'];depth=max(depth,tree['maximum_depth_reached'])
                need(kept+removed==sum((F(l['root_directed_volume_exact']) for l in leaves),F(0)),'all new root exact measure not conserved')
                if phase=='all_primitive_support_frames':
                    need(kept+removed==old_kept,'new exclusions must be deducted from prior retained sum, not selected/min bound')
                    selected=min(kept,F(old['coarse_whole_support_upper_exact_mm3']))
                    need(selected<=F(prior_frame['trim_model_conditional_upper_exact_mm3']),'new certified model bound grew beyond prior selected bound')
                else:selected=kept
                frame.update(retained_leaf_sum_exact=str(kept),newly_excluded_open_leaf_sum_exact=str(removed),new_root_sum_exact=str(kept+removed),
                    primitive_support_model_conditional_upper_exact_mm3=str(selected),primitive_support_model_conditional_upper_mm3=float(selected),
                    primitive_support_model_conditional_clearance_gate_passed=selected<=F(1e-7),
                    all_V5_and_new_closed_carriers_retained=True,total_leaf_count=leaf_count,maximum_depth_reached=depth,
                    exact_splits_this_frame=report['counters']['splits']-before['splits'],
                    exact_piece_tests_this_frame=report['counters']['boundary_box_tests']-before['boundary_box_tests'],
                    exact_support_inequality_tests_this_frame=report['counters']['support_inequality_tests']-before['support_inequality_tests'])
                destination=args.output/(key[0]+'-frame-'+str(key[1])+'-primitive-support.json.gz')
                payload={'schema':'razr-r5e-primitive-support-tree-v6','frame':frame,'boundary_refinement':boundary,'roots':roots,
                         'actual_V5_excluded_open_sum_preserved_exact':str(old_removed),'V5_producer_rerun':False}
                with destination.open('wb') as raw:
                    with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:stream.write((json.dumps(payload,separators=(',',':'))+'\n').encode())
                frame['certificate']=dict(identity(destination),path=destination.name)
            report['frames'].append(frame);save()
            need(report['seconds']<=600 and report['peak_RSS_bytes']<=805306368,'registered process budget exceeded')
        report.update(total_actual_V5_retained_roots=total_roots,complete_phase_maximum_tree_nodes=total_roots+8192,
                      complete_phase_maximum_leaves=total_roots+4096,maximum_complete_piece_count_per_material=max_pieces,
                      maximum_exact_coordinate_character_count=max_characters,maximum_additional_slabs_per_piece=max_slabs,
                      applied_plane_face_occurrences=planes,applied_cylinder_face_occurrences=cylinders,
                      retained_original_face_occurrences_after_rejection=fallbacks)
        report['primitive_support_model_conditional_clearance_passes']=sum(f.get('primitive_support_model_conditional_clearance_gate_passed',False) for f in report['frames'])
        report['all_frame_capacity_observations_completed']=len(report['frames'])==(1 if phase=='single_primitive_support_leaf' else 16)
        need(report['all_frame_capacity_observations_completed'] and report['counters']['splits']<=4096 and
             report['counters']['boundary_box_tests']<=12000000 and report['counters']['support_inequality_tests']<=12000000,'registered finite phase state differs')
        need(identity(__file__)['sha256']==contract['producer_sha256'] and identity(args.contract)['sha256']==report['contract_sha256'],'producer source/contract changed')
        for key in ['primitive_model_source','primitive_source_bundle','base_V5_input_bridge','base_channel_source','r4_report','real_retained_leaf_selection','V5_trim_source_bundle']:bound(contract[key])
        for item in archive.values():bound(item)
        report['source_and_contract_unchanged']=True;report['execution_completed']=True
    except BaseException as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        print(json.dumps({k:report.get(k) for k in ['phase','execution_completed','primitive_support_model_conditional_clearance_passes','counters','seconds','peak_RSS_bytes','failure']}),flush=True)


if __name__=='__main__':main()
