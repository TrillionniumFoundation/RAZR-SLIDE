"""R32 source/evidence/historical-unit receipts attestation.
PASS = independently reproducible research findings including negative cases.
"""
from __future__ import annotations
import json,hashlib,re,platform,importlib.metadata
import cadquery as cq
from r25_capture import ROOT

LABELS={'R21':28,'R22':37,'R22_adversarial':11,'R23':22,'R24':25,
        'R25':30,'R26':38,'R27':35,'R28':42,'R29':40,'R30':40,'R31':45,'R32':40}
NAMES=('integration','envelope','dynamic','tolerance','faults','vendor_fit','STEP_manifest')

def run(write=True):
    freeze=json.loads((ROOT/'audit'/'R32_R31_FROZEN_SHA256.json').read_text())
    assert freeze['verified_R31_original_files']==564 and freeze['original_unchanged']
    for f in freeze['entries']:
        p=ROOT/f['path'];assert p.stat().st_size==f['size_bytes'],f['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],f['path']
    from r32_freeze import SOURCE
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==freeze['R31_original_SHA256']
    j={n:json.loads((ROOT/'verification'/f'R32_{n}.json').read_text()) for n in NAMES}
    assert all(v['manufacturing_go'] is False for v in j.values())
    assert j['integration']['A_valid_single'] and j['integration']['B_valid_single']
    assert j['integration']['actual_B_frame_added_mm3']>2.7
    assert j['integration']['actual_B_channel_removed_mm3']>.9
    assert j['dynamic']['reference_pose_count']==10
    assert not j['dynamic']['unexpected_reference_collisions']
    assert not j['dynamic']['insertion_clashes']
    assert j['tolerance']['configurations']==162
    assert [x['jam_count'] for x in j['tolerance']['results_by_width']]==[0,0,48]
    assert j['faults']['inherited_mechanical_escape_counterexamples']==36
    assert j['faults']['power_single_fault_dangerous_minimal_cut_count']==3
    assert j['vendor_fit']['axis_aligned_envelope_fit_count']==0
    assert j['envelope']['A_minus_B_extent_xyz_mm']==[0.,-.35,3.4]
    assert j['STEP_manifest']['scene_count']==7
    for st in j['STEP_manifest']['scenes']:
        assert st['imported_valid_solids']==st['parts']
        assert hashlib.sha256((ROOT/'cad'/st['filename']).read_bytes()).hexdigest()==st['sha256']
    for n in ('R32_A_R31_UNMODIFIED.brep','R32_B_REAR_CASSETTE_BAYS.brep'):
        sh=cq.importers.importBrep(str(ROOT/'cad'/n)).val()
        assert sh.isValid() and len(sh.Solids())==1
    assert (ROOT/'verification/R32_geometry_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R32_inherited_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R32_new_40_exit.code').read_text().strip()=='0'
    receipts={}
    for label,n in LABELS.items():
        p=ROOT/'verification'/('R32_new_40.log' if label=='R32' else f'R32_inherited_{label}.log')
        raw=p.read_text(errors='replace')
        match=re.search(r'Ran\s+(\d+)\s+tests?',raw)
        assert match and int(match.group(1))==n and raw.rstrip().endswith('OK'),label
        receipts[label]=dict(tests=n,log=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    outputs=dict(
        revision='R32 research B-shell reinforced rearward cassette openings, negative safety witnesses',
        platform=dict(python=platform.python_version(),cadquery=importlib.metadata.version('cadquery')),
        R31_ancestor_original_ZIP_SHA256=freeze['R31_original_SHA256'],
        R31_ancestor_files_hash_verified=freeze['verified_R31_original_files'],
        inherited_test_count=sum(n for k,n in LABELS.items() if k!='R32'),
        new_R32_test_count=LABELS['R32'],
        total_reexecuted_and_passed=sum(LABELS.values()),
        tests_include_expected_negative_failures=True,
        receipts=receipts,
        R32_actual_B_frame_fused_material_mm3=j['integration']['actual_B_frame_added_mm3'],
        R32_actual_B_channel_removed_material_mm3=j['integration']['actual_B_channel_removed_mm3'],
        completed_reference_postures=j['dynamic']['reference_pose_count'],
        reference_named_interference_count=len(j['dynamic']['unexpected_reference_collisions']),
        rechecked_nominal_insert_samples=len(j['dynamic']['insertion_cases']),
        tolerance_configs=j['tolerance']['configurations'],
        tolerance_failure_count_by_width=j['tolerance']['results_by_width'],
        original_64_fault_cases_escape_count=j['faults']['inherited_mechanical_escape_counterexamples'],
        inherited_live_power_single_fault_minimal_cuts=j['faults']['power_single_fault_dangerous_minimal_cut_count'],
        R32_box_cross_section_NOT_fit_for_TE_catalogue_envelope=j['vendor_fit']['axis_aligned_envelope_fit_count']==0,
        product_equal_outer_ended_body_CAD_unproven=j['envelope']['native_solids_full_bbox_equal'] is False,
        STEP_count=j['STEP_manifest']['scene_count'],
        GHOST_STEP_count=sum(x['ghost_known_unsafe'] for x in j['STEP_manifest']['scenes']),
        source_report_sha256={x:hashlib.sha256((ROOT/'verification'/f'R32_{x}.json').read_bytes()).hexdigest() for x in NAMES},
        power_signals_USB_real_connected=False,
        true_OLED_supplier_material_lifetime_qualified=False,
        mechanical_independent_positive_capture_safe_finite_force_retraction_qualified=False,
        manufacturing_go=False)
    if write:(ROOT/'verification/R32_results.json').write_text(json.dumps(outputs,indent=2,ensure_ascii=False)+'\n')
    print('R32 ATTEST',outputs['total_reexecuted_and_passed'],'tests; ancestors',freeze['verified_R31_original_files'],
          'ZIP',freeze['R31_original_SHA256'],'MANUFACTURING NO-GO',flush=True)
    return outputs
if __name__=='__main__':run()
