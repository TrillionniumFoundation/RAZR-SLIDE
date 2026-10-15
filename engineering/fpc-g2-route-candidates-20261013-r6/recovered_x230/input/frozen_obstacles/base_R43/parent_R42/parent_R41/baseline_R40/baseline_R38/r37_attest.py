"""Strict R37 safety-negative research attestation. No manufacturing approval."""
import json,hashlib,re,platform,importlib.metadata
from r25_capture import ROOT
from r37_freeze import EXPECTED_SHA,SOURCE,hash_file

DOCS=['integration','catalogue','dynamic','tolerance','faults','STEP_manifest']

def run(write=True):
    immutable=json.loads((ROOT/'audit/R37_R36_immutable.json').read_text())
    assert immutable['immutable_original_files']==977 and immutable['all_bytes_identical']
    assert hash_file(SOURCE)==EXPECTED_SHA
    for member in immutable['entries']:
        p=ROOT/member['path']
        assert p.is_file() and p.stat().st_size==member['size']
        assert hash_file(p)==member['sha256'],member['path']
    docs={n:json.loads((ROOT/f'verification/R37_{n}.json').read_text()) for n in DOCS}
    i,c,d,t,f,step=[docs[n] for n in DOCS]
    assert i['B_valid'] and i['B_solids']==1 and .06<i['added_B_volume_mm3']<.08
    assert all(p['root_shell_overlap_mm3']>.01 and p['cap_installed_overlap_mm3']<1e-8 and
      p['cap_forced_pull_0p05_overlap_mm3']>.004 for p in i['lips'])
    assert i['reference_pose_count']==10 and all(not p['unexpected_occupied_intersections_mm3'] for p in i['reference_poses'])
    assert d['original_front_assembly_interfering_positions']>20
    assert t['configuration_count']==162 and t['OCC_intersections']==324
    assert t['aggregation']['0.05']['installed_clash']>0 and t['aggregation']['0.05']['no_catch_by_0p05']>0
    assert all(x['top_sheet_does_not_fit_existing_keeper'] and x['bigger_top_sheet_drill_makes_disconnected_solids']==2
      for x in c['rows'])
    assert f['single_integral_lip_fracture_exposes_that_side']
    assert f['previous_legacy_unsafe_mechanical_modes']==36 and f['previous_single_point_electric_bypasses']==3
    assert step['count']==7 and step['ghost_count']==4
    assert all(p['parts']==p['reimported_valid_solids'] for p in step['scenes'])
    for p in step['scenes']:
        file=ROOT/'cad'/p['file'];assert file.is_file() and hash_file(file)==p['sha256']
    assert all(x['manufacturing_go'] is False for x in docs.values())
    testlog=(ROOT/'verification/R37_new_48.log').read_text()
    assert re.search(r'Ran 48 tests?',testlog) and testlog.rstrip().endswith('OK')
    assert (ROOT/'verification/R37_new_exit.code').read_text().strip()=='0'
    inherited=json.loads((ROOT/'verification/R37_inherited_receipts.json').read_text())
    assert inherited['success'] and inherited['R36_fresh_inherited_count']==613
    assert len(inherited['cases'])==17
    for case in inherited['cases']:
        log=(ROOT/case['log']).read_text()
        assert case['success'] and case['returncode']==0
        assert re.search(r'Ran\s+(\d+)\s+tests?',log) and log.rstrip().endswith('OK')
        assert hash_file(ROOT/case['log'])==case['sha256']
    assert (ROOT/'verification/R37_inherited_exit.code').read_text().strip()=='0'
    out=dict(revision='R37 integral B-shell lips; research-level NO-GO',
       source_R36_zip_sha256=EXPECTED_SHA,source_frozen_member_count=977,
       source_bytes_all_unchanged=True,source_zip_crc_verified=True,
       python_version=platform.python_version(),cadquery_version=importlib.metadata.version('cadquery'),
       inherited_fresh_test_count=613,new_test_count=48,total_fresh_test_count=661,
       inherited_receipts=inherited['cases'],
       new_test_receipt={'count':48,'log':'verification/R37_new_48.log',
           'sha256':hash_file(ROOT/'verification/R37_new_48.log')},
       B_shell_valid_single_body=True,B_added_mm3=i['added_B_volume_mm3'],
       nominal_integral_lip_stop_both_sides=True,
       old_front_insertion_collisions=d['original_front_assembly_interfering_positions'],
       hypothetical_tol_configurations=t['configuration_count'],
       hypothetical_tolerance_only=True,
       worst_0p05_installed_jams=t['aggregation']['0.05']['installed_clash'],
       worst_0p05_missing_stop=t['aggregation']['0.05']['no_catch_by_0p05'],
       PEM_off_the_shelf_direct_replacement_rejected=True,
       nominal_boltless_lip_not_elastically_assembled=True,
       no_vendor_native_TE_or_PEM_3D=True,
       original_joint_fault_36_of_64_still_unsafe=True,
       single_integral_hook_failure_unsafe=True,
       electrical_PCB_bypass_3_single_faults_still_unsafe=True,
       no_real_power_USB_OLED_qualification=True,
       nominal_A_B_finished_equal_external_shape_not_proven=True,
       battery_4700mAh_target_only=True,
       R37_STEP_count=7,R37_GHOST_count=4,manufacturing_go=False)
    # JSON keys are ASCII; no executable consequence for any key naming
    if write:(ROOT/'verification/R37_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R37 research attested',out['total_fresh_test_count'],'steps',out['R37_STEP_count'],'NO-GO',flush=True)
    return out
if __name__=='__main__':run()
