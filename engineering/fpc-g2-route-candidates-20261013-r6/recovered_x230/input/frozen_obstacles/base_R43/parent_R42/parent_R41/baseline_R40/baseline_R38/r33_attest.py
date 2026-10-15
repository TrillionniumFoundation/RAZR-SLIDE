"""Independent attestation: research tests include explicit NEGATIVE witnesses.
No mechanical/electrical/OLED manufacturing approval is inferred.
"""
from __future__ import annotations
import json,hashlib,re,platform,importlib.metadata
import cadquery as cq
from r25_capture import ROOT
from r32_attest import LABELS as HISTORICAL
NAMES=('integration','retention','dynamic','catalogue','expansion_rejected','STEP_manifest')

def run(write=True):
    immutable=json.loads((ROOT/'audit/R33_R32_immutable.json').read_text())
    assert immutable['R32_ancestor_count']==636 and immutable['R32_all_members_unchanged']
    for x in immutable['records']:
        p=ROOT/x['path']
        assert p.stat().st_size==x['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
    d={x:json.loads((ROOT/'verification'/f'R33_{x}.json').read_text()) for x in NAMES}
    assert all(x['manufacturing_go'] is False for x in d.values())
    assert d['integration']['B_valid_single'] and d['integration']['A_valid_single']
    assert d['retention']['withdrawal_barrier_paths']==2
    assert d['retention']['misalignment_jam_count']==8
    assert d['retention']['pin_axial_no_B_stop_all_offsets']
    assert d['retention']['legacy_mechanical_escape_counterexamples']==36
    assert len(d['dynamic']['unexpected_collisions'])==0 and d['dynamic']['reference_pose_count']==10
    assert d['catalogue']['axis_aligned_channel_fit_count']==0
    assert d['catalogue']['actual_oem_supplier_CAD_imported'] is False
    assert d['expansion_rejected']['keeper_conflicts']==20
    assert d['STEP_manifest']['count']==7 and d['STEP_manifest']['ghost_unsafe_count']==4
    for x in d['STEP_manifest']['scenes']:
        assert hashlib.sha256((ROOT/'cad'/x['file']).read_bytes()).hexdigest()==x['sha256']
        assert x['parts']==x['valid_solids_imported']
    for n in ('R33_A_R32_BYTE_IDENTICAL.brep','R33_B_BILATERAL_PIN_PORTS.brep',
              'R33_B_TE_LARGER_BAY_REJECTED.brep'):
        sh=cq.importers.importBrep(str(ROOT/'cad'/n)).val()
        assert sh.isValid() and len(sh.Solids())==1
    assert (ROOT/'verification/R33_inherited_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R33_new_40_exit.code').read_text().strip()=='0'
    assert (ROOT/'verification/R33_geometry_exit.code').read_text().strip()=='0'
    receipts={}
    for label,count in {**HISTORICAL,'R33':40}.items():
        name='R33_new_40.log' if label=='R33' else f'R33_inherited_{label}.log'
        raw=(ROOT/'verification'/name).read_text(errors='replace')
        match=re.search(r'Ran\s+(\d+)\s+tests?',raw)
        assert match and int(match.group(1))==count and raw.rstrip().endswith('OK'),(label,raw[-100:])
        receipts[label]=dict(tests=count,log='verification/'+name,
                             sha256=hashlib.sha256((ROOT/'verification'/name).read_bytes()).hexdigest())
    out=dict(revision='R33 unpowered removable keeper research + rejected TE true-size envelope',
      date='2026-10-11',python=platform.python_version(),cadquery=importlib.metadata.version('cadquery'),
      frozen_ancestor_R32_zip_sha256=immutable['R32_zip_sha256'],
      ancestor_files_sha_verified=immutable['R32_ancestor_count'],
      inherited_reexecuted_tests=sum(HISTORICAL.values()),new_tests=40,
      total_reexecuted_research_tests=sum(x['tests'] for x in receipts.values()),
      test_receipts=receipts,
      pass_does_not_waive_reported_hazardous_conditions=True,
      B_removed_for_two_pin_holes_mm3=d['integration']['bore_cut_mm3'],
      new_geometry_A_and_B_single_body=True,
      reference_poses_checked=d['dynamic']['reference_pose_count'],
      unexpected_named_reference_pose_collisions=len(d['dynamic']['unexpected_collisions']),
      retention_with_pin_sweep_cases=d['retention']['sweep_cases'],
      retention_both_sides_block_with_pin=d['retention']['withdrawal_barrier_paths']==2,
      pin_axial_escape_unblocked=d['retention']['pin_axial_no_B_stop_all_offsets'],
      pin_misalignment_probes=len(d['retention']['misalignment_cases']),
      pin_misalignment_hard_jam_count=d['retention']['misalignment_jam_count'],
      keeper_missing_or_broken_unopposed=True,
      inherited_64_fault_cases_escape_count=36,
      R33_vendor_catalogue_configurations=d['catalogue']['configurations'],
      R33_TE_envelope_nominal_fit_count=d['catalogue']['axis_aligned_channel_fit_count'],
      R33_TE_enlarged_bay_REJECTED_due_to_critical_web_loss_and_keeper_collision=True,
      STEP_imported_count=d['STEP_manifest']['count'],GHOST_STEP_count=d['STEP_manifest']['ghost_unsafe_count'],
      vendor_TE_native_STEP_imported=False,
      vendor_signal_first_make_last_break_UNVERIFIED=True,
      separate_USB_SI_qualification=False,separate_dual_battery_power_qualification=False,
      mechanical_performance_qualification=False,
      OLED_model_full_package_and_lifetime_qualification=False,
      identical_finished_A_B_outer_shell_CAD_qualification=False,
      manufacturing_go=False)
    if write:(ROOT/'verification/R33_results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print('R33 ATTEST',out['total_reexecuted_research_tests'],'ancestor',out['ancestor_files_sha_verified'],'manufacturing NO-GO',flush=True)
    return out
if __name__=='__main__':run()
