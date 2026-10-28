#!/usr/bin/env python3
"""Cross-author exact readback of the actual failed V4 single-cell execution.

Low-level archive and exact interval predicates below are copied from this
reviewer's frozen V3 auditor (SHA 1efdc3cf4e824a0db2ad0babb1d6ee66eb16a8dc2b6a196c8f94c81e03631309).
No producer, verifier, owned supervisor, or native CAD code is imported/run.
"""
import copy
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
import sys
import time
import traceback
import zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ACTUAL=BASE/'r5-ci-results/run-40643098035'
ARCHIVE=BASE/'r5-ci-results/RAZR-R5-refinement-v4-run-40643098035.zip'
V3=BASE/'r5-ci-results/run-40641230212'
R5=BASE/'r5-envelope'
R4=BASE/'razr-current/engineering/engineering-followup-20261027-r4/envelope'
REMOTE_OUTPUT='/home/runner/work/_temp/razr-r5-refinement-v4'
REMOTE_R5='/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/engineering/engineering-followup-20261028-r5/compute'
REMOTE_R4='/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/engineering/engineering-followup-20261027-r4/envelope'
HEAD='06e4f37690e2d5b9dc2abaf69cab9ba16957f1e2'
ANCHOR='c5f6606924937d716b007cd3ffa8e54df8ecfa5d'
ZIP_SHA='bb76de46294c6cc77aed277602aaf11c8548486364ace52ba31250a285757987'
LOCK_SHA='9068291e6684299604d489fbf175cf781c0d1a1648cf690a2f5c337dec139c20'
LIMITS=dict(wall_seconds=600,RSS_limit_bytes=805306368,shared_ceiling_bytes=7301444403,disk_floor_bytes=104857600,maximum_output_bytes=41943040,metadata_margin_bytes=4194304)
CAPACITY=dict(wall_seconds=600,RSS_limit_bytes=805306368,maximum_splits=4096,maximum_depth=24,maximum_boundary_box_tests=12000000,tiny_retained_volume_exact=str(Q(1e-7)/100000))
CACHE={}
COUNTS=dict(assertions=0,excluded_cell_separation_inequalities=0,blocked_direction_checks=0,boundary_box_degeneracies_preserved=0)
REPORT={'schema':'razr-r5-cross-author-actual-v4-failed-execution-readback-v1','audit_completed':False,'actual_V4_pipeline_completed':False,'actual_V4_single_clearance_passed':False,'actual_V4_checker_execution_completed':False,'producer_or_verifier_code_imported':False,'native_operations_executed':0,'full_continuous_G2':False,'all_blockers_closed':False,'independent_negative_controls':[]}
OUTPUT=HERE/'R5_V4_INDEPENDENT_ACTUAL_FAILURE_READBACK.json'
REGISTRATION=HERE/'R5_V4_ACTUAL_READBACK_BUDGET.json'

def need(value, message):
    COUNTS['assertions'] += 1
    if not value:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def identity(path):
    path = Path(path)
    if path not in CACHE:
        data = path.read_bytes()
        CACHE[path] = {'bytes':len(data), 'sha256':sha(data)}
    return CACHE[path]

def read_json(path):
    return json.loads(Path(path).read_text())

def mapped(path):
    for prefix, root in ((REMOTE_OUTPUT, ACTUAL), (REMOTE_R5, R5), (REMOTE_R4, R4)):
        if path.startswith(prefix + '/'):
            tail = PurePosixPath(path[len(prefix)+1:])
            need(not tail.is_absolute() and '..' not in tail.parts, 'recorded path escapes bound root')
            return root.joinpath(*tail.parts)
    raise ValueError('unregistered recorded path: ' + path)

def bound(record, relative_root=None):
    path = relative_root / record['path'] if relative_root is not None else mapped(record['path'])
    need(identity(path) == {k:record[k] for k in ('bytes','sha256')}, 'identity mismatch: ' + str(path))
    return path

def utc(value):
    return dt.datetime.fromisoformat(value.replace('Z','+00:00'))

def ranges(value):
    need(len(value) == 3 and all(len(pair) == 2 for pair in value), 'three interval axes required')
    result = tuple(tuple(Q(x) for x in pair) for pair in value)
    need(all(a <= b for a,b in result), 'reversed source interval')
    return result

def measure(box):
    need(all(a < b for a,b in box), 'cell must have three positive directed widths')
    return (box[0][1]-box[0][0]) * (box[1][1]-box[1][0]) * (box[2][1]-box[2][0])

