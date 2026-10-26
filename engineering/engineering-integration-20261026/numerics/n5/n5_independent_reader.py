"""Independent byte/field/update-chain readback of the bounded N5 experiment."""
import hashlib,json,os,pathlib
import numpy as np
from scipy.sparse import load_npz

root=pathlib.Path(os.environ['CASE_DIR']);folder=root/'probe-N5';seed=root/'seed-N4b'
result={'schema':'N5-independent-original-float64-and-actual-update-readback-v1',
 'completed':False,'five_original_gates_passed':False,'original_gate_limit':1e-7,
 'probe_execution_state':'not_executed_or_no_report','hardware_or_H_restore_qualified':False}


def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def array_sha(a):return hashlib.sha256(np.asarray(a,dtype=np.float64).tobytes()).hexdigest()


try:
 report=json.loads((folder/'report.json').read_text());sup=json.loads((root/'probe-N5-supervisor.json').read_text())
 result['probe_execution_state']='report_exists'
 result['original_report_sha256']=sha(folder/'report.json');result['original_supervisor_sha256']=sha(root/'probe-N5-supervisor.json')
 assert report['source_candidate']==report['source_base_commit']==os.environ['S4']=='dd7def6e6a4de9f47dc91ca2ab336fb1a8828560'
 assert report['diagnostic_completed'] and report['environment']['passed'] and report['all_five_rhs_prepared']
 assert report['original_residual_threshold']==1e-7 and report['address_space_limit_bytes']==int(4.5*1024**3)
 assert sup['resource_stop_reason'] is None and sup['supervisor_source_unchanged']
 assert report['solver_strategy']['maximum_outer_updates']==32 and not report['solver_strategy']['new_sparse_factorization'] and not report['solver_strategy']['select_best_iterate']
 assert report['original_Kff_identity_before']==report['original_Kff_identity_after']
 K=load_npz(root/'volume/panel/level-2/K.npz').tocsc()
 assert sha(root/'volume/panel/level-2/K.npz')=='80f6f50243d421a3b0ab9eeff1324db029677b63febeaad1f023bf9609e9f1cb'
 assert sha(root/'volume/panel/level-2/loads.npz')=='811ba687959bb34dec5ada401b35f07123c917bfc4e68ad982d661fd62fac9a6'
 with np.load(root/'volume/panel/level-2/loads.npz',allow_pickle=False) as loads:fixed=loads['D']
 free=np.setdiff1d(np.arange(344103),fixed)
 assert len(fixed)==6 and len(free)==344097
 assert np.array_equal(fixed,np.load(folder/'fixed-original-DOFs.npy',allow_pickle=False))
 assert np.array_equal(free,np.load(folder/'free-original-DOFs.npy',allow_pickle=False))
 A=K[free][:,free].tocsc();del K
 identity={'shape':list(A.shape),'format':A.format,**{name:{'dtype':str(getattr(A,name).dtype),'sha256':hashlib.sha256(getattr(A,name).tobytes()).hexdigest()} for name in ('data','indices','indptr')}}
 assert identity==report['original_Kff_identity_before']
 diag=A.diagonal();row_abs=np.asarray(abs(A)@np.ones(len(free),dtype=np.float64)).ravel()
 assert np.all(np.isfinite(diag)) and np.all(diag>0)
 raw_bound=float(np.max(row_abs/diag));allowance=4.0*len(free)*np.finfo(np.float64).eps
 bound=float(np.nextafter(raw_bound*(1.0+allowance),np.inf));omega=float(1.0/bound)
 assert report['damping']['raw_absolute_row_sum_over_diagonal_max']==raw_bound
 assert report['damping']['roundoff_relative_allowance']==allowance and report['damping']['inflated_row_sum_bound']==bound
 assert report['damping']['omega']==omega and 0<omega<=1
 assert np.array_equal(diag,np.load(folder/'original-diagonal.npy',allow_pickle=False))
 assert np.array_equal(row_abs,np.load(folder/'original-absolute-row-sums.npy',allow_pickle=False))
 extended=A.astype(np.longdouble);assert np.finfo(np.longdouble).eps<np.finfo(np.float64).eps
 C=load_npz(folder/'C.npz').tocsc();assert C.shape==(344103,3885)
 assert sha(folder/'C.npz')=='9f75b00a961ee850857c82942332ebfdd5cb13aa9da55c5266d93337deca436f'
 directions=np.load(folder/'five-probe-directions.npy',allow_pickle=False);rhs=np.load(folder/'five-probe-rhs.npy',allow_pickle=False)
 assert directions.shape==(3885,5) and directions.dtype==rhs.dtype==np.float64 and rhs.shape==(344103,5)
 assert sha(folder/'five-probe-directions.npy')=='abe862cf2823c8511358e34c884957eae26e30ec381a605a594f91f4ad114861'
 assert sha(folder/'five-probe-rhs.npy')=='c78a9fe77aadfa65b46d56a5ec2085122d46306872ae57e05e5701a0428e8bd1'
 generator=np.random.default_rng(73021);expected=[np.ones(3885)]+[generator.choice([-1.,1.],3885) for _ in range(4)]
 for index,direction in enumerate(expected):
  assert np.array_equal(directions[:,index],direction) and np.array_equal(rhs[:,index],np.asarray(C@direction).ravel())
 initial=np.load(folder/'baseline-five-probe-fields.npy',allow_pickle=False);final=np.load(folder/'refined-five-probe-fields.npy',allow_pickle=False)
 assert sha(seed/'probe-N4/refined-five-probe-fields.npy')=='d1c679c82001673466c41d652e11b9fb878acae8ed57f61859cde99f374f8389'
 assert sha(folder/'baseline-five-probe-fields.npy')=='d1c679c82001673466c41d652e11b9fb878acae8ed57f61859cde99f374f8389'
 assert sha(seed/'probe-N4/report.engineering.json')=='4c0e3d6aa9750f6f5d7a93290d715e9192bb036bbc56833abbb7039765fcc6e4'
 prior=json.loads((seed/'probe-N4/report.engineering.json').read_text())['selected_engineering_fields']
 assert np.array_equal(initial,np.load(seed/'probe-N4/refined-five-probe-fields.npy',allow_pickle=False))
 assert initial.shape==final.shape==(344103,5) and initial.dtype==final.dtype==np.float64
 assert len(report['baseline_probes'])==len(report['refined_probes'])==5
 result['independent_original_K_C_directions_RHS_free_fixed_and_N4b_start_fields_checked']=True
 result['independent_damping_and_original_diagonal_checked']=True

 def check(u,b,record):
  assert u.dtype==b.dtype==np.float64 and np.isfinite(u).all() and np.isfinite(b).all() and np.all(u[fixed]==0.)
  uf=u[free];bf=b[free];error=A@uf-bf
  numerator=float(np.max(np.abs(error)));denominator=max(float(np.max(np.abs(bf))),1.)
  ratio=numerator/denominator;at=int(np.argmax(np.abs(error)))
  assert record['threshold']==1e-7 and ratio==record['free_dof_residual_infinity_ratio']
  assert numerator==record['residual_numerator'] and denominator==record['normalization_denominator']
  assert int(free[at])==record['max_residual_original_dof'] and float(error[at])==record['signed_residual_at_max_dof']
  assert float(bf[at])==record['rhs_at_max_dof'] and float(np.max(np.abs(uf)))==record['solution_infinity_norm']
  assert array_sha(error)==record['residual_sha256'] and array_sha(bf)==record['rhs_free_sha256'] and array_sha(uf)==record['solution_free_sha256']
  assert bool(ratio<=1e-7)==record['passes_original_threshold']
  return {'ratio':ratio,'max_original_DOF':int(free[at]),'passes':bool(ratio<=1e-7)}

 result['baseline']=[];result['final']=[];result['outer_fields_checked']=0;result['correction_fields_checked']=0;result['actual_update_fields_checked']=0;result['updates']=[]
 for index in range(5):
  baseline=check(initial[:,index],rhs[:,index],report['baseline_probes'][index]);result['baseline'].append(baseline)
  row=report['refined_probes'][index];result['final'].append(check(final[:,index],rhs[:,index],row['final_original_residual']))
  assert row['probe_index']==index and report['baseline_probes'][index]['probe_index']==index
  assert np.array_equal(initial[:,index],np.load(folder/f'probe-{index}-baseline-field.npy',allow_pickle=False))
  assert np.array_equal(final[:,index],np.load(folder/f'probe-{index}-final-field.npy',allow_pickle=False))
  assert row['actual_updates']==len(row['iterations'])<=32 and row['select_best_iterate'] is False
  previous=initial[:,index].copy();passed=baseline['passes'];step=0
  for iteration in row['iterations']:
   assert not passed
   step+=1;correction=iteration['local_return']
   assert iteration['outer_iteration']==correction['outer_iteration']==step and correction['omega']==omega
   u=np.load(folder/iteration['field_file'],allow_pickle=False);v=np.load(folder/correction['field_file'],allow_pickle=False)
   expected_rhs=-(A@previous[free]-rhs[free,index])
   actual_rhs=np.load(folder/correction['equation_rhs_file'],allow_pickle=False)
   assert actual_rhs.dtype==np.float64 and actual_rhs.tobytes()==expected_rhs.tobytes()
   assert np.array_equal(v[free],(actual_rhs/diag)*omega) and np.all(v[fixed]==0.)
   assert np.array_equal(u,previous+v)
   b=np.zeros(344103);b[free]=actual_rhs
   check(v,b,correction['equation_residual']);result['correction_fields_checked']+=1
   check(u,rhs[:,index],iteration['equation_residual']);result['outer_fields_checked']+=1
   actual=np.load(folder/iteration['actual_update_file'],allow_pickle=False)
   assert np.array_equal(actual,u-previous);result['actual_update_fields_checked']+=1
   for entry,value,equation_rhs in [(correction,v[free],actual_rhs),(iteration,u[free],rhs[free,index])]:
    stored_rhs=np.load(folder/entry['equation_rhs_file'],allow_pickle=False);stored_error=np.load(folder/entry['residual_file'],allow_pickle=False)
    assert np.array_equal(stored_rhs,equation_rhs) and np.array_equal(stored_error,A@value-equation_rhs)
    ex=extended@value.astype(np.longdouble)-equation_rhs.astype(np.longdouble)
    assert float(np.max(np.abs(ex)))/entry['equation_residual']['normalization_denominator']==entry['longdouble_equation_residual_ratio_diagnostic_only']
   obs=iteration['update_observation'];old=previous[free];new=u[free];request=v[free];delta=actual[free]
   changed=new!=old;requested=request!=0.;old_bits=old.view(np.uint64);new_bits=new.view(np.uint64);sign=np.uint64(1<<63)
   lo=np.where((old_bits&sign)!=0,~old_bits,old_bits^sign);hi=np.where((new_bits&sign)!=0,~new_bits,new_bits^sign)
   ulps=(np.maximum(lo,hi)-np.minimum(lo,hi))[changed]
   checks={'requested_nonzero_DOFs':int(np.count_nonzero(requested)),
    'actually_changed_DOFs':int(np.count_nonzero(changed)),
    'nonzero_requests_rounded_to_no_change':int(np.count_nonzero(requested&~changed)),
    'actual_update_infinity_norm':float(np.max(np.abs(delta),initial=0.)),
    'requested_update_infinity_norm':float(np.max(np.abs(request),initial=0.)),
    'actual_minus_requested_infinity_norm':float(np.max(np.abs(delta-request),initial=0.)),
    'actual_update_free_sha256':array_sha(delta),'representational_stagnation':bool(not np.any(changed)),
    'ULP_distance_over_actually_changed_DOFs':{'maximum':int(np.max(ulps,initial=np.uint64(0))),
     'one':int(np.count_nonzero(ulps==1)),'two_to_four':int(np.count_nonzero((ulps>=2)&(ulps<=4))),
     'five_to_sixteen':int(np.count_nonzero((ulps>=5)&(ulps<=16))),'more_than_sixteen':int(np.count_nonzero(ulps>16))}}
   assert obs==checks
   result['updates'].append({'probe_index':index,'outer_iteration':step,**checks})
   previous=u.copy();passed=iteration['equation_residual']['passes_original_threshold']
  assert np.array_equal(previous,final[:,index])
  assert passed==row['passes_original_threshold']
  assert passed or step==32
  if baseline['passes']:
   assert step==0 and np.array_equal(initial[:,index],final[:,index])
   assert sha(folder/f'probe-{index}-final-field.npy')==prior['refined_probes'][index]['final_field_file_sha256']
   assert sha(folder/f'probe-{index}-baseline-field.npy')==prior['refined_probes'][index]['final_field_file_sha256']
 assert [r['passes'] for r in result['baseline']]==[False,True,True,True,True]
 result['independent_float64_RHS_damping_update_actual_change_ULP_and_last_field_chain_checked']=True
 result['no_best_selection_and_first_pass_or_32_updates_checked']=True
 result['four_prior_pass_fields_retain_exact_N4b_array_and_file_bytes']=True
 for name,digest in report['files_sha256'].items():
  p=folder/name;assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(folder.resolve()) and sha(p)==digest
 result['files_hash_checked']=len(report['files_sha256'])
 result['five_original_gates_passed']=all(r['passes'] for r in result['final'])
 assert result['five_original_gates_passed']==report['refined_all_five_passed']
 assert sup['exit_code']==(0 if result['five_original_gates_passed'] else 2)
 for name in ('H_action_restore_executed','complete_body_response_accepted','new_QP_executed','candidate_go','fixture_fabrication_go','manufacturing_go'):assert report[name] is False
 result.update(completed=True,probe_execution_state='completed_all_five',diagnostic_completed=True,
  supervisor_stop_reason=sup['resource_stop_reason'],supervisor_exit_code=sup['exit_code'])
except BaseException as exc:
 result['failure_type']=type(exc).__name__;result['failure']=str(exc)
 (root/'N5-independent-field-readback.json').write_text(json.dumps(result,indent=2)+'\n')
 raise
(root/'N5-independent-field-readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('updates',)},indent=2))
