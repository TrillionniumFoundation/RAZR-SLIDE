"""Eight bounded stdlib controls; never added to historical S4 test counts."""
from pathlib import Path
import argparse
import ast
from fractions import Fraction
import hashlib
import json
import math
import sys
import tempfile
import unittest
import n8_contract as contract
from export_n8_engineering import export, frozen_reference_ledger

HERE=Path(__file__).resolve().parent
WORKER=(HERE/"probe_n8_coordinates.py").read_text()
TREE=ast.parse(WORKER)
pure_names={"qpack","exact_product","ordered_row_dot","row_screen","acceptance_conditions","select_unaffected_anchor","ExactCache"}
nodes=[n for n in TREE.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in pure_names]
G={**vars(contract),"Fraction":Fraction,"math":math,"sys":sys}
exec(compile(ast.Module(body=nodes,type_ignores=[]),"<actual-N8-pure-functions>","exec"),G)
CONTROL=json.loads((HERE/"N7_ROW_SCREEN_CONTROL.json").read_text())
ANCHOR_CONTROL=json.loads((HERE/"N8_ANCHOR_CONTROL.json").read_text())
SOURCE_ROOT=None
TMP_ROOT=None

class FakeCSR:
    def __init__(self):
        self.indptr=[0,1,2]
        self.indices=[0,0]
        self.data=[1.0,1.0]

