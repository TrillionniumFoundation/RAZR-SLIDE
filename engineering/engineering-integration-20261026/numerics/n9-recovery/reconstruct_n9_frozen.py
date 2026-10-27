"""Recover frozen N9 bytes from immutable N8 and retained derivation records.

This is pure text/Fraction work, not a native numerical or FE run. Old SHA
records remain authoritative comparison targets; a mismatch is never relabeled
as recovered original bytes. Historical elapsed values are only used to restore
an already hashed historical document, while a separate recovery receipt records
the current work.
"""
from pathlib import Path
from fractions import Fraction
import ast
import gzip
import hashlib
import json
import math
import struct
import time

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'N8-published-source'
SCI=ROOT/'N8-original-scientific'
OUT=ROOT/'N9-reconstructed'
OUT.mkdir(exist_ok=True)
HEAD='0f86820367a4444796d9fe9f72b63d324ee5c3c5'
BASE='289153703ed68fd9b8161858195865a088325de58b0d66395f16844787c8420a'
ZIP_SHA='ac747737b52960596c6a35be47ba3d924f6276227d22a98be8fd3b1fde0d9d0e'
MAN_SHA='aa84d34b26847f308296809ff83002d32535a56a92eb09adcc7e42b571e88ee7'
OLD_BYTE_RECEIPT='0d11bf289bc0b2559705a8017f4095f15609736813acba498870cca77f6cff8d'
EXPECTED={
 'n9_contract.py':(4068,'3e0195cc248733d6cde63a540a961c86fcdbfde0cd402d06764b97c57494b385'),
 'fetch_n9_inputs.py':(8560,'94ea77c82c8201e9f68aed074d7dc6f2a68f76a5b3fa4dd8a365487f7c6a9fb1'),
 'probe_n9_coordinates.py':(31029,'013801678e9bbc3125469d4a6b18e57996eb3498cd2a0912bc584b170d04a933'),
 'readback_n9_coordinates.py':(33784,'3be80de01e78f6ecd326616b0c6d1ccfffc1ca367fdd3e8f488b1c0ffbea045e'),
 'export_n9_engineering.py':(25375,'724840ff06c03c19cd368b37704de7aa5be5fed9f2341600dbaaa587cc0577da'),
 'N9_STRATEGY.json':(16320,'3871da0d05166b94fe719c8d293c30fe21a37e0cb526c8eb00b9669b7c89f499'),
 'N9_FROZEN_INPUTS.json':(4868,'83eee2a51d60d4ccd60b3dac5095dc3cf9f6b3bcef9e42efa9ca10fc72a0f681'),
 'N7_ROW_SCREEN_CONTROL.json':(62138,'2f2c831d6f375d00f6dfc8ba1a81c5963fbab6220ed81ca181013f82d7eff462'),
 'N7_SCALAR_CAPACITY_SAMPLE.json':(1027,'44fadedb7a0dfd75c8c979273c1bde77a30ae0880e91e906b4d2d9d4e8641f61'),
 'N8_ANCHOR_CONTROL.json':(14826,'9bc59025d418f0eec086f4cabd6c9d868393fc7060b1e2b3676b5401931ad35f'),
 'N9_N8_LAST_STAGE_CONTROL.json':(45389,'ab8f7a89d8113c4151e6b654328814e9545fdc72fe7316109d07986e1e002aef'),
 'test_n9_contract.py':(16742,'954600656a16acdd0a5b5774770c1589ab406b6227e3178a417a257ad11527c5'),
 's4-panel-n9-hosted.yml':(376997,'596240794f140cdc55b947a472aa90a1e6782c95e2557f6c65f26015d346af36'),
 'N9_N8_LAST_STAGE_REPLAY.json':(3356,'10bfaccd909a78ed1770f77b462cedf8bebea508f687ed2377e445f1416d459a'),
 'N9_TREE_REQUEST.json':(680704,'b8f4d47bf9173cce528d3db6614756bab15e4b99edd894ee1d2f95253562e4e3'),
 'N9_TREE_REQUEST.json.gz':(127776,'6c2fc4c1b3feaa3305a2b7e347f271cc39bf1ca30043e873434038b8b3b5056a'),
}
records=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,b):
    if isinstance(b,str):b=b.encode()
    (OUT/name).write_bytes(b)
    expected=EXPECTED.get(name)
    item={'file':name,'bytes':len(b),'sha256':sha(b),'expected_pre_reset_bytes':expected[0] if expected else None,'expected_pre_reset_sha256':expected[1] if expected else None,'matches_retained_pre_reset_identity':(len(b),sha(b))==expected if expected else None}
    records.append(item)
    return item
