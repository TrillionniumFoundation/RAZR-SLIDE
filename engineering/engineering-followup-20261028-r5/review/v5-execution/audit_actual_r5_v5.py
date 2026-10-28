#!/usr/bin/env python3
"""Independent actual V5 audit. No producer, helper or checker is imported.

Exact tree/channel predicates adapted from this reviewer's frozen V4 auditor,
SHA 38cf95ec9dd157f414a6efdb658cd45b82343dd559d9a121402d60b58d329984.
V5 conditional UV boundary reconstruction uses independent U-stratum sweeps
and unions of closed V intervals, not the producer's rectangle subtraction
or the independent CI checker's patch-per-stratum search.
"""
import copy
from collections import Counter
import datetime as dt
from fractions import Fraction as Q
import gc
import gzip
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath
import resource
import signal
import time
import traceback
import zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ACTUAL=BASE/'r5-ci-results/run-40645988108'
ARCHIVE=BASE/'r5-ci-results/RAZR-R5-trim-model-v5-run-40645988108.zip'
R5=BASE/'r5-envelope'
R4=BASE/'r4-envelope/public-final-v2'
REMOTE_OUTPUT='/home/runner/work/_temp/razr-r5-trim-model-v5'
REMOTE_R5='/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/engineering/engineering-followup-20261028-r5/compute'
REMOTE_R4='/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/engineering/engineering-followup-20261027-r4/envelope'
HEAD='2ce252f25d340b056bfd350bdde8c743f915c9a4'
ANCHOR='c5f6606924937d716b007cd3ffa8e54df8ecfa5d'
ZIP_SHA='3128fa481c2e7fe5e5cbf4e09822739349cc1e12b0edf16544c483ca7bdac0d9'
LOCK_SHA='d05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211'
WORKFLOW_SHA='d47de5cb65f6abaed20392ca1ad06032d243cea703dc081b835e43d73a8e1417'
LIMITS=dict(wall_seconds=600,RSS_limit_bytes=805306368,shared_ceiling_bytes=7301444403,disk_floor_bytes=104857600,maximum_output_bytes=41943040,metadata_margin_bytes=4194304)
CAPACITY=dict(wall_seconds=600,RSS_limit_bytes=805306368,maximum_splits=4096,maximum_depth=24,maximum_boundary_box_tests=12000000,tiny_retained_volume_exact=str(Q(1e-7)/100000),maximum_uv_patches_per_face=1024,maximum_boundary_pieces_per_material=4096)
SEQUENCE=[('single-trim-model-cell','single_trim_model_cell'),('verify-single','verify_single'),('preflight-trim-model','preflight_trim_model'),('all-trim-model-frames','all_trim_model_frames'),('verify-all','verify_all')]
EXPECTED=[(case,frame) for case in ('case-001','case-006','case-028','case-037','case-054','case-063','case-072','case-089') for frame in (1,2)]
CACHE={}
COUNTS=dict(assertions=0,excluded_cell_separation_inequalities=0,blocked_direction_checks=0,independent_control_inequalities=0,independent_control_blockers=0,source_proofs_decoded=0,source_proof_decoded_bytes=0,certificate_files_decoded=0,certificate_decoded_bytes=0)
MUTATING=False
REPORT={'schema':'razr-r5-v5-independent-actual-conditional-model-readback','audit_completed':False,'actual_run_id':40645988108,'actual_head':HEAD,'producer_helper_or_verifier_imported':False,'native_operations_executed':0,'original_R4_enclosure_recomputed':False,'full_channel_search_replayed':False,'conditional_trim_model_only':True,'native_trim_class_membership_verified':False,'inner_wire_hole_semantics_verified_for_native':False,'original_raw_gate_reclassified':False,'full_continuous_G2':False,'all_blockers_closed':False,'independent_negative_controls':[],'frames':[]}
OUTPUT=HERE/'R5_V5_INDEPENDENT_ACTUAL_EXECUTION_READBACK.json'
REGISTRATION=HERE/'R5_V5_ACTUAL_READBACK_BUDGET.json'


def need(value, message):
    COUNTS['assertions'] += 1
    if not value:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def ranges(value):
    need(len(value) == 3 and all(len(pair) == 2 for pair in value), 'three interval axes required')
    result = tuple(tuple(Q(x) for x in pair) for pair in value)
    need(all(a <= b for a,b in result), 'reversed source interval')
    return result

def measure(box):
    need(all(a < b for a,b in box), 'cell must have three positive directed widths')
    return (box[0][1]-box[0][0]) * (box[1][1]-box[1][0]) * (box[2][1]-box[2][0])

def valid_index(value, maximum):
    return type(value) is int and 0 <= value < maximum

def check_excluded(cell, target, sources, count=True):
    need(cell['excluded_open_interior'] is True, 'expected excluded open interior')
    need(cell['closed_cell_boundary_retained_as_zero_volume_carrier'] is True and cell['whole_closed_cell_disjoint_claimed'] is False,
         'closed boundary must be retained; closed-cell disjointness overclaims')
    side, axis, end = (cell[k] for k in ('material_side','axis','end'))
    need(valid_index(side,2) and valid_index(axis,3) and valid_index(end,2), 'bad chosen channel index')
    pieces, hull = sources[side]
    channel = ranges(cell['open_channel_exact'])
    need(all(a < b for a,b in channel), 'channel has no connected open interior')
    need(all(channel[k] == target[k] for k in range(3) if k != axis), 'channel transverse cell identity changed')
    need(channel[axis][1] == target[axis][1] and channel[axis][0] < min(hull[axis][0],target[axis][0]) if end == 0
         else channel[axis][0] == target[axis][0] and channel[axis][1] > max(hull[axis][1],target[axis][1]), 'channel fails to reach known exterior')
    codes = cell['complete_piece_separation_codes']
    need(type(codes) is str and len(codes) == len(pieces) == cell['boundary_piece_count'], 'incomplete boundary-piece separation coverage')
    for piece, code in zip(pieces,codes):
        need(code in '012345', 'invalid separating coordinate code')
        k, end_sign = divmod(int(code),2)
        need(piece[k][1] <= channel[k][0] if end_sign == 0 else piece[k][0] >= channel[k][1], 'false closed-box/open-channel separating inequality')
    if count:
        COUNTS['independent_control_inequalities' if MUTATING else 'excluded_cell_separation_inequalities'] += len(pieces)
    return len(pieces)

def check_kept(cell, target, sources):
    need(cell['excluded_open_interior'] is False and cell['actual_material_interference_claimed'] is False, 'unresolved cover cannot claim actual collision')
    rows = cell['all_registered_channels_blocked']
    need(len(rows) == 12, 'all twelve registered channels must remain represented')
    seen = set()
    for row in rows:
        side, axis, end, index = (row[k] for k in ('material_side','axis','end','blocking_piece_index'))
        need(valid_index(side,2) and valid_index(axis,3) and valid_index(end,2), 'invalid blocked channel')
        need((side,axis,end) not in seen, 'duplicate blocked channel')
        seen.add((side,axis,end))
        pieces, hull = sources[side]
        need(valid_index(index,len(pieces)), 'invalid blocked boundary index')
        channel = list(target)
        channel[axis] = (min(hull[axis][0]-1,target[axis][0]-1),target[axis][1]) if end == 0 else (target[axis][0],max(hull[axis][1]+1,target[axis][1]+1))
        need(all(pieces[index][k][1] > channel[k][0] and pieces[index][k][0] < channel[k][1] for k in range(3)), 'recorded boundary blocker misses open channel')
        COUNTS['independent_control_blockers' if MUTATING else 'blocked_direction_checks'] += 1
    need(seen == set(itertools.product(range(2),range(3),range(2))), 'incomplete blocked direction identities')

def exact_box_strings(box):
    return [[str(x) for x in pair] for pair in box]

def tree_readback(tree, root_box, sources):
    nodes=tree['nodes']
    need(nodes and all(type(n['id']) is int and n['id']==i for i,n in enumerate(nodes)), 'contiguous tree identities required')
    pending=[(0,root_box,0)]
    seen=set(); leaves=[]; splits=[]; retained=Q(0); removed=Q(0); reasons={}; max_depth=0
    while pending:
        i, box, depth=pending.pop()
        need(type(i) is int and 0<=i<len(nodes) and i not in seen, 'missing, repeated, cyclic or unreachable child')
        seen.add(i); node=nodes[i]; value=measure(box); max_depth=max(max_depth,depth)
        need(depth<=CAPACITY['maximum_depth'], 'path depth budget exceeded')
        if node['kind']=='split':
            k=node['axis'];need(valid_index(k,3), 'invalid split axis')
            cut=Q(node['cut_exact']);need(box[k][0]<cut<box[k][1], 'split must lie strictly inside parent')
            witness=node['cut_source'];side,piece,axis,end=(witness[x] for x in ('material_side','piece_index','axis','endpoint'))
            need(valid_index(side,2) and valid_index(piece,len(sources[side][0])) and type(axis) is int and axis==k and valid_index(end,2), 'invalid registered model endpoint witness')
            need(sources[side][0][piece][k][end]==cut, 'split is not registered model boundary endpoint')
            children=node['children']
            need(type(children) is list and len(children)==2 and all(type(x) is int and i<x<len(nodes) for x in children) and children[0]!=children[1], 'two distinct forward children required')
            left=list(box);right=list(box);left[k]=(box[k][0],cut);right[k]=(cut,box[k][1]);a,b=measure(left),measure(right)
            need(a+b==value==Q(node['parent_positive_directed_volume_exact']), 'exact parent signed volume conservation failed')
            need([a,b]==[Q(x) for x in node['children_positive_directed_volumes_exact']], 'declared child signed volumes differ')
            need(node['closed_cut_plane_retained_as_zero_volume_carrier'] is True, 'closed cut carrier missing')
            splits.append({'node_id':i,'depth':depth,'parent_box_exact':exact_box_strings(box),'cut_source':witness,'cut_exact':str(cut),'parent_volume_exact':str(value),'children_volume_exact':[str(a),str(b)]})
            pending.extend([(children[1],tuple(right),depth+1),(children[0],tuple(left),depth+1)])
        elif node['kind']=='retained':
            need(Q(node['positive_directed_volume_exact'])==value and node['actual_material_interference_claimed'] is False, 'positive retained volume/scope altered')
            reason=node['reason']
            need(reason in ('tiny_exact_volume_retained','global_predicate_budget_retained','path_depth_limit_retained','global_split_limit_retained','no_registered_model_boundary_endpoint_inside_cell'), 'unregistered stop reason')
            if reason=='tiny_exact_volume_retained':need(value<=Q(CAPACITY['tiny_retained_volume_exact']), 'tiny retained threshold invalid')
            if reason=='path_depth_limit_retained':need(depth==CAPACITY['maximum_depth'], 'incorrect path stop')
            observation=node.get('actual_channel_observation')
            checked_directions=0
            if observation is not None:
                need(observation['excluded_open_interior'] is False and observation['actual_material_interference_claimed'] is False, 'retained observation overclaims')
                if observation.get('search_stopped_at_predicate_budget'):
                    need(reason=='global_predicate_budget_retained', 'partial search needs explicit budget retention')
                else:
                    check_kept(observation,box,sources);checked_directions=12
            if reason=='no_registered_model_boundary_endpoint_inside_cell':
                need(observation is not None and checked_directions==12, 'no-cut reason requires twelve real blockers')
                for obstruction in observation['all_registered_channels_blocked']:
                    piece_box=sources[obstruction['material_side']][0][obstruction['blocking_piece_index']]
                    need(all(not box[k][0]<endpoint<box[k][1] for k in range(3) for endpoint in piece_box[k]), 'no-cut label contradicts a strictly interior blocking endpoint')
            retained+=value;reasons[reason]=reasons.get(reason,0)+1
            leaves.append({'node_id':i,'depth':depth,'kind':'retained','reason':reason,'box_exact':exact_box_strings(box),'positive_directed_volume_exact':str(value),'display_mm3':float(value),'blocked_directions_checked':checked_directions})
        elif node['kind']=='excluded':
            need(Q(node['positive_directed_volume_exact'])==value, 'excluded positive directed volume changed')
            checked=check_excluded(node['certificate'],box,sources)
            removed+=value
            leaves.append({'node_id':i,'depth':depth,'kind':'excluded','box_exact':exact_box_strings(box),'positive_directed_volume_exact':str(value),'boundary_piece_separations_checked':checked})
        else:raise ValueError('unknown node disposition')
    need(seen==set(range(len(nodes))), 'allocated pending leaf or unreachable node omitted')
    need(retained+removed==measure(root_box), 'root exact volume not conserved')
    need(retained==Q(tree['retained_sum_exact']) and removed==Q(tree['excluded_open_sum_exact']), 'tree exact sums differ')
    need(len(nodes)==2*len(splits)+1 and len(leaves)==len(splits)+1, 'full binary tree topology identity differs')
    excluded=sum(x['kind']=='excluded' for x in leaves)
    need(len(leaves)==tree['total_leaf_count'] and excluded==tree['excluded_leaf_count'] and len(leaves)-excluded==tree['retained_leaf_count'], 'complete leaf count differs')
    need(reasons==tree['retained_reason_counts'] and max_depth==tree['maximum_depth_reached'], 'actual stop/depth summary differs')
    need(tree['all_closed_cut_planes_and_root_boundaries_retained'] is True, 'root/cut closed carriers not retained')
    return {'retained_sum_exact':str(retained),'excluded_open_sum_exact':str(removed),'node_count':len(nodes),'split_count':len(splits),'leaf_count':len(leaves),'excluded_leaf_count':excluded,'retained_leaf_count':len(leaves)-excluded,'maximum_depth':max_depth,'retention_reasons':reasons,'leaves':leaves,'splits':splits}