class Contracts(unittest.TestCase):
    def test_all_162_original_row_screens_and_native_baseline_replay(self):
        co=[float.fromhex(x) for x in CONTROL["coefficients_hex"]]
        u=[float.fromhex(x) for x in CONTROL["values_hex"]]
        exact=Fraction(int(CONTROL["exact_row_before"]["numerator"]),int(CONTROL["exact_row_before"]["denominator"]))
        b=float.fromhex(CONTROL["RHS_hex"])
        self.assertEqual(contract.bits(G["ordered_row_dot"](co,u)-b),CONTROL["native_row_residual_bits"])
        self.assertEqual(sum((Fraction.from_float(a)*Fraction.from_float(v) for a,v in zip(co,u)),Fraction())-Fraction.from_float(b),exact)
        good=0
        for t in CONTROL["trials"]:
            new,delta,r=G["row_screen"](co,u,t["support_index"],t["direction"],b,exact,CONTROL["denominator"])
            self.assertEqual(new.hex(),t["new_hex"])
            self.assertEqual(r["predicted_original_order_float64_residual_bits"],t["residual_bits"])
            self.assertEqual(r["predicted_row_ratio"],t["ratio"])
            self.assertEqual(r["exact_row_after"],t["exact_after"])
            self.assertEqual(r["eligible_for_full_candidate"],t["eligible"])
            self.assertFalse(r["native_full_gate_evaluated_by_this_screen"])
            good+=t["eligible"]
        self.assertEqual(len(CONTROL["trials"]),162);self.assertEqual(good,7)

    def test_all_affected_norm_rejects_target_only_improvement(self):
        cache=G["ExactCache"](FakeCSR(),[0.0,2.0],[59009,59010])
        delta=Fraction.from_float(math.nextafter(1.0,-math.inf))-Fraction(1)
        changes,proof=cache.candidate([0,1],[1.0,1.0],delta,[1.0],"0"*64)
        self.assertLess(abs(changes[0]),abs(cache.values[0]))
        self.assertGreater(abs(changes[1]),abs(cache.values[1]))
        self.assertFalse(proof["all_affected_exact_infinity_nonincrease"])
        self.assertEqual(cache.values,{0:Fraction(1),1:Fraction(-1)})
        self.assertEqual(proof["affected_row_count"],2)
        self.assertEqual(cache.reader_terms_registered,4)

    def test_finite_cache_terms_rows_and_memory_limits(self):
        cache=G["ExactCache"](FakeCSR(),[0.0,2.0],[59009,59010])
        cache.terms=contract.MAX_EXACT_TERMS
        with self.assertRaises(contract.CapacityStop):cache.get(0,[1.0])
        cache=G["ExactCache"](FakeCSR(),[0.0,2.0],[59009,59010])
        cache.values={i+10:Fraction() for i in range(contract.MAX_CACHE_ROWS)}
        with self.assertRaises(contract.CapacityStop):cache.get(0,[1.0])
        cache=G["ExactCache"](FakeCSR(),[0.0,2.0],[59009,59010])
        cache.storage_estimate_bytes=contract.MAX_CACHE_BYTES
        with self.assertRaises(contract.CapacityStop):cache.get(0,[1.0])
        cache=G["ExactCache"](FakeCSR(),[0.0,2.0],[59009,59010])
        cache.reader_terms_registered=contract.MAX_READER_EXACT_TERMS
        with self.assertRaises(contract.CapacityStop):cache.candidate([0],[1.0],Fraction(1,2),[1.0],"0"*64)

    def test_exact_gate_violation_and_global_conditions_are_all_required(self):
        old=[{"free_dof_residual_infinity_ratio":1.8e-7,"over_gate_row_count":20,"passes_original_threshold":False}]
        old += [{"free_dof_residual_infinity_ratio":1e-9,"over_gate_row_count":0,"passes_original_threshold":True} for _ in range(4)]
        new=[dict(x) for x in old];new[0].update(free_dof_residual_infinity_ratio=1.6e-7,over_gate_row_count=19)
        yes={"global_exact_infinity_nonincrease_certified":True}
        self.assertTrue(all(G["acceptance_conditions"](yes,old,new).values()))
        self.assertFalse(all(G["acceptance_conditions"]({"global_exact_infinity_nonincrease_certified":False},old,new).values()))
        new[0]["over_gate_row_count"]=20
        self.assertFalse(all(G["acceptance_conditions"](yes,old,new).values()))
        new[0]["over_gate_row_count"]=19;new[0]["free_dof_residual_infinity_ratio"]=2e-7
        self.assertFalse(all(G["acceptance_conditions"](yes,old,new).values()))

    def test_actual_N7_anchor_certificate_and_unaffected_negative_controls(self):
        q=lambda x:Fraction(int(x["numerator"]),int(x["denominator"]))
        known={x["original_DOF"]:q(x["signed_exact_residual"]) for x in ANCHOR_CONTROL["known_current_top_16"]}
        trial=next(x for x in ANCHOR_CONTROL["candidates"] if x["N7_trial_index"]==4)
        free=sorted(set(known)|set(trial["affected_rows"]))
        index={d:i for i,d in enumerate(free)}
        values={index[d]:v for d,v in known.items()};affected=[index[d] for d in trial["affected_rows"]]
        after=q(trial["affected_after_exact_infinity"]);seed=index[59009]
        chosen=G["select_unaffected_anchor"](values,affected,free,after,seed)
        self.assertEqual(chosen,seed);self.assertNotIn(seed,affected)
        self.assertEqual(abs(values[chosen])-after,q(trial["exact_anchor_margin"]))
        self.assertGreater(abs(values[chosen]),after)
        self.assertFalse(trial["original_N7_acceptance_conditions"]["all_affected_exact_infinity_nonincrease"])
        self.assertTrue(trial["original_N7_acceptance_conditions"]["probe0_violation_count_strictly_decreases"])
        blocked=G["select_unaffected_anchor"](values,affected+[seed],free,after,seed)
        self.assertNotEqual(blocked,seed);self.assertLess(abs(values[blocked]),after)
        too_large=abs(values[seed])+Fraction(1,2**100)
        blocked=G["select_unaffected_anchor"](values,affected,free,too_large,seed)
        self.assertLess(abs(values[blocked]),too_large)
        self.assertFalse(ANCHOR_CONTROL["N7_rules_or_rejections_rewritten"])
        self.assertFalse(ANCHOR_CONTROL["new_native_execution"])

    def test_all_eight_frozen_references_require_actual_hash_ledger_and_explicit_records(self):
        frozen=contract.load_frozen_contract();copied={};probes=[{}]
        for j in range(1,5):
            rec={"scientific_storage":"explicit_frozen_original_field_and_residual_reference",
                 "new_native_residual_equals_frozen_original_array_bytes":True}
            for kind in ("field","residual"):
                source=f"probe-N7/final/probe-{j}-{kind}.npy";relative="frozen/"+source
                ident=frozen["members"][source]
                copied[relative]={**ident,"original_bytes":True}
                rec[kind+"_file"]=relative;rec[kind+"_identity"]=dict(ident)
            probes.append(rec)
        records,missing=frozen_reference_ledger({1:{"probes":probes}},{1},frozen,copied)
        self.assertEqual(len(records),8);self.assertEqual(missing,[])
        victim="frozen/probe-N7/final/probe-3-residual.npy"
        saved=copied.pop(victim)
        records,missing=frozen_reference_ledger({1:{"probes":probes}},{1},frozen,copied)
        self.assertEqual(len(missing),1);self.assertFalse(missing[0]["referenced_original_bytes_present_and_hash_verified"])
        copied[victim]=saved
        probes[3]["residual_identity"]["sha256"]="0"*64
        records,missing=frozen_reference_ledger({1:{"probes":probes}},{1},frozen,copied)
        self.assertEqual(len(missing),1);self.assertFalse(missing[0]["explicit_report_reference_matches"])
        records,missing=frozen_reference_ledger({1:{}},{1},frozen,copied)
        self.assertEqual(len(missing),8)

    def test_original_float64_residual_functions_and_independent_reader_identity(self):
        original=(SOURCE_ROOT/contract.HELPER).read_text()
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),contract.HELPER_SHA)
        ot=ast.parse(original)
        for name in ("array_sha","residual_record"):
            before=next(n for n in ot.body if isinstance(n,ast.FunctionDef) and n.name==name)
            after=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))
        rt=ast.parse((HERE/"readback_n8_coordinates.py").read_text())
        for node in ast.walk(rt):
            if isinstance(node,ast.ImportFrom):self.assertNotEqual(node.module,"probe_n8_coordinates")
            if isinstance(node,ast.Import):
                self.assertNotIn("probe_n8_coordinates",[x.name for x in node.names])
        self.assertEqual(contract.FIXED,(0,1,2,13,14,8))
        self.assertEqual((contract.MAX_FULL,contract.MAX_SCALAR,contract.WALL_SECONDS),(96,8192,180))

    def test_export_scientific_partial_allowlist_and_private_rejection(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as td:
            base=Path(td);case=base/"case";case.mkdir()
            array=case/"probe-N8/trial-01/probe-0-field.npy.writing"
            array.parent.mkdir(parents=True)
            header=repr({"descr":"<f8","fortran_order":False,"shape":(344103,)})
            raw=bytes([147])+b"NUMPY"+bytes([1,0])+(118).to_bytes(2,"little")+(header+" "*(117-len(header))+"\n").encode()
            self.assertEqual(len(raw),128);array.write_bytes(raw)
            (case/"raw-environment.json").write_text('{"private":"person@example.invalid"}')
            fragment=case/"probe-N8/N8_REPORT.json.writing"
            fragment.write_bytes(b'{"schema":"razr-N8-finite-original-five-probe-v1","completed":false,')
            out=base/"export";export(case,out)
            self.assertEqual((out/array.relative_to(case)).read_bytes(),raw)
            self.assertFalse((out/"raw-environment.json").exists())
            manifest=json.loads((out/"EXPORT_MANIFEST.json").read_text())
            self.assertIn(array.relative_to(case).as_posix(),manifest["scientific_fragments"])
            self.assertIn(fragment.relative_to(case).as_posix(),manifest["scientific_fragments"])
            self.assertEqual((out/fragment.relative_to(case)).read_bytes(),fragment.read_bytes())
            actual=manifest["scientific_preservation_actual"]
            self.assertFalse(actual["all_22_selected_complete_inputs_identity_verified"])
            self.assertFalse(actual["all_started_full_candidate_new_arrays_complete"])
            self.assertFalse(actual["all_ten_final_arrays_present"])
            self.assertEqual(len(actual["missing_selected_complete_inputs"]),22)
            self.assertEqual(actual["started_full_candidate_indices"],[1])
            self.assertEqual(len(actual["missing_complete_candidate_arrays"]),4)
            self.assertFalse(actual["all_started_full_candidates_all5_fields_and_residuals_recoverable"])
            self.assertEqual(len(actual["missing_or_incomplete_candidate_frozen_references"]),8)
            bad=case/"probe-N8/N8_REPORT.json"
            bad.write_text(json.dumps({"schema":"razr-N8-finite-original-five-probe-v1","completed":False,"unexpected":"value"}))
            with self.assertRaises(ValueError):export(case,base/"bad-unknown")
            bad.write_text(json.dumps({"schema":"razr-N8-finite-original-five-probe-v1","completed":False,"failure_type":"person@example.invalid"}))
            with self.assertRaises(ValueError):export(case,base/"bad-private")
            bad.unlink()
            fragment.write_bytes(b'{"schema":"razr-N8-finite-original-five-probe-v1","value":"/tmp/private')
            with self.assertRaises(ValueError):export(case,base/"bad-partial-tmp")
            fragment.write_bytes(b'{"schema":"razr-N8-finite-original-five-probe-v1","value":"/proc/123/private')
            with self.assertRaises(ValueError):export(case,base/"bad-partial-proc")
            fragment.unlink()
            array.write_bytes(bytes([147])+b"NUMPY"+bytes([1,0])+b"/tmp/private")
            with self.assertRaises(ValueError):export(case,base/"bad-NPY-header-tmp")
            array.write_bytes(bytes([147])+b"NUMPY"+bytes([1,0])+b"/proc/123/private")
            with self.assertRaises(ValueError):export(case,base/"bad-NPY-header-proc")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--tmp-root",type=Path)
    args=p.parse_args();SOURCE_ROOT=args.source_root;TMP_ROOT=args.tmp_root
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Contracts)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt={"schema":"razr-N8-small-contract-results-v1","tests_run":result.testsRun,
        "failure_count":len(result.failures),"error_count":len(result.errors),"passed":result.wasSuccessful(),
        "historical_S4_test_count_modified":False,"original_N6b_162_row_screens_replayed":result.wasSuccessful(),
        "original_N7_anchor_counterexample_replayed":result.wasSuccessful(),
        "test_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(receipt,indent=2)+"\n")
    raise SystemExit(0 if result.wasSuccessful() else 2)