def jwrite(name,v,compact=False):
    return write(name,json.dumps(v,separators=(',',':') if compact else None,indent=None if compact else 2,allow_nan=False)+'\n')
def old(name):return (SRC/name).read_text()
def replace(s,a,b,n=1):
    assert s.count(a)==n,(a,s.count(a),n)
    return s.replace(a,b)
def relabel(s):return s.replace('N8','N9').replace('n8','n9')
def qpack(x):return {'numerator':str(x.numerator),'denominator':str(x.denominator)}
def qunpack(x):return Fraction(int(x['numerator']),int(x['denominator']))
def bits(x):return struct.pack('>d',float(x)).hex()
def ordered(co,u):
    v=0.0
    for a,b in zip(co,u):v+=a*b
    return v

started=time.perf_counter()
s=relabel(old('n8_contract.py')).replace('probe-N7/final','probe-N8/final')
for a,b in [('d28f4626b3985612d14ab3b894e70b93f930c251f0239e8256593c979d4788b4',BASE),('ZIP_BYTES = 307198106','ZIP_BYTES = 238609175'),('2541e06e5c5dcc6a1797e5c85cde410a35056e4e23cae22b2ef9bb7759d85a1c',ZIP_SHA),('MANIFEST_BYTES = 167280','MANIFEST_BYTES = 166609'),('f911ecc8f08fe78526af1be49ea2292f94ee49e64789f514359196d7875d01b2',MAN_SHA)]:s=replace(s,a,b)
write('n9_contract.py',s)

s=relabel(old('fetch_n8_inputs.py')).replace('N7','N8')
for a,b in [('12633916809','12634369890'),('40285015238','40288924586'),('7de04d5570ce3fdce2e220a8e0db9eaab2d37812',HEAD),('len(manifest) == 129 and len(z.namelist()) == 130 and len(set(z.namelist())) == 130','len(manifest) == 86 and len(z.namelist()) == 87 and len(set(z.namelist())) == 87'),('8d23a2a4764bfa2db00bf6996560e8a579907eaa0a98e7b4d144bf8919ad33d0',OLD_BYTE_RECEIPT)]:
    assert a in s,a
    s=s.replace(a,b)
write('fetch_n9_inputs.py',s)

s=relabel(old('probe_n8_coordinates.py')).replace('probe-N7/final','probe-N8/final').replace('case/"frozen/frozen"','case/"frozen/frozen/frozen"').replace('N7_rejected_sequential_start','N8_rejected_sequential_start').replace('N7_last_sequential_accepted_starting_field','N8_last_sequential_accepted_starting_field')
s=replace(s,'"eligible_for_full_candidate": bool(ratio <= LIMIT and abs(exact_after) <= abs(exact_before))','"eligible_for_full_candidate": bool(ratio <= LIMIT)')
s=replace(s,'"finite adjacent-ULP coordinates with affected-maximum or unaffected-exact-anchor global nonincrease certificate"','"finite adjacent-ULP coordinates; predicted original row pass admits a complete trial; unchanged affected-maximum or unaffected-exact-anchor global nonincrease acceptance"')
write('probe_n9_coordinates.py',s)

s=relabel(old('readback_n8_coordinates.py')).replace('probe-N7/final','probe-N8/final').replace('case/"frozen/frozen"','case/"frozen/frozen/frozen"').replace('reader_N7_last_sequential_accepted_start','reader_N8_last_sequential_accepted_start')
s=replace(s,'eligible=ratio<=LIMIT and abs(after)<=abs(exact_before)','eligible=ratio<=LIMIT')
write('readback_n9_coordinates.py',s)

