import hashlib,json,os,pathlib,sys
import numpy as np
from scipy.sparse import load_npz
EXPECTED_PANEL_C_SHA256 = '9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f'
EXPECTED_RHS_SHA256 = ['abae22600aa78c69bd1ac06e08df22e8a2740f4d5752d04e9f0922d71eeef2e7', 'e47ab9c4cc6707f8f549aeb8c27c099c02d03a5e0e2101de8ea97218d3b7848f', 'cc9ff568a50adf56034282b90e95b37dac1ba64219efaed23e7ca9bcab72e4f8', 'de6fa75d5fd4d63ecc5588e27eb097a31411720e71454b4c5bfe62457080513f', 'ada335a73f4a47813c3d14192adacd242e833155f224f1346bed0a586f1d2adc']
EXPECTED_DIRECTION_SHA256 = ['4d9dc6cf2bf3be139d0858e5a2ccdd996c5f76eac2fa0ee16f3166223ba2e8cb', 'ed71e39c886f4ff054a8f4a010756a3784ee4f727da5fe23d856b134fdbf92b7', 'f1aad589d38d6667299b5f7eaf934fdad37aebe7612cf03783bb72355280cd8a', '8fb443e916b10eaf2087860b05409a6030f13df620f5a8afd3417a66e405d8cb', '5b2fa88303ef4c095bc1cfa7b6e3ffa4db205527a6bac3b2e5a955c3ec81aaf3']
root=pathlib.Path(os.environ['N4_ROOT']);folder=root/'probe-N4'
result={'schema':'N4-independent-original-float64-readback-v2','completed':False,'five_original_gates_passed':False,'original_gate_limit':1e-7,'hardware_or_H_restore_qualified':False}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
try:
 report=json.loads((folder/'report.json').read_text());sup=json.loads((root/'probe-N4-supervisor.json').read_text())
 result['original_report_sha256']=sha(folder/'report.json');result['original_supervisor_sha256']=sha(root/'probe-N4-supervisor.json')
 result['diagnostic_completed']=report['diagnostic_completed'];result['supervisor_stop_reason']=sup['resource_stop_reason'];result['supervisor_exit_code']=sup['exit_code']
 assert report['source_candidate']==os.environ['S4'] and report['source_base_commit']==os.environ['S4']
 assert report['original_residual_threshold']==1e-7 and report['environment']['passed'] is True
 assert report['address_space_limit_bytes']==int(4.5*1024**3)
 assert report['original_Kff_identity_before']==report['original_Kff_identity_after']
 assert report['all_five_rhs_prepared'] is True and len(report['baseline_probes'])==len(report['refined_probes'])==5
 assert report['diagnostic_completed'] is True and sup['resource_stop_reason'] is None and sup['supervisor_source_unchanged'] is True
 K=load_npz(root/'volume/panel/level-2/K.npz').tocsc()
 assert sha(root/'volume/panel/level-2/K.npz')=='80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb'
 free=np.load(folder/'free-original-DOFs.npy',allow_pickle=False);fixed=np.load(folder/'fixed-original-DOFs.npy',allow_pickle=False)
 with np.load(root/'volume/panel/level-2/loads.npz',allow_pickle=False) as original_loads:
  assert sha(root/'volume/panel/level-2/loads.npz')=='811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6'
  assert np.array_equal(fixed,original_loads['D'])
 assert np.array_equal(free,np.setdiff1d(np.arange(344103),fixed))
 assert len(free)==344097 and len(fixed)==6
 A=K[free][:,free].tocsc();del K
 actual_identity={'shape':list(A.shape),'format':A.format,**{name:{'dtype':str(getattr(A,name).dtype),'sha256':hashlib.sha256(getattr(A,name).tobytes()).hexdigest()} for name in ('data','indices','indptr')}}
 assert actual_identity==report['original_Kff_identity_before']
 extended=A.astype(np.longdouble)
 assert np.finfo(np.longdouble).eps<np.finfo(np.float64).eps
 C=load_npz(folder/'C.npz').tocsc()
 assert C.shape==(344103,3885) and sha(folder/'C.npz')==EXPECTED_PANEL_C_SHA256
 directions=np.load(folder/'five-probe-directions.npy',allow_pickle=False)
 assert directions.shape==(3885,5) and directions.dtype==np.float64
 generator=np.random.default_rng(73021)
 original_directions=[np.ones(3885)]+[generator.choice([-1.0,1.0],3885) for _ in range(4)]
 for index,expected_direction in enumerate(original_directions):
  assert np.array_equal(directions[:,index],expected_direction)
  assert hashlib.sha256(directions[:,index].tobytes()).hexdigest()==EXPECTED_DIRECTION_SHA256[index]
 result['independent_original_free_fixed_domain_and_operator_checked']=True
 rhs=np.load(folder/'five-probe-rhs.npy',allow_pickle=False)
 original=np.load(folder/'baseline-five-probe-fields.npy',allow_pickle=False);final=np.load(folder/'refined-five-probe-fields.npy',allow_pickle=False)
 assert rhs.shape==original.shape==final.shape==(344103,5)
 for index in range(5):
  assert hashlib.sha256(rhs[:,index].tobytes()).hexdigest()==EXPECTED_RHS_SHA256[index]
  assert np.array_equal(np.asarray(C @ directions[:,index]).ravel(),rhs[:,index])
 result['independent_original_C_and_all_five_directions_and_RHS_checked']=True
 def check(u,b,record):
  assert u.dtype==b.dtype==np.float64 and np.isfinite(u).all() and np.isfinite(b).all()
  assert np.all(u[fixed]==0.)
  residual=A @ u[free]-b[free]
  numerator=float(np.max(np.abs(residual)));denominator=max(float(np.max(np.abs(b[free]))),1.)
  ratio=numerator/denominator
  assert ratio==record['free_dof_residual_infinity_ratio'] and numerator==record['residual_numerator'] and denominator==record['normalization_denominator']
  assert int(free[np.argmax(abs(residual))])==record['max_residual_original_dof']
  assert hashlib.sha256(residual.tobytes()).hexdigest()==record['residual_sha256']
  assert bool(ratio<=1e-7)==record['passes_original_threshold']
  return {'ratio':ratio,'max_original_DOF':record['max_residual_original_dof'],'passes':bool(ratio<=1e-7)}
 result['baseline']=[];result['final']=[];result['outer_fields_checked']=0;result['correction_fields_checked']=0;result['inner_iteration_counts']=[]
 for i in range(5):
  result['baseline'].append(check(original[:,i],rhs[:,i],report['baseline_probes'][i]))
  row=report['refined_probes'][i];result['final'].append(check(final[:,i],rhs[:,i],row['final_original_residual']))
  assert row['probe_index']==i and report['baseline_probes'][i]['probe_index']==i
  assert len(row['iterations'])<=8
  previous=original[:,i].copy();previous_passed=result['baseline'][-1]['passes']
  assert np.array_equal(previous,np.load(folder/f'probe-{i}-baseline-field.npy',allow_pickle=False))
  assert np.array_equal(final[:,i],np.load(folder/f'probe-{i}-final-field.npy',allow_pickle=False))
  step=0
  for iteration in row['iterations']:
   u=np.load(folder/iteration['field_file'],allow_pickle=False)
   check(u,rhs[:,i],iteration['equation_residual']);result['outer_fields_checked']+=1
   correction=iteration['gmres_return'];v=np.load(folder/correction['field_file'],allow_pickle=False)
   step+=1
   assert not previous_passed and iteration['outer_iteration']==correction['outer_iteration']==step
   expected_correction_rhs=-np.asarray(extended @ previous[free].astype(np.longdouble)-rhs[free,i].astype(np.longdouble),dtype=np.float64)
   actual_correction_rhs=np.load(folder/correction['equation_rhs_file'],allow_pickle=False)
   assert actual_correction_rhs.tobytes()==expected_correction_rhs.tobytes()
   assert np.array_equal(u,previous+v)
   previous=u.copy();previous_passed=iteration['equation_residual']['passes_original_threshold']
   b=np.zeros(344103);b[free]=actual_correction_rhs
   check(v,b,correction['equation_residual']);result['correction_fields_checked']+=1
   assert iteration['actual_inner_iterations']==len(iteration['gmres_callbacks'])
   assert iteration['actual_inner_iterations']==correction['actual_inner_iterations']<=40
   assert iteration['gmres_info']==correction['gmres_info']
   result['inner_iteration_counts'].append(iteration['actual_inner_iterations'])
  assert np.array_equal(previous,final[:,i])
  assert previous_passed==row['passes_original_threshold']
 result['independent_correction_rhs_update_chain_and_final_field_checked']=True
 for name,digest in report['files_sha256'].items():
  p=folder/name;assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(folder.resolve()) and sha(p)==digest
 result['files_hash_checked']=len(report['files_sha256'])
 result['five_original_gates_passed']=all(r['passes'] for r in result['final'])
 assert result['five_original_gates_passed']==report['refined_all_five_passed']
 assert sup['exit_code']==(0 if result['five_original_gates_passed'] else 2)
 for name in ('H_action_restore_executed','complete_body_response_accepted','new_QP_executed','candidate_go','fixture_fabrication_go','manufacturing_go'):assert report[name] is False
 result['completed']=True
except BaseException as exc:
 result['failure_type']=type(exc).__name__;result['failure']=str(exc)
 (root/'N4-independent-field-readback.json').write_text(json.dumps(result,indent=2)+'\n')
 raise
(root/'N4-independent-field-readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('original_report_sha256','original_supervisor_sha256')},indent=2))
