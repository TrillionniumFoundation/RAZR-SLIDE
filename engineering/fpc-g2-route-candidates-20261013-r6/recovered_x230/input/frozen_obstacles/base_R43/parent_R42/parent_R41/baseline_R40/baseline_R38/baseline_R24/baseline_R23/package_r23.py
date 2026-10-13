"""Evidence-preserving project packager. Run AFTER all tests and STEP exports."""
from pathlib import Path
import json,hashlib,re,zipfile,shutil,sys,os
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def run():
    v=ROOT/'verification'
    completion=v/'R23_FINAL_FULL_EXIT.txt'
    assert completion.exists() and completion.read_text().strip()=='0', 'full-run exit receipt missing or nonzero'
    expected={'R23_R21_28.log':28,'R23_R22_37.log':37,
              'R23_R22_adversarial_11.log':11,'R23_unittest.log':22}
    for name,n in expected.items():
        s=(v/name).read_text()
        assert f'Ran {n} tests' in s and '\nOK' in s,(name,s[-300:])
    states=json.loads((v/'R23_lock_fault_results.json').read_text())
    integ=json.loads((v/'R23_B_integration.json').read_text())
    elec=json.loads((v/'R23_power_faulttree.json').read_text())
    oled=json.loads((v/'R23_OLED_tolerance_gate.json').read_text())
    exp=json.loads((v/'R23_STEP_manifest.json').read_text())
    for name,data in [('lock',states),('integration',integ),('power',elec),('OLED',oled)]:
        assert data['manufacturing_go'] is False,name
    m=states['independent_fault_enumeration']
    assert m['states']==2048 and m['R22_dangerous_now_blocked_both_new_closed']==56
    assert m['all_R22_open_both_new_open_unseated_escape']==56
    assert integ['B_final_one_solid'] and integ['final_B_valid'] and integ['selected_pose_clash_count']==0
    assert exp['valid_exports']==6 and exp['NO_MANUFACTURING_RELEASE']
    audit=ROOT/'audit'
    origin=OUT/'RAZR_SLIDE_R22_hardgate_review_20261010.zip'
    provenance={'R22_archive_SHA256':sha(origin) if origin.exists() else None,
                'R22_archive_read_only_baseline_copied':origin.exists(),
                'python_executable':sys.executable,
                'R23_safety_release':'MANUFACTURING_NO_GO',
                'R23_existing_R22_56_escapes_blocked_only_when_independent_jaws_closed':56,
                'R23_new_double_jaw_open_same_56_escapes_remain':56,
                'R23_320_old_witness_scan_not_real_captive_key':True,
                'actual_R23_A_capturable_key_cam_assembled':False,
                'real_A_and_B_battery_main_connector':False,
                '7inch_real_module_vendor_data':False,
                'hardware_300k_proof':False,
                'tests_passed':expected}
    (audit/'R23_independent_attestation.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    allfiles=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'
      and p.relative_to(ROOT).as_posix()!='audit/R23_SHA256_MANIFEST.json')
    manifest={'project':'RAZR_SLIDE_R23','status':'MANUFACTURING_NO_GO',
              'items':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in allfiles]}
    (audit/'R23_SHA256_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    finalfiles=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    zipfp=OUT/'RAZR_SLIDE_R23_engineering_package_20261010.zip'
    with zipfile.ZipFile(zipfp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7,allowZip64=True) as zf:
        for p in finalfiles:
            zf.write(p, 'RAZR_SLIDE_R23/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(zipfp) as zf:
        corrupt=zf.testzip();assert corrupt is None,corrupt
        assert len(zf.namelist())==len(finalfiles)
    (OUT/'RAZR_SLIDE_R23_engineering_package_20261010.sha256').write_text(sha(zipfp)+'  '+zipfp.name+'\n')
    shutil.copy2(audit/'R23_硬门槛复核及否决结论.md',OUT/'R23_hardgate_audit_20261010.md')
    shutil.copy2(ROOT/'cad'/'R23_double_guard_cross_section.png',OUT/'R23_lock_section_20261010.png')
    results={'overall':'MANUFACTURING_NO_GO','validation_tests':expected,
             'M_lock':states['independent_fault_enumeration'],
             'M_full_B':{'valid':integ['final_B_valid'],'single_solid':integ['B_final_one_solid'],
                 'cut_mm3':integ['B_pockets_removed_from_R22_mm3'],
                 'net_mm3':integ['B_net_volume_change_from_R22_mm3'],
                 'poses':len(integ['five_pose_checks']),'collision_count':integ['selected_pose_clash_count'],
                 'A_key_mechanism_exists':integ['physically_modelled_A_positive_key_wedge']},
             'E_isolation':{'enumerated_fault_states':elec['modeled_weld_short_bypass_combinations'],
                 'unsafe_fault_states_without_direct_bypass':elec['number_unsafe_cases_excluding_bypass'],
                 'unsafe_single_bypass_possible':bool(elec['unsafe_single_faults'])},
             'D_OLED':{'tolerance_cases':oled['stress_cases'],
                 'passes_on_model_assumptions':oled['stress_cases_nominal_geometric_screen_pass'],
                 'hypothetical_min_cavity_mm':oled['hypothetical_required_cavity_depth_mm'],
                 'supplier_qualified':oled['real_panel_qualified']},
             'STEP_import_valid_files':exp['valid_exports'],
             'archive_sha256':sha(zipfp),'all_material_OEM_hardware_available':False}
    (OUT/'R23_results_20261010.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'zip':str(zipfp),'bytes':zipfp.stat().st_size,'test_logs':expected,
                      'sha256':sha(zipfp),'files':len(finalfiles),'status':results['overall']},indent=2))
if __name__=='__main__':run()