def identity(path):
    path=Path(path).resolve()
    if path not in CACHE:
        with path.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        CACHE[path]={'bytes':path.stat().st_size,'sha256':digest}
    return CACHE[path]


def read_json(path):
    return json.loads(Path(path).read_text())


def mapped(path):
    for prefix, root in ((REMOTE_OUTPUT,ACTUAL),(REMOTE_R5,R5),(REMOTE_R4,R4)):
        if path.startswith(prefix+'/'):
            relative=PurePosixPath(path[len(prefix)+1:])
            need(not relative.is_absolute() and '..' not in relative.parts,'remote identity escapes registered root')
            return root.joinpath(*relative.parts)
    raise ValueError('unregistered recorded path: '+path)


def bound(record, relative_root=None):
    path=mapped(record['path']) if relative_root is None else relative_root/record['path']
    need(identity(path)=={k:record[k] for k in ('bytes','sha256')},'actual identity differs: '+str(path))
    return path


def canonical(value):
    return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())


def decoded_gzip(path, maximum, kind):
    with gzip.open(path,'rb') as stream:data=stream.read(maximum+1)
    need(len(data)<=maximum,'registered decode budget exceeded: '+str(path))
    if kind=='source':
        COUNTS['source_proofs_decoded']+=1;COUNTS['source_proof_decoded_bytes']+=len(data)
        need(COUNTS['source_proofs_decoded']<=16,'original proof decoded more than once per frame')
    elif kind=='certificate':
        COUNTS['certificate_files_decoded']+=1;COUNTS['certificate_decoded_bytes']+=len(data)
    return json.loads(data)


def utc(value):
    return dt.datetime.fromisoformat(value.replace('Z','+00:00'))


def conditional(record):
    need(record['conditional_trim_model_only'] is True and
         record['native_trim_class_membership_verified'] is False and
         record['inner_wire_hole_semantics_verified_for_native'] is False and
         record['original_raw_gate_reclassified'] is False and record['full_continuous_G2'] is False,
         'conditional model promoted to native/original qualification')


def archive_and_source_chain():
    remote=read_json(HERE/'R5_V5_INDEPENDENT_REMOTE_METADATA.json')
    run=json.loads(remote['run']['structuredContent']['content'])
    jobs=remote['jobs']['structuredContent']['jobs']
    artifacts=remote['artifacts']['structuredContent']['artifacts']
    need(run['id']==40645988108 and run['head_sha']==HEAD and run['head_branch']=='evidence/full-sprint-20261028-r5'
         and run['run_attempt']==1 and run['event']=='push' and run['status']=='completed' and run['conclusion']=='success',
         'fresh remote run/head/branch/attempt differs')
    need(run['repository']['full_name']=='TrillionniumFoundation/RAZR-SLIDE' and run['path']=='.github/workflows/r5-exterior-channel.yml',
         'remote workflow/repository differs')
    need(len(jobs)==1 and jobs[0]['id']==122674800673 and jobs[0]['run_id']==run['id'] and
         jobs[0]['status']=='completed' and jobs[0]['conclusion']=='success' and
         all(s['status']=='completed' and s['conclusion']=='success' for s in jobs[0]['steps']), 'remote actual job incomplete')
    need(len(artifacts)==1,'unexpected remote artifact inventory')
    artifact=artifacts[0]
    need(artifact['id']==12797591032 and artifact['name']=='R5-trim-model-v5-40645988108-1' and
         artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==HEAD and
         artifact['workflow_run']['head_branch']==run['head_branch'] and not artifact['expired'], 'remote artifact provenance differs')
    archive_id=identity(ARCHIVE)
    need(archive_id=={'bytes':1356621,'sha256':ZIP_SHA} and artifact['size_in_bytes']==archive_id['bytes'] and
         artifact['digest']=='sha256:'+ZIP_SHA,'published artifact/received archive identity differs')
    members=[]
    with zipfile.ZipFile(ARCHIVE) as stream:
        rows=stream.infolist();names=[r.filename for r in rows]
        need(len(names)==len(set(names))==53 and all(not r.is_dir() for r in rows),'archive member count/uniqueness differs')
        for row in rows:
            relative=PurePosixPath(row.filename)
            need(not relative.is_absolute() and '..' not in relative.parts,'unsafe archive member path')
            data=stream.read(row)
            member={'path':row.filename,'bytes':len(data),'sha256':sha(data)}
            need(identity(ACTUAL/row.filename)=={k:member[k] for k in ('bytes','sha256')},'archive member differs from expanded actual artifact')
            members.append(member)
        need(stream.testzip() is None,'archive CRC failure')
    need(sum(r['bytes'] for r in members)==1602929,'actual artifact byte total differs')
    need({str(p.relative_to(ACTUAL)) for p in ACTUAL.rglob('*') if p.is_file()}==set(names),'expanded files missing/extra')
    receipt=read_json(BASE/'r5-ci-results/R5_V5_CI_ARTIFACT_RECEPTION.json')
    need(receipt['run_id']==run['id'] and receipt['head_sha']==HEAD and receipt['artifact_id']==artifact['id'] and
         receipt['zip_sha256']==ZIP_SHA and sorted(receipt['members'],key=lambda x:x['path'])==sorted(members,key=lambda x:x['path']),
         'root reception differs from independent archive readback')
    for key,local,expected in [('workflow',BASE/'r5-integration/r5-trim-v5-workflow.yml',WORKFLOW_SHA),
                               ('source_lock',R5/'R5E_PORTABLE_SOURCE_LOCK_V5.json',LOCK_SHA)]:
        item=remote[key]['structuredContent'];data=item['content'].encode()
        need(sha(data)==expected==identity(local)['sha256'] and len(data)==identity(local)['bytes'],'exact-head source differs from frozen local review')
        need(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['sha'],'remote Git blob digest differs')
    pipeline=read_json(ACTUAL/'pipeline.json');conditional(pipeline)
    need(pipeline['completed'] is True and pipeline['source_and_public_inputs_unchanged'] is True and
         pipeline['environment']['github_sha']==HEAD and pipeline['environment']['github_run_id']==str(run['id']),
         'actual complete pipeline/current execution binding differs')
    need([(s['label'],s['phase']) for s in pipeline['stages']]==SEQUENCE,'actual five-stage order differs')
    need(pipeline['source_commit']==ANCHOR and pipeline['source_root']==REMOTE_R5 and pipeline['public_r4_root']==REMOTE_R4,
         'original source anchor or source root changed')
    need(pipeline['original_V3_raw_clearance_passes_unchanged']==4 and pipeline['original_V4_selected_cell_bound_and_control_failure_unchanged'] is True and
         pipeline['native_Common_called'] is False and pipeline['original_clearance_threshold_changed'] is False and
         pipeline['original_displacement_boxes_changed'] is False and pipeline['all_blockers_closed'] is False,'historical/scope claim changed')
    bound(pipeline['source_lock_identity']);need(pipeline['source_lock_identity']['sha256']==LOCK_SHA,'actual source lock differs')
    lock=read_json(R5/'R5E_PORTABLE_SOURCE_LOCK_V5.json');wanted=[]
    for category,prefix,local in [('r5_files',REMOTE_R5,R5),('r4_source_files',REMOTE_R4,R4)]:
        for item in lock[category]:
            need(identity(local/item['path'])=={k:item[k] for k in ('bytes','sha256')},'frozen source member altered')
            wanted.append(dict(item,path=prefix+'/'+item['path']))
    need(len(wanted)==17 and pipeline['actual_source_identities']==wanted,'actual complete source identity list differs')
    bridge=read_json(R5/'R5E_PUBLIC_INPUT_BRIDGE.json')
    need(len(bridge['files'])==19 and bridge['source_commit']==ANCHOR,'original public bridge differs')
    wanted_public=[]
    for item in bridge['files']:
        need(item['decoded_json_equal'] is True and not item['changed_strings'],'public input semantic change declared')
        record=dict(item['public_identity'],path=REMOTE_R4+'/'+item['path']);bound(record);wanted_public.append(record)
    need(pipeline['public_inputs']==wanted_public,'actual complete public input identities differ')
    REPORT['actual_remote_execution']={'run_id':run['id'],'head_sha':HEAD,'head_tree':run['head_commit']['tree_id'],
        'branch':run['head_branch'],'event':run['event'],'run_attempt':run['run_attempt'],'job_id':jobs[0]['id'],
        'artifact_id':artifact['id'],'artifact_created_at':artifact['created_at'],'job_steps':jobs[0]['steps'],
        'workflow_exact_head_SHA256':WORKFLOW_SHA,'source_lock_exact_head_SHA256':LOCK_SHA,
        'fresh_independent_remote_metadata_identity':identity(HERE/'R5_V5_INDEPENDENT_REMOTE_METADATA.json')}
    REPORT['archive']={'identity':archive_id,'CRC_verified':True,'members':members,'member_count':53,
        'raw_member_bytes':1602929,'all_expanded_files_equal':True}
    REPORT['actual_source_and_input_chain']={'locked_sources_checked':17,'public_inputs_checked':19,
        'runtime_payload_and_public_input_posthash_flag_present':True,'source_lock_itself_not_in_payload_posthash_list':True,
        'original_R4_anchor':ANCHOR,'full_locked_source_identities':wanted,'full_public_input_identities':wanted_public}
    return pipeline,{r['path']:r for r in bridge['files']}


