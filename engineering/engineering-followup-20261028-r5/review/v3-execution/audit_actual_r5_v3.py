#!/usr/bin/env python3
"""Independent, bounded archive/certificate readback; no producer/verifier import.

This audits an already executed CI job.  It neither re-runs native geometry nor
reconstructs the underlying R4 boundary-enclosure proof.  Exact enclosure and
native material semantics remain explicitly stated premises.
"""
import copy
import datetime as dt
from fractions import Fraction as Q
import gc
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path, PurePosixPath
import resource
import signal
import sys
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
OUTPUT = HERE / 'R5_INDEPENDENT_ACTUAL_V3_EXECUTION_AUDIT.json'
REGISTRATION = HERE / 'R5_INDEPENDENT_READBACK_BUDGET.json'
ARCHIVE = BASE / 'r5-ci-results/RAZR-R5-exterior-channel-run-40641230212.zip'
ACTUAL = BASE / 'r5-ci-results/run-40641230212'
R5 = BASE / 'r5-envelope'
R4 = BASE / 'razr-current/engineering/engineering-followup-20261027-r4/envelope'
REMOTE_OUTPUT = '/home/runner/work/_temp/razr-r5-exterior'
REMOTE_R5 = '/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/engineering/engineering-followup-20261028-r5/compute'
REMOTE_R4 = '/home/runner/work/RAZR-SLIDE/RAZR-SLIDE/engineering/engineering-followup-20261027-r4/envelope'
HEAD = '41333a369cbc44aab6fb5a723b75833a693ac16c'
ANCHOR = 'c5f6606924937d716b007cd3ffa8e54df8ecfa5d'
LOCK_SHA = '0c2c867ac8d644341d5d6f0b5596ae2e346061a23cacdab7be6ab18f75eb0a2c'
ZIP_SHA = '62151d3a17e7feb5fc613033dc0eb9dc3dd2ba13e00027c1f81102548a44fc84'
EXPECTED = [(c, f) for c in ('case-001','case-006','case-028','case-037','case-054','case-063','case-072','case-089') for f in (1, 2)]
ORDER = [('single-stationary-witness','single_stationary_witness'),('verify-single','verify_single'),('preflight','preflight'),('all-raw','all_raw'),('verify-all','verify_all')]
LIMITS = dict(wall_seconds=600, RSS_limit_bytes=805306368, shared_ceiling_bytes=7301444403, disk_floor_bytes=104857600, maximum_output_bytes=41943040, metadata_margin_bytes=4194304)
COUNTS = dict(assertions=0, excluded_cell_separation_inequalities=0, blocked_direction_checks=0, boundary_box_degeneracies_preserved=0, source_proofs_decoded=0, source_proof_raw_bytes=0, largest_source_proof_raw_bytes=0)
REPORT = {'schema':'razr-r5-cross-author-actual-v3-execution-audit-v1', 'audit_completed':False,
          'native_operations_executed':0, 'producer_or_verifier_code_imported':False,
          'underlying_R4_enclosure_proofs_reexecuted':False,
          'full_continuous_G2':False, 'all_blockers_closed':False,
          'certificate_reads':[], 'stages':[], 'independent_negative_controls':[]}
CACHE = {}


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


def frame_keys(rows):
    return [(r['case_id'],r['frame']) for r in rows]


def complete_phase(producer, phase, expected):
    need(producer['phase'] == phase, 'actual phase differs')
    keys = frame_keys(producer['frames'])
    need(len(keys) == len(set(keys)), 'duplicate frame')
    need(keys == expected, 'missing, extra, or reordered frame')
    need(expected == EXPECTED if phase == 'all_raw' else expected == [('case-001',1)], 'unexpected registered phase coverage')


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


def rejection(name, callback):
    error = None
    try:
        callback()
    except (ValueError,IndexError,TypeError) as exc:
        error = str(exc)
    need(error is not None, 'independent corrupted-input control accepted: '+name)
    REPORT['independent_negative_controls'].append({'name':name,'actual_rejected':True,'reason':error})


def independent_mutations(good, target, sources, producer):
    changed = dict(good, complete_piece_separation_codes=good['complete_piece_separation_codes'][:-1])
    rejection('omitted-complete-boundary-piece', lambda:check_excluded(changed,target,sources,False))
    changed = dict(good, whole_closed_cell_disjoint_claimed=True)
    rejection('overclaim-closed-cell-disjointness', lambda:check_excluded(changed,target,sources,False))
    changed = copy.deepcopy(good)
    changed['open_channel_exact'][good['axis']][good['end']] = str(target[good['axis']][good['end']])
    rejection('channel-does-not-reach-known-exterior', lambda:check_excluded(changed,target,sources,False))
    changed = dict(good)
    codes = list(good['complete_piece_separation_codes'])
    channel = ranges(good['open_channel_exact'])
    found = False
    for i,piece in enumerate(sources[good['material_side']][0]):
        for k,e in itertools.product(range(3),range(2)):
            holds = piece[k][1] <= channel[k][0] if e == 0 else piece[k][0] >= channel[k][1]
            if not holds:
                codes[i] = str(2*k+e)
                found = True
                break
        if found:
            break
    need(found, 'negative control needs a genuinely false inequality')
    changed['complete_piece_separation_codes'] = ''.join(codes)
    rejection('false-separating-coordinate', lambda:check_excluded(changed,target,sources,False))
    variants = [('missing-frame',dict(producer,frames=producer['frames'][:-1])),
                ('duplicate-frame',dict(producer,frames=producer['frames']+[producer['frames'][0]])),
                ('wrong-actual-phase',dict(producer,phase='preflight'))]
    for name, candidate in variants:
        rejection(name, lambda candidate=candidate:complete_phase(candidate,'all_raw',EXPECTED))


