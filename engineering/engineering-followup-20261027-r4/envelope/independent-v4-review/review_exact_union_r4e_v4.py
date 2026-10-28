"""Narrow independent V4 union-run and affine-cell readback; no producer rerun."""
from pathlib import Path
from fractions import Fraction as F
import datetime as dt
import gzip
import hashlib
import json
import time


def identity(path):
    with Path(path).open('rb') as stream:
        return {'bytes': Path(path).stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def box(value):
    return tuple(tuple(map(F, axis)) for axis in value)


def volume(value):
    result = F(1)
    for a, b in value:
        if a >= b:
            return F(0)
        result *= b-a
    return result


def main():
    started = time.monotonic()
    root = Path(__file__).resolve().parents[1]
    out = Path(__file__).resolve().parent
    frozen = {}
    def read(path):
        path = Path(path); frozen[str(path)] = identity(path)
        return json.loads(path.read_text())
    result = {'schema':'razr-r4e-independent-v4-exact-union-and-affine-cell-review-v1',
              'recorded_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'reviewer':'/root/r4_real_sources',
              'source_identity':identity(__file__), 'frames':[], 'completed':False,
              'producer_reruns':0, 'full_verifier_reruns':0, 'native_geometry_runs':0,
              'historical_execution_requalified':False, 'native_boundary_semantics_verified':False,
              'compiled_error_bound_verified':False, 'full_continuous_G2':False, 'physical_qualification':False}
    produced = read(root/'support-v4/report.json')
    verified = read(root/'independent-support-v4/report.json')
    contract = read(root/'R4E_SUPPORT_CONTRACT_V4.json')
    verification_contract = read(root/'R4E_INDEPENDENT_VERIFICATION_CONTRACT_V2.json')
    for path, expected in [(root/'slab_enclosure_r4e_v4.py',contract['slab_module_sha256']),
                           (root/'run_independent_support_r4e_v4.py',contract['producer_sha256']),
                           (root/'verify_exact_material_bounds_r4e_v2.py',verification_contract['verifier_sha256'])]:
        frozen[str(path)] = identity(path); require(frozen[str(path)]['sha256']==expected,'Reviewed source registration')
    require(produced['execution_completed'] and verified['execution_completed'] and len(produced['frames'])==len(verified['frames'])==16,'Actual producer/verifier not complete16')
    checked = {(row['case_id'],row['frame']):row for row in verified['frames']}
    require(len(checked)==16,'Duplicate verifier frame')
    cover_count=0;run_count=0;cell_count=0;fine_count=0
    for frame in produced['frames']:
        key=frame['case_id'],frame['frame']; peer=checked[key]
        path=root/'support-v4'/frame['proof']['path']; frozen[str(path)]=identity(path)
        require(frozen[str(path)]=={k:frame['proof'][k] for k in ('bytes','sha256')},'Compressed certificate binding')
        proof=json.loads(gzip.decompress(path.read_bytes()))
        rows=[]
        for name in ('complete_raw_boundary_slab_cover','complete_declared_tolerance_boundary_slab_cover','complete_whole_self_boundary_slab_negative_control'):
            cover=proof[name]; combined=cover['combined']; cover_count+=1
            if not volume(box(cover['global_intersection_box_exact'])):
                require(not combined['positive_cells'] and F(combined['sum_directed_volume_exact'])==0,'Lower-dimensional domain positive volume')
                rows.append({'name':name,'lower_dimensional_or_empty_domain':True,'fine_boxes':0,'merged_runs':0,'positive_cells':0});continue
            require(len(cover['axis_covers'])==3 and len(combined['exact_positive_slab_box_union_runs'])==3,'Three covers required')
            runs=[];current_fine=0;current_runs=0
            for axis,axis_cover in enumerate(cover['axis_covers']):
                require(axis_cover['axis']==axis and axis_cover['cut_planes_retained_as_zero_volume_closed_carriers'],'Original cut plane carrier missing')
                cuts=list(map(F,axis_cover['cuts_exact']));require(all(a<b for a,b in zip(cuts,cuts[1:])),'Cut ordering')
                fine={}
                for i,row in enumerate(axis_cover['all_open_slab_records']):
                    require(row['index']==i and list(map(F,row['open_interval_exact']))==cuts[i:i+2],'Original fine interval changed')
                    if F(row['volume_exact'])>0:
                        region=box(row['intersection_outer_box_exact']);require(volume(region)==F(row['volume_exact']),'Fine box volume')
                        fine[i]=region
                seen=[];actual=[]
                for i,run in enumerate(combined['exact_positive_slab_box_union_runs'][axis]):
                    require(run['axis']==axis and run['run_index']==i,'Run identity')
                    ids=run['fine_slab_indices'];require(ids and ids==sorted(set(ids)),'Run fine indices')
                    members=[fine[j] for j in ids]
                    require(all(members[j][axis][1]==members[j+1][axis][0] for j in range(len(members)-1)),'Positive width gap merged')
                    require(all(all(m[k]==members[0][k] for k in range(3) if k!=axis) for m in members),'Transverse ranges differ')
                    expected=list(members[0]);expected[axis]=members[0][axis][0],members[-1][axis][1]
                    require(box(run['box_exact'])==tuple(expected),'Run is not exact original union')
                    actual.append(tuple(expected));seen.extend(ids)
                require(seen==sorted(fine),'Fine positive boxes omitted/duplicated')
                require(all(a[axis][1]<=b[axis][0] for a,b in zip(actual,actual[1:])),'Run axis interiors overlap or order invalid for bisect')
                require(len(fine)==combined['fine_positive_box_counts'][axis] and len(actual)==combined['merged_positive_box_counts'][axis],'Counts changed')
                runs.append(actual);current_fine+=len(fine);current_runs+=len(actual)
            keys=set();total=F(0)
            for cell in combined['positive_cells']:
                indices=tuple(cell['slab_run_index_xyz']);require(len(indices)==3 and indices not in keys,'Duplicate or malformed cell')
                keys.add(indices);source=[runs[k][indices[k]] for k in range(3)]
                expected=tuple((max(x[k][0] for x in source),min(x[k][1] for x in source)) for k in range(3))
                require(box(cell['box_exact'])==expected,'Cell does not equal run intersection')
                widths=[b-a for a,b in expected]
                require(all(w>0 for w in widths) and list(map(F,cell['affine_diagonal_exact']))==widths,'Injective positive diagonal affine map')
                value=volume(expected);require(value==F(cell['positive_directed_volume_exact']),'Affine determinant/directed cell volume')
                total+=value
            require(len(keys)==combined['positive_cell_count'] and total==F(combined['sum_directed_volume_exact']),'Stored cells sum')
            require(combined['all_fine_boundary_cuts_retained'] and combined['all_partition_boundary_planes_retained'] and combined['zero_volume_boundary_planes_not_discarded'],'Zero-dimensional-volume carriers lost')
            current_cells=len(keys);run_count+=current_runs;cell_count+=current_cells;fine_count+=current_fine
            rows.append({'name':name,'fine_boxes':current_fine,'merged_runs':current_runs,'positive_cells':current_cells,'all_exact_unions_and_positive_affine_maps_checked':True,'recorded_sum_exact':str(total)})
        raw=F(frame['conditional_complete_material_intersection_upper_exact_mm3']);diagnostic=F(frame['declared_tolerance_diagnostic_upper_exact_mm3'])
        require(raw==F(peer['raw_bound_exact_mm3']) and diagnostic==F(peer['declared_tolerance_bound_exact_mm3']),'Producer/verifier exact values differ')
        require(frame['original_clearance_gate_passed']==peer['original_clearance_gate_passed']==(raw<=F(1e-7)),'Raw criterion differs')
        require(frame['declared_tolerance_diagnostic_gate_passed']==peer['declared_tolerance_gate_passed']==(diagnostic<=F(1e-7)),'L2 diagnostic criterion differs')
        result['frames'].append({'case_id':key[0],'frame':key[1],'covers':rows,'raw_upper_exact_mm3':str(raw),
            'original_clearance_gate_passed':frame['original_clearance_gate_passed'],
            'original_min_volume_plus_TOL_gate_passed':frame['original_min_volume_plus_TOL_gate_passed'],
            'declared_L2_diagnostic_gate_passed':frame['declared_tolerance_diagnostic_gate_passed']})
    controllers=[]
    for label,contract_name in [('support-v4','R4E_SUPPORT_SUPERVISION_V4_OWNED.json'),('independent-support-v4','R4E_INDEPENDENT_VERIFICATION_SUPERVISION_V2.json')]:
        supervisor_contract=read(root/contract_name);controller=read(root/(label+'-supervision')/'controller.json');entry=read(root/(label+'-supervision')/'entry-receipt.json')
        require(controller['completed'] and controller['worker_exit_code']==0 and controller['resource_stop'] is None and entry['completed'],'Actual supervised run not successful')
        require(entry['peak_RSS_bytes']<=805306368 and controller['elapsed_seconds']<=600,'Original wall/RSS gate')
        require(entry['actual_argument_bindings']['mathematical_contract_sha256']==supervisor_contract['registered_math_contract_sha256'],'Actual bound contract')
        require(Path(entry['actual_argument_bindings']['worker_output_directory'])==Path(supervisor_contract['worker_output_directory']),'Actual bound output')
        require(all(supervisor_contract[k]==v for k,v in {'wall_seconds':600,'RSS_limit_bytes':805306368,'shared_ceiling_bytes':7301444403,'disk_floor_bytes':104857600,'maximum_output_bytes':41943040}.items()),'Original numeric limits changed')
        controllers.append({'phase':label,'actual_controller_seconds':controller['elapsed_seconds'],'actual_peak_RSS_bytes':entry['peak_RSS_bytes'],'canonical_contract_output_bound':True,'completed':True})
    result['actual_supervision']=controllers
    result['original_min_volume_plus_TOL_gate_passes']=sum(x['original_min_volume_plus_TOL_gate_passed'] for x in result['frames'])
    result['original_clearance_passes']=sum(x['original_clearance_gate_passed'] for x in result['frames'])
    result['original_clearance_failures']=16-result['original_clearance_passes']
    result['declared_L2_diagnostic_passes']=sum(x['declared_L2_diagnostic_gate_passed'] for x in result['frames'])
    require((result['original_min_volume_plus_TOL_gate_passes'],result['original_clearance_passes'],result['declared_L2_diagnostic_passes'])==(16,4,0),'V4 original gates count')
    result['legacy_aggregate_field_interpretation']={'field':'conditional_upper_bound_gate_failures','actual_value':produced['conditional_upper_bound_gate_failures'],'counts':'clearance failures, NOT min(volume)+TOL upper-limit failures','min_volume_gate_failures':0}
    final_v3=read(root/'support-v3-supervision/controller.json')
    require(final_v3['completed'] is False and final_v3['resource_stop']=='wall_seconds' and final_v3['worker_exit_code']!=0,'V3 capacity failure not retained')
    result['V3_final_actual_failure']={k:final_v3[k] for k in ('completed','worker_exit_code','resource_stop','elapsed_seconds','failure')}
    result['actual_union_review_counts']={'covers':cover_count,'fine_positive_boxes':fine_count,'merged_runs':run_count,'positive_cells':cell_count}
    result['separate_verifier_scope']='Existing independent implementation exhaustively enumerated all X/Y/Z run triples without producer bisect; this review checks its frozen successful receipt plus every emitted exact union and positive affine cell, without rerunning exhaustive enumeration.'
    require(all(identity(p)==value for p,value in frozen.items()),'Input changed during review')
    require(identity(__file__)==result['source_identity'],'Review source changed')
    result['input_identities']=[{'path':p,**value} for p,value in frozen.items()]
    result['completed']=True;result['elapsed_seconds']=time.monotonic()-started
    target=out/'R4E_V4_EXACT_UNION_AND_ACTUAL_RESULTS_INDEPENDENT_REVIEW.json';target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report':str(target),'identity':identity(target),'completed':True,'seconds':result['elapsed_seconds'],'counts':result['actual_union_review_counts'],'upper_clearance_diagnostic_passes':[16,4,0]}),flush=True)


if __name__=='__main__':main()
