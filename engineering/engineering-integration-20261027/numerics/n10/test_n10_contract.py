"""Small stdlib controls for the actual N9 counterexample and N10 evidence rules.

No NumPy/SciPy import, matrix assembly, native sparse multiplication or solve.
These controls do not alter S4's historical test count or confer qualification.
"""
from pathlib import Path
import argparse
import ast
from fractions import Fraction
import hashlib
import json
import math
import struct
import tempfile
import unittest
import n10_contract as contract
from export_n10_engineering import export, frozen_reference_ledger, private_strings_forbidden

HERE=Path(__file__).parent
CONTROL=json.loads((HERE/'N10_CAPACITY_CONTROL.json').read_text())

def selected_functions(filename,names):
    tree=ast.parse((HERE/filename).read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    namespace={'math':math,'Fraction':Fraction,'ULP_STEPS':contract.ULP_STEPS,
               'MAX_FRACTION_BITS':contract.MAX_FRACTION_BITS,'LIMIT':contract.LIMIT,
               'require':contract.require,'bits':contract.bits}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'),namespace)
    return namespace

PRODUCER=selected_functions('probe_n10_coordinates.py',
    ['candidate_specs','changed_values','ordered_row_dot','acceptance_conditions'])
READER=selected_functions('readback_n10_coordinates.py',['specification_at','Q','packed','unpack'])

def rational(row):return Fraction(int(row['numerator']),int(row['denominator']))

def target_components():
    rows=CONTROL['ordered_target_row']
    columns=[r['DOF'] for r in rows]
    coefficients=[float.fromhex(r['coefficient_hex']) for r in rows]
    values={r['DOF']:float.fromhex(r['value_hex']) for r in rows}
    exact_dot=sum((Fraction.from_float(a)*Fraction.from_float(values[j]) for j,a in zip(columns,coefficients)),Fraction())
    exact_rhs=exact_dot-rational(CONTROL['exact_base_target'])
    assert Fraction.from_float(float(exact_rhs))==exact_rhs
    return columns,coefficients,values,float(exact_rhs)

class Controls(unittest.TestCase):
    def test_original_114_scalar_bits_are_preserved(self):
        columns,coefficients,values,rhs=target_components()
        records=CONTROL['all_114_adjacent_target_bits']
        self.assertEqual(len(records),114)
        for row in records:
            changed=dict(values);direction=row['direction']
            changed[row['column']]=math.nextafter(changed[row['column']],math.copysign(math.inf,direction))
            dot=PRODUCER['ordered_row_dot'](coefficients,[changed[j] for j in columns])-rhs
            self.assertEqual(contract.bits(dot),row['bits'])
            self.assertEqual(abs(dot)/CONTROL['normalization_denominator']<=contract.LIMIT,row['pass'])

    def test_all_904_positions_and_original_paired_candidates(self):
        columns,coefficients,values,rhs=target_components();target=CONTROL['target_original_DOF']
        descriptors=list(PRODUCER['candidate_specs'](columns,target,-1))
        self.assertEqual(len(descriptors),904)
        for index,value in enumerate(descriptors,1):
            self.assertEqual(value,READER['specification_at'](index,columns,target,-1))
        with self.assertRaises(contract.GateError):READER['specification_at'](905,columns,target,-1)
        for candidate in CONTROL['coupled_candidates']:
            kind,spec=descriptors[candidate['index']-1]
            self.assertEqual(kind,'paired')
            changed,deltas,records=PRODUCER['changed_values'](values,spec,{j:j for j in columns})
            self.assertEqual([(r['original_DOF'],r['direction'],r['ULP_steps']) for r in records],
                             [(r['DOF'],r['direction'],r['ULP_steps']) for r in candidate['changes']])
            for actual,original in zip(records,candidate['changes']):
                self.assertEqual((actual['old_value_hex'],actual['new_value_hex'],actual['actual_delta_hex']),
                                 (original['old_hex'],original['new_hex'],original['delta_hex']))
            total=PRODUCER['ordered_row_dot'](coefficients,[changed.get(j,values[j]) for j in columns])-rhs
            self.assertEqual(contract.bits(total),candidate['target_predicted_residual_bits'])
            self.assertFalse(candidate['native_full_five_gate_executed'])

    def test_two_actual_full_support_exact_certificates(self):
        candidates={r['index']:r for r in CONTROL['coupled_candidates']}
        for certificate in CONTROL['coupled_full_affected_certificates']:
            candidate=candidates[certificate['candidate_index']]
            deltas={str(r['DOF']):Fraction.from_float(float.fromhex(r['delta_hex'])) for r in candidate['changes']}
            rows=certificate['all_affected_rows'];self.assertEqual(len(rows),candidate['affected_rows'])
            self.assertEqual(len({r['DOF'] for r in rows}),len(rows))
            self.assertNotIn(candidate['anchor_original_DOF'],[r['DOF'] for r in rows])
            after_values=[]
            for row in rows:
                prediction=rational(row['exact_before'])
                for dof,delta in deltas.items():prediction+=Fraction.from_float(float.fromhex(row['changed_column_coefficients_hex'][dof]))*delta
                self.assertEqual(prediction,rational(row['exact_after']));after_values.append(abs(prediction))
            maximum=max(after_values)
            self.assertEqual(maximum,rational(candidate['affected_exact_infinity_after']))
            self.assertLessEqual(maximum,abs(rational(candidate['anchor_exact'])))
            self.assertLess(candidate['predicted_whole_probe0_violating_rows'],15)
            self.assertLessEqual(candidate['predicted_whole_original_probe0_ratio'],CONTROL['current_N9_five_ratios'][0])

    def test_actual_N9_single_coordinate_rejection_remains_a_rejection(self):
        trial=CONTROL['actual_rejected_trial2']
        old=[{'free_dof_residual_infinity_ratio':r,'over_gate_row_count':15 if j==0 else 0,
              'passes_original_threshold':r<=contract.LIMIT} for j,r in enumerate(CONTROL['current_N9_five_ratios'])]
        result=PRODUCER['acceptance_conditions'](trial['exact_affected_proof'],old,trial['probes'])
        self.assertEqual(result,trial['acceptance_conditions'])
        self.assertFalse(all(result.values()));self.assertFalse(trial['accepted'])
        self.assertFalse(result['global_exact_infinity_nonincrease_certificate'])
        self.assertFalse(result['probe0_violation_count_strictly_decreases'])
        self.assertFalse(result['original_full_five_max_ratio_nonincrease'])

    def test_original_domain_and_strict_independent_reader_import_boundary(self):
        frozen=contract.load_frozen_contract()
        self.assertEqual(len(frozen['members']),22)
        self.assertEqual(sum(x['bytes'] for x in frozen['members'].values()),382222748)
        self.assertEqual(contract.FIXED,(0,1,2,13,14,8))
        self.assertEqual((contract.WALL_SECONDS,contract.AS_BYTES,contract.OUTPUT_BYTES,contract.RESERVE_BYTES),
                         (180,4831838208,1610612736,524288000))
        self.assertEqual((contract.MAX_FULL,contract.MAX_SCALAR,contract.LIMIT),(96,8192,1e-7))
        tree=ast.parse((HERE/'readback_n10_coordinates.py').read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module or '')
        self.assertFalse(any('probe_n10' in name or 'probe_n9' in name for name in imports))
        self.assertEqual([name for name in imports if name.endswith('_contract')],['n10_contract'])

    def test_all_eight_references_require_actual_original_identity(self):
        frozen=contract.load_frozen_contract();copied={};probes=[{}]
        for j in range(1,5):
            row={'scientific_storage':'explicit_frozen_original_field_and_residual_reference',
                 'new_native_residual_equals_frozen_original_array_bytes':True}
            for label in ('field','residual'):
                source=f'probe-N9/final/probe-{j}-{label}.npy';relative='frozen/'+source;ident=frozen['members'][source]
                row[label+'_file']=relative;row[label+'_identity']=ident
                copied[relative]={**ident,'original_bytes':True}
            probes.append(row)
        records,missing=frozen_reference_ledger({1:{'probes':probes}},{1},frozen,copied)
        self.assertEqual((len(records),len(missing)),(8,0))
        copied['frozen/probe-N9/final/probe-4-residual.npy']['sha256']='0'*64
        _,missing=frozen_reference_ledger({1:{'probes':probes}},{1},frozen,copied)
        self.assertEqual(len(missing),1)
        _,missing=frozen_reference_ledger({1:{}},{1},frozen,copied)
        self.assertEqual(len(missing),8)

    def test_true_partial_virtual_and_array_evidence_never_claims_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);case=base/'case';folder=case/'probe-N10';folder.mkdir(parents=True)
            (folder/'N10_SCREEN_ATTEMPTS.jsonl').write_bytes(b'{"schema":"razr-N10-virtual-attempt-v1","screen_index":1}\n{"schema":')
            (folder/'N10_SCALAR_SCREENS.jsonl').write_bytes(b'{"schema":"razr-N10-virtual-support-screen-v1","screen_index":1}\n')
            (folder/'N10_REPORT.json.writing').write_bytes(b'')
            trial=folder/'trial-01';trial.mkdir();(trial/'requested-update.npy.writing').write_bytes(b'\x93NUMPY\x01\x00')
            out=base/'export';export(case,out)
            m=json.loads((out/'EXPORT_MANIFEST.json').read_text());actual=m['scientific_preservation_actual']
            self.assertFalse(actual['all_22_selected_complete_inputs_identity_verified'])
            self.assertFalse(actual['all_started_full_candidates_all5_fields_and_residuals_recoverable'])
            self.assertFalse(actual['all_ten_final_arrays_present'])
            self.assertEqual(len(actual['missing_selected_complete_inputs']),22)
            self.assertEqual(len(actual['missing_or_incomplete_candidate_frozen_references']),8)
            self.assertTrue(m['virtual_record_preservation_actual'][1]['last_record_is_partial'])
            self.assertEqual((out/'probe-N10/N10_REPORT.json.writing').read_bytes(),b'')
            self.assertFalse(m['raw_runtime_records_exported'])
            (folder/'N10_SCREEN_ATTEMPTS.jsonl').write_bytes(b'{"schema":"razr-N10-virtual-attempt-v1","unexpected":true}\n')
            with self.assertRaises(ValueError):export(case,base/'unknown')
            (folder/'N10_SCREEN_ATTEMPTS.jsonl').write_bytes(b'{"schema":"razr-N10-virtual-attempt-v1","base_field_sha256":"/tmp/private')
            with self.assertRaises(ValueError):export(case,base/'private')
            for value in ('/tmp/a','/proc/123/x','/workspace/x','/home/x','/dev/shm/x','name@example.com'):
                with self.assertRaises(ValueError):private_strings_forbidden({'x':value})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    record={'schema':'razr-N10-small-contract-results-v1','tests_run':result.testsRun,
        'failure_count':len(result.failures),'error_count':len(result.errors),'passed':result.wasSuccessful(),
        'historical_S4_test_count_modified':False,'original_N9_rejection_retained':True,
        'finite_904_order_and_114_original_predictions_checked':True,
        'two_full_affected_exact_capacity_certificates_checked':True,'native_numeric_execution':False,
        'test_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if args.output:args.output.write_text(json.dumps(record,indent=2)+'\n')
    return 0 if result.wasSuccessful() else 2

if __name__=='__main__':raise SystemExit(main())
