"""Explicitly preserve R34 negative safety evidence and inherited R27/R31 hazards.

Do not promote catalogue size/fit to electrical or mechanical qualification.
"""
from __future__ import annotations
import json
from r25_capture import ROOT

def run(write=True):
    dynamic=json.loads((ROOT/'verification/R34_dynamic.json').read_text())
    tol=json.loads((ROOT/'verification/R34_tolerance.json').read_text())
    history=json.loads((ROOT/'verification/R31_faults.json').read_text())
    power=json.loads((ROOT/'verification/R27_power_faults.json').read_text())
    d=dict(revision='R34 gated decision: catalogue Signal envelope geometric fit only',
           supplier_native_TE_STEP_file_present=False,
           te_catalogue_in_current_miniature_R33_channel_fits=0,
           new_nominal_signal_envelope_B_clashes=0,
           nominal_assembled_reference_pose_clashes=len(dynamic['unexpected_named_pose_collisions']),
           front_feed_rigid_pose_count=dynamic['front_feed_cases'],
           front_feed_rigid_interferences=dynamic['front_feed_interference_cases'],
           rejected_top_feed_pose_count=dynamic['rejected_top_feed_cases'],
           rejected_top_feed_rigid_interferences=dynamic['top_feed_interference_cases'],
           zero_front_cap_or_lid_fitted=True,
           front_feed_reverse_escape_unopposed=True,
           removal_of_R33_unqualified_keeper_does_not_increase_safety=True,
           legacy_mechanical_combined_fault_states=history['old_R30_original_64_fault_modes'],
           legacy_mechanical_combined_fault_escapes=history['old_R30_original_36_escapes'],
           electrical_fault_tree_enumerated_states=power['enumerated_fault_states'],
           electrical_minimal_cut_sets=power['minimal_cut_sets'],
           electrical_single_fault_bypass_count=len(power['one_fault_dangerous_minimal_cuts']),
           TE_2199001_1_for_SIGNAL_only_and_not_power=True,
           power_connectors_and_battery_4700mAh_OEM_unselected=True,
           USB_contact_pinout_TDR_eye_and_EMI_unverified=True,
           live_pad_actual_voltage_and_make_break_mm_unmeasured=True,
           actual_OLED_full_width_dynamic_radius_flatten_force_lifetime_unverified=True,
           hypothetical_point_wall_GDT_FEA_shear_fatigue_unverified=True,
           safety_contact_already_extended_retract_force_unmeasured=True,
           finished_A_B_identical_outer_shell_not_proven=True,
           fail_closed_hardware_lock_not_achieved=True,
           scope='Negative safety acceptance. All CAD results RESEARCH ONLY.',
           manufacturing_go=False)
    if write:(ROOT/'verification/R34_faults.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print('R34 hazards legacy escape',d['legacy_mechanical_combined_fault_escapes'],'single point electrical bypass',d['electrical_single_fault_bypass_count'],'NO-GO',flush=True)
    return d
if __name__=='__main__':run()