def owned_stages(pipeline):
    previous=utc(pipeline['started_utc']);nonces=set();drivers=set();results={};rows=[]
    for stage in pipeline['stages']:
        label,phase=stage['label'],stage['phase'];verifying=phase.startswith('verify_')
        for key in ('contract','supervision_contract','driver_log','controller','report'):bound(stage[key])
        contract=read_json(mapped(stage['contract']['path']));supervision=read_json(mapped(stage['supervision_contract']['path']))
        controller=read_json(mapped(stage['controller']['path']));report=read_json(mapped(stage['report']['path']))
        ep=ACTUAL/(label+'-supervision')/'entry-receipt.json';entry=read_json(ep)
        cp=REMOTE_OUTPUT+'/'+label+'-contract.json';sp=REMOTE_OUTPUT+'/'+label+'-supervision-contract.json';out=REMOTE_OUTPUT+'/'+label
        worker='verify_exterior_trim_r5e_v5.py' if verifying else 'exterior_trim_r5e_v5.py'
        conditional(contract);conditional(report)
        need(contract['phase']==phase and contract['capacity']==CAPACITY and contract['source_commit']==ANCHOR and
             contract['producer_sha256']==identity(R5/worker)['sha256'],'actual math contract/source/capacity mismatch')
        for key in ('r4_report','r4_independent_report','r4_stationary_diagnostic','public_input_bridge','method',
                    'base_producer_source','base_verifier_source','single_verifier_source','real_retained_cell_selection','trim_model_source','trim_source_bundle'):bound(contract[key])
        need(contract['all_original_D_components_retained'] is True and contract['original_float64_TOL_unchanged'] is True and
             contract['native_boundary_semantics_remains_a_premise'] is True and contract['current_factory_G2_qualified'] is False,
             'actual contract overstates native/full-D/threshold scope')
        need({k:supervision[k] for k in LIMITS}==LIMITS and supervision['expected_output_bytes']==41943040 and
             supervision['zero_RSS_missing_observations_allowed'] is False,'original resource gate changed')
        need(controller['limits']==supervision and controller['contract_sha256']==stage['supervision_contract']['sha256'] and
             supervision['registered_math_contract_sha256']==stage['contract']['sha256']==report['contract_sha256'], 'actual hash chain differs')
        need(supervision['supervisor_sha256']==controller['source_sha256']==identity(R4/'supervise_owned_pure_math_r4e_v2.py')['sha256'] and
             supervision['worker_entry_sha256']==identity(R4/'run_owned_pure_math_r4e_v3.py')['sha256'],'original controller/entry source differs')
        bound(supervision['worker']);bound(supervision['owned_process'])
        need(supervision['worker']['path']==REMOTE_R5+'/'+worker and supervision['worker_entry']==REMOTE_R4+'/run_owned_pure_math_r4e_v3.py' and
             supervision['worker_output_directory']==out,'actual owned worker/output binding differs')
        need(supervision['canonical_worker_options']==['--contract','--output'] and entry['canonical_worker_arguments']==['--contract',cp,'--output',out],
             'actual canonical arguments differ')
        need(entry['actual_argument_bindings']=={'worker_output_directory':out,'mathematical_contract_path':cp,
             'mathematical_contract_sha256':report['contract_sha256']},'actual entry did not bind math/output identity')
        need(stage['command']==['/usr/bin/python3','-I','-S','-B',REMOTE_R4+'/supervise_owned_pure_math_r4e_v2.py','--contract',sp,'--out',out+'-supervision','--','--contract',cp,'--output',out],
             'driver command differs')
        need(controller['command']==['/usr/bin/python3','-I','-S','-B',supervision['worker_entry'],'--supervision-contract',sp,'--receipt',out+'-supervision/entry-receipt.json','--','--contract',cp,'--output',out],
             'controller command differs')
        need(all(v is True for v in [stage['completed'],stage['owned_supervisor_completed'],controller['completed'],controller['entry_completed'],entry['completed'],report['execution_completed']]),
             'actual scientific/owned stage completion differs')
        need(stage['supervisor_exit_code']==controller['worker_exit_code']==entry['worker_exit_code']==0,'actual exit chain differs')
        need(all(v is True for v in [stage['actual_worker_started'],stage['worker_started_by_driver'],controller['worker_started'],entry['worker_started']]),'stage did not actually start')
        need(stage['resource_stop'] is None and controller['resource_stop'] is None and controller['missing_RSS_zero_substitutions']==0,'actual resource stop/missing-RSS substitution')
        need(controller['owned_child_identity_verified'] and controller['owned_channel_descriptors_closed'] and controller['source_and_contract_unchanged'] and
             entry['entry_and_worker_and_owned_source_unchanged'] and entry['native_geometry_imported'] is False,'owned closeout source/identity differs')
        need(previous<=utc(contract['registered_utc'])<=utc(controller['started_utc'])<=utc(controller['finished_utc']),'stage sequencing/registration differs')
        previous=utc(controller['finished_utc'])
        need(0<=report['seconds']<=controller['elapsed_seconds']<=600 and 0<report['peak_RSS_bytes']==entry['peak_RSS_bytes']<=805306368,'wall/RSS gate violation')
        handshake=controller['owned_child_handshake'];packet=handshake['packet'];parent=handshake['parent_identity'];verified=handshake['verified_binding']
        need(packet['kind']=='razr_owned_child_identity_v1' and packet['source_sha256']==supervision['worker_entry_sha256'] and packet['stat']==verified['stat'] and
             packet['status']==verified['status'],'handshake source/PID/starttime differs')
        need(packet['os_getpid']==packet['stat']['pid']==packet['status']['Pid']==int(packet['proc_self_visible_pid']) and
             packet['os_getppid']==packet['stat']['ppid']==packet['status']['PPid']==parent['os_getpid'],'child/parent PID differs')
        need(packet['pid_namespace']==verified['pid_namespace']==parent['pid_namespace'] and
             packet['pid_for_children_namespace']==verified['pid_for_children_namespace'] and
             parent['stat']['starttime_ticks']<=packet['stat']['starttime_ticks'],'namespace/starttime binding differs')
        need(len(packet['nonce'])==64 and set(packet['nonce'])<=set('0123456789abcdef') and packet['nonce'] not in nonces,'missing/reused handshake nonce')
        nonces.add(packet['nonce']);drivers.add(parent['os_getppid'])
        initial=handshake['initial_memory'];need(0<initial['VmRSS']<=initial['VmHWM']<=entry['peak_RSS_bytes'],'initial real memory differs')
        observations=controller['observations'];need(observations,'missing original admission sample')
        admission=observations[0]
        need(admission['disk_available_bytes']>=104857600+41943040+4194304 and admission['shared_unreclaimable_bytes']+805306368<=7301444403,
             'original admission gate violated')
        prior_sample=0;live=0;postexit=0
        for sample in observations[1:]:
            need(prior_sample<sample['elapsed_seconds']<=controller['elapsed_seconds'],'sample temporal order differs');prior_sample=sample['elapsed_seconds']
            need(sample['disk_available_bytes']>=104857600 and sample['shared_unreclaimable_bytes']<=7301444403 and sample['actual_output_bytes']<=41943040,'live resource gate exceeded')
            memory=sample['owned_worker_memory']
            if memory is None:
                need(sample['elapsed_seconds']>=report['seconds'],'missing memory while scientific worker still active');postexit+=1
            else:
                need(0<memory['VmRSS']<=memory['VmHWM']<=entry['peak_RSS_bytes'],'live RSS missing/zero/exceeds final peak');live+=1
        final=controller['final_resources'];need(final['disk_available_bytes']>=104857600 and final['shared_unreclaimable_bytes']<=7301444403,'final original resource gate exceeded')
        output_bytes=sum(p.stat().st_size for p in (ACTUAL/label).rglob('*') if p.is_file());need(output_bytes<=41943040,'actual output exceeds original maximum')
        prerequisites=[] if phase in ('single_trim_model_cell','verify_single','verify_all') else ['single_trim_model_cell'] if phase=='preflight_trim_model' else ['single_trim_model_cell','preflight_trim_model']
        need([r['phase'] for r in contract['completed_prerequisites']]==prerequisites,'actual prerequisite sequence differs')
        for row in contract['completed_prerequisites']:
            item=results[row['phase']]
            need(row['report']==item['stage']['report'] and row['supervisor']==item['stage']['controller'],'prerequisite references wrong actual owned stage')
            bound(row['report']);bound(row['supervisor'])
            need(item['contract']['producer_sha256']==contract['producer_sha256'] and item['contract']['r4_report']==contract['r4_report'] and
                 item['contract']['trim_source_bundle']==contract['trim_source_bundle'] and item['contract']['trim_model_source']==contract['trim_model_source'],
                 'later producer changes original/model source')
        if phase in ('preflight_trim_model','all_trim_model_frames'):
            previous_single=results['single_trim_model_cell'];verified_single=results['verify_single']
            single=previous_single['report'];first=single['frames'][0]
            need(single['trim_model_conditional_clearance_passes']==1 and Q(first['excluded_open_leaf_sum_exact'])>0 and first['model_boundary_applied_face_count']>0 and
                 first['model_boundary_applied_inner_wire_count']>0 and (first['case_id'],first['frame'])==('case-001',1) and first['root_original_cell_indices']==[202],
                 'actual single-cell prerequisite not satisfied')
            expected_binding={'report':verified_single['stage']['report'],'supervisor':verified_single['stage']['controller']}
            need(contract['independent_single_verification']==expected_binding==report['actual_independent_single_verification'] and
                 verified_single['report']['trim_model_conditional_clearance_passes']==1 and
                 verified_single['report']['verified_producer_report']==previous_single['stage']['report'],'independent prerequisite not exact actual single producer')
        if phase=='all_trim_model_frames':
            pre=results['preflight_trim_model'];pr=pre['report']
            need(contract['actual_capacity_basis']==pre['stage']['report'] and pr['all_frame_capacity_observations_completed'] and
                 len(pr['frames'])==16 and pr['total_original_roots']==1474 and pr['complete_phase_maximum_tree_nodes']==9666 and
                 pr['new_predicate_hard_budget']==12000000 and pr['maximum_uv_patch_count_per_face']<=1024 and
                 pr['maximum_boundary_piece_count_per_material']<=4096,'actual preflight/source/capacity qualification differs')
        if verifying:
            prior='single_trim_model_cell' if phase=='verify_single' else 'all_trim_model_frames';item=results[prior]
            need(contract['producer_report']==item['stage']['report'] and contract['producer_owned_supervision']==item['stage']['controller'] and
                 report['verified_producer_report']==contract['producer_report'] and contract['expected_phase']==prior,
                 'actual verifier not bound to exact completed producer')
            need(contract['verifier_sha256']==supervision['worker']['sha256'] and report['producer_code_imported'] is False and report['trim_producer_or_helper_imported'] is False,
                 'independent verifier identity/import scope differs')
            need(report['trim_source_bundle']==report['verified_trim_source_bundle']==contract['trim_source_bundle'] and
                 report['registered_trim_model_source_not_imported']==contract['trim_model_source'],'actual verifier model input/source binding differs')
        else:
            need(report['schema']=='razr-r5e-trim-model-conditioned-refinement-v5' and report['source_report_identity']==contract['r4_report'] and
                 report['public_input_bridge']==contract['public_input_bridge'] and report['trim_source_bundle']==contract['trim_source_bundle'] and
                 report['trim_model_source']==contract['trim_model_source'] and report['real_retained_cell_selection']==contract['real_retained_cell_selection'],
                 'actual producer report/input/model source binding differs')
            need(report['source_and_contract_unchanged'] and report['all_frame_capacity_observations_completed'] and len(report['base_channel_controls'])==5 and
                 all(x['passed'] is True for x in report['base_channel_controls']),'producer complete source/control record differs')
        rows.append({'label':label,'phase':phase,'all_owned_and_scientific_completed':True,'controller_seconds':controller['elapsed_seconds'],
            'worker_seconds':report['seconds'],'actual_peak_RSS_bytes':entry['peak_RSS_bytes'],'entry_receipt_identity':identity(ep),
            'contract_identity':stage['contract'],'supervision_contract_identity':stage['supervision_contract'],'report_identity':stage['report'],
            'controller_identity':stage['controller'],'recorded_resource_observations':observations,'recorded_live_memory_samples':live,
            'postexit_missing_memory_samples_not_zero_substituted':postexit,'handshake_initial_memory':initial,'final_resources':final,
            'actual_output_bytes':output_bytes,'resource_stop':None,'all_recorded_original_resource_gates_satisfied':True})
        results[phase]={'stage':stage,'contract':contract,'report':report,'controller':controller,'entry':entry}
    need(previous<=utc(pipeline['finished_utc']) and len(drivers)==1,'pipeline final/common owned driver identity differs')
    REPORT['actual_owned_stages']=rows;REPORT['unchanged_original_resource_gates']=LIMITS
    REPORT['resource_sample_scope']='Actual persisted samples, handshake memory and final entry peaks only. Admission-only subsecond stages do not gain invented live samples.'
    return results


