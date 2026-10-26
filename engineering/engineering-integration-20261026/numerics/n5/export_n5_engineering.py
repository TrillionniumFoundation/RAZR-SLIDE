"""Export an explicit numerical allowlist; original producer records stay untouched.

Raw environment/proc/namespace/log/API collections are not exported. Numerical
arrays and mathematical history records retain their original bytes. Projected
reports identify their original SHA256 and byte count and do not claim that the
omitted raw runtime records have been durably preserved.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

REPORT_KEYS = '''schema source_candidate source_baseline_helper_sha256 new_solver_research_identity new_resource_budget_identity diagnostic_completed historical_K_or_H_recovered H_action_restore_executed complete_body_response_accepted new_QP_executed candidate_go fixture_fabrication_go manufacturing_go original_probe_seed original_probe_count original_residual_threshold original_residual_denominator original_gate_matvec_precision all_five_rhs_prepared baseline_probes refined_probes probe_execution solver_strategy source_base_commit output_data_budget_bytes address_space_limit_bytes C_sha256 prepared_input_arrays_sha256 original_Kff_identity_before original_Kff_shape original_Kff_nnz factorization baseline_all_five_passed longdouble_finfo refined_all_five_passed five_probe_residuals_passed_after_optional_refinement original_Kff_identity_after runtime files_sha256 phase seconds peak_rss_kib disk_free_bytes probe_index outer_iteration residual_ratio passes_original_threshold outer_iterations error_type initial_field_origin damping actually_changed_DOFs representational_stagnation'''.split()
ASSEMBLY_KEYS = '''schema body level original_tetrahedra subtetrahedra dofs condensed_dofs full_uncondensed_dofs E_normalization nu body_loads_on_added_internal_DOFs original_faces_and_surface_P2_traces_unchanged K_sha256 loads_sha256 mesh_sha256 mapping_sha256 K_bytes K_nnz K_symmetry_absolute_max global_directional_energy_probes global_energy_relative_error_max rigid_modes_checked rigid_mode_action_max coordinate_mapping_max_error_mm minimum_scalar_DOF_separation_mm runtime element_assembly_seconds seconds peak_rss_kib new_rebuild_identity original_historical_artifact_restored full_inverse_operator_probes_executed new_QP_executed contact_or_mesh_convergence_qualified candidate_go fixture_fabrication_go manufacturing_go completed phase elapsed_seconds original_vector_dofs coordinate_mapping_error_mm minimum_scalar_dof_separation_mm original_mesh_and_load_bytes_exact material_E material_nu volume_level element_storage assembled_elements total_elements five_global_assembly_energy_probes_relative_error six_rigid_modes_action_absolute_max numerical_primitive_unchanged original_artifact_restored full_inverse_solved contact_solved disk_free_bytes error_type'''.split()
SUPERVISOR_KEYS = '''schema exit_code resource_stop_reason seconds peak_worker_RSS_bytes peak_worker_high_water_RSS_bytes peak_worker_virtual_bytes sampled_peak_cgroup_current_bytes sampled_peak_cgroup_shmem_bytes sampled_peak_nonreclaimable_budget_bytes peak_task_payload_bytes minimum_filesystem_available_bytes file_cache_counted_separately_from_nonreclaimable_budget memory_budget_definition supervisor_source_sha256 supervisor_source_sha256_after supervisor_source_unchanged log_sha256 samples'''.split()
SAMPLE_KEYS = '''monotonic task_filesystem_available_bytes task_payload_bytes cgroup_current_bytes cgroup_anon_bytes cgroup_shmem_bytes cgroup_file_bytes nonreclaimable_budget_bytes VmRSS_bytes VmHWM_bytes VmSize_bytes'''.split()
SOURCE_PATHS = [
 'source/probe_panel_float64_local_refinement.py','source/N5_STRATEGY.json',
 'source/import_n5_inputs.py','source/N5_FROZEN_N4B_INPUTS.json',
 'source/n5_independent_reader.py','source/export_n5_engineering.py',
 'source/host-cap.py','source/service-launch.py','source/python-downloads.json',
 *['source/S4/'+p for p in [
  'engineering/engineering-integration-20261025/numerics/recover_inputs.py',
  'engineering/engineering-integration-20261025/numerics/assemble_l2.py',
  'engineering/engineering-integration-20261025/numerics/run_bounded.py',
  'engineering/engineering-integration-20261025/numerics/probe_original_actions.py',
  'integration/tetra_bubble_refinement.py','integration/contact_patch_audit.py',
  'integration/contact_exchange.py','tools/check_environment.py','pyproject.toml','uv.lock']],
 *['source/original-v4/'+p for p in [
  'integration/probe_key_endpoint_extension.py','tools/key_endpoint_resume.py',
  'run_key_endpoint_trials.py','tests/test_key_endpoint_extension.py','tests/test_key_endpoint_resume.py']]
]
PLAIN_NUMERIC = [
 'seed-N4b/probe-N4/C.npz',
 'seed-N4b/probe-N4/points.json',
 'seed-N4b/probe-N4/five-probe-rhs.npy',
 'seed-N4b/probe-N4/five-probe-directions.npy',
 'seed-N4b/probe-N4/fixed-original-DOFs.npy',
 'seed-N4b/probe-N4/free-original-DOFs.npy',
 'seed-N4b/probe-N4/refined-five-probe-fields.npy',
 'seed-N4b/probe-N4/report.engineering.json',
 'seed-N4b/N4-independent-field-readback.engineering.json',
 'seed-N4b/N4B-input-recovery.json',
 'seed-N4b/EXPORT_MANIFEST.json',
 'N5-input-recovery.json',
 'original-inputs/panel/mesh.npz','original-inputs/panel/loads.npz',
 'volume/panel/level-2/K.npz','volume/panel/level-2/mesh.npz','volume/panel/level-2/loads.npz','volume/panel/mapping.npz',
 'probe-N5/C.npz','probe-N5/points.json','probe-N5/fixed-original-DOFs.npy','probe-N5/free-original-DOFs.npy',
 'probe-N5/five-probe-rhs.npy','probe-N5/five-probe-directions.npy','probe-N5/factor-perm-r.npy','probe-N5/factor-perm-c.npy',
 'probe-N5/original-diagonal.npy','probe-N5/original-absolute-row-sums.npy',
 'probe-N5/baseline-five-probe-fields.npy','probe-N5/refined-five-probe-fields.npy',
 *[f'probe-N5/probe-{i}-{kind}-{what}.npy' for i in range(5) for kind in ('baseline','final') for what in ('field','residual')],
]
HISTORY_RE = re.compile(r'probe-N5/probe-[0-4]-history/outer-(?:0[1-9]|[12][0-9]|3[0-2])-(?:local-return|field)(?:-rhs|-residual|-actual-update)?\.(?:npy|json)$')


def sha(path: Path) -> str:
 digest=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
 return digest.hexdigest()


def valid_source(root: Path, name: str) -> Path:
 p=root/name
 if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
  raise ValueError('source is missing, nonregular, symlinked or outside task: '+name)
 return p


def no_private_runtime_strings(value):
 if isinstance(value,dict):
  for k,v in value.items():no_private_runtime_strings(k);no_private_runtime_strings(v)
 elif isinstance(value,list):
  for v in value:no_private_runtime_strings(v)
 elif isinstance(value,str):
  if re.search(r'(?:/home/|/workspace/|/tmp/|/proc/[0-9]|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})',value):
   raise ValueError('private runtime string in selected engineering value')


def main(root: Path, output: Path):
 root=root.resolve(strict=True);output=output.resolve()
 if output==root or root in output.parents:raise ValueError('export must be outside original case directory')
 output.mkdir(parents=True,exist_ok=False)
 manifest={'schema':'razr-N5-engineering-allowlist-export-v1','complete_original_runtime_collection_exported':False,
  'raw_runtime_records_durable':False,'omitted_runtime_remains_on_ephemeral_runner_only':True,
  'producer_originals_modified':False,'numerical_arrays_and_mathematical_histories_are_original_bytes':True,
  'projection_does_not_replace_originals_or_change_acceptance':True,'copied':{},'projections':{},'original_records_inventory':[],
  'policy':'explicit source/numerical allowlist; no environment, proc, namespace, raw logs, API or repository identity records exported'}
 def copy(name):
  p=valid_source(root,name);dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True)
  if p.suffix=='.json' and name not in SOURCE_PATHS:no_private_runtime_strings(json.loads(p.read_text()))
  before=sha(p)
  # Hard-link immutable originals where possible; no extra full-matrix capacity.
  try:os.link(p,dest)
  except OSError:shutil.copyfile(p,dest)
  assert before==sha(dest)==sha(p)
  manifest['copied'][name]={'sha256':before,'bytes':p.stat().st_size,'original_bytes':True}
 def project(name,keys,destination=None,transform=None):
  p=valid_source(root,name);raw=json.loads(p.read_text());selected={k:raw[k] for k in keys if k in raw}
  if transform is not None:selected=transform(raw,selected)
  no_private_runtime_strings(selected)
  record={'schema':'razr-derived-engineering-projection-v1','original_record_sha256':sha(p),'original_record_bytes':p.stat().st_size,
   'is_original_record':False,'omitted_runtime_record_durable':False,'selected_engineering_fields':selected}
  destname=destination or name.removesuffix('.json')+'.engineering.json'
  dest=output/destname;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
  manifest['projections'][destname]={'sha256':sha(dest),'bytes':dest.stat().st_size,'original_sha256':record['original_record_sha256']}
 for name in SOURCE_PATHS+PLAIN_NUMERIC:
  if (root/name).exists():copy(name)
 for p in sorted((root/'probe-N5').glob('probe-*-history/*')):
  name=str(p.relative_to(root))
  if HISTORY_RE.fullmatch(name):copy(name)
 for name in ('probe-N5/report.json','probe-N5/progress.json'):
  if (root/name).is_file():project(name,REPORT_KEYS)
 for name in ('volume/panel/level-2/report.json','volume/panel/progress.json'):
  if (root/name).is_file():project(name,ASSEMBLY_KEYS)
 for name in ('panel-assembly-supervisor.json','input-recovery-supervisor.json','probe-N5-supervisor.json','readback-N5-supervisor.json'):
  if (root/name).is_file():
   def numeric_samples(raw,value):
    value['samples']=[{k:r[k] for k in SAMPLE_KEYS if k in r} for r in raw.get('samples',[])]
    if raw.get('supervisor_error'):value['supervisor_error_type']=raw['supervisor_error']['type']
    return value
   project(name,SUPERVISOR_KEYS,transform=numeric_samples)
 for name in ('original-K-byte-identity.json','N5-independent-field-readback.json'):
  if (root/name).is_file():
   raw=json.loads((root/name).read_text())
   project(name,[k for k in raw if k not in ('failure','traceback')])
 # Version/provenance checks are projected; no raw environment maps are copied.
 checks={}
 for name in ('environment-before.json','environment-after.json'):
  if (root/name).is_file():
   p=valid_source(root,name);raw=json.loads(p.read_text())
   checks[name]={'original_sha256':sha(p),'original_bytes':p.stat().st_size,'passed':raw.get('passed'),
    'python_version':raw.get('python_version'),'checked_package_count':raw.get('checked_package_count'),
    'checked_packages':raw.get('checked_packages'),'pyproject_sha256':raw.get('pyproject_sha256'),'uv_lock_sha256':raw.get('uv_lock_sha256')}
 if (root/'source-after.json').is_file():
  p=valid_source(root,'source-after.json');raw=json.loads(p.read_text())
  checks['functional_source_after']={'original_sha256':sha(p),'original_bytes':p.stat().st_size,
   'head_equals_S4':raw.get('head',{}).get('exit_code')==0 and raw.get('head',{}).get('stdout','').strip()=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560',
   'git_status_empty':raw.get('status',{}).get('exit_code')==0 and not raw.get('status',{}).get('stdout','').strip(),
   'original_five_sources_unchanged':raw.get('original_five_sources_unchanged')}
 # Namespace/signal receipts: only qualification booleans and numeric exits.
 checks['execution_harness']=[]
 for p in sorted(root.rglob('SUMMARY.json')):
  raw=json.loads(p.read_text())
  if raw.get('schema')!='razr-D4-private-service-launch':continue
  manager=raw.get('manager_result',{})
  checks['execution_harness'].append({'original_sha256':sha(p),'original_bytes':p.stat().st_size,
   'compatibility_verified':raw.get('compatibility_verified'),'cleanup_verified':raw.get('cleanup_verified'),
   'normal_command_completed':raw.get('normal_command_completed'),'command_exit_code':raw.get('command_exit_code'),
   'wrapper_exit_code':raw.get('exit_code'),'forced_cleanup':manager.get('forced_cleanup'),
   'adopted_descendant_cleanup_required':manager.get('adopted_descendant_cleanup_required')})
 no_private_runtime_strings(checks)
 (output/'EXECUTION_CHECKS.engineering.json').write_text(json.dumps({'schema':'razr-N5-projected-execution-checks-v1',
  'raw_runtime_records_exported':False,'raw_runtime_records_durable':False,'checks':checks},indent=2,allow_nan=False)+'\n')
 # Every omitted raw record is represented by content identity only, not paths
 # or content. This is an inventory, never a claim of durable raw availability.
 for p in sorted(root.rglob('*')):
  if p.is_file() and not p.is_symlink():
   manifest['original_records_inventory'].append({'sha256':sha(p),'bytes':p.stat().st_size,
    'exported_original_bytes':str(p.relative_to(root)) in manifest['copied']})
 manifest['exported_files']={str(p.relative_to(output)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(output.rglob('*')) if p.is_file()}
 (output/'EXPORT_MANIFEST.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
 summary=output.parent/'engineering-summary';summary.mkdir(exist_ok=False)
 for name in ['EXPORT_MANIFEST.json','EXECUTION_CHECKS.engineering.json','N5-independent-field-readback.engineering.json',
  'N5-input-recovery.json','input-recovery-supervisor.engineering.json',
  'original-K-byte-identity.engineering.json','panel-assembly-supervisor.engineering.json',
  'volume/panel/level-2/report.engineering.json','volume/panel/progress.engineering.json',
  'probe-N5-supervisor.engineering.json','probe-N5/report.engineering.json','probe-N5/progress.engineering.json']:
  p=output/name
  if p.is_file():
   d=summary/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
 print(json.dumps({'copied_files':len(manifest['copied']),'projected_records':len(manifest['projections']),
  'raw_runtime_records_exported':False,'raw_runtime_records_durable':False},indent=2))


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();main(a.root,a.output)