s=relabel(old('export_n8_engineering.py')).replace('N9_ANCHOR_CONTROL.json','N8_ANCHOR_CONTROL.json').replace('probe-N7/final','probe-N8/final').replace('source_N7_long_term_archive_status_at_registration','source_N8_long_term_archive_status_at_registration').replace('original N7 scientific manifest differs','original N8 scientific manifest differs')
s=replace(s,'"original_input_fields_source_artifact_id": 12633916809','"original_input_fields_source_artifact_id": 12634369890')
s=replace(s,'"N8_ANCHOR_CONTROL.json","test_n9_contract.py"]','"N8_ANCHOR_CONTROL.json","N9_N8_LAST_STAGE_CONTROL.json","test_n9_contract.py"]')
s=replace(s,'original_N6b_162_row_screens_replayed original_N7_anchor_counterexample_replayed test_source_sha256','original_N6b_162_numeric_predictions_and_historical_eligibility_checked original_N8_108_numeric_predictions_and_historical_eligibility_checked new_N9_eligibility_checked_separately original_N7_anchor_counterexample_replayed test_source_sha256')
write('export_n9_engineering.py',s)
for name in ['N7_ROW_SCREEN_CONTROL.json','N7_SCALAR_CAPACITY_SAMPLE.json','N8_ANCHOR_CONTROL.json']:write(name,(SRC/name).read_bytes())

rp=SCI/'probe-N8/N8_REPORT.json'; sp=SCI/'probe-N8/N8_SCALAR_SCREENS.jsonl'; rdp=SCI/'N8-independent-readback.json'
r=json.loads(rp.read_text()); rd=json.loads(rdp.read_text()); screens=[json.loads(x) for x in sp.read_text().splitlines()]
assert len(screens)==203
assert sha(rp.read_bytes())=='53635acef5e2f7112a3d8cb56d79794008d6e147f0f299e4dd56eadaffd06dad'
assert sha(sp.read_bytes())=='1d209f163d801494defd16be7289482d659455696f48d4352dc3a41e53ef7d35'
assert sha(rdp.read_bytes())=='e48b0f699c43a1bfc72fb4b46d36fdf7227e70d55a4275e81a164bf7c07ba3a3'
stage=r['stages'][-1]; selected=screens[95:203]; support=stage['ordered_support']
assert len(support)==54 and stage['base_field_sha256']==BASE
co=[float.fromhex(x['coefficient_hex']) for x in support]
values=[float.fromhex(selected[2*i]['old_value_hex']) for i in range(54)]
b=float(r['final'][0]['rhs_at_max_dof']); denominator=r['final'][0]['normalization_denominator']
before=sum((Fraction.from_float(a)*Fraction.from_float(u) for a,u in zip(co,values)),Fraction())-Fraction.from_float(b)
native_before=ordered(co,values)-b
assert native_before==r['final'][0]['signed_residual_at_max_dof']
controls=[]
for pos,original in enumerate(selected):
    at=pos//2; direction=-1 if pos%2==0 else 1
    proposed=values.copy(); new=math.nextafter(values[at],-math.inf if direction<0 else math.inf); proposed[at]=new
    delta=Fraction.from_float(new)-Fraction.from_float(values[at])
    native=ordered(co,proposed)-b; ratio=abs(native)/denominator
    after=sum((Fraction.from_float(a)*Fraction.from_float(u) for a,u in zip(co,proposed)),Fraction())-Fraction.from_float(b)
    nonincrease=abs(after)<=abs(before); eligible=ratio<=1e-7 and nonincrease
    assert original['base_field_sha256']==BASE and original['target_original_DOF']==160238
    assert original['support_index']==at and original['direction']==direction
    assert original['original_free_column_DOF']==support[at]['original_column_DOF']
    assert original['old_value_hex']==values[at].hex() and original['adjacent_value_hex']==new.hex()
    assert original['actual_delta_hex']==float(delta).hex() and original['predicted_original_order_float64_residual_bits']==bits(native)
    assert original['predicted_row_ratio']==ratio and original['exact_row_after']==qpack(after) and original['exact_row_before']==qpack(before)
    assert original['exact_row_absolute_nonincrease']==nonincrease and original['eligible_for_full_candidate']==eligible
    assert original['row_only_gate_predicted']==(ratio<=1e-7) and original['native_full_gate_evaluated_by_this_screen'] is False
    controls.append({'N8_screen_index':original['screen_index'],'support_index':at,'direction':direction,'new_hex':new.hex(),'delta_hex':float(delta).hex(),'residual_bits':bits(native),'ratio':ratio,'exact_after':qpack(after),'N8_exact_nonincrease':nonincrease,'N8_eligible':eligible,'N9_predicted_pass_eligibility':ratio<=1e-7})