def box_dimension(value,n):
    need(type(value) is list and len(value)==n and all(type(row) is list and len(row)==2 for row in value),'exact box dimension differs')
    result=tuple(tuple(Q(x) for x in row) for row in value)
    need(all(a<=b for a,b in result),'reversed exact source interval')
    return result


def location_identity(record):
    need([[Q(v) for v in row] for row in record['matrix_3x4_exact']]==
         [[Q(1),Q(0),Q(0),Q(0)],[Q(0),Q(1),Q(0),Q(0)],[Q(0),Q(0),Q(1),Q(0)]],
         'nonidentity source placement cannot be admitted')


def source_hole(wire, declared):
    need(wire['is_outer'] is False,'admitted loop is not an inner wire');location_identity(wire['location'])
    occurrences=wire['edge_occurrences'];need(len(occurrences)==4,'complete four-line source required')
    segments=[];constants=[[],[]]
    for occurrence in occurrences:
        location_identity(occurrence['location']);curve=occurrence['pcurve']
        need(curve['type']=='GeomAbs_CurveType.GeomAbs_Line','unsupported pcurve class admitted')
        origin=tuple(map(Q,curve['origin_exact']));direction=tuple(map(Q,curve['direction_exact']))
        need(len(origin)==2 and direction in ((Q(1),Q(0)),(Q(-1),Q(0)),(Q(0),Q(1)),(Q(0),Q(-1))),
             'pcurve is not a registered axis-unit line')
        first,last=Q(curve['first_parameter']['exact']),Q(curve['last_parameter']['exact'])
        need(first<last,'nonpositive original parameter span')
        ends=[tuple(origin[k]+direction[k]*t for k in range(2)) for t in (first,last)]
        need(occurrence['orientation'] in ('TopAbs_Orientation.TopAbs_FORWARD','TopAbs_Orientation.TopAbs_REVERSED'),'unsupported edge occurrence orientation')
        if occurrence['orientation'].endswith('REVERSED'):ends.reverse()
        segments.append(tuple(ends));constant_axis=0 if direction[0]==0 else 1
        constants[constant_axis].append(ends[0][constant_axis])
    need(all(len(v)==2 and len(set(v))==2 for v in constants),'two distinct actual side constants per axis required')
    (u0,u1),(v0,v1)=[sorted(v) for v in constants]
    corners=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)];arrows=[];offsets=[];radius=Q(0)
    for start,end in segments:
        axis=0 if start[0]==end[0] else 1
        side=[i for i,corner in enumerate(corners) if corner[axis]==start[axis]]
        need(len(side)==2,'actual segment does not lie on one ideal side')
        arrow=[];pairs=[]
        for endpoint in (start,end):
            choices=sorted((max(abs(endpoint[k]-corners[i][k]) for k in range(2)),i) for i in side)
            need(choices[0][0]<choices[1][0],'ambiguous true endpoint assignment')
            distance,index=choices[0];radius=max(radius,distance);arrow.append(index)
            pairs.append([str(endpoint[k]-corners[index][k]) for k in range(2)])
        need(arrow[0]!=arrow[1],'degenerate auxiliary side');arrows.append(arrow);offsets.append(pairs)
    need(sorted(a for a,b in arrows)==list(range(4)) and sorted(b for a,b in arrows)==list(range(4)), 'not one-in/one-out at all four corners')
    successor=dict(arrows);cycle=[0]
    for _ in range(4):cycle.append(successor[cycle[-1]])
    need(cycle[-1]==0 and len(set(cycle[:-1]))==4,'not a single four-cycle')
    twice_area=sum(corners[a][0]*corners[b][1]-corners[a][1]*corners[b][0] for a,b in arrows)
    need(abs(twice_area)==2*(u1-u0)*(v1-v0),'auxiliary winding not plus/minus one')
    need(4*radius<min(u1-u0,v1-v0),'corner squares can reach/opacify open core')
    core=((u0+radius,u1-radius),(v0+radius,v1-radius))
    expected={'wire_index':wire['index'],'oriented_segments_exact':[
        {'occurrence_index':i,'start_exact':[str(x) for x in start],'end_exact':[str(x) for x in end]}
        for i,(start,end) in enumerate(segments)],'ideal_rectangle_exact':exact_box_strings(((u0,u1),(v0,v1))),
        'directed_corner_indices':arrows,'uniform_corner_radius_exact':str(radius),
        'endpoint_corner_offsets_exact':offsets,
        'corner_squares_exact':[exact_box_strings(((u-radius,u+radius),(v-radius,v+radius))) for u,v in corners],
        'hole_core_exact':exact_box_strings(core),'cycle_corner_indices':cycle,
        'native_closure_class_membership_verified':False,'inner_wire_hole_semantics_verified_for_native':False,
        'original_pcurve_endpoints_replaced':False}
    for key,value in expected.items():need(declared[key]==value,'source-derived true hole certificate differs: '+key)
    return core,{'wire_index':wire['index'],'delta_exact':str(radius),'delta_approx':float(radius),
                 'exact_zero_endpoint_gap':radius==0,'conditional_model_only':True,'native_membership_unverified':True}


def plane_projection(face, stationary):
    location_identity(face['location']);plane=face['local_surface']
    need(plane['type']=='GeomAbs_SurfaceType.GeomAbs_Plane','unsupported nonplanar face admitted')
    origin,x,y=[tuple(map(Q,plane[key])) for key in ('origin_exact','X_exact','Y_exact')]
    need(len(origin)==len(x)==len(y)==3,'plane vector dimensions')
    matrices=[]
    for a,b in itertools.combinations(range(3),2):
        determinant=x[a]*y[b]-y[a]*x[b]
        if determinant:matrices.append(((a,b),((y[b]/determinant,-y[a]/determinant),(-x[b]/determinant,x[a]/determinant))))
    need(matrices,'rank-deficient affine plane');axes,inverse=matrices[0]
    shifted=[(stationary[k][0]-origin[k],stationary[k][1]-origin[k]) for k in axes]
    outer=[]
    for row in inverse:
        terms=[[c*v for v in interval] for c,interval in zip(row,shifted)]
        outer.append((sum(min(v) for v in terms),sum(max(v) for v in terms)))
    need(all(a<b for a,b in outer),'stationary full face projection not positive')
    return origin,x,y,axes,inverse,tuple(outer)


def uv_coverage_by_interval_union(outer, cores, patches):
    coordinates=[set(axis) for axis in outer]
    for core in cores:
        need(all(outer[k][0]<core[k][0]<core[k][1]<outer[k][1] for k in range(2)), 'admitted open core escapes projected old full face')
        for k in range(2):coordinates[k].update(core[k])
    for patch in patches:
        need(all(outer[k][0]<=patch[k][0]<=patch[k][1]<=outer[k][1] and set(patch[k])<=coordinates[k] for k in range(2)),
             'patch has unregistered endpoint or escapes original projected face')
    atoms=[]
    for axis in coordinates:
        ordered=sorted(axis);parts=[(v,v) for v in ordered]+list(zip(ordered,ordered[1:]));atoms.append(sorted(parts))
    required=0;dimensions=Counter();merge_count=0
    for u in atoms[0]:
        intervals=sorted(p[1] for p in patches if p[0][0]<=u[0]<=u[1]<=p[0][1])
        merged=[]
        for a,b in intervals:
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
            else:merged.append((a,b))
        merge_count+=len(merged)
        for v in atoms[1]:
            part=(u,v)
            removed=any(all(c[k][0]<a<c[k][1] if a==b else c[k][0]<=a<b<=c[k][1]
                            for k,(a,b) in enumerate(part)) for c in cores)
            carrier=any(all(c[k][0]<=a<=b<=c[k][1] for k,(a,b) in enumerate(part)) and
                        any(a==b and a in c[k] for k,(a,b) in enumerate(part)) for c in cores)
            if not removed or carrier:
                need(any(a<=v[0]<=v[1]<=b for a,b in merged),'required exact UV stratum lost from union of closed patches')
                required+=1;dimensions[sum(a<b for a,b in part)]+=1
    return {'exact_strata_checked':len(atoms[0])*len(atoms[1]),'required_strata_covered':required,
            'required_strata_by_dimension':{str(k):v for k,v in sorted(dimensions.items())},
            'U_strata_count':len(atoms[0]),'merged_closed_V_intervals':merge_count,
            'all_closed_core_edges_and_points_covered':True,'sampling_used':False}