def original_sources(proof, stationary=False):
    displacement = ranges(proof['full_remaining_displacement_box_exact'])
    cover = proof['complete_raw_boundary_slab_cover']
    result = []
    for side, key in enumerate(('first_complete_boundary_boxes','second_complete_boundary_boxes')):
        records = cover[key]
        need(bool(records), 'complete boundary cannot be empty')
        pieces = []
        ids = []
        for record in records:
            box = ranges(record['box_exact'])
            if stationary and side == 0:
                box = tuple((a-displacement[k][0], b-displacement[k][1]) for k,(a,b) in enumerate(box))
                need(all(a <= b for a,b in box), 'stationary unexpansion inverted interval')
            COUNTS['boundary_box_degeneracies_preserved'] += int(any(a == b for a,b in box))
            pieces.append(box)
            ids.append((record['kind'],record['index']))
        need(len(ids) == len(set(ids)), 'duplicate complete boundary identity')
        hull = tuple((min(p[k][0] for p in pieces),max(p[k][1] for p in pieces)) for k in range(3))
        declared = ranges(cover['first_whole_support_box_exact' if side == 0 else 'second_whole_support_box_exact'])
        if stationary and side == 0:
            declared = tuple((a-displacement[k][0],b-displacement[k][1]) for k,(a,b) in enumerate(declared))
        need(hull == declared, 'complete boundary hull differs from declared whole support')
        result.append((pieces,hull))
    return result

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
        COUNTS['excluded_cell_separation_inequalities'] += len(pieces)
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
        COUNTS['blocked_direction_checks'] += 1
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
            need(valid_index(side,2) and valid_index(piece,len(sources[side][0])) and type(axis) is int and axis==k and valid_index(end,2), 'invalid original endpoint witness')
            need(sources[side][0][piece][k][end]==cut, 'split is not original complete boundary endpoint')
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
            need(reason in ('tiny_exact_volume_retained','global_predicate_budget_retained','path_depth_limit_retained','global_split_limit_retained','no_original_blocking_endpoint_inside_cell'), 'unregistered stop reason')
            if reason=='tiny_exact_volume_retained':need(value<=Q(CAPACITY['tiny_retained_volume_exact']), 'tiny retained threshold invalid')
            if reason=='path_depth_limit_retained':need(depth==CAPACITY['maximum_depth'], 'incorrect path stop')
            observation=node.get('actual_channel_observation')
            checked_directions=0
            if observation is not None:
                need(observation['excluded_open_interior'] is False and observation['actual_material_interference_claimed'] is False, 'retained observation overclaims')
                need(not observation.get('search_stopped_at_predicate_budget'), 'unexpected partial-budget observation in actual six-split single tree')
                check_kept(observation,box,sources);checked_directions=12
            if reason=='no_original_blocking_endpoint_inside_cell':
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


def phase_coverage(report):
    need(report['phase']=='single_retained_cell', 'incorrect phase')
    keys=[(r['case_id'],r['frame']) for r in report['frames']]
    need(len(keys)==len(set(keys)), 'duplicate actual frame')
    need(keys==[('case-001',1)], 'single selected frame missing/extra')


def root_coverage(frame, certificate):
    need(frame['root_original_cell_indices']==[202] and frame['root_count']==1 and [r['original_cell_index'] for r in certificate['roots']]==[202], 'missing/extra/duplicate original root')


def reject(name, function):
    error=None
    try:function()
    except (ValueError,KeyError,IndexError,TypeError) as exc:error=str(exc)
    need(error is not None, 'independent negative mutation accepted: '+name)
    REPORT['independent_negative_controls'].append({'name':name,'actual_rejected':True,'reason':error})


def independent_controls(producer, certificate, sources, stats):
    frame=producer['frames'][0];tree=certificate['roots'][0]['tree'];root=ranges(certificate['roots'][0]['root_box_exact'])
    for name, change in [('missing-frame',dict(producer,frames=[])),('duplicate-frame',dict(producer,frames=producer['frames']*2)),('incorrect-phase',dict(producer,phase='preflight'))]:
        reject(name,lambda change=change:phase_coverage(change))
    for name, roots in [('omitted-original-root',[]),('duplicate-original-root',certificate['roots']*2)]:
        reject(name,lambda roots=roots:root_coverage(frame,dict(certificate,roots=roots)))
    split=stats['splits'][0];i=split['node_id'];parent=ranges(split['parent_box_exact']);smallest=min(stats['leaves'],key=lambda x:Q(x['positive_directed_volume_exact']));si=smallest['node_id']
    changes=[('omitted-partition-child',lambda t:t['nodes'][i].update(children=t['nodes'][i]['children'][:1])),
             ('duplicated-partition-child',lambda t:t['nodes'][i].update(children=t['nodes'][i]['children'][:1]*2)),
             ('cut-on-parent-boundary',lambda t:t['nodes'][i].update(cut_exact=str(parent[t['nodes'][i]['axis']][0]))),
             ('discarded-closed-cut-plane',lambda t:t['nodes'][i].update(closed_cut_plane_retained_as_zero_volume_carrier=False)),
             ('incorrect-positive-directed-volume',lambda t:t['nodes'][i].update(parent_positive_directed_volume_exact='0')),
             ('omitted-pending-leaf-node',lambda t:t['nodes'].pop()),
             ('discarded-smallest-nonzero-leaf-volume',lambda t:t['nodes'][si].update(positive_directed_volume_exact='0'))]
    for name, alter in changes:
        changed=copy.deepcopy(tree);alter(changed)
        reject(name,lambda changed=changed:tree_readback(changed,root,sources))
    REPORT['independent_negative_controls'][-1].update(actual_original_leaf_kind=smallest['kind'],actual_original_leaf_reason=smallest['reason'],actual_original_positive_volume_exact=smallest['positive_directed_volume_exact'])
    REPORT['independent_channel_negative_controls_executed']=0
    REPORT['independent_channel_negative_controls_reason']='Actual V4 tree has zero excluded leaves; no actual V4 exclusion certificate exists to mutate. No V3 or synthetic substitute is counted as a V4 control.'