identities={'N8_report_sha256':sha(rp.read_bytes()),'N8_scalar_chain_sha256':sha(sp.read_bytes()),'N8_independent_reader_sha256':sha(rdp.read_bytes())}
control={'schema':'razr-N9-N8-retained-last-stage-control-v1',**identities,'base_field_sha256':BASE,'target_original_DOF':160238,'coefficients_hex':[x['coefficient_hex'] for x in support],'original_column_DOFs':[x['original_column_DOF'] for x in support],'values_hex':[v.hex() for v in values],'RHS_hex':b.hex(),'denominator':denominator,'native_row_residual_bits':bits(native_before),'exact_row_before':qpack(before),'trials':controls,'N8_rules_or_rejections_rewritten':False,'new_native_execution':False}
jwrite('N9_N8_LAST_STAGE_CONTROL.json',control,True)
unique=next(x for x in controls if x['N9_predicted_pass_eligibility']); assert unique['N8_screen_index']==142
anchor=Fraction(-115287269818758193826613,316912650057057350374175801344)
lastproof=r['trials'][-1]['exact_affected_proof']
counts={'total':len(controls),'predicted_row_pass':sum(x['N9_predicted_pass_eligibility'] for x in controls),'exact_target_abs_nonincrease':sum(x['N8_exact_nonincrease'] for x in controls),'old_intersection_eligible':sum(x['N8_eligible'] for x in controls),'predicted_pass_and_exact_increase':sum(x['N9_predicted_pass_eligibility'] and not x['N8_exact_nonincrease'] for x in controls),'exact_nonincrease_but_predicted_fail':sum(x['N8_exact_nonincrease'] and not x['N9_predicted_pass_eligibility'] for x in controls),'both_failed':sum(not x['N8_exact_nonincrease'] and not x['N9_predicted_pass_eligibility'] for x in controls)}
basis={'schema':'razr-N9-N8-last-stage-independent-scalar-replay-v1',**identities,'completed':True,'source_run_id':40288924586,'source_head_sha':HEAD,'base_field_sha256':BASE,'N8_original_rejection_preserved':True,'N8_original_five_passed':False,'all_203_original_screens_retained_separately':True,'last_stage_counts':counts,'native_before_bits':bits(native_before),'exact_before':qpack(before),'all_108_original_predictions_and_old_eligibility_replayed_exactly':True,'direct_exact_product_terms':5886,'original_order_float64_product_add_pairs':5886,'unique_predicted_pass':{**unique,'original_column_DOF':160238,'coefficient_hex':support[23]['coefficient_hex'],'old_value_hex':values[23].hex(),'native_full_candidate_executed':False},'current_anchor_trace':{'original_DOF':59009,'absolute_exact_residual':qpack(abs(anchor)),'current_field_sha256':BASE,'trace':'N8 last accepted trial4 directly verified this anchor before/after outside changed column19259; final field bytes equal trial4.','target_after_absolute_residual':qpack(abs(qunpack(unique['exact_after']))),'target_only_margin_below_anchor':qpack(abs(anchor)-abs(qunpack(unique['exact_after']))),'prospective_column160238_support_and_other_affected_equations_evaluated':False,'new_global_nonincrease_certificate_claimed':False},'conclusion':'A single adjacent ULP does predict a passing target row. N8 did not evaluate it as a full candidate because exact target-row absolute residual increased. N9 may evaluate it under the unchanged full global exact-nonincreasing proof and original five native gates; no success is inferred from this row-only replay.','native_full_field_gate_executions':0,'original_K_loaded':False,'new_full_field_arrays_created':False,'elapsed_seconds':0.031196242009173147}
jwrite('N9_N8_LAST_STAGE_REPLAY.json',basis)