def rebuild_boundary(proof, old, boundary, source_records, source_bindings):
    need(boundary['schema']=='razr-r5e-conditional-planar-trim-boundary-v5' and boundary['conditional_trim_model_only'] is True and
         boundary['native_trim_class_membership_verified'] is False and boundary['inner_wire_hole_semantics_verified_for_native'] is False,
         'boundary schema or conditional scope differs')
    key=(old['case_id'],old['frame']);binding=source_bindings[key]
    need(binding['original_R4_raw_proof_identity']==old['proof'] and binding['original_full_D']==proof['full_remaining_displacement_box_exact'],
         'lossless source frame/whole proof/fullD mapping differs')
    displacement=ranges(proof['full_remaining_displacement_box_exact']);cover=proof['complete_raw_boundary_slab_cover']
    need(len(boundary['sources'])==2,'missing complete material side')
    output=[];summary={'applied_faces':0,'hole_core_certificates_verified':0,'unapplied_faces_preserved':0,
        'original_edges_vertices_preserved':0,'exact_UV_strata_checked':0,'new_boundary_pieces':0,'face_reviews':[]}
    for side,declared in enumerate(boundary['sources']):
        material=tuple(binding['moving_and_fixed_material_keys'][side]);source=source_records[material]
        input_name=('moving_input','fixed_input')[side]
        need(source['input']==proof[input_name] and declared['material_key']==list(material),'whole material identity mismatch')
        original=cover[('first_complete_boundary_boxes','second_complete_boundary_boxes')[side]]
        whole_name=('first_whole_support_box_exact','second_whole_support_box_exact')[side]
        need(declared['original_complete_piece_count']==len(original) and declared['original_whole_support_box_exact']==cover[whole_name],
             'original complete boundary/whole support identity changed')
        identities=[(r['kind'],r['index']) for r in original]
        need(len(identities)==len(set(identities)),'duplicate original complete boundary identity')
        counts=Counter(r['kind'] for r in original)
        need(all(counts[kind]==source['original_complete_boundary_counts'][plural] for kind,plural in [('face','faces'),('edge','edges'),('vertex','vertices')]),
             'original complete boundary census differs')
        candidates={f['face_index']:f for f in source['candidate_faces']}
        certificates=declared['face_certificates'];need(len(certificates)==len(candidates),'candidate face lost/extra')
        seen=set();replacement={};cert_index={}
        for ci,face_certificate in enumerate(certificates):
            index=face_certificate['original_piece_index'];face_index=face_certificate['face_index']
            need(valid_index(index,len(original)) and face_index in candidates and face_index not in seen and index not in cert_index,
                 'invalid/duplicate face replacement mapping')
            seen.add(face_index);cert_index[index]=ci;candidate=candidates[face_index];face=candidate['complete_original_face']
            need(original[index]['kind']=='face' and original[index]['index']==face_index==face['index'] and
                 canonical(face)==candidate['complete_original_face_canonical_sha256']==face_certificate['source_face_canonical_sha256'],
                 'complete original face/material provenance differs')
            need(type(face_certificate['applied']) is bool,'face application status not explicit')
            if not face_certificate['applied']:
                need(isinstance(face_certificate['face_refinement_not_applied_reason'],str) and face_certificate['face_refinement_not_applied_reason'],
                     'whole-face fallback lacks reason')
                summary['unapplied_faces_preserved']+=1;continue
            need(face_certificate['original_pcurve_values_changed'] is False and face_certificate['closed_hole_core_boundaries_retained'] is True and
                 face_certificate['native_trim_class_membership_verified'] is False and face_certificate['inner_wire_hole_semantics_verified_for_native'] is False,
                 'applied face hides original endpoint change/native premise/core boundary loss')
            oldbox=ranges(original[index]['box_exact'])
            stationary=tuple((a-displacement[k][0],b-displacement[k][1]) if side==0 else (a,b) for k,(a,b) in enumerate(oldbox))
            need(all(a<=b for a,b in stationary),'completeD unexpansion is reversed')
            origin,x,y,axes,inverse,outer=plane_projection(face,stationary)
            need(face_certificate['stationary_original_boundary_box_exact']==exact_box_strings(stationary) and
                 face_certificate['projection_axes']==list(axes) and face_certificate['inverse_rows_exact']==[[str(v) for v in row] for row in inverse] and
                 face_certificate['uv_outer_box_exact']==exact_box_strings(outer),'independent stationary plane inverse differs')
            wires={w['index']:w for w in face['wires']};holes=face_certificate['holes']
            need([h['wire_index'] for h in holes]==candidate['candidate_inner_wire_indices'] and bool(holes),'candidate source hole coverage differs')
            cores=[];hole_details=[]
            for hole in holes:
                core,detail=source_hole(wires[hole['wire_index']],hole);cores.append(core);hole_details.append(detail)
            patches=[box_dimension(p,2) for p in face_certificate['uv_closed_patch_boxes_exact']]
            need(len(patches)<=1024,'patch capacity exceeded')
            uv_result=uv_coverage_by_interval_union(outer,cores,patches)
            retained=[];empty=[];stationary_boxes=[];swept=[]
            for ui,patch in enumerate(patches):
                box=[]
                for k in range(3):
                    terms=[[x[k]*v for v in patch[0]],[y[k]*v for v in patch[1]]]
                    box.append((max(stationary[k][0],origin[k]+sum(min(t) for t in terms)),
                                min(stationary[k][1],origin[k]+sum(max(t) for t in terms))))
                if any(a>b for a,b in box):empty.append(ui);continue
                box=tuple(box);retained.append(ui);stationary_boxes.append(box)
                swept.append(tuple((a+displacement[k][0],b+displacement[k][1]) if side==0 else (a,b) for k,(a,b) in enumerate(box)))
            need(bool(retained) and face_certificate['retained_uv_patch_indices']==retained and face_certificate['empty_uv_patch_indices']==empty,
                 'strict empty/closed zero-width patch partition differs')
            need(face_certificate['stationary_patch_boxes_exact']==[exact_box_strings(b) for b in stationary_boxes] and
                 face_certificate['swept_patch_boxes_exact']==[exact_box_strings(b) for b in swept],
                 'independent affine map/intersection/fullD sweep differs')
            replacement[index]=list(zip(retained,swept));summary['applied_faces']+=1
            summary['hole_core_certificates_verified']+=len(holes);summary['exact_UV_strata_checked']+=uv_result['exact_strata_checked']
            summary['face_reviews'].append({'material_side':side,'material_key':list(material),'face_index':face_index,
                'source_face_sha256':candidate['complete_original_face_canonical_sha256'],'hole_details':hole_details,
                'closed_UV_patch_count':len(patches),'strict_empty_patch_count':len(empty),'retained_patch_count':len(retained),
                'retained_zero_width_stationary_patch_count':sum(any(lo==hi for lo,hi in patch_box) for patch_box in stationary_boxes),
                'independent_U_stratum_closed_V_union_cover':uv_result})
        need(seen==set(candidates),'original candidate face missing')
        expected_rows=[];boxes=[]
        for index,piece in enumerate(original):
            common={'original_piece_index':index,'kind':piece['kind'],'index':piece['index']}
            if index in replacement:
                for ui,box in replacement[index]:
                    expected_rows.append(dict(common,replacement='trim_patch',face_certificate_index=cert_index[index],uv_patch_index=ui,box_exact=exact_box_strings(box)))
                    boxes.append(box)
            else:
                expected_rows.append(dict(common,replacement='unchanged',box_exact=piece['box_exact']));boxes.append(ranges(piece['box_exact']))
                summary['original_edges_vertices_preserved']+=int(piece['kind'] in ('edge','vertex'))
        need(declared['pieces']==expected_rows and 0<len(boxes)<=4096,'full original-piece replacement lineage differs')
        hull=tuple((min(p[k][0] for p in boxes),max(p[k][1] for p in boxes)) for k in range(3));old_hull=ranges(cover[whole_name])
        need(declared['whole_exact']==exact_box_strings(hull) and all(old_hull[k][0]<=hull[k][0]<=hull[k][1]<=old_hull[k][1] for k in range(3)),
             'independent complete boundary hull differs/escapes old support')
        output.append((boxes,hull));summary['new_boundary_pieces']+=len(boxes)
    need(boundary['applied_face_count']==summary['applied_faces'] and boundary['applied_inner_wire_count']==summary['hole_core_certificates_verified'] and
         boundary['retained_original_face_count_after_rejection']==summary['unapplied_faces_preserved'],'model complete-phase face/hole counts differ')
    return output,summary


CONTROL_NAMES={
 'phase':['missing-frame','duplicate-frame','incorrect-phase'],
 'root':['omitted-original-root','duplicate-original-root'],
 'leaf':['omitted-allocated-leaf-node','discarded-smallest-selected-tree-leaf-volume'],
 'channel':['omitted-complete-boundary-piece','overclaim-closed-cell-disjointness','channel-does-not-reach-known-exterior','false-separating-coordinate'],
 'split':['omitted-partition-child','duplicated-partition-child','cut-on-parent-boundary','discarded-closed-cut-plane','incorrect-positive-directed-volume'],
 'boundary':['expanded-actual-hole-core-endpoint','omitted-actual-closed-UV-patches','omitted-actual-original-edge-or-vertex','incorrect-actual-swept-patch-endpoint'],
}


def phase_complete(producer,phase):
    expected=[('case-001',1)] if phase=='single_trim_model_cell' else EXPECTED
    need(producer['phase']==phase and [(r['case_id'],r['frame']) for r in producer['frames']]==expected,
         'actual complete original case/frame coverage differs')


def roots_complete(frame,certificate,indices):
    need(frame['root_original_cell_indices']==indices and frame['root_count']==len(indices) and
         [r['original_cell_index'] for r in certificate['roots']]==indices,'complete original root coverage differs')


def independently_reject(phase,group,name,check,locator=None):
    global MUTATING
    old_mode=MUTATING;MUTATING=True;error=None
    try:
        try:check()
        except (ValueError,IndexError,KeyError,TypeError) as exc:error=str(exc)
        need(error is not None,'independent corrupt-copy mutation was accepted: '+name)
    finally:MUTATING=old_mode
    record={'phase':phase,'group':group,'name':name,'actual_rejected_by_local_audit':True,'reason':error,
            'scope':'independent audit copy mutation; separate from actual CI checker rejection'}
    if locator is not None:record['actual_original_object']=locator
    REPORT['independent_negative_controls'].append(record)


def rejection_records(rows,names):
    need([r['name'] for r in rows]==names and all(r['actual_rejected'] is True and isinstance(r['reason'],str) and r['reason'] for r in rows),
         'actual remote rejection controls incomplete/relabelled')


def checker_control_metadata(phase,checker,counts):
    for key,group in [('phase_negative_controls','phase'),('root_coverage_negative_controls','root'),('leaf_negative_controls','leaf')]:
        rejection_records(checker[key],CONTROL_NAMES[group])
    for group,key,count in [('channel','channel_negative_controls',counts['excluded']),('split','split_negative_controls',counts['splits'])]:
        rows=checker[key];app=checker['real_case_control_applicability'][group+'_mutations']
        need(app['actual_eligible_count']==count and app['analytic_controls_are_separate'] is True,'actual control object applicability count differs')
        if count:
            rejection_records(rows,CONTROL_NAMES[group]);need(app['status']=='executed' and app['reason'] is None,'applicable actual control not executed')
        else:
            need(rows==[] and app['status']=='not_applicable' and isinstance(app['reason'],str) and app['reason'],'fabricated missing actual control objects')
    app=checker['real_case_control_applicability']['leaf_mutations']
    need(app['status']=='executed' and app['actual_eligible_count']==counts['leaves'],'actual positive leaf controls mislabelled')
    boundary_rows=checker['boundary_refinement_negative_controls'];rejection_records(boundary_rows,CONTROL_NAMES['boundary'])
    need(all(r['status']=='executed' and r['original_inputs_modified'] is False for r in boundary_rows),'actual trim mutation scope differs')
    app=checker['real_case_control_applicability']['boundary_refinement_mutations']
    need(app['status']=='executed' and app['actual_applied_face_count']==counts['faces'] and app['actual_rejected_controls']==4,'real applied-face control count differs')
    analytic=checker['mandatory_analytic_controls']
    need(analytic['schema']=='razr-r5e-mandatory-analytic-checker-controls-v5' and analytic['execution_kind']=='synthetic_analytic_control' and
         analytic['qualifies_original_or_trim_model_case'] is False and analytic['real_case_result_changed'] is False and
         analytic['mandatory_controls_completed'] is True,'analytic controls relabelled as real-case qualification')
    for key,group in [('channel_negative_controls','channel'),('split_negative_controls','split'),('leaf_negative_controls','leaf')]:rejection_records(analytic[key],CONTROL_NAMES[group])
    tiny=Q(CAPACITY['tiny_retained_volume_exact']);delta=tiny/2;point=Q(2)+delta
    unit=((Q(0),Q(1)),)*3;second=((point,Q(4)),(Q(0),Q(1)),(Q(0),Q(1)))
    need(analytic['source_closed_boxes_exact']==[exact_box_strings(unit),exact_box_strings(second)] and analytic['source_complete_face_counts']==[6,6],
         'actual analytic closed-box sources differ')
    first=analytic['complete_box_positive'];target=((Q(2),Q(3)),(Q(0),Q(1)),(Q(0),Q(1)))
    need(first=={'verified':True,'root_box_exact':exact_box_strings(target),'positive_volume_exact':'1','excluded_open_volume_exact':'1','complete_boundary_pieces_verified':6},
         'actual synthetic positive complete box result differs')
    faces=[]
    for axis,end in itertools.product(range(3),range(2)):
        face=list(unit);face[axis]=(unit[axis][end],)*2;faces.append(tuple(face))
    need(len(faces)==6 and measure(target)==1 and all(face[0][1]<=target[0][0] for face in faces),
         'independent analytic closed-box exterior algebra failed')
    split=analytic['exact_split_positive']
    need(split['verified'] is True and Q(split['split_exact'])==point and list(map(Q,split['positive_child_volumes_exact']))==[delta,1-delta] and
         split['tiny_leaf_retained_in_full'] is True and Q(split['retained_sum_exact'])==delta>0 and
         split['all_closed_carriers_retained'] is True and delta+(1-delta)==1,'actual analytic exact tiny partition differs')
    for r in analytic['leaf_negative_controls']:
        need(r['original_leaf_id']==1 and r['original_leaf_kind']=='retained' and r['original_leaf_reason']=='tiny_exact_volume_retained' and
             Q(r['original_positive_volume_exact'])==delta,'synthetic tiny leaf incorrectly substituted for real leaf control')
    names=['phase_negative_controls','root_coverage_negative_controls','leaf_negative_controls','channel_negative_controls','split_negative_controls','boundary_refinement_negative_controls']
    return {'phase':phase,'actual_case_rejections':sum(len(checker[k]) for k in names),'actual_synthetic_rejections':11,
        'actual_synthetic_positive_cases':2,'actual_case_control_groups':{k:checker[k] for k in names},
        'actual_case_applicability':checker['real_case_control_applicability'],
        'actual_synthetic_control_record':analytic,'synthetic_positive_algebra_independently_read_back':True,
        'local_synthetic_negative_mutations_reexecuted':False,'old_V4_twelve_rejections_counted_here':False}