def audit_archive_and_binding():
    need(identity(ARCHIVE) == {'bytes':395931,'sha256':ZIP_SHA}, 'actual archive digest/size changed')
    manifest = []
    with zipfile.ZipFile(ARCHIVE) as z:
        infos = z.infolist()
        need(len(infos) == 53 and len({i.filename for i in infos}) == 53, 'expected exactly 53 unique artifact members')
        for info in infos:
            name = PurePosixPath(info.filename)
            need(not name.is_absolute() and '..' not in name.parts and not info.is_dir(), 'unexpected archive member path')
            data = z.read(info)  # zipfile independently verifies each member CRC.
            need(len(data) == info.file_size, 'archive uncompressed size differs')
            ident = {'bytes':len(data),'sha256':sha(data)}
            need(identity(ACTUAL.joinpath(*name.parts)) == ident, 'expanded archive member differs')
            manifest.append(dict(path=info.filename,crc32=info.CRC,**ident))
    need({r['path'] for r in manifest} == {str(p.relative_to(ACTUAL)) for p in ACTUAL.rglob('*') if p.is_file()}, 'expanded directory has omitted or extra files')
    REPORT['artifact'] = dict(identity(ARCHIVE), member_count=len(manifest), members=manifest)
    pipeline = read_json(ACTUAL/'pipeline.json')
    meta = read_json(HERE/'R5_REMOTE_RUN_METADATA_RETRIEVAL.json')['records']
    run = next(r['data'] for r in meta if r['url'].endswith('/40641230212'))
    listing = next(r['data'] for r in meta if '/artifacts?' in r['url'])
    artifact = next(x for x in listing['artifacts'] if x['id'] == 12795308068)
    need(run['id'] == 40641230212 and run['head_sha'] == HEAD and run['head_branch'] == 'evidence/full-sprint-20261028-r5', 'actual GitHub run identity differs')
    need(run['status'] == 'completed' and run['conclusion'] == 'success' and run['event'] == 'push' and run['run_attempt'] == 1, 'unexpected actual CI state')
    need(artifact['digest'] == 'sha256:'+ZIP_SHA and artifact['size_in_bytes'] == 395931 and not artifact['expired'], 'remote artifact identity differs')
    need(artifact['workflow_run']['id'] == run['id'] and artifact['workflow_run']['head_sha'] == HEAD, 'artifact belongs to another execution')
    remote = read_json(HERE/'R5_REMOTE_CURRENT_HEAD_BINDING.json')
    need(remote['commit'] == HEAD, 'retrieved source head differs')
    fetched = {x['path']:x['content'] for x in remote['files']}
    workflow = fetched['.github/workflows/r5-exterior-channel.yml'].encode()
    need({'bytes':len(workflow),'sha256':sha(workflow)} == identity(BASE/'r5-integration/r5-exterior-channel-v2.yml'), 'executed workflow differs from independently reviewed V2')
    lock_raw = fetched['engineering/engineering-followup-20261028-r5/compute/R5E_PORTABLE_SOURCE_LOCK.json'].encode()
    need(sha(lock_raw) == LOCK_SHA and lock_raw == (R5/'R5E_PORTABLE_SOURCE_LOCK.json').read_bytes(), 'HEAD source lock differs from reviewed/runtime lock')
    need(LOCK_SHA in workflow.decode() and "github.ref == 'refs/heads/evidence/full-sprint-20261028-r5'" in workflow.decode(), 'workflow does not enforce lock/ref')
    need(pipeline['environment']['github_sha'] == HEAD and pipeline['environment']['github_run_id'] == str(run['id']), 'pipeline actual HEAD/run differs')
    need(pipeline['source_commit'] == ANCHOR and pipeline['source_commit'] != HEAD, 'R4 anchor must be distinguished from actual R5 HEAD')
    need(pipeline['completed'] is True and frame_keys([{'case_id':x['label'],'frame':x['phase']} for x in pipeline['stages']]) == ORDER, 'five sequential stages incomplete')
    need(pipeline['source_root'] == REMOTE_R5 and pipeline['public_r4_root'] == REMOTE_R4, 'source roots differ')
    need(pipeline['unchanged_process_limits'] == LIMITS, 'pipeline changed original limits')
    need(all(pipeline[k] is False for k in ('native_Common_called','native_material_semantics_verified','compiled_transform_error_verified','full_continuous_G2','all_blockers_closed','original_clearance_threshold_changed','original_displacement_boxes_changed')), 'pipeline overclaims qualification')
    bound(pipeline['source_lock_identity'])
    lock = read_json(R5/'R5E_PORTABLE_SOURCE_LOCK.json')
    need(lock['source_commit'] == ANCHOR, 'source anchor changed')
    expected_sources = []
    for key, remote_root, local_root in (('r5_files',REMOTE_R5,R5),('r4_source_files',REMOTE_R4,R4)):
        for row in lock[key]:
            need(identity(local_root/row['path']) == {k:row[k] for k in ('bytes','sha256')}, 'locked source differs')
            expected_sources.append(dict(row,path=remote_root+'/'+row['path']))
    need(pipeline['actual_source_identities'] == expected_sources and len(expected_sources) == 8, 'runtime source set differs from complete source lock')
    bridge = read_json(R5/'R5E_PUBLIC_INPUT_BRIDGE.json')
    need(bridge['source_commit'] == ANCHOR and len(bridge['files']) == len({r['path'] for r in bridge['files']}) == 19, 'public bridge coverage differs')
    expected_inputs = []
    for row in bridge['files']:
        need(row['decoded_json_equal'] is True and row['changed_strings'] == [], 'public projection changed decoded values')
        path = R4/row['path']
        need(identity(path) == row['public_identity'], 'public input digest differs')
        expected_inputs.append(dict(row['public_identity'],path=REMOTE_R4+'/'+row['path']))
        if path.suffix == '.json':
            canonical = json.dumps(read_json(path),sort_keys=True,separators=(',',':')).encode()
            need(sha(canonical) == row['public_canonical_json_sha256'], 'small public JSON decoded content differs')
    need(pipeline['public_inputs'] == expected_inputs and pipeline['source_and_public_inputs_unchanged'] is True, 'runtime complete public input/postcheck differs')
    original_limits = read_json(R4/'support-v4-supervision/controller.json')['limits']
    need({k:original_limits[k] for k in LIMITS} == LIMITS, 'six gates do not match original R4 actual controller')
    REPORT['current_git_and_source_binding'] = {'actual_head':HEAD,'actual_run_id':run['id'],'artifact_id':artifact['id'],'actual_branch':run['head_branch'],'workflow_sha256':sha(workflow),'source_lock_sha256':LOCK_SHA,'R4_source_anchor':ANCHOR,'locked_sources_rehashed':8,'public_inputs_rehashed':19,'source_lock_postexecution_hash_record_present':False,'payload_source_and_input_postcheck_recorded':True,'remote_runtime_executable_reacquired':False}
    return pipeline, {r['path']:r for r in bridge['files']}