previous=json.loads(old('N8_FROZEN_INPUTS.json')); manifest=json.loads((SCI/'EXPORT_MANIFEST.json').read_text())
members={}
for name,prior in previous['members'].items():
    newname='frozen/'+name if name.startswith('frozen/') else name.replace('probe-N7/final/','probe-N8/final/')
    item=manifest['exported_files'][newname]
    members[newname]={key:item[key] for key in ('bytes','sha256')}
    if not name.startswith('probe-N7/final/probe-0-'):assert members[newname]==prior
assert len(members)==22 and sum(x['bytes'] for x in members.values())==382222748
frozen={'schema':'razr-N9-frozen-original-inputs-v1','functional_source_commit':previous['functional_source_commit'],'functional_source_tree':previous['functional_source_tree'],'source_run_id':40288924586,'source_head_sha':HEAD,'source_artifact_id':12634369890,'source_durable_draft_asset_id':None,'source_durable_archive_pending_at_registration':True,'source_ZIP_bytes':238609175,'source_ZIP_sha256':ZIP_SHA,'source_manifest_bytes':166609,'source_manifest_sha256':MAN_SHA,'members':members,'all_selected_original_input_bytes':382222748,'source_all_87_members_and_whole_ZIP_actual_SHA_CRC_verified':True,'source_independent_byte_readback_sha256':OLD_BYTE_RECEIPT,'starting_state_is_N8_last_sequential_accepted_state':True,'starting_probe0_field_sha256':BASE,'N8_rejected_screen142_is_strategy_basis_not_a_full_candidate_or_accepted_state':True,'prior_failure_records_retained_separately':True,'original_runtime_collection_included':False}
jwrite('N9_FROZEN_INPUTS.json',frozen)