def copied_header_controls(producer,phase,frame,certificate,indices):
    for name,change in [('missing-frame',dict(producer,frames=producer['frames'][:-1])),
                        ('duplicate-frame',dict(producer,frames=producer['frames']+[producer['frames'][0]])),
                        ('incorrect-phase',dict(producer,phase='preflight_trim_model'))]:
        independently_reject(phase,'phase',name,lambda change=change:phase_complete(change,phase))
    for name,roots in [('omitted-original-root',certificate['roots'][:-1]),('duplicate-original-root',certificate['roots']+[certificate['roots'][0]])]:
        independently_reject(phase,'root',name,lambda roots=roots:roots_complete(frame,dict(certificate,roots=roots),indices))


def copied_leaf_controls(phase,tree,root,sources,stats,remote_rows,locator):
    smallest=min(stats['leaves'],key=lambda r:Q(r['positive_directed_volume_exact']));index=smallest['node_id']
    for row in remote_rows:
        need(row['original_leaf_id']==index and row['original_leaf_kind']==smallest['kind'] and row['original_leaf_reason']==smallest.get('reason') and
             Q(row['original_positive_volume_exact'])==Q(smallest['positive_directed_volume_exact']), 'actual CI leaf mutation does not match actual first selected tree')
    changes=[('omitted-allocated-leaf-node',lambda t:t['nodes'].pop(index)),
             ('discarded-smallest-selected-tree-leaf-volume',lambda t:t['nodes'][index].update(positive_directed_volume_exact='0'))]
    for name,edit in changes:
        changed=copy.deepcopy(tree);edit(changed)
        independently_reject(phase,'leaf',name,lambda changed=changed:tree_readback(changed,root,sources),
                             dict(locator,node_id=index,kind=smallest['kind'],reason=smallest.get('reason'),volume_exact=smallest['positive_directed_volume_exact']))


def copied_split_controls(phase,tree,root,sources,stats,locator):
    first=stats['splits'][0];index=first['node_id'];parent=ranges(first['parent_box_exact'])
    changes=[('omitted-partition-child',lambda t:t['nodes'][index].update(children=t['nodes'][index]['children'][:1])),
             ('duplicated-partition-child',lambda t:t['nodes'][index].update(children=[t['nodes'][index]['children'][0]]*2)),
             ('cut-on-parent-boundary',lambda t:t['nodes'][index].update(cut_exact=str(parent[t['nodes'][index]['axis']][0]))),
             ('discarded-closed-cut-plane',lambda t:t['nodes'][index].update(closed_cut_plane_retained_as_zero_volume_carrier=False)),
             ('incorrect-positive-directed-volume',lambda t:t['nodes'][index].update(parent_positive_directed_volume_exact='0'))]
    for name,edit in changes:
        changed=copy.deepcopy(tree);edit(changed)
        independently_reject(phase,'split',name,lambda changed=changed:tree_readback(changed,root,sources),dict(locator,node_id=index))


def copied_channel_controls(phase,tree,sources,stats,locator):
    leaf=next(row for row in stats['leaves'] if row['kind']=='excluded')
    index=leaf['node_id'];target=ranges(leaf['box_exact']);certificate=tree['nodes'][index]['certificate']
    for name in CONTROL_NAMES['channel']:
        changed=copy.deepcopy(certificate)
        if name=='omitted-complete-boundary-piece':changed['complete_piece_separation_codes']=changed['complete_piece_separation_codes'][:-1]
        elif name=='overclaim-closed-cell-disjointness':changed['whole_closed_cell_disjoint_claimed']=True
        elif name=='channel-does-not-reach-known-exterior':changed['open_channel_exact'][changed['axis']]=exact_box_strings(target)[changed['axis']]
        else:
            codes=changed['complete_piece_separation_codes'];changed['complete_piece_separation_codes']=str(int(codes[0])^1)+codes[1:]
        independently_reject(phase,'channel',name,lambda changed=changed:check_excluded(changed,target,sources),dict(locator,node_id=index))


def copied_boundary_controls(phase,proof,old,boundary,records,bindings,remote_rows):
    original_hash=canonical(boundary)
    for row in remote_rows:
        need(row['original_case_id']==old['case_id'] and row['original_frame']==old['frame'] and row['status']=='executed' and row['actual_rejected'] is True,
             'actual remote trim control points to a different case/frame')
        locator=row['actual_certificate_locator'];side=locator['material_side'];changed=copy.deepcopy(boundary);name=row['name']
        if name=='expanded-actual-hole-core-endpoint':
            hole=changed['sources'][side]['face_certificates'][locator['face_certificate_index']]['holes'][locator['hole_index']]
            hole['hole_core_exact'][0][0]=str(Q(hole['hole_core_exact'][0][0])-1)
        elif name=='omitted-actual-closed-UV-patches':
            changed['sources'][side]['face_certificates'][locator['face_certificate_index']]['uv_closed_patch_boxes_exact']=[]
        elif name=='omitted-actual-original-edge-or-vertex':
            piece=changed['sources'][side]['pieces'][locator['piece_index']]
            need(piece['kind']==locator['kind'] and piece['kind'] in ('edge','vertex') and piece['replacement']=='unchanged','actual trim control target is not a preserved source edge/vertex')
            changed['sources'][side]['pieces'].pop(locator['piece_index'])
        else:
            need(name=='incorrect-actual-swept-patch-endpoint','unknown actual trim mutation')
            patch=changed['sources'][side]['face_certificates'][locator['face_certificate_index']]['swept_patch_boxes_exact'][locator['retained_patch_list_index']]
            axis=locator['axis'];d=ranges(proof['full_remaining_displacement_box_exact']);step=d[axis][1]-d[axis][0] if side==0 else Q(0)
            patch[axis][1]=str(Q(patch[axis][1])-(step if step>0 else Q(1)))
        independently_reject(phase,'boundary',name,lambda changed=changed:rebuild_boundary(proof,old,changed,records,bindings),
                             dict(locator,case_id=old['case_id'],frame=old['frame']))
    need(canonical(boundary)==original_hash,'independent copied-control audit mutated actual certificate input')


def registered_original_sources(results):
    source_review=BASE/'r5-integration/independent-trim-v5-preexecution-review/R5_V5_INDEPENDENT_SOURCE_PROJECTION_AUDIT.json'
    need(identity(source_review)=={'bytes':40701,'sha256':'f2a68e29cff6bd5972adac5ad3ccdddf265b8c56d774a512f08058b7cbf286a4'},
         'prior independent lossless source-projection audit differs')
    audit=read_json(source_review);need(audit['audit_completed'] is True and audit['source_projection_only'] is True and
         audit['new_mathematical_qualification'] is False and audit['new_native_operations']==0,'prior source-only review scope differs')
    baseline=read_json(R4/'support-v4/report.json')
    need(baseline['execution_completed'] is True and [(r['case_id'],r['frame']) for r in baseline['frames']]==EXPECTED,
         'original complete16 report differs')
    path=bound(results['single_trim_model_cell']['contract']['trim_source_bundle'])
    bundle=decoded_gzip(path,1048576,'bundle')
    need(bundle['schema']=='razr-r5e-original-planar-trim-source-projection-v5' and bundle['original_public_R4_report_identity']==identity(R4/'support-v4/report.json'),
         'source projection original public report differs')
    need(dict(bundle['original_native_inventory_identity'],path=bundle['original_native_inventory_relative_path']) in baseline['input_identities'],
         'source original native inventory not anchored to old public report')
    need(bundle['new_native_operations']==0 and bundle['new_mathematical_qualification'] is False and bundle['original_pcurve_values_changed'] is False and
         bundle['native_trim_class_membership_verified'] is False,'projection silently becomes geometry qualification')
    records={};faces=wires=0
    for record in bundle['records']:
        key=(record['input']['case_id'],record['input']['material_id']);need(key not in records,'duplicate whole source material')
        need(record['full_original_face_records_unchanged'] is True,'changed original face record')
        for candidate in record['candidate_faces']:
            need(candidate['complete_original_face']['index']==candidate['face_index'] and canonical(candidate['complete_original_face'])==candidate['complete_original_face_canonical_sha256'],
                 'projected full face identity differs')
            faces+=1;wires+=len(candidate['candidate_inner_wire_indices'])
        records[key]=record
    bindings={(r['case_id'],r['frame']):r for r in bundle['frame_bindings']}
    need(len(records)==32 and len(bindings)==len(bundle['frame_bindings'])==16 and list(bindings)==EXPECTED and faces==40 and wires==80,
         'complete original32/16/40/80 source census differs')
    need({tuple(key) for item in bindings.values() for key in item['moving_and_fixed_material_keys']}==set(records),'orphan or missing whole material source')
    selection=read_json(bound(results['single_trim_model_cell']['contract']['real_retained_cell_selection']))
    v3=BASE/'r5-ci-results/run-40641230212'
    for field,path in [('source_pipeline',v3/'pipeline.json'),('source_all_raw_report',v3/'all-raw/report.json'),('source_independent_all_report',v3/'verify-all/report.json')]:
        need(identity(path)==selection[field],'selected real cell historical actual V3 identity differs')
    path=v3/selection['source_certificate']['relative_path']
    need(identity(path)=={k:selection['source_certificate'][k] for k in ('bytes','sha256')},'actual selected V3 certificate differs')
    certificate=decoded_gzip(path,4194304,'legacy')
    need(selection['source_run_id']==40641230212 and selection['source_commit']=='41333a369cbc44aab6fb5a723b75833a693ac16c' and
         (selection['case_id'],selection['frame'],selection['original_raw_cell_index'])==('case-001',1,202) and
         certificate['cells'][202]==selection['actual_V3_cell'] and selection['actual_V3_cell']['excluded_open_interior'] is False,
         'single is not the registered actual V3 retained cell')
    REPORT['lossless_original_source_reuse']={'prior_source_only_audit':identity(source_review),'trim_source_bundle':identity(R5/'R5E_V5_PLANAR_TRIM_SOURCE.json.gz'),
        'native_inventory_identity':bundle['original_native_inventory_identity'],'native_inventory_redecoded':False,
        'whole_material_records':32,'source_frame_bindings':16,'candidate_complete_faces':40,'candidate_original_inner_wires':80,
        'old_V3_real_selection_rebound':True,'old_V3_run_id':40641230212,'selected_original_cell_index':202,
        'source_projection_does_not_prove_native_membership':True}
    return baseline,records,bindings,selection


