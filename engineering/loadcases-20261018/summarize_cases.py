"""Compare freshly independently verified states, never report arbitrary preload.
Baseline displacements are descriptive equilibria, not a path-dependent test.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.sparse import load_npz
R=Path('/home/qian-qi/RAZR-SLIDE-loadcases-schur-20261018');O=Path('/home/qian-qi/.local/share/razr-slide-evidence/loadcases-20261018')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((R/'engineering/loadcases-20261018/EXPERIMENT_PLAN.json').read_text())
solvestatus=json.loads((O/'solve-status.json').read_text());auditstatus=json.loads((O/'audit-status.json').read_text())
assert len(solvestatus)==len(auditstatus)==9
assert all(x['passed'] for x in solvestatus if x['id']!='assembly-reference') and all(x['passed'] for x in auditstatus if x['id']!='assembly-reference')
assert int((O/'assembly-reference.exit').read_text())==124
assert (O/'assembly-reference-schur.exit').read_text().strip()=='0' and (O/'audit-assembly-reference-schur.exit').read_text().strip()=='0'
reference={};rows=[];files={}
for entry in plan['cases']:
 label=entry['id'];effective_label='assembly-reference-schur' if label=='assembly-reference' else label;src=O/effective_label;ad=O/('audit-'+effective_label)
 assert (O/(effective_label+'.exit')).read_text().strip()=='0' and (O/('audit-'+effective_label+'.exit')).read_text().strip()=='0'
 rr=json.loads((src/'report.json').read_text());aa=json.loads((ad/'report.json').read_text())
 assert rr['passed'] and aa['passed'] and aa['case_id']==label and aa['definition']==entry
 assert rr['gap_tolerance_mm']==aa['gap_tolerance_mm']==plan['gap_tolerance_mm']
 assert aa['total_regions']==5255 and aa['minimum_covered_bound_mm']>=-plan['gap_tolerance_mm']
 assert rr['frozen_selection_sha256']==aa['frozen_selection_sha256']==plan['frozen_selection_sha256']
 assert rr['surface_load_mode']=='consistent'
 for body in ('panel','frame'):
  sel=json.loads((src/body/'selection.json').read_text());coupling=load_npz(src/body/'coupling.npz');local=dict(np.load(src/body/'local-blocks.npz',allow_pickle=False));loads=dict(np.load(src/body/'effective-loads.npz',allow_pickle=False))
  if body not in reference:reference[body]=(sel,coupling,local,loads)
  ss,cc,ll,ff=reference[body]
  assert sel==ss and (cc!=coupling).nnz==0
  assert set(local)==set(ll) and all(np.array_equal(local[k],ll[k]) for k in local)
  assert set(loads)==set(ff) and all(np.array_equal(loads[k],ff[k]) for k in loads)
  assert aa['full_checks'][body]['internal_recovery']['private_DOFs_recovered']==(4321500 if body=='panel' else 5972100)
 z=dict(np.load(src/'full-fields.npz',allow_pickle=False))
 patches={}
 for f,p in zip(z['forces'][4:],rr['contact_points'][4:]):patches[p['patch']]=patches.get(p['patch'],0.)+float(f)
 rows.append({'id':label,'source_label':effective_label,'source_functional_commit':'26539a79b953bdd0b6978551f13c3361f13853b6' if label=='assembly-reference' else 'e54d71cc2c838091e9c6b20c1063acf1049e9a06','definition':entry,'independently_passed':True,'contact_constraints':len(rr['contact_points'])-4,'finite_exchange_solves':len(rr['history']),
  'minimum_gap_bound_mm':aa['minimum_covered_bound_mm'],'bolt_forces_over_Epanel_mm2':z['forces'][:4].tolist(),
  'load_weighted_observations_mm':aa['load_weighted_observations'],'load_weighted_response_mm':aa['load_weighted_response'],
  'elastic_energy_normalized':.5*aa['twice_elastic_energy'],'rigid_mode_coordinates':z['rigid'].tolist(),
  'contact_patch_scalar_resultants_over_Epanel':patches,'full_checks':aa['full_checks'],'force_moment_residual':aa['balance'],
  'complementarity':aa['contact_complementarity'],'report_sha256':sha(src/'report.json'),'independent_report_sha256':sha(ad/'report.json'),'field_sha256':sha(src/'full-fields.npz')})
 for p in [src/'report.json',src/'full-fields.npz',ad/'report.json']:files[str(p)]=sha(p)
byid={x['id']:x for x in rows};assembly=byid['assembly-reference'];la=np.array(assembly['bolt_forces_over_Epanel_mm2']);initial=2e-4
preload={'input_initial_spring_parameter':initial,'equilibrated_zero_external_forces_over_Epanel_mm2':la.tolist(),
 'ratio_to_input_initial_parameter':(la/initial).tolist(),'difference_is_model_redistribution_not_measured_preload_loss':True}
transfers=[]
for case in range(8):
 row=byid['case-'+str(case)];force=np.array(row['bolt_forces_over_Epanel_mm2']);scale=row['definition']['external_load_scale_over_Epanel_mm2'];base=la if case>=4 else np.zeros(4)
 transfers.append({'case':case,'load_index':case%4,'initial_spring_parameter':row['definition']['initial_spring_force_over_Epanel_mm2'],
  'reference':'independently_solved_assembly' if case>=4 else 'exact_zero_load_zero_force_algebraic_state',
  'bolt_force_increment_over_Epanel_mm2':(force-base).tolist(),'increment_over_applied_load':((force-base)/scale).tolist()})
coverage={'original_normalized_load_cases':8,'unloaded_references_solved':1,'all_current_model_states_passed':True,
 'new_trace_faces':86,'new_trace_coefficients':258,'same_volume_contact_basis_and_load_maps':True,
 'same_target':1e-7,'regions_per_field':5255,'total_region_field_checks':5255*9,
 'not_new_mesh_or_full_trace_convergence':True,'not_installed_preload_or_servicerating':True}
summary={'base_main':plan['base_main'],'functional_commit':'26539a79b953bdd0b6978551f13c3361f13853b6','original_eight_source_commit':'e54d71cc2c838091e9c6b20c1063acf1049e9a06','eight_fields_not_rerun_after_optional_equality_fix':True,'original_assembly_timeout_retained':True,'coverage':coverage,'cases':rows,'preload_reference':preload,
 'load_to_bolt_transfers':transfers,'absolute_displacements_not_path_or_clearance_free_tangent_stiffness':True,
 'ideal_remote_fixture_neutralY_prescribed_pressure_and_uncovered_edges_unchanged':True,
 'raw_input_and_result_sha256':files,'source_sha256':sha(__file__),'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False}
for path,h in files.items():assert sha(path)==h
out=O/'nine-case-summary.json';assert not out.exists();out.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
print('NINE_CASE_SUMMARY_COMPLETE',json.dumps(preload),flush=True)