s=json.loads(old('N8_STRATEGY.json')); s['schema']='razr-N9-global-proof-coordinate-preregistration-v1';s['status']='registered_before_any_N9_original_full_candidate_execution'
s['actual_basis']={'N8_run_id':40288924586,'N8_head_sha':frozen['source_head_sha'],'N8_worker_seconds':r['elapsed_seconds'],'N8_worker_peak_rss_KiB':r['peak_rss_KiB'],'N8_full_candidates':r['full_candidates_completed'],'N8_scalar_screens':r['scalar_screen_count'],'N8_reader_seconds':rd['elapsed_seconds'],'N8_reader_direct_exact_product_terms':rd['direct_exact_product_terms'],'N8_final_original_ratios':[p['free_dof_residual_infinity_ratio'] for p in r['final']],'N8_current_violating_rows':r['final'][0]['over_gate_row_count'],'N8_current_probe0_field_sha256':r['final_sequential_base_field_sha256'],'N8_termination':r['termination'],'N8_final_stage_independent_replay':{'bytes':3356,'sha256':EXPECTED['N9_N8_LAST_STAGE_REPLAY.json'][1]},'N8_last_stage_counts':basis['last_stage_counts'],'N8_unique_row_predicted_pass':basis['unique_predicted_pass'],'N8_current_anchor_trace':basis['current_anchor_trace'],'N8_all_203_screens_preserved':True,'N8_rules_or_rejections_rewritten':False,'concrete_difference':'N8 required predicted target-row pass AND exact target-row absolute nonincrease to construct a full candidate. The actual final-stage screen142 passes the original row gate but fails the latter local condition. N9 constructs the full candidate on predicted row pass alone, then still requires the complete unchanged global exact-nonincreasing proof and all original full-field conditions.','first_new_full_candidate_must_be_executed':True,'new_N9_original_full_candidate_execution_before_registration':False}
d=s['deterministic_policy'];d['initial_state']='exact last accepted chronological N8 five fields, frozen file bytes from N8 final; no rejected full trial or virtual screen is imported as an accepted state';d['virtual_eligibility']='predicted target row passes the original float64 gate; exact target-row before/after and nonincrease are recorded but are not an extra eligibility condition'
d.update(local_exact_increase_cannot_be_accepted_without_global_proof=True,N8_scalar_prediction_operations_unchanged=True,N8_full_candidate_acceptance_conditions_unchanged=True,single_adjacent_ULP_only_no_multistep_or_two_coordinate_search=True)
c=s['capacity'];c['input_files_and_original_manifest_bytes']=382222748+166609;c['remaining_after_all_these_original_arrays_bytes']=c['original_case_payload_limit_bytes']-c['input_files_and_original_manifest_bytes']-c['maximum_96_trial_new_arrays_bytes']-c['final_all5_field_and_residual_array_bytes'];c['staged_transfer_case_export_required_free_bytes']=238609175+2*1610612736+524288000+64*1024**2
del c['N7_history_retained_complete_verified_scientific_artifact'];c['N8_history_retained_complete_verified_scientific_artifact']=True
t=s['time_basis'];measured=[sum(p['native_gate_diagnostic_and_persistence_seconds'] for p in trial['probes']) for trial in r['trials']];oldmax=t['N7_max_measured_full_candidate_seconds'];oldread=8.93004459399998/35;n8bf=sum(p['native_gate_diagnostic_and_persistence_seconds'] for p in r['baseline']+r['final']);n8setup=r['input_and_matrix_setup_seconds'];n8max=max(measured)
t.update(N8_measured_full_candidate_all5_native_diagnostics_and_persistence_seconds=measured,N8_max_measured_full_candidate_seconds=n8max,N8_baseline_plus_final_seconds=n8bf,N8_input_and_matrices_seconds=n8setup,N8_measured_whole_worker_seconds=r['elapsed_seconds'],N8_measured_whole_reader_seconds=rd['elapsed_seconds'],N8_reader_native_gate_evaluations=rd['native_float64_gate_evaluations'],N8_last108_stdlib_scalar_replay_seconds=0.031196242009173147,N8_last108_replay_exact_product_terms=5886,N8_local_scalar_replay_is_not_native_full_candidate_timing=True,full_candidate_planning_seconds_per_trial=max(oldmax,n8max),reader_planning_seconds_per_native_evaluation=max(oldread,rd['elapsed_seconds']/30),worker_planning_formula='96 * max(N7,N8 measured 5-gate full-candidate diagnostic/write time) + max(N7,N8 baseline/final time) + max(N7,N8 input/matrix setup) + sample one-million exact-term cost + 20 s bookkeeping/reference margin',reader_planning_formula='490 * max(N7 whole-reader seconds/35 gates, N8 whole-reader seconds/30 gates) + sample full 2M exact-term cost + 20 s margin; includes setup and some exact work again and remains an estimate, not a guarantee')
t['worker_planning_seconds']=96*max(oldmax,n8max)+max(t['N7_baseline_plus_final_seconds'],n8bf)+max(t['N7_input_and_matrices_seconds'],n8setup)+t['producer_registered_one_million_exact_terms_sample_projection_seconds']+20
t['reader_planning_seconds']=490*max(oldread,rd['elapsed_seconds']/30)+t['reader_registered_two_million_exact_terms_sample_projection_seconds']+20
s['small_controls']={'old_162_scalar_control':'All original numerical predictions, rational before/after values, and original historical eligibility are checked against the retained fixture; N9 eligibility is separately checked as row-only original float64 predicted pass. Old eligibility is not relabeled.','new_108_scalar_control':'All actual N8 last-stage numerical predictions are checked byte-for-byte, original old eligibility remains zero, and exactly the previously rejected screen142 becomes eligible for a NEW complete evaluation. No new native candidate pass is inferred.','all_original_N8_global_proof_and_partial_export_controls_retained':True,'historical_S4_test_count_modified':False}
jwrite('N9_STRATEGY.json',s)

