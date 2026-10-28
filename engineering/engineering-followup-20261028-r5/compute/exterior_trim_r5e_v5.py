"""Conditioned planar trim boundary model on complete original R4 raw cells.

Each non-excluded leaf retains its full exact directed volume. This worker
does not prove native trim membership, call CAD, or reclassify original gates.
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


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def bound(record):
    path=Path(record['path']);need(path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],'bound input differs: '+str(path));return path


def load_base(contract):
    path=bound(contract['base_producer_source']);spec=importlib.util.spec_from_file_location('r5e_v5_frozen_channel_geometry',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def load_trim_model(contract):
    path=bound(contract['trim_model_source']);spec=importlib.util.spec_from_file_location('r5e_v5_conditioned_trim_geometry',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def require_conditional_scope(record):
    need(record['conditional_trim_model_only'] is True and record['native_trim_class_membership_verified'] is False and
         record['inner_wire_hole_semantics_verified_for_native'] is False and record['original_raw_gate_reclassified'] is False and
         record['full_continuous_G2'] is False,'conditional-model/native qualification scope differs')


def attempt_channel(base,cell,sources,counters,limits):
    failures=[]
    for side,source in enumerate(sources):
        for axis in range(3):
            for end in (0,1):
                channel=base.channel_for(cell,source['whole'],axis,end);codes=[];blocker=None
                counters['channels_tested']+=1
                for index,piece in enumerate(source['pieces']):
                    if counters['boundary_box_tests']>=limits['maximum_boundary_box_tests']:
                        return {'excluded_open_interior':False,'search_stopped_at_predicate_budget':True,
                                'completed_blocked_channels':failures,'actual_material_interference_claimed':False}
                    counters['boundary_box_tests']+=1;code=base.separation(piece,channel)
                    if code is None:blocker=index;break
                    codes.append(str(code))
                if blocker is None:
                    need(len(codes)==len(source['pieces']),'complete boundary certificate required')
                    return {'excluded_open_interior':True,'material_side':side,'axis':axis,'end':end,
                            'open_channel_exact':base.encode(channel),'complete_piece_separation_codes':''.join(codes),
                            'boundary_piece_count':len(codes),'closed_cell_boundary_retained_as_zero_volume_carrier':True,
                            'whole_closed_cell_disjoint_claimed':False}
                failures.append({'material_side':side,'axis':axis,'end':end,'blocking_piece_index':blocker})
    return {'excluded_open_interior':False,'all_registered_channels_blocked':failures,'actual_material_interference_claimed':False}


def choose_registered_model_cut(cell,sources,blocked):
    candidates={}
    for obstruction in blocked['all_registered_channels_blocked']:
        side,index=obstruction['material_side'],obstruction['blocking_piece_index']
        piece=sources[side]['pieces'][index]
        for axis in range(3):
            lo,hi=cell[axis]
            for end,cut in enumerate(piece[axis]):
                if lo<cut<hi:
                    key=(axis,cut)
                    witness={'material_side':side,'piece_index':index,'axis':axis,'endpoint':end}
                    if key not in candidates:candidates[key]=witness
    if not candidates:return None
    def score(item):
        axis,cut=item;lo,hi=cell[axis]
        return (min(cut-lo,hi-cut)/(hi-lo),axis,cut)
    key=min(candidates,key=score)
    return key[0],key[1],candidates[key]


def refine(base,root,sources,counters,limits):
    nodes=[None];pending=[(0,root,0)];retained=F(0);removed=F(0);max_depth=0
    retained_reasons={};excluded_leaves=retained_leaves=0
    tiny=F(limits['tiny_retained_volume_exact'])
    while pending:
        index,cell,depth=pending.pop();max_depth=max(max_depth,depth);value=base.volume(cell)
        need(value>0,'strictly positive affine cell required')
        counters['tree_nodes_visited']+=1
        reason=None;certificate=None
        if value<=tiny:
            reason='tiny_exact_volume_retained'
        elif counters['boundary_box_tests']>=limits['maximum_boundary_box_tests']:
            reason='global_predicate_budget_retained'
        else:
            certificate=attempt_channel(base,cell,sources,counters,limits)
            if certificate['excluded_open_interior']:
                nodes[index]={'id':index,'kind':'excluded','positive_directed_volume_exact':str(value),'certificate':certificate}
                removed+=value;excluded_leaves+=1;continue
            if certificate.get('search_stopped_at_predicate_budget'):
                reason='global_predicate_budget_retained'
            elif depth>=limits['maximum_depth']:
                reason='path_depth_limit_retained'
            elif counters['splits']>=limits['maximum_splits']:
                reason='global_split_limit_retained'
            else:
                cut=choose_registered_model_cut(cell,sources,certificate)
                if cut is None:reason='no_registered_model_boundary_endpoint_inside_cell'
                else:
                    axis,point,witness=cut
                    low=list(cell);high=list(cell)
                    low[axis]=(cell[axis][0],point);high[axis]=(point,cell[axis][1])
                    a,b=base.volume(low),base.volume(high)
                    need(a>0 and b>0 and a+b==value,'exact partition volume identity failed')
                    left,right=len(nodes),len(nodes)+1;nodes.extend([None,None]);counters['splits']+=1
                    nodes[index]={'id':index,'kind':'split','axis':axis,'cut_exact':str(point),'cut_source':witness,
                                  'children':[left,right],'parent_positive_directed_volume_exact':str(value),
                                  'children_positive_directed_volumes_exact':[str(a),str(b)],
                                  'closed_cut_plane_retained_as_zero_volume_carrier':True}
                    # Stack order: evaluate the larger child first; keep both.
                    children=[(left,low,depth+1),(right,high,depth+1)]
                    if a>=b:pending.extend([children[1],children[0]])
                    else:pending.extend(children)
                    continue
        need(reason is not None,'retained leaf needs an actual stopping reason')
        leaf={'id':index,'kind':'retained','reason':reason,'positive_directed_volume_exact':str(value),
              'actual_material_interference_claimed':False}
        if certificate is not None:leaf['actual_channel_observation']=certificate
        nodes[index]=leaf;retained+=value;retained_leaves+=1;retained_reasons[reason]=retained_reasons.get(reason,0)+1
    need(all(node is not None for node in nodes),'pending tree leaf omitted')
    need(retained+removed==base.volume(root),'root partition measure not conserved')
    return {'nodes':nodes,'retained_sum_exact':str(retained),'excluded_open_sum_exact':str(removed),
            'total_leaf_count':excluded_leaves+retained_leaves,'excluded_leaf_count':excluded_leaves,
            'retained_leaf_count':retained_leaves,'retained_reason_counts':retained_reasons,'maximum_depth_reached':max_depth,
            'all_closed_cut_planes_and_root_boundaries_retained':True,'positive_cell_topology':'positive diagonal affine images of the original checked unit cube'}


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();contract=json.loads(args.contract.read_text());need(sha(__file__)==contract['producer_sha256'],'registered V5 producer identity')
    base=load_base(contract);model=load_trim_model(contract);args.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();limits=contract['capacity']
    result={'schema':'razr-r5e-trim-model-conditioned-refinement-v5','started_utc':datetime.now(timezone.utc).isoformat(),'phase':contract['phase'],
            'contract_sha256':sha(args.contract),'execution_completed':False,'frames':[],
            'counters':{'channels_tested':0,'boundary_box_tests':0,'splits':0,'tree_nodes_visited':0},
            'original_TOL_exact':str(F(1e-7)),'native_Common_called':False,'native_material_semantics_verified':False,
            'compiled_error_bound_verified':False,'full_continuous_G2':False,'all_blockers_closed':False,
            'capacity':limits,'no_positive_thin_leaf_discarded':True,
            'conditional_trim_model_only':True,'native_trim_class_membership_verified':False,
            'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,
            'trim_source_bundle':contract['trim_source_bundle'],'trim_model_source':contract['trim_model_source'],
            'original_V3_raw_clearance_passes_unchanged':4,'original_V4_selected_cell_bound_and_control_failure_unchanged':True}
    def save():
        result['seconds']=time.monotonic()-start;result['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        require_conditional_scope(contract)
        need(limits['maximum_splits']==4096 and limits['maximum_depth']==24 and limits['maximum_boundary_box_tests']==12000000,'registered finite refinement policy differs')
        need(limits['maximum_uv_patches_per_face']==1024 and limits['maximum_boundary_pieces_per_material']==4096,'registered finite conditional boundary policy differs')
        need(limits['wall_seconds']==600 and limits['RSS_limit_bytes']==805306368,'original mathematical process limits differ')
        need(F(limits['tiny_retained_volume_exact'])==F(1e-7)/100000,'tiny retained leaf policy differs')
        phase=contract['phase'];need(phase in ['single_trim_model_cell','preflight_trim_model','all_trim_model_frames'],'registered producer phase')
        selection=json.loads(bound(contract['real_retained_cell_selection']).read_text())
        selected_case_frame=(selection['case_id'],selection['frame'])
        selected_root_index=selection['original_raw_cell_index']
        expected=[] if phase=='single_trim_model_cell' else ['single_trim_model_cell'] if phase=='preflight_trim_model' else ['single_trim_model_cell','preflight_trim_model']
        need([r['phase'] for r in contract['completed_prerequisites']]==expected,'registered prerequisite phase sequence')
        for prerequisite in contract['completed_prerequisites']:
            old=json.loads(bound(prerequisite['report']).read_text());controller=json.loads(bound(prerequisite['supervisor']).read_text())
            need(old['execution_completed'] and old['phase']==prerequisite['phase'] and controller['completed'] and controller['worker_started'] and controller['worker_exit_code']==0 and controller['resource_stop'] is None,'incomplete prerequisite')
            require_conditional_scope(old)
            need(controller['limits']['registered_math_contract_sha256']==old['contract_sha256'],'prerequisite contract differs')
            need(controller['limits']['worker']['sha256']==contract['producer_sha256'],'prerequisite producer source differs')
            need(Path(controller['limits']['worker_output_directory']).resolve()==Path(prerequisite['report']['path']).resolve().parent,'prerequisite output differs')
            need(old['source_report_identity']==contract['r4_report'] and old['public_input_bridge']==contract['public_input_bridge'],
                 'prerequisite full original input identities differ')
            need(old['trim_source_bundle']==contract['trim_source_bundle'] and old['trim_model_source']==contract['trim_model_source'],
                 'prerequisite conditional-model source differs')
            if prerequisite['phase']=='single_trim_model_cell':
                need(old['trim_model_conditional_clearance_passes']==1 and len(old['frames'])==1 and F(old['frames'][0]['excluded_open_leaf_sum_exact'])>0,
                     'selected real retained cell did not pass the unchanged threshold in the conditional trim model')
                need(old['frames'][0]['model_boundary_applied_face_count']>0 and old['frames'][0]['model_boundary_applied_inner_wire_count']>0,
                     'required actual planar hole refinement was not demonstrated')
                need((old['frames'][0]['case_id'],old['frames'][0]['frame'])==selected_case_frame and
                     old['frames'][0]['root_original_cell_indices']==[selected_root_index] and
                     old['real_retained_cell_selection']==contract['real_retained_cell_selection'],
                     'prerequisite single case/frame/root or actual selection identity differs')
            if prerequisite['phase']=='preflight_trim_model':
                need(old['all_frame_capacity_observations_completed'] and len(old['frames'])==16 and old['total_original_roots']==1474 and
                     old['new_predicate_hard_budget']==limits['maximum_boundary_box_tests'] and old['complete_phase_maximum_tree_nodes']==9666,
                     'actual full16 finite capacity preflight differs')
                need(contract['actual_capacity_basis']==prerequisite['report'],'actual capacity basis report identity differs')
                need(old['maximum_uv_patch_count_per_face']<=limits['maximum_uv_patches_per_face'] and
                     old['maximum_boundary_piece_count_per_material']<=limits['maximum_boundary_pieces_per_material'],
                     'actual preflight conditional boundary capacity exceeds registered limits')
        if phase!='single_trim_model_cell':
            binding=contract['independent_single_verification']
            verified=json.loads(bound(binding['report']).read_text());owned=json.loads(bound(binding['supervisor']).read_text())
            need(verified['execution_completed'] and verified['expected_phase']=='single_trim_model_cell' and verified['trim_model_conditional_clearance_passes']==1,
                 'actual independent single-cell pass required before larger work')
            require_conditional_scope(verified)
            need(verified['trim_source_bundle']==contract['trim_source_bundle'],'independent prerequisite conditional input differs')
            need(verified['expected_case_frames']==[list(selected_case_frame)],'independent prerequisite case/frame differs')
            need(owned['completed'] and owned['worker_started'] and owned['worker_exit_code']==0 and owned['resource_stop'] is None,
                 'independent prerequisite not completed under original owned gates')
            need(owned['limits']['registered_math_contract_sha256']==verified['contract_sha256'],'independent prerequisite contract differs')
            need(owned['limits']['worker']['sha256']==contract['single_verifier_source']['sha256'] and
                 sha(bound(contract['single_verifier_source']))==contract['single_verifier_source']['sha256'],
                 'independent prerequisite verifier source differs')
            need(Path(owned['limits']['worker_output_directory']).resolve()==Path(binding['report']['path']).resolve().parent,
                 'independent prerequisite output binding differs')
            need(verified['verified_producer_report']==contract['completed_prerequisites'][0]['report'],
                 'independent verifier did not check the actual required single-cell report')
            result['actual_independent_single_verification']=binding
        report_path=bound(contract['r4_report']);original=json.loads(report_path.read_text());need(original['execution_completed'] and len(original['frames'])==16,'original16 source required')
        result['source_report_identity']=contract['r4_report'];result['public_input_bridge']=contract['public_input_bridge']
        with gzip.open(bound(contract['trim_source_bundle']),'rt') as stream:trim_bundle=json.load(stream)
        need(trim_bundle['schema']=='razr-r5e-original-planar-trim-source-projection-v5','registered trim source projection schema differs')
        need(trim_bundle['original_public_R4_report_identity']=={k:contract['r4_report'][k] for k in ('bytes','sha256')},'trim source original R4 report identity differs')
        need(dict(trim_bundle['original_native_inventory_identity'],path=trim_bundle['original_native_inventory_relative_path']) in original['input_identities'],
             'trim source original native inventory identity not anchored to original R4 report')
        need(trim_bundle['native_inventory_was_preexisting_actual_evidence'] is True and trim_bundle['new_native_operations']==0 and
             trim_bundle['new_mathematical_qualification'] is False and trim_bundle['original_pcurve_values_changed'] is False and
             trim_bundle['native_trim_class_membership_verified'] is False,'source projection scope differs')
        need(len(trim_bundle['records'])==32 and len({(r['input']['case_id'],r['input']['material_id']) for r in trim_bundle['records']})==32,
             'complete unique whole-material trim source projection required')
        need([(r['case_id'],r['frame']) for r in trim_bundle['frame_bindings']]==[(r['case_id'],r['frame']) for r in original['frames']],
             'trim source frame sequence differs from original16')
        independent=json.loads(bound(contract['r4_independent_report']).read_text());need(independent['execution_completed'],'original independent source incomplete')
        bridge_json=json.loads(bound(contract['public_input_bridge']).read_text());need(bridge_json['source_commit']=='c5f6606924937d716b007cd3ffa8e54df8ecfa5d','public source anchor differs')
        need(len(bridge_json['files'])==19 and all(x['decoded_json_equal'] and not x['changed_strings'] for x in bridge_json['files']),'complete unchanged public bridge')
        bridge={x['path']:x for x in bridge_json['files']};need(len(bridge)==19,'duplicate source bridge')
        result['real_retained_cell_selection']=contract['real_retained_cell_selection']
        frames=original['frames']
        if phase=='single_trim_model_cell':frames=[next(r for r in frames if (r['case_id'],r['frame'])==(selection['case_id'],selection['frame']))]
        result['base_channel_controls']=base.controlled_examples()
        total_roots=0;max_source_pieces=0;max_coordinate_chars=0;input_bytes=0;old_static=0
        max_uv_patches=max_material_pieces=applied_faces=applied_holes=rejected_faces=0
        for row in frames:
            entry=bridge['support-v4/'+row['proof']['path']]
            need(entry['raw_identity']=={k:row['proof'][k] for k in ('bytes','sha256')},'public/raw proof identity mismatch')
            proof_record=dict(entry['public_identity'],path=str(report_path.parent/row['proof']['path']))
            with gzip.open(bound(proof_record),'rt') as stream:proof=json.load(stream)
            need(hashlib.sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()==entry['public_canonical_json_sha256'],'decoded original proof differs')
            need(proof['full_remaining_displacement_box_exact']==row['full_remaining_displacement_box_exact'],'original full D differs')
            source_binding=next(r for r in trim_bundle['frame_bindings'] if (r['case_id'],r['frame'])==(row['case_id'],row['frame']))
            need(source_binding['original_R4_raw_proof_identity']==row['proof'],'trim source exact original raw proof identity differs')
            sources,boundary=model.build_boundary(base,proof,trim_bundle,limits)
            cells=proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
            need(len(cells)==row['boundary_slab_positive_cell_count'],'complete raw cells differ')
            indices=list(range(len(cells)))
            if phase=='single_trim_model_cell':
                index=selection['original_raw_cell_index'];need(selection['actual_V3_cell']['excluded_open_interior'] is False,'selected original V3 result not retained')
                need(selection['actual_V3_cell']['box_exact']==cells[index]['box_exact'] and selection['actual_V3_cell']['positive_directed_volume_exact']==cells[index]['positive_directed_volume_exact'],'selected actual V3 cell differs from original R4 cell')
                need(selection['source_row_original_D']==row['full_remaining_displacement_box_exact'],'selected original D differs');indices=[index]
            total_roots+=len(indices);piece_count=sum(len(s['pieces']) for s in sources);max_source_pieces=max(max_source_pieces,piece_count)
            applied_faces+=boundary['applied_face_count'];applied_holes+=boundary['applied_inner_wire_count']
            rejected_faces+=boundary['retained_original_face_count_after_rejection']
            max_material_pieces=max(max_material_pieces,*(len(s['pieces']) for s in sources))
            for source_certificate in boundary['sources']:
                for face in source_certificate['face_certificates']:
                    if face['applied']:max_uv_patches=max(max_uv_patches,len(face['uv_closed_patch_boxes_exact']))
            input_bytes+=proof_record['bytes'];old_static+=6*piece_count*len(indices)
            for source in sources:
                for piece in source['pieces']:
                    for interval in piece:
                        max_coordinate_chars=max(max_coordinate_chars,*(len(str(v)) for v in interval))
            frame={'case_id':row['case_id'],'frame':row['frame'],'pair':row['pair'],'source_proof':proof_record,
                   'original_raw_proof_identity':row['proof'],'original_remaining_displacement_box_exact':row['full_remaining_displacement_box_exact'],
                   'source_piece_counts':[len(s['pieces']) for s in sources],'original_raw_cell_count':len(cells),
                   'root_original_cell_indices':indices,'root_count':len(indices),
                   'trim_source_bundle':contract['trim_source_bundle'],
                   'conditional_trim_model_only':True,'native_trim_class_membership_verified':False,
                   'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,'full_continuous_G2':False,
                   'original_R4_min_volume_plus_TOL_gate_passed':row['original_min_volume_plus_TOL_gate_passed'],
                   'model_boundary_applied_face_count':boundary['applied_face_count'],
                   'model_boundary_applied_inner_wire_count':boundary['applied_inner_wire_count'],
                   'model_boundary_retained_original_face_count_after_rejection':boundary['retained_original_face_count_after_rejection']}
            if phase=='preflight_trim_model':
                frame['new_clearance_result_claimed']=False
                frame['registered_model_coordinate_endpoint_counts']=[len({v for s in sources for p in s['pieces'] for v in p[k]}) for k in range(3)]
                frame['model_boundary_face_statuses']=[{'material_key':s['material_key'],'faces':[
                    {'face_index':f['face_index'],'applied':f['applied'],
                     'retained_original_reason':f.get('face_refinement_not_applied_reason'),
                     'admitted_inner_wires':len(f.get('holes',[])),'closed_uv_patch_count':len(f.get('uv_closed_patch_boxes_exact',[]))}
                    for f in s['face_certificates']]} for s in boundary['sources']]
            else:
                roots=[];retained=F(0);removed=F(0);leaves=0;max_depth=0;before=dict(result['counters'])
                for original_index in indices:
                    old=cells[original_index];cell=base.decode(old['box_exact']);value=base.volume(cell)
                    need(value==F(old['positive_directed_volume_exact'])>0,'original positive cell volume differs')
                    tree=refine(base,cell,sources,result['counters'],limits)
                    roots.append({'original_cell_index':original_index,'root_box_exact':old['box_exact'],'root_directed_volume_exact':str(value),'tree':tree})
                    retained+=F(tree['retained_sum_exact']);removed+=F(tree['excluded_open_sum_exact']);leaves+=tree['total_leaf_count'];max_depth=max(max_depth,tree['maximum_depth_reached'])
                if phase=='all_trim_model_frames':need(retained+removed==F(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']),'original full cell sum not conserved')
                selected=min(retained,F(row['coarse_whole_support_upper_exact_mm3'])) if phase=='all_trim_model_frames' else retained
                if phase=='all_trim_model_frames':
                    need(selected<=F(row['conditional_complete_material_intersection_upper_exact_mm3']),'refinement upper grew beyond original R4 bound')
                    need(row['original_min_volume_plus_TOL_gate_passed'] is True,'original upper sanity gate is not established')
                frame.update(retained_leaf_sum_exact=str(retained),excluded_open_leaf_sum_exact=str(removed),original_root_sum_exact=str(retained+removed),
                             trim_model_conditional_upper_exact_mm3=str(selected),trim_model_conditional_upper_mm3=float(selected),
                             trim_model_conditional_clearance_gate_passed=selected<=F(1e-7),
                             all_closed_cut_planes_and_original_cell_boundaries_retained=True,total_leaf_count=leaves,maximum_depth_reached=max_depth,
                             exact_splits_this_frame=result['counters']['splits']-before['splits'],
                             exact_boundary_box_tests_this_frame=result['counters']['boundary_box_tests']-before['boundary_box_tests'])
                dest=args.output/(row['case_id']+'-frame-'+str(row['frame'])+'-trim-model.json.gz')
                payload={'schema':'razr-r5e-trim-model-conditioned-tree-v5','frame':frame,'boundary_refinement':boundary,'roots':roots}
                with dest.open('wb') as raw:
                    with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as stream:stream.write((json.dumps(payload,separators=(',',':'))+'\n').encode())
                frame['certificate']={'path':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest)}
            result['frames'].append(frame);save()
            need(result['seconds']<=limits['wall_seconds'] and result['peak_RSS_bytes']<=limits['RSS_limit_bytes'],'registered worker process budget exceeded')
            del proof,sources
        result.update(total_original_roots=total_roots,maximum_complete_piece_count_sum=max_source_pieces,
                      maximum_exact_coordinate_character_count=max_coordinate_chars,total_compressed_original_input_bytes=input_bytes,
                      model_root_channel_static_predicate_upper=old_static,
                      complete_phase_maximum_leaves=total_roots+limits['maximum_splits'],
                      complete_phase_maximum_tree_nodes=total_roots+2*limits['maximum_splits'],
                      new_predicate_hard_budget=limits['maximum_boundary_box_tests'],
                      maximum_uv_patch_count_per_face=max_uv_patches,maximum_boundary_piece_count_per_material=max_material_pieces,
                      applied_face_occurrences_across_frames=applied_faces,applied_inner_wire_occurrences_across_frames=applied_holes,
                      retained_original_face_occurrences_after_rejection=rejected_faces)
        need(result['counters']['splits']<=limits['maximum_splits'] and result['counters']['boundary_box_tests']<=limits['maximum_boundary_box_tests'],'finite algorithm budget escaped')
        result['trim_model_conditional_clearance_passes']=sum(r.get('trim_model_conditional_clearance_gate_passed',False) for r in result['frames'])
        result['all_frame_capacity_observations_completed']=len(result['frames'])==(1 if phase=='single_trim_model_cell' else 16)
        result['source_and_contract_unchanged']=sha(__file__)==contract['producer_sha256'] and sha(args.contract)==result['contract_sha256'] and all(
            sha(Path(contract[key]['path']))==contract[key]['sha256'] for key in ['base_producer_source','trim_model_source','trim_source_bundle','public_input_bridge','r4_report'])
        need(result['source_and_contract_unchanged'] and result['all_frame_capacity_observations_completed'],'incomplete source/frame state')
        result['execution_completed']=True
    except BaseException as exc:
        result['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:
        result['finished_utc']=datetime.now(timezone.utc).isoformat();save()
        print(json.dumps({k:result.get(k) for k in ['phase','execution_completed','trim_model_conditional_clearance_passes','counters','seconds','peak_RSS_bytes','failure']}),flush=True)


if __name__=='__main__':main()
