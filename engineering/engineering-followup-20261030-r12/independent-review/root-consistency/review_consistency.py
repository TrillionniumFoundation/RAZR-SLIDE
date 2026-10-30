"""Read-only closeout consistency checks; no CAD rerun or physical inference."""
from fractions import Fraction as Q
import hashlib,json,pathlib,re

BASE=pathlib.Path('/workspace/scratch/1b842ca762be')
ROOT=BASE/'RAZR-SLIDE'
R12=ROOT/'engineering/engineering-followup-20261030-r12'
GEO=BASE/'geometry_work'
OUT=pathlib.Path(__file__).resolve().parent


def ident(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())


def read(p):return json.loads(p.read_text())


def main():
    audit=read(R12/'real-inputs/CURRENT_INPUT_READBACK.json')
    checked=[]
    for rec in [audit['source']]+audit['input_identities']:
        p=pathlib.Path(rec['path']);p=p if p.is_absolute() else ROOT/p
        actual=ident(p);assert actual['sha256']==rec['sha256'] and actual['bytes']==rec['bytes'];checked.append(actual)
    structural=read(R12/'real-inputs/source/CURRENT_K3_STRUCTURAL_INPUT_CONTRACT.json')
    physical=read(R12/'real-inputs/source/CURRENT_K3_PHYSICAL_AND_GATE_INPUT_CONTRACT.json')
    assert structural['current_K3_binding']==physical['current_K3_binding']
    mats=structural['all_current_roles_material_inputs'];matvalues=[v for item in mats.values() for v in item['physical_material_inputs'].values()]
    loads=structural['original_13_loadcases_retained'];loadvalues=[v for item in loads.values() for v in item.values()]
    stops=structural['K3_additional_stop_load_and_tolerance_cases'];stopvalues=[v for item in stops.values() for v in item.values()]
    counts=dict(material_roles=len(mats),material_slots=len(matvalues),unassigned_material_slots=matvalues.count(None),original_loadcases=len(loads),load_slots=len(loadvalues),unassigned_load_slots=loadvalues.count(None),additional_stop_loadcases=len(stops),additional_stop_load_slots=len(stopvalues),unassigned_stop_load_slots=stopvalues.count(None),same_specimen_identity_fields=len(physical['ten_identity_fields']),part_roles=len(physical['seven_part_originals']),interfaces=len(physical['twelve_interfaces']))
    assert all(audit[k]==v for k,v in counts.items())
    gate_counts={}
    for name,gate in physical['physical_gate_contracts'].items():
        slot_values=[]
        for collection in ('requirements','criteria','exposure'):
            for item in gate.get(collection,{}).values():
                slot_values.extend(v for k,v in item.items() if k in ('value','minimum','maximum'))
        count=dict(records=sum(len(gate.get(x,{})) for x in ('requirements','criteria','exposure')),numeric_limit_slots=len(slot_values),unassigned_numeric_limits=slot_values.count(None))
        assert all(audit['physical_gates'][name][k]==v for k,v in count.items())
        assert gate['actual_execution'] is False and audit['physical_gates'][name]['real_pass_obtained'] is False
        gate_counts[name]=count
    assert sum(x['records'] for x in gate_counts.values())==audit['gate_records']==54
    assert sum(x['unassigned_numeric_limits'] for x in gate_counts.values())==audit['unassigned_gate_limit_slots']==67
    for key in ('current_absolute_FE_qualified','OEM_electrical_qualified','complete_current_physical_contract_frozen','G3_pass','G4_pass','G5_pass','candidate_go','fixture_fabrication_go','manufacturing_go'):
        assert audit[key] is False
    for filename in ('key_forward_loop_v1.py','panel_key_travel_stops_v1.py'):
        expected=structural['current_K3_binding']['candidate_source_and_contract_bytes'][filename]
        actual=ident(GEO/'inputs'/filename);assert actual['sha256']==expected['sha256'] and actual['bytes']==expected['bytes'];checked.append(actual)
    search=read(R12/'real-inputs/R12_SAME_SPECIMEN_SEARCH.json');assert search['global_absence_proved'] is False and search['new_same_specimen_originals_acquired']==0
    endpoint=read(R12/'real-inputs/KNOWN_DEVICE_ENDPOINT_CHECK.json');assert endpoint['device_commands_sent']==endpoint['physical_measurements']==0 and endpoint['tcp_connection']=='not_established_in_this_executor'
    oem=read(R12/'real-inputs/OEM_DOWNLOAD_ATTEMPTS.json');assert len(oem)==3 and all(x['pdf_header'] is False and x['specimen_binding_established'] is False for x in oem)
    source_tests=read(R12/'qualification/SOURCE_AND_TEST_READBACK.json')
    for x in source_tests['source_identities']:
        actual=ident(ROOT/x['path']);assert actual['sha256']==x['sha256'] and actual['bytes']==x['bytes'];checked.append(actual)
    logs=[]
    for rec in source_tests['final_disjoint_test_executions']:
        p=R12/'qualification'/rec['log'];actual=ident(p);text=p.read_text();assert actual['sha256']==rec['log_sha256']
        assert re.search(r'Ran '+str(rec['tests'])+r' tests\b',text) and text.rstrip().endswith('OK')
        logs.append(dict(tests=rec['tests'],file=actual))
    assert sum(x['tests'] for x in logs)==127==source_tests['tests_total']
    assert source_tests['physical_executions']==0 and source_tests['physical_G3_G4_G5_pass'] is False
    failure=read(GEO/'REAL_FAILURE_NATIVE_READBACK.json');actual=ident(GEO/'read_actual_failed_shapes.py');assert actual['sha256']==failure['source_sha256'];checked.append(actual)
    rows=failure['shapes']
    for row in rows:
        actual=ident(GEO/row['file']);assert actual['sha256']==row['sha256'] and actual['bytes']==row['bytes'];checked.append(actual)
        assert row['positive_solid_gate_passes']==all(v>0 for v in row['all_solid_signed_volumes_mm3'])
        assert len(row['all_solid_signed_volumes_mm3'])==1
    assert rows[0]['signed_volume_mm3']<0 and rows[0]['positive_solid_gate_passes'] is False
    assert rows[1]['signed_volume_mm3']>0 and rows[1]['positive_solid_gate_passes'] is True
    assert rows[3]['signed_volume_mm3']==rows[4]['signed_volume_mm3']==0 and not rows[3]['positive_solid_gate_passes'] and not rows[4]['positive_solid_gate_passes']
    report3=read(GEO/'producer-v3/report.json');panel=report3['panel']['signature']['signed_volume_mm3'];tiny=rows[1]['signed_volume_mm3'];common=rows[2]['signed_volume_mm3'];tolerance=1e-7
    native_bound=min(panel,tiny)+tolerance
    rational_bound=min(Q(panel),Q(tiny))+Q(tolerance)
    assert native_bound==failure['impossible_Common_original_operand_bound_mm3']
    assert Q(common)>rational_bound and common==failure['observed_impossible_Common_mm3'] and failure['impossible_Common_violation_preserved'] is True
    assert not failure['original_reports_rewritten'] and not failure['failures_reclassified_as_pass']
    original_failed=[]
    for v in (1,2,3,4):
        p=GEO/f'producer-v{v}/report.json';j=read(p);assert j['completed'] is False and j['failures']
        original_failed.append(ident(p))
    result=dict(schema='r12.independent_closeout_consistency_review.v1',completed=True,source=ident(pathlib.Path(__file__)),
        checked_byte_identities=checked,real_input_counts=counts,gate_counts=gate_counts,declared_gate_records=54,declared_missing_gate_limit_slots=67,
        K3_source_names_match_current_geometry_inputs=True,counts_scope='Slots actually declared in the frozen K3 input contracts, not proof of a complete physical input universe.',
        qualification_readme_test_claim_verified=dict(disjoint_executions=logs,total=127,physical_executions=0,seven_extra_synthetic_admission_controls_separate=True),
        native_failure_review=dict(cad_kernel_rerun=False,all_five_shape_files_SHA_verified=True,original_failed_reports=original_failed,
            negative_signed_volume_preserved=rows[0]['signed_volume_mm3'],tiny_positive_operand_preserved=tiny,zero_signed_volume_shapes=2,
            panel_operand_mm3=panel,reported_Common_mm3=common,original_min_operand_plus_tol_native_bound_mm3=native_bound,
            exact_rational_comparison_confirms_violation=True,no_absolute_volume_reclassification=True,
            topology_valid_or_positive_volume_does_not_imply_Common_operand_bound_pass=True),
        remaining_concrete_contradictions=[],limitations=[
            'OEM receipts record HTML/non-PDF/no specimen binding. The three actual response bodies are not present in the current artifacts; their body SHA values could not be independently re-read.',
            'Known device endpoint permission failure is local executor evidence only; it does not prove the user device is offline.',
            'Bounded no-match source searches do not prove global absence.',
            'Shape SHA and recorded-volume arithmetic were checked; this review did not independently rerun CAD kernel measurements.',
            'Source identities match current workspace bytes. Final commit identity must be bound by root closeout before describing them as committed.',
            'No physical G3/G4/G5, current absolute FE or OEM qualification is established by these checks.'])
    (OUT/'INDEPENDENT_CONSISTENCY_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(completed=True,verified_files=len(checked),physical_tests=0,qualification_tests=127,min_operand_bound=native_bound,common=common,remaining_contradictions=[])))


if __name__=='__main__':main()
