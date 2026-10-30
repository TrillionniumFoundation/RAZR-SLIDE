"""Build a hash-bound scope projection without changing any executed evidence."""
import hashlib
import gzip
import json
import os
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

HERE=Path(__file__).resolve().parent


def identity(path):
    path=Path(path)
    return {'path':os.path.relpath(path,HERE),'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def read(relative):
    return json.loads((HERE/relative).read_text())


def main():
    producer=read('cylinder-slab-all16-attempt1/report.json')
    reader=read('independent-cylinder-slab-all16-attempt1/report.json')
    assert producer['execution_completed'] and producer['recorded_budget_passed'] and producer['seconds']<=600
    assert reader['completed'] and producer['conditional_pass_count']==reader['conditional_pass_count']==16
    terminal_counts=Counter();terminal_bounds={};per_frame_terminal=[]
    for frame in producer['frames']:
        path=HERE/'cylinder-slab-all16-attempt1'/Path(frame['proof']['path']).name
        with gzip.open(path,'rt') as stream:proof=json.load(stream)
        counts=Counter();bounds={}
        for root in proof['roots']:
            for node in root['nodes']:
                if node['kind']!='leaf':continue
                kind=node['observation']['kind'];value=F(node['bound_exact'])
                counts[kind]+=1;bounds[kind]=bounds.get(kind,F(0))+value
                terminal_counts[kind]+=1;terminal_bounds[kind]=terminal_bounds.get(kind,F(0))+value
        assert sum(bounds.values(),F(0))==F(frame['intersection_upper_bound_exact'])
        per_frame_terminal.append({'case_id':frame['case_id'],'frame':frame['frame'],'counts':counts,
                                   'upper_bound_contributions_exact':{k:str(v) for k,v in bounds.items()}})
    inherit=HERE/'inherited-native-source-scopes'
    matrix=read('inherited-native-source-scopes/R3E_ORIGINAL_FAILURE_MATRIX.json')
    binding=read('inherited-native-source-scopes/R9_INHERITED_FILE_BINDINGS.json')
    input_binding=read('inherited-native-source-scopes/R3E_INPUT_BINDING.json')
    requirements=[]
    definitions=[
        ('temporary_prism_topology_and_directed_volume','nonpositive signed solid',
         'Inherited exact oriented rational carriers from the complete original source face; carrier topology, orientation and directed volume independently checked.',
         'No new native prism was built or qualified in R9. The original negative native signed volume and failed positive-material guard remain.',False),
        ('common_upper_bound','invalid signed common volume',
         'Inherited complete A-material boundary carrier upper bounds; the impossible original Common C is not used as an acceptance upper bound.',
         'No native Boolean set-correctness theorem or repaired native Common result is qualified in R9. The original min-volume-plus-TOL failures remain.',False),
        ('extrusion','unsupported advancing surface EXTRUSION',
         'Inherited complete affine-trim oblique rational sweep carriers in four actual displacement cases; original EXTRUSION source retained.',
         'General EXTRUSION support, a new native swept BREP and uniform compiled-transform error remain unqualified.',False),
        ('tiny_displacement_and_correlated_envelope','finite nonzero displacement required',
         'New R9 all-original-root rational cylinder/slab upper bounds pass all sixteen original frames, independently read back under unchanged limits and exact original float64 threshold.',
         'The complete coherent material boundary, native carrier inclusion/filling, compiled transform/B-spline semantics and full mechanical domain remain premises. R9 does not use an observed base Common as its bound.',True),
    ]
    for name,error,conditional,remaining,new in definitions:
        cases=[c for c in matrix['cases'] if c['original_error']==error]
        ids=sorted({c['case_id'] for c in cases})
        requirements.append({'requirement':name,'original_error':error,'original_event_count':len(cases),'case_ids':ids,
                             'original_case_result_files':[identity(inherit/'original-case-results'/case/'result.json') for case in ids],
                             'original_failure_matrix':identity(inherit/'R3E_ORIGINAL_FAILURE_MATRIX.json'),
                             'conditional_source_model_result':conditional,'r9_new_full_computation':new,
                             'r9_new_native_prism_common_or_extrusion_execution':False,
                             'original_failures_preserved':True,'native_obligation_closed':False,
                             'remaining_obligation':remaining,'inherited_case_outcomes':cases})
    history=[]
    for stem in ('balanced','gradient','cylinder-slab'):
        report=read(stem+'-all16-attempt1/report.json')
        checked=read('independent-'+stem+'-all16-attempt1/report.json')
        history.append({'strategy':stem,'producer_report':identity(HERE/(stem+'-all16-attempt1/report.json')),
                        'reader_report':identity(HERE/('independent-'+stem+'-all16-attempt1/report.json')),
                        'original_frame_gate_passes':report['conditional_pass_count'],
                        'global_splits':report['global_splits'],'producer_seconds':report['seconds'],
                        'reader_seconds':checked['seconds'],'all_16_gate_passed':report['conditional_pass_count']==16,
                        'producer_original_budget_success_is_not_native_qualification':True})
    prepared=['SELECTED_CYLINDER_SLAB_BASIS.md','selected_cylinder_slab_r9.py','check_selected_cylinder_slab_r9.py',
              'original_input_cache_r9.py','selected_cylinder_slab_pilot_r9.py','selected_cylinder_slab_all16_r9.py',
              'read_selected_cylinder_slab_all16_r9.py']
    scope={
        'schema':'razr-r9-envelope-final-scope-and-l1-obligations',
        'accepted_result':'16/16 original fixed frames pass the original conditional serialized-source volume gate',
        'full_native_envelope_qualified':False,'full_continuous_G2':False,'physical_domain_qualified':False,
        'G3_pass':False,'G4_pass':False,'G5_pass':False,'release_go':False,
        'producer_report':identity(HERE/'cylinder-slab-all16-attempt1/report.json'),
        'independent_report':identity(HERE/'independent-cylinder-slab-all16-attempt1/report.json'),
        'exact_original_threshold':producer['original_TOL_exact'],'original_tiny_threshold':producer['original_tiny_exact'],
        'original_limits':producer['limits'],'original_root_count':sum(f['root_count'] for f in producer['frames']),
        'all_positive_tiny_boxes_retained':True,'tiny_node_count':producer['counts']['tiny_nodes'],
        'global_splits':producer['global_splits'],'maximum_depth':max(f['maximum_depth'] for f in producer['frames']),
        'complete_piece_tests':producer['counts']['pieces'],'complete_channel_tests':producer['counts']['channels'],
        'producer_recorded_seconds':producer['seconds'],'producer_peak_RSS_bytes':producer['peak_RSS_bytes'],
        'producer_time_scope':'timed initialization, fresh root computation and complete proof serialization; sampled before writing final report',
        'RSS_is_not_the_address_space_cap':True,'independent_external_wall_measurement_claimed':False,
        'independent_reader_seconds':reader['seconds'],
        'independent_reader_peak_RSS_bytes':reader['peak_RSS_bytes'],
        'independently_checked_material_records':reader['whole_native_material_records'],
        'all_node_observation_counts':reader['totals'],
        'terminal_observation_counts':terminal_counts,
        'terminal_upper_bound_contributions_exact':{k:str(v) for k,v in terminal_bounds.items()},
        'per_frame_terminal_contributions':per_frame_terminal,
        'acceptance_means_upper_bound_at_most_original_tolerance_not_zero_intersection':True,
        'conditional_frames':[{k:f[k] for k in ('case_id','frame','root_count','intersection_upper_bound_exact','intersection_upper_bound_display_mm3','splits','maximum_depth','conditional_gate_passed')} for f in producer['frames']],
        'original_L1_archive_identity':input_binding['original_zip'],
        'inherited_complete_scientific_archive':binding['complete_original_scientific_archive'],
        'inherited_evidence_copies':identity(inherit/'R9_INHERITED_FILE_BINDINGS.json'),
        'inherited_native_scope_is_not_new_execution':True,'original_four_failure_classes':requirements,
        'actual_strategy_history':history,
        'independent_recorded_budget_audit':identity(HERE.parent/'independent-review/R9_CYLINDER_SLAB_RECORDED_BUDGET_AUDIT.json'),
        'strict_quadric_reader_repair':{
            'new_enforcement':'Only below_radius or above_radius classifications may exclude a piece; a valid loose unresolved enclosure cannot exclude.',
            'actual_successful_channel_mutation_rejected':True,
            'old_R8_channel_reader_actually_accepted_mutated_unresolved_bound':True,
            'old_R8_scope':'Its math checker verified the bound, but the old channel reader did not require strict radial separation.',
            'existing_original_valid_bounds_invalidated':False,
            'evidence':identity(HERE/'independent-balanced-all16-attempt1/report.json')},
        'interruption_and_serialization_scope':{
            'executed_full_producer':'cylinder_slab_all16_r9.py',
            'successful_actual_run_has_no_computation_or_serialization_exception':True,
            'actual_atomic_split_interruption_controls':identity(HERE/'ATOMIC_REFINEMENT_INTERRUPTION_CONTROLS.json'),
            'v1_remaining_exception_path_gaps':['post-commit/pre-clear pending evidence label can be imprecise','timeout during serialization does not guarantee every remaining committed payload is recovered'],
            'prepared_v2_full_producer':identity(HERE/'cylinder_slab_all16_r9_v2.py'),
            'v2_full_run_executed':False,
            'recovery_helper_actual_small_controls':identity(HERE/'RECOVERY_SERIALIZATION_CONTROLS.json'),
            'v2_controls_retroactively_qualify_v1_exception_paths':False},
        'prepared_candidate_optimization':{'files':[identity(HERE/name) for name in prepared],
                                           'pilot_executed':False,'full_run_executed':False,'qualification_claimed':False,
                                           'reason_not_executed':'Full-twelve-channel original-budget run already passed; complete its independent acceptance instead of optional extra runs.'},
        'remaining_native_premises':[
            'Complete coherent material boundary and inclusion of the actual native BREP in the serialized carriers.',
            'Native filling and complete native envelope topology/orientation under all requested displacements.',
            'Uniform compiled geometry/transform error and frozen-source-to-installed-binary correspondence.',
            'Source-specific overlong degree-1 B-spline trim semantics retained from original evidence.',
            'Full actual independent mechanical domain and STOP/SPRING segment support; fixed sixteen frames do not replace this.',
            'Original Boolean kernel set correctness and physical/FE/electrical/test qualification.'
        ]
    }
    (HERE/'R9_ENVELOPE_SCOPE.json').write_text(json.dumps(scope,indent=2)+'\n')
    skipped={'R9_ENVELOPE_DELIVERY_MANIFEST.json'}
    files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in skipped and '__pycache__' not in p.parts]
    items=[identity(p) for p in files]
    manifest={'schema':'razr-r9-envelope-complete-file-delivery-manifest','all_listed_files_required_in_scientific_delivery':True,
              'manifest_excludes_itself':True,'file_count':len(items),'total_bytes':sum(x['bytes'] for x in items),'files':items,
              'external_complete_original_scientific_archive':binding['complete_original_scientific_archive'],
              'projection_entrypoints':['README_R9_ENVELOPE.md','R9_ENVELOPE_SCOPE.json','R9_ENVELOPE_DELIVERY_MANIFEST.json',
                                       'cylinder-slab-all16-attempt1/report.json','independent-cylinder-slab-all16-attempt1/report.json',
                                       'inherited-native-source-scopes/R9_INHERITED_FILE_BINDINGS.json'],
              'full_proof_directories':['balanced-all16-attempt1','gradient-all16-attempt1','cylinder-slab-all16-attempt1'],
              'selected_prepared_sources_are_unexecuted':prepared,
              'not_copied_or_changed_by_this_subtask':['R8 complete originals and independent checker sources','parent-managed full scientific publication archive']}
    (HERE/'R9_ENVELOPE_DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'scope_written':True,'files':len(items),'bytes':manifest['total_bytes'],'passes':16}))


if __name__=='__main__':main()
