"""One fixed old leaf, one original spatial split, at most two child attempts.

This cost diagnostic exceeds the original cumulative V6 depth-24 gate.
It never qualifies V6, V9, the UV method, a full frame, or native geometry.
Original producer/helper functions are copied exactly, not imported.
Only the pinned original independent checker is imported for proof replay.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
from types import SimpleNamespace

def need(ok,message):
    if not ok:raise ValueError(message)

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

def require(ok, message):
    if not ok:
        raise ValueError(message)

def decode(box):
    result = [tuple(map(F, interval)) for interval in box]
    require(len(result) == 3 and all(len(i) == 2 and i[0] <= i[1] for i in result), 'ordered finite 3D box required')
    return result

def encode(box):
    return [[str(v) for v in interval] for interval in box]

def volume(box):
    if any(lo >= hi for lo, hi in box):
        return F(0)
    value = F(1)
    for lo, hi in box:
        value *= hi-lo
    return value

def channel_for(cell, whole, axis, end):
    result = list(cell)
    # Exactly 1 mm beyond the complete support box, with no floating operation.
    if end == 0:
        result[axis] = (min(whole[axis][0]-1, cell[axis][0]-1), cell[axis][1])
    else:
        result[axis] = (cell[axis][0], max(whole[axis][1]+1, cell[axis][1]+1))
    require(all(lo < hi for lo, hi in result), 'open channel must be positive and connected')
    return result

def add(a,b):return (a[0]+b[0],a[1]+b[1])

def scale(c,a):return (min(c*a[0],c*a[1]),max(c*a[0],c*a[1]))

def project(normal,ranges):
    result=(F(0),F(0))
    for value,part in zip(normal,ranges):result=add(result,scale(value,part))
    return result



def identity(path):
    p=Path(path).resolve();h=hashlib.sha256()
    with p.open('rb') as stream:
        for data in iter(lambda:stream.read(1048576),b''):h.update(data)
    return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}


def same(a,b):return all(a[k]==b[k] for k in ('bytes','sha256'))
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load(row,compressed=False):
    need(same(identity(row['path']),row),'registered source input differs')
    if compressed:
        with gzip.open(row['path'],'rb') as stream:raw=stream.read(67108865)
    else:
        need(row['bytes']<=67108864,'registered finite input byte cap exceeded')
        raw=Path(row['path']).read_bytes()
    need(len(raw)<=67108864,'registered finite decoded input byte cap exceeded')
    return json.loads(raw)


def verify_original_function_copies(contract,inputs):
    own=ast.parse(Path(__file__).read_text());own_functions={n.name:n for n in own.body if isinstance(n,ast.FunctionDef)}
    source_trees={}
    rows=[]
    for binding in contract['original_function_bindings']:
        label=binding['original_source_input']
        if label not in source_trees:
            source_trees[label]={n.name:n for n in ast.parse(Path(inputs[label]['path']).read_text()).body if isinstance(n,ast.FunctionDef)}
        original=source_trees[label][binding['original_function']];copied=own_functions[binding['copied_function']]
        need(ast.dump(original)==ast.dump(copied),'original method/helper function AST changed')
        digest=hashlib.sha256(ast.dump(original).encode()).hexdigest()
        need(digest==binding['original_AST_sha256']==binding['copied_AST_sha256'],'registered original function identity differs')
        rows.append(dict(binding,actual_AST_equality=True))
    need(len(rows)==12,'complete twelve original method/helper function bindings required')
    return rows


def runtime_sources(boundary):
    out=[]
    for s in boundary['sources']:
        pieces=[]
        for p in s['pieces']:
            ranges=decode(p['box_exact']);slabs=[]
            need(len(p['additional_slabs'])<=1,'complete original at-most-one support slab required')
            for slab in p['additional_slabs']:
                normal=tuple(map(F,slab['normal_exact']));bounds=tuple(map(F,slab['bounds_exact']))
                need(len(normal)==3 and any(normal) and len(bounds)==2 and bounds[0]<=bounds[1],'original closed support slab required')
                slabs.append((normal,bounds))
            pieces.append({'box':ranges,'additional_slabs':slabs,'slab_source':p['additional_slabs'][0]['source'] if slabs else None})
        out.append({'whole':decode(s['known_whole_exact']),'pieces':pieces})
    need([s['material_key'] for s in boundary['sources']]==[['case-028',3],['case-028',2]] and [len(s['pieces']) for s in out]==[523,179],
         'complete original two-material carrier/order/census differs')
    return out


def original_source_selection(old,selection):
    signature=tuple(tuple(v) for v in selection['complete_original_first_blocker_signature'])
    fixed_volume=F(selection['selected_source_volume_exact'])
    signature_rows=[];volume_rows=[];intersection=[];selected=None
    for ri,r in enumerate(old['roots']):
        nodes={n['id']:n for n in r['tree']['nodes']};parents={c:(n['id'],i) for n in nodes.values() if n['kind']=='split' for i,c in enumerate(n['children'])}
        for ni,n in nodes.items():
            if n['kind']!='retained' or (ri,ni)==(76,47):continue
            failures=n.get('actual_channel_observation',{}).get('all_registered_channels_unresolved',[])
            recorded=tuple((f['material_side'],f['axis'],f['end'],f['unresolved_piece_index']) for f in failures)
            loc=(ri,ni)
            if recorded==signature:signature_rows.append(loc)
            if F(n['positive_directed_volume_exact'])==fixed_volume:volume_rows.append(loc)
            if recorded==signature and F(n['positive_directed_volume_exact'])==fixed_volume:intersection.append(loc)
            if loc==(78,375):selected=(r,n,nodes,parents)
    need(len(signature_rows)==3106 and len(volume_rows)==3153 and len(intersection)==3097 and min(intersection)==(78,375),
         'pre-registered metadata-only representative class differs')
    need(selection['selected_locator']==[78,375] and selection['intersection_original_locators']==[list(v) for v in sorted(intersection)],
         'complete registered intersection/locator membership differs')
    need(selected is not None,'fixed original leaf missing')
    root,node,nodes,parents=selected
    need(node==selection['complete_selected_original_leaf'] and node['reason']=='path_depth_limit_retained','complete original source leaf differs')
    reversed_path=[];ni=375
    while ni:
        parent,branch=parents[ni];reversed_path.append((parent,ni,branch));ni=parent
    path=list(reversed(reversed_path));cell=decode(root['root_box_exact']);records=[]
    for parent,child,branch in path:
        n=nodes[parent];axis=n['axis'];cut=F(n['cut_exact'])
        need(cell[axis][0]<cut<cell[axis][1] and n['children'][branch]==child,'original path cut/child identity differs')
        lo,hi=cell[axis];cell=list(cell);cell[axis]=(lo,cut) if branch==0 else (cut,hi)
        records.append({'original_parent_node':parent,'original_child_node':child,'branch':branch,'axis':axis,
                        'cut_exact':str(cut),'original_cut_source':n['cut_source']})
    need(len(path)==selection['selected_original_depth']==24 and volume(cell)==fixed_volume==F(node['positive_directed_volume_exact']),
         'original inherited depth/positive volume differs')
    return cell,node,records


def import_original_checker(row):
    need(same(identity(row['path']),row),'pinned original independent checker source differs')
    spec=importlib.util.spec_from_file_location('r7e_cost_probe_original_independent_v6_checker',row['path'])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    need(not any(name.split('.')[0] in ('FreeCAD','Part','OCC','OCP','cadquery') for name in sys.modules),'native module unexpectedly imported')
    return module


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();contract=json.loads(args.contract.read_text())
    need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0 and sys.dont_write_bytecode,
         'isolated unoptimized bytecode-disabled original standard Python entry required')
    need(contract['schema']=='razr-r7e-one-split-spatial-cost-probe-contract-v1' and same(identity(__file__),contract['source']),
         'registered standalone one-split probe source differs')
    need(contract['wall_seconds']==60 and contract['address_space_bytes']==536870912 and contract['maximum_new_splits']==1 and
         contract['maximum_new_child_channel_attempts']==2 and contract['maximum_parent_channel_replays']==1,
         'registered finite cost-probe scope/resource cap differs')
    need(contract['original_V6_depth_cap_exceeded'] is True and contract['original_V6_depth_gate_passed'] is False and
         contract['qualification_claimed'] is False,'depth-exceeding cost-diagnostic scope must remain explicit')
    need(not args.output.exists(),'new diagnostic output directory required');args.output.mkdir(parents=True)
    started=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('registered 60-second finite spatial cost-probe cap')));signal.alarm(60)
    report={'schema':'razr-r7e-one-original-split-spatial-cost-probe-v1','started_utc':datetime.now(timezone.utc).isoformat(),
        'completed':False,'source':identity(__file__),'contract':identity(args.contract),'finite_cost_diagnostic_only':True,
        'new_full_frame_execution':False,'V9_first_u_qualification':False,'original_V9_owned_failure_reclassified':False,
        'planned_probe_exceeds_original_V6_depth_cap':True,'actual_new_split_exceeds_original_V6_depth_cap':False,
        'original_V6_depth_gate_passed':False,'original_cumulative_depth_unchanged_claimed':False,
        'native_operations':0,'producer_or_primitive_helper_imported':False,'pinned_original_independent_checker_imported':False,
        'new_owned_scientific_qualification':False,'full_continuous_G2':False,'all_blockers_closed':False,'child_observations':[]}
    counters=None;baseline=None;independent_calls=0;earlier=None;before={}
    try:
        inputs=contract['inputs'];archive=contract['original_V6_archive_files']
        bound_all=dict(inputs)
        for name,row in archive.items():bound_all['V6_archive/'+name]=row
        before={k:identity(v['path']) for k,v in bound_all.items()}
        need(all(same(before[k],v) for k,v in bound_all.items()),'complete registered source/archive identity differs')
        report['original_function_copy_checks']=verify_original_function_copies(contract,inputs)
        bridge=load(inputs['original_V6_archive_bridge']);expected={r['path']:r for r in bridge['files']}
        need(len(archive)==len(expected)==53 and set(archive)==set(expected) and all(same(archive[k],expected[k]) for k in archive),
             'complete original53 V6 archive mapping differs')
        old_producer=load(archive['all-primitive-support-frames/report.json']);old_checker=load(archive['verify-all/report.json']);old_pipeline=load(archive['pipeline.json'])
        need(old_producer['execution_completed'] and old_checker['execution_completed'] and old_pipeline['completed'] and
             old_producer['primitive_support_model_conditional_clearance_passes']==old_checker['primitive_support_model_conditional_clearance_passes']==8,
             'original qualified V6 mathematical/owned status differs')
        need(same(old_checker['verified_producer_report'],archive['all-primitive-support-frames/report.json']),
             'original independent V6 reader verified another producer report')
        old_lock=load(inputs['original_V6_source_lock']);old_files={r['path']:r for r in old_lock['r5_files']}
        need(same(old_pipeline['source_lock_identity'],inputs['original_V6_source_lock']),
             'original qualified pipeline source-lock identity differs')
        for label,filename in [('original_primitive_producer_source','primitive_refinement_r5e_v6.py'),
                               ('original_primitive_model_source','primitive_support_model_r5e_v6.py'),
                               ('original_channel_source','exterior_channels_r5e_v3.py'),
                               ('original_independent_checker_source','verify_primitive_support_r5e_v6.py')]:
            need(same(inputs[label],old_files[filename]),'original qualified function source differs from its frozen lock')
        for label in ('all-primitive-support-frames','verify-all'):
            control=load(archive[label+'-supervision/controller.json']);stage=next(s for s in old_pipeline['stages'] if s['label']==label)
            need(control['completed'] and control['worker_exit_code']==0 and control['resource_stop'] is None and stage['completed'] and
                 same(stage['report'],archive[label+'/report.json']),'original owned V6 stage binding differs')
            worker_name='primitive_refinement_r5e_v6.py' if label=='all-primitive-support-frames' else 'verify_primitive_support_r5e_v6.py'
            need(control['limits']['worker']['sha256']==old_files[worker_name]['sha256'],
                 'original owned worker did not execute the frozen source')
        old_frame=next(f for f in old_producer['frames'] if (f['case_id'],f['frame'])==('case-028',1))
        old_row=archive['all-primitive-support-frames/'+old_frame['certificate']['path']]
        need(same(old_frame['certificate'],old_row),'original selected-frame certificate binding differs')
        old=load(old_row,True);need(old['frame']=={k:v for k,v in old_frame.items() if k!='certificate'},'complete original V6 frame header differs')
        v9=load(inputs['actual_V9_producer_report']);v9_checker=load(inputs['actual_V9_checker_report']);v9_controller=load(inputs['actual_V9_checker_controller']);v9_pipeline=load(inputs['actual_V9_pipeline'])
        need(v9['execution_completed'] and v9_checker['execution_completed'] and v9_controller['completed'] is False and
             v9_controller['worker_exit_code']==0 and v9_pipeline['completed'] is False and len(v9_pipeline['stages'])==2,
             'original completed workers/failed owned V9 distinction differs')
        need(v9_controller['failure']=={'type':'RuntimeError','message':"still-running owned child RSS unavailable: KeyError: 'VmRSS'"},
             'original V9 ownership failure must remain unchanged')
        need(v9_checker['total_saved_planar_u_separations_verified']==0,'original V9 saved-u failure differs')
        v9_frame=v9['frames'][0];boundary=old['boundary_refinement']
        need(canonical(boundary)==v9_frame['base_V6_boundary_canonical_sha256'] and
             old_frame['original_remaining_displacement_box_exact']==v9_frame['original_remaining_displacement_box_exact'],
             'complete original material carriers or whole displacement changed')
        selection=load(inputs['fixed_source_selection']);cell,old_leaf,path=original_source_selection(old,selection)
        need(same(selection['original_V6_certificate'],old_row) and selection['selected_original_depth']==24,
             'registered representative selected another original frame/depth')
        limits=dict(contract['original_capacity']);actual_contract=load(inputs['actual_V9_single_contract'])
        need(limits==actual_contract['capacity']==v9['capacity'] and limits['maximum_depth']==24 and limits['maximum_splits']==4096 and
             limits['maximum_boundary_box_tests']==limits['maximum_support_inequality_tests']==12000000 and
             F(limits['tiny_retained_volume_exact'])==F(1e-7)/100000,'original tolerance/capacity definitions differ')
        baseline=dict(v9['counters']);need(baseline['splits']==81 and baseline['boundary_box_tests']==171429 and baseline['support_inequality_tests']==342440,
                                         'original V9 actual work may not be erased')
        counters=dict(baseline)
        corr=load(inputs['actual_correlation_diagnostic']);wire=load(inputs['actual_wire_diagnostic'])
        need(corr['completed'] and wire['completed'] and len(wire['targets'])==4,'prior finite diagnostic outcomes differ')
        prior_support=sum(corr['counters'][k] for k in ('clip_endpoint_inequalities','vertex_feasibility_inequalities','UV_support_inequalities'))+sum(wire['counters'].values())
        prior_pieces=corr['counters']['UV_piece_tests']+wire['complete_saved_source_piece_tests']+wire['complete_original_Line_tests']+wire['fixed_original_Circle_parameter_tests']+sum(t['wire_winding_diagnosis']['complete_source_piece_count'] for t in wire['targets'])
        need(prior_support==19928 and prior_pieces==1432,'prior finite diagnostic actual work ledger differs')
        earlier={'conservative_support_like_debit':prior_support,'conservative_piece_like_debit':prior_pieces,
            'correlation_actual_counters':corr['counters'],'wire_actual_counters':wire['counters'],
            'correlation_actual_seconds':corr['elapsed_seconds'],'wire_actual_seconds':wire['elapsed_seconds'],
            'wire_Taylor_parameters':wire['independent_Taylor_parameter_count'],'wire_terms_per_function':wire['Taylor_terms_per_function'],
            'noncomparable_source_construction_cost_is_not_hidden_in_separator_counts':True,
            'all_counted_diagnostic_comparisons_debited_conservatively':True}
        earlier['earlier_original_domain_source_validation_attempts']=[]
        for key in ('actual_original_domain_attempt1','actual_original_domain_attempt2'):
            domain=load(inputs[key])
            need(domain['channel_searches']==0 and domain['native_operations']==0,'earlier source diagnostic scope differs')
            earlier['earlier_original_domain_source_validation_attempts'].append({'input':inputs[key],
                'completed':domain['completed'],'failure':domain.get('failure'),'elapsed_seconds':domain['elapsed_seconds'],
                'peak_RSS_bytes':domain['peak_RSS_bytes'],'channel_searches':0,'algebraic_validation_comparison_count_recorded':False,
                'not_claimed_free_or_a_reusable_spatial_separator_proof':True})
        del corr,wire
        sources=runtime_sources(boundary);base=SimpleNamespace(channel_for=channel_for,encode=encode);model=SimpleNamespace(project=project)
        check=import_original_checker(inputs['original_independent_checker_source']);report['pinned_original_independent_checker_imported']=True
        check_sources=[]
        for s in boundary['sources']:
            check_sources.append({'whole':check.intervals(s['known_whole_exact']),
                'pieces':[{'box':check.intervals(p['box_exact']),
                           'additional_slabs':[(check.vector(v['normal_exact']),check.intervals([v['bounds_exact']],1)[0]) for v in p['additional_slabs']],
                           'slab_source':p['additional_slabs'][0]['source'] if p['additional_slabs'] else None} for p in s['pieces']]})
        original_separator=check.separator_holds
        def counted_original_separator(piece,channel,code):
            nonlocal independent_calls
            independent_calls+=1
            need(independent_calls<=contract['maximum_independent_separator_calls'],'fixed original-checker predicate-call cap exceeded')
            need(counters['support_inequality_tests']+prior_support+independent_calls<=12000000 and
                 counters['boundary_box_tests']+prior_pieces+independent_calls<=12000000,'cumulative experiment budget including diagnostics exceeded')
            return original_separator(piece,channel,code)
        check.separator_holds=counted_original_separator
        need(volume(cell)>F(limits['tiny_retained_volume_exact']),'registered representative is already original-tiny')
        parent_before=dict(counters);parent=attempt_channel(base,model,cell,sources,counters,limits)
        need(parent==old_leaf['actual_channel_observation'] and parent['excluded_open_interior'] is False,
             'fresh original parent replay differs from complete saved original failure')
        parent_cost={k:counters[k]-parent_before[k] for k in counters}
        axis,cut,witness=choose_cut(cell,sources,parent)
        independent_cut=check.independent_cut(tuple(cell),check_sources,parent)
        need((axis,cut,witness)==independent_cut,'original independent cut derivation differs')
        need(cell[axis][0]<cut<cell[axis][1],'original split must be strictly internal')
        low=list(cell);high=list(cell);low[axis]=(cell[axis][0],cut);high[axis]=(cut,cell[axis][1])
        parent_volume=volume(cell);child_volumes=[volume(low),volume(high)]
        need(all(v>0 for v in child_volumes) and sum(child_volumes,F(0))==parent_volume,'exact positive partition must conserve complete source volume')
        counters['splits']+=1;need(counters['splits']==82 and counters['splits']<=limits['maximum_splits'],'one and only one new split allowed')
        counters['tree_nodes_visited']+=1
        report.update(source_locator=[78,375],source_original_depth=24,diagnostic_local_depth=1,cumulative_depth_from_original_V6_root=25,
            actual_new_split_exceeds_original_V6_depth_cap=True,
            original_V6_global_split_cap_already_spent=4096,prior_V9_additional_splits=81,
            original_V6_plus_V9_plus_probe_split_count=4096+counters['splits'],
            original_complete_parent_leaf=old_leaf,original_complete_path=path,original_parent_box_exact=encode(cell),
            original_full_remaining_D=old_frame['original_remaining_displacement_box_exact'],
            complete_original_boundary_canonical_sha256=canonical(boundary),original_source_material_keys=[s['material_key'] for s in boundary['sources']],
            original_source_piece_counts=[len(s['pieces']) for s in boundary['sources']],
            actual_parent_replay=parent,actual_parent_replay_counter_cost=parent_cost,
            actual_cut={'axis':axis,'cut_exact':str(cut),'cut_source':witness,'original_independent_cut_equal':True,
                        'closed_cut_plane_retained_as_zero_volume_carrier':True},
            original_parent_positive_directed_volume_exact=str(parent_volume),actual_child_positive_directed_volumes_exact=[str(v) for v in child_volumes])
        excluded=F(0);pending=F(0);new_attempts=0
        for child_index,child in enumerate((low,high)):
            value=child_volumes[child_index];prior_counts=dict(counters);prior_independent=independent_calls
            counters['tree_nodes_visited']+=1
            row={'child_index':child_index,'box_exact':encode(child),'positive_directed_volume_exact':str(value),
                 'diagnostic_local_depth':1,'cumulative_depth_from_original_V6_root':25,
                 'whole_closed_cell_disjoint_claimed':False,'all_closed_boundaries_retained':True}
            if value<=F(limits['tiny_retained_volume_exact']):
                row.update(status='retained_tiny_at_original_threshold',separator_attempt_executed=False);pending+=value
            else:
                new_attempts+=1;observation=attempt_channel(base,model,child,sources,counters,limits)
                need(not observation.get('search_stopped_at_predicate_budget'),'fixed complete probe must preserve any actual predicate-budget failure')
                row.update(separator_attempt_executed=True,complete_actual_original_channel_observation=observation)
                if observation['excluded_open_interior']:
                    check_result=check.check_exclusion(observation,tuple(child),check_sources);excluded+=value
                    row.update(status='original_spatial_rule_excludes_open_interior',original_independent_checker_result=check_result)
                else:
                    checked=check.check_unresolved(observation,tuple(child),check_sources);pending+=value
                    row.update(status='pending_after_fixed_one_split_cost_probe',actual_material_interference_claimed=False,
                               original_independent_unresolved_channels_checked=checked,not_an_original_V6_depth_gate_pass=True)
            row['actual_producer_counter_cost']={k:counters[k]-prior_counts[k] for k in counters}
            row['actual_independent_separator_calls']=independent_calls-prior_independent
            report['child_observations'].append(row)
        need(new_attempts<=2 and len(report['child_observations'])==2 and excluded+pending==parent_volume,
             'fixed complete two-child source volume accounting failed')
        bad=dict(parent);bad['all_registered_channels_unresolved']=parent['all_registered_channels_unresolved'][:-1]
        rejected=False
        try:check.check_unresolved(bad,tuple(cell),check_sources)
        except ValueError as exc:rejected=True;message=str(exc)
        need(rejected,'original independent checker accepted omitted actual unresolved channel')
        controls=[{'name':'omitted_actual_parent_failed_channel','execution_kind':'actual_saved_source_mutation','rejected':True,'message':message}]
        successes=[r for r in report['child_observations'] if r['status']=='original_spatial_rule_excludes_open_interior']
        if successes:
            r=successes[0];mutated=dict(r['complete_actual_original_channel_observation']);mutated['complete_piece_separation_codes']=mutated['complete_piece_separation_codes'][:-1]
            rejected=False
            try:check.check_exclusion(mutated,tuple(decode(r['box_exact'])),check_sources)
            except ValueError as exc:rejected=True;message=str(exc)
            need(rejected,'original independent checker accepted omitted actual source-piece proof')
            controls.append({'name':'omitted_actual_child_piece_proof','execution_kind':'actual_new_child_proof_mutation','rejected':True,'message':message})
        else:controls.append({'name':'omitted_actual_child_piece_proof','execution_kind':'not_applicable_no_actual_excluded_child','rejected':False,'counted_as_control_pass':False})
        delta={k:counters[k]-baseline[k] for k in counters}
        need(delta['splits']==1 and delta['tree_nodes_visited']==3 and delta['boundary_box_tests']<=12636 and
             delta['support_inequality_tests']<=101088 and independent_calls<=1142,'registered finite three-attempt capacity exceeded')
        support_debit=counters['support_inequality_tests']+prior_support+independent_calls
        piece_debit=counters['boundary_box_tests']+prior_pieces+independent_calls
        need(support_debit<=12000000 and piece_debit<=12000000,'all diagnostic and replay work must remain visible within cumulative debit')
        report.update(completed=True,original_V9_owned_failure_retained=v9_controller['failure'],original_first_u_gate_reached=False,
            actual_new_child_channel_attempts=new_attempts,actual_new_splits=1,
            local_excluded_open_volume_exact=str(excluded),local_pending_positive_volume_exact=str(pending),
            exact_complete_parent_volume_conserved=True,pending_is_not_evidence_of_native_interference=True,
            diagnostic_controls=controls,original_V6_producer_historical_counters=old_producer['counters'],
            original_V9_producer_historical_counters=baseline,actual_this_probe_producer_counter_cost=delta,
            actual_this_probe_independent_separator_calls=independent_calls,earlier_diagnostic_cost_ledger=earlier,
            cumulative_conservative_additional_stage_debit={'splits':counters['splits'],'piece_like_tests':piece_debit,'support_like_tests':support_debit},
            remaining_conservative_additional_stage_budget={'splits':4096-counters['splits'],'piece_like_tests':12000000-piece_debit,
                                                           'support_like_tests':12000000-support_debit},
            actual_independent_source_unchanged=same(identity(inputs['original_independent_checker_source']['path']),inputs['original_independent_checker_source']),
            all_registered_inputs_unchanged=all(same(identity(v['path']),before[k]) for k,v in bound_all.items()),
            source_input_identities=before,
            representative_result_transferred_to_other_leaves=False,full_frame_bound_computed=False,
            original_V6_depth24_or_V9_UV_qualification_claimed=False)
        need(report['all_registered_inputs_unchanged'] and report['actual_independent_source_unchanged'],'registered frozen input source changed')
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0)
        report.update(actual_partial_producer_counters=counters,actual_prior_V9_counter_baseline=baseline,
            actual_independent_separator_calls_including_failure=independent_calls,earlier_diagnostic_cost_ledger_if_reached=earlier,
            partial_or_complete_registered_input_identities=before,
            elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            finished_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=60,address_space_bytes=536870912)
        path=args.output/'R7E_ONE_SPLIT_ORIGINAL_SPATIAL_COST_PROBE_V1.json'
        path.write_text(json.dumps(report,indent=2)+'\n');need(path.stat().st_size<=4194304,'registered 4-MiB diagnostic output cap exceeded')
    print(json.dumps({'completed':report['completed'],'report':identity(path),'seconds':report['elapsed_seconds'],
                      'RSS':report['peak_RSS_bytes'],'failure':report.get('failure')}))
    return 0 if report['completed'] else 2


if __name__=='__main__':raise SystemExit(main())
