"""Refine the actual V6 retained forest with complete closed-UV exterior paths."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import time
import traceback

SHARED_INPUT_FIELDS = ['r4_report','r4_independent_report','r4_stationary_diagnostic','public_input_bridge','method',
    'base_channel_source','base_verifier_source','single_verifier_source','planar_producer_source','planar_model_source',
    'primitive_producer_source','primitive_model_source','primitive_source_bundle','base_V6_verifier_source',
    'base_V6_input_bridge','base_V6_source_lock','base_V6_actual_report','base_V6_actual_independent_report',
    'base_V5_input_bridge','base_V5_source_lock','base_V5_verifier_source','V5_trim_source_bundle',
    'base_V5_actual_report','base_V5_actual_independent_report','real_retained_leaf_selection','static_source_capacity']


def need(ok,message):
    if not ok: raise ValueError(message)


def identity(path):
    path=Path(path)
    with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest}


def equal(a,b): return all(a[k]==b[k] for k in ('bytes','sha256'))
def bound(record):
    path=Path(record['path']);need(equal(identity(path),record),'bound file differs: '+str(path));return path
def read(record): return json.loads(bound(record).read_text())
def canonical(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def module(record,name):
    path=bound(record);spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def scope(record):
    for key in ('conditional_planar_exterior_model_only','conditional_primitive_support_model_only','conditional_trim_model_only'):
        need(record[key] is True,'missing conditional source-model scope: '+key)
    for key in ('native_planar_region_semantics_verified','native_primitive_semantics_verified','native_trim_class_membership_verified',
                'inner_wire_hole_semantics_verified_for_native','original_raw_gate_reclassified','full_continuous_G2'):
        need(record[key] is False,'unverified source/native qualification changed: '+key)


def actual_v6_inputs(contract):
    root=Path(contract['base_V6_root']).resolve();bridge=read(contract['base_V6_input_bridge'])
    need(bridge['schema']=='razr-r5e-immutable-actual-v6-input-bridge-v7' and bridge['actual_execution_kind']=='local_owned_pipeline' and
         bridge['original_reports_or_certificates_edited'] is False and bridge['path_mapping_only'] is True and
         bridge['actual_pipeline_source_lock_sha256']=='5cf2c18e7971912949e7e7167451cf547e291be421f205d78ef668fd7ab5b499',
         'actual complete V6 archive scope differs')
    actual={}
    for row in bridge['files']:
        path=(root/row['path']).resolve();need(path.is_relative_to(root),'archived V6 input escapes root')
        actual[row['path']]=identity(path);need(equal(actual[row['path']],row),'actual V6 archived bytes differ')
    need(len(actual)==len(bridge['files'])==53,'all53 unique actual V6 files required')
    def load(name):return json.loads(Path(actual[name]['path']).read_text())
    producer=load('all-primitive-support-frames/report.json');checker=load('verify-all/report.json');pipeline=load('pipeline.json')
    need(producer['execution_completed'] and checker['execution_completed'] and pipeline['completed'],'actual V6 was incomplete')
    need(producer['primitive_support_model_conditional_clearance_passes']==checker['primitive_support_model_conditional_clearance_passes']==8,
         'actual V6 false and true gates changed')
    need(equal(contract['base_V6_actual_report'],actual['all-primitive-support-frames/report.json']) and
         equal(contract['base_V6_actual_independent_report'],actual['verify-all/report.json']),'actual V6 report bindings differ')
    need(equal(contract['base_V6_source_lock'],pipeline['source_lock_identity']),'actual V6 source lock differs')
    lock=read(contract['base_V6_source_lock']);sources={r['path']:r for r in lock['r5_files']}
    for label,filename in [('all-primitive-support-frames','primitive_refinement_r5e_v6.py'),('verify-all','verify_primitive_support_r5e_v6.py')]:
        item=load(label+'/report.json');controller=load(label+'-supervision/controller.json');stage=next(s for s in pipeline['stages'] if s['label']==label)
        need(controller['completed'] and controller['worker_started'] and controller['worker_exit_code']==0 and controller['resource_stop'] is None,
             'actual V6 original owned stage did not complete')
        need(stage['completed'] and equal(stage['report'],actual[label+'/report.json']) and
             controller['limits']['registered_math_contract_sha256']==item['contract_sha256'] and
             controller['limits']['worker']['sha256']==sources[filename]['sha256'],'actual V6 source/contract/report receipt differs')
        need(Path(controller['limits']['worker_output_directory'])==Path(stage['report']['path']).parent,'actual V6 output binding differs')
    need(equal(checker['verified_producer_report'],actual['all-primitive-support-frames/report.json']),'actual V6 checker checked another report')
    need(checker['expected_phase']=='all_primitive_support_frames' and producer['native_primitive_semantics_verified'] is False and
         checker['native_primitive_semantics_verified'] is False and producer['original_raw_gate_reclassified'] is False,
         'actual V6 qualified scope was changed')
    return actual,producer,checker,pipeline


def retained_v6_leaves(base,certificate):
    leaves=[];kept=F(0);removed=F(0)
    for root_index,root in enumerate(certificate['roots']):
        nodes=root['tree']['nodes'];pending=[(0,base.decode(root['root_box_exact']),0)];seen=set();total=F(0)
        while pending:
            index,cell,depth=pending.pop();need(index not in seen and 0<=index<len(nodes),'actual V6 source tree invalid')
            seen.add(index);node=nodes[index];need(node['id']==index,'actual V6 node identity differs');volume=base.volume(cell)
            need(volume>0,'actual V6 positive leaf required')
            if node['kind']=='split':
                axis=node['axis'];cut=F(node['cut_exact']);need(cell[axis][0]<cut<cell[axis][1],'actual V6 cut not strictly internal')
                low=list(cell);high=list(cell);low[axis]=(cell[axis][0],cut);high[axis]=(cut,cell[axis][1]);children=node['children']
                need(len(children)==2 and children[0]!=children[1],'complete original V6 partition required')
                pending.extend([(children[1],high,depth+1),(children[0],low,depth+1)])
            else:
                need(node['kind'] in ('excluded','retained') and F(node['positive_directed_volume_exact'])==volume,'actual V6 leaf measure differs')
                total+=volume
                if node['kind']=='retained':
                    kept+=volume;leaves.append({'locator':[root_index,index],'box':cell,'volume_exact':str(volume),'node':node,'depth':depth,
                                               'base_V5_leaf_locator':root['base_V5_leaf_locator']})
                else:removed+=volume
        need(len(seen)==len(nodes) and total==base.volume(base.decode(root['root_box_exact'])),'actual V6 complete source tree coverage differs')
    return leaves,kept,removed


def runtime_sources(model,boundary):
    return [{'whole':model.box(source['known_whole_exact']),
             'pieces':[{'box':model.box(piece['box_exact']),
                        'additional_slabs':[(model.vec(s['normal_exact']),tuple(map(F,s['bounds_exact']))) for s in piece['additional_slabs']],
                        'slab_source':piece['additional_slabs'][0]['source'] if piece['additional_slabs'] else None}
                       for piece in source['pieces']]} for source in boundary['sources']]


def spatial_separator(model,piece,channel,counters,limits):
    if counters['boundary_box_tests']>=limits['maximum_boundary_box_tests']:return 'budget'
    counters['boundary_box_tests']+=1;counters['spatial_boundary_piece_tests']+=1
    for axis in range(3):
        for end in (0,1):
            if not model.count_inequality(counters,limits,False):return 'budget'
            holds=piece['box'][axis][1]<=channel[axis][0] if end==0 else piece['box'][axis][0]>=channel[axis][1]
            if holds:return str(2*axis+end)
    need(len(piece['additional_slabs'])<=1,'at most one inherited nonaxis slab per spatial piece')
    for normal,interval in piece['additional_slabs']:
        target=model.project(normal,channel)
        for end in (0,1):
            if not model.count_inequality(counters,limits,False):return 'budget'
            if interval[1]<=target[0] if end==0 else interval[0]>=target[1]:
                counters['successful_nonaxis_separations']+=1;return str(6+end)
    return None


def attempt_channel(base,model,cell,sources,planar,counters,limits):
    failures=[]
    for side,source in enumerate(sources):
        for axis in range(3):
            for end in (0,1):
                channel=base.channel_for(cell,source['whole'],axis,end);codes=[];uv_proofs=[];blocker=None
                counters['channels_tested']+=1
                for index,piece in enumerate(source['pieces']):
                    code=spatial_separator(model,piece,channel,counters,limits);uv=None
                    if code=='budget':
                        return {'excluded_open_interior':False,'search_stopped_at_predicate_budget':True,
                                'completed_unresolved_channels':failures,'actual_material_interference_claimed':False,
                                'incomplete_spatial_channel':{'material_side':side,'axis':axis,'end':end,'piece_index_at_stop':index,'completed_piece_prefix_count':len(codes)}}
                    if code is None and (side,index) in planar:
                        uv=model.planar_channel_exclusion(planar[(side,index)],channel,counters,limits)
                        if uv.get('search_stopped_at_predicate_budget'):
                            return {'excluded_open_interior':False,'search_stopped_at_predicate_budget':True,
                                    'completed_unresolved_channels':failures,'actual_material_interference_claimed':False,
                                    'incomplete_spatial_channel':{'material_side':side,'axis':axis,'end':end,'piece_index_at_stop':index,
                                                                 'completed_piece_prefix_count':len(codes),'planar_exterior_attempt':uv}}
                        if uv['excluded']:
                            code='u';uv_proofs.append({'piece_index':index,'certificate':uv['certificate']})
                            counters['successful_planar_exterior_separations']+=1
                    if code is None:
                        blocker={'material_side':side,'axis':axis,'end':end,'unresolved_piece_index':index}
                        if uv is not None:blocker['planar_exterior_attempt']=uv
                        break
                    codes.append(code)
                if blocker is None:
                    need(len(codes)==len(source['pieces']),'complete material carrier must be separated')
                    need([r['piece_index'] for r in uv_proofs]==[i for i,c in enumerate(codes) if c=='u'],'complete unique UV-proof map required')
                    return {'excluded_open_interior':True,'material_side':side,'axis':axis,'end':end,
                            'open_channel_exact':base.encode(channel),'complete_piece_separation_codes':''.join(codes),
                            'boundary_piece_count':len(codes),'planar_exterior_certificates':uv_proofs,
                            'closed_cell_boundary_retained_as_zero_volume_carrier':True,'whole_closed_cell_disjoint_claimed':False,
                            'nonaxis_separation_code_count':sum(c in '67' for c in codes),'planar_exterior_separation_code_count':len(uv_proofs)}
                failures.append(blocker)
    return {'excluded_open_interior':False,'all_registered_channels_unresolved':failures,'actual_material_interference_claimed':False}


def choose_cut(cell,sources,observation):
    # The frozen V6 deterministic split strategy is retained; the new proof rule is the change.
    candidates={};slabs=[]
    for unresolved in observation['all_registered_channels_unresolved']:
        side,index=unresolved['material_side'],unresolved['unresolved_piece_index'];piece=sources[side]['pieces'][index]
        for axis in range(3):
            lo,hi=cell[axis]
            for end,cut in enumerate(piece['box'][axis]):
                if lo<cut<hi:candidates.setdefault((axis,cut),{'kind':'model_boundary_endpoint','material_side':side,'piece_index':index,'axis':axis,'endpoint':end})
        for normal,unused in piece['additional_slabs']:slabs.append((piece.get('slab_source')=='exact_cylinder_patch_radial_support',side,index,normal))
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


def refine(base,model,root,sources,planar,counters,limits):
    nodes=[None];pending=[(0,root,0)];kept=F(0);removed=F(0);max_depth=0;reasons={};excluded=retained=uv_used=0
    while pending:
        index,cell,depth=pending.pop();value=base.volume(cell);need(value>0,'positive inherited leaf required')
        counters['tree_nodes_visited']+=1;max_depth=max(max_depth,depth);reason=None;observation=None
        if value<=F(limits['tiny_retained_volume_exact']):reason='tiny_exact_volume_retained'
        elif counters['boundary_box_tests']>=limits['maximum_boundary_box_tests'] or counters['support_inequality_tests']>=limits['maximum_support_inequality_tests']:
            reason='global_predicate_budget_retained'
        else:
            observation=attempt_channel(base,model,cell,sources,planar,counters,limits)
            if observation['excluded_open_interior']:
                nodes[index]={'id':index,'kind':'excluded','positive_directed_volume_exact':str(value),'certificate':observation}
                removed+=value;excluded+=1;uv_used+=len(observation['planar_exterior_certificates']);continue
            if observation.get('search_stopped_at_predicate_budget'):reason='global_predicate_budget_retained'
            elif depth>=limits['maximum_depth']:reason='path_depth_limit_retained'
            elif counters['splits']>=limits['maximum_splits']:reason='global_split_limit_retained'
            else:
                axis,cut,witness=choose_cut(cell,sources,observation);need(cell[axis][0]<cut<cell[axis][1],'strict internal registered split required')
                low=list(cell);high=list(cell);low[axis]=(cell[axis][0],cut);high[axis]=(cut,cell[axis][1])
                a,b=base.volume(low),base.volume(high);need(a>0 and b>0 and a+b==value,'exact complete positive partition required')
                left,right=len(nodes),len(nodes)+1;nodes.extend([None,None]);counters['splits']+=1
                nodes[index]={'id':index,'kind':'split','axis':axis,'cut_exact':str(cut),'cut_source':witness,'children':[left,right],
                              'parent_positive_directed_volume_exact':str(value),'children_positive_directed_volumes_exact':[str(a),str(b)],
                              'closed_cut_plane_retained_as_zero_volume_carrier':True,'actual_channel_observation':observation}
                children=[(left,low,depth+1),(right,high,depth+1)];pending.extend([children[1],children[0]] if a>=b else children);continue
        leaf={'id':index,'kind':'retained','reason':reason,'positive_directed_volume_exact':str(value),'actual_material_interference_claimed':False}
        if observation is not None:leaf['actual_channel_observation']=observation
        nodes[index]=leaf;kept+=value;retained+=1;reasons[reason]=reasons.get(reason,0)+1
    need(all(n is not None for n in nodes) and kept+removed==base.volume(root),'complete new tree measure changed')
    return {'nodes':nodes,'retained_sum_exact':str(kept),'excluded_open_sum_exact':str(removed),
            'total_leaf_count':excluded+retained,'excluded_leaf_count':excluded,'retained_leaf_count':retained,
            'retained_reason_counts':reasons,'maximum_depth_reached':max_depth,
            'actual_planar_exterior_separator_count_in_excluded_leaves':uv_used,
            'all_closed_cut_planes_and_root_boundaries_retained':True}


def require_prerequisites(contract,phase):
    expected=[] if phase=='single_planar_exterior_leaf' else ['single_planar_exterior_leaf'] if phase=='preflight_planar_exterior' else ['single_planar_exterior_leaf','preflight_planar_exterior']
    rows=contract['completed_prerequisites'];need([r['phase'] for r in rows]==expected,'actual prerequisite sequence differs')
    for row in rows:
        old=read(row['report']);owned=read(row['supervisor'])
        need(old['execution_completed'] and old['phase']==row['phase'] and owned['completed'] and owned['worker_started'] and owned['resource_stop'] is None and owned['worker_exit_code']==0,
             'actual completed owned prerequisite required')
        need(owned['limits']['registered_math_contract_sha256']==old['contract_sha256'] and
             Path(owned['limits']['worker_output_directory']).resolve()==Path(row['report']['path']).resolve().parent and
             owned['limits']['worker']['sha256']==contract['producer_sha256'],'actual prerequisite binding differs')
        scope(old)
        need(old['registered_input_identities']=={k:contract[k] for k in SHARED_INPUT_FIELDS} and old['capacity']==contract['capacity'],
             'actual prerequisite used different source, inputs, selection or capacity')
        if row['phase']=='single_planar_exterior_leaf':
            need(len(old['frames'])==1 and (old['frames'][0]['case_id'],old['frames'][0]['frame'])==('case-028',1) and
                 old['frames'][0]['root_base_V6_leaf_locators']==[[76,47]] and old['planar_exterior_model_conditional_clearance_passes']==1 and
                 F(old['frames'][0]['newly_excluded_open_leaf_sum_exact'])>0 and
                 old['frames'][0]['actual_planar_exterior_separator_count_in_excluded_leaves']>0,'actual first planar witness not qualified')
        if row['phase']=='preflight_planar_exterior':
            need(old['total_actual_V6_retained_roots']==4943 and old['complete_phase_maximum_tree_nodes']==13135 and
                 old['all_frame_capacity_observations_completed'],'actual full16 finite source preflight required')
    if phase!='single_planar_exterior_leaf':
        binding=contract['independent_single_verification'];verified=read(binding['report']);owned=read(binding['supervisor'])
        need(verified['execution_completed'] and verified['expected_phase']=='single_planar_exterior_leaf' and
             verified['planar_exterior_model_conditional_clearance_passes']==1 and owned['completed'] and
             owned['resource_stop'] is None and owned['worker_exit_code']==0,'actual first independent planar proof required')
        need(owned['limits']['registered_math_contract_sha256']==verified['contract_sha256'] and
             owned['limits']['worker']['sha256']==contract['single_verifier_source']['sha256'] and
             Path(owned['limits']['worker_output_directory']).resolve()==Path(binding['report']['path']).resolve().parent,
             'actual independent prerequisite identity differs')
        need(verified['expected_case_frames']==[['case-028',1]] and equal(verified['verified_producer_report'],rows[0]['report']),
             'actual independent prerequisite verified another selected experiment')
        scope(verified)


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();contract=json.loads(args.contract.read_text());need(identity(__file__)['sha256']==contract['producer_sha256'],'registered V7 producer differs')
    need(not args.output.exists(),'new output directory required');args.output.mkdir(parents=True)
    started=time.monotonic();phase=contract['phase']
    report={'schema':'razr-r5e-planar-exterior-refinement-v7','phase':phase,'started_utc':datetime.now(timezone.utc).isoformat(),
            'source_sha256':identity(__file__)['sha256'],'contract_sha256':identity(args.contract)['sha256'],'execution_completed':False,
            'conditional_planar_exterior_model_only':True,'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
            'native_planar_region_semantics_verified':False,'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
            'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,'full_continuous_G2':False,
            'all_blockers_closed':False,'native_Common_called':False,'compiled_transform_error_verified':False,
            'original_V3_raw_passes_unchanged':4,'actual_V5_conditional_passes_preserved':8,'actual_V6_conditional_passes_preserved':8,
            'original_V4_failure_preserved':True,'V5_producer_rerun':False,'V6_producer_rerun':False,'frames':[],
            'counters':{k:0 for k in ['channels_tested','boundary_box_tests','spatial_boundary_piece_tests','UV_boundary_piece_tests',
                                      'support_inequality_tests','UV_support_inequality_tests','UV_channels_tested',
                                      'successful_nonaxis_separations','successful_planar_exterior_separations','splits','tree_nodes_visited']}}
    def save():
        report['seconds']=time.monotonic()-started;report['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        scope(contract);need(phase in ('single_planar_exterior_leaf','preflight_planar_exterior','all_planar_exterior_frames'),'registered V7 phase required')
        limits=contract['capacity'];need(limits['maximum_splits']==4096 and limits['maximum_depth']==24 and
             limits['maximum_boundary_box_tests']==limits['maximum_support_inequality_tests']==12000000 and
             F(limits['tiny_retained_volume_exact'])==F(1e-7)/100000 and limits['maximum_UV_pieces_per_face']==225 and
             limits['maximum_total_UV_pieces']==4064,'original budgets or fixed new source capacity changed')
        base=module(contract['base_channel_source'],'r5e_v7_frozen_base_channels')
        model=module(contract['planar_model_source'],'r5e_v7_planar_source_helpers')
        actual,prior,prior_verified,pipeline=actual_v6_inputs(contract)
        report['actual_V6_report']=actual['all-primitive-support-frames/report.json'];report['actual_V6_independent_report']=actual['verify-all/report.json']
        report['immutable_V6_input_count']=len(actual);report['capacity']=limits
        report['registered_input_identities']={k:contract[k] for k in SHARED_INPUT_FIELDS}
        selection=read(contract['real_retained_leaf_selection']);chosen=(selection['case_id'],selection['frame'])
        need(chosen==('case-028',1) and selection['V6_root_index']==76 and selection['V6_node_index']==47,'original actual selected V6 leaf differs')
        require_prerequisites(contract,phase)
        with gzip.open(bound(contract['primitive_source_bundle']),'rt') as stream:projection=json.load(stream)
        need(projection['schema']=='razr-r5e-original-primitive-source-projection-v6','complete original V6 primitive projection required')
        expected=[(c,f) for c in ['case-001','case-006','case-028','case-037','case-054','case-063','case-072','case-089'] for f in (1,2)]
        need([(r['case_id'],r['frame']) for r in prior['frames']]==expected,'original full16 actual source order changed')
        frames=[r for r in prior['frames'] if (r['case_id'],r['frame'])==chosen] if phase=='single_planar_exterior_leaf' else prior['frames']
        total_roots=total_uv=total_models=rejected=0;max_piece=max_uv=0
        for old in frames:
            key=(old['case_id'],old['frame']);name='all-primitive-support-frames/'+old['certificate']['path']
            need(equal(old['certificate'],actual[name]),'actual source certificate differs')
            with gzip.open(actual[name]['path'],'rt') as stream:certificate=json.load(stream)
            need(certificate['frame']=={k:v for k,v in old.items() if k!='certificate'},'actual V6 frame header changed')
            leaves,old_kept,old_removed=retained_v6_leaves(base,certificate)
            need(old_kept==F(old['retained_leaf_sum_exact']),'actual V6 retained measure differs')
            if phase=='single_planar_exterior_leaf':
                leaves=[r for r in leaves if r['locator']==[76,47]];need(len(leaves)==1,'actual selected old leaf missing')
                selected=leaves[0]
                need(base.encode(selected['box'])==selection['actual_leaf_box_exact'] and selected['node']==selection['actual_V6_leaf_record'] and
                     selected['depth']==24 and selected['base_V5_leaf_locator']==selection['base_V5_leaf_locator'] and
                     canonical(certificate['roots'][76])==selection['actual_V6_root_record_canonical_sha256'] and
                     equal(selection['actual_V6_certificate'],actual[name]),'complete selected source leaf binding differs')
            boundary=certificate['boundary_refinement'];sources=runtime_sources(model,boundary)
            planar,models=model.build_models(boundary,old,projection,limits)
            total_roots+=len(leaves);total_uv+=models['total_UV_boundary_piece_count'];total_models+=models['applied_plane_model_count'];rejected+=models['rejected_plane_model_count']
            max_piece=max(max_piece,max(len(s['pieces']) for s in sources))
            max_uv=max([max_uv]+[len(m['uv_boundary_pieces']) for s in models['sources'] for m in s['models'] if m['applied']])
            row={'case_id':key[0],'frame':key[1],'pair':old['pair'],'original_raw_proof_identity':old['original_raw_proof_identity'],
                 'original_remaining_displacement_box_exact':old['original_remaining_displacement_box_exact'],
                 'base_V6_certificate':actual[name],'base_V6_boundary_canonical_sha256':canonical(boundary),
                 'base_V6_frame_conditional_upper_exact_mm3':old['primitive_support_model_conditional_upper_exact_mm3'],
                 'base_V6_retained_leaf_sum_exact':str(old_kept),'base_V6_excluded_open_leaf_sum_exact':str(old_removed),
                 'root_base_V6_leaf_locators':[r['locator'] for r in leaves],'root_count':len(leaves),
                 'source_piece_counts':[len(s['pieces']) for s in sources],
                 'applied_planar_model_count':models['applied_plane_model_count'],'rejected_planar_model_count':models['rejected_plane_model_count'],
                 'UV_boundary_piece_count':models['total_UV_boundary_piece_count'],
                 'conditional_planar_exterior_model_only':True,'conditional_primitive_support_model_only':True,'conditional_trim_model_only':True,
                 'native_planar_region_semantics_verified':False,'native_primitive_semantics_verified':False,'native_trim_class_membership_verified':False,
                 'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,'full_continuous_G2':False}
            if phase=='preflight_planar_exterior':
                row['new_clearance_result_claimed']=False
                row['source_models_canonical_sha256']=canonical(models)
                row['face_statuses']=[{'material_key':s['material_key'],'models':[{'piece_index':m['piece_index'],'original_face_index':m['original_face_index'],
                    'applied':m['applied'],'reason':m.get('retained_original_plane_reason'),'UV_pieces':len(m.get('uv_boundary_pieces',[]))} for m in s['models']]} for s in models['sources']]
            else:
                roots=[];kept=F(0);removed=F(0);leaf_count=depth=uv_used=0;before=dict(report['counters'])
                for leaf in leaves:
                    tree=refine(base,model,leaf['box'],sources,planar,report['counters'],limits)
                    roots.append({'base_V6_leaf_locator':leaf['locator'],'root_box_exact':base.encode(leaf['box']),
                                  'root_directed_volume_exact':leaf['volume_exact'],'tree':tree})
                    kept+=F(tree['retained_sum_exact']);removed+=F(tree['excluded_open_sum_exact']);leaf_count+=tree['total_leaf_count']
                    depth=max(depth,tree['maximum_depth_reached']);uv_used+=tree['actual_planar_exterior_separator_count_in_excluded_leaves']
                need(kept+removed==sum((F(r['volume_exact']) for r in leaves),F(0)),'all inherited positive source leaves must be conserved')
                if phase=='all_planar_exterior_frames':
                    need(kept+removed==old_kept,'all original V6 positive retained volume required')
                    upper=min(kept,F(old['primitive_support_model_conditional_upper_exact_mm3']))
                else:upper=kept
                row.update(retained_leaf_sum_exact=str(kept),newly_excluded_open_leaf_sum_exact=str(removed),new_root_sum_exact=str(kept+removed),
                    planar_exterior_model_conditional_upper_exact_mm3=str(upper),planar_exterior_model_conditional_upper_mm3=float(upper),
                    planar_exterior_model_conditional_clearance_gate_passed=upper<=F(1e-7),all_prior_and_new_closed_carriers_retained=True,
                    total_leaf_count=leaf_count,maximum_depth_reached=depth,actual_planar_exterior_separator_count_in_excluded_leaves=uv_used,
                    exact_splits_this_frame=report['counters']['splits']-before['splits'],
                    exact_combined_piece_tests_this_frame=report['counters']['boundary_box_tests']-before['boundary_box_tests'],
                    exact_combined_support_tests_this_frame=report['counters']['support_inequality_tests']-before['support_inequality_tests'])
                payload={'schema':'razr-r5e-planar-exterior-tree-v7','frame':row,'planar_models':models,'roots':roots,
                         'base_V6_boundary_canonical_sha256':canonical(boundary),'actual_V6_excluded_open_sum_preserved_exact':str(old_removed),
                         'V6_producer_rerun':False}
                destination=args.output/(key[0]+'-frame-'+str(key[1])+'-planar-exterior.json.gz')
                with destination.open('wb') as raw:
                    with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:stream.write((json.dumps(payload,separators=(',',':'))+'\n').encode())
                row['certificate']=dict(identity(destination),path=destination.name)
            report['frames'].append(row);save()
            need(report['seconds']<=600 and report['peak_RSS_bytes']<=805306368,'original owned mathematical budget exceeded')
        report.update(total_actual_V6_retained_roots=total_roots,complete_phase_maximum_tree_nodes=total_roots+2*4096,
                      complete_phase_maximum_leaves=total_roots+4096,maximum_complete_spatial_pieces_per_material=max_piece,
                      actual_total_UV_boundary_pieces=total_uv,maximum_UV_pieces_per_face=max_uv,
                      actual_applied_plane_models=total_models,actual_rejected_plane_models=rejected,
                      all_frame_capacity_observations_completed=len(report['frames'])==(1 if phase=='single_planar_exterior_leaf' else 16),
                      planar_exterior_model_conditional_clearance_passes=sum(r.get('planar_exterior_model_conditional_clearance_gate_passed',False) for r in report['frames']))
        need(total_uv<=4064 and max_uv<=225 and max_piece<=4096 and total_models+rejected<=(6 if phase=='single_planar_exterior_leaf' else 48),'actual source capacity exceeds fixed census')
        if phase!='single_planar_exterior_leaf':need(total_roots==4943,'full actual V6 retained forest census differs')
        need(report['counters']['boundary_box_tests']==report['counters']['spatial_boundary_piece_tests']+report['counters']['UV_boundary_piece_tests'],
             'all spatial and UV boundary tests must share original total budget')
        need(all(equal(identity(r['path']),r) for r in actual.values()),'actual V6 input changed during work')
        for record in contract.values():
            if isinstance(record,dict) and set(('path','bytes','sha256'))<=set(record):bound(record)
        need(identity(__file__)['sha256']==contract['producer_sha256'] and identity(args.contract)['sha256']==report['contract_sha256'],'source or contract changed')
        report['all_source_contract_and_archived_inputs_unchanged']=True;report['execution_completed']=True
    except BaseException as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        print(json.dumps({k:report.get(k) for k in ('phase','execution_completed','planar_exterior_model_conditional_clearance_passes','counters','seconds','peak_RSS_bytes','failure')}),flush=True)
    return 0 if report['execution_completed'] else 2


if __name__=='__main__':raise SystemExit(main())
