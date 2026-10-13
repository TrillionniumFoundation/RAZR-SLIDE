"""Strict R31 source/evidence gate. PASS is a research-reproducibility
attestation ONLY; it expressly rejects manufacturing or electrical release.
"""
from __future__ import annotations
import hashlib,json,platform,re,importlib.metadata
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT

V=ROOT/'verification'
LABELS={'R21':28,'R22':37,'R22_adversarial':11,'R23':22,'R24':25,
        'R25':30,'R26':38,'R27':35,'R28':42,'R29':40,'R30':40,'R31':45}
REPORTS=('integration','dynamic','tolerance','faults','section','STEP_manifest')

def run(write=True):
    freeze=json.loads((ROOT/'audit'/'R31_R30_ORIGINAL_ZIP_MEMBERS.json').read_text())
    assert freeze['verified_count']==504 and len(freeze['entries'])==504
    assert freeze['original_zip_sha256']=='09cbeba46fd486b34cfec0492af780db3c4a728e97fbf6dffa9023f5d9c84985'
    for f in freeze['entries']:
        p=ROOT/f['path'];assert p.is_file() and p.stat().st_size==f['size_bytes'],f['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],f['path']
    d={x:json.loads((V/f'R31_{x}.json').read_text()) for x in REPORTS}
    assert all(x['manufacturing_go'] is False for x in d.values())
    assert d['integration']['A_valid_single'] and d['integration']['B_valid_single']
    assert len(d['integration']['operations'])==6
    assert d['dynamic']['reference_poses']==10 and d['dynamic']['near_seat_cases']==20
    assert d['dynamic']['unexpected_clashes']==0
    assert d['tolerance']['configurations']==108
    assert [x['false_release_before_seat'] for x in d['tolerance']['per_width']]==[0,18]
    assert [x['seat_refuses_to_release'] for x in d['tolerance']['per_width']]==[18,18]
    assert [x['B_cavity_interference_configurations'] for x in d['tolerance']['per_width']]==[0,44]
    assert d['faults']['old_R30_original_36_escapes']==36
    assert d['faults']['new_cross_product_escapes_sum']==36
    assert d['faults']['STOW_endpoint_false_capture_still_unremedied']
    assert d['section']['old_R29_lip_not_replaced_with_qualified_load_path']
    assert d['STEP_manifest']['scene_count']==8
    for x in d['STEP_manifest']['scenes']:
        p=ROOT/'cad'/x['filename'];assert p.stat().st_size==x['size_bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256']
        assert x['valid_reimported_solids']==x['parts']
    for n in ('R31_A_POSITIVE_OPEN_SHELVES.brep','R31_B_PRESENCE_POCKETS.brep'):
        sh=cq.importers.importBrep(str(ROOT/'cad'/n)).val()
        assert sh.isValid() and len(sh.Solids())==1
    assert (V/'R31_inherited_exit.code').read_text().strip()=='0'
    assert (V/'R31_geometry_exit.code').read_text().strip()=='0'
    assert (V/'R31_new_45_exit.code').read_text().strip()=='0'
    log_receipts={}
    for label,n in LABELS.items():
        logfile='R31_new_45.log' if label=='R31' else f'R31_inherited_{label}.log'
        raw=(V/logfile).read_text(errors='replace')
        found=re.search(r'Ran\s+(\d+)\s+tests?',raw)
        assert found and int(found.group(1))==n and raw.rstrip().endswith('OK'),label
        log_receipts[label]={'tests':n,'filename':logfile,
                             'sha256':hashlib.sha256((V/logfile).read_bytes()).hexdigest()}
    results={'revision':'R31 actual CAD rebuild, adversarial tolerance and real unit-test receipts',
             'timestamp_UTC_not_a_manufacturing_date':'2026-10-11',
             'platform':{'python':platform.python_version(),'cadquery':importlib.metadata.version('cadquery')},
             'R30_frozen_files_verified_untouched':len(freeze['entries']),
             'R30_original_ZIP_sha256':freeze['original_zip_sha256'],
             'inherited_tests_run_and_passed':sum(n for k,n in LABELS.items() if k!='R31'),
             'R31_new_tests_run_and_passed':LABELS['R31'],
             'total_tests_run_and_passed':sum(LABELS.values()),
             'tests_include_negative_failure_scenarios':True,
             'test_receipts':log_receipts,
             'A_B_valid_connected':True,
             'A_shelf_net_added_mm3':round(d['integration']['A_new_volume_mm3']-d['integration']['A_old_volume_mm3'],9),
             'B_shell_net_material_removed_mm3':round(d['integration']['B_old_volume_mm3']-d['integration']['B_new_volume_mm3'],9),
             'reference_pose_count':d['dynamic']['reference_poses'],
             'reference_collision_failures':d['dynamic']['unexpected_clashes'],
             'near_dock_checks':d['dynamic']['near_seat_cases'],
             'tolerance_configs':d['tolerance']['configurations'],
             'tolerance_failure_summary':d['tolerance']['per_width'],
             'inherited_old_escape_modes':d['faults']['old_R30_original_36_escapes'],
             'escapes_if_both_new_interposers_stuck_release':36,
             'new_interposer_force_return_spring_or_bearing_mounted':False,
             'STOW_and_lost_motion_retraction_not_repaired':True,
             'STEP_scene_count':d['STEP_manifest']['scene_count'],
             'STEP_deliberately_bad_ghost_count':sum(x['ghost_known_unsafe'] for x in d['STEP_manifest']['scenes']),
             'real_power_USB_OLED_vendor_qualification_present':False,
             'manufacturing_go':False,
             'report_sha256':{x:hashlib.sha256((V/f'R31_{x}.json').read_bytes()).hexdigest() for x in REPORTS}}
    if write:(V/'R31_results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
    print('R31 ATTEST',results['total_tests_run_and_passed'],'tests; 504 immutable ancestors; MANUFACTURING NO-GO',flush=True)
    return results
if __name__=='__main__':run()