def new_phase_context(results,phase):
    producer=results[phase]['report'];checker_phase='verify_single' if phase=='single_trim_model_cell' else 'verify_all'
    checker=results[checker_phase]['report'];contract=results[checker_phase]['contract']
    phase_complete(producer,phase)
    expected=[['case-001',1]] if phase=='single_trim_model_cell' else [list(k) for k in EXPECTED]
    need(contract['expected_case_frames']==expected==checker['expected_case_frames'] and checker['expected_phase']==phase,
         'actual verifier expected complete case/frame differs')
    need([(r['case_id'],r['frame']) for r in checker['frames']]==[tuple(k) for k in expected],'actual verified frame list differs')
    need(producer['capacity']==CAPACITY and producer['original_TOL_exact']==str(Q(1e-7)) and producer['no_positive_thin_leaf_discarded'] is True,
         'producer original threshold/capacity/positive leaf scope differs')
    sums=dict(roots=0,nodes=0,splits=0,leaves=0,excluded=0,faces=0,holes=0,fallback=0,checked=0)
    return {'phase':phase,'producer':producer,'checker':checker,'controlled':set(),'sums':sums,'rows':[],
            'max_pieces':0,'max_piece_sum':0,'max_uv':0,'max_chars':0,'input_bytes':0,'static_upper':0,
            'retained_reasons':Counter(),'tiny_volume':Q(0),'original_cells_volume':Q(0)}