def actual_identity_and_archive():
    need(identity(ARCHIVE)=={'bytes':21547,'sha256':ZIP_SHA}, 'received actual artifact differs')
    members=[]
    with zipfile.ZipFile(ARCHIVE) as archive:
        items=archive.infolist();need(len(items)==len({x.filename for x in items})==16, 'expected actual 16 unique files')
        for item in items:
            name=PurePosixPath(item.filename);need(not name.is_absolute() and '..' not in name.parts and not item.is_dir(), 'unsafe/unexpected artifact member')
            data=archive.read(item);record={'bytes':len(data),'sha256':sha(data)}
            need(len(data)==item.file_size and identity(ACTUAL.joinpath(*name.parts))==record, 'expanded actual member differs')
            members.append(dict(path=item.filename,crc32=item.CRC,**record))
    need({x['path'] for x in members}=={str(f.relative_to(ACTUAL)) for f in ACTUAL.rglob('*') if f.is_file()}, 'omitted/extra expanded actual file')
    REPORT['artifact']=dict(identity(ARCHIVE),file_count=16,members=members)
    metadata=read_json(HERE/'R5_V4_REMOTE_ACTUAL_METADATA.json')['records']
    run=next(x['data'] for x in metadata if x['url'].endswith('/40643098035'))
    artifacts=next(x['data']['artifacts'] for x in metadata if '/artifacts?' in x['url'])
    artifact=next(x for x in artifacts if x['id']==12796451605)
    need(run['id']==40643098035 and run['head_sha']==HEAD and run['head_branch']=='evidence/full-sprint-20261028-r5' and run['event']=='push' and run['run_attempt']==1, 'actual run/head/branch mismatch')
    need(run['status']=='completed' and run['conclusion']=='failure', 'real failure run reclassified')
    need(artifact['digest']=='sha256:'+ZIP_SHA and artifact['size_in_bytes']==21547 and artifact['workflow_run']['id']==run['id'] and artifact['workflow_run']['head_sha']==HEAD, 'artifact remote digest/run binding mismatch')
    retrieved=read_json(HERE/'R5_V4_REMOTE_CURRENT_HEAD_SOURCES.json');need(retrieved['commit']==HEAD, 'exact source retrieval commit differs')
    fetched={r['path']:r['content'].encode() for r in retrieved['files']}
    workflow=fetched['.github/workflows/r5-exterior-channel.yml'];lock=fetched['engineering/engineering-followup-20261028-r5/compute/R5E_PORTABLE_SOURCE_LOCK_V4.json']
    need(workflow==(BASE/'r5-integration/r5-refinement-v4-workflow.yml').read_bytes(), 'actual current workflow differs from prepared workflow')
    need(sha(lock)==LOCK_SHA and lock==(R5/'R5E_PORTABLE_SOURCE_LOCK_V4.json').read_bytes(), 'actual source-lock bytes differ')
    for text in (LOCK_SHA,"github.ref == 'refs/heads/evidence/full-sprint-20261028-r5'",'contents: read','timeout-minutes: 55','actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1','actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9'):
        need(text in workflow.decode(), 'workflow required binding absent')
    pipeline=read_json(ACTUAL/'pipeline.json');need(pipeline['environment']['github_sha']==HEAD and pipeline['environment']['github_run_id']==str(run['id']), 'actual runtime head/run mismatch')
    need(pipeline['source_commit']==ANCHOR and pipeline['source_root']==REMOTE_R5 and pipeline['public_r4_root']==REMOTE_R4, 'old source anchor and actual roots differ')
    bound(pipeline['source_lock_identity'])
    lock_json=json.loads(lock);expected=[]
    for field,remote,local in [('r5_files',REMOTE_R5,R5),('r4_source_files',REMOTE_R4,R4)]:
        for row in lock_json[field]:
            need(identity(local/row['path'])=={k:row[k] for k in ('bytes','sha256')}, 'final locked source changed')
            expected.append(dict(row,path=remote+'/'+row['path']))
    need(len(expected)==12 and pipeline['actual_source_identities']==expected, 'complete runtime source set differs')
    bridge=read_json(R5/'R5E_PUBLIC_INPUT_BRIDGE.json');expected=[]
    need(len(bridge['files'])==19 and len({x['path'] for x in bridge['files']})==19 and bridge['source_commit']==ANCHOR, 'public bridge completeness differs')
    for row in bridge['files']:
        need(row['decoded_json_equal'] is True and not row['changed_strings'] and identity(R4/row['path'])==row['public_identity'], 'public input identity/semantics changed')
        expected.append(dict(row['public_identity'],path=REMOTE_R4+'/'+row['path']))
    need(expected==pipeline['public_inputs'], 'actual complete public input identity set differs')
    need(pipeline['unchanged_process_limits']==LIMITS and {k:read_json(R4/'support-v4-supervision/controller.json')['limits'][k] for k in LIMITS}==LIMITS, 'original six gates changed')
    need(pipeline['completed'] is False and pipeline['failure']['message']=='owned stage failed; later stages remain unexecuted: verify-single', 'actual pipeline failure not preserved')
    need([(x['label'],x['phase']) for x in pipeline['stages']]==[('single-retained-cell','single_retained_cell'),('verify-single','verify_single')], 'unexpected later stage launched')
    need(not any(x['path'].startswith(('preflight','all-refined','verify-all')) for x in members), 'later stage contract/output exists after failure')
    need('source_and_public_inputs_unchanged' not in pipeline and 'actual_frame_count' not in pipeline and 'conditional_raw_clearance_passes' not in pipeline, 'unexecuted final pipeline qualification fabricated')
    need(all(pipeline[k] is False for k in ('native_Common_called','native_material_semantics_verified','compiled_transform_error_verified','full_continuous_G2','all_blockers_closed','original_clearance_threshold_changed','original_displacement_boxes_changed')), 'scientific scope overclaimed')
    joblog=BASE/'r5-integration/R5_V4_CI_JOB_122665572124.log';log=joblog.read_text()
    for text in (HEAD,LOCK_SHA,ZIP_SHA,'Artifact ID 12796451605','21547 bytes','Process completed with exit code 2.','owned stage failed; later stages remain unexecuted: verify-single'):
        need(text in log, 'actual CI log chain lacks '+text)
    REPORT['actual_run_binding']={'run_id':run['id'],'actual_commit':HEAD,'actual_branch':run['head_branch'],'conclusion':'failure','artifact_id':artifact['id'],'source_lock_sha256':LOCK_SHA,'workflow_sha256':sha(workflow),'locked_source_files_rehashed':12,'public_input_files_rehashed':19,'job_log':identity(joblog),'actual_global_postexecution_source_check_record_present':False,'actual_driver_original_threshold_post_verify_guard_reached':False,'later_three_stages_unexecuted':True}
    return pipeline,{x['path']:x for x in bridge['files']}