def audit_stages(pipeline):
    reports = {}
    previous_end = utc(pipeline['started_utc'])
    nonces = set()
    parents = set()
    for stage, (label, phase) in zip(pipeline['stages'], ORDER):
        paths = {key:bound(stage[key]) for key in ('contract','supervision_contract','driver_log','controller','report')}
        c, s, controller, report = (read_json(paths[key]) for key in ('contract','supervision_contract','controller','report'))
        entry = read_json(ACTUAL/(label+'-supervision')/'entry-receipt.json')
        cp, sp, output = REMOTE_OUTPUT+'/'+label+'-contract.json', REMOTE_OUTPUT+'/'+label+'-supervision-contract.json', REMOTE_OUTPUT+'/'+label
        supervisor, entry_source = REMOTE_R4+'/supervise_owned_pure_math_r4e_v2.py', REMOTE_R4+'/run_owned_pure_math_r4e_v3.py'
        worker_name = 'verify_exterior_channels_r5e_v3.py' if phase.startswith('verify_') else 'exterior_channels_r5e_v3.py'
        expected_driver = ['/usr/bin/python3','-I','-S','-B',supervisor,'--contract',sp,'--out',output+'-supervision','--','--contract',cp,'--output',output]
        expected_entry = ['/usr/bin/python3','-I','-S','-B',entry_source,'--supervision-contract',sp,'--receipt',output+'-supervision/entry-receipt.json','--','--contract',cp,'--output',output]
        need(stage['command'] == expected_driver and controller['command'] == expected_entry, 'actual stage directory/command binding differs')
        need(c['phase'] == phase and c['source_commit'] == ANCHOR, 'math contract phase/anchor mismatch')
        need(c['producer_sha256'] == identity(R5/worker_name)['sha256'], 'mathematical contract worker identity mismatch')
        need(c['capacity'] == {'wall_seconds':600,'RSS_limit_bytes':805306368,'maximum_candidate_cells':1 if phase == 'single_stationary_witness' else 1474,'maximum_static_boundary_box_tests':50000000}, 'math capacity differs')
        need(c['all_original_D_components_retained'] is True and c['original_float64_TOL_unchanged'] is True and c['current_factory_G2_qualified'] is False, 'contract changes scientific scope')
        for key in ('r4_report','r4_independent_report','r4_stationary_diagnostic','public_input_bridge','method'):
            bound(c[key])
        need({k:s[k] for k in LIMITS} == LIMITS and s['expected_output_bytes'] == LIMITS['maximum_output_bytes'] and s['zero_RSS_missing_observations_allowed'] is False, 'supervision gate changed')
        need(s['registered_math_contract_sha256'] == identity(paths['contract'])['sha256'] and controller['contract_sha256'] == identity(paths['supervision_contract'])['sha256'], 'contract hash chain broken')
        need(controller['limits'] == s and controller['source_sha256'] == s['supervisor_sha256'] == identity(R4/'supervise_owned_pure_math_r4e_v2.py')['sha256'], 'actual controller source/contract differs')
        need(s['worker_entry'] == entry_source and s['worker_entry_sha256'] == identity(R4/'run_owned_pure_math_r4e_v3.py')['sha256'], 'entry source differs')
        bound(s['owned_process']); bound(s['worker'])
        need(s['worker']['path'] == REMOTE_R5+'/'+worker_name and s['worker_output_directory'] == output and s['canonical_worker_options'] == ['--contract','--output'], 'worker path differs')
        need(entry['canonical_worker_arguments'] == ['--contract',cp,'--output',output], 'canonical worker arguments differ')
        need(entry['actual_argument_bindings'] == {'mathematical_contract_path':cp,'mathematical_contract_sha256':identity(paths['contract'])['sha256'],'worker_output_directory':output}, 'entry actual argument binding differs')
        need(all(stage[k] is True for k in ('worker_started_by_driver','completed','actual_worker_started','owned_supervisor_completed')) and stage['supervisor_exit_code'] == 0 and stage['resource_stop'] is None, 'actual driver stage incomplete')
        need(all(controller[k] is True for k in ('worker_started','completed','entry_completed','owned_child_identity_verified','owned_channel_descriptors_closed','source_and_contract_unchanged')) and controller['worker_exit_code'] == 0 and controller['resource_stop'] is None and controller['missing_RSS_zero_substitutions'] == 0 and 'failure' not in controller, 'actual owned controller failed')
        need(all(entry[k] is True for k in ('worker_started','completed','entry_and_worker_and_owned_source_unchanged')) and entry['worker_exit_code'] == 0 and entry['native_geometry_imported'] is False, 'actual owned entry failed')
        need(report['execution_completed'] is True and 'failure' not in report, 'scientific report incomplete')
        need(0 < entry['peak_RSS_bytes'] == report['peak_RSS_bytes'] <= LIMITS['RSS_limit_bytes'], 'actual entry peak invalid/exceeds original gate')
        need(0 <= report['seconds'] <= controller['elapsed_seconds'] <= LIMITS['wall_seconds'], 'actual stage time exceeded original gate')
        need(previous_end <= utc(c['registered_utc']) <= utc(controller['started_utc']) <= utc(controller['finished_utc']), 'five stage chronological registration/execution order broken')
        previous_end = utc(controller['finished_utc'])
        handshake = controller['owned_child_handshake']; packet, parent, verified = (handshake[k] for k in ('packet','parent_identity','verified_binding'))
        need(packet['kind'] == 'razr_owned_child_identity_v1' and packet['source_sha256'] == s['worker_entry_sha256'], 'handshake entry source differs')
        need(packet['stat'] == verified['stat'] and packet['status'] == verified['status'], 'handshake child PID/starttime binding differs')
        need(packet['os_getpid'] == packet['stat']['pid'] == packet['status']['Pid'] == int(packet['proc_self_visible_pid']), 'child PID receipts inconsistent')
        need(packet['os_getppid'] == packet['stat']['ppid'] == packet['status']['PPid'] == parent['os_getpid'], 'owned parent receipt differs')
        need(parent['os_getpid'] == parent['stat']['pid'] == parent['status']['Pid'] and parent['stat']['starttime_ticks'] <= packet['stat']['starttime_ticks'], 'parent PID/starttime invalid')
        need(packet['pid_namespace'] == verified['pid_namespace'] == parent['pid_namespace'] and packet['pid_for_children_namespace'] == verified['pid_for_children_namespace'], 'namespace binding differs')
        nonce = packet['nonce']; need(len(nonce) == 64 and set(nonce) <= set('0123456789abcdef') and nonce not in nonces, 'handshake nonce malformed/reused'); nonces.add(nonce)
        parents.add(parent['os_getppid'])
        need(0 < min(handshake['initial_memory'].values()) <= max(handshake['initial_memory'].values()) <= entry['peak_RSS_bytes'], 'initial owned memory invalid')
        observations = controller['observations']; first = observations[0]
        need(first['disk_available_bytes'] >= LIMITS['disk_floor_bytes'] + LIMITS['maximum_output_bytes'] + LIMITS['metadata_margin_bytes'], 'actual disk admission failed')
        need(first['shared_unreclaimable_bytes'] + LIMITS['RSS_limit_bytes'] <= LIMITS['shared_ceiling_bytes'], 'actual shared-memory admission failed')
        live = []; null_after_exit = []
        for i, row in enumerate(observations + [controller['final_resources']]):
            need(row['disk_available_bytes'] >= LIMITS['disk_floor_bytes'] and row['shared_unreclaimable_bytes'] <= LIMITS['shared_ceiling_bytes'], 'recorded runtime resource gate violation')
            if 'elapsed_seconds' in row:
                need(0 <= row['elapsed_seconds'] <= LIMITS['wall_seconds'] and 0 <= row['actual_output_bytes'] <= LIMITS['maximum_output_bytes'], 'actual persisted time/output gate violation')
                if row['owned_worker_memory'] is None:
                    need(i == len(observations)-1, 'unexpected missing intermediate owned memory')
                    null_after_exit.append(i)
                else:
                    need(0 < min(row['owned_worker_memory'].values()) <= max(row['owned_worker_memory'].values()) <= entry['peak_RSS_bytes'], 'recorded owned memory invalid')
                    live.append(row)
        output_bytes = sum(p.stat().st_size for p in (ACTUAL/label).rglob('*') if p.is_file())
        need(output_bytes <= LIMITS['maximum_output_bytes'], 'actual stage output exceeds original allowance')
        if phase.startswith('verify_'):
            bound(c['producer_report']); bound(c['producer_owned_supervision'])
            prior = 'single-stationary-witness' if phase == 'verify_single' else 'all-raw'
            need(c['producer_report'] == pipeline['stages'][0 if prior == 'single-stationary-witness' else 3]['report'], 'verifier producer report identity differs')
            need(c['verifier_sha256'] == s['worker']['sha256'] and report['producer_code_imported'] is False, 'verifier not separately bound')
            expected_names = ['omitted-complete-boundary-piece','overclaim-closed-cell-disjointness','channel-does-not-reach-known-exterior','false-separating-coordinate','missing-frame','duplicate-frame','wrong-actual-phase']
            controls = report['negative_controls'] + report['phase_coverage_negative_controls']
            need([x['name'] for x in controls] == expected_names and all(x['actual_rejected'] is True and bool(x['reason']) for x in controls), 'actual seven negative-control outcomes missing')
            need(report['expected_phase'] == c['expected_phase'] and report['expected_case_frames'] == c['expected_case_frames'], 'verifier complete phase contract differs')
        else:
            need(report['contract_sha256'] == identity(paths['contract'])['sha256'] and report['phase'] == phase and report['source_and_contract_unchanged'] is True, 'worker actual contract/postcheck mismatch')
            need(Q(report['original_TOL_exact']) == Q(1e-7), 'original binary64 tolerance altered')
            need(len(report['controls']) == 5 and all(x['passed'] is True for x in report['controls']), 'actual producer five semantic controls incomplete')
            need(all(report[k] is False for k in ('native_Common_called_or_used_as_premise','native_material_boundary_semantics_verified','compiled_curve_transform_error_verified','full_continuous_G2','all_blockers_closed')) and report['new_native_operations'] == 0, 'worker overclaims native/whole-domain qualification')
        for prior in c['completed_prerequisites']:
            bound(prior['report']); bound(prior['supervisor'])
            need(read_json(mapped(prior['report']['path']))['execution_completed'] is True and read_json(mapped(prior['supervisor']['path']))['completed'] is True, 'prerequisite incomplete')
        if phase == 'all_raw':
            bound(c['actual_capacity_basis'])
            need(c['actual_capacity_basis'] == pipeline['stages'][2]['report'], 'all-raw detached from actual capacity preflight')
        REPORT['stages'].append({'phase':phase,'label':label,'controller_sha256':identity(paths['controller'])['sha256'],'entry_receipt':identity(ACTUAL/(label+'-supervision')/'entry-receipt.json'),'controller_seconds':controller['elapsed_seconds'],'worker_seconds':report['seconds'],'entry_peak_RSS_bytes':entry['peak_RSS_bytes'],'persisted_resource_rows_including_admission':len(observations),'persisted_live_RSS_rows':len(live),'persisted_null_memory_after_exit_rows':len(null_after_exit),'initial_owned_memory':handshake['initial_memory'],'admission':first,'final_resources':controller['final_resources'],'owned_child_pid':packet['os_getpid'],'owned_child_starttime_ticks':packet['stat']['starttime_ticks'],'actual_worker_output_bytes':output_bytes,'actual_negative_control_types':7 if phase.startswith('verify_') else 0,'all_recorded_gates_satisfied':True})
        reports[label] = report
    need(previous_end <= utc(pipeline['finished_utc']) and len(parents) == 1, 'pipeline finish/common owned driver PID inconsistent')
    REPORT['original_six_gates'] = LIMITS
    REPORT['original_gate_sampling_limitation'] = 'Original monitor polls at 0.2 s and persists about 1 s rows. Two subsecond stages retain admission plus handshake and entry peak, not every live RSS sample. The null memory preflight row is the post-exit observe() record, never a zero substitute. Historic process identity is checked from receipts, not probed anew.'
    return reports


