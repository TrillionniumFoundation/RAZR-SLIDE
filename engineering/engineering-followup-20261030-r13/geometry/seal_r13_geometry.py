"""Freeze R13 evidence, external identities, scope and complete archive readback."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rec(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
assert not (HERE/'DELIVERY_MANIFEST.json').exists()
required=['native-brep-attempt1/report.json','native-step-attempt1/report.json','stop-spring-readback-attempt1/report.json',
          'exact-sections-attempt1/report.json','MODIFIED_SECTIONS_INDEPENDENT_REVIEW.json','COMPLETE_SOURCE_MOTION_DOMAIN.json',
          'SOURCE_MOTION_INDEPENDENT_REVIEW.json','CURRENT_NOMINAL_LOAD_PATH_AND_SECTION_INPUTS.json','R13_TRIM_INDEPENDENT_REVIEW.json','trim-negative-controls/report.json']
data={p:json.loads((HERE/p).read_text()) for p in required}
for p,r in data.items():assert r.get('completed',r.get('all_replayed_rejections')) is True,p
sections=data['MODIFIED_SECTIONS_INDEPENDENT_REVIEW.json'];trim=data['R13_TRIM_INDEPENDENT_REVIEW.json']
scope={'schema':'razr-r13-current-geometry-structure-and-domain-scope-v1','completed':True,
       'source':rec(__file__),'input_manifest':rec(HERE/'INPUT_MANIFEST.json'),'results':{p:rec(HERE/p) for p in required},
       'new_native_executions':{'full_modified_windows':6,'serialization_formats':2,'actual_crops':12,'directed_material_differences':24,
           'all_24_directed_material_differences_zero':True,'STOP_SPRING_complete_bodies':8,'STOP_SPRING_format_readbacks':16,
           'STOP_SPRING_complete_face_occurrences':192,'new_native_failures':0,'all_new_native_processes_ended':True,'new_complete_factory_pair_run':False},
       'complete_source_region_models':{'coordinate_interpretations':2,'region_models':12,
           'positive_3D_cells':sum(x['complete_positive_cells'] for x in sections['results']),
           'complete_axis_strata':sum(x['complete_axis_strata'] for x in sections['results']),
           'complete_transverse_chord_strata':sum(x['complete_transverse_chord_strata'] for x in sections['results']),
           'whole_declared_named_K1_K3_modification_windows_covered':True,'all_inherited_parent_CSG_or_global_part_thickness_covered':False},
       'full_source_motion_real_model':{'profile_branches':16,'merged_left_right_pairs':25,'feasible_pairs':17,'infeasible_pairs':8,
           'tiny_two_contact_lower_stop_interval_preserved':True,'cam_STOP_and_panel_travel_stops_are_distinct':True,
           'full_float64_acceptance_equivalence_proved':False,'physical_allowed_domain_proved':False},
       'negative_controls':{'section_ledger_rejections':4,'source_domain_ledger_rejections':3,'actual_original_profile_out_of_domain_rejections':8,
           'shared_slide_extreme_pair_infeasibility':1,'trim_rejections':8,'complete_trim_variants_and_replay_preserved':True,
           'separate_two_finite_cuts_miss_middle_material_counterexample':True},
       'envelope_bounds_per_side_mm3':{'unchanged_R12_B0_only':0.9600000000000029,'conditional_B0_and_T':3.1510793974117154e-15,
           'old_bound_replaced':False,'conditional_threshold_passed':True,'native_B0_and_T_membership_proved':False,
           'complete_global_native_realization_existence_proved':False,'uniform_compiled_error_proved':False},
       'open_qualification':{'native_material_filling_identity':False,'whole_KEY_or_panel_global_minimum_wall':False,
           'weakest_effective_whole_structure_load_section':False,'current_geometry_FE_tolerance_qualification':False,
           'physical_material_process_load_preload_spring_data_complete':False,'actual_physical_allowed_domain':False,
           'full_15D_G2':False,'G3':False,'G4':False,'G5':False,'manufacturing_go':False},
       'R12_sealed_directories_modified':False,'public_push_performed_by_this_agent':False}
(HERE/'R13_GEOMETRY_SCOPE.json').write_text(json.dumps(scope,indent=2)+'\n')
external=[]
for path in ['r13_envelope_work/native-attempt1/report.json','r13_envelope_work/producer-attempt1/complete_trim_corridors.json',
             'r13_envelope_work/producer-attempt1/L_KEY-completed-trim-ledger.json.gz','r13_envelope_work/producer-attempt1/R_KEY-completed-trim-ledger.json.gz',
             'panel_fill_work/exterior-refinement-attempt1/complete_face_projections.json.gz',
             'panel_fill_work/exterior-refinement-attempt1/L_KEY-exterior-ledger.json.gz','panel_fill_work/exterior-refinement-attempt1/R_KEY-exterior-ledger.json.gz']:
    external.append(rec(HERE.parent/path))
old=Path('/workspace/scratch/f11ac2a81fe4/RAZR-SLIDE/engineering/engineering-followup-20261030-r11/geometry-proof')
for p in ('roi-producer-v2/report.json','roi-reader-v2/report.json','roi-inputs-v1/L_KEY.brep','roi-inputs-v1/R_KEY.brep'):external.append(rec(old/p))
(HERE/'EXTERNAL_DEPENDENCIES.json').write_text(json.dumps({'schema':'razr-r13-external-execution-layout-identities-v1','files':external,
    'original_execution_paths_retained':True,'R13_envelope_full_evidence_pack_is_companion_dependency':True,
    'prior_R11_evidence_not_new_R13_execution':True},indent=2)+'\n')
files={}
for p in sorted(HERE.rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and p.name not in ('DELIVERY_MANIFEST.json','ARCHIVE_READBACK.json'):
        files[str(p.relative_to(HERE))]={'bytes':p.stat().st_size,'sha256':sha(p)}
manifest={'schema':'razr-r13-complete-current-geometry-delivery-v1','file_count':len(files),'total_bytes':sum(v['bytes'] for v in files.values()),'files':files,
          'excludes':['DELIVERY_MANIFEST.json','ARCHIVE_READBACK.json','__pycache__']}
(HERE/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=HERE.parent/'RAZR_R13_current_geometry_structure_domain.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name in files:z.write(HERE/name,'r13_geometry_work/'+name)
    z.write(HERE/'DELIVERY_MANIFEST.json','r13_geometry_work/DELIVERY_MANIFEST.json')
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist())=={'r13_geometry_work/'+name for name in files}|{'r13_geometry_work/DELIVERY_MANIFEST.json'}
    for name,record in files.items():
        b=z.read('r13_geometry_work/'+name);assert len(b)==record['bytes'] and hashlib.sha256(b).hexdigest()==record['sha256']
    assert z.read('r13_geometry_work/DELIVERY_MANIFEST.json')==(HERE/'DELIVERY_MANIFEST.json').read_bytes()
readback={'schema':'razr-r13-complete-archive-readback-v1','archive':rec(archive),'scientific_and_source_members_verified':len(files),
          'all_member_size_and_SHA256_equal':True,'manifest_sha256':sha(HERE/'DELIVERY_MANIFEST.json'),'scope_sha256':sha(HERE/'R13_GEOMETRY_SCOPE.json')}
(HERE/'ARCHIVE_READBACK.json').write_text(json.dumps(readback,indent=2)+'\n');print(json.dumps(readback))