def stage_receipts(pipeline):
    previous=utc(pipeline['started_utc']);rows=[];nonces=set();drivers=set()
    for number,stage in enumerate(pipeline['stages']):
        label=stage['label'];phase=stage['phase'];success=number==0
        for key in ('contract','supervision_contract','driver_log','controller'):bound(stage[key])
        c=read_json(mapped(stage['contract']['path']));s=read_json(mapped(stage['supervision_contract']['path']));controller=read_json(mapped(stage['controller']['path']))
        receipt_path=ACTUAL/(label+'-supervision')/'entry-receipt.json';entry=read_json(receipt_path);report_path=ACTUAL/label/'report.json';report=read_json(report_path)
        cp=REMOTE_OUTPUT+'/'+label+'-contract.json';sp=REMOTE_OUTPUT+'/'+label+'-supervision-contract.json';out=REMOTE_OUTPUT+'/'+label
        worker='exterior_refinement_r5e_v4.py' if success else 'verify_exterior_refinement_r5e_v4.py'
        need(c['phase']==phase and c['capacity']==CAPACITY and c['source_commit']==ANCHOR and c['producer_sha256']==identity(R5/worker)['sha256'], 'math contract phase/capacity/source binding differs')
        need(c['completed_prerequisites']==[] and c['all_original_D_components_retained'] is True and c['original_float64_TOL_unchanged'] is True and c['current_factory_G2_qualified'] is False, 'actual initial-stage contract scope differs')
        for key in ('r4_report','r4_independent_report','r4_stationary_diagnostic','public_input_bridge','method','base_producer_source','base_verifier_source','single_verifier_source','real_retained_cell_selection'):bound(c[key])
        need({k:s[k] for k in LIMITS}==LIMITS and s['expected_output_bytes']==41943040 and s['zero_RSS_missing_observations_allowed'] is False, 'actual original supervision limits changed')
        need(controller['limits']==s and controller['contract_sha256']==identity(mapped(stage['supervision_contract']['path']))['sha256'] and s['registered_math_contract_sha256']==identity(mapped(stage['contract']['path']))['sha256']==report['contract_sha256'], 'actual contract hash chain differs')
        need(s['supervisor_sha256']==controller['source_sha256']==identity(R4/'supervise_owned_pure_math_r4e_v2.py')['sha256'] and s['worker_entry_sha256']==identity(R4/'run_owned_pure_math_r4e_v3.py')['sha256'], 'owned entry/controller source differs')
        bound(s['worker']);bound(s['owned_process'])
        need(s['worker']['path']==REMOTE_R5+'/'+worker and s['worker_entry']==REMOTE_R4+'/run_owned_pure_math_r4e_v3.py' and s['worker_output_directory']==out, 'owned worker/output path mismatch')
        need(s['canonical_worker_options']==['--contract','--output'] and entry['canonical_worker_arguments']==['--contract',cp,'--output',out], 'entry canonical arguments mismatch')
        need(entry['actual_argument_bindings']=={'worker_output_directory':out,'mathematical_contract_path':cp,'mathematical_contract_sha256':report['contract_sha256']}, 'actual worker arguments not bound')
        expected_command=['/usr/bin/python3','-I','-S','-B',REMOTE_R4+'/supervise_owned_pure_math_r4e_v2.py','--contract',sp,'--out',out+'-supervision','--','--contract',cp,'--output',out]
        expected_entry=['/usr/bin/python3','-I','-S','-B',s['worker_entry'],'--supervision-contract',sp,'--receipt',out+'-supervision/entry-receipt.json','--','--contract',cp,'--output',out]
        need(stage['command']==expected_command and controller['command']==expected_entry, 'actual command path/argument binding differs')
        need(stage['completed'] is success and stage['owned_supervisor_completed'] is success and controller['completed'] is success and controller['entry_completed'] is success and entry['completed'] is success and report['execution_completed'] is success, 'actual success/failure state changed')
        need(stage['supervisor_exit_code']==(0 if success else 2) and controller['worker_exit_code']==(0 if success else 1) and entry['worker_exit_code']==(0 if success else None), 'original exit chain differs')
        need(stage['actual_worker_started'] is True and stage['worker_started_by_driver'] is True and controller['worker_started'] is True and entry['worker_started'] is True, 'owned stage did not actually start')
        need(stage['resource_stop'] is None and controller['resource_stop'] is None and controller['missing_RSS_zero_substitutions']==0, 'resource failure incorrectly replaced by checker failure')
        need(controller['owned_child_identity_verified'] is True and controller['owned_channel_descriptors_closed'] is True and controller['source_and_contract_unchanged'] is True and entry['entry_and_worker_and_owned_source_unchanged'] is True and entry['native_geometry_imported'] is False, 'owned identity/source closeout mismatch')
        need(previous<=utc(c['registered_utc'])<=utc(controller['started_utc'])<=utc(controller['finished_utc']), 'execution registration/order mismatch');previous=utc(controller['finished_utc'])
        need(0<=report['seconds']<=controller['elapsed_seconds']<=600 and 0<report['peak_RSS_bytes']==entry['peak_RSS_bytes']<=805306368, 'actual wall/RSS original gate violated')
        handshake=controller['owned_child_handshake'];packet=handshake['packet'];parent=handshake['parent_identity'];verified=handshake['verified_binding']
        need(packet['kind']=='razr_owned_child_identity_v1' and packet['source_sha256']==s['worker_entry_sha256'] and packet['stat']==verified['stat'] and packet['status']==verified['status'], 'owned handshake source/PID/starttime mismatch')
        need(packet['os_getpid']==packet['stat']['pid']==packet['status']['Pid']==int(packet['proc_self_visible_pid']) and packet['os_getppid']==packet['stat']['ppid']==packet['status']['PPid']==parent['os_getpid'], 'owned child/parent PID binding mismatch')
        need(packet['pid_namespace']==verified['pid_namespace']==parent['pid_namespace'] and packet['pid_for_children_namespace']==verified['pid_for_children_namespace'] and parent['stat']['starttime_ticks']<=packet['stat']['starttime_ticks'], 'owned namespace/starttime mismatch')
        need(packet['nonce'] not in nonces and len(packet['nonce'])==64 and set(packet['nonce'])<=set('0123456789abcdef'), 'owned nonce missing/reused');nonces.add(packet['nonce']);drivers.add(parent['os_getppid'])
        need(0<min(handshake['initial_memory'].values())<=max(handshake['initial_memory'].values())<=entry['peak_RSS_bytes'], 'handshake memory invalid')
        observations=controller['observations'];need(len(observations)==1, 'expected actual subsecond admission-only persisted rows')
        admission=observations[0]
        need(admission['disk_available_bytes']>=104857600+41943040+4194304 and admission['shared_unreclaimable_bytes']+805306368<=7301444403, 'actual resource admission did not satisfy original gates')
        final=controller['final_resources'];need(final['disk_available_bytes']>=104857600 and final['shared_unreclaimable_bytes']<=7301444403, 'actual final resources exceed original gates')
        output_bytes=sum(p.stat().st_size for p in (ACTUAL/label).rglob('*') if p.is_file());need(output_bytes<=41943040, 'actual output limit exceeded')
        if success:
            bound(stage['report']);need(report['source_and_contract_unchanged'] is True and report['all_frame_capacity_observations_completed'] is True and len(report['base_channel_controls'])==5 and all(x['passed'] is True for x in report['base_channel_controls']), 'completed producer provenance/control scope differs')
        else:
            need('report' not in stage and 'failure' in report and report['failure']['message']=='actual geometric and partition controls required', 'actual checker failure missing/reclassified')
            need(c['producer_report']==pipeline['stages'][0]['report'] and c['producer_owned_supervision']==pipeline['stages'][0]['controller'], 'failed checker producer prerequisite not the actual completed single stage')
            need(c['expected_phase']=='single_retained_cell' and c['expected_case_frames']==[['case-001',1]] and c['verifier_sha256']==s['worker']['sha256'], 'failed checker expected case/source binding differs')
            need(report['verified_producer_report']==c['producer_report'] and report['producer_code_imported'] is False, 'failed checker report identity differs')
            need(report['failure']['message'] in (ACTUAL/(label+'-supervision')/'execution.log').read_text(), 'actual checker traceback not preserved in execution log')
        rows.append({'label':label,'phase':phase,'worker_completed':success,'controller_completed':controller['completed'],'supervisor_exit_code':stage['supervisor_exit_code'],'controller_worker_exit_code':controller['worker_exit_code'],'entry_worker_exit_code':entry['worker_exit_code'],'controller_seconds':controller['elapsed_seconds'],'worker_seconds':report['seconds'],'entry_peak_RSS_bytes':entry['peak_RSS_bytes'],'entry_receipt_identity':identity(receipt_path),'scientific_report_identity':identity(report_path),'persisted_resource_rows':1,'persisted_live_RSS_rows':0,'handshake_initial_memory':handshake['initial_memory'],'admission':admission,'final_resources':final,'actual_output_bytes':output_bytes,'resource_stop':None,'all_recorded_original_resource_checks_satisfied':True})
    need(previous<=utc(pipeline['finished_utc']) and len(drivers)==1, 'pipeline finish/common driver identity mismatch')
    REPORT['stages']=rows;REPORT['original_remote_gates']=LIMITS
    REPORT['actual_resource_sampling_scope']='Both actual stages were shorter than 1 s; controller persisted admission only, plus handshake initial memory and entry peak RSS. No persisted live sample is invented. Historical identity is checked from receipts, not re-probed in the current OS.'
    return read_json(ACTUAL/'single-retained-cell/report.json'),read_json(ACTUAL/'verify-single/report.json')