def inspect_certificate(label, row, original, original_cells, sources, independent_row, producer, controls=False):
    path = bound(row['certificate'], ACTUAL/label)
    with gzip.open(path,'rb') as f:
        payload = f.read(8*1024*1024+1)
    need(len(payload) <= 8*1024*1024, 'new certificate exceeds registered small readback budget')
    cert = json.loads(payload)
    need(cert['schema'] == 'razr-r5e-exterior-channel-cell-certificate-v1', 'certificate schema mismatch')
    need(cert['frame'] == {k:v for k,v in row.items() if k != 'certificate'}, 'certificate frame/header identity mismatch')
    cells = cert['cells']
    need(len(cells) == len(original_cells) == row['candidate_cell_count'], 'positive cell complete coverage changed')
    original_sum = removed = retained = Q(0)
    excluded = separations = blockers = 0
    for i,(cell, old) in enumerate(zip(cells, original_cells)):
        need(cell['cell_index'] == i and cell['box_exact'] == old['box_exact'], 'positive cell identity/order changed')
        box = ranges(old['box_exact']); volume = measure(box)
        need(volume == Q(old['positive_directed_volume_exact']) == Q(cell['positive_directed_volume_exact']), 'directed positive volume altered')
        original_sum += volume
        if cell['excluded_open_interior'] is True:
            separations += check_excluded(cell,box,sources)
            removed += volume; excluded += 1
            if controls and not REPORT['independent_negative_controls']:
                independent_mutations(cell,box,sources,producer)
        else:
            check_kept(cell,box,sources)
            retained += volume; blockers += 12
    need(original_sum == removed+retained == Q(row['original_disjoint_cell_sum_exact']), 'signed volume partition is not conserved')
    need(Q(row['removed_open_cell_sum_exact']) == removed and Q(row['retained_cell_sum_exact']) == retained, 'reported exact volume sums differ')
    need(row['excluded_cell_count'] == excluded and row['retained_cell_count'] == len(cells)-excluded, 'cell counts differ')
    need(row['all_cell_boundaries_retained_as_zero_volume_carriers'] is True and row['positive_cell_topology_unchanged'] is True, 'cell-boundary or topology scope changed')
    chosen = retained
    if label == 'all-raw':
        chosen = min(retained,Q(original['coarse_whole_support_upper_exact_mm3']))
        need(chosen == Q(row['selected_conditional_raw_upper_exact_mm3']) <= Q(original['conditional_complete_material_intersection_upper_exact_mm3']), 'selected upper bound exceeds unchanged original bound')
        need(original['original_min_volume_plus_TOL_gate_passed'] is True and row['original_min_volume_plus_TOL_gate_passed'] is True, 'original min-volume sanity gate not preserved')
        need(original_sum == Q(original['boundary_slab_raw_upper_exact_mm3']), 'original positive-cell sum detached from R4 slab upper')
    clearance = chosen <= Q(1e-7)
    need(row['conditional_raw_clearance_gate_passed'] is clearance, 'producer original binary64 clearance decision differs')
    need(independent_row == {'case_id':row['case_id'],'frame':row['frame'],'complete_cells':len(cells),'excluded_cells':excluded,'independently_checked_boundary_piece_separations':separations,'retained_upper_exact':str(chosen),'original_clearance_gate_passed':clearance}, 'CI independent verifier result differs from third-author exact recomputation')
    answer = {'phase':label,'case_id':row['case_id'],'frame':row['frame'],'pair':row['pair'],'complete_positive_cells':len(cells),'excluded_open_interiors':excluded,'retained_cells':len(cells)-excluded,'checked_boundary_separation_inequalities':separations,'checked_blocked_channel_intersections':blockers,'complete_boundary_piece_counts':[len(x[0]) for x in sources],'source_D_exact':row['original_remaining_displacement_box_exact'],'original_positive_cell_sum_exact':str(original_sum),'removed_open_interior_volume_exact':str(removed),'retained_volume_exact':str(retained),'selected_conditional_upper_exact':str(chosen),'selected_conditional_upper_mm3_display':float(chosen),'original_binary64_1e_7_passed':clearance,'zero_volume_closed_boundaries_retained':True,'certificate':dict(row['certificate'])}
    REPORT['certificate_reads'].append(answer)
    return answer


