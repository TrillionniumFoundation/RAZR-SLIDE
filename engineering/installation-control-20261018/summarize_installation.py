"""Compare independently verified installation and fixed-adjustment service fields."""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.sparse import load_npz
R=Path('/home/qian-qi/RAZR-SLIDE-installation-control-20261018')
O=Path('/home/qian-qi/.local/share/razr-slide-evidence/installation-control-20261018')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
lock=json.loads((O/'locked-installation.json').read_text());plan=json.loads((R/'engineering/installation-control-20261018/force-target-plan.json').read_text())
rows=[];arrays=[]
for name in ['install-force','service-locked']:
    src=O/name;ad=O/('audit-'+name);r=json.loads((src/'report.json').read_text());a=json.loads((ad/'report.json').read_text())
    assert r['passed'] and a['passed'] and a['total_regions']==5255 and a['minimum_covered_bound_mm']>=-1e-7
    for p in [src/'report.json',src/'full-fields.npz']:assert a['input_sha256'][str(p)]==sha(p)
    x=dict(np.load(src/'full-fields.npz',allow_pickle=False));arrays.append(x)
    c=np.asarray(lock['compliance_Epanel_over_k_per_mm']);q=np.asarray(a['bolt_weighted_displacements_mm']);delta=np.asarray(lock['adjustment_mm'])
    zero_hold_error=float(np.max(abs(x['forces'][:4]-(q+delta)/c)))
    assert zero_hold_error<1e-10
    assert np.array_equal(np.asarray(r['installation_control']['adjustment_mm']),delta)
    assert r['installation_control']['model_identity']==lock['model_identity']
    for body in ['panel','frame']:
        assert a['full_checks'][body]['internal_recovery']['private_DOFs_recovered']==(4321500 if body=='panel' else 5972100)
    rows.append({'stage':name,'mode':r['installation_control']['mode'],'external_load_scale_over_Epanel_mm2':r['external_load_scale_over_Epanel_mm2'],
       'forces_over_Epanel_mm2':x['forces'][:4].tolist(),'weighted_separations_mm':q.tolist(),'locked_adjustment_mm':delta.tolist(),
       'locked_law_force_residual':zero_hold_error,'finite_exchange_solves':len(r['history']),'contact_constraints':len(r['contact_points'])-4,
       'independent_minimum_gap_mm':a['minimum_covered_bound_mm'],'audited_regions':a['total_regions'],
       'load_observations_mm':a['load_weighted_observations'],'elastic_energy_over_Epanel':a['twice_elastic_energy']/2,
       'full_checks':a['full_checks'],'force_moment_balance':a['balance'],'complementarity':a['contact_complementarity'],
       'source_report_sha256':sha(src/'report.json'),'source_fields_sha256':sha(src/'full-fields.npz'),'audit_report_sha256':sha(ad/'report.json')})
for body in ['panel','frame']:
    A=O/'install-force'/body;B=O/'service-locked'/body
    assert json.loads((A/'selection.json').read_text())==json.loads((B/'selection.json').read_text())
    assert (load_npz(A/'coupling.npz')!=load_npz(B/'coupling.npz')).nnz==0
    for filename in ['local-blocks.npz','effective-loads.npz']:
        a=dict(np.load(A/filename,allow_pickle=False));b=dict(np.load(B/filename,allow_pickle=False))
        assert set(a)==set(b) and all(np.array_equal(a[k],b[k]) for k in a)
reference=json.loads((R/'engineering/loadcases-20261018/nine-case-summary.json').read_text());byid={x['id']:x for x in reference['cases']}
old_assembly=byid['assembly-reference'];old_service=byid['case-6']
installed=np.asarray(rows[0]['forces_over_Epanel_mm2']);service=np.asarray(rows[1]['forces_over_Epanel_mm2']);targets=np.asarray(plan['target_force_over_Epanel_mm2'])
assert np.max(abs(installed-targets))<1e-10
summary={'base_main':'ee9a30831208c7e282c3518abdca2cf1cfe50726','functional_commit':'2303ac50f7f881ca243cc7315718aba99354fd6a',
  'new_independently_verified_full_fields':2,'stages':rows,'same_energy_trace_and_pressure_maps':True,'model_identity':lock['model_identity'],
  'initial_target_vector_not_assumed_equal_load_sharing':targets.tolist(),
  'equivalent_historical_initial_parameter_after_calibration':(np.asarray(lock['adjustment_mm'])/np.asarray(lock['compliance_Epanel_over_k_per_mm'])).tolist(),
  'force_target_residual_max':float(np.max(abs(installed-targets))),
  'service_increment_from_installed_reference':(service-installed).tolist(),
  'incremental_force_per_external_scale_not_capacity':((service-installed)/1e-5).tolist(),
  'zero_external_locked_state_reproduction':{'method':'same full installation field retains equilibrium/contact and satisfies fixed-adjustment bolt law after removing force-control actuators','bolt_law_residual':rows[0]['locked_law_force_residual'],'separate_FEA_rerun':False,'no_force_control_retained_in_service':True},
  'prior_unloaded_initial_parameter_reference':{'reference_commit':reference['functional_commit'],'source_id':old_assembly['id'],'initial_parameter':.0002,'equilibrium_forces':old_assembly['bolt_forces_over_Epanel_mm2'],'not_rerun':True},
  'prior_service_reference':{'source_id':'case-6','equilibrium_forces':old_service['bolt_forces_over_Epanel_mm2'],'load_weighted_response_mm':old_service['load_weighted_response_mm'],'not_rerun':True},
  'service_vs_prior_reference':{'bolt_force_difference':(service-np.asarray(old_service['bolt_forces_over_Epanel_mm2'])).tolist(),'load_weighted_observation_change_mm':rows[1]['load_observations_mm'][2]-old_service['load_weighted_response_mm'],'different_installed_state_not_accuracy_improvement':True},
  'simultaneous_force_installation_not_sequential_torque_tightening':True,'targets_normalized_research_not_actual_measurements':True,
  'prescribed_head_nut_pressure_and_ideal_frame_support_retained':True,'no_new_full_trace_mesh_or_material_qualification':True,
  'candidate_go':False,'fixture_fabrication_go':False,'manufacturing_go':False,
  'source_sha256':sha(__file__),'state_sha256':sha(O/'locked-installation.json')}
out=O/'installation-sequence-summary.json';assert not out.exists();out.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
print('INSTALLATION_SEQUENCE_SUMMARY',json.dumps({k:summary[k] for k in ['equivalent_historical_initial_parameter_after_calibration','service_increment_from_installed_reference','incremental_force_per_external_scale_not_capacity']}),flush=True)
