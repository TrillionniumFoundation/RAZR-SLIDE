"""Bind the executed R13 conditional proof, its reviews and all retained variants."""
from pathlib import Path
from fractions import Fraction as F
import datetime,gzip,hashlib,json
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((ROOT/n).read_text())
def ref(n):
    p=ROOT/n;return {'path':n,'bytes':p.stat().st_size,'sha256':sha(p)}
def readz(n):
    with gzip.open(ROOT/n,'rt') as f:return json.load(f)
def main():
    scope_path=ROOT/'R13_ENVELOPE_SCOPE.json';manifest_path=ROOT/'R13_ENVELOPE_DELIVERY_MANIFEST.json'
    assert not scope_path.exists() and not manifest_path.exists(),'already sealed'
    native=read('native-attempt1/report.json');producer=read('producer-attempt1/report.json')
    cert=read('producer-attempt1/complete_trim_corridors.json')
    review=read('independent-review/R13_TRIM_INDEPENDENT_REVIEW.json')
    controls=read('independent-review/trim-negative-controls/report.json')
    assert native['completed'] and producer['completed'] and review['completed'] and controls['all_replayed_rejections']
    for report,name in ((native,'extract_wire_semantics_r13.py'),(producer,'produce_trim_corridors_r13.py')):
        assert report['source']['sha256']==sha(ROOT/name)
        assert report['capacity_basis']['sha256']==sha(ROOT/'ALGORITHM_AND_CAPACITY.md')
    assert producer['model_source']['sha256']==sha(ROOT/'completion_model_r13.py')
    assert producer['model_definition']['sha256']==sha(ROOT/'COMPLETION_MODEL_DEFINITION.md')
    assert producer['native_report']['sha256']==sha(ROOT/'native-attempt1/report.json')
    assert producer['complete_trim_corridors']['sha256']==sha(ROOT/'producer-attempt1/complete_trim_corridors.json')
    assert native['input']['sha256']==sha(ROOT/'inputs/A_BACK_PANEL.brep')
    for row in read('inputs/INPUT_MANIFEST.json')['files']:
        assert (ROOT/'inputs'/row['path']).stat().st_size==row['bytes'] and sha(ROOT/'inputs'/row['path'])==row['sha256']
    assert review['source_sha256']==sha(ROOT/'independent-review/audit_r13_trim_independently.py')
    assert controls['source_sha256']==sha(ROOT/'independent-review/preserve_trim_negative_controls.py')
    assert controls['checker_sha256']==review['source_sha256']
    assert controls['original_independent_review_sha256']==sha(ROOT/'independent-review/R13_TRIM_INDEPENDENT_REVIEW.json')
    assert controls['seed_native_report_sha256']==sha(ROOT/'native-attempt1/report.json')
    assert controls['seed_corridors_sha256']==sha(ROOT/'producer-attempt1/complete_trim_corridors.json')
    assert len(controls['complete_variants'])==len(review['negative_controls'])==8
    assert all(x['rejected'] for x in review['negative_controls'])
    for row in controls['complete_variants']:
        path=ROOT/'independent-review'/row['complete_variant_file']
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'] and row['replay']['rejected']
    assert review['producer_or_model_helpers_imported'] is False and review['sqrt_helper_imported'] is False
    for key in ('native_material_belongs_to_B0_and_T_proved','existence_of_full_global_native_material_realizing_B0_and_T_proved',
                'uniform_compiled_error_proved','actual_collision_proved','full_15D_G2','physical_allowed_domain','G3','G4','G5'):
        assert review['scope'][key] is False
    pairs=[];gaps=[];total_boxes=positive_boxes=new_boxes=trim_queries=0
    for index,key in enumerate(('L_KEY','R_KEY')):
        row=producer['pairs'][index];checked=review['pairs'][index]
        assert row['key']==checked['key']==key and row['B0_and_T_upper_exact']==checked['conditional_B0_and_T_exact']
        assert row['R12_B0_only_upper_exact']==checked['unchanged_R12_B0_only_exact']
        assert F(row['B0_and_T_upper_exact'])>0 and F(row['B0_and_T_upper_exact'])<=F(1e-7)<F(row['R12_B0_only_upper_exact'])
        assert row['all_original_positive_boxes']==checked['positive_boxes'] and row['counts']==checked['counts']
        ledger=readz('producer-attempt1/'+key+'-completed-trim-ledger.json.gz')
        assert sha(ROOT/'producer-attempt1'/f'{key}-completed-trim-ledger.json.gz')==checked['ledger_sha256']
        assert len(ledger['original_positive_boxes'])==row['all_original_positive_boxes']
        for b in ledger['original_positive_boxes']:
            if b['kind']=='new_panel_completed_trim_exterior':
                witnesses=b['all_298_complete_face_witnesses'];assert len(witnesses)==298 and sorted(w['face_index'] for w in witnesses)==list(range(298))
                for w in witnesses:
                    if w['method']!='original_complete_support':
                        assert w['total_winding']==0;trim_queries+=1
                        for wire in w['wires']:
                            gaps += [F(s['strict_gap_exact']) for s in wire['all_complete_edge_corridors_strictly_outside_query']]
        total_boxes+=row['all_original_positive_boxes'];positive_boxes+=row['counts']['retained_positive_full_box'];new_boxes+=row['counts']['new_panel_completed_trim_exterior']
        pairs.append({'key':key,'nominal_only_q_exact':['0','12'],'complete_original_positive_boxes':row['all_original_positive_boxes'],
            'inherited_KEY_exterior_boxes':row['counts']['inherited_KEY_exterior'],'new_panel_conditional_exterior_boxes':row['counts']['new_panel_completed_trim_exterior'],
            'retained_full_positive_boxes':row['counts']['retained_positive_full_box'],
            'unchanged_B0_only_upper_exact_mm3':row['R12_B0_only_upper_exact'],'unchanged_B0_only_upper_approx_mm3':row['R12_B0_only_upper_approx_mm3'],
            'new_B0_and_T_upper_exact_mm3':row['B0_and_T_upper_exact'],'new_B0_and_T_upper_approx_mm3':row['B0_and_T_upper_approx_mm3'],
            'original_threshold_passes_only_under_B0_and_T':True})
    assert total_boxes==169 and positive_boxes==157 and new_boxes==8 and trim_queries==12 and min(gaps)>0
    joins=[j for face in cert['faces'] for w in face['wires'] for j in w['joins']]
    assert len(joins)==48 and sum(any(F(x)!=0 for x in j['original_exact_pcurve_gap']) for j in joins)==44
    scope={'schema':'razr-r13-completed-trim-conditional-envelope-scope-v1','sealed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'classification':'new exact conditional B0 AND T bound; original B0-only bound and actual native qualification blockers retained',
        'premises':{'B0':'unchanged R12 complete serialized boundary support contains the complete compact material boundary',
                    'T':'six complete oriented trim fillings obey the explicitly bounded continuous completion-corridor family and declared face-coordinate displacement model'},
        'native_original_BREP_mutated':False,'native_endpoints_snapped_or_healed':False,
        'native_faces':6,'native_ordered_wires':12,'native_complete_edges':48,'native_common_vertex_joins':48,'native_vertex_endpoint_checks':96,
        'original_nonzero_exact_endpoint_joins_preserved':44,'pairs':pairs,
        'all_original_positive_boxes_accounted':169,'retained_full_positive_boxes':157,'new_complete_panel_exterior_boxes':8,
        'complete_trim_query_face_certificates':12,'minimum_query_to_complete_corridor_gap_exact_mm':str(min(gaps)),
        'minimum_query_to_complete_corridor_gap_approx_mm':float(min(gaps)),
        'independent_reconstruction_verified':True,'independent_helpers_shared':False,'actual_negative_control_variants_replayed_and_rejected':8,
        'original_float64_threshold_exact':str(F(1e-7)),'original_split_limit':4096,'original_depth_limit':24,'new_splits':0,'new_depth':0,
        'old_B0_only_bound_replaced':False,'local_reference_completion_loops_constructed':True,
        'actual_native_B0_membership_proved':False,'actual_native_T_membership_proved':False,
        'existence_of_full_global_actual_native_material_realizing_B0_and_T_proved':False,
        'recorded_native_tolerance_is_uniform_compiled_error_bound':False,'uniform_compiled_error_proved':False,
        'fixed_version_OCCT_source_binary_equivalence_proved':False,'current_native_aperture_proved_by_literal_source_context':False,
        'actual_collision_proved':False,'physical_allowed_domain_proved':False,'continuous_G2':False,'whole_15D_G2':False,
        'G3':False,'G4':False,'G5':False,'manufacturing_go':False,
        'native_failure_attempts_this_round':0,'unavailable_official_fixed_version_URL_requests_retained':8,
        'scientific_reports':[ref(n) for n in ('native-attempt1/report.json','producer-attempt1/report.json','producer-attempt1/complete_trim_corridors.json',
            'SOURCE_GUIDE_CONTEXT.json','OFFICIAL_SOURCE_RETRIEVAL.json','independent-review/R13_TRIM_INDEPENDENT_REVIEW.json','independent-review/trim-negative-controls/report.json')],
        'model_and_frontier':[ref(n) for n in ('ALGORITHM_AND_CAPACITY.md','COMPLETION_MODEL_DEFINITION.md','MODEL_MEMBERSHIP_FRONTIER.md')],
        'seal_source':ref('seal_r13_envelope.py')}
    scope_path.write_text(json.dumps(scope,indent=2)+'\n')
    files=[]
    for p in sorted(ROOT.rglob('*')):
        assert not p.is_symlink(),'archive must not contain symlinks'
        if p.is_file() and p!=manifest_path:
            assert '__pycache__' not in p.parts,'exclude reproducible bytecode caches before sealing'
            files.append(ref(p.relative_to(ROOT).as_posix()))
    manifest={'schema':'razr-r13-complete-trim-delivery-manifest-v1','file_count_excluding_self':len(files),'bytes_excluding_self':sum(x['bytes'] for x in files),
              'scope_sha256':sha(scope_path),'files':files,'native_or_physical_qualification_release':False}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    assert all((ROOT/r['path']).stat().st_size==r['bytes'] and sha(ROOT/r['path'])==r['sha256'] for r in files)
    print(json.dumps({'file_count_excluding_self':len(files),'bytes_excluding_self':manifest['bytes_excluding_self'],
                      'scope_sha256':sha(scope_path),'manifest_sha256':sha(manifest_path),'new_conditional_upper_mm3':[p['new_B0_and_T_upper_approx_mm3'] for p in pairs],
                      'actual_native_G2':False}))

if __name__=='__main__':main()