def exact_actual_tree(producer, checker, bridge):
    phase_coverage(producer);need(producer['capacity']==CAPACITY and Q(producer['original_TOL_exact'])==Q(1e-7) and producer['no_positive_thin_leaf_discarded'] is True, 'original threshold/finite policy changed')
    need(all(producer[k] is False for k in ('native_Common_called','native_material_semantics_verified','compiled_error_bound_verified','full_continuous_G2','all_blockers_closed')), 'producer native/full-domain overclaim')
    selection=read_json(bound(producer['real_retained_cell_selection']))
    need(selection['source_run_id']==40641230212 and selection['source_commit']=='41333a369cbc44aab6fb5a723b75833a693ac16c' and selection['case_id']=='case-001' and selection['frame']==1 and selection['original_raw_cell_index']==202, 'real V3 selection identity changed')
    for key, filename in [('source_pipeline','pipeline.json'),('source_all_raw_report','all-raw/report.json'),('source_independent_all_report','verify-all/report.json')]:need(identity(V3/filename)==selection[key], 'actual V3 prerequisite bytes changed')
    v3cert=selection['source_certificate'];need(identity(V3/v3cert['relative_path'])=={k:v3cert[k] for k in ('bytes','sha256')}, 'actual V3 certificate identity changed')
    old_actual=json.loads(gzip.decompress((V3/v3cert['relative_path']).read_bytes()))
    need(old_actual['cells'][202]==selection['actual_V3_cell'] and old_actual['cells'][202]['excluded_open_interior'] is False, 'V4 selected cell was not the exact actual V3 retained cell')
    baseline=read_json(bound(producer['source_report_identity']));original=next(r for r in baseline['frames'] if (r['case_id'],r['frame'])==('case-001',1));frame=producer['frames'][0]
    need(frame['pair']==original['pair'] and frame['original_raw_proof_identity']==original['proof']==selection['original_R4_raw_proof_identity'], 'actual material pair/raw source detached')
    proof_path=bound(frame['source_proof']);entry=bridge['support-v4/'+original['proof']['path']]
    need(entry['raw_identity']=={k:original['proof'][k] for k in ('bytes','sha256')} and entry['public_identity']==selection['public_R4_proof_identity']==identity(proof_path), 'original/public proof bridge differs')
    with gzip.open(proof_path,'rb') as stream:raw=stream.read(33554432+1)
    need(len(raw)<=33554432,'single proof readback cap exceeded');REPORT['source_proofs_read']={'count':1,'compressed_bytes':proof_path.stat().st_size,'decoded_bytes':len(raw),'full_R4_enclosure_math_reexecuted':False}
    proof=json.loads(raw);del raw
    canonical=json.dumps(proof,sort_keys=True,separators=(',',':')).encode();need(sha(canonical)==entry['public_canonical_json_sha256'], 'complete decoded source proof differs');del canonical
    need(frame['original_remaining_displacement_box_exact']==proof['full_remaining_displacement_box_exact']==original['full_remaining_displacement_box_exact']==selection['source_row_original_D'], 'full original D changed or stationary substitution used')
    sources=original_sources(proof,stationary=False);cover=proof['complete_raw_boundary_slab_cover'];original_cells=cover['combined']['positive_cells'];oldcell=original_cells[202]
    need(len(original_cells)==215==frame['original_raw_cell_count'] and frame['source_piece_counts']==[len(s[0]) for s in sources]==[1438,460], 'complete source cells/pieces changed')
    cert_path=bound(frame['certificate'],ACTUAL/'single-retained-cell')
    with gzip.open(cert_path,'rb') as stream:raw=stream.read(67108864+1)
    need(len(raw)<=67108864,'actual tree certificate decode cap exceeded');certificate=json.loads(raw);del raw
    need(certificate['schema']=='razr-r5e-exact-endpoint-refinement-tree-v4' and certificate['frame']=={k:v for k,v in frame.items() if k!='certificate'}, 'tree header detached from actual producer frame')
    root_coverage(frame,certificate);root_record=certificate['roots'][0]
    need(root_record['root_box_exact']==oldcell['box_exact']==selection['actual_V3_cell']['box_exact'] and Q(root_record['root_directed_volume_exact'])==Q(oldcell['positive_directed_volume_exact']), 'original positive root changed')
    root_box=ranges(root_record['root_box_exact']);stats=tree_readback(root_record['tree'],root_box,sources)
    need(stats['node_count']==13 and stats['split_count']==6 and stats['leaf_count']==7 and stats['excluded_leaf_count']==0 and stats['retained_leaf_count']==7 and stats['maximum_depth']==6, 'actual six-split/zero-exclusion topology differs')
    need(Q(stats['retained_sum_exact'])==measure(root_box)==Q(frame['retained_leaf_sum_exact'])==Q(frame['original_root_sum_exact'])==Q(frame['selected_conditional_raw_upper_exact_mm3']), 'full original retained volume not conserved')
    need(Q(stats['excluded_open_sum_exact'])==Q(frame['excluded_open_leaf_sum_exact'])==0 and frame['original_clearance_gate_passed'] is False and Q(frame['selected_conditional_raw_upper_exact_mm3'])>Q(1e-7), 'zero-exclusion original-threshold failure altered')
    need(frame['all_closed_cut_planes_and_original_cell_boundaries_retained'] is True and frame['total_leaf_count']==7 and frame['maximum_depth_reached']==6 and frame['exact_splits_this_frame']==6 and frame['original_min_volume_plus_TOL_gate_passed'] is None, 'single-frame topology/qualification scope differs')
    need(producer['counters']=={'channels_tested':84,'boundary_box_tests':4017,'splits':6,'tree_nodes_visited':13} and frame['exact_boundary_box_tests_this_frame']==4017, 'recorded actual bounded counters changed')
    need(producer['total_original_roots']==1 and producer['maximum_complete_piece_count_sum']==1898 and producer['total_compressed_original_input_bytes']==1114119 and producer['original_root_channel_static_predicate_upper']==11388 and producer['complete_phase_maximum_leaves']==4097 and producer['complete_phase_maximum_tree_nodes']==8193 and producer['new_predicate_hard_budget']==12000000 and producer['conditional_clearance_passes']==0, 'actual single capacity/result differs')
    need(producer['maximum_exact_coordinate_character_count']==max(len(str(v)) for source in sources for box in source[0] for interval in box for v in interval), 'actual original coordinate size metadata differs')
    expected_checker={'case_id':'case-001','frame':1,'original_roots_verified':1,'exact_tree_nodes_verified':13,'exact_splits_verified':6,'all_retained_and_excluded_leaves_verified':7,'complete_boundary_piece_separations_checked':0,'retained_upper_exact_mm3':stats['retained_sum_exact'],'original_clearance_gate_passed':False}
    need(checker['frames']==[expected_checker] and checker['execution_completed'] is False and checker['channel_negative_controls']==[], 'actual partial checker result misrepresented')
    names=['missing-frame','duplicate-frame','incorrect-phase','omitted-original-root','duplicate-original-root','omitted-partition-child','duplicated-partition-child','cut-on-parent-boundary','discarded-closed-cut-plane','incorrect-positive-directed-volume','omitted-pending-leaf-node','discarded-smallest-nonzero-leaf-volume']
    controls=checker['phase_negative_controls']+checker['root_coverage_negative_controls']+checker['partition_negative_controls']
    need([r['name'] for r in controls]==names and all(r['actual_rejected'] is True and r['reason'] for r in controls), 'actual twelve rejected controls not complete')
    tiny=[x for x in stats['leaves'] if x.get('reason')=='tiny_exact_volume_retained'];big=[x for x in stats['leaves'] if x.get('reason')=='no_original_blocking_endpoint_inside_cell']
    need(len(tiny)==6 and len(big)==1 and all(0<Q(x['positive_directed_volume_exact'])<=Q(CAPACITY['tiny_retained_volume_exact']) for x in tiny), 'positive tiny-layer preservation differs')
    smallest=min(stats['leaves'],key=lambda x:Q(x['positive_directed_volume_exact']))
    need(controls[-1]['actual_original_leaf_kind']==smallest['kind']=='retained' and controls[-1]['actual_original_positive_volume_exact']==smallest['positive_directed_volume_exact'] and smallest['reason']=='tiny_exact_volume_retained', 'actual smallest-leaf negative control classification differs')
    large_id=big[0]['node_id'];observation=root_record['tree']['nodes'][large_id]['actual_channel_observation'];pieces=[]
    for obstruction in observation['all_registered_channels_blocked']:
        side,index=obstruction['material_side'],obstruction['blocking_piece_index'];record=cover['first_complete_boundary_boxes' if side==0 else 'second_complete_boundary_boxes'][index]
        pieces.append(dict(obstruction,source_boundary_piece_kind=record['kind'],source_boundary_piece_original_index=record['index'],source_complete_boundary_box_exact=record['box_exact']))
    REPORT['exact_tree_readback']=stats
    REPORT['actual_large_retained_leaf_blockers']={'node_id':large_id,'all_twelve_channels_rechecked':True,'no_recorded_blocker_endpoint_strictly_inside_leaf':True,'records':pieces,'material_collision_claimed':False}
    REPORT['scientific_failure']={'selected_original_cell':202,'root_volume_exact':str(measure(root_box)),'root_volume_mm3_display':float(measure(root_box)),'retained_volume_exact':stats['retained_sum_exact'],'excluded_open_volume_exact':'0','original_TOL_exact':str(Q(1e-7)),'original_threshold_passed':False,'retained_over_TOL_ratio_exact':str(Q(stats['retained_sum_exact'])/Q(1e-7)),'tiny_retained_leaf_count':6,'tiny_retained_sum_exact':str(sum(Q(x['positive_directed_volume_exact']) for x in tiny)),'tiny_retained_sum_mm3_display':float(sum(Q(x['positive_directed_volume_exact']) for x in tiny)),'large_retained_leaf_volume_exact':big[0]['positive_directed_volume_exact'],'smallest_retained_leaf_exact':smallest['positive_directed_volume_exact'],'smallest_retained_leaf_reason':smallest['reason'],'new_clearance_gain_exact':'0','full16_not_executed':True}
    REPORT['checker_failure']={'execution_completed':False,'actual_message':checker['failure']['message'],'actual_phase_controls_rejected':3,'actual_root_coverage_controls_rejected':2,'actual_partition_controls_rejected':7,'actual_channel_controls_executed':0,'actual_channel_control_types_unexecuted':4,'cause':'No excluded leaf existed from which the checker could obtain an actual exclusion-certificate sample. Its final unconditional requirement for nonempty channel_negative_controls raised ValueError.','partial_tree_summary_matches_independent_readback':True,'partial_checks_do_not_equal_successful_checker_execution':True,'changing_checker_outcome_cannot_make_unchanged_0_48_bound_pass':True}
    independent_controls(producer,certificate,sources,stats)
    need(len(REPORT['independent_negative_controls'])==12, 'independent finite control count differs')
    REPORT['scope']={'complete_actual_single_root_coverage_checked':True,'complete_all16_root_coverage_claimed':False,'actual_single_six_cut_endpoint_and_volume_identities_checked':True,'all_positive_thin_leaves_preserved':True,'actual_retention_no_cut_reason_independently_checked':True,'full_channel_search_counter_replayed':False,'actual_counter_records_only_for_4017_predicates':True,'native_material_boundary_and_compiled_error_still_premises':True,'previous_V3_4_of_16_result_unchanged':True}
    del proof,sources,certificate,original_cells;gc.collect()