def read_frame(context,old,proof,records,bindings,selection,preflight_frame):
    phase=context['phase'];producer=context['producer'];checker=context['checker'];key=(old['case_id'],old['frame'])
    row=next(r for r in producer['frames'] if (r['case_id'],r['frame'])==key)
    checked_row=next(r for r in checker['frames'] if (r['case_id'],r['frame'])==key)
    conditional(row)
    need(row['original_raw_proof_identity']==old['proof'] and row['original_remaining_displacement_box_exact']==old['full_remaining_displacement_box_exact']==proof['full_remaining_displacement_box_exact'],
         'actual original proof/fullD changed')
    need(row['trim_source_bundle']==producer['trim_source_bundle'],'frame model source bundle differs')
    certificate=decoded_gzip(bound(row['certificate'],ACTUAL/('single-trim-model-cell' if phase=='single_trim_model_cell' else 'all-trim-model-frames')),67108864,'certificate')
    need(certificate['schema']=='razr-r5e-trim-model-conditioned-tree-v5' and certificate['frame']=={k:v for k,v in row.items() if k!='certificate'},
         'certificate schema/complete frame header differs from report')
    sources,boundary_audit=rebuild_boundary(proof,old,certificate['boundary_refinement'],records,bindings)
    for field in ('original_edges_vertices_preserved','applied_faces','unapplied_faces_preserved','hole_core_certificates_verified','exact_UV_strata_checked','new_boundary_pieces'):
        need(checked_row['independent_boundary_refinement'][field]==boundary_audit[field],'independent boundary count differs from actual checker: '+field)
    need(row['source_piece_counts']==[len(source[0]) for source in sources] and
         row['model_boundary_applied_face_count']==boundary_audit['applied_faces'] and
         row['model_boundary_applied_inner_wire_count']==boundary_audit['hole_core_certificates_verified'] and
         row['model_boundary_retained_original_face_count_after_rejection']==boundary_audit['unapplied_faces_preserved'],
         'actual per-frame model boundary metadata differs')
    cells=proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
    need(row['original_raw_cell_count']==len(cells),'reported original cell census differs')
    indices=[202] if phase=='single_trim_model_cell' else list(range(len(cells)))
    roots_complete(row,certificate,indices)
    if phase=='single_trim_model_cell':
        need(selection['original_R4_raw_proof_identity']==old['proof'] and selection['source_row_original_D']==proof['full_remaining_displacement_box_exact'] and
             selection['actual_V3_cell']['box_exact']==cells[202]['box_exact'] and
             Q(selection['actual_V3_cell']['positive_directed_volume_exact'])==Q(cells[202]['positive_directed_volume_exact']),
             'selected actual old V3 cell/root/fullD differs')
    if 'header' not in context['controlled']:
        copied_header_controls(producer,phase,row,certificate,indices);context['controlled'].add('header')
    if boundary_audit['applied_faces'] and 'boundary' not in context['controlled']:
        copied_boundary_controls(phase,proof,old,certificate['boundary_refinement'],records,bindings,checker['boundary_refinement_negative_controls'])
        context['controlled'].add('boundary')
    before_inequalities=COUNTS['excluded_cell_separation_inequalities'];before_blockers=COUNTS['blocked_direction_checks']
    retained=Q(0);removed=Q(0);nodes=splits=leaves=excluded=0;depth=0;tiny=Q(0);reasons=Counter();largest=[]
    for root_record,index in zip(certificate['roots'],indices):
        cell=cells[index];root=ranges(cell['box_exact'])
        need(root_record['root_box_exact']==cell['box_exact'] and Q(root_record['root_directed_volume_exact'])==Q(cell['positive_directed_volume_exact'])==measure(root),
             'original positive root box/volume differs')
        tree=root_record['tree'];stats=tree_readback(tree,root,sources)
        retained+=Q(stats['retained_sum_exact']);removed+=Q(stats['excluded_open_sum_exact'])
        nodes+=stats['node_count'];splits+=stats['split_count'];leaves+=stats['leaf_count'];excluded+=stats['excluded_leaf_count'];depth=max(depth,stats['maximum_depth'])
        reasons.update(stats['retention_reasons'])
        locator={'case_id':key[0],'frame':key[1],'original_root_index':index}
        if 'leaf' not in context['controlled']:
            copied_leaf_controls(phase,tree,root,sources,stats,checker['leaf_negative_controls'],locator);context['controlled'].add('leaf')
        if stats['split_count'] and 'split' not in context['controlled']:
            copied_split_controls(phase,tree,root,sources,stats,locator);context['controlled'].add('split')
        if stats['excluded_leaf_count'] and 'channel' not in context['controlled']:
            copied_channel_controls(phase,tree,sources,stats,locator);context['controlled'].add('channel')
        for leaf in stats['leaves']:
            if leaf['kind']=='retained':
                if leaf['reason']=='tiny_exact_volume_retained':tiny+=Q(leaf['positive_directed_volume_exact'])
                largest.append(dict(leaf,original_root_index=index));largest=sorted(largest,key=lambda r:Q(r['positive_directed_volume_exact']),reverse=True)[:3]
    need(retained==Q(row['retained_leaf_sum_exact']) and removed==Q(row['excluded_open_leaf_sum_exact']) and retained+removed==Q(row['original_root_sum_exact']),
         'actual original root directed sums differ')
    need(row['all_closed_cut_planes_and_original_cell_boundaries_retained'] is True and row['exact_splits_this_frame']==splits and
         row['total_leaf_count']==leaves and row['maximum_depth_reached']==depth,'actual tree metadata/carriers differ')
    selected=retained
    if phase=='all_trim_model_frames':
        need(retained+removed==Q(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']), 'complete original positive root sum changed')
        selected=min(retained,Q(old['coarse_whole_support_upper_exact_mm3']))
        need(selected<=Q(old['conditional_complete_material_intersection_upper_exact_mm3']) and old['original_min_volume_plus_TOL_gate_passed'] is True,
             'conditional refined upper exceeds old bound/inherited sanity premise absent')
    passed=selected<=Q(1e-7)
    need(row['original_R4_min_volume_plus_TOL_gate_passed']==old['original_min_volume_plus_TOL_gate_passed'] and
         Q(row['trim_model_conditional_upper_exact_mm3'])==selected and row['trim_model_conditional_upper_mm3']==float(selected) and
         row['trim_model_conditional_clearance_gate_passed'] is passed,'actual conditional bound/pass does not follow exact original threshold')
    checks={'original_roots_verified':len(indices),'exact_tree_nodes_verified':nodes,'exact_splits_verified':splits,
        'all_retained_and_excluded_leaves_verified':leaves,'actual_excluded_leaf_count':excluded,
        'complete_boundary_piece_separations_checked':COUNTS['excluded_cell_separation_inequalities']-before_inequalities,
        'trim_model_conditional_upper_exact_mm3':str(selected),'trim_model_conditional_clearance_gate_passed':passed,
        'original_R4_raw_clearance_gate_passed_unchanged':old['original_clearance_gate_passed'],'original_raw_gate_reclassified':False,
        'native_trim_class_membership_verified':False,'conditional_trim_model_only':True}
    for field,value in checks.items():need(checked_row[field]==value,'cross-author exact result differs from actual CI checker: '+field)
    need(checks['complete_boundary_piece_separations_checked']<=row['exact_boundary_box_tests_this_frame'], 'declared search predicates below independently checked successful inequalities')
    sums=context['sums']
    for field,value in [('roots',len(indices)),('nodes',nodes),('splits',splits),('leaves',leaves),('excluded',excluded),
                        ('faces',boundary_audit['applied_faces']),('holes',boundary_audit['hole_core_certificates_verified']),
                        ('fallback',boundary_audit['unapplied_faces_preserved']),('checked',checks['complete_boundary_piece_separations_checked'])]:sums[field]+=value
    context['max_pieces']=max(context['max_pieces'],*(len(s[0]) for s in sources));piece_sum=sum(len(s[0]) for s in sources)
    context['max_piece_sum']=max(context['max_piece_sum'],piece_sum)
    context['max_uv']=max(context['max_uv'],*(f['closed_UV_patch_count'] for f in boundary_audit['face_reviews']),0)
    for material,_ in sources:
        for box in material:
            for axis in box:context['max_chars']=max(context['max_chars'],*(len(str(v)) for v in axis))
    context['input_bytes']+=row['source_proof']['bytes'];context['static_upper']+=6*piece_sum*len(indices)
    context['retained_reasons'].update(reasons);context['tiny_volume']+=tiny;context['original_cells_volume']+=retained+removed
    result={'phase':phase,'case_id':key[0],'frame':key[1],'pair':row['pair'],'source_proof_identity':row['source_proof'],
        'certificate_identity':row['certificate'],'original_full_D_exact':proof['full_remaining_displacement_box_exact'],
        'source_piece_counts':[len(s[0]) for s in sources],'original_root_count':len(indices),'exact_tree_nodes':nodes,
        'exact_splits':splits,'all_positive_leaves':leaves,'excluded_open_leaves':excluded,'retained_positive_leaves':leaves-excluded,
        'retained_volume_exact':str(retained),'excluded_open_volume_exact':str(removed),'original_root_volume_exact':str(retained+removed),
        'tiny_retained_volume_exact':str(tiny),'tiny_retained_volume_approx_mm3':float(tiny),'retention_reasons':dict(reasons),
        'largest_unresolved_positive_leaves':largest,'exact_upper_mm3':str(selected),'upper_approx_mm3':float(selected),
        'conditional_model_clearance_passed':passed,'unchanged_original_raw_clearance_passed':old['original_clearance_gate_passed'],
        'complete_boundary_separation_inequalities_verified':checks['complete_boundary_piece_separations_checked'],
        'blocked_directions_verified':COUNTS['blocked_direction_checks']-before_blockers,
        'closed_root_and_cut_carriers_preserved':True,'complete_conditional_boundary_reconstruction':boundary_audit,
        'native_membership_or_hole_semantics_verified':False}
    context['rows'].append(result);REPORT['frames'].append(result)
    if phase=='all_trim_model_frames':
        need(preflight_frame['case_id']==key[0] and preflight_frame['frame']==key[1] and preflight_frame['new_clearance_result_claimed'] is False,
             'actual preflight frame/scope differs')
        for field in ('source_proof','original_raw_proof_identity','original_remaining_displacement_box_exact','source_piece_counts','original_raw_cell_count','root_original_cell_indices','root_count',
                      'trim_source_bundle','model_boundary_applied_face_count','model_boundary_applied_inner_wire_count','model_boundary_retained_original_face_count_after_rejection'):
            need(preflight_frame[field]==row[field],'actual preflight/full frame inputs or counts differ: '+field)
        expected_statuses=[{'material_key':s['material_key'],'faces':[{'face_index':f['face_index'],'applied':f['applied'],
            'retained_original_reason':f.get('face_refinement_not_applied_reason'),'admitted_inner_wires':len(f.get('holes',[])),
            'closed_uv_patch_count':len(f.get('uv_closed_patch_boxes_exact',[]))} for f in s['face_certificates']]} for s in certificate['boundary_refinement']['sources']]
        need(preflight_frame['model_boundary_face_statuses']==expected_statuses and preflight_frame['registered_model_coordinate_endpoint_counts']==
             [len({v for material,_ in sources for p in material for v in p[k]}) for k in range(3)],'actual measured preflight face/endpoint census differs')
    return result


def finish_phase(context):
    phase=context['phase'];producer=context['producer'];checker=context['checker'];sums=context['sums']
    need(sums['splits']==producer['counters']['splits']<=4096 and sums['nodes']==producer['counters']['tree_nodes_visited'] and
         producer['counters']['boundary_box_tests']<=12000000,'actual complete-phase tree/predicate budget count differs')
    for field,key in [('total_original_roots','roots'),('applied_face_occurrences_across_frames','faces'),
                      ('applied_inner_wire_occurrences_across_frames','holes'),('retained_original_face_occurrences_after_rejection','fallback')]:
        need(producer[field]==sums[key],'actual producer global count differs: '+field)
    values={'maximum_complete_piece_count_sum':context['max_piece_sum'],'maximum_exact_coordinate_character_count':context['max_chars'],
        'total_compressed_original_input_bytes':context['input_bytes'],'model_root_channel_static_predicate_upper':context['static_upper'],
        'maximum_uv_patch_count_per_face':context['max_uv'],'maximum_boundary_piece_count_per_material':context['max_pieces'],
        'complete_phase_maximum_tree_nodes':sums['roots']+8192,'complete_phase_maximum_leaves':sums['roots']+4096}
    for field,value in values.items():need(producer[field]==value,'actual producer measured/combinatorial capacity differs: '+field)
    for field,key in [('total_tree_nodes_verified','nodes'),('total_splits_verified','splits'),('total_leaves_verified','leaves'),
                      ('total_actual_excluded_leaves_verified','excluded'),('applied_face_occurrences_verified','faces'),
                      ('applied_inner_wire_occurrences_verified','holes'),('retained_original_face_occurrences_after_rejection_verified','fallback')]:
        need(checker[field]==sums[key],'actual independent complete-phase count differs: '+field)
    passes=sum(r['conditional_model_clearance_passed'] for r in context['rows'])
    need(passes==producer['trim_model_conditional_clearance_passes']==checker['trim_model_conditional_clearance_passes'],'actual pass count differs from independent reconstruction')
    control_record=checker_control_metadata(phase,checker,sums)
    actual_local=[r for r in REPORT['independent_negative_controls'] if r['phase']==phase]
    expected_groups={'phase':3,'root':2,'leaf':2,'channel':4 if sums['excluded'] else 0,'split':5 if sums['splits'] else 0,'boundary':4 if sums['faces'] else 0}
    need(Counter(r['group'] for r in actual_local)==Counter({k:v for k,v in expected_groups.items() if v}), 'bounded independent copied-control set incomplete')
    return {'phase':phase,'actual_and_rebuilt_counts':sums,'conditional_model_clearance_passes':passes,
        'actual_producer_search_counters_not_replayed':producer['counters'],'retention_reason_counts':dict(context['retained_reasons']),
        'all_tiny_positive_volume_retained_exact':str(context['tiny_volume']),'all_tiny_positive_volume_retained_approx_mm3':float(context['tiny_volume']),
        'independently_rebuilt_capacity_observations':values,'actual_remote_control_readback':control_record,
        'separate_local_copied_control_rejections':len(actual_local),'original_raw_gates_reclassified':False,
        'native_class_membership_verified':False}


def exact_all_frames(results,bridge):
    baseline,records,bindings,selection=registered_original_sources(results)
    contexts={phase:new_phase_context(results,phase) for phase in ('single_trim_model_cell','all_trim_model_frames')}
    full=contexts['all_trim_model_frames'];preflight=results['preflight_trim_model']['report']
    need([(r['case_id'],r['frame']) for r in preflight['frames']]==EXPECTED and
         all(v==0 for v in preflight['counters'].values()) and preflight['trim_model_conditional_clearance_passes']==0,
         'preflight claims new clearance/search or incomplete frames')
    for old in baseline['frames']:
        key=(old['case_id'],old['frame']);entry=bridge['support-v4/'+old['proof']['path']]
        need(entry['raw_identity']=={k:old['proof'][k] for k in ('bytes','sha256')},'original raw/public proof bridge differs')
        path=R4/'support-v4'/old['proof']['path'];need(identity(path)==entry['public_identity'],'original public proof identity differs')
        proof=decoded_gzip(path,33554432,'source')
        need(canonical(proof)==entry['public_canonical_json_sha256'] and (proof['case_id'],proof['frame'])==key and
             proof['full_remaining_displacement_box_exact']==old['full_remaining_displacement_box_exact'],'original decoded proof/header/fullD differs')
        need(len(proof['complete_raw_boundary_slab_cover']['combined']['positive_cells'])==old['boundary_slab_positive_cell_count'],
             'complete original cell count differs')
        pre=next(r for r in preflight['frames'] if (r['case_id'],r['frame'])==key)
        for context in contexts.values():
            for actual_row in context['producer']['frames']:
                if (actual_row['case_id'],actual_row['frame'])==key:
                    wanted=dict(entry['public_identity'],path=REMOTE_R4+'/support-v4/'+old['proof']['path'])
                    need(actual_row['source_proof']==wanted,'actual report public source identity/path differs')
                    bound(actual_row['source_proof'])
        if key==('case-001',1):read_frame(contexts['single_trim_model_cell'],old,proof,records,bindings,selection,None)
        read_frame(full,old,proof,records,bindings,selection,pre)
        del proof;gc.collect()
    REPORT['phases']=[finish_phase(contexts[phase]) for phase in ('single_trim_model_cell','all_trim_model_frames')]
    need(full['sums']['roots']==1474 and len(full['rows'])==16,'original complete16/1474 coverage differs')
    for field,value in REPORT['phases'][1]['independently_rebuilt_capacity_observations'].items():
        need(preflight[field]==value,'actual preflight capacity disagrees with independently rebuilt full source: '+field)
    need(preflight['total_original_roots']==1474 and preflight['applied_face_occurrences_across_frames']==full['sums']['faces'] and
         preflight['applied_inner_wire_occurrences_across_frames']==full['sums']['holes'] and
         preflight['retained_original_face_occurrences_after_rejection']==full['sums']['fallback'],'preflight source face/hole totals differ')
    REPORT['actual_conditional_model_passes']=REPORT['phases'][1]['conditional_model_clearance_passes']
    REPORT['actual_conditional_model_frame_count']=16
    REPORT['conditional_model_unresolved_frames']=[{'case_id':r['case_id'],'frame':r['frame'],'pair':r['pair'],
        'upper_exact_mm3':r['exact_upper_mm3'],'upper_approx_mm3':r['upper_approx_mm3'],'material_interference_claimed':False}
        for r in full['rows'] if not r['conditional_model_clearance_passed']]
    REPORT['new_conditional_model_pass_frames']=[{'case_id':r['case_id'],'frame':r['frame'],'upper_exact_mm3':r['exact_upper_mm3']}
        for r in full['rows'] if r['conditional_model_clearance_passed'] and not r['unchanged_original_raw_clearance_passed']]


def main():
    started=time.monotonic();registration=read_json(REGISTRATION)
    resource.setrlimit(resource.RLIMIT_AS,(402653184,402653184));resource.setrlimit(resource.RLIMIT_CPU,(240,240))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('registered 240-second independent readback budget exceeded')))
    signal.alarm(240)
    try:
        need(identity(__file__)==registration['audit_source_identity'] and identity(ARCHIVE)==registration['actual_archive_identity'], 'final audit source/archive not registered before execution')
        need(registration['wall_seconds']==240 and registration['RSS_limit_bytes']==402653184 and registration['address_space_limit_bytes']==402653184,
             'pre-registered independent readback budget changed')
        REPORT['audit_source_identity']=identity(__file__);REPORT['budget_registration_identity']=identity(REGISTRATION)
        pipeline,bridge=archive_and_source_chain();results=owned_stages(pipeline)
        exact_all_frames(results,bridge)
        need(pipeline['trim_model_conditional_clearance_passes']==pipeline['independent_trim_model_conditional_clearance_passes']==REPORT['actual_conditional_model_passes'] and
             pipeline['actual_frame_count']==16,'actual driver final result differs from exact reconstruction')
        need(pipeline['unchanged_process_limits']==LIMITS,'actual pipeline original gate values differ')
        log=BASE/'r5-integration/R5_V5_CI_JOB_122674800673.log';logtext=log.read_text()
        for item in (HEAD,LOCK_SHA,ZIP_SHA,'Artifact ID 12797591032','1356621 bytes'):
            need(item in logtext,'actual job log/source/artifact chain missing '+item)
        REPORT['job_log_identity']=identity(log)
        REPORT['actual_pipeline_elapsed_seconds']=pipeline['elapsed_seconds']
        REPORT['original_V3_raw_passes_unchanged']=4
        REPORT['actual_V4_math_and_checker_failures_preserved']=True
        REPORT['remaining_unproved_premises']=['Native inner-wire-as-hole semantics.','Native joining of actual endpoint gaps remains inside registered corner squares.',
            'Compiled/native geometry errors and complete-factory G2.','The eight conditional model upper bounds still above original TOL.','Physical G3-G5 and device/material evidence.']
        for path,expected in list(CACHE.items()):
            with path.open('rb') as stream:actual={'bytes':path.stat().st_size,'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
            need(actual==expected,'input/source changed during independent audit: '+str(path))
        REPORT['all_readback_source_and_input_identities_unchanged_after_audit']=True
        REPORT['audit_completed']=True
    except BaseException as exc:
        REPORT['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        raise
    finally:
        signal.alarm(0)
        REPORT['audit_seconds']=time.monotonic()-started
        REPORT['audit_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        REPORT['independent_readback_counters']=COUNTS
        REPORT['registered_budget_respected']=REPORT['audit_seconds']<=240 and REPORT['audit_peak_RSS_bytes']<=402653184
        data=(json.dumps(REPORT,indent=2)+'\n').encode()
        need(len(data)<=4194304,'registered 4 MiB audit output budget exceeded')
        need(not OUTPUT.exists(),'refuse overwrite previous actual audit attempt')
        OUTPUT.write_bytes(data)
        print(json.dumps({'audit_completed':REPORT['audit_completed'],'output':str(OUTPUT),'bytes':len(data),'sha256':sha(data),
            'seconds':REPORT['audit_seconds'],'peak_RSS_bytes':REPORT['audit_peak_RSS_bytes'],
            'conditional_model_passes':REPORT.get('actual_conditional_model_passes'),'failure':REPORT.get('failure')}),flush=True)


if __name__=='__main__':main()