def audit_certificates(reports, bridge):
    baseline = read_json(R4/'support-v4/report.json')
    diagnostic = read_json(R4/'remaining-spatial-diagnostic/report.json')
    need(frame_keys(baseline['frames']) == EXPECTED and baseline['execution_completed'] is True, 'baseline original frame set changed')
    for label, phase in (('single-stationary-witness','single_stationary_witness'),('all-raw','all_raw')):
        complete_phase(reports[label], phase, [('case-001',1)] if label.startswith('single') else EXPECTED)
    need(frame_keys(reports['preflight']['frames']) == EXPECTED and reports['preflight']['phase'] == 'preflight', 'preflight full frame set changed')
    need(reports['preflight']['counters'] == {'channels_tested':0,'boundary_box_tests':0}, 'preflight claims exclusion work')
    for label, expected in (('verify-single',[('case-001',1)]),('verify-all',EXPECTED)):
        need(frame_keys(reports[label]['frames']) == expected, 'independent verifier actual frame set incomplete')
    total_cells = total_static = total_compressed = 0
    single_answer = None
    for index, original in enumerate(baseline['frames']):
        key = (original['case_id'],original['frame'])
        row = reports['all-raw']['frames'][index]
        preflight = reports['preflight']['frames'][index]
        proof_path = bound(row['source_proof'])
        bridge_row = bridge['support-v4/'+original['proof']['path']]
        need(row['original_raw_proof_identity'] == original['proof'] and bridge_row['raw_identity'] == {k:original['proof'][k] for k in ('bytes','sha256')}, 'original raw proof identity lost')
        with gzip.open(proof_path,'rb') as f:
            raw = f.read(32*1024*1024+1)
        need(len(raw) <= 32*1024*1024, 'source proof exceeds per-file readback budget')
        COUNTS['source_proofs_decoded'] += 1
        COUNTS['source_proof_raw_bytes'] += len(raw)
        COUNTS['largest_source_proof_raw_bytes'] = max(COUNTS['largest_source_proof_raw_bytes'],len(raw))
        proof = json.loads(raw); del raw
        canonical = json.dumps(proof,sort_keys=True,separators=(',',':')).encode()
        need(sha(canonical) == bridge_row['public_canonical_json_sha256'], 'decoded complete public proof hash differs')
        del canonical
        need(proof['case_id'] == key[0] and proof['frame'] == key[1] and row['pair'] == original['pair'], 'source case/frame/pair changed')
        need(proof['full_remaining_displacement_box_exact'] == original['full_remaining_displacement_box_exact'] == row['original_remaining_displacement_box_exact'], 'full original D was narrowed or altered')
        sources = original_sources(proof)
        original_cells = proof['complete_raw_boundary_slab_cover']['combined']['positive_cells']
        static = len(original_cells)*6*sum(len(x[0]) for x in sources)
        need(len(original_cells) == original['boundary_slab_positive_cell_count'] == row['candidate_cell_count'] and row['source_piece_counts'] == [len(x[0]) for x in sources], 'original complete cells/pieces changed')
        need(row['static_boundary_box_test_upper'] == static, 'frame finite capacity bound differs')
        for k in ('case_id','frame','pair','source_proof','original_raw_proof_identity','original_remaining_displacement_box_exact','source_piece_counts','candidate_cell_count','static_boundary_box_test_upper'):
            need(preflight[k] == row[k], 'actual preflight is detached from frame '+k)
        need(preflight['mathematical_exclusion_attempted'] is False, 'capacity preflight overclaims exclusion')
        answer = inspect_certificate('all-raw',row,original,original_cells,sources,reports['verify-all']['frames'][index],reports['all-raw'],controls=True)
        need(Q(proof['complete_raw_boundary_slab_cover']['combined']['sum_directed_volume_exact']) == Q(answer['original_positive_cell_sum_exact']), 'source combined sum differs')
        total_cells += len(original_cells); total_static += static; total_compressed += identity(proof_path)['bytes']
        if key == ('case-001',1):
            single_row = reports['single-stationary-witness']['frames'][0]
            witness = next(r for r in diagnostic['rows'] if (r['case_id'],r['frame']) == key)['zero_displacement_spatial_cover_witness']
            one = [{'box_exact':witness['stationary_enclosure_positive_cell_exact'],'positive_directed_volume_exact':witness['stationary_enclosure_cell_volume_exact']}]
            need(single_row['original_remaining_displacement_box_exact'] == original['full_remaining_displacement_box_exact'] and single_row['original_raw_proof_identity'] == original['proof'], 'stationary witness lost original D/source provenance')
            need(single_row['source_proof'] == row['source_proof'], 'single witness source proof differs')
            single_answer = inspect_certificate('single-stationary-witness',single_row,original,one,original_sources(proof,stationary=True),reports['verify-single']['frames'][0],reports['single-stationary-witness'])
            need(single_answer['excluded_open_interiors'] == 1 and single_answer['selected_conditional_upper_exact'] == '0', 'single stationary witness was not removed')
        del proof, sources, original_cells
        gc.collect()
    need(total_cells == 1474 and total_static == 11452692 and total_compressed == 20506080, 'actual preflight capacity baseline differs')
    for label in ('preflight','all-raw'):
        r = reports[label]
        need(r['total_candidate_cells'] == total_cells and r['static_boundary_box_test_upper'] == total_static and r['static_coordinate_comparison_upper'] == total_static*3 and r['total_original_compressed_proof_bytes'] == total_compressed, 'actual total finite preflight basis differs')
    all_answers = [r for r in REPORT['certificate_reads'] if r['phase'] == 'all-raw']
    passed = sum(r['original_binary64_1e_7_passed'] for r in all_answers)
    need(passed == reports['all-raw']['conditional_clearance_passes'] == reports['verify-all']['conditional_clearance_passes'] == 4, 'actual all16 original clearance count differs')
    need(reports['single-stationary-witness']['conditional_clearance_passes'] == reports['verify-single']['conditional_clearance_passes'] == 1, 'single witness pass count differs')
    need(reports['preflight']['conditional_clearance_passes'] == 0, 'preflight masquerades as clearance pass')
    REPORT['result'] = {'actual_full_frame_count':len(all_answers),'actual_full_conditional_clearance_passes':passed,'actual_full_unresolved_frames':16-passed,'single_stationary_positive_cell_removed':True,'single_stationary_original_volume_exact':single_answer['original_positive_cell_sum_exact'],'single_stationary_post_exclusion_upper_exact':'0','original_binary64_TOL_exact':str(Q(1e-7)),'total_original_positive_cells':total_cells,'full_excluded_open_interiors':sum(r['excluded_open_interiors'] for r in all_answers),'full_retained_cells':sum(r['retained_cells'] for r in all_answers),'static_boundary_box_tests_upper':total_static,'source_gzip_bytes':total_compressed,'actual_remote_negative_control_types':7,'actual_remote_negative_control_stage_runs':2,'actual_remote_negative_control_rejections':14,'third_author_independent_negative_control_rejections':len(REPORT['independent_negative_controls']),'audit_pass_means_all_reviewed_records_and_exact_predicates_agree':True,'audit_pass_does_not_mean_full_G2_or_16_frame_clearance':True}