s=relabel(old('test_n8_contract.py')).replace('N9_ANCHOR_CONTROL.json','N8_ANCHOR_CONTROL.json').replace('probe-N7/final','probe-N8/final')
s=replace(s,'Eight bounded stdlib controls','Nine bounded stdlib controls')
s=replace(s,'ANCHOR_CONTROL=json.loads((HERE/"N8_ANCHOR_CONTROL.json").read_text())','ANCHOR_CONTROL=json.loads((HERE/"N8_ANCHOR_CONTROL.json").read_text())\nN8_CONTROL=json.loads((HERE/"N9_N8_LAST_STAGE_CONTROL.json").read_text())')
s=replace(s,'test_all_162_original_row_screens_and_native_baseline_replay','test_all_162_original_numeric_predictions_and_historical_eligibility')
s=replace(s,'            self.assertEqual(r["eligible_for_full_candidate"],t["eligible"])','            self.assertEqual(t["eligible"],r["row_only_gate_predicted"] and r["exact_row_absolute_nonincrease"])\n            self.assertEqual(r["eligible_for_full_candidate"],r["row_only_gate_predicted"])')
newtest='''    def test_actual_N8_last108_predictions_preserved_only_new_eligibility_differs(self):
        co=[float.fromhex(x) for x in N8_CONTROL["coefficients_hex"]]
        u=[float.fromhex(x) for x in N8_CONTROL["values_hex"]]
        exact=Fraction(int(N8_CONTROL["exact_row_before"]["numerator"]),int(N8_CONTROL["exact_row_before"]["denominator"]))
        b=float.fromhex(N8_CONTROL["RHS_hex"])
        self.assertEqual(contract.BASE_FIELD_SHA,N8_CONTROL["base_field_sha256"])
        self.assertEqual(contract.bits(G["ordered_row_dot"](co,u)-b),N8_CONTROL["native_row_residual_bits"])
        self.assertEqual(sum((Fraction.from_float(a)*Fraction.from_float(v) for a,v in zip(co,u)),Fraction())-Fraction.from_float(b),exact)
        old_eligible=[];new_eligible=[];exact_nonincrease=[]
        for record in N8_CONTROL["trials"]:
            new,delta,r=G["row_screen"](co,u,record["support_index"],record["direction"],b,exact,N8_CONTROL["denominator"])
            self.assertEqual(new.hex(),record["new_hex"])
            self.assertEqual(float(delta).hex(),record["delta_hex"])
            self.assertEqual(r["predicted_original_order_float64_residual_bits"],record["residual_bits"])
            self.assertEqual(r["predicted_row_ratio"],record["ratio"])
            self.assertEqual(r["exact_row_after"],record["exact_after"])
            self.assertEqual(r["exact_row_absolute_nonincrease"],record["N8_exact_nonincrease"])
            historical=r["row_only_gate_predicted"] and r["exact_row_absolute_nonincrease"]
            self.assertEqual(historical,record["N8_eligible"])
            self.assertEqual(r["eligible_for_full_candidate"],record["N9_predicted_pass_eligibility"])
            self.assertEqual(r["eligible_for_full_candidate"],r["row_only_gate_predicted"])
            self.assertFalse(r["native_full_gate_evaluated_by_this_screen"])
            if historical:old_eligible.append(record["N8_screen_index"])
            if r["eligible_for_full_candidate"]:new_eligible.append(record["N8_screen_index"])
            if r["exact_row_absolute_nonincrease"]:exact_nonincrease.append(record["N8_screen_index"])
        self.assertEqual(len(N8_CONTROL["trials"]),108)
        self.assertEqual(old_eligible,[]);self.assertEqual(new_eligible,[142])
        self.assertEqual(len(exact_nonincrease),52)
        self.assertFalse(N8_CONTROL["N8_rules_or_rejections_rewritten"])
        self.assertFalse(N8_CONTROL["new_native_execution"])

'''
s=replace(s,'    def test_all_affected_norm_rejects_target_only_improvement(self):',newtest+'    def test_all_affected_norm_rejects_target_only_improvement(self):')
s=replace(s,'"original_N6b_162_row_screens_replayed":result.wasSuccessful(),','"original_N6b_162_numeric_predictions_and_historical_eligibility_checked":result.wasSuccessful(),\n        "original_N8_108_numeric_predictions_and_historical_eligibility_checked":result.wasSuccessful(),\n        "new_N9_eligibility_checked_separately":result.wasSuccessful(),')
write('test_n9_contract.py',s)

