"""Finite stdlib controls for N12 target order, witnesses and preservation.

No NumPy/SciPy import, sparse operator, matrix assembly or solver.
"""
from pathlib import Path
import argparse,ast,hashlib,json,math,tempfile,unittest
from fractions import Fraction
import n12_contract as contract
from export_n12_engineering import export,frozen_reference_ledger,private_strings_forbidden
HERE=Path(__file__).parent
CONTROL=json.loads((HERE/'N12_CAPACITY_CONTROL.json').read_text())
CAPACITY=CONTROL['original_capacity_actual_result']
def selected_functions(name,names):
 tree=ast.parse((HERE/name).read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assert {n.name for n in nodes}==set(names)
 namespace={'math':math,'Fraction':Fraction,'require':contract.require,'bits':contract.bits}
 namespace.update({k:getattr(contract,k) for k in ['ULP_STEPS','MAX_FRACTION_BITS','LIMIT','INITIAL_EXHAUSTED_TARGET_DOF','MAX_TARGETS_PER_FIELD','BASE_FIELD_SHA']})
 exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),namespace);return namespace
P=selected_functions('probe_n12_coordinates.py',['ordered_target_indices','candidate_specs','changed_values','ordered_row_dot','acceptance_conditions'])
R=selected_functions('readback_n12_coordinates.py',['specification_at','Q','packed','unpack'])
def q(x):return Fraction(int(x['numerator']),int(x['denominator']))
class Controls(unittest.TestCase):
 def test_current_field_target_order_ties_and_initial_exhaustion(self):
  rows=CAPACITY['current_all_violating_rows'];free=[r['original_DOF'] for r in rows]
  error=[float.fromhex('0x0p+0') for _ in rows]
  import struct
  error=[struct.unpack('>d',bytes.fromhex(r['residual_bits']))[0] for r in rows]
  indices=P['ordered_target_indices'](error,free,CAPACITY['current_original_five_ratios'][0] and abs(error[0])/CAPACITY['current_original_five_ratios'][0],contract.BASE_FIELD_SHA)
  self.assertEqual([free[i] for i in indices],[196556,202034,159161])
  den=abs(error[0])/CAPACITY['current_original_five_ratios'][0]
  self.assertEqual([free[i] for i in P['ordered_target_indices'](error,free,den,'0'*64)],[54122,196556,202034])
  free.reverse();error.reverse()
  self.assertEqual([free[i] for i in P['ordered_target_indices'](error,free,den,'0'*64)],[54122,196556,202034])
  self.assertEqual(P['ordered_target_indices']([0.0,0.0],[54122,196556],1.0,contract.BASE_FIELD_SHA),[])
 def test_complete_original_candidate_order_and_first_five_actual_bits(self):
  stage=CAPACITY['stages'][0];rows=stage['ordered_original_row'];columns=[r['original_column_DOF'] for r in rows]
  coeff=[float.fromhex(r['coefficient_hex']) for r in rows];values={r['original_column_DOF']:float.fromhex(r['value_hex']) for r in rows}
  exact=sum((Fraction.from_float(a)*Fraction.from_float(values[j]) for j,a in zip(columns,coeff)),Fraction())
  rhs=exact-q(stage['exact_target_before']);self.assertEqual(Fraction.from_float(float(rhs)),rhs)
  specs=list(P['candidate_specs'](columns,196556,-1));self.assertEqual(len(specs),1096)
  for i,spec in enumerate(specs,1):self.assertEqual(spec,R['specification_at'](i,columns,196556,-1))
  with self.assertRaises(contract.GateError):R['specification_at'](1097,columns,196556,-1)
  for record in CAPACITY['candidate_records']:
   kind,spec=specs[record['stage_position']-1]
   self.assertEqual((kind,[list(x) for x in spec]),(record['kind'],record['specification']))
   changed,delta,description=P['changed_values'](values,spec,{j:j for j in columns})
   native=P['ordered_row_dot'](coeff,[changed.get(j,values[j]) for j in columns])-float(rhs)
   self.assertEqual(contract.bits(native),record['target_predicted_bits'])
   predicted=q(stage['exact_target_before'])+sum((Fraction.from_float(dict(zip(columns,coeff))[j])*delta[j] for j in changed),Fraction())
   self.assertEqual(predicted,q(record['exact_target_after']))
  self.assertEqual(specs[4],('single',[(3110,-1,1)]))
  self.assertEqual([r['global_index'] for r in CAPACITY['candidate_records'] if r['eligible_for_full_native_candidate']],[5])
 def test_complete_affected_exact_and_unaffected_anchor_certificate(self):
  certificate=CAPACITY['first_eligible_complete_support_certificate'];proof=certificate['all_affected_rows_and_anchor']
  changes=certificate['coordinate_changes'];delta={r['original_DOF']:Fraction.from_float(float.fromhex(r['actual_delta_hex'])) for r in changes}
  rows=proof['all_affected_rows'];self.assertEqual(len(rows),96);self.assertEqual(len({r['original_row_DOF'] for r in rows}),96)
  maximum=Fraction()
  for row in rows:
   value=q(row['exact_before'])+sum((Fraction.from_float(float.fromhex(a['coefficient_hex']))*delta[a['original_column_DOF']] for a in row['coefficients']),Fraction())
   self.assertEqual(value,q(row['exact_after']));maximum=max(maximum,abs(value))
  self.assertEqual(maximum,q(proof['affected_exact_infinity_after']))
  anchor=proof['anchor'];self.assertEqual(anchor['original_DOF'],59009)
  self.assertNotIn(59009,[r['original_row_DOF'] for r in rows]);self.assertLessEqual(maximum,abs(q(anchor['signed_exact_residual'])))
  self.assertEqual(anchor['base_field_sha256'],contract.BASE_FIELD_SHA)
  self.assertTrue(certificate['not_an_actual_native_five_probe_evaluation']);self.assertFalse(CAPACITY['original_full_five_gate_evaluated'])
 def test_auxiliary_acceptance_cannot_replace_original_five_gate(self):
  old=[{'free_dof_residual_infinity_ratio':x,'over_gate_row_count':12 if i==0 else 0,'passes_original_threshold':x<=contract.LIMIT} for i,x in enumerate(CAPACITY['current_original_five_ratios'])]
  new=[dict(x) for x in old];new[0]['over_gate_row_count']=11
  self.assertTrue(all(P['acceptance_conditions']({'global_exact_infinity_nonincrease_certified':True},old,new).values()))
  self.assertFalse(all(x['passes_original_threshold'] for x in new))
  self.assertFalse(all(P['acceptance_conditions']({'global_exact_infinity_nonincrease_certified':False},old,new).values()))
  new[0]['over_gate_row_count']=12
  self.assertFalse(all(P['acceptance_conditions']({'global_exact_infinity_nonincrease_certified':True},old,new).values()))
 def test_original_source_gate_domain_guard_and_independent_import_boundary(self):
  frozen=contract.load_frozen_contract();self.assertEqual(len(frozen['members']),22)
  self.assertEqual(sum(x['bytes'] for x in frozen['members'].values()),382222748)
  self.assertEqual(contract.FIXED,(0,1,2,13,14,8))
  self.assertEqual((contract.WALL_SECONDS,contract.AS_BYTES,contract.OUTPUT_BYTES,contract.RESERVE_BYTES),(180,4831838208,1610612736,524288000))
  self.assertEqual((contract.MAX_FULL,contract.MAX_SCALAR,contract.LIMIT,contract.INITIAL_VIOLATION_COUNT),(96,8192,1e-7,12))
  self.assertEqual(frozen['source_durable_asset_id'],680922058)
  imports=[]
  for node in ast.walk(ast.parse((HERE/'readback_n12_coordinates.py').read_text())):
   if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
   if isinstance(node,ast.ImportFrom):imports.append(node.module or '')
  self.assertFalse(any(x.startswith('probe_n') for x in imports));self.assertEqual([x for x in imports if x.endswith('_contract')],['n12_contract'])
 def test_all_eight_references_require_original_actual_identity(self):
  frozen=contract.load_frozen_contract();copied={};probes=[{}]
  for j in range(1,5):
   row={'scientific_storage':'explicit_frozen_original_field_and_residual_reference','new_native_residual_equals_frozen_original_array_bytes':True}
   for label in ('field','residual'):
    name=f'probe-N10/final/probe-{j}-{label}.npy';rel='frozen/'+name;ident=frozen['members'][name]
    row[label+'_file']=rel;row[label+'_identity']=ident;copied[rel]={**ident,'original_bytes':True}
   probes.append(row)
  records,missing=frozen_reference_ledger({1:{'probes':probes}},{1},frozen,copied);self.assertEqual((len(records),len(missing)),(8,0))
  copied['frozen/probe-N10/final/probe-4-residual.npy']['sha256']='0'*64
  self.assertEqual(len(frozen_reference_ledger({1:{'probes':probes}},{1},frozen,copied)[1]),1)
  self.assertEqual(len(frozen_reference_ledger({1:{}},{1},frozen,copied)[1]),8)
 def test_partial_preservation_and_privacy(self):
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);case=base/'case';folder=case/'probe-N12';folder.mkdir(parents=True)
   (folder/'N12_SCREEN_ATTEMPTS.jsonl').write_bytes(b'{"schema":"razr-N12-virtual-attempt-v1","screen_index":1}\n{"schema":')
   (folder/'N12_SCALAR_SCREENS.jsonl').write_bytes(b'{"schema":"razr-N12-virtual-support-screen-v1","screen_index":1}\n')
   (folder/'N12_REPORT.json.writing').write_bytes(b'')
   trial=folder/'trial-01';trial.mkdir();(trial/'requested-update.npy.writing').write_bytes(b'\x93NUMPY\x01\x00')
   out=base/'export';export(case,out);m=json.loads((out/'EXPORT_MANIFEST.json').read_text());a=m['scientific_preservation_actual']
   self.assertFalse(a['all_22_selected_complete_inputs_identity_verified']);self.assertFalse(a['all_started_full_candidates_all5_fields_and_residuals_recoverable']);self.assertFalse(a['all_ten_final_arrays_present'])
   self.assertEqual(len(a['missing_selected_complete_inputs']),22);self.assertEqual(len(a['missing_or_incomplete_candidate_frozen_references']),8)
   self.assertTrue(m['virtual_record_preservation_actual'][1]['last_record_is_partial']);self.assertFalse(m['raw_runtime_records_exported'])
   (folder/'N12_SCREEN_ATTEMPTS.jsonl').write_bytes(b'{"schema":"razr-N12-virtual-attempt-v1","unexpected":true}\n')
   with self.assertRaises(ValueError):export(case,base/'unknown')
   (folder/'N12_SCREEN_ATTEMPTS.jsonl').write_bytes(b'{"schema":"razr-N12-virtual-attempt-v1","base_field_sha256":"/tmp/private')
   with self.assertRaises(ValueError):export(case,base/'private')
   for value in ('/tmp/a','/proc/123/x','/workspace/x','/home/x','/dev/shm/x','name@example.com'):
    with self.assertRaises(ValueError):private_strings_forbidden({'x':value})
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 record={'schema':'razr-N12-small-contract-results-v1','tests_run':result.testsRun,'failure_count':len(result.failures),
  'error_count':len(result.errors),'passed':result.wasSuccessful(),'historical_S4_test_count_modified':False,
  'original_N10_and_N11_rejections_retained':True,'finite_target_order_and_first_capacity_witness_checked':True,
  'all_acceptance_and_native_resource_constants_unchanged':True,'native_numeric_execution':False,
  'test_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 if args.output:args.output.write_text(json.dumps(record,indent=2)+'\n')
 return 0 if result.wasSuccessful() else 2
if __name__=='__main__':raise SystemExit(main())
