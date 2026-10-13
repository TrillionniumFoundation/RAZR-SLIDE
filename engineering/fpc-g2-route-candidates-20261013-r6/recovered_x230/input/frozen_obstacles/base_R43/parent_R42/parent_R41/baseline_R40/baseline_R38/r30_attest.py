"""Independent R30 evidence gate. Rejects stale/missing geometry/test results.
PASS means only reproducible defined CAD experiments, NOT manufacturing approval.
"""
from __future__ import annotations
import json,hashlib,re,platform,importlib.metadata
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT

V=ROOT/'verification'
LABELS={'R21':28,'R22':37,'R22_adversarial':11,'R23':22,'R24':25,
        'R25':30,'R26':38,'R27':35,'R28':42,'R29':40,'R30':40}

def run(write=True):
 frozen=json.loads((ROOT/'audit'/'R30_R29_ORIGINAL_ZIP_MEMBERS.json').read_text())
 assert frozen['R29_zip_member_count_verified']==441
 for f in frozen['entries']:
    p=ROOT/f['path']
    assert p.is_file() and len(p.read_bytes())==f['size_bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],f['path']
 reports={k:json.loads((V/f'R30_{k}.json').read_text()) for k in
          ('integration','dynamic','tolerance','retention','faults','section','STEP_manifest')}
 assert all(r.get('manufacturing_go') is False for r in reports.values())
 assert reports['integration']['A_valid_single_body'] and reports['integration']['B_valid_single_body']
 assert len(reports['integration']['subtractions'])==8
 assert reports['integration']['actual_boss_added_over_R27_mm3']>0
 assert reports['dynamic']['pose_count']==10 and reports['dynamic']['unexpected_collision_count']==0
 assert reports['tolerance']['number_configurations']==108 and reports['tolerance']['occ_pair_checks']==324
 assert all(v['configs']==54 and v['jam_configs']==0 for v in reports['tolerance']['summary'])
 assert reports['retention']['xyz_guide_configurations']==324 and reports['retention']['guide_jam_configs']==0
 assert reports['retention']['hard_axis_probes']==24 and reports['retention']['hard_axis_fail_to_intercept']==0
 assert reports['faults']['normal_nominal_positions']==38 and reports['faults']['normal_poses_all_collision_free']
 assert reports['faults']['inherited_original_fault_escape_counterexamples']==36
 assert reports['faults']['no_A_key_false_capture_still_possible']
 assert reports['STEP_manifest']['scene_count']==6
 for r in reports['STEP_manifest']['scenes']:
    p=ROOT/'cad'/r['filename'];assert p.exists() and p.stat().st_size==r['file_size']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    assert r['valid_imported_solids']==r['exported_parts']
 for n in ('R30_A_R29_KEYS_FROZEN.brep','R30_B_LONGITUDINAL_REBASE.brep'):
    s=cq.importers.importBrep(str(ROOT/'cad'/n)).val()
    assert s.isValid() and len(s.Solids())==1
 assert (V/'R30_geometry_exit.code').read_text().strip()=='0'
 assert (V/'R30_inherited_exit.code').read_text().strip()=='0'
 tests={}
 for label,n in LABELS.items():
    logfile=f'R30_new_40.log' if label=='R30' else f'R30_inherited_{label}.log'
    p=V/logfile;content=p.read_text(errors='replace')
    m=re.search(r'Ran\s+(\d+)\s+tests?',content)
    assert m and int(m.group(1))==n and content.rstrip().endswith('OK'),f'incomplete {label}'
    tests[label]={'tests':n,'path':str(p.relative_to(ROOT)),
                  'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 out={'revision':'R30 hardgate executed source tests and complete real CAD rebuild',
   'platform':{'python':platform.python_version(),'cadquery':importlib.metadata.version('cadquery')},
   'R29_original_frozen_files':len(frozen['entries']),
   'R29_original_archive_sha256':frozen['R29_zip_sha256'],
   'test_receipts':tests,'total_tests':sum(LABELS.values()),'all_tests_passed':True,
   'B_represents_rebuilt_R27_B_plus_guided_tail_and_real_boss':True,
   'R30_B_rebased_volume_mm3':reports['integration']['B_R30_volume_mm3'],
   'B_guide_boss_added_material_vs_R27_mm3':reports['integration']['actual_boss_added_over_R27_mm3'],
   'B_guide_pocket_removed_mm3':reports['integration']['pocket_removed_from_reinforced_mm3'],
   'ten_pose_unexpected_collisions':reports['dynamic']['unexpected_collision_count'],
   'kinematic_cam_relative_offset_cases':reports['tolerance']['number_configurations'],
   'cam_occ_checks':reports['tolerance']['occ_pair_checks'],
   'cam_jam_0p02':reports['tolerance']['summary'][0]['jam_configs'],
   'cam_jam_0p05':reports['tolerance']['summary'][1]['jam_configs'],
   'fixed_sleeve_relative_offset_cases':reports['retention']['xyz_guide_configurations'],
   'sleeve_jam_count':reports['retention']['guide_jam_configs'],
   'directional_0p10_hard_stop_witnesses':reports['retention']['hard_axis_probes'],
   'hard_stop_witness_failures':reports['retention']['hard_axis_fail_to_intercept'],
   'STEP_scenes':reports['STEP_manifest']['scene_count'],
   'OLD_R29_0p03mm_front_lip_unfixed':True,
   'OLD_R24_0p22mm_rail_fatigue_unqualified':True,
   'R29_original_joint_fault_escape_unfixed':reports['faults']['inherited_original_fault_escape_counterexamples'],
   'no_A_false_capture_still_possible':True,
   'contact_e0p07_mm_electrical_engagement_unknown':True,
   'physical_force_limited_retraction_unverified':True,
   'TE_signal_contact_not_main_battery_power_qualified':True,
   'USB_high_speed_real_SI_tests_missing':True,
   'OEM_7in_OLED_dynamic_radius_full_pkg_width_lifetime_missing':True,
   'manufacturing_go':False,
   'report_sha256':{k:hashlib.sha256((V/f'R30_{k}.json').read_bytes()).hexdigest() for k in reports}}
 if write:(V/'R30_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 print('R30 ATTEST',out['total_tests'],'tests, frozen R29',len(frozen['entries']),'files. MANUFACTURING NO-GO',flush=True)
 return out
if __name__=='__main__':run()