names=['n9_contract.py','fetch_n9_inputs.py','probe_n9_coordinates.py','readback_n9_coordinates.py','export_n9_engineering.py','N9_STRATEGY.json','N9_FROZEN_INPUTS.json','N7_ROW_SCREEN_CONTROL.json','N7_SCALAR_CAPACITY_SAMPLE.json','N8_ANCHOR_CONTROL.json','N9_N8_LAST_STAGE_CONTROL.json','test_n9_contract.py']
w=old('s4-panel-n8-hosted-summary-scope.yml');a=w.index('        cat > "$HOST_ROOT/n8_contract.py" <<\'N8_SOURCE_0\'\n');b=w.index('        python3 -B - <<\'N8_ORIGINAL_SOURCE_COPY\'\n')
first=relabel(w[:a]);last=relabel(w[b:]).replace('Run eight bounded contracts including original row and unaffected-anchor counterexamples','Run nine bounded contracts including original N8 screening and unaffected-anchor counterexamples').replace('Read exact N7 last sequential state','Read exact N8 last sequential state')
blocks=[]
for i,name in enumerate(names):
    raw=(OUT/name).read_bytes();content=raw.decode();assert content.endswith('\n')
    body='\n'.join('        '+line for line in content[:-1].split('\n'))+'\n'
    blocks.append(f'        cat > "$HOST_ROOT/{name}" <<\'N9_SOURCE_{i}\'\n'+body+f'        N9_SOURCE_{i}\n        cp "$HOST_ROOT/{name}" "$CASE_DIR/source/{name}"\n        printf \'{sha(raw)}  %s\\n\' "$HOST_ROOT/{name}" | sha256sum --check --strict\n')
write('s4-panel-n9-hosted.yml',first+''.join(blocks)+last)
elements=[{'path':'engineering/engineering-integration-20261026/numerics/n9/'+name,'mode':'100644','type':'blob','content':(OUT/name).read_text()} for name in names]
elements.append({'path':'.github/workflows/s4-panel-n9-hosted.yml','mode':'100644','type':'blob','content':(OUT/'s4-panel-n9-hosted.yml').read_text()})
request={'repository_full_name':'TrillionniumFoundation/RAZR-SLIDE','base_tree_sha':'cdd9e2c41216201b6cd04dd610d45fde80499045','tree_elements':elements}
raw=(json.dumps(request,ensure_ascii=False,separators=(',',':'))+'\n').encode()
write('N9_TREE_REQUEST.json',raw);write('N9_TREE_REQUEST.json.gz',gzip.compress(raw,compresslevel=9,mtime=0))
receipt={'schema':'razr-N9-frozen-byte-reset-reconstruction-v1','old_temporary_files_recovered':False,'source':'immutable original N8 published bytes and all87 verified original scientific artifact members, with retained pre-reset derivation and expected SHA records','native_execution':False,'full_fields_loaded':False,'all_108_scalar_predictions_directly_recomputed':True,'historical_replay_elapsed_value_is_restored_historical_record_not_current_timing':True,'current_reconstruction_elapsed_seconds':time.perf_counter()-started,'entries':records,'all_retained_pre_reset_identities_match':all(x['matches_retained_pre_reset_identity'] for x in records),'original_S4_five_passed':False,'H_frame_restore_executed':False}
jwrite('N9_RESET_RECONSTRUCTION_RECEIPT.json',receipt)
print(json.dumps({'matches':sum(x['matches_retained_pre_reset_identity'] is True for x in records),'mismatches':[x for x in records if x['matches_retained_pre_reset_identity'] is False],'current_reconstruction_elapsed_seconds':receipt['current_reconstruction_elapsed_seconds'],'native_execution':False}))
