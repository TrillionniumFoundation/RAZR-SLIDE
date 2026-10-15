"""Independent evidence/receipt validator. A PASS is not a manufacturing approval."""
import hashlib,json,re,platform,importlib.metadata
from pathlib import Path
import cadquery as cq
from r25_capture import ROOT
from r35_attest import COUNTS as PRIOR
COUNTS={**PRIOR,'R36':54}
DOCS=['integration','dynamic','tolerance','faults','STEP_manifest']

def run(write=True):
    freeze=json.loads((ROOT/'audit/R36_R35_immutable.json').read_text())
    assert freeze['original_file_count']==853 and freeze['original_bytes_unchanged']
    for row in freeze['members']:
        file=ROOT/row['path']
        assert file.is_file() and file.stat().st_size==row['size']
        assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256'],row['path']
    docs={n:json.loads((ROOT/f'verification/R36_{n}.json').read_text()) for n in DOCS}
    hw=json.loads((ROOT/'verification/R36_catalogue_fit.json').read_text())
    assert not hw['manufacturing_go'] and len(hw['rows'])==2
    assert all(z['large_shaft_B_shell_overlap_mm3']>1 and z['large_shaft_R35_cap_overlap_mm3']>.2 for z in hw['rows'])
    assert all(z['square_nut_R36_B_interference_mm3']>2.0 for z in hw['rows'])
    assert all(v['manufacturing_go'] is False for v in docs.values())
    i,d,t,f,step=(docs[n] for n in DOCS)
    assert i['B_valid'] and i['B_solids']==1 and i['revised_B_delta_mm3']>4
    assert d['pose_count']==10 and all(not p['unexpected_penetrations_mm3'] for p in d['poses'])
    assert t['configurations']==162 and t['intersections_per_config']==4
    assert t['aggregation']['0.05']['keeper_M08_shank_hole_jam']>0
    assert f['old_R35_direct_pin_axial_loss_blocked_at_0p05_when_keeper_present']
    assert f['M0p8_screw_unthreaded_bore_can_withdraw_without_OCC_contact']
    assert f['R35_original_joint_unsafe']==36 and f['electrical_single_bypass']==3
    assert step['count']==8 and step['ghosts']==5
    for a in step['scenes']:
        assert a['parts']==a['valid_reimport']
        assert hashlib.sha256((ROOT/'cad'/a['file']).read_bytes()).hexdigest()==a['sha256']
    for filename in ('R36_A_R35_UNCHANGED.brep','R36_B_INBOARD_KEEPER_BOSSES_AND_CLEARANCE_BORES.brep'):
        ss=cq.importers.importBrep(str(ROOT/'cad'/filename)).val()
        assert ss.isValid() and len(ss.Solids())==1
    assert (ROOT/'verification/R36_inherited_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R36_new_exit.code').read_text().strip()=='0'
    receipts={}
    for label,count in COUNTS.items():
        name=(f'R36_new_{count}.log' if label=='R36' else f'R36_inherited_{label}.log')
        path=ROOT/'verification'/name;log=path.read_text(errors='replace')
        m=re.search(r'Ran\s+(\d+)\s+tests?',log)
        assert m and int(m.group(1))==count and log.rstrip().endswith('OK'),(label,log[-300:])
        receipts[label]=dict(count=count,log='verification/'+name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    total=sum(COUNTS.values())
    out=dict(revision='R36 conditional stop-plate + unthreaded M0.8 catalogue screw; manufacturing NO-GO',
        python_version=platform.python_version(),cadquery_version=importlib.metadata.version('cadquery'),
        original_R35_zip_sha256=freeze['ancestor_archive_sha256'],original_R35_member_count=853,
        ancestor_bytes_unchanged=True,inherited_test_count=sum(PRIOR.values()),new_R36_test_count=54,
        total_research_tests_reexecuted=total,original_test_receipts=receipts,
        nominal_B_single_solid=True,B_net_added_mm3=i['revised_B_delta_mm3'],
        ten_reference_poses_no_named_interference=True,
        tolerance_configurations=162,nominal_pin_head_catch_both_sides=True,
        stop_plate_current_single_screw_loss_defeats_catch=True,
        no_nut_assembly_route=True,standard_ring_shaft_collides_with_B_and_cap=True,nut_envelope_rejected_due_to_B_interference=True,
        E_ring_current_shaft_mismatch=True,
        legacy_36_of_64_mechanical_unsafe_unresolved=True,
        three_electrical_single_point_bypasses_unresolved=True,
        no_vendor_native_3D_for_contacts_screw_nut=True,
        no_screw_torque_thread_retention_validation=True,
        no_loaded_force_retraction_and_contact_timing=True,
        no_power_USB_OLED_manufacturing_qualifications=True,
        battery_capacity_4700mAh_not_proven=True,
        actual_A_B_finished_equal_external_envelopes_not_proven=True,
        STEP_count=step['count'],GHOST_count=step['ghosts'],
        manufacturing_go=False)
    if write:(ROOT/'verification/R36_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R36 ATTEST',total,'=',sum(PRIOR.values()),'+ 54,',step['count'],'STEP,',step['ghosts'],'GHOST. NO-GO',flush=True)
    return out
if __name__=='__main__':run()
