"""Pure independent record/hash audit of all seventy L3 native cases.

Uses the immutable original static postguard.  No CAD is imported; BREP bytes
are hashed, while their reported native signatures are checked as records.
"""
from pathlib import Path
import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import io
import json
import math
import subprocess
import sys
import tarfile
import zipfile

S4='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline-repo',type=Path,required=True)
    ap.add_argument('--original-archive',type=Path,required=True)
    ap.add_argument('--source-dir',type=Path,required=True)
    ap.add_argument('--zip',action='append',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();root=args.baseline_repo
    for rel in ('tools/validate_product_nominal_report.py','integration/cam_contact_profile.py'):
        assert (root/rel).read_bytes()==subprocess.check_output(['git','show',S4+':'+rel],cwd=root)
    sys.path[:0]=[str(root/'tools'),str(root/'integration')]
    import validate_product_nominal_report as guard
    from cam_contact_profile import ContactProfile
    binding=json.loads((args.source_dir/'L3_BINDING.json').read_text())
    profile_path=root/'engineering/thin-mechanism-20261015/native-verification.json.gz'
    profile_bytes=profile_path.read_bytes()
    assert profile_bytes==subprocess.check_output(['git','show',S4+':'+str(profile_path.relative_to(root))],cwd=root)
    profile_data=json.loads(gzip.decompress(profile_bytes))
    profiles={}
    for side in 'LR':
        for index,saved in enumerate(profile_data['sides'][side]['contacts']):
            profiles[side,index]=ContactProfile(**{k:saved['profile'][k] for k in ContactProfile.__dataclass_fields__})
    original={}
    with tarfile.open(args.original_archive,'r:gz') as arc:
        for shard,meta in binding['shards'].items():
            member=next(m for m in arc.getmembers() if Path(m.name).name=='c2-slide-L1-'+shard+'-40210275856-1.zip')
            with zipfile.ZipFile(io.BytesIO(arc.extractfile(member).read())) as z:
                for case in meta['cases']:
                    path='run/'+case+'/result.json';data=z.read(path)
                    assert sha(data)==meta['members'][path]['sha256'];original[case]=data
    rows=[];artifacts=[];negative=[];rounding=[];total_breps=0
    for path in args.zip:
        with zipfile.ZipFile(path) as z:
            manifest=json.loads(z.read('MANIFEST.json'))
            assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(manifest)|{'MANIFEST.json'}
            for name,m in manifest.items():
                data=z.read(name);assert len(data)==m['bytes'] and sha(data)==m['sha256']
            report=json.loads(z.read('report.json'));controller=json.loads(z.read('CONTROLLER_OUTCOME.json'))
            assert report['native_profile_source']['sha256']==sha(profile_bytes)
            for name in ('correlated_v3.py','replay_l3.py','supervise_l3.py','L3_BINDING.json'):
                assert z.read(name)==(args.source_dir/name).read_bytes()
            for flag in ('all_11781_pairs_reexecuted','full_continuous_domain_clear','physical_qualification',
                         'candidate_go','fixture_fabrication_go','manufacturing_go','original_results_replaced','independent_CAD_kernel'):
                assert report[flag] is False
            expected=binding['shards'][report['shard']]['cases']
            declared=report['case_results']
            assert len(declared)==len({r['case_id'] for r in declared})
            if report['execution_completed']:assert {r['case_id'] for r in declared}==set(expected)
            artifacts.append({'local_zip':str(path.resolve()),'zip_sha256':sha(path.read_bytes()),
                'all_member_sizes_and_hashes_verified':True,'member_count':len(manifest),'shard':report['shard'],
                'execution_completed':report['execution_completed'],'seconds':report['seconds'],
                'peak_RSS_bytes':report['peak_RSS_bytes'],'controller':controller})
            for summary in declared:
                case=summary['case_id'];raw=z.read(case+'.json');assert sha(raw)==summary['result_sha256']
                e=json.loads(raw);o=json.loads(original[case]);t=o['target'];spec=t['specification']
                assert e['original_result_sha256']==sha(original[case]) and e['original_specification']==spec
                assert e['original_q_interval_exact']==t['q_interval_exact']
                assert [e['a'],e['b']]==[t['a'],t['b']]
                for mat in e['material_readbacks']:
                    old=next(m for m in o['material_exports'] if any(r['role']==mat['role'] for r in m['references']))
                    for fmt in ('brep','step'):
                        assert mat[fmt+'_sha256']==old['exports'][fmt]['sha256']
                    assert 0<=mat['BREP_minus_STEP_mm3']<=1e-7 and 0<=mat['STEP_minus_BREP_mm3']<=1e-7
                exports=e['exported_scientific_material'];total_breps+=len(exports)
                assert len({r['path'] for r in exports})==len(exports)
                assert {r['path'] for r in exports}=={n for n in z.namelist() if n.startswith(case+'-') and n.endswith('.brep')}
                for exported in exports:
                    data=z.read(exported['path']);assert sha(data)==exported['sha256'] and len(data)==exported['bytes']
                    sig=exported['signature'];assert sig['is_valid'] and sig['signed_volume_mm3']>0
                    assert all(math.isfinite(v) and v>0 for v in sig['solid_signed_volumes_mm3'])
                r=e['new_result'];audit=e['method_audit'];checks=[]
                def visit(value):
                    if isinstance(value,dict):
                        if 'original_static_carrier_postguard_record' in value:
                            record=value['original_static_carrier_postguard_record'];guard.validate_frame(record)
                            common=value['strict_common']['common_mm3'];assert math.isfinite(common) and common>=0
                            assert common==record.get('common_upper_bound_mm3',record.get('examined_region_common_sum_mm3'))
                            checks.append(common)
                        for child in value.values():visit(child)
                    elif isinstance(value,list):
                        for child in value:visit(child)
                visit(r)
                side=audit['original_profile_side'];index=audit['original_profile_index'];profile=profiles[side,index]
                assert audit['original_source_profile']==json.loads(json.dumps(profile.receipt()))
                lo,hi=map(lambda x:float(Fraction(x)),t['q_interval_exact']);hmin,hmax=profile.height_bounds(lo,hi);home=profile.evaluate(0.)[0]
                record={'case_id':case,'shard':report['shard'],'pair':[e['a'],e['b']],
                    'original_q_interval_exact':t['q_interval_exact'],'new_disposition':r['disposition'],
                    'method':r['method'],'common_upper_bound_mm3':r['common_upper_bound_mm3'],
                    'static_original_postguard_records_independently_checked':len(checks),
                    'whole_BREP_exports_hashed':len(exports),'case_report_sha256':sha(raw)}
                if r['method']=='whole_STOP_pin_and_remainder_correlated_contact_path':
                    assert len(exports)==16 and len(r['carrier_checks'])==4
                    assert spec['parameter_intervals']==[[lo,hi],[hmin-home,hmax-home]]
                    sums={frame:math.fsum(c[frame+'_frame']['strict_common']['common_mm3'] for c in r['carrier_checks']) for frame in ('contact','phone')}
                    assert sums==r['frame_common_sums_mm3'] and max(sums.values())==r['common_upper_bound_mm3']
                    g=r['whole_STOP_decomposition']
                    assert abs(g['full_pin_volume_mm3']+g['remainder_volume_mm3']-g['native_STOP_volume_mm3'])<=1e-7
                    assert abs(math.fsum(c['source_piece_volume_mm3'] for c in r['remainder_carrier_constructions'])-g['remainder_volume_mm3'])<=1e-7
                    alignment=r['profile_alignment_to_actual_whole_STOP'];pp=alignment['path_profile'];native=alignment['native_extracted_profile']
                    qshift,rshift=alignment['source_graph_shift_qr_mm']
                    assert qshift==native['pin_q']-profile.pin_q and rshift==g['native_pin_center_qr'][1]-home
                    assert pp['pin_radius']==native['pin_radius']==profile.pin_radius
                    aligned=ContactProfile(**{k:pp[k] for k in ContactProfile.__dataclass_fields__})
                    qs={0.,12.,lo,hi,(lo+hi)/2,*profile.breakpoints,*aligned.breakpoints}
                    residuals=[{'q_mm':q,'relative_height_difference_mm':(aligned.evaluate(q)[0]-g['native_pin_center_qr'][1])-(profile.evaluate(q)[0]-home)} for q in sorted(qs)]
                    maximum=max(abs(v['relative_height_difference_mm']) for v in residuals);rounding.append(maximum)
                    record.update(covered_q_interval_mm=r['covered_q_interval_mm'],frame_sums_mm3=sums,
                                  profile_graph_shift_qr_mm=[qshift,rshift],
                                  source_vs_aligned_relative_height_finite_differences=residuals,
                                  profile_float_crosschecks_are_not_continuous_certificate=True)
                    assert r['full_independent_product_domain_or_dynamic_branch_selection_proved'] is False
                else:
                    assert len(exports)==13 and len(r['finite_crosschecks'])==3
                    desc=spec['fixed'];assert desc['profile_height_bounds_mm']==[hmin,hmax] and desc['profile_home_height_mm']==home
                    sign=-1 if side=='L' else 1;delta=sign*(hmin-home);base=desc['base_bounds_mm']
                    endpoints=[base[0]-delta,base[1]] if side=='L' else [base[0],base[1]-delta]
                    assert r['nesting']['relative_cylinder_X_endpoints_mm']==endpoints
                    assert r['nesting']['STOP_X_displacement_at_q_high_mm']==delta
                    assert r['common_upper_bound_mm3']==r['static_carrier_check']['strict_common']['common_mm3']
                    for sample in r['finite_crosschecks']:
                        assert 0<=sample['whole_relative_cylinder_outside_mm3']<=1e-7
                        assert sample['whole_actual_pair_common']['strict_common']['common_mm3']<=r['common_upper_bound_mm3']+1e-7
                    record['nesting']=r['nesting'];assert r['physical_spring_wire_force_fatigue_qualification'] is False
                nv=r['negative_control']['strict_common']['common_mm3'];assert nv>1e-7;negative.append(nv)
                assert (r['common_upper_bound_mm3']<=1e-7)==(r['disposition']=='clear')
                assert e['unchanged_original_postguards_passed'] is True
                record['negative_control_positive_Common_mm3']=nv;rows.append(record)
    assert len(rows)==len({r['case_id'] for r in rows})
    result={'schema':'razr-L3-independent-record-audit-v1','archives':artifacts,'case_count':len(rows),
        'expected_original_correlated_cases':70,'all_70_present':len(rows)==70,
        'new_disposition_counts':dict(Counter(r['new_disposition'] for r in rows)),
        'method_counts':dict(Counter(r['method'] for r in rows)),
        'whole_BREP_exports_hashed':total_breps,'source_profile_input_sha256':sha(profile_bytes),
        'negative_control_Common_range_mm3':[min(negative),max(negative)],
        'maximum_finite_profile_translation_roundoff_mm':max(rounding),
        'cases':sorted(rows,key=lambda x:x['case_id']),
        'geometric_operations_reexecuted_by_this_reader':False,
        'BREP_shapes_reimported_by_this_reader':False,'independent_CAD_kernel':False,
        'formal_directed_rounding_or_full_dynamic_domain_proved':False,
        'scope':'New nominal correlated set construction on original whole bodies. Static original postguards do not certify the nonlinear dynamic domain; all full-domain, force, manufacturing and physical flags remain false.'}
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['case_count','all_70_present','new_disposition_counts','method_counts','whole_BREP_exports_hashed','negative_control_Common_range_mm3','maximum_finite_profile_translation_roundoff_mm']},indent=2))


if __name__=='__main__':main()
