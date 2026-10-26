"""Independent non-CAD readback of L2 scientific ZIPs and original L1 records.

Checks artifact member hashes, original identities, unchanged report guard,
signed values and summed Common accounting.  It never recomputes geometry or
turns a carrier overlap into a whole-body collision witness.
"""
from pathlib import Path
import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
import subprocess
import sys
import tarfile
import zipfile

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def family(case):
    n=int(case.split('-')[-1])
    if n in (1,6,28,37,54,63,72,89):return 'original_tiny_nonzero_displacement_error'
    if 11<=n<=15:return 'original_negative_prism_signed_volume_error'
    if n==16:return 'original_unsupported_generated_EXTRUSION_error'
    if 17<=n<=19:return 'original_invalid_Common_upper_bound_error'
    if n in (2,3,4,5,7,8,9,10):return 'original_panel_KEY_conservative_overlap'
    return 'original_correlated_contact_independent_box_overlap'


def frames(row):
    yield row
    for key in ('initial_reference_frame_result','opposite_reference_frame_result'):
        if key in row:yield from frames(row[key])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline-repo',type=Path,required=True)
    ap.add_argument('--original-dir',type=Path,required=True)
    ap.add_argument('--original-archive',type=Path,required=True)
    ap.add_argument('--binding',type=Path,required=True)
    ap.add_argument('--zip',action='append',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    guard_path=args.baseline_repo/'tools/validate_product_nominal_report.py'
    old=subprocess.check_output(['git','show',S4+':tools/validate_product_nominal_report.py'],cwd=args.baseline_repo)
    assert guard_path.read_bytes()==old
    sys.path.insert(0,str(args.baseline_repo/'tools'))
    import validate_product_nominal_report as guard
    binding=json.loads(args.binding.read_text())
    archive_hash=hashlib.sha256()
    with args.original_archive.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):archive_hash.update(chunk)
    assert archive_hash.hexdigest()=='58128815aaeee9e9b2ddc2b983f3499bab4b22788bc447c55e037a24016da39a'
    original_records={}
    with tarfile.open(args.original_archive,'r:gz') as arc:
        for shard,meta in binding['shards'].items():
            member=next(m for m in arc.getmembers() if Path(m.name).name=='c2-slide-L1-'+shard+'-40210275856-1.zip')
            with zipfile.ZipFile(io.BytesIO(arc.extractfile(member).read())) as source:
                for case in meta['cases']:
                    path='run/'+case+'/result.json';data=source.read(path)
                    assert sha(data)==meta['members'][path]['sha256']
                    original_records[case]=data
    rows=[];archives=[];families=defaultdict(Counter)
    for zip_path in args.zip:
        with zipfile.ZipFile(zip_path) as z:
            manifest=json.loads(z.read('MANIFEST.json'))
            assert len(z.namelist())==len(set(z.namelist()))
            assert set(z.namelist())==set(manifest)|{'MANIFEST.json'}
            for name,m in manifest.items():
                data=z.read(name)
                assert len(data)==m['bytes'] and sha(data)==m['sha256'],name
            report=json.loads(z.read('report.json'));shard=report['shard'];bound=binding['shards'][shard]
            controller=json.loads(z.read('CONTROLLER_OUTCOME.json'))
            for source_name in ('envelope_v2.py','replay_l2.py','supervise_l2.py','test_l2_native.py','L2_BINDING.json'):
                assert z.read(source_name)==(args.binding.parent/source_name).read_bytes(),source_name
            for flag in ('all_11781_pairs_reexecuted','full_continuous_domain_clear',
                         'physical_qualification','candidate_go','fixture_fabrication_go',
                         'manufacturing_go','original_results_replaced','independent_CAD_kernel'):
                assert report[flag] is False,flag
            declared=report['case_results']
            assert len({r['case_id'] for r in declared})==len(declared)
            if report['execution_completed']:assert {r['case_id'] for r in declared}==set(bound['cases'])
            artifact={'local_zip':str(zip_path.resolve()),'zip_sha256':sha(zip_path.read_bytes()),
                      'member_count':len(manifest),'all_member_sizes_and_hashes_verified':True,
                      'shard':shard,'report':{k:report.get(k) for k in
                          ['execution_completed','new_disposition_counts','new_method_native_controls',
                           'all_unchanged_original_postguards_passed','seconds','peak_RSS_bytes','failure']},
                      'controller':controller}
            archives.append(artifact)
            for summary in declared:
                name=summary['case_id'];raw=z.read(name+'.json');assert sha(raw)==summary['result_sha256']
                entry=json.loads(raw);original_bytes=original_records[name]
                assert sha(original_bytes)==entry['original_result_sha256']
                original=json.loads(original_bytes);target=original['target']
                # The local inspection copies were JSON formatted on extraction;
                # require semantic equality, while byte identity comes from the
                # unchanged archived original and immutable binding above.
                assert json.loads((args.original_dir/name/'result.json').read_text())==original
                assert entry['original_specification']==target['specification']
                assert entry['original_disposition']==original['current_original_aggregate_disposition']
                assert entry['original_q_interval_exact']==target['q_interval_exact']
                assert [entry['a'],entry['b']]==[target['a'],target['b']]
                for material in entry['material_readbacks']:
                    om=next(m for m in original['material_exports'] if any(r['role']==material['role'] for r in m['references']))
                    for fmt in ('brep','step'):
                        assert material[fmt+'_sha256']==om['exports'][fmt]['sha256']
                        sig=material[fmt+'_signature']
                        assert sig['is_valid'] and math.isfinite(sig['signed_volume_mm3']) and sig['signed_volume_mm3']>0
                        assert sig['solid_signed_volumes_mm3'] and all(v>0 and math.isfinite(v) for v in sig['solid_signed_volumes_mm3'])
                    assert 0<=material['BREP_minus_STEP_mm3']<=1e-7 and 0<=material['STEP_minus_BREP_mm3']<=1e-7
                result=entry['new_result'];guard_error=None
                try:guard.validate_frame(result)
                except Exception as exc:guard_error=type(exc).__name__+': '+str(exc)
                assert (guard_error is None)==entry['unchanged_original_postguard_passed']
                frame_rows=[];surface_types=Counter();carrier_methods=Counter();rejected_prisms=[];face_volumes=[]
                for frame in frames(result):
                    checks=frame.get('v2_region_checks',[])
                    if checks:
                        values=[r['common_mm3'] for r in checks]
                        assert all(v>=0 and math.isfinite(v) for v in values)
                        upper=math.fsum(values)
                        assert upper==frame.get('common_upper_bound_mm3',frame.get('examined_region_common_sum_mm3'))
                    else:upper=None
                    frame_rows.append({'disposition':frame['disposition'],'summed_Common_mm3':upper,
                        'regions_checked':len(checks),'error':frame.get('error')})
                    for audit in frame.get('v2_carrier_audit',[]):
                        for face in audit['faces']:
                            surface_types[face['surface_type']]+=1;carrier_methods[face['method']]+=1
                            volume=face['signed_volume_mm3'];assert math.isfinite(volume) and volume>0;face_volumes.append(volume)
                            if 'native_prism_rejected' in face:rejected_prisms.append(face['native_prism_rejected'])
                retained=[]
                for m in entry.get('material_retention',[]):
                    carrier=m['carrier'];assert sha(z.read(carrier['path']))==carrier['sha256']
                    cs=carrier['signature'];assert cs['is_valid'] and all(v>0 for v in cs['solid_signed_volumes_mm3'])
                    common=m.get('recomputed_native_Common');common_value=None
                    if common:
                        assert sha(z.read(common['path']))==common['sha256']
                        sig=common['signature'];common_value=sig['signed_volume_mm3']
                        if 'strict_common' in m:
                            assert sig['is_valid'] and all(v>0 for v in sig['solid_signed_volumes_mm3'])
                            assert abs(common_value-m['strict_common']['common_mm3'])<=1e-7
                            fixed_index=1 if m['frame']=='initial' else 0
                            fixed_volume=entry['material_readbacks'][fixed_index]['brep_signature']['signed_volume_mm3']
                            assert 0<=common_value<=min(cs['signed_volume_mm3'],fixed_volume)+1e-7
                    retained.append({'frame':m['frame'],'carrier_path':carrier['path'],
                                     'carrier_sha256':carrier['sha256'],'carrier_signed_volume_mm3':cs['signed_volume_mm3'],
                                     'followup_Common_signed_volume_mm3':common_value,
                                     'followup_failure':m.get('followup_Common_failure')})
                kind=family(name);families[kind][result['disposition']]+=1
                rows.append({'case_id':name,'shard':shard,'family':kind,'pair':[entry['a'],entry['b']],
                    'q_interval_exact':target['q_interval_exact'],'original_disposition':entry['original_disposition'],
                    'new_disposition':result['disposition'],'independent_original_postguard_passed':guard_error is None,
                    'independent_postguard_error':guard_error,'frames':frame_rows,
                    'recorded_surface_types':dict(surface_types),'recorded_carrier_methods':dict(carrier_methods),
                    'recorded_face_carrier_signed_volume_range_mm3':[min(face_volumes),max(face_volumes)] if face_volumes else None,
                    'rejected_native_prisms_retained':rejected_prisms,'retained_examined_materials':retained,
                    'case_report_sha256':sha(raw)})
    assert len({r['case_id'] for r in rows})==len(rows)
    result={'schema':'razr-L2-independent-scientific-record-readback-v1','archives':archives,
        'case_count':len(rows),'expected_original_cases':89,'all_89_present':len(rows)==89,
        'original_archive_sha256':archive_hash.hexdigest(),
        'original_JSON_raw_bytes_verified_from_retained_archive':True,
        'local_formatted_original_JSON_semantically_equal':True,
        'unchanged_original_postguard_source_sha256':sha(old),
        'disposition_counts':dict(Counter(r['new_disposition'] for r in rows)),
        'family_counts':{k:dict(v) for k,v in families.items()},'cases':sorted(rows,key=lambda x:x['case_id']),
        'geometric_operations_reexecuted_by_this_reader':False,'independent_CAD_kernel':False,
        'formal_continuous_containment_certificate':False,
        'whole_body_collision_proved_from_carrier_overlap':False,
        'EXTRUSION_branch_tested_directly':any(r['recorded_surface_types'].get('EXTRUSION',0)>0 for r in rows),
        'scope':'Saved original whole pair domains only. A numerical clear on an epsilon interval is not full panel/KEY travel clearance. Original whole-domain material interference remains independent evidence.'}
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['case_count','all_89_present','disposition_counts','family_counts','EXTRUSION_branch_tested_directly']},indent=2))


if __name__=='__main__':main()