def main():
    start = time.monotonic()
    REPORT['started_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    registration = read_json(REGISTRATION)
    def time_exceeded(signum,frame):
        raise TimeoutError('independent readback registered wall budget exceeded')
    signal.signal(signal.SIGALRM,time_exceeded)
    signal.alarm(registration['wall_seconds'])
    resource.setrlimit(resource.RLIMIT_AS,(registration['address_space_limit_bytes'],registration['address_space_limit_bytes']))
    try:
        need(identity(__file__) == registration['audit_source_identity'], 'audit source changed after budget registration')
        need(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0, 'registered isolated audit invocation required')
        REPORT['registration_identity'] = identity(REGISTRATION)
        REPORT['audit_source_identity'] = identity(__file__)
        pipeline, bridge = audit_archive_and_binding()
        reports = audit_stages(pipeline)
        audit_certificates(reports,bridge)
        need(pipeline['actual_frame_count'] == 16 and pipeline['conditional_raw_clearance_passes'] == pipeline['independent_conditional_raw_clearance_passes'] == 4, 'pipeline final result mismatch')
        REPORT['actual_remote_pipeline_seconds'] = pipeline['elapsed_seconds']
        REPORT['limitations'] = [
            'This is independent post-run exact certificate/record readback, not new CI execution or native Common/CAD execution.',
            'Underlying complete R4 boundary covers, their relation to native material, and compiled transformation/rounding semantics remain premises; the large supporting R4 algorithm proofs are not re-executed here.',
            'Seven negative-control types were actually rejected in each of two remote verifier stages. The independent local seven mutations above are separately counted.',
            'A removed open interior retains its closed faces as zero-volume carriers. Kept cells and twelve unresolved frames are upper-bound uncertainty, not proved material collision.',
            'Original driver hashes every payload source/input again at completion. The source-lock metadata file itself has a startup identity but no separate end-of-run hash receipt.',
            'Remote Python executable identity is recorded by CI; this audit does not reacquire or independently attest the historical runtime binary.',
            'The successful job exercised the normal five-stage path. Fail-stop branch behavior is covered by bound source review, not claimed as a newly injected CI failure experiment.'
        ]
        REPORT['audit_completed'] = True
    except BaseException as exc:
        REPORT['failure'] = {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        signal.alarm(0)
        REPORT['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        REPORT['audit_seconds'] = time.monotonic()-start
        REPORT['audit_peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        REPORT['counts'] = COUNTS
        REPORT['local_readback_budget_respected'] = REPORT['audit_seconds'] <= registration['wall_seconds'] and REPORT['audit_peak_RSS_bytes'] <= registration['RSS_limit_bytes']
        data = (json.dumps(REPORT,indent=2,ensure_ascii=False)+'\n').encode()
        if len(data) > registration['maximum_output_bytes']:
            REPORT['audit_completed'] = False
            REPORT['output_budget_failed'] = True
            REPORT['artifact'].pop('members',None)
            data = (json.dumps(REPORT,indent=2,ensure_ascii=False)+'\n').encode()
        OUTPUT.write_bytes(data)
        print(json.dumps({k:REPORT.get(k) for k in ('audit_completed','audit_seconds','audit_peak_RSS_bytes','local_readback_budget_respected','result','failure')},ensure_ascii=False))
    return 0 if REPORT['audit_completed'] and REPORT['local_readback_budget_respected'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