def main():
    start=time.monotonic();REPORT['started_utc']=dt.datetime.now(dt.timezone.utc).isoformat();registration=read_json(REGISTRATION)
    def stop(signum,frame):raise TimeoutError('registered independent V4 audit wall budget exhausted')
    signal.signal(signal.SIGALRM,stop);signal.alarm(registration['wall_seconds']);resource.setrlimit(resource.RLIMIT_AS,(registration['address_space_limit_bytes'],registration['address_space_limit_bytes']))
    try:
        need(identity(__file__)==registration['audit_source_identity'], 'registered independent audit source changed')
        need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0, 'isolated unoptimized audit entry required')
        REPORT['audit_registration_identity']=identity(REGISTRATION);REPORT['audit_source_identity']=identity(__file__)
        pipeline,bridge=actual_identity_and_archive();producer,checker=stage_receipts(pipeline);exact_actual_tree(producer,checker,bridge)
        REPORT['actual_pipeline_elapsed_seconds']=pipeline['elapsed_seconds']
        REPORT['outcome']='Actual failed execution evidence is internally bound and the complete single-root conservative tree was independently read back. Mathematical clearance failed; original checker failed; later stages were not executed.'
        REPORT['audit_completed']=True
    except BaseException as exc:REPORT['audit_failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0);REPORT['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat();REPORT['audit_seconds']=time.monotonic()-start;REPORT['audit_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;REPORT['audit_operation_counts_including_negative_checks']=COUNTS
        REPORT['registered_local_readback_budget_respected']=REPORT['audit_seconds']<=registration['wall_seconds'] and REPORT['audit_peak_RSS_bytes']<=registration['RSS_limit_bytes']
        data=(json.dumps(REPORT,indent=2,ensure_ascii=False)+'\n').encode()
        if len(data)>registration['maximum_output_bytes']:
            REPORT['audit_completed']=False;REPORT['output_budget_failure']=True;data=(json.dumps(REPORT,indent=2,ensure_ascii=False)+'\n').encode()
        OUTPUT.write_bytes(data)
        print(json.dumps({k:REPORT.get(k) for k in ('audit_completed','audit_seconds','audit_peak_RSS_bytes','registered_local_readback_budget_respected','scientific_failure','checker_failure','audit_failure')},ensure_ascii=False))
    return 0 if REPORT['audit_completed'] and REPORT['registered_local_readback_budget_respected'] else 2


if __name__=='__main__':raise SystemExit(main())
