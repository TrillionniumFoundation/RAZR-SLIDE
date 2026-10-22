#!/usr/bin/env python3
"""Independent EP5 STEP and pair-inventory readback.

Imports only the frozen EP3 metric reader, never assembly/routing generators.
Count/volume/bounds round trips are explicitly not full source material
equivalence, manufacturing tolerance, or continuous obstacle qualification.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
import math
import re
from pathlib import Path
import sys
import traceback

HELPER = 'engineering/product-integration-20261018/phase3-20261020/read_ep3_step_independent.py'
HELPER_SHA = '14b2aa3362aba950a39244b0130021b72231fa2866e15d96e2f34a6dac6798c5'
TOLERANCE = {'bounds_mm':1e-6,'absolute_volume_mm3':1e-6,'relative_volume':1e-9}
EXPECTED = {'STOW':154,'PREDOCK':154,'OPEN':161}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)



ENDPOINT_PART_NAMES = (
    'M1_board_head_1','M1_board_head_2','M1_board_head_3','M1_board_head_4',
    'M1_board_shaft_1','M1_board_shaft_2','M1_board_shaft_3','M1_board_shaft_4',
    'M2_clamp_head_1','M2_clamp_head_2','M2_clamp_screw_1','M2_clamp_screw_2',
    'inner_carrier_jaw','mated_BM28_reservation','mini_DP_PCB','mini_DS_PCB',
    'outer_stiffener_jaw','static_26wire_transfer_reservation','stiffener','tail')
CANDIDATE_NAMES = {'EP5_finite_material'}|{end+'_'+name for end in ('A','B') for name in ENDPOINT_PART_NAMES}
REQUIRED_SOURCE_ROLES = (
    'integration/product_routing_ep5.py','design/product_routing_ep5.json',
    'integration/product_routing_ep4.py','integration/product_fpc.py',
    'integration/product_interfaces.py','design/product_routing_ep4.json',
    'integration/product_assembly.py','design/product_geometry.json',
    'integration/oled_storage.py')

def finite_nonnegative(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0

def validate_native_header(native):
    require(isinstance(native,dict),'native report object required')
    require(native.get('schema') in ('razr-ep5-full-pair-native-v1','razr-ep5-local-motion-native-v1'),
            'wrong native manifest schema')
    require(native.get('native_checks_executed') is True,'native checks were not executed')
    require(native.get('source_bytes_unchanged') is True,'native source check incomplete')
    poses = native.get('selected_poses')
    require(isinstance(poses,list) and poses and all(type(p) is str and p in EXPECTED for p in poses)
            and len(set(poses))==len(poses),'nonempty unique legal selected poses required')
    records = native.get('poses')
    require(isinstance(records,list) and all(isinstance(p,dict) for p in records)
            and [p.get('pose') for p in records]==poses,'pose selection differs')
    sources = native.get('source_sha256')
    require(isinstance(sources,dict) and sources,'nonempty executed source identity required')
    require(all(type(k) is str and type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for k,v in sources.items()),
            'invalid source identity entry')
    for key in ('candidate_go','fixture_fabrication_go','manufacturing_go'):
        require(native.get(key) is False,'research native report granted a release')
    return native['schema']=='razr-ep5-local-motion-native-v1'

def validate_pair_rows(matrix, parts):
    rows = matrix.get('rows')
    require(isinstance(rows,list),'complete native pair rows required')
    native_calls = 0
    for row in rows:
        require(not row.get('evaluation_failed') and not row.get('diagnostic_artifact_failure'),
                'native Boolean or diagnostic evaluation failed')
        value = row.get('common_mm3')
        require(finite_nonnegative(value),'finite nonnegative Common volume required')
        first,second = parts[row['a']],parts[row['b']]
        require(value<=min(first['volume_mm3'],second['volume_mm3'])+1e-7,'Common exceeds complete source material')
        require(row.get('rejected') is (value>1e-7),'Common rejection flag inconsistent')
        require(row.get('a_bounds_mm')==first['bounds_mm'] and row.get('b_bounds_mm')==second['bounds_mm'],
                'pair geometry bounds differ from complete assembly')
        method = row.get('method')
        if method=='native_Common':
            native_calls += 1
            n = row.get('common_positive_solids')
            require(type(n) is int and n>=0 and (n>0)==(value>0),'native positive Common solid count inconsistent')
        elif method=='cached_native_geometry_bounds_positive_axis_gap':
            a,b=first['bounds_mm'],second['bounds_mm']
            gap=max(max(a[2*i]-b[2*i+1],b[2*i]-a[2*i+1]) for i in range(3))
            reported=row.get('axis_gap_lower_mm')
            require(finite_nonnegative(reported) and reported>1e-7 and abs(reported-gap)<1e-9
                    and value==0.,'unjustified broad-phase Common omission')
        else:
            raise ValueError('unknown or unevaluated native pair method')
    failures = [r for r in rows if r['rejected']]
    require(matrix.get('failures')==failures,'pair failures inventory inconsistent')
    require(matrix.get('native_Common_calls')==native_calls
            and matrix.get('cached_axis_gap_rejections_of_intersection')==len(rows)-native_calls,
            'pair evaluation coverage counters inconsistent')
    require(matrix.get('positive_Common_count_including_below_tolerance')==sum(r['common_mm3']>0 for r in rows),
            'positive Common count inconsistent')
    require(matrix.get('rejection_volume_tolerance_mm3')==1e-7,'native rejection tolerance changed')
    require(matrix.get('no_Common_above_tolerance_or_evaluation_error') is (not failures),
            'pair completion or rejection summary inconsistent')

def validate_containment(contained,parts,local_only):
    rows=contained.get('rows')
    require(isinstance(rows,list),'containment row list required')
    if local_only:
        require(rows==[] and contained.get('executed') is False,'local containment must remain explicitly unexecuted')
        return
    require(contained.get('parts')==41 and len(rows)==41
            and {r.get('part') for r in rows}==CANDIDATE_NAMES,'full candidate containment inventory incomplete')
    for row in rows:
        require(not row.get('evaluation_failed'),'native containment evaluation failed')
        value=row.get('outside_outer_union_mm3')
        require(finite_nonnegative(value) and value<=parts[row['part']]['volume_mm3']+1e-7,
                'finite physically bounded outside volume required')
        require(type(row.get('native_domain_cuts_executed')) is int and row['native_domain_cuts_executed'] in (1,2),
                'native domain cut coverage invalid')
        require(row.get('validated_empty_result') is (value==0.)
                and row.get('rejected') is (value>1e-7),'containment result flags inconsistent')
        require(value==0. or row.get('outside_material'),'positive outside material lacks native export')
    failures=[r for r in rows if r['rejected']]
    require(contained.get('failures')==failures
            and contained.get('all_material_inside_optimistic_outer_union') is (not failures),
            'containment summary inconsistent')


def validate_declared_input_roles(native, expected):
    """An explicit complete data-role inventory is mandatory in current reports."""
    require(native.get('input_closure_schema')=='razr-ep5-native-input-closure-v1',
            'missing or unsupported native input closure schema')
    require(type(native.get('declared_input_roles')) is dict
            and native['declared_input_roles']==expected,
            'native declared input role inventory differs')
    digest=native.get('input_closure_helper_sha256')
    require(isinstance(digest,str) and len(digest)==64 and all(x in '0123456789abcdef' for x in digest),
            'native input closure helper identity missing')


def execute(manifest_path, repository_root, output):
    root = Path(repository_root).resolve(); manifest_path = Path(manifest_path).resolve()
    artifact_root = manifest_path.parent; output = Path(output).resolve()
    require(not output.exists(),'new output required')
    output.mkdir(parents=True)
    helper_path = root/HELPER
    require(sha(helper_path)==HELPER_SHA,'independent helper source changed')
    spec = importlib.util.spec_from_file_location('ep5_frozen_metric_reader',helper_path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    result = {'schema':'razr-ep5-independent-step-readback-v1',
        'started_UTC':datetime.now(timezone.utc).isoformat(),'runtime':helper.versions(),
        'reader_sha256':sha(__file__),'helper_sha256':sha(helper_path),
        'native_report_sha256':sha(manifest_path),'poses':[],'failures':[],
        'execution_completed':False,'declared_readback_checks_passed':False,
        'geometry_generator_modules_imported':False,'independent_process_from_generator':True,
        'full_source_material_equivalence_proved':False,'STEP_label_identity_proved':False,
        'continuous_interference_clearance_proved':False,'tolerance_is_not_manufacturing_tolerance':True,
        'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
    tracked = {str(path):sha(path) for path in (Path(__file__),helper_path,manifest_path)}
    try:
        native = json.loads(manifest_path.read_text())
        local_only = validate_native_header(native)
        result['scope'] = '46-part local research scene only' if local_only else 'complete phone at selected finite poses'
        result['selected_poses'] = native['selected_poses']
        result['all_three_finite_poses_included'] = set(native['selected_poses'])==set(EXPECTED)
        stage_root = Path(__file__).resolve().parents[3]
        required_roles = REQUIRED_SOURCE_ROLES+('integration/ep5_input_closure.py',)+(('integration/product_split_assembly.py',) if not local_only else ())
        available = {Path(name).resolve() for name in native['source_sha256']}
        for role in required_roles:
            require(any((base/role).resolve() in available for base in (root,stage_root)),
                    'required executed source role missing: '+role)
        closure_paths=[(base/'integration/ep5_input_closure.py').resolve() for base in (stage_root,root)]
        closure_path=next((p for p in closure_paths if p in available),None)
        require(closure_path is not None and closure_path.is_file(), 'native closure helper unavailable')
        require(native['source_sha256'].get(str(closure_path))==sha(closure_path)
                ==native.get('input_closure_helper_sha256'), 'native closure helper bytes differ')
        closure_spec=importlib.util.spec_from_file_location('ep5_declared_input_closure',closure_path)
        closure=importlib.util.module_from_spec(closure_spec);closure_spec.loader.exec_module(closure)
        verified = native.get('verified_mounted_members_before')
        roles=closure.native_input_roles('local' if local_only else 'full',verified is not None)
        validate_declared_input_roles(native,roles)
        for relative in roles:
            path=(root/relative).resolve()
            require(path in available and path.is_file() and native['source_sha256'].get(str(path))==sha(path),
                    'required data role was not pinned before execution: '+relative)
        result['input_closure_schema']=closure.SCHEMA
        result['declared_input_roles']=roles
        result['input_closure_helper_sha256']=sha(closure_path)
        external_allowed = set()
        if verified is not None:
            validator_path=root/'integration/verified_native_members.py'
            require(validator_path.resolve() in available
                    and native['source_sha256'].get(str(validator_path.resolve()))==sha(validator_path),
                    'verified member input validator source identity missing')
            vs=importlib.util.spec_from_file_location('ep5_input_identity_validator',validator_path)
            validator=importlib.util.module_from_spec(vs);vs.loader.exec_module(validator)
            observed=validator.verify_mounted_members(verified['directory'],root)
            require(verified==observed==native.get('verified_mounted_members_after'),
                    'executed original member identities differ at independent readback')
            external_allowed={Path(name).resolve() for name in observed['source_sha256']}
            result['verified_original_member_input_rechecked'] = observed
        for name,digest in native['source_sha256'].items():
            path = Path(name).resolve()
            require(path.is_relative_to(root) or path.is_relative_to(stage_root) or path in external_allowed,'source input outside declared roots')
            require(path.is_file() and sha(path)==digest,'executed native source identity differs: '+name)
            tracked[str(path)] = digest
        def local_path(base,relative):
            require(isinstance(relative,str) and not Path(relative).is_absolute(),'relative export path required')
            path = (base/relative).resolve()
            require(path.is_file() and path.is_relative_to(artifact_root),'missing or escaped native export')
            return path
        def read(metadata,expected,base):
            path = local_path(base,metadata['file'])
            require(sha(path)==metadata['sha256'],'native export bytes differ')
            _,_,record = helper.read_file(path,len(expected))
            matching = helper.match_recorded_metrics(expected,record['flat_solids'],TOLERANCE)
            require(record['flat_solid_count_matches'] and record['all_flat_solids_valid_positive'],
                    'native root/leaf validity or positive solid count differs')
            require(matching['recorded_objects_all_matched_injectively'] and not matching['unassigned_observed_indices'],
                    'incomplete or noninjective exported native metric inventory')
            tracked[str(path)] = sha(path)
            return {'file':str(path.relative_to(artifact_root)),'sha256':tracked[str(path)],
                'flat_solids':len(record['flat_solids']),'metric_comparison':matching}
        for pose in native['poses']:
            label = pose['pose']; expected = 46 if local_only else EXPECTED[label]; names = set(pose['parts'])
            require(len(names)==expected==pose['combined_participants'],'complete pose inventory differs')
            require(CANDIDATE_NAMES<=names,'complete candidate role inventory differs')
            require(pose['candidate_participants']==41 and pose['external_participants']==expected-41,
                    'candidate or external participant inventory differs')
            assembly = read(pose['complete_assembly_STEP'],pose['parts'],artifact_root)
            matrix = pose['complete_pair_matrix']
            validate_pair_rows(matrix,pose['parts'])
            validate_containment(pose['containment'],pose['parts'],local_only)
            pairs = [tuple(sorted((row['a'],row['b']))) for row in matrix['rows']]
            required_pairs = set(itertools.combinations(sorted(names),2))
            require(len(pairs)==len(set(pairs))==matrix['pair_count']==expected*(expected-1)//2,
                    'pair count contains omission or duplicate')
            require(set(pairs)==required_pairs,'unordered full pair inventory differs')
            base = artifact_root/label/'all-pairs'; positive = []
            for row in matrix['rows']:
                require(not row.get('evaluation_failed'),'native Boolean evaluation failed')
                if row.get('common_mm3',0.) <= 0:continue
                require(row.get('common_material') and row.get('common_artifact_directory'),'positive Common lacks export')
                folder_name = row['common_artifact_directory']
                require(Path(folder_name).name==folder_name,'escaped Common folder')
                folder = base/folder_name; metadata = row['common_material']
                common = read(metadata,{str(i):v for i,v in enumerate(metadata['solids'])},folder)
                context = row['local_material_context']; crop_metrics = {}
                require(context['margin_each_face_mm']==2.,'Common context margin differs')
                for item in context['parts']:
                    require(not item.get('crop_evaluation_failed'),'Common context native evaluation failed')
                    require(item['actual_local_wall_thickness_mm'] is None and item['thickness_inferred_from_bounds'] is False,
                            'unmeasured wall was relabelled as qualified')
                    for index,metric in enumerate(item.get('crop_solids',[])):
                        crop_metrics[item['part']+'/'+str(index)] = metric
                require(crop_metrics and context['neighborhood_STEP'],'positive Common lacks complete neighborhood')
                neighborhood = read(context['neighborhood_STEP'],crop_metrics,folder)
                positive.append({'a':row['a'],'b':row['b'],'common':common,'neighborhood':neighborhood})
            outside = []
            for row in pose['containment']['rows']:
                if row.get('outside_material'):
                    metadata = row['outside_material']
                    outside.append(read(metadata,{str(i):v for i,v in enumerate(metadata['solids'])},
                                        artifact_root/label/'outside-domain'))
            result['poses'].append({'pose':label,'assembly':assembly,'full_pair_count':len(pairs),
                'all_pairs_present_once':True,'positive_Common_exports':positive,'outside_exports':outside})
        forbidden = [name for name in sys.modules if name.startswith(('product_routing_','product_assembly','product_split_assembly'))]
        require(not forbidden,'geometry generator imported into independent reader')
        require(all(Path(path).is_file() and sha(path)==digest for path,digest in tracked.items()),
                'readback inputs changed during execution')
        result['execution_completed'] = True
        result['declared_readback_checks_passed'] = True
    except Exception as exc:
        result['failures'].append(type(exc).__name__+': '+str(exc))
        result['exception_traceback'] = traceback.format_exc()
    result['retained_input_sha256'] = tracked
    result['finished_UTC'] = datetime.now(timezone.utc).isoformat()
    (output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--repository-root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args(); report = execute(args.manifest,args.repository_root,args.output)
    print(json.dumps({k:report[k] for k in ('execution_completed','declared_readback_checks_passed','failures')}))
    raise SystemExit(0 if report['declared_readback_checks_passed'] else 1)
